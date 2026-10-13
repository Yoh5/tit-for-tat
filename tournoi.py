"""Le moteur : un duel, un tournoi, et le bruit qui change tout.

## Les deux bruits, qu'il ne faut pas confondre

- **Bruit d'exécution** (*trembling hand*) : le coup joué dérape. Les deux
  joueurs voient le même coup — le mauvais. C'est le défaut d'un agent dont un
  message se perd ou dont une action échoue.
- **Bruit de perception** : le coup est bien joué mais mal lu. Les deux joueurs
  ont alors des historiques **différents**, et aucun ne peut savoir lequel.

On attendrait qu'ils se comportent très différemment : sous bruit d'exécution le
fautif voit son propre dérapage, sous bruit de perception il ne le voit pas. Et
la littérature les distingue soigneusement.

**Mesuré, l'écart est presque nul.** Sur le rétablissement d'une paire de clones,
les deux régimes donnent les mêmes chiffres à un point près, et les classements
bougent à peine. La seule différence tient en un tour : Pavlov se relève en 2
tours sous bruit d'exécution et en 3 sous bruit de perception, parce que le
malentendu lui impose un tour de punition supplémentaire avant que les deux
n'atteignent l'état (trahir, trahir) dont elle sait sortir.

J'avais écrit ici l'inverse — que Pavlov s'en sortait dans un cas et pas dans
l'autre — avant de le mesurer. C'était faux, et c'est noté parce que l'erreur
est instructive : la distinction entre les deux bruits est réelle dans le détail
du mécanisme et sans effet sur ce qui nous intéresse.

## Pourquoi un nombre de tours tiré au hasard

Si les deux joueurs connaissent le dernier tour, la trahison au dernier tour est
dominante, puis l'avant-dernier, et la coopération s'effondre par récurrence.
Axelrod tirait donc la longueur au hasard. On fait pareil : espérance `tours`,
loi géométrique.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from itertools import combinations_with_replacement
from typing import Dict, List, Sequence, Tuple

from strategies import COOP, GAINS, TRAHIR, Strategie


@dataclass
class Duel:
    """Ce qu'un duel laisse derrière lui, pour que les propriétés soient
    mesurables après coup."""
    gain_a: float
    gain_b: float
    tours: int
    #: Coups **exécutés**, ceux que les deux joueurs ont observés.
    joues_a: List[int] = field(default_factory=list)
    joues_b: List[int] = field(default_factory=list)
    #: Coups **voulus** : la différence avec les joués est le bruit d'exécution.
    voulus_a: List[int] = field(default_factory=list)
    voulus_b: List[int] = field(default_factory=list)
    #: Coups **vus** : ce que A a cru lire de B, et réciproquement. La différence
    #: avec les joués est le bruit de perception.
    #:
    #: Sans ces deux listes, un accident de perception est indétectable après
    #: coup — le coup joué étant le coup voulu, `voulus != joues` ne signale
    #: rien. La première version de ce module ne les gardait pas, et la mesure
    #: de rétablissement rendait alors **0% pour toutes les stratégies**,
    #: Rancunier compris, ce qui est impossible : c'était un échantillon vide
    #: rendu comme un résultat.
    vus_a: List[int] = field(default_factory=list)
    vus_b: List[int] = field(default_factory=list)

    def accident(self, t: int) -> bool:
        """Y a-t-il eu un dérapage ou une mélecture au tour `t` ?

        La définition couvre les deux bruits, donc une mesure écrite avec elle
        vaut dans les deux régimes.
        """
        return (self.voulus_a[t] != self.joues_a[t]
                or self.voulus_b[t] != self.joues_b[t]
                or self.vus_a[t] != self.joues_b[t]
                or self.vus_b[t] != self.joues_a[t])


def longueur(alea: random.Random, tours: int) -> int:
    """Longueur tirée, d'espérance `tours`, minimum 1."""
    if tours <= 1:
        return 1
    return max(1, int(alea.expovariate(1 / tours)) + 1)


def duel(a: Strategie, b: Strategie, alea: random.Random, tours: int = 200,
         bruit: float = 0.0, perception: bool = False) -> Duel:
    """Fait jouer `a` contre `b`.

    `bruit` est la probabilité qu'un coup dérape (exécution) ou soit mal lu
    (`perception=True`). Les historiques passés aux stratégies sont toujours ce
    qu'elles **observent** : c'est la seule information dont un joueur dispose.
    """
    a.nouvelle_partie()
    b.nouvelle_partie()
    n = longueur(alea, tours)
    d = Duel(0.0, 0.0, n)

    # Sous bruit de perception, chaque joueur tient sa propre version des faits.
    vu_par_a: List[int] = []   # ce que A croit que B a joué
    vu_par_b: List[int] = []   # ce que B croit que A a joué
    propre_a: List[int] = []   # ce que A croit avoir joué
    propre_b: List[int] = []

    for _ in range(n):
        va = a.jouer(propre_a, vu_par_a, alea)
        vb = b.jouer(propre_b, vu_par_b, alea)
        d.voulus_a.append(va)
        d.voulus_b.append(vb)

        if bruit and not perception:
            ja = (1 - va) if alea.random() < bruit else va
            jb = (1 - vb) if alea.random() < bruit else vb
        else:
            ja, jb = va, vb

        ga, gb = GAINS[(ja, jb)]
        d.gain_a += ga
        d.gain_b += gb
        d.joues_a.append(ja)
        d.joues_b.append(jb)

        if bruit and perception:
            # Le coup est juste, la lecture ne l'est pas : A peut voir une
            # trahison là où B a coopéré, sans que B puisse le deviner.
            vu_par_a.append((1 - jb) if alea.random() < bruit else jb)
            vu_par_b.append((1 - ja) if alea.random() < bruit else ja)
        else:
            vu_par_a.append(jb)
            vu_par_b.append(ja)
        propre_a.append(ja)
        propre_b.append(jb)
        d.vus_a.append(vu_par_a[-1])
        d.vus_b.append(vu_par_b[-1])

    return d


@dataclass
class Resultat:
    """Le classement et de quoi le discuter."""
    moyennes: Dict[str, float]
    duels: Dict[Tuple[str, str], List[Duel]]
    bruit: float
    perception: bool
    repetitions: int
    tours: int

    def classement(self) -> List[Tuple[str, float]]:
        return sorted(self.moyennes.items(), key=lambda kv: -kv[1])

    def rang(self, nom: str) -> int:
        for i, (n, _) in enumerate(self.classement(), start=1):
            if n == nom:
                return i
        raise KeyError(nom)


def tournoi(pool: Sequence[Strategie], graine: int = 1, tours: int = 200,
            repetitions: int = 20, bruit: float = 0.0,
            perception: bool = False) -> Resultat:
    """Toutes contre toutes, chacune aussi contre une copie d'elle-même.

    Le score est le **gain moyen par tour**, pas le total : les longueurs sont
    tirées, donc les totaux ne sont pas comparables. C'est aussi la bonne unité
    pour parler d'une relation sans supposer sa durée.

    Déterministe à graine fixée : deux exécutions rendent le même classement.
    """
    noms = [s.nom for s in pool]
    if len(set(noms)) != len(noms):
        raise ValueError(f"deux stratégies portent le même nom : {noms}")

    cumul = {n: 0.0 for n in noms}
    tours_joues = {n: 0 for n in noms}
    duels: Dict[Tuple[str, str], List[Duel]] = {}

    for i, j in combinations_with_replacement(range(len(pool)), 2):
        a, b = pool[i], pool[j]
        for rep in range(repetitions):
            # Une graine par (paire, répétition) : le bruit subi par une paire
            # ne dépend pas de l'ordre dans lequel on parcourt le tournoi.
            alea = random.Random((graine, i, j, rep).__hash__())
            if i == j:
                import copy
                d = duel(a, copy.deepcopy(b), alea, tours, bruit, perception)
            else:
                d = duel(a, b, alea, tours, bruit, perception)
            duels.setdefault((a.nom, b.nom), []).append(d)
            cumul[a.nom] += d.gain_a
            tours_joues[a.nom] += d.tours
            cumul[b.nom] += d.gain_b
            tours_joues[b.nom] += d.tours

    moyennes = {n: (cumul[n] / tours_joues[n] if tours_joues[n] else 0.0)
                for n in noms}
    return Resultat(moyennes, duels, bruit, perception, repetitions, tours)


def matrice_gains(pool: Sequence[Strategie], graine: int = 1, tours: int = 200,
                  repetitions: int = 10, bruit: float = 0.0,
                  perception: bool = False) -> Tuple[List[str], List[List[float]]]:
    """Gain moyen par tour de i contre j — l'entrée de la dynamique évolutive.

    On la calcule séparément du tournoi parce qu'elle a besoin des deux sens
    (i contre j **et** j contre i), que le classement agrège.
    """
    import copy
    noms = [s.nom for s in pool]
    n = len(pool)
    A = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            total = tour_total = 0.0
            for rep in range(repetitions):
                alea = random.Random((graine, "M", i, j, rep).__hash__())
                a = copy.deepcopy(pool[i])
                b = copy.deepcopy(pool[j])
                d = duel(a, b, alea, tours, bruit, perception)
                total += d.gain_a
                tour_total += d.tours
            A[i][j] = total / tour_total if tour_total else 0.0
    return noms, A


def evolution(noms: Sequence[str], A: Sequence[Sequence[float]],
              generations: int = 500, seuil: float = 1e-4) -> Dict[str, float]:
    """Dynamique de réplication : les parts suivent leur gain relatif.

    `x_i' = x_i * f_i / f_moyen`, où `f_i` est le gain de i contre la population
    courante. Une stratégie qui gagne tous ses duels mais ruine ses partenaires
    voit sa propre ressource disparaître — c'est le mécanisme par lequel
    l'extorsion s'effondre alors qu'elle gagnait le face-à-face.
    """
    n = len(noms)
    x = [1.0 / n] * n
    for _ in range(generations):
        f = [sum(A[i][j] * x[j] for j in range(n)) for i in range(n)]
        moyen = sum(x[i] * f[i] for i in range(n))
        if moyen <= 0:
            break
        suivant = [x[i] * f[i] / moyen for i in range(n)]
        total = sum(suivant)
        suivant = [v / total for v in suivant]
        if max(abs(suivant[i] - x[i]) for i in range(n)) < seuil / n:
            x = suivant
            break
        x = suivant
    return {noms[i]: x[i] for i in range(n)}
