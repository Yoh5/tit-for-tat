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

Code de sortie 1 si un chiffre du README ne correspond plus. Les tests couvrent
les affirmations rapides ; celui-ci couvre **tous** les chiffres, y compris ceux
qui demandent plusieurs minutes de calcul.
"""
from __future__ import annotations

import json
import sys
import unicodedata
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple

RACINE = Path(__file__).resolve().parent


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


def controles(d: Dict[str, Any]) -> List[Tuple[str, str]]:
    """(ce qu'on vérifie, la chaîne qui doit figurer dans le README)."""
    e1, e2, e3 = d["experience_1"], d["experience_2"], d["experience_3"]
    e4, e6 = d["experience_4"], d["experience_6"]
    c: List[Tuple[str, str]] = []

    c.append(("E1 — séparation des gentilles",
              f"La dernière des gentilles marque {fr(e1['pire_gentille'])} par tour"))
    c.append(("E1 — meilleure non gentille",
              f"première des autres {fr(e1['meilleure_non_gentille'])}"))

    clones = e2["entre_clones"]
    dd = [p for p in clones["Donnant-donnant"]["parts_non_reparees"] if p is not None]
    c.append(("E2 — donnant-donnant ne se relève pas",
              f"**{min(dd) * 100:.0f} à {max(dd) * 100:.0f} %**"))
    c.append(("E2 — délai de Pavlov",
              f"| Pavlov | **0 %** | {fr(clones['Pavlov']['delai_moyen'], 2)} tour"))

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
    return c


def main() -> int:
    chemin = RACINE / "resultats.json"
    if not chemin.exists():
        print("resultats.json absent — lancer d'abord :")
        print("    python experiences.py --json resultats.json")
        return 2

    d = json.loads(chemin.read_text(encoding="utf-8"))
    texte = normaliser((RACINE / "README.md").read_text(encoding="utf-8"))

    echecs = 0
    for quoi, attendu in controles(d):
        if normaliser(attendu) in texte:
            print(f"  ok   {quoi}")
        else:
            echecs += 1
            print(f"  ECHEC {quoi}")
            print(f"        le README devrait contenir : {attendu}")

    print()
    if echecs:
        print(f"{echecs} chiffre(s) du README ne correspondent plus au code.")
        print("Corriger le texte — ou dire pourquoi la mesure a changé.")
        return 1
    print("Tous les chiffres du README correspondent au code.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
