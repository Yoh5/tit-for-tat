# Donnant-donnant ne gagne pas

Un tournoi de dilemme du prisonnier itéré, écrit pour vérifier une histoire
qu'on raconte souvent : *« Robert Axelrod a organisé un tournoi, la stratégie
Donnant-donnant l'a gagné, et c'est donc la meilleure réponse au conflit. »*

La première partie est vraie. Les deux autres ne tiennent pas, et ce dépôt
permet de le voir soi-même plutôt que de me croire.

```
python experiences.py              # les quatre expériences
python -m pytest test_tournoi.py -q   # 31 tests
```

Aucune dépendance en dehors de la bibliothèque standard. Déterministe à graine
fixée : les chiffres ci-dessous se reproduisent.

---

## 1. Sans bruit, ce qui gagne n'est pas une stratégie

Sur notre plateau de neuf stratégies, **Rancunier arrive premier et
Donnant-donnant sixième**. Ce n'est pas un démenti d'Axelrod : son tournoi de
1980 comptait quinze entrées précises que nous n'avons pas, et il a lui-même
écrit que le classement dépendait du plateau. Sur douze graines différentes,
trois stratégies se partagent la première place — **le vainqueur n'est même pas
stable.**

Ce qui est stable, et que l'expérience vérifie par assertion :

> **Les six stratégies qui ne trahissent jamais les premières terminent toutes
> devant les trois autres.** La dernière des gentilles marque 2,506 par tour, la
> première des autres 2,248. Les deux familles ne se recouvrent pas.

Le trait gagnant n'est pas une stratégie, c'est de ne pas ouvrir les hostilités.
« Donnant-donnant gagne » était vrai d'un plateau ; « ne trahis pas le premier »
tient aussi sur celui-ci.

## 2. Avec du bruit, donnant-donnant se suicide

Dans la vraie vie, un geste part de travers, un message se perd, une intention
est mal lue. On ajoute donc une probabilité qu'un coup **dérape** : les deux
joueurs voient le mauvais coup, et personne n'a triché.

Le résultat central, mesuré sur des paires de la **même** stratégie, parce
qu'une stratégie qui réussit finit entourée d'elle-même :

| stratégie | ne se relève pas de son propre accident | délai quand elle se relève |
|---|---|---|
| Donnant-donnant x2 | **0 %** | 1,2 tour |
| Pavlov | **0 %** | 2,0 tours |
| Donnant-donnant généreux | 1 à 2 % | 2,6 tours |
| **Donnant-donnant** | **71 à 78 %** | 1 tour |
| Sondeur (Joss) | 82 à 93 % | 1 tour |
| Rancunier | **100 %** | jamais |

*(fenêtre de 10 tours sans nouvel accident ; stable de 1 % à 10 % de bruit)*

**Deux donnant-donnant ne se relèvent pas de leur propre accident dans trois cas
sur quatre.** Le mécanisme est un écho : A dérape, B riposte, A riposte à la
riposte, et la paire alterne trahison et coopération en décalé sans jamais
retomber en phase. Aucun des deux n'a mal agi, aucun des deux ne peut réparer.

Trois stratégies s'en sortent toujours, et chacune autrement :

- **absorber** — ne riposter qu'à la deuxième trahison, donc ignorer un accident
  isolé (Donnant-donnant x2) ;
- **sortir** — changer de coup quand un tour a mal payé, donc quitter la spirale
  sans attendre un geste de l'autre (Pavlov) ;
- **pardonner** — rouvrir au hasard de temps en temps, ce qui suffit à casser
  l'écho (Donnant-donnant généreux, pardon 1/3).

Sur douze graines, donnant-donnant ne gagne à **aucun** niveau de bruit. À 1 et
2 %, c'est Donnant-donnant x2 (7 fois sur 12). À 5 et 10 %, Pavlov passe devant.
À 20 %, la coopération ne vaut plus la peine et Rancunier et Toujours trahir se
partagent la tête.

Ce n'est pas une trouvaille : Nowak et Sigmund l'ont publié en 1992 et 1993. Mais
c'est la moitié de l'histoire qui ne survit presque jamais à la vulgarisation.

## 3. L'extorsion gagne le duel et perd le monde

En 2012, Press et Dyson ont montré qu'un joueur peut imposer un rapport fixe
entre son gain et celui de l'autre. L'adversaire qui cherche à maximiser son
score se met alors à servir le gain de l'extorqueur.

Mesuré ici, sans faire confiance à la dérivation :

- extorsion contre donnant-donnant : **1,139 contre 1,086** — elle gagne ;
- extorsion contre un coopérateur naïf : **3,565 contre 2,286** — elle rançonne.

Et pourtant, dans une population qui évolue par dynamique de réplication,
**l'extorsion s'éteint**, avec Toujours trahir, Aléatoire et le Sondeur. La
population se stabilise sur les généreuses : Donnant-donnant généreux 15,4 %,
Rancunier 15,3 %, la variante généreuse à déterminant nul 15,2 %.

L'extorqueur vit de partenaires qu'il ruine. Sa victoire en duel ne survit pas au
fait que la population change — c'est le résultat de Stewart et Plotkin (2013).

## 4. « La meilleure stratégie » n'existe pas

En 2004, au tournoi du vingtième anniversaire, une équipe de l'université de
Southampton a inscrit une soixantaine d'agents qui se reconnaissaient par une
signature dans leurs premiers coups. Les coéquipiers reconnus se répartissaient
les rôles : les uns se sacrifiaient, l'un encaissait. Il a pris la première place.

Reproduit ici avec un récolteur et huit sacrifiés :

| | gain par tour | rang |
|---|---|---|
| Coalition (récolteur) | **2,972** | **1** |
| Coalition (sacrifiés, moyenne) | 2,446 | dispersés |
| Donnant-donnant | — | **12** |

Un classement individuel ne dit donc pas quelle stratégie est bonne : il dit qui
a été le mieux servi par les règles d'inscription. La question « quelle est la
meilleure stratégie » est mal posée tant qu'on n'a pas dit **combien d'agents on
peut inscrire, et s'ils peuvent se reconnaître.**

---

## Ce que mesure le dépôt, et pourquoi c'est l'essentiel

Axelrod, en relisant son tournoi, a dit que les gagnantes étaient **gentilles,
réactives, indulgentes et lisibles**. Ce sont des adjectifs. `proprietes.py` les
transforme en nombres lus **dans les parties jouées**, pas dans la définition des
stratégies — et ce déplacement a produit le seul résultat que je n'attendais pas.

Pavlov affiche une **indulgence de 0,00** : elle ne rend pas la coopération à qui
la lui rend. Donnant-donnant affiche **1,00**. Et c'est Pavlov qui survit au
bruit. « Indulgent » recouvrait donc deux gestes différents :

- **rendre** la coopération quand l'autre la rend — ce que donnant-donnant fait ;
- **reprendre** l'initiative quand les deux sont coincés — ce qu'il ne fait pas.

Seul le second décide de la survie sous bruit. Le dépôt mesure donc une
cinquième propriété, `sortie_de_spirale`, qui vaut 0,00 pour donnant-donnant et
1,00 pour Pavlov. Une propriété nommée l'avait cachée ; une propriété mesurée
l'a fait apparaître.

### La mesure a demandé trois tentatives

Les deux premières versions du temps de rétablissement donnaient un chiffre qui
**baissait** quand le bruit montait, de 46 % à 16 %. Deux causes successives, et
aucune n'était le résultat :

1. fenêtre longue, accidents suivants ignorés — à 10 % de bruit, la paire « se
   rétablit » parce qu'un **second** dérapage la remet en coopération. On
   mesurait la chance ;
2. fenêtre longue, échantillon écarté dès qu'un accident survient — on n'écarte
   alors que les fenêtres longues, donc les rétablissements lents : biais de
   survie ;
3. fenêtre **courte et exigée saine avant** de regarder le résultat. La
   conservation d'un échantillon ne dépend plus de ce qu'il contient, et le
   chiffre devient le même à 1 % et à 10 % de bruit.

Cette platitude est la seule preuve que la mesure porte sur la stratégie et non
sur les conditions. `test_le_retablissement_ne_depend_pas_du_bruit` la vérifie.

---

## Les fichiers

| | |
|---|---|
| `strategies.py` | les stratégies, et pourquoi chacune est là |
| `tournoi.py` | duel, tournoi, les deux bruits, dynamique de réplication |
| `proprietes.py` | les propriétés d'Axelrod comme mesures, et la cinquième |
| `experiences.py` | les quatre expériences ; `--json` pour les chiffres |
| `test_tournoi.py` | 31 tests, dont les trois affirmations centrales |

## Références

- R. Axelrod, *The Evolution of Cooperation*, 1984 — le tournoi de 1980.
- M. Nowak et K. Sigmund, « Tit for tat in heterogeneous populations »,
  *Nature*, 1992 — Donnant-donnant généreux.
- M. Nowak et K. Sigmund, « A strategy of win-stay, lose-shift that outperforms
  tit-for-tat », *Nature*, 1993 — Pavlov.
- W. Press et F. Dyson, « Iterated Prisoner's Dilemma contains strategies that
  dominate any evolutionary opponent », *PNAS*, 2012 — l'extorsion.
- A. Stewart et J. Plotkin, « From extortion to generosity, evolution in the
  Iterated Prisoner's Dilemma », *PNAS*, 2013 — sa chute.
- Le tournoi du vingtième anniversaire, 2004 — la coalition de Southampton.

## Portée et limites

Ce dépôt **n'est pas** une réplication du tournoi de 1980 : les quinze entrées
originales n'y sont pas, et le plateau a été choisi pour que les comparaisons
soient lisibles. Les classements dépendent du plateau — c'est d'ailleurs l'un des
résultats. Ce qui ne dépend pas du plateau est signalé comme tel et vérifié par
un test.

Les gains sont ceux d'Axelrod (3 / 1 / 5 / 0). Les durées de partie sont tirées
au hasard, d'espérance 200 tours, pour éviter que la trahison au dernier tour ne
remonte par récurrence. Le bruit implémenté dans les expériences est celui
d'**exécution** ; `tournoi.duel(..., perception=True)` propose l'autre, où les
deux joueurs ont des historiques différents et ne peuvent pas le savoir.

Licence : Apache 2.0.
