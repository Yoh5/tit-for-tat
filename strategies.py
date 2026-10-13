"""Les stratégies du dilemme du prisonnier itéré.

On garde celles qui servent l'argument, pas un catalogue. Chacune est là parce
qu'elle **contredit** quelque chose : Donnant-Donnant gagne sans bruit et
s'effondre avec, Pavlov se relève de ses propres erreurs, l'extorsion montre
qu'un joueur à mémoire plus longue peut imposer son taux de change.

Convention : `COOP = 1`, `TRAHIR = 0`. Un entier plutôt qu'un booléen, parce
qu'il sert d'indice dans la matrice de gains.

Matrice standard d'Axelrod (celle de la vidéo) : coopération mutuelle 3,
trahison mutuelle 1, tentation 5, dupe 0. L'ordre T > R > P > S et la condition
2R > T + S en font bien un dilemme du prisonnier.
"""
from __future__ import annotations

import random
from typing import Dict, List, Sequence, Tuple

COOP = 1
TRAHIR = 0

R, S, T, P = 3, 0, 5, 1

#: (mon coup, son coup) -> (mon gain, son gain)
GAINS: Dict[Tuple[int, int], Tuple[int, int]] = {
    (COOP, COOP): (R, R),
    (COOP, TRAHIR): (S, T),
    (TRAHIR, COOP): (T, S),
    (TRAHIR, TRAHIR): (P, P),
}

assert T > R > P > S and 2 * R > T + S, "ce n'est pas un dilemme du prisonnier"


class Strategie:
    """Une stratégie décide son coup à partir des deux historiques observés.

    `moi` et `lui` sont les coups **exécutés** tels qu'ils ont été observés —
    pas les coups voulus. Sous bruit d'exécution, la différence est tout le
    sujet : une stratégie qui raisonne sur ses intentions ne voit jamais son
    propre dérapage et ne peut donc pas le réparer.
    """

    nom = "sans nom"

    def nouvelle_partie(self) -> None:
        """Appelé avant chaque duel. Une stratégie ne garde rien entre duels."""

    def jouer(self, moi: Sequence[int], lui: Sequence[int],
              alea: random.Random) -> int:
        raise NotImplementedError


class MemoireUn(Strategie):
    """Stratégie à mémoire d'un coup : quatre probabilités de coopérer.

    `p[(mon dernier, son dernier)]`. C'est la famille dans laquelle vivent
    Donnant-Donnant, Pavlov et les stratégies à déterminant nul — ce qui permet
    de les comparer sans changer de cadre.
    """

    def __init__(self, nom: str, p: Dict[Tuple[int, int], float],
                 premier: int = COOP) -> None:
        self.nom = nom
        self.p = p
        self.premier = premier

    def jouer(self, moi, lui, alea):
        if not lui:
            return self.premier
        prob = self.p[(moi[-1], lui[-1])]
        if prob >= 1.0:
            return COOP
        if prob <= 0.0:
            return TRAHIR
        return COOP if alea.random() < prob else TRAHIR


class ToujoursCooperer(Strategie):
    nom = "Toujours coopérer"

    def jouer(self, moi, lui, alea):
        return COOP


class ToujoursTrahir(Strategie):
    nom = "Toujours trahir"

    def jouer(self, moi, lui, alea):
        return TRAHIR


class Aleatoire(Strategie):
    nom = "Aléatoire"

    def jouer(self, moi, lui, alea):
        return COOP if alea.random() < 0.5 else TRAHIR


class Rancunier(Strategie):
    """Grim Trigger : coopère jusqu'à la première trahison, puis jamais plus.

    Présente parce qu'elle est le contre-exemple du pardon : sous le moindre
    bruit, elle condamne une relation entière sur un accident.
    """

    nom = "Rancunier"

    def jouer(self, moi, lui, alea):
        return TRAHIR if TRAHIR in lui else COOP


class DonnantDonnantDeuxFois(Strategie):
    """Tit for Two Tats : ne riposte qu'après deux trahisons de suite.

    Elle encaisse une erreur isolée sans représailles — la forme la plus simple
    de tolérance au bruit, et elle était déjà dans le tournoi de 1980.
    """

    nom = "Donnant-donnant x2"

    def jouer(self, moi, lui, alea):
        return TRAHIR if len(lui) >= 2 and lui[-1] == lui[-2] == TRAHIR else COOP


class Sondeur(Strategie):
    """Joss : donnant-donnant qui trahit 10% du temps sans raison.

    Dans le tournoi d'Axelrod, c'est elle qui a montré le danger : sa trahison
    gratuite déclenche, contre un donnant-donnant, une vengeance mutuelle dont
    aucune des deux ne sort. Le bruit d'exécution produit exactement le même
    accident, sans qu'aucune des deux stratégies ne l'ait cherché.
    """

    nom = "Sondeur (Joss)"

    def jouer(self, moi, lui, alea):
        if not lui:
            return COOP
        if lui[-1] == TRAHIR:
            return TRAHIR
        return TRAHIR if alea.random() < 0.10 else COOP


class Equipe(Strategie):
    """Un membre d'une coalition qui se reconnaît par mot de passe.

    Le schéma de l'équipe de Southampton, qui a gagné le tournoi du 20e
    anniversaire en 2004 en inscrivant une soixantaine d'agents : les premiers
    coups servent de signature ; si l'adversaire la donne aussi, les coéquipiers
    se répartissent les rôles — l'un se sacrifie, l'autre encaisse. Sinon, ils
    trahissent sans condition.

    Elle n'est pas là pour gagner le débat sur la meilleure stratégie : elle est
    là pour montrer que la question est **mal posée** dès qu'on peut inscrire
    plusieurs agents.
    """

    SIGNATURE = (COOP, TRAHIR, COOP, TRAHIR, TRAHIR)

    def __init__(self, recolte: bool) -> None:
        self.recolte = recolte
        self.nom = "Coalition (récolteur)" if recolte else "Coalition (sacrifié)"

    def jouer(self, moi, lui, alea):
        tour = len(lui)
        if tour < len(self.SIGNATURE):
            return self.SIGNATURE[tour]
        coequipier = tuple(lui[:len(self.SIGNATURE)]) == self.SIGNATURE
        if not coequipier:
            return TRAHIR
        return TRAHIR if self.recolte else COOP


# --------------------------------------------------------------------------- #
# Les stratégies à mémoire d'un coup
# --------------------------------------------------------------------------- #
def donnant_donnant() -> MemoireUn:
    """Tit for Tat (Rapoport, 1980) : copie le dernier coup de l'autre."""
    return MemoireUn("Donnant-donnant", {
        (COOP, COOP): 1.0, (COOP, TRAHIR): 0.0,
        (TRAHIR, COOP): 1.0, (TRAHIR, TRAHIR): 0.0})


#: Probabilité de pardon de Generous Tit for Tat. Nowak et Sigmund la donnent
#: comme min(1 - (T-R)/(R-S), (R-P)/(T-P)) ; avec 3/0/5/1 cela vaut 1/3.
PARDON = min(1 - (T - R) / (R - S), (R - P) / (T - P))


def donnant_donnant_genereux(pardon: float = PARDON) -> MemoireUn:
    """Generous Tit for Tat : comme donnant-donnant, mais pardonne parfois.

    C'est la stratégie qui bat donnant-donnant sous bruit (Nowak et Sigmund,
    1992). Le pardon n'est pas de la gentillesse : c'est ce qui coupe la boucle
    de représailles qu'un accident déclenche.
    """
    return MemoireUn(f"Donnant-donnant généreux ({pardon:.2f})", {
        (COOP, COOP): 1.0, (COOP, TRAHIR): pardon,
        (TRAHIR, COOP): 1.0, (TRAHIR, TRAHIR): pardon})


def pavlov() -> MemoireUn:
    """Win-Stay, Lose-Shift (Nowak et Sigmund, 1993).

    Garde son coup si le tour a bien payé (R ou T), le change sinon (P ou S).
    Elle se relève donc de **ses propres** erreurs sans avoir besoin que
    l'adversaire pardonne — la propriété que donnant-donnant n'a pas.
    """
    return MemoireUn("Pavlov", {
        (COOP, COOP): 1.0,     # R : on reste
        (COOP, TRAHIR): 0.0,   # S : on change
        (TRAHIR, COOP): 0.0,   # T : on reste... en trahissant
        (TRAHIR, TRAHIR): 1.0})  # P : on change


def extorsion_zd() -> MemoireUn:
    """Extort-2, une stratégie à déterminant nul (Press et Dyson, 2012).

    Press et Dyson ont montré qu'un joueur à mémoire plus longue peut imposer
    un rapport fixe entre son gain et celui de l'autre : l'adversaire qui
    cherche à maximiser son score finit par servir le gain de l'extorqueur.

    Les quatre probabilités sont celles d'Extort-2 (facteur d'extorsion 2). On
    ne demande pas au lecteur de faire confiance à la dérivation : le test
    `test_extorsion_extorque` **mesure** la propriété au lieu de l'affirmer.
    """
    return MemoireUn("Extorsion (ZD, x2)", {
        (COOP, COOP): 8 / 9, (COOP, TRAHIR): 1 / 2,
        (TRAHIR, COOP): 1 / 3, (TRAHIR, TRAHIR): 0.0})


def genereuse_zd() -> MemoireUn:
    """ZDGTFT-2, la variante *généreuse* des stratégies à déterminant nul.

    Stewart et Plotkin (2013) : dans une population qui évolue, l'extorsion
    s'effondre et c'est la version généreuse qui s'impose. L'extorsion gagne le
    duel et perd le monde.
    """
    return MemoireUn("Généreuse (ZD)", {
        (COOP, COOP): 1.0, (COOP, TRAHIR): 1 / 8,
        (TRAHIR, COOP): 1.0, (TRAHIR, TRAHIR): 1 / 4})


def pool_classique() -> List[Strategie]:
    """Le plateau de base : de quoi rejouer l'argument de 1980.

    Ce n'est **pas** une réplication du tournoi d'Axelrod — il comptait quinze
    entrées précises que nous n'avons pas. C'est le même mécanisme avec un
    plateau choisi pour que la comparaison soit lisible.
    """
    return [
        donnant_donnant(),
        DonnantDonnantDeuxFois(),
        Rancunier(),
        ToujoursCooperer(),
        ToujoursTrahir(),
        Aleatoire(),
        Sondeur(),
        pavlov(),
        donnant_donnant_genereux(),
    ]


def pool_moderne() -> List[Strategie]:
    """Le plateau de 1980 plus ce que la littérature a ajouté depuis."""
    return pool_classique() + [extorsion_zd(), genereuse_zd()]
