"""Les quatre propriétés d'Axelrod, mesurées sur les parties jouées.

Axelrod, en relisant son tournoi, a dit que les stratégies gagnantes
partageaient quatre traits : elles sont **gentilles** (ne trahissent jamais les
premières), **réactives** (ne laissent pas passer une trahison), **indulgentes**
(reviennent à la coopération) et **lisibles** (l'adversaire peut les prévoir).

Ce sont des adjectifs. Ce module les transforme en nombres lus **dans les
parties**, et pas dans la définition des stratégies : une propriété déclarée
n'est pas une propriété vérifiée, et le cas de Pavlov le montre — ses
probabilités ne disent nulle part qu'elle pardonne, c'est son comportement qui
le dit.

La mesure qui porte l'argument est la dernière, `temps_de_retablissement` :
**combien de tours une paire met à retrouver la coopération après un accident.**
C'est elle qui sépare une stratégie qui survit au bruit d'une qui s'y suicide,
et c'est la seule qui ait une traduction directe en production : un agent qui ne
se rétablit pas d'un message perdu est un agent qui lâche la relation pour de
bon.
"""
from __future__ import annotations

from dataclasses import dataclass
from statistics import mean
from typing import Dict, List, Optional, Sequence

from strategies import COOP, TRAHIR
from tournoi import Duel, Resultat

#: Longueur de la fenêtre d'observation après un accident, en tours.
#:
#: Court exprès. Il a fallu trois versions pour obtenir une mesure comparable
#: entre niveaux de bruit, et la fenêtre courte est ce qui l'autorise :
#:
#: 1. fenêtre de 50 tours, accidents suivants ignorés — à 10% de bruit, la paire
#:    « se rétablit » parce qu'un second dérapage la remet en coopération. On
#:    mesurait la chance ;
#: 2. fenêtre de 50 tours, échantillon écarté dès qu'un accident survient — on
#:    n'écarte alors que les fenêtres longues, donc les rétablissements lents :
#:    biais de survie, et la part d'échecs baissait encore avec le bruit ;
#: 3. fenêtre **courte et exigée saine d'avance**, avant de regarder s'il y a eu
#:    rétablissement. La conservation d'un échantillon ne dépend plus de son
#:    résultat, et le chiffre devient comparable d'un bruit à l'autre.
#:
#: À 10% de bruit, une fenêtre de 10 tours reste saine une fois sur huit environ
#: — assez rare pour qu'il faille beaucoup de parties, assez fréquent pour que
#: l'échantillon tienne.
FENETRE = 10

#: Conservé pour la lisibilité du code appelant.
PLAFOND_RETABLISSEMENT = FENETRE


@dataclass
class Profil:
    """Les quatre traits d'Axelrod, plus les deux que la mesure a imposés."""
    nom: str
    gentillesse: float          # 1 = ne trahit jamais la première
    riposte: float              # 1 = riposte toujours à une trahison
    indulgence: float           # 1 = revient quand l'autre revient
    sortie_de_spirale: float    # 1 = sort d'une trahison mutuelle de soi-même
    lisibilite: float           # 1 = parfaitement prévisible à mémoire d'un coup
    retablissement: Optional[float]  # tours après un accident ; None = jamais
    coups: int

    def ligne(self) -> str:
        ret = ("jamais" if self.retablissement is None
               else f"{self.retablissement:.1f}")
        return (f"{self.nom:<32} {self.gentillesse:>6.2f} {self.riposte:>7.2f} "
                f"{self.indulgence:>9.2f} {self.sortie_de_spirale:>8.2f} "
                f"{self.lisibilite:>8.2f} {ret:>14}")


def _perspectives(res: Resultat, nom: str):
    """Rend (mes coups, ses coups, mes voulus, ses voulus) par duel joué.

    Un duel est enregistré sous (a, b) ; selon le côté, les listes s'échangent.
    Une stratégie jouant contre sa copie apparaît des deux côtés du même duel,
    et on compte bien les deux.

    Les voulus des **deux** joueurs sont rendus, parce que mesurer un
    rétablissement demande de savoir si un second accident est survenu entre
    temps — de n'importe lequel des deux côtés.
    """
    for (na, nb), liste in res.duels.items():
        for d in liste:
            if na == nom:
                yield d.joues_a, d.joues_b, d.voulus_a, d.voulus_b
            if nb == nom:
                yield d.joues_b, d.joues_a, d.voulus_b, d.voulus_a


def gentillesse(res: Resultat, nom: str) -> float:
    """Part des duels où la stratégie n'a pas trahi la première.

    « La première » au sens strict : on cherche le premier tour où l'un des deux
    trahit, et on regarde qui. Un tour où les deux trahissent simultanément ne
    compte contre personne — sans quoi le bruit rendrait toute stratégie méchante.
    """
    scores: List[float] = []
    for moi, lui, _, _ in _perspectives(res, nom):
        verdict = 1.0
        for t in range(len(moi)):
            if moi[t] == TRAHIR or lui[t] == TRAHIR:
                if moi[t] == TRAHIR and lui[t] == COOP:
                    verdict = 0.0
                break
        scores.append(verdict)
    return mean(scores) if scores else 1.0


def riposte(res: Resultat, nom: str) -> float:
    """Probabilité de trahir au tour suivant une trahison subie.

    Une stratégie sans riposte se fait exploiter ; c'est le défaut de
    « Toujours coopérer », et la raison pour laquelle l'indulgence seule ne
    suffit pas.
    """
    occasions = ripostes = 0
    for moi, lui, _, _ in _perspectives(res, nom):
        for t in range(len(moi) - 1):
            if lui[t] == TRAHIR:
                occasions += 1
                ripostes += moi[t + 1] == TRAHIR
    return ripostes / occasions if occasions else 0.0


def indulgence(res: Resultat, nom: str) -> float:
    """Probabilité de recoopérer quand l'autre revient, alors que je trahissais.

    C'est le passage de l'état (je trahis, il coopère) à la coopération. Le
    Rancunier y est à zéro par construction ; donnant-donnant y est à un, ce qui
    masque son vrai défaut — il sort de la boucle seulement si l'autre en sort
    le premier, et sous bruit personne n'en sort. D'où la mesure suivante.
    """
    occasions = retours = 0
    for moi, lui, _, _ in _perspectives(res, nom):
        for t in range(len(moi) - 1):
            if moi[t] == TRAHIR and lui[t] == COOP:
                occasions += 1
                retours += moi[t + 1] == COOP
    return retours / occasions if occasions else 1.0


def sortie_de_spirale(res: Resultat, nom: str) -> float:
    """Probabilité de recoopérer **le premier** alors que les deux trahissent.

    Cette mesure n'était pas dans la liste d'Axelrod. Elle s'est imposée en
    lisant les résultats : Pavlov affiche une indulgence de 0,00 — elle ne rend
    pas la coopération à qui la lui rend — et pourtant elle survit au bruit,
    alors que donnant-donnant, à 1,00 d'indulgence, s'y effondre.

    L'explication est ici. Donnant-donnant ne sort d'une trahison mutuelle que
    si l'autre en sort d'abord ; deux donnant-donnant coincés attendent donc
    chacun un geste que l'autre n'a aucune raison de faire, et la relation est
    morte. Pavlov, elle, change de coup quand un tour a mal payé : elle rouvre
    toute seule.

    « Indulgent » recouvrait donc deux gestes différents — *rendre* la
    coopération et *reprendre* l'initiative — et seul le second décide de la
    survie sous bruit. C'est le genre de distinction qu'une propriété nommée
    cache et qu'une propriété mesurée fait apparaître.
    """
    occasions = sorties = 0
    for moi, lui, _, _ in _perspectives(res, nom):
        for t in range(len(moi) - 1):
            if moi[t] == TRAHIR and lui[t] == TRAHIR:
                occasions += 1
                sorties += moi[t + 1] == COOP
    return sorties / occasions if occasions else 1.0


def lisibilite(res: Resultat, nom: str) -> float:
    """Dans quelle mesure un modèle à mémoire d'un coup prévoit le coup suivant.

    Pour chacun des quatre états (mon dernier coup, son dernier coup), on relève
    la fréquence de coopération, et la prévisibilité de l'état est la plus
    grande des deux fréquences. La moyenne est pondérée par la fréquence des
    états : être imprévisible dans un cas qui n'arrive jamais ne gêne personne.

    Axelrod appelait ça « clarity » et y voyait une condition de la coopération :
    on ne peut pas s'entendre avec quelqu'un dont on ne peut rien anticiper.
    """
    etats: Dict[tuple, List[int]] = {}
    for moi, lui, _, _ in _perspectives(res, nom):
        for t in range(len(moi) - 1):
            etats.setdefault((moi[t], lui[t]), []).append(moi[t + 1] == COOP)
    if not etats:
        return 1.0
    total = sum(len(v) for v in etats.values())
    return sum(len(v) / total * max(mean(v), 1 - mean(v))
               for v in etats.values())


def temps_de_retablissement(res: Resultat, nom: str) -> Optional[float]:
    """Tours nécessaires pour retrouver la coopération mutuelle après un accident.

    Un accident est un tour où le coup **exécuté** diffère du coup **voulu** :
    seul le bruit produit ça. On repart de là et on compte les tours jusqu'au
    premier (coopère, coopère). Au-delà de `PLAFOND_RETABLISSEMENT`, on compte
    la relation comme perdue et le duel ne contribue pas à la moyenne — mais sa
    part est rendue par `part_perdue`, sinon la moyenne flatterait précisément
    les stratégies qui ne se rétablissent jamais.

    Rend `None` s'il n'y a eu aucun accident (tournoi sans bruit).
    """
    delais = _delais(res, nom)
    finis = [d for d in delais if d is not None]
    return mean(finis) if finis else None


def part_perdue(res: Resultat, nom: str) -> float:
    """Part des accidents dont la paire ne s'est jamais relevée.

    C'est le chiffre honnête à côté du temps moyen : donnant-donnant affiche un
    rétablissement rapide sur les accidents qu'il répare, et ne répare presque
    rien.
    """
    delais = _delais(res, nom)
    return (sum(d is None for d in delais) / len(delais)) if delais else 0.0


def _delais(res: Resultat, nom: str) -> List[Optional[int]]:
    """Délai de retour à la coopération mutuelle après chaque accident.

    `None` quand la paire ne s'est pas relevée dans la fenêtre.

    On ne retient un accident que si les `FENETRE` tours qui le suivent sont
    **entièrement exempts d'accident**, et cette condition est vérifiée *avant*
    de regarder s'il y a eu rétablissement. L'ordre est tout : décider de garder
    l'échantillon après avoir vu son résultat, c'est garder préférentiellement
    les rétablissements rapides, et c'est l'erreur que les deux versions
    précédentes ont faite (voir `FENETRE`).

    Ce qu'on mesure est donc : *quand une paire dérape puis est laissée
    tranquille, se remet-elle d'elle-même, et en combien de tours ?*
    """
    delais: List[Optional[int]] = []
    for moi, lui, mes_voulus, ses_voulus in _perspectives(res, nom):
        n = len(moi)
        for t in range(n):
            if mes_voulus[t] == moi[t] and ses_voulus[t] == lui[t]:
                continue  # pas d'accident à ce tour
            fin = t + 1 + FENETRE
            if fin > n:
                continue  # fenêtre tronquée par la fin du duel
            if any(mes_voulus[u] != moi[u] or ses_voulus[u] != lui[u]
                   for u in range(t + 1, fin)):
                continue  # fenêtre polluée : écartée sans regarder le résultat
            trouve = None
            for u in range(t + 1, fin):
                if moi[u] == COOP and lui[u] == COOP:
                    trouve = u - t
                    break
            delais.append(trouve)
    return delais


def _delais_entre_soi(res: Resultat, nom: str) -> List[Optional[int]]:
    """Les mêmes délais, mais sur les duels de la stratégie **contre sa copie**.

    La mesure tous adversaires confondus ne répond pas à la question posée :
    elle plaçait Pavlov à 55% d'accidents non réparés, au même niveau que
    donnant-donnant, alors que Pavlov sort d'une spirale par construction. La
    raison est que la moyenne inclut des adversaires avec qui aucun
    rétablissement n'est possible — Rancunier, Toujours trahir — et qu'une
    stratégie ne peut pas réparer une relation à elle seule.

    Contre sa propre copie, la question devient nette et c'est aussi la question
    évolutive : **une population de cette stratégie survit-elle à ses propres
    accidents ?** C'est celle qui décide, parce qu'une stratégie qui réussit
    finit entourée d'elle-même.
    """
    delais: List[Optional[int]] = []
    for d in res.duels.get((nom, nom), []):
        n = len(d.joues_a)
        for t in range(n):
            if not d.accident(t):
                continue
            fin = t + 1 + FENETRE
            if fin > n:
                continue
            if any(d.accident(u) for u in range(t + 1, fin)):
                continue
            trouve = None
            for u in range(t + 1, fin):
                if d.joues_a[u] == COOP and d.joues_b[u] == COOP:
                    trouve = u - t
                    break
            delais.append(trouve)
    return delais


def entre_soi(res: Resultat, nom: str) -> Dict[str, Optional[float]]:
    """Rétablissement d'une paire de clones : part non réparée, délai, effectif.

    `part_non_reparee` vaut **`None`** quand aucun accident n'a été observé, et
    non zéro. La version précédente rendait 0,0 dans ce cas, et un tournoi sans
    accident détectable affichait donc « 0% d'accidents non réparés » pour
    Rancunier — une stratégie qui ne pardonne jamais. Un échantillon vide doit
    se dire vide ; rendu comme une mesure, il est pire qu'une erreur, parce
    qu'il a l'air d'un résultat.
    """
    d = _delais_entre_soi(res, nom)
    finis = [x for x in d if x is not None]
    return {
        "echantillon": len(d),
        "part_non_reparee": (sum(x is None for x in d) / len(d)) if d else None,
        "delai_moyen": mean(finis) if finis else None,
    }


def profil(res: Resultat, nom: str) -> Profil:
    coups = sum(len(m) for m, _, _, _ in _perspectives(res, nom))
    return Profil(
        nom=nom,
        gentillesse=gentillesse(res, nom),
        riposte=riposte(res, nom),
        indulgence=indulgence(res, nom),
        sortie_de_spirale=sortie_de_spirale(res, nom),
        lisibilite=lisibilite(res, nom),
        retablissement=temps_de_retablissement(res, nom),
        coups=coups,
    )


def profils(res: Resultat, noms: Sequence[str]) -> List[Profil]:
    return [profil(res, n) for n in noms]


EN_TETE = (f"{'stratégie':<32} {'gentil':>6} {'riposte':>7} "
           f"{'indulgent':>9} {'sortie':>8} {'lisible':>8} "
           f"{'rétablissement':>14}")
