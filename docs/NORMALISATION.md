# Normalisation du texte

Code : `src/quran_harness/normalize.py`. Tests : `tests/test_normalize.py`.

Le texte brut n'est jamais modifié. La normalisation produit une copie du mot à un
niveau donné, uniquement **en retirant des caractères** : aucune lettre n'est remplacée
par une autre. Toute comparaison de texte arabe doit dire à quel niveau elle est faite.

## Les trois niveaux (SPEC §3)

| Niveau | Nom | Colonne de `words` | Ce qui est retiré |
|---|---|---|---|
| 0 | brut | `text_raw` | rien |
| 1 | sans signes de récitation | `text_norm1` | les signes de récitation |
| 2 | sans voyelles | `text_norm2` | les signes de récitation et les voyelles |

Exemples tirés du texte :

| Brut | Niveau 1 | Niveau 2 | Ce qui change |
|---|---|---|---|
| وَيَقْدِرُ | وَيَقْدِرُ | ويقدر | voyelles |
| مِنۢ | مِن | من | petit mīm (iqlāb), puis voyelle |
| ٱلسَّمَآءِ | ٱلسَّمَاءِ | ٱلسماء | madda, puis voyelles |
| ءَامَنُوا۟ | ءَامَنُوا | ءامنوا | zéro rond sur l'alif muet, puis voyelles |
| لَهُۥ | لَهُۥ | له | petit wāw retiré avec les voyelles |

## Classement des caractères

Tous les caractères présents dans le texte Tanzil ʿuthmānī sont classés ci-dessous.
Un caractère non classé arrête l'ingestion : une nouvelle version du texte ne peut donc
pas introduire un signe qui serait ignoré en silence.

### Lettres — conservées à tous les niveaux
- U+0621 à U+063A et U+0641 à U+064A : les lettres, formes de hamza comprises.
- U+0671 : alif waṣla (ٱ). Il reste distinct de l'alif simple.
- U+0654 : hamza sans support, portée par un tatweel (U+0640), comme dans `شَيْـًٔا`.

### Signes de récitation — retirés dès le niveau 1
| Caractère | Nom | Occurrences |
|---|---|---|
| U+0653 | madda | 5 376 |
| U+06D6 à U+06DB | marques de pause | 4 359 |
| U+06DC | petit sīn haut | 7 |
| U+06DF | petit zéro rond (lettre jamais prononcée) | 3 988 |
| U+06E0 | petit zéro rectangulaire (lettre muette en liaison) | 66 |
| U+06E2, U+06ED | petit mīm haut ou bas (iqlāb) | 609 |
| U+06E3 | petit sīn bas | 1 |
| U+06EA, U+06EB, U+06EC | imāla, ishmām, tashīl | 3 |

Les marques de pause sont presque toujours des jetons séparés du mot. Elles ne font
alors pas partie du mot : elles sont rangées dans la colonne `sign_after` du mot qui
les précède, et serviront à la segmentation (étape 4).

### Voyelles — retirées au niveau 2
| Caractère | Nom | Occurrences |
|---|---|---|
| U+064B à U+064D | tanwīn | 8 893 |
| U+064E à U+0650 | fatḥa, ḍamma, kasra | 207 358 |
| U+0651 | shadda | 23 016 |
| U+0652 | sukūn | 37 372 |
| U+0670 | alif suscrit | 9 838 |
| U+06E5, U+06E6 | petit wāw, petit yāʾ | 2 214 |
| U+06E7, U+06E8 | petit yāʾ haut, petit nūn haut | 39 |

Le niveau 2 ne garde donc que ce qui est écrit sur la ligne, plus la hamza. Le tatweel
qui portait un petit yāʾ haut est retiré avec lui (`إِبْرَٰهِـۧمَ` donne `إبرهم`).

## Ce que la normalisation ne fait pas
- **Pas de normalisation Unicode (NFC, NFD…).** Le fichier Tanzil n'est pas en ordre
  canonique Unicode : la shadda y précède la voyelle, et la madda suit l'alif sans être
  fusionnée avec lui. Appliquer NFC modifierait le texte. Un test le vérifie.
- **Pas de passage à l'orthographe courante.** Le niveau 2 de `ٱلْعَٰلَمِينَ` est
  `ٱلعلمين`, pas `العالمين`.
- **Pas d'unification des hamzas ni des alifs.**
- **Pas de neutralisation des assimilations entre mots** (voir QUESTIONS.md, Q12).

## Conséquence pratique pour le code et les tests
Un littéral arabe tapé dans un fichier source peut être réordonné par un éditeur. Les
tests écrivent donc leurs exemples en translittération Buckwalter, convertie par
`quran_harness.buckwalter.to_arabic`, ou en échappements `\uXXXX`.

## La forme d'une case (D-03, D-04) — depuis le code 0.10.0

Code : `normalize.split_final_vowel`, `normalize.drop_assimilation_shadda`,
`units.form_of`. Tests : `tests/test_units.py`. Réglages : section `form` de `config.yaml`.

La **forme** est ce sur quoi on décide que deux cases sont « la même forme ». Elle part
du niveau 1 (sans signes de récitation) et retire encore, sans jamais retirer une lettre :

| Ce qui est retiré | Exemple | Réglage pour le garder |
|---|---|---|
| La shadda d'assimilation de la première lettre | `لَّا` → `لَا` | `assimilation_marks_in_form: true` |
| Les signes de la dernière lettre : voyelle, tanwīn, sukūn, petit wāw ou yāʾ | `يَقْدِرُ` → `يَقْدِر` | `final_vowel_in_form: true` |
| Le tanwīn écrit avant son alif | `رِزْقًا` → `رِزْقا` | idem |
| La voyelle de cas avant un pronom complément collé | `رَبَّكَ` → `رَبّك` | idem |

Ne sont pas retirés : la shadda et l'alif suscrit de la dernière lettre, la voyelle d'un
mot d'une seule lettre. Ce qui est retiré est stocké (`units.stem_vowel`,
`units.final_vowel`) et reste affichable. Détail et points à confirmer : QUESTIONS.md, Q21
et Q27.

Les quatre niveaux du SPEC §3 correspondent donc à : `text_raw` (brut), niveau 1 (sans
signes de récitation), `units.form` (sans voyelle finale), `units.skeleton` (squelette).
