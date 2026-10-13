"""Tests : les affirmations du README, vérifiées par le code.

Le principe est celui du reste du dépôt : on ne demande pas au lecteur de
croire une dérivation. Les trois affirmations qui portent l'argument —
l'écho de donnant-donnant, le relèvement de Pavlov, et le fait que l'extorsion
extorque — sont des **tests**, pas des phrases.

    python -m pytest test_tournoi.py -q
"""
from __future__ import annotations

import random

import proprietes as P
import pytest
import strategies as S
from tournoi import duel, evolution, matrice_gains, tournoi


def alea():
    return random.Random(0)


# --------------------------------------------------------------------------- #
# Le jeu
# --------------------------------------------------------------------------- #
def test_cest_bien_un_dilemme_du_prisonnier():
    """T > R > P > S, et 2R > T + S pour que la coopération mutuelle batte
    l'alternance entre trahisons."""
    assert S.T > S.R > S.P > S.S
    assert 2 * S.R > S.T + S.S


def test_gains_symetriques():
    for (a, b), (ga, gb) in S.GAINS.items():
        assert S.GAINS[(b, a)] == (gb, ga)


# --------------------------------------------------------------------------- #
# Les stratégies font ce que leur nom dit
# --------------------------------------------------------------------------- #
def test_donnant_donnant_copie():
    dd = S.donnant_donnant()
    assert dd.jouer([], [], alea()) == S.COOP, "gentille : coopère d'abord"
    assert dd.jouer([S.COOP], [S.TRAHIR], alea()) == S.TRAHIR
    assert dd.jouer([S.TRAHIR], [S.COOP], alea()) == S.COOP


@pytest.mark.parametrize("mien,sien,attendu", [
    (S.COOP, S.COOP, S.COOP),      # R : gagné, on garde
    (S.COOP, S.TRAHIR, S.TRAHIR),  # S : perdu, on change
    (S.TRAHIR, S.COOP, S.TRAHIR),  # T : gagné, on garde
    (S.TRAHIR, S.TRAHIR, S.COOP),  # P : perdu, on change
])
def test_pavlov_win_stay_lose_shift(mien, sien, attendu):
    assert S.pavlov().jouer([mien], [sien], alea()) == attendu


def test_pardon_genereux_vaut_un_tiers():
    """Nowak et Sigmund : min(1-(T-R)/(R-S), (R-P)/(T-P)) ; ici 1/3."""
    assert S.PARDON == pytest.approx(1 / 3)


def test_rancunier_ne_pardonne_jamais():
    r = S.Rancunier()
    assert r.jouer([S.COOP], [S.TRAHIR], alea()) == S.TRAHIR
    assert r.jouer([S.TRAHIR] * 9, [S.TRAHIR] + [S.COOP] * 8, alea()) == S.TRAHIR


def test_donnant_donnant_deux_fois_absorbe_un_accident():
    """Une trahison isolée ne déclenche rien ; deux de suite, oui."""
    d = S.DonnantDonnantDeuxFois()
    assert d.jouer([S.COOP], [S.TRAHIR], alea()) == S.COOP
    assert d.jouer([S.COOP] * 2, [S.TRAHIR] * 2, alea()) == S.TRAHIR


# --------------------------------------------------------------------------- #
# Le mécanisme central : l'écho
# --------------------------------------------------------------------------- #
def _echo(fabrique, tours: int = 40) -> bool:
    """Deux clones, un seul accident au tour 0 : retrouvent-ils la coopération ?

    On force le dérapage à la main plutôt que d'attendre le bruit, pour que le
    test soit déterministe et que l'accident soit exactement un.
    """
    a, b = fabrique(), fabrique()
    a.nouvelle_partie()
    b.nouvelle_partie()
    ha, hb = [], []
    al = alea()
    for t in range(tours):
        ca = a.jouer(ha, hb, al)
        cb = b.jouer(hb, ha, al)
        if t == 0:
            ca = S.TRAHIR  # l'accident, une fois
        ha.append(ca)
        hb.append(cb)
        if t > 0 and ca == S.COOP and cb == S.COOP:
            return True
    return False


def test_deux_donnant_donnant_ne_se_relevent_pas():
    """L'AFFIRMATION CENTRALE : un seul accident condamne la paire.

    A dérape, B riposte, A riposte à la riposte : les deux alternent trahison
    et coopération en décalé et ne retombent jamais en phase.
    """
    assert not _echo(S.donnant_donnant), "donnant-donnant devrait rester coincé"


def test_rancunier_est_pire_encore():
    assert not _echo(S.Rancunier)


@pytest.mark.parametrize("fabrique", [
    S.pavlov,                       # sort de la spirale de lui-même
    S.DonnantDonnantDeuxFois,       # absorbe l'accident
    S.donnant_donnant_genereux,     # pardonne au hasard
])
def test_ces_strategies_se_relevent(fabrique):
    assert _echo(fabrique), f"{fabrique} devrait retrouver la coopération"


def test_pavlov_se_releve_en_deux_tours():
    """Le détail du mécanisme : (D,C) puis (D,D) puis (C,C)."""
    a, b = S.pavlov(), S.pavlov()
    ha, hb = [S.TRAHIR], [S.COOP]          # l'accident vient d'avoir lieu
    al = alea()
    ca, cb = a.jouer(ha, hb, al), b.jouer(hb, ha, al)
    assert (ca, cb) == (S.TRAHIR, S.TRAHIR), "elle encaisse un tour de punition"
    ha.append(ca)
    hb.append(cb)
    assert (a.jouer(ha, hb, al), b.jouer(hb, ha, al)) == (S.COOP, S.COOP)


# --------------------------------------------------------------------------- #
# L'extorsion extorque — mesuré, pas affirmé
# --------------------------------------------------------------------------- #
def test_extorsion_extorque():
    """Contre un coopérateur naïf, elle doit prendre nettement plus qu'elle ne
    donne. On ne vérifie pas la dérivation de Press et Dyson, on vérifie la
    propriété qu'elle annonce."""
    noms, A = matrice_gains([S.extorsion_zd(), S.ToujoursCooperer()],
                            graine=3, tours=400, repetitions=8)
    i, j = noms.index("Extorsion (ZD, x2)"), noms.index("Toujours coopérer")
    assert A[i][j] > A[j][i] * 1.4, (A[i][j], A[j][i])


def test_extorsion_bat_donnant_donnant_en_duel():
    noms, A = matrice_gains([S.extorsion_zd(), S.donnant_donnant()],
                            graine=3, tours=400, repetitions=8)
    i, j = noms.index("Extorsion (ZD, x2)"), noms.index("Donnant-donnant")
    assert A[i][j] > A[j][i]


def test_extorsion_disparait_en_population():
    """Et pourtant elle s'éteint : elle vit de partenaires qu'elle ruine."""
    pool = S.pool_moderne()
    noms, A = matrice_gains(pool, graine=3, tours=200, repetitions=6)
    parts = evolution(noms, A, generations=3000)
    assert parts["Extorsion (ZD, x2)"] < 1e-3
    assert parts["Toujours trahir"] < 1e-3


# --------------------------------------------------------------------------- #
# Le tournoi
# --------------------------------------------------------------------------- #
def test_les_gentilles_passent_devant_les_autres():
    """Le seul résultat de l'expérience 1 qui résiste au changement de plateau."""
    res = tournoi(S.pool_classique(), graine=1, bruit=0.0)
    profs = P.profils(res, [s.nom for s in S.pool_classique()])
    gentilles = [p.nom for p in profs if p.gentillesse > 0.99]
    autres = [p.nom for p in profs if p.gentillesse <= 0.99]
    assert gentilles and autres
    assert (min(res.moyennes[n] for n in gentilles)
            > max(res.moyennes[n] for n in autres))


def test_donnant_donnant_ne_gagne_pas_ce_plateau():
    """Pour que personne ne lise le dépôt comme une réplication de 1980."""
    res = tournoi(S.pool_classique(), graine=1, bruit=0.0)
    assert res.rang("Donnant-donnant") > 1


def test_deterministe_a_graine_fixee():
    a = tournoi(S.pool_classique(), graine=7, bruit=0.05)
    b = tournoi(S.pool_classique(), graine=7, bruit=0.05)
    assert a.classement() == b.classement()


def test_noms_uniques_exiges():
    with pytest.raises(ValueError):
        tournoi([S.donnant_donnant(), S.donnant_donnant()])


def test_longueur_tiree_evite_la_recurrence():
    """Les durées varient : sinon trahir au dernier tour serait dominant."""
    al = random.Random(1)
    longueurs = {len(duel(S.donnant_donnant(), S.ToujoursCooperer(), al,
                          tours=50).joues_a) for _ in range(30)}
    assert len(longueurs) > 5


# --------------------------------------------------------------------------- #
# La mesure
# --------------------------------------------------------------------------- #
def test_le_retablissement_ne_depend_pas_du_bruit():
    """Une mesure bien posée est une propriété de la stratégie.

    C'est ce test qui a validé la troisième version de `_delais` : les deux
    premières donnaient un chiffre qui variait du simple au triple selon le
    niveau de bruit, parce qu'elles mesuraient tantôt la chance, tantôt un
    biais de survie.
    """
    parts = []
    for bruit in (0.02, 0.10):
        res = tournoi(S.pool_classique(), graine=2, bruit=bruit, repetitions=60)
        parts.append(P.entre_soi(res, "Donnant-donnant")["part_non_reparee"])
    assert abs(parts[0] - parts[1]) < 0.12, parts


def test_entre_soi_separe_pavlov_de_donnant_donnant():
    """La mesure tous adversaires confondus les confondait à 55% chacun."""
    res = tournoi(S.pool_classique(), graine=2, bruit=0.05, repetitions=60)
    dd = P.entre_soi(res, "Donnant-donnant")["part_non_reparee"]
    pv = P.entre_soi(res, "Pavlov")["part_non_reparee"]
    assert dd > 0.5 and pv < 0.05, (dd, pv)


def test_sortie_de_spirale_distingue_les_indulgences():
    """« Indulgent » recouvrait deux gestes : rendre, et reprendre."""
    res = tournoi(S.pool_classique(), graine=1, bruit=0.05)
    assert P.indulgence(res, "Donnant-donnant") > 0.9
    assert P.sortie_de_spirale(res, "Donnant-donnant") < 0.1
    assert P.sortie_de_spirale(res, "Pavlov") > 0.9


def test_toujours_cooperer_na_pas_de_riposte():
    res = tournoi(S.pool_classique(), graine=1, bruit=0.0)
    assert P.riposte(res, "Toujours coopérer") == 0.0
    assert P.riposte(res, "Donnant-donnant") == 1.0


def test_aleatoire_est_illisible():
    res = tournoi(S.pool_classique(), graine=1, bruit=0.0)
    assert P.lisibilite(res, "Aléatoire") < 0.6
    assert P.lisibilite(res, "Donnant-donnant") > 0.95


# --------------------------------------------------------------------------- #
# La coalition
# --------------------------------------------------------------------------- #
def test_la_coalition_se_reconnait():
    recolteur, sacrifie = S.Equipe(True), S.Equipe(False)
    sig = list(S.Equipe.SIGNATURE)
    assert recolteur.jouer(sig, sig, alea()) == S.TRAHIR, "il récolte"
    assert sacrifie.jouer(sig, sig, alea()) == S.COOP, "il se sacrifie"
    etranger = [S.COOP] * len(sig)
    assert recolteur.jouer(sig, etranger, alea()) == S.TRAHIR
    assert sacrifie.jouer(sig, etranger, alea()) == S.TRAHIR, "pas de cadeau"


def test_la_coalition_place_son_recolteur_premier():
    pool = S.pool_classique()
    r = S.Equipe(True)
    r.nom = "Coalition (récolteur)"
    pool.append(r)
    for n in range(8):
        s = S.Equipe(False)
        s.nom = f"Coalition (sacrifié {n + 1})"
        pool.append(s)
    res = tournoi(pool, graine=1, bruit=0.0)
    assert res.rang("Coalition (récolteur)") == 1
    assert res.rang("Donnant-donnant") > 5, "le plateau a changé sous ses pieds"


# --------------------------------------------------------------------------- #
# Les deux bruits, et le zéro qui n'en était pas un
# --------------------------------------------------------------------------- #
def test_un_echantillon_vide_ne_vaut_pas_zero():
    """Sans accident observable, la mesure doit dire « indéfini », pas 0%.

    La première version rendait 0,0, et un tournoi où aucun accident n'était
    détectable affichait donc « 0% d'accidents non réparés » pour Rancunier —
    une stratégie qui ne pardonne jamais. Un échantillon vide rendu comme une
    mesure est pire qu'une erreur : il a l'air d'un résultat.
    """
    res = tournoi(S.pool_classique(), graine=1, bruit=0.0)
    m = P.entre_soi(res, "Rancunier")
    assert m["echantillon"] == 0
    assert m["part_non_reparee"] is None
    assert m["delai_moyen"] is None


def test_le_bruit_de_perception_produit_des_accidents_detectables():
    """Sous bruit de perception, le coup joué EST le coup voulu.

    L'accident ne se voit donc que dans l'écart entre ce qui a été joué et ce
    qui a été lu — c'est pourquoi `Duel` garde `vus_a` et `vus_b`. Sans elles,
    la mesure était silencieusement vide.
    """
    res = tournoi(S.pool_classique(), graine=1, bruit=0.05, perception=True,
                  repetitions=30)
    d = res.duels[("Donnant-donnant", "Donnant-donnant")][0]
    assert d.voulus_a == d.joues_a, "aucun dérapage d'exécution en mode perception"
    assert any(d.accident(t) for t in range(len(d.joues_a)))
    assert P.entre_soi(res, "Donnant-donnant")["echantillon"] > 0


@pytest.mark.parametrize("nom,plancher,plafond", [
    ("Donnant-donnant", 0.55, 0.90),
    ("Pavlov", 0.0, 0.05),
    ("Rancunier", 0.95, 1.0),
])
def test_les_deux_bruits_donnent_le_meme_retablissement(nom, plancher, plafond):
    """L'écart attendu entre les deux régimes ne se produit pas.

    Les deux doivent tomber dans la même fourchette : c'est le résultat de
    l'expérience 5, et il contredit ce que ce dépôt affirmait avant de mesurer.
    """
    for perception in (False, True):
        res = tournoi(S.pool_classique(), graine=1, bruit=0.05,
                      repetitions=60, perception=perception)
        part = P.entre_soi(res, nom)["part_non_reparee"]
        assert part is not None
        assert plancher <= part <= plafond, (nom, perception, part)


def test_pavlov_paie_un_tour_de_plus_sous_malentendu():
    """La seule différence mesurable entre les deux bruits."""
    delais = {}
    for perception in (False, True):
        res = tournoi(S.pool_classique(), graine=1, bruit=0.05,
                      repetitions=60, perception=perception)
        delais[perception] = P.entre_soi(res, "Pavlov")["delai_moyen"]
    assert delais[True] > delais[False]
    assert delais[True] - delais[False] == pytest.approx(1.0, abs=0.3), delais


# --------------------------------------------------------------------------- #
# Le pardon : ce qui bouge n'est pas ce qu'on croyait
# --------------------------------------------------------------------------- #
import experiences as E


def _cout(bruit: float, graines: int = 6) -> float:
    """Écart, en %, entre le meilleur taux de pardon et ne jamais pardonner."""
    base, _ = E._gain(0.0, bruit, graines)
    top = max(E._gain(g, bruit, graines)[0] for g in (0.10, 0.20))
    return (top / base - 1) * 100


def test_ne_jamais_pardonner_coute_quand_le_bruit_est_faible():
    """Le résultat de l'expérience 6, dans sa forme la plus simple."""
    assert _cout(0.01) > 3.0


def test_le_cout_du_non_pardon_sannule_a_fort_bruit():
    """Au-delà de 20%, plus personne ne tient une coopération : il n'y a plus
    de relation à sauver, donc le pardon ne rapporte plus rien."""
    assert _cout(0.25) < 2.0


def test_le_cout_est_plus_fort_a_faible_bruit_qua_fort_bruit():
    """L'affirmation centrale, et elle est contre-intuitive : le pardon rapporte
    le plus quand les accidents sont RARES."""
    faible, fort = _cout(0.015), _cout(0.25)
    assert faible > fort + 2.0, (faible, fort)


def test_tout_pardonner_est_aussi_mauvais():
    """L'optimum est intérieur : sans exploiteurs dans le plateau, il serait
    trivialement 1, et l'expérience ne dirait rien."""
    partout = E._gain(1.0, 0.02, 6)[0]
    milieu = E._gain(0.20, 0.02, 6)[0]
    assert milieu > partout


def test_le_plateau_garde_ses_exploiteurs():
    noms = {s.nom for s in E._pool_avec_pardon(0.2)}
    assert "Toujours trahir" in noms and "Sondeur (Joss)" in noms
    assert "CANDIDAT" in noms
    assert sum(n.startswith("Donnant-donnant g") for n in noms) == 0


def test_deterministe_entre_processus():
    """Deux processus avec des sels de hachage différents doivent s'accorder.

    C'est le test qui aurait attrapé le bug : `matrice_gains` tirait sa graine
    de `hash((graine, "M", i, j, rep))`, et le hachage des chaînes est salé au
    démarrage de chaque processus. Un test dans un seul processus ne peut pas
    le voir — il faut en lancer deux.
    """
    import os
    import subprocess
    import sys

    code = (
        "import strategies as S;"
        "from tournoi import matrice_gains;"
        "n, A = matrice_gains([S.extorsion_zd(), S.donnant_donnant()],"
        " graine=3, tours=120, repetitions=4);"
        "print(round(A[0][1], 9), round(A[1][0], 9))"
    )
    sorties = set()
    for sel in ("0", "1", "12345"):
        env = {**os.environ, "PYTHONHASHSEED": sel}
        r = subprocess.run([sys.executable, "-c", code], capture_output=True,
                           text=True, cwd=os.path.dirname(__file__) or ".",
                           env=env, timeout=120)
        assert r.returncode == 0, r.stderr
        sorties.add(r.stdout.strip())
    assert len(sorties) == 1, f"résultats divergents selon le sel : {sorties}"


def test_le_readme_ne_derive_pas_du_code():
    """Les affirmations rapides du README, revérifiées à chaque exécution.

    Le dépôt a cité deux fois des chiffres que le code ne produisait plus, la
    seconde au moment de publier. Pour un dépôt dont l'argument est « ne me
    croyez pas, relancez », c'est la pire erreur possible : un lecteur qui
    relance et trouve autre chose ne peut pas savoir si le texte a dérivé ou si
    la mesure est instable.

    Ce test couvre ce qui se calcule en quelques secondes ; `verifier_readme.py`
    couvre tout, y compris l'expérience 6, qui demande plusieurs minutes.
    """
    import pathlib
    import verifier_readme as V

    readme = V.normaliser(
        (pathlib.Path(__file__).parent / "README.md").read_text(encoding="utf-8"))

    res = tournoi(S.pool_classique(), graine=1, bruit=0.0)
    profs = P.profils(res, [s.nom for s in S.pool_classique()])
    gentilles = [p.nom for p in profs if p.gentillesse > 0.99]
    autres = [p.nom for p in profs if p.gentillesse <= 0.99]
    pire = min(res.moyennes[n] for n in gentilles)
    meilleure = max(res.moyennes[n] for n in autres)
    assert V.normaliser(f"La dernière des gentilles marque {V.fr(pire)} par tour") \
        in readme
    assert V.normaliser(f"première des autres {V.fr(meilleure)}") in readme

    # Le délai du tableau vient du DERNIER niveau de bruit balayé par
    # l'expérience 2, pas d'un niveau choisi ici : un contrôle qui mesure
    # autrement que le texte ne contrôle rien.
    bruite = tournoi(S.pool_classique(), graine=1, bruit=E.BRUITS[-1],
                     repetitions=60)
    pavlov = P.entre_soi(bruite, "Pavlov")["delai_moyen"]
    assert V.normaliser(f"| Pavlov | **0 %** | {V.fr(pavlov, 2)} tour") in readme
