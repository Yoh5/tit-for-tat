"""Les quatre expériences, dans l'ordre où elles démontent l'histoire répandue.

1. **Sans bruit, donnant-donnant gagne.** La vidéo a raison, et on le montre.
2. **Avec du bruit, il perd.** C'est le résultat de Nowak et Sigmund (1992), et
   c'est ce que la vulgarisation ne dit presque jamais.
3. **L'extorsion gagne le duel et perd le monde.** Press et Dyson (2012),
   Stewart et Plotkin (2013).
4. **La question « quelle est la meilleure stratégie » est mal posée** dès qu'on
   peut inscrire plusieurs agents (Southampton, 2004).
5. **Les deux sortes de bruit se valent** pour cette question — un écart attendu
   qui ne se produit pas.
6. **Le pardon rapporte le plus quand les accidents sont rares**, pas quand ils
   sont fréquents.
7. **Être irréprochable ne protège pas** : celui qui dérape gagne plus que celui
   qui ne dérape jamais.

Usage :
    python experiences.py              # les quatre
    python experiences.py --une 2      # une seule
    python experiences.py --json resultats.json
"""
from __future__ import annotations

import argparse
import json
import random
from statistics import mean, stdev
from typing import Any, Dict, List, Optional, Tuple

import proprietes as P
import strategies as S
from tournoi import duel, evolution, matrice_gains, tournoi

#: Niveaux de bruit balayés. 0,01 veut dire « un coup sur cent dérape » : c'est
#: optimiste pour un système distribué, et il suffit déjà à tout changer.
BRUITS = (0.0, 0.01, 0.02, 0.05, 0.10)

TRAIT = "-" * 78


def _pct(v: Optional[float], largeur: int = 8) -> str:
    """Un pourcentage, ou « n/d » quand la mesure n'a pas d'échantillon.

    `entre_soi` rend `None` plutôt que zéro quand aucun accident n'a été
    observé, et cette distinction ne doit pas se perdre à l'affichage : un
    tableau qui imprime 0 % là où il n'a rien mesuré raconte exactement le
    mensonge que ce choix de `None` servait à empêcher.
    """
    return f"{'n/d':>{largeur}}" if v is None else f"{v:>{largeur}.0%}"


def _tours(v: Optional[float], largeur: int = 7) -> str:
    return f"{'-':>{largeur}}" if v is None else f"{v:>{largeur - 1}.1f}t"


def _classement(res, titre: str, montrer: int = 99) -> List[Dict[str, Any]]:
    print(f"\n{titre}")
    print(f"  {'rang':<5} {'stratégie':<32} {'gain/tour':>10}")
    lignes = []
    for i, (nom, score) in enumerate(res.classement()[:montrer], start=1):
        print(f"  {i:<5} {nom:<32} {score:>10.3f}")
        lignes.append({"rang": i, "strategie": nom, "gain_par_tour": round(score, 4)})
    return lignes


def experience_1(graine: int = 1) -> Dict[str, Any]:
    """Sans bruit : ce qui est robuste n'est pas ce qu'on raconte.

    On attendait « donnant-donnant gagne ». Il arrive 6e. Ce n'est pas une
    erreur de mesure et ce n'est pas un démenti d'Axelrod : son tournoi de 1980
    comptait quinze entrées précises, que nous n'avons pas, et il a lui-même
    écrit que le classement dépendait du plateau.

    Ce qui survit au changement de plateau, et que l'expérience vérifie, est
    plus fort et moins cité : **toutes les stratégies gentilles passent devant
    toutes les autres.** Le trait gagnant n'est pas une stratégie, c'est de ne
    pas trahir le premier.
    """
    print(TRAIT)
    print("1. SANS BRUIT — ce qui gagne n'est pas une stratégie, c'est un trait")
    print(TRAIT)
    pool = S.pool_classique()
    res = tournoi(pool, graine=graine, bruit=0.0)
    lignes = _classement(res, "classement, gain moyen par tour :")
    gagnant = res.classement()[0][0]
    rang_dd = res.rang("Donnant-donnant")

    print(f"\n  Les propriétés, mesurées sur les parties (pas déclarées) :")
    print("  " + P.EN_TETE)
    profs = P.profils(res, [s.nom for s in pool])
    for pr in sorted(profs, key=lambda p: -res.moyennes[p.nom]):
        print("  " + pr.ligne())

    # L'affirmation est vérifiée par le code, pas avancée dans le texte.
    gentilles = [p.nom for p in profs if p.gentillesse > 0.99]
    autres = [p.nom for p in profs if p.gentillesse <= 0.99]
    pire_gentille = min(res.moyennes[n] for n in gentilles)
    meilleure_autre = max(res.moyennes[n] for n in autres)
    separe = pire_gentille > meilleure_autre

    print(f"\n  => {gagnant} arrive en tête ; donnant-donnant est {rang_dd}e.")
    print(f"     La dernière des {len(gentilles)} gentilles marque "
          f"{pire_gentille:.3f}, la première des {len(autres)} autres "
          f"{meilleure_autre:.3f}.")
    print(f"     Les deux familles sont{'' if separe else ' NE sont PAS'} "
          f"séparées sans recouvrement.")
    print("\n  « Donnant-donnant gagne » était donc vrai d'un plateau, pas d'un")
    print("  jeu. « Ne trahis pas le premier » tient sur celui-ci aussi.")
    return {"classement": lignes, "gagnant": gagnant,
            "rang_donnant_donnant": rang_dd,
            "gentilles_separees": separe,
            "pire_gentille": round(pire_gentille, 4),
            "meilleure_non_gentille": round(meilleure_autre, 4)}


def experience_2(graine: int = 1, graines: int = 12) -> Dict[str, Any]:
    """Avec du bruit : deux défenses, et chacune son régime.

    **Pourquoi plusieurs graines.** Le premier jet de cette expérience tournait
    sur une seule, et annonçait « Donnant-donnant généreux gagne dès 1% de
    bruit ». Sur douze graines, ce vainqueur-là n'est majoritaire à aucun
    niveau : à 0% de bruit, le classement lui-même n'est pas stable (trois
    stratégies différentes gagnent selon la graine). Un vainqueur lu sur une
    exécution n'est pas un résultat, c'est un tirage.

    Ce qui est stable, et c'est le résultat : **l'ordre des régimes.**
    """
    print("\n" + TRAIT)
    print("2. AVEC DU BRUIT — deux défenses, et chacune son régime")
    print(TRAIT)
    print("\n  Bruit d'exécution : un coup sur N dérape. Les deux joueurs voient")
    print("  le mauvais coup ; personne n'a triché.")
    print(f"  Vainqueur compté sur {graines} graines, parce qu'une seule ne")
    print("  départage rien (voir le docstring).\n")
    print(f"  {'bruit':>6}  {'vainqueurs (sur ' + str(graines) + ')':<52} "
          f"{'rang moyen DD':>13}")

    from collections import Counter
    suivi = []
    for bruit in BRUITS + (0.20,):
        votes: Counter = Counter()
        rangs = []
        for g in range(1, graines + 1):
            r = tournoi(S.pool_classique(), graine=g, bruit=bruit)
            votes[r.classement()[0][0]] += 1
            rangs.append(r.rang("Donnant-donnant"))
        resume = ", ".join(f"{n} {c}" for n, c in votes.most_common(3))
        moyen = sum(rangs) / len(rangs)
        print(f"  {bruit:>6.0%}  {resume[:52]:<52} {moyen:>13.1f}")
        suivi.append({"bruit": bruit, "votes": dict(votes),
                      "rang_moyen_donnant_donnant": round(moyen, 2)})

    print("\n  Donnant-donnant ne gagne à aucun niveau, et son rang ne bouge")
    print("  presque pas : ce n'est pas lui que le bruit départage.")

    # Le mécanisme. Mesuré sur les paires de clones : une stratégie ne peut pas
    # réparer une relation à elle seule, donc la moyenne tous adversaires
    # confondus ne répond pas à la question (elle mettait Pavlov au niveau de
    # donnant-donnant, à cause des adversaires avec qui rien n'est réparable).
    print("\n  UNE PAIRE DE CLONES, après un accident de l'un des deux.")
    print("  Part des accidents dont la paire ne retrouve pas la coopération")
    print("  dans une fenêtre de 10 tours sans nouvel accident :\n")
    print(f"  {'stratégie':<32} " +
          " ".join(f"{b:>10.0%}" for b in BRUITS[1:]) + f" {'délai':>8}")
    mecanisme: Dict[str, Any] = {}
    cache = {b: tournoi(S.pool_classique(), graine=graine, bruit=b,
                        repetitions=60) for b in BRUITS[1:]}
    for s in S.pool_classique():
        mesures = [P.entre_soi(cache[b], s.nom) for b in BRUITS[1:]]
        parts = [m["part_non_reparee"] for m in mesures]
        d = mesures[-1]["delai_moyen"]
        print(f"  {s.nom:<32} " + " ".join(_pct(p, 10) for p in parts) +
              (f" {'jamais':>8}" if d is None else f" {d:>7.1f}t"))
        mecanisme[s.nom] = {"parts_non_reparees": [None if p is None else round(p, 4)
                                                   for p in parts],
                            "delai_moyen": None if d is None else round(d, 2),
                            "echantillons": [m["echantillon"] for m in mesures]}

    print("\n  Le chiffre ne bouge pas avec le bruit : c'est une propriété de la")
    print("  stratégie, pas du niveau de bruit — ce qu'on attend d'une mesure")
    print("  bien posée. Il a fallu trois versions pour l'obtenir (voir")
    print("  proprietes.FENETRE : les deux premières mesuraient la chance, puis")
    print("  un biais de survie).")
    print("\n  DEUX DONNANT-DONNANT NE SE RELÈVENT PAS DE LEUR PROPRE ACCIDENT")
    print("  DANS ENVIRON TROIS CAS SUR QUATRE. Le mécanisme est un écho : A")
    print("  dérape, B riposte, A riposte à la riposte, et la paire alterne")
    print("  trahison et coopération en décalé sans jamais retomber en phase.")
    print("\n  Trois stratégies se relèvent toujours, et chacune autrement :")
    print("   - ABSORBER (Donnant-donnant x2, 0%, 1 tour) : ne riposte qu'à la")
    print("     deuxième trahison, donc un accident isolé ne déclenche rien ;")
    print("   - SORTIR (Pavlov, 0%, 2 tours) : change de coup quand un tour a")
    print("     mal payé, donc quitte la spirale sans attendre un geste ;")
    print("   - PARDONNER (généreux, 1-2%, 2,7 tours) : rouvre au hasard, ce qui")
    print("     suffit à casser l'écho.")
    print("\n  Et Rancunier est à 100% : il condamne toute relation sur le")
    print("  premier accident. C'est la stratégie qui gagnait l'expérience 1.")
    return {"balayage_multigraines": suivi, "entre_clones": mecanisme,
            "niveaux": list(BRUITS[1:]), "fenetre": P.FENETRE}


def experience_3(graine: int = 1) -> Dict[str, Any]:
    """L'extorsion : imbattable en duel, non viable en population."""
    print("\n" + TRAIT)
    print("3. L'EXTORSION — gagner le duel, perdre le monde")
    print(TRAIT)

    pool = S.pool_moderne()
    res = tournoi(pool, graine=graine, bruit=0.0)
    _classement(res, "tournoi toutes contre toutes (plateau moderne) :")

    noms, A = matrice_gains(pool, graine=graine, repetitions=10)
    i = noms.index("Extorsion (ZD, x2)")
    j = noms.index("Donnant-donnant")
    print(f"\n  En face-à-face : extorsion contre donnant-donnant "
          f"=> {A[i][j]:.3f} contre {A[j][i]:.3f}")
    k = noms.index("Toujours coopérer")
    print(f"  Extorsion contre un coopérateur naïf "
          f"=> {A[i][k]:.3f} contre {A[k][i]:.3f}")

    parts = evolution(noms, A, generations=2000)
    print("\n  Dynamique de réplication, 2000 générations, départ à parts égales :")
    for nom, part in sorted(parts.items(), key=lambda kv: -kv[1]):
        if part > 1e-4:
            print(f"    {nom:<32} {part:>7.1%}")
    eteintes = [n for n, p in parts.items() if p <= 1e-4]
    if eteintes:
        print(f"    (éteintes : {', '.join(eteintes)})")

    print("\n  L'extorqueur rançonne qui se laisse faire, mais il ruine ses")
    print("  partenaires — et il vit de leur présence. Sa victoire en duel ne")
    print("  survit pas au fait que la population change.")
    return {
        "extorsion_vs_donnant_donnant": [round(A[i][j], 4), round(A[j][i], 4)],
        "extorsion_vs_cooperateur": [round(A[i][k], 4), round(A[k][i], 4)],
        "parts_finales": {n: round(p, 5) for n, p in parts.items()},
    }


def experience_4(graine: int = 1) -> Dict[str, Any]:
    """La coalition : la question de « la meilleure stratégie » se dissout."""
    print("\n" + TRAIT)
    print("4. LA COALITION — pourquoi la question est mal posée")
    print(TRAIT)
    print("\n  En 2004, au tournoi du 20e anniversaire, une équipe de")
    print("  Southampton a inscrit une soixantaine d'agents qui se")
    print("  reconnaissaient par une signature de premiers coups : les")
    print("  sacrifiés nourrissaient le récolteur, qui a pris la première place.")

    pool: List[S.Strategie] = S.pool_classique()
    recolteur = S.Equipe(recolte=True)
    recolteur.nom = "Coalition (récolteur)"
    pool.append(recolteur)
    sacrifies = []
    for n in range(8):
        s = S.Equipe(recolte=False)
        s.nom = f"Coalition (sacrifié {n + 1})"
        sacrifies.append(s)
    pool.extend(sacrifies)

    res = tournoi(pool, graine=graine, bruit=0.0)
    _classement(res, "classement avec la coalition en lice :", montrer=6)

    rang_r = res.rang("Coalition (récolteur)")
    moy_sacrifies = sum(res.moyennes[s.nom] for s in sacrifies) / len(sacrifies)
    print(f"\n  Récolteur : rang {rang_r}, gain {res.moyennes['Coalition (récolteur)']:.3f}")
    print(f"  Sacrifiés : gain moyen {moy_sacrifies:.3f} "
          f"(rangs {', '.join(str(res.rang(s.nom)) for s in sacrifies[:3])}, ...)")
    print(f"  Donnant-donnant : rang {res.rang('Donnant-donnant')}")

    print("\n  Un classement individuel ne dit donc pas quelle stratégie est")
    print("  bonne : il dit qui a été le mieux servi par les règles d'inscription.")
    print("  « La meilleure stratégie » n'existe pas sans dire combien d'agents")
    print("  on peut inscrire, et s'ils peuvent se reconnaître.")
    return {
        "rang_recolteur": rang_r,
        "gain_recolteur": round(res.moyennes["Coalition (récolteur)"], 4),
        "gain_moyen_sacrifies": round(moy_sacrifies, 4),
        "rang_donnant_donnant": res.rang("Donnant-donnant"),
    }


def experience_5(graine: int = 1) -> Dict[str, Any]:
    """Les deux bruits : une distinction réelle, et sans effet mesurable.

    Le coup qui dérape et le coup mal lu sont deux accidents différents. Dans le
    premier, le fautif voit son propre dérapage ; dans le second, personne ne
    sait qui s'est trompé. La littérature les traite séparément et on s'attend à
    ce que ça compte.

    Ça ne compte presque pas — pour cette question-là. Ce qui vaut d'être dit,
    parce qu'un écart attendu qui ne se produit pas est aussi un résultat.
    """
    print("\n" + TRAIT)
    print("5. LES DEUX BRUITS — un écart attendu qui n'arrive pas")
    print(TRAIT)
    print("\n  Exécution : le coup joué dérape, les deux voient le même coup.")
    print("  Perception : le coup est juste, la lecture ne l'est pas, et les")
    print("  deux joueurs ont des historiques différents sans pouvoir le savoir.\n")

    ex = tournoi(S.pool_classique(), graine=graine, bruit=0.05, repetitions=60)
    pe = tournoi(S.pool_classique(), graine=graine, bruit=0.05, repetitions=60,
                 perception=True)

    print(f"  {'stratégie':<32} {'exécution':>10} {'délai':>7} "
          f"{'perception':>12} {'délai':>7}")
    compare = {}
    for s in S.pool_classique():
        a, b = P.entre_soi(ex, s.nom), P.entre_soi(pe, s.nom)
        print(f"  {s.nom:<32} {_pct(a['part_non_reparee'], 10)} "
              f"{_tours(a['delai_moyen'])} {_pct(b['part_non_reparee'], 12)} "
              f"{_tours(b['delai_moyen'])}")
        compare[s.nom] = {"execution": a, "perception": b}

    print("\n  Les parts sont identiques à un point près. Le seul écart tient en")
    print("  un tour : Pavlov se relève en 2 tours quand le coup a dérapé, en 3")
    print("  quand il a été mal lu — le malentendu lui coûte un tour de punition")
    print("  de plus avant que les deux n'atteignent (trahir, trahir), l'état")
    print("  dont elle sait sortir.")
    print("\n  J'avais écrit le contraire dans tournoi.py avant de le mesurer :")
    print("  que Pavlov s'en sortirait dans un cas et pas dans l'autre. La")
    print("  distinction est réelle dans le mécanisme et sans effet sur le")
    print("  résultat. Un écart attendu qui ne vient pas se publie aussi.")

    print(f"\n  {'':<13} {'tête du classement':<40}")
    for nom, r in (("exécution", ex), ("perception", pe)):
        tete = " | ".join(f"{n[:20]} {v:.2f}" for n, v in r.classement()[:3])
        print(f"  {nom:<13} {tete}")
    return {"comparaison": compare,
            "classement_execution": ex.classement()[:3],
            "classement_perception": pe.classement()[:3]}


#: Taux de pardon balayés. Resserrés autour de l'optimum, étalés ailleurs.
PARDONS = (0.0, 0.05, 0.10, 0.15, 0.20, 0.25, 0.33, 0.50, 0.75, 1.0)

#: Niveaux de bruit, resserrés en bas : le résultat de l'expérience 6 vit entre
#: 0,5 % et 3 %, et un échantillonnage par pas de 5 % le manquerait entièrement.
BRUITS_FINS = (0.0, 0.005, 0.01, 0.02, 0.03, 0.05, 0.08, 0.12, 0.20, 0.30)


def _pool_avec_pardon(g: float) -> List[S.Strategie]:
    """Le plateau classique où la stratégie généreuse prend le taux `g`.

    Le plateau **garde ses exploiteurs** — Toujours trahir, Aléatoire, le
    Sondeur. Sans eux l'arbitrage disparaît : pardonner serait gratuit et
    l'optimum vaudrait trivialement 1.
    """
    base = [s for s in S.pool_classique()
            if not s.nom.startswith("Donnant-donnant g")]
    gt = S.donnant_donnant_genereux(g)
    gt.nom = "CANDIDAT"
    return base + [gt]


def _gain(g: float, bruit: float, graines: int) -> Tuple[float, float]:
    """Gain moyen du candidat, et erreur-type de cette moyenne.

    L'erreur-type n'est pas décorative : sans elle, on lit un écart de 0,004
    comme un déplacement d'optimum. C'est exactement ce que la première version
    de cette expérience a fait.
    """
    v = [tournoi(_pool_avec_pardon(g), graine=s, tours=120, repetitions=10,
                 bruit=bruit).moyennes["CANDIDAT"]
         for s in range(1, graines + 1)]
    return mean(v), (stdev(v) / len(v) ** 0.5 if len(v) > 1 else 0.0)


def experience_6(graine: int = 1, graines: int = 16) -> Dict[str, Any]:
    """À quel taux pardonner — et surtout, quand est-ce que ça compte ?

    Deux questions, et c'est la seconde qui donne le résultat.

    **L'hypothèse de départ était qu'il faut pardonner d'autant plus que le
    bruit est fort. Elle est fausse.** L'optimum reste autour de 0,20 à tous les
    niveaux, et la bande indistinguable du meilleur est bien trop large pour
    qu'un argmax veuille dire quelque chose.

    Ce qui bouge, c'est le **coût de ne pas pardonner**, et il n'est pas
    monotone : il culmine vers 1 à 2 % de bruit et s'annule au-delà de 20 %.
    """
    print("\n" + TRAIT)
    print("6. QUAND LE PARDON COMPTE — un coût qui culmine là où on l'attend pas")
    print(TRAIT)
    print(f"\n  Donnant-donnant qui pardonne au taux g, dans un plateau qui")
    print(f"  garde ses exploiteurs. Moyennes sur {graines} graines.\n")

    print("  a) L'optimum se déplace-t-il avec le bruit ?\n")
    repere = (0.0, 0.01, 0.05, 0.10)
    print(f"  {'g':>6} " + " ".join(f"{b:>8.0%}" for b in repere))
    table: Dict[float, List[float]] = {}
    erreurs: Dict[float, List[float]] = {}
    for g in PARDONS:
        paires = [_gain(g, b, graines) for b in repere]
        table[g] = [m for m, _ in paires]
        erreurs[g] = [e for _, e in paires]
        print(f"  {g:>6.2f} " + " ".join(f"{m:>8.3f}" for m in table[g]))

    optima = []
    for i, b in enumerate(repere):
        meilleur = max(PARDONS, key=lambda g: table[g][i])
        marge = 2 * max(erreurs[g][i] for g in PARDONS)
        bande = [g for g in PARDONS if table[g][i] >= table[meilleur][i] - marge]
        optima.append({"bruit": b, "argmax": meilleur,
                       "bande": [min(bande), max(bande)]})
        print(f"  bruit {b:>5.0%} : meilleur g = {meilleur:.2f}, bande "
              f"indistinguable [{min(bande):.2f}, {max(bande):.2f}]")

    print("\n  => L'optimum ne bouge pas. L'hypothèse de départ n'est pas")
    print("     soutenue, et la bande est trop large pour qu'un argmax compte.")
    print("     Le 1/3 de Nowak et Sigmund est dedans, un peu au-dessus.")

    print("\n  b) Alors qu'est-ce qui bouge ? LE COÛT DE NE JAMAIS PARDONNER.\n")
    print(f"  {'bruit':>7} {'g=0':>8} {'meilleur':>9} {'écart':>8} {'±':>7}")
    courbe = []
    for b in BRUITS_FINS:
        base, eb = _gain(0.0, b, graines)
        g_etoile, top, et = max(((g, *_gain(g, b, graines))
                                 for g in (0.10, 0.20, 0.30)),
                                key=lambda r: r[1])
        ecart = (top / base - 1) * 100 if base else 0.0
        err = (((et / base) ** 2 + (top * eb / base ** 2) ** 2) ** 0.5 * 100
               if base else 0.0)
        print(f"  {b:>7.1%} {base:>8.3f} {top:>9.3f} {ecart:>7.1f}% {err:>6.1f}%")
        courbe.append({"bruit": b, "gain_sans_pardon": round(base, 4),
                       "gain_optimal": round(top, 4),
                       "ecart_pct": round(ecart, 2),
                       "erreur_pct": round(err, 2), "g_etoile": g_etoile})

    pic = max(courbe, key=lambda r: r["ecart_pct"])
    print(f"\n  => Le coût culmine à {pic['ecart_pct']:.1f}% vers "
          f"{pic['bruit']:.1%} de bruit, et s'annule au-delà de 20%.")
    print("\n  LE PARDON RAPPORTE LE PLUS QUAND LES ACCIDENTS SONT RARES.")
    print("\n  Le mécanisme : à 1% de bruit, un accident est rare mais il tue")
    print("  définitivement une longue relation, et on perd tout le reste de la")
    print("  partie. À 20%, plus personne ne tient une coopération de toute")
    print("  façon — il n'y a plus de relation à perdre, et le bruit suivant")
    print("  casse l'écho tout seul.")
    print("\n  Le régime dangereux est donc celui qui a l'air fiable : assez")
    print("  rare pour qu'on ne prévoie pas de reprise, assez définitif pour")
    print("  que chaque accident coûte une relation entière.")
    return {"table_optimum": {f"{g:.2f}": [round(v, 4) for v in table[g]]
                              for g in PARDONS},
            "repere": list(repere), "optima": optima, "courbe_cout": courbe,
            "pic": pic, "graines": graines}


#: Les deux joueurs, du moins indulgent au plus indulgent. L'ordre est le
#: résultat : c'est lui qu'on lit dans la colonne d'écart.
ECHELLE_DU_PARDON = [
    ("Rancunier (aucun pardon)", S.Rancunier),
    ("Donnant-donnant", S.donnant_donnant),
    ("Généreux 1/8", lambda: S.donnant_donnant_genereux(0.125)),
    ("Généreux 1/3", S.donnant_donnant_genereux),
    ("Généreux 2/3", lambda: S.donnant_donnant_genereux(2 / 3)),
    ("Donnant-donnant x2", S.DonnantDonnantDeuxFois),
    ("Toujours coopérer", S.ToujoursCooperer),
]


def _duo(fabrique, bruit_a: float, bruit_b: float,
         graines: int = 600) -> Tuple[float, float, float]:
    """Deux clones, l'un fiable et l'autre non. Rend (gain A, gain B, erreur)."""
    ga, gb = [], []
    for g in range(graines):
        d = duel(fabrique(), fabrique(), random.Random(g * 7919 + 13),
                 tours=200, bruit=(bruit_a, bruit_b))
        ga.append(d.gain_a / d.tours)
        gb.append(d.gain_b / d.tours)
    err = ((stdev(ga) ** 2 + stdev(gb) ** 2) / len(ga)) ** 0.5
    return mean(ga), mean(gb), err


def experience_7(graine: int = 1, bruit: float = 0.04) -> Dict[str, Any]:
    """Ma fiabilité me protège-t-elle d'un correspondant qui dérape ? Non.

    Jusqu'ici les deux joueurs subissaient le même bruit. Ce n'est pas la
    situation qu'on rencontre : deux services n'ont pas la même fiabilité, et la
    question qu'on se pose vraiment est de savoir si la sienne sert à quelque
    chose.

    **Elle ne sert pas.** Le joueur irréprochable finit *derrière* celui qui
    commet toutes les erreurs — parce qu'un dérapage est une trahison, qu'une
    trahison contre un coopérateur rapporte la tentation, et que les représailles
    qui suivent se paient à deux. L'accident enrichit celui qui le commet.

    Et l'écart grandit avec le pardon : plus on est indulgent, plus on
    subventionne un correspondant peu fiable.
    """
    print("\n" + TRAIT)
    print("7. LA FIABILITÉ NE PROTÈGE PAS — c'est le pardon de l'autre qui le fait")
    print(TRAIT)
    print(f"\n  A est IRRÉPROCHABLE (0 % de bruit). B dérape {bruit:.0%} du temps.")
    print("  Les deux jouent la même stratégie, de la moins à la plus indulgente.\n")
    print(f"  {'stratégie des deux':<28} {'A parfait':>10} {'B fautif':>10} "
          f"{'écart':>12}")
    lignes = []
    for nom, fabrique in ECHELLE_DU_PARDON:
        a, b, err = _duo(fabrique, 0.0, bruit)
        print(f"  {nom:<28} {a:>10.3f} {b:>10.3f} {b - a:>+9.3f} ±{err:.3f}")
        lignes.append({"strategie": nom, "gain_irreprochable": round(a, 4),
                       "gain_fautif": round(b, 4), "ecart": round(b - a, 4),
                       "erreur": round(err, 4)})

    rancunier = lignes[0]
    cooperer = lignes[-1]
    print(f"\n  => Sauf chez Rancunier, CELUI QUI DÉRAPE GAGNE PLUS QUE CELUI QUI")
    print(f"     NE DÉRAPE JAMAIS, et l'écart suit l'indulgence : "
          f"{lignes[1]['ecart']:+.3f} pour donnant-donnant, "
          f"{cooperer['ecart']:+.3f} pour la coopération inconditionnelle.")
    print("\n  Le mécanisme est simple une fois dit : un dérapage est une")
    print("  trahison, une trahison contre un coopérateur rapporte la tentation,")
    print("  et les représailles qui suivent se paient à deux. L'accident")
    print("  enrichit celui qui le commet.")
    print(f"\n  Rancunier est la seule exception — l'irréprochable y finit devant")
    print(f"  de {-rancunier['ecart']:.3f}. Mais les deux y gagnent "
          f"{rancunier['gain_irreprochable']:.2f} et "
          f"{rancunier['gain_fautif']:.2f} contre près de 2,9 ailleurs : il")
    print("  gagne la comparaison en ruinant les deux joueurs.")
    print("\n  CE QUE ÇA CHANGE. Le pardon n'est ni gratuit ni altruiste : c'est")
    print("  un transfert, et il va précisément à celui qui dérape. On le")
    print("  consent parce que refuser coûte davantage — mais on le paie, et")
    print("  une politique de reprise indulgente subventionne le correspondant")
    print("  le moins fiable. Raison de mesurer sa fiabilité séparément plutôt")
    print("  que de la supposer réglée par la sienne.")
    return {"bruit": bruit, "lignes": lignes}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--une", type=int, choices=(1, 2, 3, 4, 5, 6, 7))
    ap.add_argument("--graine", type=int, default=1)
    ap.add_argument("--json")
    args = ap.parse_args()

    faire = {1: experience_1, 2: experience_2, 3: experience_3,
             4: experience_4, 5: experience_5, 6: experience_6,
             7: experience_7}
    choisies = [args.une] if args.une else [1, 2, 3, 4, 5, 6, 7]
    out = {f"experience_{k}": faire[k](args.graine) for k in choisies}

    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump({"graine": args.graine, **out}, f,
                      ensure_ascii=False, indent=2)
        print(f"\necrit : {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
