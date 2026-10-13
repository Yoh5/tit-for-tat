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

Usage :
    python experiences.py              # les quatre
    python experiences.py --une 2      # une seule
    python experiences.py --json resultats.json
"""
from __future__ import annotations

import argparse
import json
from typing import Any, Dict, List

import proprietes as P
import strategies as S
from tournoi import evolution, matrice_gains, tournoi

#: Niveaux de bruit balayés. 0,01 veut dire « un coup sur cent dérape » : c'est
#: optimiste pour un système distribué, et il suffit déjà à tout changer.
BRUITS = (0.0, 0.01, 0.02, 0.05, 0.10)

TRAIT = "-" * 78


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
        print(f"  {s.nom:<32} " + " ".join(f"{p:>10.0%}" for p in parts) +
              (f" {'jamais':>8}" if d != d else f" {d:>7.1f}t"))
        mecanisme[s.nom] = {"parts_non_reparees": [round(p, 4) for p in parts],
                            "delai_moyen": None if d != d else round(d, 2),
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

    def pct(v):
        return " n/d " if v is None else f"{v:>4.0%}"

    def tours(v):
        return "   - " if v is None else f"{v:>3.1f}t"

    print(f"  {'stratégie':<32} {'exécution':>10} {'délai':>7} "
          f"{'perception':>12} {'délai':>7}")
    compare = {}
    for s in S.pool_classique():
        a, b = P.entre_soi(ex, s.nom), P.entre_soi(pe, s.nom)
        print(f"  {s.nom:<32} {pct(a['part_non_reparee']):>10} "
              f"{tours(a['delai_moyen']):>7} {pct(b['part_non_reparee']):>12} "
              f"{tours(b['delai_moyen']):>7}")
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


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--une", type=int, choices=(1, 2, 3, 4, 5))
    ap.add_argument("--graine", type=int, default=1)
    ap.add_argument("--json")
    args = ap.parse_args()

    faire = {1: experience_1, 2: experience_2, 3: experience_3,
             4: experience_4, 5: experience_5}
    choisies = [args.une] if args.une else [1, 2, 3, 4, 5]
    out = {f"experience_{k}": faire[k](args.graine) for k in choisies}

    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump({"graine": args.graine, **out}, f,
                      ensure_ascii=False, indent=2)
        print(f"\necrit : {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
