"""Le README dit-il encore ce que le code calcule ?

## Pourquoi cet outil existe

Deux fois dans l'histoire de ce dépôt, le README a cité des chiffres que le code
ne produisait plus. La seconde fois, c'était au moment de publier : la correction
du déterminisme avait changé tous les tirages, et le texte annonçait encore
« 2,506 contre 2,248 » là où le code rendait « 2,420 contre 2,329 ».

Les conclusions tenaient, les nombres non. C'est la pire espèce d'erreur pour un
dépôt dont l'argument est *« ne me croyez pas, relancez »* : un lecteur qui
relance et trouve autre chose n'a aucun moyen de savoir si le texte a dérivé ou
si la mesure est instable.

Un dépôt qui invite à le vérifier doit se vérifier lui-même.

## Usage

    python experiences.py --json resultats.json   # d'abord, produire les chiffres
    python verifier_readme.py                     # ensuite, les confronter au texte
    python verifier_readme.py --aussi ../linkedin/POSTS.md   # et les textes publiés

Code de sortie 1 si un chiffre du README ne correspond plus. Les tests couvrent
les affirmations rapides ; celui-ci couvre **tous** les chiffres, y compris ceux
qui demandent plusieurs minutes de calcul.

## Pourquoi `--aussi`

Troisième dérive, et cette fois hors du dépôt : un brouillon de post annonçait
« il arrive sixième » et « 44 tests » bien après que la correction du
déterminisme ait fait passer donnant-donnant quatrième et la suite à 48 tests.
Le README, lui, était juste — c'est le texte destiné au public qui avait vieilli.

Un garde-fou qui ne protège que le fichier le plus relu protège le moins exposé.
`--aussi` prend un fichier quelconque et n'y vérifie que les chiffres énoncés en
prose, ceux qu'on recopie à la main et qu'on oublie de rejouer.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

RACINE = Path(__file__).resolve().parent

ORDINAUX = {1: "premier", 2: "deuxième", 3: "troisième", 4: "quatrième",
            5: "cinquième", 6: "sixième", 7: "septième", 8: "huitième",
            9: "neuvième", 10: "dixième"}


def fr(x: float, decimales: int = 3) -> str:
    """Un nombre à la française : la virgule décimale, comme dans le texte."""
    return f"{x:.{decimales}f}".replace(".", ",")


def normaliser(s: str) -> str:
    """Rend comparables les espaces et tirets que le markdown laisse traîner.

    Les espaces insécables et les demi-cadratins se glissent dans un texte rédigé
    à la main, et un contrôle qui les confond avec leurs équivalents ASCII
    signale des écarts qui n'en sont pas.
    """
    s = unicodedata.normalize("NFKC", s)
    for a, b in ((" ", " "), (" ", " "), ("−", "-"), ("–", "-")):
        s = s.replace(a, b)
    return " ".join(s.split())


def nombre_de_tests() -> Optional[int]:
    """Combien de tests pytest collecte réellement.

    Compter les ``def test_`` donnerait 41 : trois d'entre eux sont
    paramétrés, et c'est justement l'écart qui a laissé passer « 44 tests »
    dans un brouillon. Seul pytest sait combien de cas existent.

    Rend ``None`` si pytest est absent : un outil de cohérence n'a pas à
    transformer une dépendance manquante en échec de vérification.
    """
    try:
        r = subprocess.run(
            [sys.executable, "-m", "pytest", "--collect-only", "-q",
             str(RACINE / "test_tournoi.py")],
            capture_output=True, text=True, cwd=RACINE, timeout=120)
    except (OSError, subprocess.TimeoutExpired):
        return None
    m = re.search(r"(\d+) tests? collected", r.stdout)
    return int(m.group(1)) if m else None


def controles(d: Dict[str, Any]) -> List[Tuple[str, str]]:
    """(ce qu'on vérifie, la chaîne qui doit figurer dans le README)."""
    e1, e2, e3 = d["experience_1"], d["experience_2"], d["experience_3"]
    e4, e6 = d["experience_4"], d["experience_6"]
    e7 = d.get("experience_7")
    c: List[Tuple[str, str]] = []

    c.append(("E1 — séparation des gentilles",
              f"La dernière des gentilles marque {fr(e1['pire_gentille'])} par tour"))
    c.append(("E1 — meilleure non gentille",
              f"première des autres {fr(e1['meilleure_non_gentille'])}"))
    c.append(("E1 — rang de donnant-donnant, en prose",
              f"Donnant-donnant {ORDINAUX[e1['rang_donnant_donnant']]}"))

    clones = e2["entre_clones"]
    dd = [p for p in clones["Donnant-donnant"]["parts_non_reparees"] if p is not None]
    c.append(("E2 — donnant-donnant ne se relève pas",
              f"**{min(dd) * 100:.0f} à {max(dd) * 100:.0f} %**"))
    c.append(("E2 — délai de Pavlov",
              f"| Pavlov | **0 %** | {fr(clones['Pavlov']['delai_moyen'], 2)} tour"))
    # La légende d'une figure est du texte comme un autre, et elle avait
    # dérivé plus longtemps que le tableau : personne ne relit un alt.
    c.append(("E2 — légende de retablissement.png",
              f"{min(dd) * 100:.0f} à {max(dd) * 100:.0f} % pour Donnant-donnant"))

    c.append(("E3 — extorsion contre donnant-donnant",
              f"**{fr(e3['extorsion_vs_donnant_donnant'][0])} contre "
              f"{fr(e3['extorsion_vs_donnant_donnant'][1])}**"))
    c.append(("E3 — extorsion contre un naïf",
              f"**{fr(e3['extorsion_vs_cooperateur'][0])} contre "
              f"{fr(e3['extorsion_vs_cooperateur'][1])}**"))

    c.append(("E4 — gain du récolteur",
              f"| Coalition (récolteur) | **{fr(e4['gain_recolteur'])}** | **1** |"))
    c.append(("E4 — gain des sacrifiés",
              f"| Coalition (sacrifiés, moyenne) | {fr(e4['gain_moyen_sacrifies'])} |"))
    c.append(("E4 — rang de donnant-donnant",
              f"| Donnant-donnant | — | **{e4['rang_donnant_donnant']}** |"))

    # Le sommet est mis en gras comme **bande**, et non comme point unique :
    # plusieurs niveaux de bruit y sont indistinguables compte tenu des barres
    # d'erreur, et la figure le dit déjà ainsi. Un texte qui désignerait un
    # maximum unique contredirait son illustration.
    courbe = e6["courbe_cout"]
    sommet = max(courbe, key=lambda r: r["ecart_pct"])
    seuil = sommet["ecart_pct"] - 2 * sommet["erreur_pct"]
    ligne = " | ".join(
        (f"**{fr(p['ecart_pct'], 1)} %**" if p["ecart_pct"] >= seuil
         else f"{fr(p['ecart_pct'], 1)} %")
        for p in courbe)
    c.append(("E6 — la courbe du coût", f"| ce qu'on perd | {ligne} |"))

    if e7:
        # Les deux bouts de l'échelle du pardon : le seul cas où l'irréprochable
        # finit devant, et celui où il est le plus dépassé. Si l'un des deux
        # bouge, c'est tout le résultat qui a bougé.
        for cle, gabarit in (
            (e7["lignes"][0], "| {s} | {a} | {b} | **{e}** |"),
            (e7["lignes"][-1], "| {s} | {a} | {b} | **{e}** |"),
        ):
            signe = "+" if cle["ecart"] > 0 else "−"
            c.append((f"E7 — {cle['strategie']}", gabarit.format(
                s=cle["strategie"], a=fr(cle["gain_irreprochable"]),
                b=fr(cle["gain_fautif"]),
                e=signe + fr(abs(cle["ecart"])))))
    return c


def controles_en_prose(d: Dict[str, Any], tests: Optional[int]
                       ) -> List[Tuple[str, str]]:
    """Les chiffres qu'un texte destiné au public énonce en français.

    Volontairement court. Ce n'est pas un correcteur de prose : ce sont les
    quelques nombres qu'on recopie à la main d'un brouillon à l'autre et qu'on
    ne rejoue jamais. Les trois qui avaient vieilli sont ici.
    """
    c: List[Tuple[str, str]] = []
    c.append(("rang de donnant-donnant",
              ORDINAUX[d["experience_1"]["rang_donnant_donnant"]]))
    if tests is not None:
        c.append(("nombre de tests", f"{tests} tests"))
    e6 = max(d["experience_6"]["courbe_cout"], key=lambda r: r["ecart_pct"])
    c.append(("coût du refus de pardonner", f"{fr(e6['ecart_pct'], 1)} %"))
    e7 = d.get("experience_7")
    if e7:
        # Les deux bornes que les posts citent : donnant-donnant, et la plus
        # indulgente. Pas la première ligne du tableau — c'est Rancunier, dont
        # l'écart est négatif, et un contrôle qui prendrait sa valeur absolue
        # chercherait dans le texte un transfert qui n'existe pas.
        par_nom = {l["strategie"]: l for l in e7["lignes"]}
        bornes = [("donnant-donnant", par_nom.get("Donnant-donnant")),
                  ("la plus indulgente", e7["lignes"][-1])]
        for bout, cle in bornes:
            if cle is None or cle["ecart"] <= 0:
                continue
            c.append((f"écart du transfert, {bout}",
                      "+" + fr(cle["ecart"], 2)))
    return c


def verifier(titre: str, texte: str, attendus: List[Tuple[str, str]]) -> int:
    """Rend le nombre d'échecs, et dit lesquels."""
    print(titre)
    echecs = 0
    for quoi, attendu in attendus:
        if normaliser(attendu) in texte:
            print(f"  ok   {quoi}")
        else:
            echecs += 1
            print(f"  ECHEC {quoi}")
            print(f"        devrait contenir : {attendu}")
    return echecs


def main(argv: List[str]) -> int:
    chemin = RACINE / "resultats.json"
    if not chemin.exists():
        print("resultats.json absent — lancer d'abord :")
        print("    python experiences.py --json resultats.json")
        return 2

    autres = [Path(a) for a in argv[argv.index("--aussi") + 1:]]         if "--aussi" in argv else []
    manquants = [a for a in autres if not a.exists()]
    if manquants:
        for a in manquants:
            print(f"introuvable : {a}")
        return 2

    d = json.loads(chemin.read_text(encoding="utf-8"))
    echecs = verifier("README.md",
                      normaliser((RACINE / "README.md").read_text(encoding="utf-8")),
                      controles(d))

    if autres:
        tests = nombre_de_tests()
        if tests is None:
            print()
            print("(pytest introuvable : le nombre de tests n'est pas verifie)")
        prose = controles_en_prose(d, tests)
        for a in autres:
            print()
            echecs += verifier(a.name,
                               normaliser(a.read_text(encoding="utf-8")), prose)

    print()
    if echecs:
        print(f"{echecs} chiffre(s) ne correspondent plus au code.")
        print("Corriger le texte — ou dire pourquoi la mesure a changé.")
        return 1
    print("Tous les chiffres correspondent au code.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
