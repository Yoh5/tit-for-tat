"""Les deux images du post, calculées depuis le code et non dessinées à la main.

**Pourquoi les calculer.** Une figure faite à la main illustre ce qu'on croit
avoir trouvé ; une figure calculée illustre ce qu'on a trouvé. Les séquences de
coups de la première image sortent d'un vrai duel, l'accident est un vrai
accident, et les chiffres de la seconde sortent d'un vrai tournoi. Si une mesure
change, les images changent avec elle.

**Daltonisme.** Vert contre rouge mesure environ 4 unités de différence
perceptuelle en deutéranopie : illisible. La coopération et la trahison se
distinguent donc par la **forme** — un disque plein contre une croix — et la
couleur ne fait que renforcer. De même, dans le graphique à barres, l'échec
porte un liseré et une valeur chiffrée, pas seulement une teinte.

Usage :
    python figures.py              # les deux, dans figures/
"""
from __future__ import annotations

import os
import random
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

from PIL import Image, ImageDraw, ImageFont

import proprietes as P
import strategies as S
from tournoi import tournoi

SORTIE = Path(__file__).resolve().parent / "figures"

SURFACE = (26, 26, 25)
ENCRE = (255, 255, 255)
ENCRE_2 = (195, 194, 183)
ENCRE_3 = (138, 137, 128)
ACCENT = (57, 135, 229)
CRITIQUE = (208, 59, 59)
SUCCES = (122, 184, 122)

_POLICES = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"


def f(nom: str, taille: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(str(_POLICES / nom), taille)
    except Exception:
        return ImageFont.load_default()


def GRAS(t: int):
    return f("arialbd.ttf", t)


def NORMAL(t: int):
    return f("arial.ttf", t)


def MONO(t: int):
    return f("consolab.ttf", t)


def ecrire(d: ImageDraw.ImageDraw, xy, texte: str, police, couleur,
           centre: bool = False, droite: bool = False) -> None:
    x, y = xy
    if centre or droite:
        g, h, dr, b = d.textbbox((0, 0), texte, font=police)
        x -= (dr - g) / 2 if centre else (dr - g)
        if centre:
            y -= (b - h) / 2
    d.text((x, y), texte, font=police, fill=couleur)


# --------------------------------------------------------------------------- #
# Les séquences, jouées pour de vrai
# --------------------------------------------------------------------------- #
def sequence(fabrique, tours: int = 13) -> Tuple[List[int], List[int], Optional[int]]:
    """Deux clones, un accident forcé au tour 1. Rend (coups A, coups B, tour du
    retour à la coopération mutuelle).

    L'accident est forcé plutôt que tiré, pour que la figure soit reproductible
    et qu'il y en ait exactement un — c'est le propre d'une illustration de
    mécanisme.
    """
    a, b = fabrique(), fabrique()
    a.nouvelle_partie()
    b.nouvelle_partie()
    alea = random.Random(0)
    ha: List[int] = []
    hb: List[int] = []
    retour = None
    for t in range(tours):
        ca = a.jouer(ha, hb, alea)
        cb = b.jouer(hb, ha, alea)
        if t == 1:
            ca = S.TRAHIR  # l'accident
        ha.append(ca)
        hb.append(cb)
        if t > 1 and retour is None and ca == S.COOP and cb == S.COOP:
            retour = t
    return ha, hb, retour


def _bande(d: ImageDraw.ImageDraw, x: int, y: int, coups: Sequence[int],
           pas: int, rayon: int, accident: int, retour: Optional[int]) -> None:
    """Une ligne de coups. Disque plein = coopère, croix = trahit."""
    for t, c in enumerate(coups):
        cx = x + t * pas
        apres = retour is not None and t >= retour
        if c == S.COOP:
            teinte = SUCCES if apres else ACCENT
            d.ellipse([cx - rayon, y - rayon, cx + rayon, y + rayon],
                      fill=teinte, outline=None)
        else:
            d.line([(cx - rayon, y - rayon), (cx + rayon, y + rayon)],
                   fill=CRITIQUE, width=4)
            d.line([(cx - rayon, y + rayon), (cx + rayon, y - rayon)],
                   fill=CRITIQUE, width=4)
        if t == accident:
            d.ellipse([cx - rayon - 7, y - rayon - 7, cx + rayon + 7, y + rayon + 7],
                      outline=ENCRE, width=3)


def _panneau(d: ImageDraw.ImageDraw, x: int, y: int, larg: int, titre: str,
             sous: str, ha: Sequence[int], hb: Sequence[int],
             retour: Optional[int], verdict: str, teinte_verdict) -> None:
    pas = int((larg - 150) / (len(ha) - 1))
    rayon = 13
    ecrire(d, (x, y), titre, GRAS(40), ENCRE)
    ecrire(d, (x, y + 50), sous, NORMAL(26), ENCRE_2)

    base = y + 150   # de l'air sous le sous-titre : l'étiquette de retour s'y loge
    ecrire(d, (x, base - 11), "A", MONO(26), ENCRE_3)
    ecrire(d, (x, base + 59), "B", MONO(26), ENCRE_3)
    gx = x + 48
    _bande(d, gx, base, ha, pas, rayon, 1, retour)
    _bande(d, gx, base + 70, hb, pas, rayon, None, retour)

    # Le tour du retour, matérialisé par un trait vertical : la géométrie dit
    # ce que la couleur seule ne dirait pas à un lecteur daltonien.
    if retour is not None:
        rx = gx + retour * pas
        d.line([(rx, base - 40), (rx, base + 112)], fill=SUCCES, width=3)
        ecrire(d, (rx, base - 58), f"retour au tour {retour}", NORMAL(22),
               SUCCES, centre=True)
    else:
        # Un trait sans légende se lit comme une scorie : on le nomme.
        rx = gx + (len(ha) - 1) * pas + 36
        d.line([(rx, base - 40), (rx, base + 112)], fill=CRITIQUE, width=3)
        ecrire(d, (rx, base - 58), "aucun retour", NORMAL(22), CRITIQUE,
               centre=True)

    ecrire(d, (x, base + 148), verdict, GRAS(28), teinte_verdict)


def figure_echo() -> Path:
    """L'écho : le mécanisme, en une image.

    C'est la figure qui porte le post, parce qu'elle montre la chose au lieu de
    l'affirmer : le même accident, deux stratégies, et l'une ne revient jamais.
    """
    L, H = 1600, 1060
    img = Image.new("RGB", (L, H), SURFACE)
    d = ImageDraw.Draw(img)

    ecrire(d, (70, 56), "Un seul accident", GRAS(62), ENCRE)
    ecrire(d, (70, 132),
           "Deux copies de la même stratégie. Au tour 1, le coup de A dérape — "
           "personne n'a triché.", NORMAL(28), ENCRE_2)

    dd_a, dd_b, dd_r = sequence(S.donnant_donnant)
    pv_a, pv_b, pv_r = sequence(S.pavlov)

    _panneau(d, 70, 230, L - 140, "Donnant-donnant",
             "riposte au premier accident, et n'en sort que si l'autre en sort",
             dd_a, dd_b, dd_r,
             "Les deux alternent en décalé. Ils ne retombent jamais en phase.",
             CRITIQUE)
    _panneau(d, 70, 630, L - 140, "Pavlov",
             "change de coup quand un tour a mal payé",
             pv_a, pv_b, pv_r,
             "Elle quitte la spirale seule, sans attendre un geste de l'autre.",
             SUCCES)

    # Légende : la forme avant la couleur.
    lx, ly = 70, H - 62
    d.ellipse([lx, ly - 10, lx + 20, ly + 10], fill=ACCENT)
    ecrire(d, (lx + 32, ly - 13), "coopère", NORMAL(24), ENCRE_3)
    lx += 160
    d.line([(lx, ly - 10), (lx + 20, ly + 10)], fill=CRITIQUE, width=4)
    d.line([(lx, ly + 10), (lx + 20, ly - 10)], fill=CRITIQUE, width=4)
    ecrire(d, (lx + 32, ly - 13), "trahit", NORMAL(24), ENCRE_3)
    lx += 150
    d.ellipse([lx - 7, ly - 17, lx + 27, ly + 17], outline=ENCRE, width=3)
    ecrire(d, (lx + 42, ly - 13), "l'accident", NORMAL(24), ENCRE_3)
    ecrire(d, (L - 70, ly - 13), "github.com/Yoh5/tit-for-tat", MONO(22),
           ENCRE_3, droite=True)

    SORTIE.mkdir(parents=True, exist_ok=True)
    chemin = SORTIE / "echo.png"
    img.save(chemin, optimize=True)
    return chemin


def figure_barres() -> Path:
    """Le chiffre, pour ceux qui veulent le chiffre.

    Les mesures viennent d'un tournoi joué à l'instant : l'image ne peut pas
    dériver du code.
    """
    res = tournoi(S.pool_classique(), graine=1, bruit=0.05, repetitions=60)
    lignes = []
    for s in S.pool_classique():
        m = P.entre_soi(res, s.nom)
        if m["part_non_reparee"] is not None:
            lignes.append((s.nom, float(m["part_non_reparee"]), m["delai_moyen"]))
    lignes.sort(key=lambda r: r[1])

    L = 1600
    H = 300 + len(lignes) * 72
    img = Image.new("RGB", (L, H), SURFACE)
    d = ImageDraw.Draw(img)

    ecrire(d, (70, 52), "Se relever de son propre accident", GRAS(58), ENCRE)
    ecrire(d, (70, 126),
           "Part des accidents après lesquels une paire de clones ne retrouve "
           "pas la coopération.", NORMAL(28), ENCRE_2)
    ecrire(d, (70, 164),
           "Bruit d'exécution 5 %, fenêtre de 10 tours sans nouvel accident. "
           "Le chiffre ne bouge pas de 1 % à 10 %.", NORMAL(24), ENCRE_3)

    x0, larg = 480, L - 480 - 230
    y = 248
    for nom, part, delai in lignes:
        teinte = CRITIQUE if part > 0.5 else (SUCCES if part < 0.05 else ACCENT)
        ecrire(d, (x0 - 24, y + 16), nom, NORMAL(27), ENCRE_2, droite=True)
        d.rounded_rectangle([x0, y, x0 + larg, y + 34], radius=6,
                            fill=(38, 38, 36))
        if part > 0:
            d.rounded_rectangle([x0, y, x0 + max(8, int(larg * part)), y + 34],
                                radius=6, fill=teinte)
        # La valeur est écrite : un lecteur qui ne distingue pas les teintes lit
        # le nombre, et le nombre suffit.
        ecrire(d, (x0 + larg + 20, y + 16), f"{part:.0%}", MONO(30), teinte)
        detail = "jamais" if delai is None else f"{delai:.1f} tours"
        ecrire(d, (x0 + larg + 118, y + 18), detail, NORMAL(22), ENCRE_3)
        y += 72

    ecrire(d, (70, H - 58), "github.com/Yoh5/tit-for-tat", MONO(22), ENCRE_3)
    ecrire(d, (L - 70, H - 58), "délai quand elle se relève", NORMAL(22),
           ENCRE_3, droite=True)

    SORTIE.mkdir(parents=True, exist_ok=True)
    chemin = SORTIE / "retablissement.png"
    img.save(chemin, optimize=True)
    return chemin


def main() -> int:
    for chemin in (figure_echo(), figure_barres()):
        ko = chemin.stat().st_size / 1024
        print(f"ecrit : figures/{chemin.name}  ({ko:.0f} Ko)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
