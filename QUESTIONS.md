# QUESTIONS.md — Questions de méthode ouvertes

Règle (CLAUDE.md) : en cas de doute sur la méthode, on ne tranche pas seul. La question
est notée ici et le programme applique le paramètre par défaut, réglable dans `config.yaml`.

**Position de l'équipe au 2026-10-10** : les résultats attendus ne sont pas certains.
Les questions Q1, Q2, Q7 et Q8 restent des problématiques ouvertes. Conséquence pour le
harnais : les chiffres du document de recherche servent de **points de comparaison**,
pas de résultats à atteindre. Quand un réglage change un résultat, le harnais affiche le
résultat sous chaque réglage, côte à côte, sans en choisir un.

| N° | Sujet | Défaut appliqué | État |
|---|---|---|---|
| Q1 | Définition du segment | pauses strictes + fin de verset | ouverte |
| Q2 | Définition de la forme de référence | mot écrit, clitiques collés | ouverte |
| Q3 | Échelle d'équivalence 0 à 3 | identité = 0 ; similarité = 1 à 3 | ouverte |
| Q4 | Cas non tranchés de la comparaison | voir détail | ouverte |
| Q5 | Forme seule / comparaison entre formes | aucun modèle imposé | ouverte |
| Q6 | Sources et format des lectures | écarts de lettres avec 7 riwāyāt ; analyse sur Hafs | ouverte |
| Q7 | Homographes sans voyelles | pas de fusion silencieuse | ouverte |
| Q8 | Cas de test en orthographe courante | cas stockés par références | ouverte |
| Q9 | MASAQ sans racines | contrôle croisé limité aux clitiques | ouverte |
| Q10 | Contrôle aléatoire | permutation du SPEC | ouverte |
| Q11 | Identifiants de mots entre sources | positions du texte Tanzil 1.1 | ouverte |
| Q12 | Assimilations entre mots dans la vocalisation | aucune neutralisation | ouverte |
| Q13 | Mots à deux radicaux dans le corpus | racine et lemme du premier radical | ouverte |
| Q14 | Ce qui compte comme clitique (article, pronoms) | article gardé, pronom sujet gardé | ouverte |
| Q15 | « قوم environ 150 fois » | aucun réglage ne donne ce chiffre | ouverte |
| Q16 | Marques de pause particulières (∴ ∴, sakt) | ne ferment pas de segment | ouverte |
| Q17 | Contenu des blocs A et B de la fiche | interprétation de l'étape 5 | ouverte |
| Q18 | Choix de l'interface web | FastAPI + une page ; PDF par impression | ouverte |
| Q19 | Aide de l'IA : garde-fous du résumé | faits seuls, chaque phrase vérifiée | ouverte |
| Q20 | Quelle واو est « de conjonction » (D-02) | étiquette CONJ, en tête de mot seulement | défaut accepté par l'utilisateur (2026-10-12) |
| Q21 | Signes d'assimilation dans la forme (D-03) | rangés parmi les signes de récitation | ouverte |
| Q22 | « Même base » sans lemme (E1, E2) | radical du corpus, sans les signes de sa dernière lettre | ouverte |
| Q23 | Cas 4 et 5 du SPEC §2.11 contre la règle R2 | règle du §2.3 (hors pivot) | ouverte |
| Q24 | Les 8 comparaisons du document | stockées par références | ouverte |
| Q25 | Gabarit attendu et découpage (D-01) | colonnes en plus listées | ouverte |
| Q26 | باب du ثلاثي مجرد et وزن des noms (niveau 0) | lu sur le الشكل, sinon « non déterminé » | ouverte |
| Q27 | Ce qui compte comme « voyelle finale » (D-04) | signes de la dernière lettre, et voyelle de cas avant un pronom collé | confirmée par l'utilisateur (2026-10-12) |
| Q28 | Types de noms que le corpus ne donne pas (niveau 0) | seuls les cas écrits dans le SPEC ; sinon « نوع غير محدد » | ouverte |

**Mise à jour du 2026-10-12 (spécification v12).** Le tableau ci-dessus et le détail
ci-dessous décrivent le code 0.9.0, bâti sur la spécification v0. Correspondance avec
`DECISIONS.md`, qui l'emporte :

| Question | Réglée ou reprise par | Conséquence |
|---|---|---|
| Q1, Q16 | D-01 (ouverte) | segments du mushaf Hafs pour toutes les riwāyāt ; strict / souple reste à décider |
| Q2 | **D-02 (tranchée)** | `match_level: 1` écarté ; seule la واو de conjonction est à part |
| Q3, Q4 | SPEC §2.2 et §2.3, D-06 | échelle 0 à 3 remplacée par E0–E4 ; le pivot ne compte plus parmi les éléments communs (voir Q23) |
| Q5 | D-13, D-17, D-19 | comparaison des formes d'une même racine seulement |
| Q6 | D-12 (ouverte) | inchangé |
| Q7 | D-03 (ouverte), **D-04 (tranchée)** | le الشكل intérieur sépare les homographes, sans lemme |
| Q12 | D-03, D-04 | voyelle finale séparée ; reste Q21 |
| Q13 | règle 4 de CLAUDE.md | plus de lemme ; un mot reste rangé sous chacune de ses racines |
| Q14 | **D-02 (tranchée)** | aucun pronom ni lettre retirés ; niveaux `noyau` et `nu` écartés |
| Q17 | SPEC étape 5, §2.4 | bloc C = familles, gabarits, matrices, usages isolés |
| Q18 | D-17 | la comparaison de deux racines sort de l'interface |
| « Document de recherche absent » | CHANGELOG v10 | présent : `docs/document_de_recherche.pdf` |

Le plan de passage du code à la nouvelle spécification est dans `docs/PLAN_ADAPTATION.md`.
Les questions Q20 à Q26 sont détaillées à la fin de ce fichier.

---

## Questions issues du SPEC §6

### Q1 — Définition exacte du segment (المقطع)
Faut-il suivre strictement les marques de وقف du Mushaf, et à quel niveau de pause ?

Observation (de mémoire, à vérifier sur le texte) : certains exemples du SPEC §2 ne
semblent pas délimités par des marques de pause, par exemple
`عبدا مملوكا لا يقدر على شيء`, qui serait un fragment au milieu d'un verset.

- **Défaut** : `segmentation.scheme = waqf`, `pause_level = strict`.
- **Ce que fait le harnais (étape 4)** : trois découpages coexistent dans la base, et
  `config.yaml` dit lequel les analyses utilisent.

  | Découpage | Ferme un segment | Segments | Mots par segment (moyenne) |
  |---|---|---|---|
  | `aya` | la fin du verset | 6 236 | 12,4 |
  | `waqf-strict` | fin de verset, pause obligatoire (م) ou préférable (قلى) | 6 861 | 11,3 |
  | `waqf-souple` | les mêmes, plus pause permise (ج) et continuation préférable (صلى) | 10 515 | 7,4 |

  La marque `لا` (pause interdite) ne ferme jamais de segment. Le sens des marques vient
  de la documentation Tanzil (https://tanzil.net/docs/pause_marks).

- **Résultat : où tombent les phrases du SPEC §2** (commande `exemples`, vérifié par
  un test). Sept des huit phrases sont retrouvées dans le texte :

  | Phrase | Passage | `aya` | `waqf-strict` | `waqf-souple` |
  |---|---|---|---|---|
  | 1a `قل إن ربي … من عباده ويقدر له` | 34:39, mots 1-11 | à l'intérieur | à l'intérieur | **égal** |
  | 2a `قل إن ربي … لمن يشاء ويقدر` | 34:36, mots 1-8 | à l'intérieur | à l'intérieur | à l'intérieur (segment 1-13) |
  | 2b `إن ربك يبسط … ويقدر` | 17:30, mots 1-7 | à l'intérieur | à l'intérieur | **égal** |
  | 3a `لا يقدرون مما كسبوا على شيء` | 14:18, mots 13-18 | à l'intérieur | à l'intérieur | **égal** |
  | 3b `لا يقدرون على شيء مما كسبوا` | 2:264, mots 28-33 | à l'intérieur | à l'intérieur | **égal** |
  | 4a `أيحسب أن لن يقدر عليه أحد` | 90:5, mots 1-6 | **égal** | **égal** | **égal** |
  | 4b `عبدا مملوكا لا يقدر على شيء` | 16:75, mots 4-9 | à l'intérieur | à l'intérieur | à l'intérieur (segment 1-19) |

  Lecture de ce tableau :
  - Le découpage du document ressemble au réglage **souple** : cinq phrases sur sept
    y sont exactement un segment. Avec le réglage strict (défaut du SPEC), une seule.
  - Deux phrases (2a et 4b) ne sont un segment sous aucun réglage : ce sont des
    extraits. Aucune marque de pause ne les délimite dans le texte.
  - Aucune phrase n'est à cheval sur deux segments.
  - Le défaut n'a pas été changé : c'est à l'équipe de choisir entre strict et souple,
    et de dire comment traiter les extraits.

### Q2 — Forme de référence
Le document dit « comme dans le mufahras » mais garde les clitiques collés.

Observation : avec le mot écrit comme clé, `ويقدر` et `يقدر` sont deux formes
différentes, et le critère « `يقدر` dans 12 versets » (SPEC §5 étape 3, §7) ne peut
probablement pas être atteint.

- **Défaut** (SPEC) : `reference_form.match_level = 0` (mot écrit).
- **Alternative proposée** : `match_level = 1` (mot sans proclitiques ni pronoms
  compléments), l'élément de comparaison restant le mot entier (règle 3 inchangée).
- **Ce que fera le harnais** : l'étape 3 donne les comptages sous les deux réglages.
- **Vérifié à l'étape 2** : le corpus coupe bien les pronoms sujets (`يقدرون` →
  `يقدر` + `ون`, étiqueté `PRON` comme un pronom complément). Il faudra donc une règle
  explicite pour ne pas confondre `يقدرون` et `يقدر`. MASAQ distingue les deux
  (`SUBJ_PRON`) et pourra servir de contrôle.
- **Résultat de l'étape 3** (commande `forme يقدر`, vérifié par un test) :

  | Réglage | Occurrences de `يقدر`, lemme `قَدَرَ` | Versets |
  |---|---|---|
  | mot écrit (`match_level: 0`, défaut du SPEC) | 3 | 16:75, 16:76, 90:5 |
  | sans clitiques (`match_level: 1`) | 12 | 13:26, 16:75, 16:76, 17:30, 28:82, 29:62, 30:37, 34:36, 34:39, 39:52, 42:12, 90:5 |

  Le chiffre de 12 versets du document correspond donc au réglage « sans clitiques »,
  pas au défaut du SPEC. Le défaut n'a pas été changé : c'est à l'équipe d'en décider.

### Q3 — Échelle d'équivalence
Les niveaux 0 à 3 (mot identique / sans clitiques / même lemme / même racine) sont une
interprétation de l'équipe. Correspondent-ils à l'intention de l'auteur ?

- **Défaut** : identité = niveau 0 ; similarité = niveaux 1 à 3.
- **Tel que réalisé à l'étape 5** (`src/quran_harness/compare.py`) : deux mots sont
  équivalents au premier niveau qui tient.

  | Niveau | Condition | Exemple tiré des cas du SPEC |
  |---|---|---|
  | 0 | même mot écrit, même lemme | `يَقْدِرَ` et `يَقْدِرُ` (comparaison sans voyelles) |
  | 1 | même mot une fois les clitiques retirés, même lemme | `رَبِّى` et `رَبَّكَ` |
  | 2 | un lemme en commun | `عَلَيْهِ` et `عَلَىٰ` |
  | 3 | une racine en commun | — |

  Le lemme est exigé aux niveaux 0 et 1 pour que deux mots différents écrits pareil ne
  soient jamais confondus (Q7). `عليه` et `على` tombent au niveau 2 et non au niveau 1
  parce que, clitique retiré, ils s'écrivent `علي` et `على`.

### Q4 — Cas non tranchés par le document
Segments de longueurs différentes, ordre différent, comparaison vue comme fonction
mathématique.

Points précis à trancher :
- La forme de référence compte-t-elle parmi les « 2 éléments » requis ? (Le cas 4 du
  SPEC §2 suggère que oui pour la similarité.)
- Une paire peut cumuler identité partielle et similarité partielle (cas 2). Le résultat
  d'une comparaison est donc une description à plusieurs composantes, pas une étiquette
  unique.
- Blocs identiques dans un ordre différent (cas 3) : identité ou similarité ?

- **Défaut** : la forme de référence compte ; la relation stockée liste toutes ses
  composantes ; les blocs déplacés sont signalés comme « identiques, ordre différent ».
- **Tel que réalisé à l'étape 5** :
  - Les blocs identiques (au moins 2 mots consécutifs) sont cherchés où qu'ils soient
    dans chaque passage, du plus long au plus court. L'alignement par plus longue
    sous-séquence commune conseillé par le SPEC ne retrouvait pas les blocs déplacés
    du cas 3 ; je l'ai remplacé par cette recherche.
  - Les mots restants sont appariés un à un, du niveau le plus fort au plus faible.
  - La relation se lit ensuite : identité totale si un seul bloc couvre les deux
    passages ; identité partielle s'il y a au moins un bloc ; similarité s'il n'y a pas
    de bloc mais au moins 2 mots communs ; différence sinon.
  - Une comparaison décrit toujours tout : blocs, mots communs hors blocs avec leur
    niveau, mots en plus de chaque côté, ordre conservé ou non.
- **Résultat sur les cas du SPEC §2** (commande `comparer`, vérifié par des tests) :

  | Cas | Passages | Attendu par le SPEC | Obtenu |
  |---|---|---|---|
  | 1 | — | identité partielle, 2 parties | **suspendu** : une des deux phrases n'existe pas dans le texte (Q8) |
  | 2 | 34:36:1-8 et 17:30:1-7 | identité partielle + `ربي`/`ربك` + un élément en plus | identique : bloc de 5 mots, `ربي`~`ربك` au niveau 1, `قل` en plus |
  | 3 | 14:18:13-18 et 2:264:28-33 | mêmes blocs, ordre différent | identique : 3 blocs de 2 mots, ordre différent |
  | 4 | 90:5:1-6 et 16:75:4-9 | similarité `على`~`عليه` + éléments différents | identique : pas de bloc, `يقدر` et `على`~`عليه` communs |

  La structure du cas 1 (deux blocs identiques autour de mots en plus) est vérifiée sur
  des éléments abstraits, sans texte coranique fabriqué.
  Les « 8 comparaisons du document » ne sont pas vérifiées : je n'ai pas le document.

### Q5 — Forme seule et comparaison entre formes
Le document dit qu'il n'y a pas encore de vision claire.

- **Défaut** : aucun modèle imposé ; les deux analyses sont produites séparément.

### Q6 — Lectures (القراءات)
**Historique.** L'équipe avait d'abord décidé de ne travailler que sur Hafs
(2026-10-10), puis a demandé de passer à l'étape 7. L'étape est donc faite, mais
seulement dans la mesure où les données le permettent ; l'analyse elle-même reste sur
le texte Hafs.

**Ce qui a été fait à l'étape 7** (`src/quran_harness/readings.py`) :

- Chaque fichier de riwāya est aligné sur le texte de base, sourate par sourate, sur
  le **squelette** des mots : leurs lettres, conventions d'écriture neutralisées
  (formes de hamza, `ى`/`ي`, alif suscrit ou écrit, alifs répétés).
- Les écarts sont rangés dans la table `variants` : `lettres` (un mot, d'autres
  lettres), `mots` (un groupe de mots remplacé), `mot_en_plus`, `mot_en_moins`, et
  `verset_absent` (verset absent du fichier : affaire de numérotation, pas de lecture).
- La table `riwaya_ayas` relie chaque verset d'une riwāya, dans sa propre
  numérotation, aux mots du texte de base.
- La fiche a un bloc D : pour chaque compagnon, dans combien de riwāyāt l'association
  est inchangée, et quels écarts la touchent.

| Riwāya | Versets | Écarts de lettres | Autres écarts |
|---|---|---|---|
| hafs (étalonnage) | 6 236 | 0 | 0 |
| shouba | 6 236 | 110 | 0 |
| warsh | 6 214 | 247 | 3, plus la basmala de la sourate 1 absente du fichier |
| qaloon | 6 214 | 237 | 3, plus la basmala |
| doori | 6 217 | 194 | 3, plus la basmala |
| soosi | 6 217 | 216 | 3, plus la basmala |
| bazzi | 6 220 | 209 | 3 |
| qumbul | 6 220 | 205 | 2 |

**Ce qui valide la méthode :**
- Le fichier Hafs du même éditeur, aligné de la même façon, ne montre **aucun** écart
  avec le texte de base : la méthode ne fabrique pas d'écarts là où il n'y en a pas.
- Pour les 8 fichiers, « texte de base + écarts » redonne le fichier lettre pour
  lettre, et le retour au texte de base est exact (critère de validation du SPEC).
- Chaque verset de chaque riwāya correspond à une suite de mots du texte de base.

**Ce qui n'a pas été fait, et pourquoi :**
- **Les écarts de voyelles et de prononciation ne sont pas relevés.** Chaque fichier
  est écrit pour sa propre police : voyelles, hamzas et petits signes n'y sont pas
  codés de la même façon. Les comparer demanderait une table de correspondance par
  police que je n'ai pas, et que je ne veux pas deviner. Le SPEC demandait de stocker
  à part les variantes de prononciation : ce n'est pas possible avec ces données.
  Une variante qui ne change que les voyelles échappe donc au bloc D.
- **Le pipeline ne tourne pas sur les autres lectures.** Le SPEC voulait une « vue
  complète » par lecture. Il n'existe pas d'annotation (racine, lemme) pour les mots
  propres aux autres riwāyāt, et je n'en invente pas. Le bloc D dit seulement quels
  mots et quelles associations du texte Hafs sont touchés.
- **Une association qui apparaîtrait** dans une autre riwāya sans exister dans Hafs
  n'est pas détectée.
- **Les segments** sont ceux du texte Hafs ; les marques de pause des autres mushafs
  ne sont pas utilisées.

**Résidus connus dans la table `variants` :**
- Deux passages de type `mots` tiennent à l'écriture, pas à la lecture : `وَأَلَّوِ` /
  `وَأَن لَّوِ` (72:16, dans 4 riwāyāt) et `أَن لَّن` / `أَلَّن` (73:20, dans 2).
- Des alifs répétés sont comptés pour un seul : un écart qui ne tiendrait qu'à cela
  serait manqué.
- Quelques écarts de lettres viennent d'un alif long (`مَٰلِكِ` / `مَلِكِ`, 1:4) :
  ce sont bien des lectures différentes, mais repérées par l'écriture.

**Questions qui restent :**

Format et sources utilisables pour les variantes.

- Le SPEC parle de « 7 lectures » mais la table `riwayat` cite Hafs et Warsh, qui sont
  des riwāyāt (transmissions). Quel est le grain voulu : 7 lectures, 10, ou une liste
  de riwāyāt ?
- Les textes téléchargés (voir `data/SOURCES.md` §5) couvrent 8 riwāyāt de 4 lecteurs
  seulement : Hafs et Shuʿba, Warsh et Qālūn, al-Dūrī et al-Sūsī, al-Bazzī et Qunbul.
  Il manque Ibn ʿĀmir, Ḥamza et al-Kisāʾī. Cela suffit-il ?
- Ce sont des textes complets, pas des tables de variantes. Les variantes seraient
  calculées par différence, après examen de l'encodage propre à chaque fichier.
- La numérotation des versets diffère (6 236, 6 214, 6 217 ou 6 220 versets selon la
  riwāya) : une table de correspondance est à construire.
- Les marques de pause diffèrent d'un mushaf à l'autre : les segments d'une autre
  lecture sont-ils ceux de Hafs, ou les siens ?

- La licence des fichiers n'est pas déclarée, et leur fidélité à la source d'origine
  (Complexe du Roi Fahd) n'a pas été vérifiée : je les ai pris sur un dépôt GitHub.
- **Défaut** : l'analyse reste sur Hafs ; le bloc D est informatif.

---

## Questions ajoutées à la lecture du SPEC

### Q7 — Homographes sans voyelles
Sans voyelles, `يقدر` recouvre deux mots de lemmes différents : `قَدَرَ` (12 versets,
voir Q2) et `قَدَّرَ` (un seul verset, 73:20). Vérifié dans la base le 2026-10-10.

- Quel niveau de normalisation définit « la même forme » : avec voyelles, sans voyelles,
  sans voyelles mais départagé par le lemme ?
- **Défaut** : quand une saisie sans voyelles correspond à plusieurs lemmes, le harnais
  liste les candidats avec leurs comptages et n'en fusionne aucun.

### Q8 — Cas de test en orthographe courante, sans références
Les cas du SPEC §2 sont écrits sans voyelles, en orthographe courante et sans référence
sourate:verset, alors que le texte de base est ʿuthmānī.

- **Défaut** : chaque cas de test est stocké par références (sourate:verset, mot de
  début, mot de fin) ; la phrase du document n'est qu'un libellé.
- Un cas dont la phrase n'est pas retrouvée dans le texte est suspendu et signalé ici,
  jamais adapté.
- **Fait à l'étape 4** : les phrases sont dans `data/reference/spec_examples.yaml` et
  leurs références sont calculées par recherche dans le texte Tanzil en orthographe
  courante (tableau en Q1).
- **Phrase introuvable** : la seconde phrase du cas 1,
  `قل إن ربي يبسط الرزق لمن يشاء ويقدر له`, n'existe pas telle quelle dans le texte.
  Le texte a `… لمن يشاء من عباده ويقدر له` (34:39) et `… لمن يشاء ويقدر` sans `له`
  (34:36). Le cas 1 du SPEC est donc suspendu : quelle paire de passages le document
  compare-t-il ?
- **Limite** : trois versets (20:94, 38:26, 72:16) ne s'alignent pas entre les deux
  graphies ; une phrase qui s'y trouverait ne serait pas placée, et serait signalée.

### Q9 — MASAQ ne contient ni racine ni lemme
Constat à la réception du fichier (voir `data/SOURCES.md` §1). Le « contrôle croisé des
racines » du SPEC §3 et la comparaison QAC / MASAQ de l'étape 3 ne sont pas faisables
tels quels.

- **Défaut** : MASAQ sert au contrôle croisé du découpage des clitiques uniquement.
- Une seconde source de racines a été téléchargée : `quran-morphology` (mustafa0x), une
  version corrigée du QAC. Elle n'est pas indépendante du QAC : seuls ses désaccords
  avec lui sont informatifs. Faut-il chercher une source de racines vraiment
  indépendante ?
- **Résultat de l'étape 3** (table `root_differences`) : une fois la hamza écrite de la
  même façon dans les deux sources, la version corrigée change la racine de 757 mots
  sur 77 429 :

  | Écart | Mots | Principaux cas |
  |---|---|---|
  | racine ajoutée | 374 | `أيي` (215), `يوم` dans `يومئذ` (70), `أدم` (25) |
  | racine changée | 310 | `نوس` → `أنس` pour `ٱلنَّاس` (241), `ندو` → `ندي` (53) |
  | racine retirée | 73 | `اول` (45), `اني` (28) |

  L'index suit le QAC d'origine. Faut-il adopter certaines de ces corrections, par
  exemple pour `ٱلنَّاس` ?

### Q10 — Contrôle aléatoire
Le mélange de tous les mots entre segments (SPEC étape 6) détruit aussi la grammaire et
l'ordre des mots : presque toute association risque de sortir « significative ».

- **Défaut** : permutation du SPEC.
- **Compléments proposés** : un second contrôle plus strict (mélange à l'intérieur de la
  sourate), une correction pour tests multiples, un seuil de fréquence minimale, un
  signalement des versets-refrains.
- **Tel que réalisé à l'étape 6** (`src/quran_harness/stats.py`, section `statistics`
  de `config.yaml`) :

  | Élément | Choix | Paramètre |
  |---|---|---|
  | Unité | le segment : on compte les segments qui contiennent la forme et son compagnon | découpage retenu |
  | Mesures | PMI et log-vraisemblance (G²), affichées à titre descriptif | — |
  | Contrôle du SPEC | mots mélangés dans tout le texte, tailles des segments conservées | `controls: corpus` |
  | Contrôle plus strict | mots mélangés à l'intérieur de chaque sourate | `controls: sura` |
  | Nombre de mélanges, graine | 1 000, graine 20261010 | `permutations`, `seed` |
  | Tests multiples | correction de Benjamini-Hochberg sur les compagnons de la fiche | `alpha: 0.05` |
  | Seuil de rareté | moins de 2 segments communs : « trop rare pour conclure » | `min_cooccurrence` |

  Ce que la fiche affiche pour chaque compagnon : « au-dessus du hasard », « attendu par
  la seule fréquence du mot », ou « trop rare pour conclure ». La mention porte sur le
  contrôle du SPEC ; si le contrôle par sourate ne suit pas, c'est dit.

- **Résultat pour `يقدر`** (sans clitiques, découpage souple, 1 000 mélanges) :

  | Compagnon | Segments communs (sur 12) | Segments du mot dans le texte | Attendu | Lecture |
  |---|---|---|---|---|
  | `يشاء` | 9 | 104 | 0,17 | au-dessus du hasard |
  | `يبسط` | 9 | 10 | 0,02 | au-dessus du hasard |
  | `ٱلرزق` | 9 | 13 | 0,01 | au-dessus du hasard |
  | `ٱلله` | 7 | 2 363 | 3,09 | au-dessus du hasard |
  | `رب` | 3 | 915 | 1,40 | attendu par la seule fréquence du mot |
  | `شىء` | 2 | 196 | 0,30 | attendu par la seule fréquence du mot (p corrigée 0,064) |

  **L'association `يقدر` – `شيء` ne passe pas le seuil.** Elle ne repose que sur 2
  segments (16:75 et 16:76). Elle est plus nette pour la forme voisine : `شيء` est avec
  `يقدرون` dans ses 3 segments. La question est donc de savoir si le document associe
  `شيء` à la forme `يقدر` ou au verbe dans son ensemble.

- **Limites, à connaître avant de lire une « significativité »** :
  - Le mélange casse aussi la grammaire : un mot qui suit toujours un autre par simple
    construction (`لمن` avant `يشاء`) sort « au-dessus du hasard ». Le contrôle dit
    « plus souvent qu'un tirage au sort », pas « lien de sens ».
  - Les versets répétés presque mot pour mot pèsent chacun pour un segment : 9 des 12
    segments de `يقدر` sont la même formule. Le bloc C les montre regroupés.
  - Avec 1 000 mélanges, la plus petite p possible est 0,001.
  - La correction porte sur les compagnons d'une fiche, pas sur l'ensemble des fiches
    qu'on pourrait consulter.

### Q11 — Identifiants de mots : les sources ne découpent pas pareil
Constats (détail dans `data/SOURCES.md`, « Comptages à la réception ») :

- Tanzil place la basmala au début du verset 1 de 112 sourates ; le QAC ne la compte pas.
- Dans 4 versets, le QAC compte un seul mot là où le texte en écrit deux : `بَعْدَ مَا`
  (2:181, 8:6, 13:37) et `إِلْ يَاسِينَ` (37:130). Les positions de mots y sont décalées.
- L'orthographe simple a un mot de plus dans 363 versets (`يا أيها` contre `يَٰٓأَيُّهَا`).

Questions :
- La basmala en tête de sourate fait-elle partie du texte analysé ?
- Quelle source fixe la position des mots dans `sourate:verset:position_mot` ?

- **Défaut appliqué à l'étape 2** :
  - Les positions sont celles du texte Tanzil 1.1 (texte de base).
  - La basmala de tête de sourate est rangée sous le numéro de verset 0
    (`2:0:1` à `2:0:4`), sans annotation. Les analyses l'excluront par défaut.
  - Chaque mot garde dans `qac_ref` sa position dans le corpus. Pour `بَعْدَ مَا`, les
    deux radicaux du corpus sont répartis sur les deux mots. Pour `إِلْ يَاسِينَ`, les deux
    mots partagent la même annotation (un nom propre, sans racine).

### Q12 — La vocalisation ʿuthmānī marque les assimilations entre mots
Constat à l'étape 2. Un même mot ne s'écrit pas toujours pareil : sa première et sa
dernière lettre changent de signes selon le mot voisin. Exemple, le mot écrit `من`
(niveau 1, sans signes de récitation) :

| Graphie | Occurrences | Graphie | Occurrences |
|---|---|---|---|
| `مِن` | 859 | `مِّنْ` | 149 |
| `مِّن` | 412 | `مَنْ` | 73 |
| `مِنَ` | 412 | `مَّن` | 49 |
| `مِّنَ` | 281 | `مَّنْ` | 24 |
| `مِنْ` | 253 | `مَنِ` | 19 |
| `مَن` | 226 | autres | 6 |

- 3 722 mots commencent par une lettre portant une shadda d'assimilation.
- Le texte compte 18 384 formes distinctes au niveau 1, et 14 814 au niveau 2.

Conséquence : au niveau 0 de l'échelle d'équivalence (« mot strictement identique »),
`مِن` et `مِّن` seraient deux mots différents. Trois façons de faire, à choisir :
1. Ajouter un niveau de normalisation qui neutralise ces marques (shadda initiale,
   sukūn final). C'est une règle à écrire et à valider.
2. Comparer sur le texte Tanzil « Simple (Plain) », vocalisé sans ces marques. Son
   découpage en mots diffère dans 363 versets.
3. Comparer sans voyelles (niveau 2) en départageant par le lemme et les traits
   grammaticaux du corpus.

- **Défaut** : aucune neutralisation ; les trois niveaux du SPEC sont appliqués tels
  quels.
- **Ce que fait l'étape 3** : l'index compare les formes sans voyelles (niveau 2) et les
  sépare par lemme. Les assimilations n'y jouent donc aucun rôle.
- **Mesure faite à l'étape 3** : retirer la shadda initiale et le sukūn final ne
  regroupe que 619 des 18 384 graphies vocalisées (17 765 restent). L'essentiel de la
  variété vocalisée vient d'ailleurs : voyelles de cas et vraies différences de mots.
  La question pèse donc moins qu'attendu, et elle ne se reposera qu'à l'étape 5, si la
  comparaison de segments doit tenir compte des voyelles.

### Q13 — Mots à deux radicaux dans le corpus
486 mots ont deux radicaux dans le corpus, par exemple `مِمَّا` (préposition + relatif)
ou `إِنَّمَا`. Un seul mot a deux racines : `يَبْنَؤُمَّ` (20:94).

- Quel lemme représente un tel mot pour les niveaux 2 et 3 de l'échelle d'équivalence ?
- **Défaut** : les colonnes `root` et `lemma` de `words` portent ceux du premier radical
  qui en a ; tous les radicaux restent disponibles dans `word_segments`.
- **Dans l'index (étape 3)** : un mot est rangé sous chacune des racines qu'il porte.
  `يَبْنَؤُمَّ` apparaît donc sous `بني` et sous `امم`.

### Q14 — Ce qui compte comme clitique
Le SPEC parle de « retrait des clitiques » sans dire lesquels. L'étape 3 a dû fixer une
règle ; elle est dans `src/quran_harness/forms.py` et chaque point peut être discuté.

| Élément | Exemple | Traitement |
|---|---|---|
| Conjonction, préposition, particule collée devant | `وَ` de `وَيَقْدِرُ`, `لِ` de `لِقَوْمِهِ` | retirée |
| Pronom complément ou possessif | `هِ` de `قَوْمِهِ`, `كُمْ` de `خَلَقَكُمْ` | retiré |
| Pronom sujet | `ونَ` de `يَقْدِرُونَ` | **gardé** : il fait partie de la forme du verbe |
| Article `ال` | `ٱلْقَوْمِ` | **gardé** au niveau « noyau », retiré au niveau « nu » |
| Nūn d'insistance | `نَّ` de `لَتُبَيِّنُنَّهُ` | gardé |
| Préposition écrite avec un pronom | `لَهُ`, `بِهِ` | le mot retenu est la préposition (`لَ`, `بِ`) |

- **Pronom sujet ou complément** : le corpus ne les distingue pas. La règle utilisée est
  grammaticale (quelles personnes du verbe portent un pronom sujet attaché). Contrôle
  contre MASAQ : accord sur 76 549 mots sur 76 969 comparés ; les 420 désaccords sont
  dans la table `pronoun_checks`. Ceux que j'ai regardés viennent d'annotations absentes
  ou d'analyses différentes dans MASAQ (`فِيمَا`, `يَوْمَئِذٍ`, pronom `ي` non écrit), pas
  d'une erreur de la règle. Je ne les ai pas tous relus un par un.
- **Article** : `قوم` et `ٱلقوم` sont-ils la même forme ? Paramètre
  `reference_form.article_is_clitic`, faux par défaut.
- **Graphies** : le mot est toujours pris tel qu'écrit. Après `لِ`, l'alif de l'article
  ne s'écrit pas (`لِلْقَوْمِ` donne `لقوم`, pas `ٱلقوم`) ; le lemme les regroupe.

### Q17 — Contenu des blocs A et B de la fiche
Le SPEC nomme les blocs « A (carte d'identité) » et « B (compagnons) » sans les
détailler. Contenu retenu à l'étape 5, à confirmer :

- **A — carte d'identité** : la forme, son lemme et sa racine ; nombre d'occurrences,
  de versets et de segments ; graphies rencontrées ; position dans le segment (début,
  milieu, fin, seul) ; liste des segments avec la forme mise en évidence.
- **B — compagnons** : les autres mots des mêmes segments, en trois familles comme au
  SPEC §1 : (a) même racine, (b) autres racines, (c) lettres et pronoms. Pour chacun :
  occurrences, nombre de segments, avant ou après la forme, références. S'y ajoute ce
  qui est collé à la forme elle-même (par exemple le `و` de `ويقدر`).
- **Comparaison des segments** : toutes les paires de segments de la forme, avec leur
  relation et son détail. Je l'ai placée à la suite du bloc B.

- **C — usages regroupés par ressemblance** (étape 6) : les segments de la forme sont
  mis dans le même groupe quand une identité, totale ou partielle, les relie,
  directement ou par l'intermédiaire d'autres segments. Pour chaque groupe : ses
  segments et le bloc identique présent dans le plus de paires. Le paramètre
  `usage_groups.links` permet de relier aussi par similarité.
  Pour `يقدر` : trois groupes, de 9, 2 et 1 segments.
- **Deux formes côte à côte** (étape 6, commande `comparer-formes`) : chaque compagnon
  est rangé en « même forme associée », « même racine, formes différentes » ou
  « aucune ». Pour `يقدر` et `يقدرون` : 8, 5 et 51.

Limites connues :
- **Un groupe d'usages peut tenir par un intermédiaire** : deux de ses segments peuvent
  ne pas se ressembler directement.
- **Une forme sans racine n'a pas de fiche** (par exemple `على`) : l'index des formes
  repose sur les racines. À étendre si l'équipe veut étudier les lettres seules.
- **Les relations ne sont pas stockées dans la base** : elles sont calculées à la
  demande. Au-delà de `relations.max_pairs` paires (20 000, soit 200 segments), la
  fiche le dit et ne compare pas.
- **Les noms et verbes sans racine dans le corpus** (noms propres surtout) sont rangés
  en (b) avec une racine vide, pas parmi les lettres.

### Q19 — Aide de l'IA (étape 9, facultative)
Le SPEC demande que l'IA ne lise que des résultats déjà calculés, n'écrive jamais de
résultat qui ne vient pas du calcul, et que les sorties distinguent *calculé*, *cité
d'une source* et *note humaine*. Réalisation dans `src/quran_harness/assistant.py`, à
confirmer :

- **Le résumé part d'une liste de faits** : des phrases écrites par le programme à
  partir des nombres de la fiche (F1, F2…). Sans modèle, le résumé est cette liste.
  Il est donc toujours disponible, hors ligne et sans clé.
- **Trois origines, marquées sur chaque ligne** :

  | Marque | D'où vient la ligne | Qui l'écrit |
  |---|---|---|
  | calculé | un ou plusieurs faits, cités par leur numéro | le programme, ou le modèle sous contrôle |
  | cité d'une source | la provenance des données, lue dans la base | le programme |
  | note humaine | `data/notes.yaml`, avec auteur et date | une personne (commande `note`) |

  Le modèle n'écrit jamais de ligne « source » ni de « note humaine ».
- **Le modèle est facultatif** (option `--ia`, bouton « Reformuler avec un modèle »).
  Il reçoit les faits et la liste des formes candidates, rien d'autre : ni le texte des
  segments, ni la base. Il doit citer les faits derrière chaque phrase.
- **Chaque phrase rendue est vérifiée**, et écartée si :
  - elle ne cite aucun fait, ou cite un fait qui n'existe pas ;
  - elle contient un nombre absent des faits qu'elle cite ;
  - elle contient un mot arabe absent des faits qu'elle cite ;
  - elle emploie un mot d'interprétation (règle 4 de CLAUDE.md).

  Les phrases écartées sont affichées avec le motif. Si aucune ne passe, ou si le
  modèle est injoignable ou décline, le résumé revient aux faits bruts et le dit.
- **Formes à comparer** : les candidates sont tirées de l'index de la racine (autres
  formes du même lemme, puis des autres lemmes). Le modèle ne peut que choisir dans
  cette liste.
- **Modèle** : `claude-opus-5-5` par défaut, réglable dans `config.yaml`
  (section `assistant`). Le paquet `anthropic` est une dépendance facultative
  (`uv sync --extra ia`) ; la clé se lit dans la variable `ANTHROPIC_API_KEY`.

Points à trancher ou à connaître :
- **La liste des mots d'interprétation refusés est mon choix** : `signifie`, `veut
  dire`, `sens`, `symbolise`, `exprime`, `désigne`, `évoque`, `suggère`, `implique`,
  `prouve`, `démontre`, `révèle`, `miracle`, `intention`, `parce que`, `car`, `donc`.
  Elle est volontairement large : elle peut écarter une phrase correcte (« dans le même
  sens »). À ajuster.
- **La vérification porte sur les nombres et les mots arabes, pas sur le sens de la
  phrase.** Une phrase peut citer les bons nombres et les relier de travers (« 9 fois
  avant » dit « 9 fois après »). Le numéro du fait permet de contrôler à la main.
- **Un nombre écrit en lettres n'est pas vérifié** ; la consigne demande des chiffres.
- **L'appel réel au modèle n'a jamais été exécuté** : aucun identifiant Anthropic n'est
  configuré sur le poste. Les tests remplacent le modèle par un simulacre, et vérifient
  la forme de la requête envoyée et le traitement des réponses, bonnes ou mauvaises.
- **Avec `--ia`, les faits partent vers un service extérieur** (l'API Anthropic) : des
  comptages, des mots du texte et les paramètres de la fiche. Rien n'est envoyé sans
  cette option.
- **Les notes humaines** sont dans `data/notes.yaml`, hors de la base : elles survivent
  à une reconstruction. Une note peut être limitée à un lemme quand deux mots
  s'écrivent pareil.

### Q18 — Interface web (étape 8)
Le SPEC laissait le choix entre Streamlit et « FastAPI + page légère ». Choix faits, à
confirmer :

- **FastAPI et une seule page**, sans ressource extérieure : la page fonctionne hors
  ligne et affiche l'arabe de droite à gauche avec les polices du poste.
- **Les mêmes fonctions que la ligne de commande** : la page ne calcule rien
  elle-même, et un test vérifie qu'elle rend la même fiche que la commande `fiche`.
- **Chaque ligne se déplie** : un segment montre ses mots avec leurs références ; un
  compagnon montre les segments où il se trouve, la forme et lui surlignés ; une
  comparaison montre les deux segments avec leurs blocs.
- **Recherche par forme ou par racine.** Une fiche de racine réunit tous les mots de
  la racine, toutes formes confondues. La comparaison de deux racines (par exemple
  `قلب` et `فؤاد`) porte sur leurs compagnons.
- **Export CSV** pour chaque tableau ; chaque ligne porte la lecture, le niveau de
  forme, le découpage et la version du code.
- **Export PDF par l'impression du navigateur** (bouton « Imprimer / PDF »). Produire
  un PDF côté serveur avec de l'arabe correctement ligaturé demanderait des composants
  supplémentaires ; je ne l'ai pas fait.
- **Le contrôle aléatoire est décoché par défaut**, parce qu'il prend environ 30
  secondes. Sans lui, la page le dit : les nombres sont de simples comptages.
- **Lecture** : seul Hafs est proposé ; les autres riwāyāt n'apparaissent que dans le
  bloc D (Q6).

Limites :
- Une racine très fréquente donne des tableaux de plusieurs centaines de lignes, et ses
  segments ne sont pas comparés deux à deux au-delà de la limite `relations.max_pairs`.
- La page n'a pas d'authentification : elle est faite pour tourner sur le poste de
  travail (`127.0.0.1`), pas pour être exposée sur un réseau.

### Q16 — Marques de pause particulières
- **Paire de trois points (∴ ∴, muʿānaqa)** : on s'arrête à l'une des deux marques, pas
  aux deux. Elle figure dans 6 versets (2:2, 2:195, 5:26, 5:41, 7:172, 14:9). Couper à
  la première ou à la seconde change le segment de quelques mots.
  **Défaut** : `segmentation.muanaqa = none`, on ne coupe à aucune des deux.
- **Petit sīn (sakt)** : courte silence sans reprise de souffle, 5 occurrences. La
  documentation Tanzil ne le compte pas parmi les marques de pause.
  **Défaut** : il ne ferme pas de segment.
- **Basmala de tête de sourate** : elle forme un segment à part (verset 0), pour que
  chaque mot ait un segment ; les analyses l'excluent (Q11).

### Q15 — « قوم environ 150 fois » (SPEC §5, étape 3)
Aucun réglage ne donne ce chiffre. Comptages de l'index (lecture Hafs) :

| Ce qu'on compte | Occurrences | Versets |
|---|---|---|
| Lemme `قَوْم`, toutes formes | 383 | 347 |
| Forme `قوم`, mot écrit | 79 | 73 |
| Forme `قوم`, sans clitiques | 278 | 253 |
| Forme `قوم`, sans clitiques ni article | 343 | 312 |

Les mots écrits `قوم` (79) et `ٱلقوم` (62) font 141 à eux deux, ce qui s'approche de
150, mais rien ne dit que c'est le compte visé. Que compte exactement le document ?
Conformément au SPEC, l'écart est noté ici et aucun résultat n'a été forcé.

---

## Écarts constatés entre le SPEC et les sources

| Point | SPEC | Constaté le 2026-10-10 |
|---|---|---|
| Licence MASAQ | CC BY 3.0 | CC BY-NC 3.0 (version 6) |
| Licence Quranic Arabic Corpus | usage non commercial | GNU GPL + conditions (copie à l'identique, mention de la source) ; pas de clause non commerciale dans le fichier |
| Édition du texte Tanzil | Caire 1924 | Tanzil le décrit comme conforme au Mushaf de Médine |
| Version du texte | une seule | Tanzil 1.1 téléchargé ; le QAC est bâti sur Tanzil 1.0.2 |
| MASAQ | contrôle croisé des racines | ni racine ni lemme dans le fichier |
| Lectures | « 7 lectures » | 8 riwāyāt de 4 lecteurs disponibles |
| Document de recherche | référence de validation | absent du projet, introuvable en ligne |

Décision de l'équipe (2026-10-10) : projet de recherche open source, sans usage
commercial ; les clauses « pas d'usage commercial » ne sont pas bloquantes.

---

## Questions nées de la spécification v12 (2026-10-12)

Constats faits par requêtes en lecture seule sur la base 0.9.0 et par lecture du
document. Aucun code n'a été modifié. Détail et conséquences : `docs/PLAN_ADAPTATION.md` §2.

### Q20 — Quelle واو est « de conjonction » (D-02)
Le corpus étiquette la واو collée de six façons :

| Étiquette | Mots | En tête du mot | À l'intérieur (`أَوَلَمْ`…) |
|---|---|---|---|
| CONJ (عاطفة) | 8 177 | 8 173 | 4 |
| REM (استئنافية) | 1 034 | 1 034 | 0 |
| CIRC (حالية) | 293 | 292 | 1 |
| SUP (زائدة) | 59 | 8 | 51 |
| P (واو القسم) | 28 | 25 | 3 |
| COM (معية) | 3 | 3 | 0 |

- D-02 dit « وَ العاطفة ». Faut-il aussi séparer la واو الاستئنافية et la واو الحالية ?
  Le المعجم المفهرس ne les distingue pas.
- Une واو à l'intérieur d'un mot (`أَوَلَمْ`) : la séparer couperait le mot en trois.
- **Défaut** : `form.detached_waw_tags: [CONJ]`, en tête de mot seulement.
- **Vérifié** : les 9 `وَيَقْدِرُ` sont CONJ. Avec cette règle, le الشكل intérieur et la
  voyelle finale séparée, يَقْدِر est dans les 12 versets de la liste de D-02
  (`يُقَدِّرُ` de 73:20 est écarté par le الشكل).

### Q21 — Signes d'assimilation dans la forme (D-03, suite de Q12)
Avec le الشكل intérieur, `مِمَّا` (14:18:15) et `مِّمَّا` (2:264:32) sont deux formes ; de même
`لَا` (16:76:7) et `لَّا` (16:75:6), `مِنْ` et `مِن`. Le cas 3 du SPEC §2.11 attend pourtant
trois blocs identiques entre 14:18 et 2:264.

- La shadda d'assimilation sur la première lettre et le sukūn de la dernière lettre
  sont-ils des signes de récitation (hors de la forme) ou du الشكل (dans la forme) ?
- **Défaut** : `form.assimilation_marks_in_form: false` (signes de récitation).

### Q22 — « Même base » sans lemme (codes E1 et E2)
Sans lemme, la base doit se lire sur le mot. Radicaux donnés par le corpus :

| Paire du document | Radicaux | Ce qui les sépare |
|---|---|---|
| `على` / `عليه` | `عَلَىٰ` / `عَلَيْ` | la dernière lettre (`ى` / `ي`) et ses signes |
| `ربي` / `ربك` | `رَبِّ` / `رَبَّ` | la voyelle de cas, à l'intérieur du mot écrit |
| `الرزق` / `رزقا` | `رِّزْقَ` / radical avec tanwīn et alif | article, assimilation, tanwīn |

- **Défaut** : base = radical du corpus, comparé avec son الشكل sauf les signes de sa
  dernière lettre (voyelle de cas, tanwīn et son alif) ; `ى` et `ي` finaux tenus pour égaux.
- Cas que le SPEC ne prévoit pas : même base, **lettre** collée différente
  (`بربك` / `لربك`). **Défaut** : E2 avec la mention « lettre changée ».

### Q23 — Les cas 4 et 5 du SPEC §2.11 contredisent la règle R2 du §2.3
Règle du §2.3 : R2 = au moins 2 éléments communs **hors pivot**. Les cas 4 (90:5 / 16:75)
et 5 (`لا يقدر على شيء` / `ما يشاء ويقدر`) n'en ont qu'un chacun (`على` ~ `عليه` ;
`شيء` ~ `يشاء`) : la règle les classe R3, le tableau attend R2.

- Le document compte la forme de référence parmi les deux éléments.
- Mais si le pivot compte, 90:5 est relié à 16:75 et l'usage de سورة البلد n'est plus
  isolé, contre l'autre test du §2.11 et contre le document.
- **Défaut** : règle du §2.3 (`relations.pivot_counts: false`). Les cas 4 et 5 sont
  testés sur leurs opérations (O2-E1, O2-E3, O5) ; leur type R est affiché sous les deux
  réglages.

### Q24 — Les exemples du document sont des citations approximatives
- Les 8 comparaisons du document sont toutes écrites avec `من عباده`, y compris pour
  13:26, 17:30, 30:37, 39:52 et 42:12, qui ne l'ont pas dans le texte.
- Le cas 1 du SPEC (Q8) correspond à l'exemple 3 du document : 34:39 contre 34:36,
  avec `من عباده` en plus **et** `له` en plus.
- Le document compte « 9 usages proches, 2 proches (سورة النحل), 1 différent (البلد) » :
  c'est ce que donnait déjà le bloc C du code 0.9.0 (groupes de 9, 2 et 1, Q17).
- **Défaut** : chaque comparaison est stockée par références ; le libellé du document
  n'est qu'un libellé.

### Q25 — Le gabarit attendu dépend du découpage (D-01)
Avec le découpage souple, le segment de 34:36 est 1-13 (`… ويقدر ولكن أكثر الناس لا
يعلمون`). Le gabarit de la famille aura donc au moins une colonne facultative de plus que
celui du SPEC §2.11. Avec le découpage strict (défaut), les segments sont plus longs encore.
- **Défaut** : le test porte sur les colonnes attendues ; les colonnes en plus sont listées.

### Q26 — Ce que le corpus ne donne pas pour le niveau 0
Le corpus donne le وزن verbal (II à X), le temps, la voix, le mode, la personne, les
participes et le مصدر. Il ne donne ni le باب du ثلاثي مجرد ni le وزن précis des noms.
- **Défaut** : le باب est lu sur le الشكل quand le ماضي et le مضارع sont tous deux employés
  dans le Coran ; sinon il vient du dictionnaire, ou la case indique « non déterminé ».
- Sources du côté « possible » (générateur de تصريف, OpenITI, lisan345) : rien n'est
  téléchargé. lisan345 n'a pas de licence indiquée.

---

## Lot A et lot B réalisés (2026-10-12, code 0.10.0)

Accord de l'utilisateur du 2026-10-12 : plan des lots accepté ; défaut de Q20 accepté ;
téléchargements acceptés (lot F) ; la racine قدر n'est qu'un exemple de test, la démarche
doit valoir pour toute racine. Q21 et Q22 : pas de réponse, défauts appliqués comme
paramètres. Q23 : à réexpliquer, elle ne bloque que le lot D.

**Ce qui est fait** (`src/quran_harness/units.py`, `tests/test_units.py`) :

- Table `units` : les « cases ». Une case par mot ; deux cases quand le mot commence par
  une واو de conjonction (`34:36:8a` = `وَ`, `34:36:8b` = `يَقْدِرُ`). La table `words` et le
  texte brut ne changent pas ; un test vérifie que les cases d'un mot redonnent le mot.
- 86 054 cases pour 77 881 mots : 8 173 واو mises à part.
- Forme d'une case : الشكل intérieur, sans signes de récitation, sans voyelle finale.
  Ce qui est retiré est gardé à côté (`stem_vowel`, `final_vowel`).
  14 655 formes distinctes, pour 13 649 squelettes.
- Index des formes **sans lemme** : `racine` et `forme` lisent les cases. Une saisie sans
  voyelles qui recouvre plusieurs formes les liste séparément.
- Segments (lot B) : une case appartient au segment de son mot (vue `segment_units`).
  Les trois découpages gardent leur nombre de segments (6 236 / 6 861 / 10 515) ;
  moyenne de 13,7 / 12,5 / 8,1 cases par segment (contre 12,4 / 11,3 / 7,4 mots).

| Contrôle | Attendu | Obtenu |
|---|---|---|
| `يقدر` (D-02) | 12 versets de la liste | `يَقْدِر` : les 12 versets ; `يُقَدِّر` : 73:20 seul, à part |
| Racine قدر | 132 occurrences | 132, en 46 formes |
| `قوم` (Q15) | « environ 150 » | `قَوْم` : 87 occurrences ; l'écart demeure |

**Ce qui n'est pas encore fait** : l'ancienne fiche (`fiche`, `comparer`, `resume`,
interface web) tourne toujours sur l'ancien index, avec le lemme. Elle sera remplacée au
lot D. Les deux chemins coexistent jusque-là ; seuls `racine` et `forme` sont passés au
nouveau.

### Q27 — Ce que j'ai appelé « voyelle finale » (D-04)
D-04 dit que la voyelle finale (الإعراب) est séparée de la forme. Règle écrite dans
`normalize.split_final_vowel` et `units.form_of`, à confirmer :

| Cas | Exemple | Forme | Retiré |
|---|---|---|---|
| Voyelle, tanwīn ou sukūn de la dernière lettre | `يَقْدِرُ`, `شَىْءٍ` | `يَقْدِر`, `شَىْء` | `ُ`, `ٍ` |
| Tanwīn écrit avant son alif | `رِزْقًا`, `هُدًى` | `رِزْقا`, `هُدى` | `ً` ; l'alif, une lettre, reste |
| Voyelle de cas avant un pronom collé | `رَبِّى`, `رَبَّكَ` | `رَبّى`, `رَبّك` | `ِ` ; `َ` et `َ` |
| Petit wāw ou yāʾ du pronom | `لَهُۥ`, `عِبَادِهِۦ` | `لَه`, `عِبَاده` | `ُۥ` ; `ِ` et `ِۦ` |
| Shadda, alif suscrit | `رَبِّ`, `عَلَىٰ` | `رَبّ`, `عَلَىٰ` | la voyelle seule ; rien |
| Mot d'une seule lettre | `وَ`, `لَ` de `لَهُ` | inchangé | rien |

- La règle retire la dernière voyelle même quand ce n'est pas de الإعراب (`يَقْدِرُونَ` →
  `يَقْدِرُون`, `مِنَ` → `مِن`) : je ne sais pas les distinguer sans grammaire.
- Avant un pronom **sujet** rien n'est retiré (`خَلَقْتُ` et `خَلَقَتْ` restent deux formes).
  La distinction sujet / complément vient de la règle de Q14, contrôlée contre MASAQ.
- `رِزْقا` et `رِزْق` restent deux formes (une lettre de différence), comme le veut D-04
  pour `يقدرون` / `يقدروا`.

### Q21 — complément
La shadda d'assimilation de la première lettre est retirée (`لَّا` → `لَا`). Reste un cas du
même genre, **non traité** : `عَلَىٰ` (440 occurrences) et `عَلَى` (258), sans alif suscrit
devant un mot qui commence par un alif de liaison. Ce sont aujourd'hui deux formes.
Faut-il les réunir ?

---

## Décisions de l'utilisateur du 2026-10-12 (suite) et lot C

**Q20 — tranchée par l'utilisateur** : les **six** sortes de واو collée sont mises à part
(عاطفة، استئنافية، حالية، زائدة، قسم، معية), en tête de mot. 9 535 واو mises à part ;
87 416 cases. Reste la واو **à l'intérieur** d'un mot (`أَوَلَمْ`, 59 mots, presque toutes
زائدة) : elle reste dans son mot, car la séparer couperait le mot en trois. À confirmer.
*Écart avec `DECISIONS.md`* : D-02 n'y nomme que la واو de conjonction. J'applique la
décision donnée par l'utilisateur ; D-02 est à compléter côté conception.

**Q21 — tranchée par l'utilisateur** : `عَلَىٰ` et `عَلَى` sont réunis. Règle générale :
l'alif suscrit d'un ى final est retiré de la forme (il manque devant un alif de liaison :
`إِلَىٰ` / `إِلَى`, `مُوسَىٰ` / `مُوسَى`…). Même réglage que la shadda d'assimilation
(`form.assimilation_marks_in_form`). Formes distinctes : 14 383.

**Q27 — confirmée par l'utilisateur.**

**lisan345 — accord exprès de l'utilisateur** pour le télécharger malgré l'absence de
licence (lot F). À noter dans `data/SOURCES.md` au téléchargement.

**Q23 — décision de l'utilisateur, avec un doute** : la forme de référence **compte**
parmi les éléments communs. `على` ~ `عليه` sont متشابهتان (même base, E1) ; `شيء` ~ `يشاء`
le sont d'une autre façon (même racine ش ي أ, E3). Le code distingue déjà ces deux types.
Conséquence : les cas 4 et 5 du SPEC §2.11 sont R2, comme le tableau l'attend.
Reste le conflit avec « سورة البلد est un usage isolé » : 90:5 est désormais en تشابه
avec 16:75. **Ma proposition**, envoyée à l'utilisateur : garder le type R du document
pour décrire chaque paire, mais ne relier deux segments dans une famille que s'ils ont
au moins 2 éléments communs **hors pivot** (c'est exactement le seuil de D-08). Le
تشابه de 90:5 avec 16:75 reste visible dans les paires, sans fusionner les familles ;
les familles redonnent alors les groupes du document (9, 2 et 1). Paramètres prévus :
`relations.pivot_counts: true`, `families.link_min_common: 2`. En attente de réponse.

### Lot C réalisé : niveau 0, côté Coran (`src/quran_harness/root_identity.py`)
Commande `identite <racine>` ; exemple : `docs/exemple_identite_qdr.md`.

- En-tête : ثلاثي / رباعي, nature des lettres (lue sur la racine ; un alif dans une racine
  du corpus note une hamza), occurrences, verbes et noms.
- Verbes : وزن (numéro du corpus I à XII, nommé selon la documentation du corpus) ×
  ماضٍ / مضارع / أمر × معلوم / مجهول ; traits الإسناد، حالة المضارع، نون التوكيد.
- باب du وزن I : lu sur la voyelle de la عين quand la racine est سالمة et que chaque temps
  ne montre qu'une voyelle (قدر : فَعَلَ يَفْعِلُ ; علم : فَعِلَ يَفْعَلُ) ; sinon
  « غير محدد » (قول, 1 722 occurrences : non déterminé).
- Noms : type donné par le corpus (اسم الفاعل، اسم المفعول، مصدر، اسم علم، ظروف) ; وزن lu
  sur la forme pour les racines سالمة ; traits العدد/الجنس، التعريف، الإعراب.
- Lettres et pronoms collés : gardés dans la forme affichée, ignorés pour le classement
  (`لَقَدِير` est dans la case de `قَدِير`). La couleur viendra avec l'interface (lot H).
- **Validation** : pour chacune des 1 642 racines, chaque occurrence est dans une seule
  case ; قدر : 132 occurrences, 41 verbes, 91 noms ; `يَقْدِر` : 12 dans مضارع معلوم.
- **Pas fait** : les formes non employées (attestées, théoriques), qui attendent le
  lot F ; la table `root_identity` (le calcul est fait à la demande, en moins d'une
  seconde) ; le وزن des racines معتلة, مهموزة ou مضعّفة (« غير محدد »).

### Q28 — Types de noms que le corpus ne donne pas
Le corpus ne nomme que اسم الفاعل، اسم المفعول، مصدر (et اسم علم, ظروف). Pour le reste, je
n'ai mis que ce que le SPEC §2.0 écrit lui-même :

| وزن | Case | Source |
|---|---|---|
| فَعِيل | ambiguë : صيغة مبالغة / صفة مشبهة | SPEC §2.0, D-23 |
| مَفْعَل | ambiguë : مصدر ميمي / اسم زمان / اسم مكان | SPEC §2.0, D-23 |
| فَعَّال، مِفْعَال، فَعُول، فَعِل | ambiguë : صيغة مبالغة | liste des صيغ المبالغة du SPEC |
| tout autre وزن | « اسم — نوع غير محدد » | — |

- Conséquence visible sur قدر : `مِقْدَار` (مِفْعَال) tombe en « ambiguë : صيغة مبالغة »,
  alors que ce n'est sans doute pas une صيغة مبالغة ; `قَدَر`, `قَدْر`, `قُدُور` sont « نوع
  غير محدد ». Je n'ai pas complété la table de mémoire (règle 2).
- **Question** : l'auteur veut-il fournir la table وزن → types, ou attendre les
  dictionnaires (lot F) ?

---

## Décisions du 2026-10-16 et lot D, première moitié (niveaux 1 et 2)

- **Q20** : la واو à l'intérieur d'un mot (`أَوَلَمْ`) reste dans son mot — accepté par
  l'utilisateur. Q20 est close.
- **Q23 — décision de l'utilisateur** : pour décrire une paire, la forme de référence
  compte (`pairs.pivot_counts: true`) ; pour former une famille, deux segments sont reliés
  dès qu'ils ont **au moins 1 élément commun en plus** de la forme de référence
  (`families.link_min_common: 1`). *Écart avec `DECISIONS.md`* : D-08 a pour défaut 2
  éléments hors pivot ; D-08 est à mettre à jour côté conception.
- **Q28 — décision de l'utilisateur** : attendre les dictionnaires (lot F).

### Ce que donnent les familles de `يَقْدِر` (mesuré, rien n'est forcé)

| Découpage | Lien ≥ 1 (réglage retenu) | Lien ≥ 2 (défaut de D-08) | Lien ≥ 3 |
|---|---|---|---|
| souple | 1 famille de 12 (cohésion 86 %) | 1 famille de 12 | 11 + البلد isolé |
| strict | 1 famille de 12 (cohésion 88 %) | 1 famille de 12 | 11 + البلد isolé |

- Aucun seuil ne redonne les groupes du document (9, 2 et 1). Les deux segments de
  سورة النحل partagent avec la formule des 9 au moins `وَ` (cases à part, Q20), `ٱللَّه`
  et `شَيْء` ~ `يَشَاء` (E3) ; avec le découpage souple, 16:75 et 13:26 ont 4 éléments
  communs hors pivot. 90:5 rejoint سورة النحل par `عَلَيْه` ~ `عَلَى` (E1) et, pour
  16:76, `أَحَد` ~ `أَحَدُهُمَا` (E3).
- **Ma proposition de l'étape précédente était donc fausse** : un seuil de 2 ne garde pas
  البلد isolé. Je l'ai dit à l'utilisateur.
- La cohésion reste au-dessus de 50 % : aucun lien n'est coupé.
- Le test du SPEC §2.11 « l'usage de سورة البلد est un usage isolé » n'est pas rempli
  avec le réglage retenu. Il l'est dès un lien ≥ 3. Les tests enregistrent le résultat
  sous chaque seuil, sans en choisir un.

### Lot D, niveaux 1 et 2 : ce qui est fait
`src/quran_harness/pairs.py`, `src/quran_harness/families.py` ; commandes `paire` et
`familles` ; tests `tests/test_pairs.py`, `tests/test_families.py`.

- Codes E0–E4 et Ø sans lemme. La « base » de chaque case (Q22) est stockée dans
  `units.base`, ce qui y est collé dans `units.attached`.
- Les cinq cas du SPEC §2.11, pris par références :

| Cas | Passages | Attendu | Obtenu |
|---|---|---|---|
| 1 | 34:39:1-11 / 34:36:1-8 | R1 partiel ; O1 (من عباده) | R1 partiel ; O1 (من عباده) ; O1 (له) ; O5 |
| 2 | 34:36:1-8 / 17:30:1-7 | R1 partiel + R2 ; O1 (قل) ; O2-E2 | identique |
| 3 | 14:18:13-18 / 2:264:28-33 | R1 partiel ; O3, une paire inversée | identique |
| 4 | 90:5:1-6 / 16:75:4-9 | R2 ; O2-E1 ; autres E4/Ø | identique |
| 5 | 16:75:6-9 / 42:12:7-9 | R2 ; O2-E3 ; O5 | identique, plus O3 (يشاء avant يقدر) |

- Cas 1 : le O1 de `له` est attendu par le document (exemple 3) ; le O5 vient de ce que
  34:36:1-8 est un extrait qui finit sur `يقدر` (Q8, Q25).
- Cas 5 : `ما يشاء ويقدر` n'est pas dans le texte ; `لمن يشاء ويقدر` (42:12) en tient lieu.

### Q29 — Règles de l'alignement que le SPEC ne fixe pas
- **Remplacement O2-E4** : deux cases restées sans partenaire, une de chaque côté, dans
  le même intervalle entre unités appariées. Sinon chacune est un ajout (O1).
- **Séparation O4** : deux unités collées d'un côté, séparées de l'autre par des cases
  qui ne sont ni un ajout (O1) ni une unité déplacée (O3). Le cas 1 du SPEC n'attend que
  O1 quand un ajout coupe un bloc ; je n'ai pas compté O4 en plus. O4 devient rare.
- **Distance au pivot** : en cases ; 0 = pivot, 1 = voisin, au-delà = éloigné. La واو mise
  à part compte comme une case.
- **Le pivot dans un bloc** : il peut faire partie d'un bloc (`وَ يَقْدِر`), mais seulement
  face au pivot de l'autre segment.

### Reste du lot D
Matrices d'alignement par famille (§2.5), contrôle de cohérence paires ↔ matrice (§2.6),
stockage (`pair_signatures`, `families`…), nouvelle fiche et retrait de l'ancien chemin
avec lemme (`compare.py`, `elements.py`, `fiche.py`).

---

## Interface en arabe et matrices (2026-10-16)

**Décision de l'utilisateur — interface en arabe** : interface web et ligne de commande en
arabe ; les codes courts (E0–E4, O1–O5, R1–R3) sont gardés à côté des libellés ; chiffres
occidentaux. *Écart avec `CLAUDE.md`* (« messages utilisateur en français ») : la décision
de l'utilisateur est appliquée ; `CLAUDE.md` est à mettre à jour côté conception. Le code,
les tests et ce journal restent en français.
- Tous les libellés sont dans `src/quran_harness/labels.py` ; on corrige un terme là, sans
  toucher aux calculs. Termes proposés : `docs/GLOSSAIRE_INTERFACE.md`, **pas encore
  validés terme à terme** par l'auteur.
- Passés en arabe : `identite`, `racine`, `forme`, `paire`, `familles` (avec matrices).
  Pas encore : l'interface web et l'ancienne fiche, qui seront remplacées par la nouvelle
  fiche (étape suivante).

**Lot D, niveau 3 : matrices** (`src/quran_harness/matrix.py`, `tests/test_matrix.py`).
La commande `familles` affiche maintenant la matrice et le gabarit de chaque famille.

| Famille | Colonnes | Écarts paires ↔ matrice | Gabarit (cœur) |
|---|---|---|---|
| Les 9 segments de la formule (souple) | 23 | 2 / 36 | `[intro] {الله|ربي|ربك} يبسط الرزق لمن يشاء [من عباده] و يقدر [له …]` |
| Les 12 segments, réglage de l'utilisateur (souple) | 32 | 22 / 66 | même cœur, avec les segments de سورة النحل et سورة البلد |

- Le gabarit des 9 redonne celui du SPEC §2.11, la واو étant une case à part.
- Les 2 écarts des 9 viennent de paires directes que la matrice ne peut pas montrer : une
  `وَ` avant le pivot dans un segment, appariée à une `وَ` après le pivot dans l'autre ;
  `شيء` ~ `يشاء` (E3) appariés de part et d'autre du pivot. Le SPEC n'attend aucun écart,
  mais ses extraits sont plus courts que les segments du texte (Q25).
- Avec les 12 segments, un tiers des paires diffère de la matrice : la famille est
  hétérogène, ce que le §2.6 prévoit de signaler.

### Q30 — Règles de construction de la matrice (SPEC §2.5 ne les fixe pas toutes)
1. **Ligne centrale** : celle qui a le plus d'éléments communs (hors pivot) avec les
   autres ; chaque ligne est placée selon sa comparaison directe avec elle. Égalité entre
   deux centres qui donnent des gabarits différents → matrice « غير محسومة ».
2. **Gauche et droite du pivot alignées à part** ; un appariement qui traverse le pivot
   ou qui est inversé (O3) n'est pas mis en colonne : la case est insérée, et l'ordre reste
   dans les paires.
3. **Remplacement** : entre deux ancres, les cases d'une ligne remplissent d'abord les
   colonnes du centre qu'elle laisse vides, en partant du pivot (O2-E4) ; c'est ce qui met
   `الله`, `ربي`, `ربك` dans une même colonne.
4. **Insertion** : les cases restantes vont dans de nouvelles colonnes ; même forme →
   même colonne ; sinon une colonne libre est partagée (le moins de colonnes) ; à gauche
   du pivot, on aligne du côté du pivot.
5. **Une colonne par case**, pas une par bloc : le SPEC dit « les blocs forment chacun une
   seule unité ». Les blocs n'étant pas les mêmes d'une paire à l'autre, je garde une
   colonne par case ; un bloc se lit comme une suite de colonnes fixes dans le gabarit.

### Nouvelle fiche (2026-10-16)
Commande `fiche <forme> [--pause] [--detail]` (`src/quran_harness/sheet.py`, `tests/test_sheet.py`) ;
exemple : `docs/exemple_fiche_yaqdir.md`. L'ancienne fiche reste disponible sous
`fiche-v0` jusqu'au branchement de l'interface web, puis sera retirée avec le code au lemme.

- **أ. الهوية** : racine, case au niveau 0 (`فَعَلَ — مضارع معلوم (12)`), occurrences,
  segments, position de la forme (في الأول / في الوسط / في الأخير).
- **ب. الارتباطات** : (a) même racine, (b) autres racines, (c) lettres et pronoms ; colonnes
  forme, segments, avant, après ; références avec `--detail`. Le statut est « ملاحظ » :
  le contrôle aléatoire n'est pas encore refait sur les cases (lot E).
- **ج. أنواع الاستعمال** : types des paires, familles, matrices et gabarits.
- **Tableaux allégés** (réponse à la question de lisibilité de la matrice) : par défaut, les
  colonnes d'une matrice remplies par un seul segment sont masquées et comptées ; `--detail`
  montre tout, avec chaque paire.
- Pas encore : regroupement des formes proches (D-16) et couleurs (lot H) ; statistique (lot E).

### Interface web branchée sur la nouvelle méthode ; ancien code retiré (2026-10-16)
- Page en arabe, de droite à gauche (`web/index.html`) ; trois onglets : الجذر (هوية الجذر
  et boutons des formes, qui ouvrent leur fiche), الصيغة (fiche, découpage, « كل التفاصيل »),
  المقارنة الثنائية. La page montre exactement ce que la ligne de commande imprime : le même
  Markdown, converti en HTML (`web/markdown.py`) ; un test le vérifie.
- **Retiré** avec le code au lemme (règle 4) : `compare.py`, `elements.py`, `fiche.py`,
  `export.py`, `assistant.py`, et les commandes `fiche-v0`, `comparer`, `comparer-formes`,
  `resume`, `note`. Fonctions perdues pour l'instant, à reconstruire sur la nouvelle
  méthode : **export CSV**, **résumé par l'IA** (étape 9, Q19), **bloc D des lectures**
  dans la fiche (les tables des riwāyāt restent : commandes `lectures`, `variantes`),
  **comparaison des compagnons de deux formes** (base du niveau 5). L'historique git les garde.
- `stats.py` garde ses mesures et son contrôle aléatoire ; seul le chargement du corpus
  (qui lisait les éléments au lemme) est retiré, à refaire sur les cases au lot E.
- `config.yaml` : sections `reference_form`, `normalization`, `equivalence`, `relations`,
  `usage_groups`, `assistant` retirées.

---

## Niveau 5, première partie : مقارنة صيغتين (2026-10-16)

Décisions de l'utilisateur : comparer **segment par segment** d'abord ; matrices par famille
au niveau de la racine ensuite ; dimensions retenues pour la première version :
1, 2, 4, 5, 7, 8, 9, 11, 12, 14, 20 (liste proposée le 2026-10-16) ; commencer par
يقدر / قدير et عالم / علام.

Réalisé : `src/quran_harness/comparison.py`, commande `comparer <forme 1> <forme 2>`,
onglet web « مقارنة صيغتين », `tests/test_comparison.py` ; exemple :
`docs/exemple_comparaison_yaqdir_qadir.md`.

- Chaque segment de la forme 1 est comparé à chaque segment de la forme 2 (niveau 1, les
  deux formes en pivots appariés par leur racine, code E3). Cas du document : (أ) même forme,
  (ب) même racine et formes différentes, (ج) ni l'un ni l'autre. **Les حروف وضمائر sont
  comptées à part** : sinon la واو mise à part serait commune à presque toutes les paires.
- Dimensions, côte à côte ; familles mixtes (segments des deux formes) avec leur matrice ;
  covariations (20).
- Observations (statut ملاحظ, pas encore de contrôle aléatoire) :

| Paire | Paires de segments | Cas (ب) | Résultat saillant |
|---|---|---|---|
| عَٰلِم / عَلَّٰم | 52 | 52 (100 %) | covariation : عَٰلِم → ٱلْغَيْب (12 sur 13), عَلَّٰم → ٱلْغُيُوب (4 sur 4) |
| يَقْدِر / قَدِير | 444 | 339 (76 %) | يَشَاء ~ شَىْء dans 297 paires ; قَدِير finit le segment 36 fois sur 37 et l'آية 33 fois ; يَقْدِر ouvre l'آية dans 9 segments |

### Q31 — Règles de la comparaison fixées par moi (à confirmer)
- **Formule** (dimension 2) : un segment est « dans une formule » s'il partage un bloc
  d'au moins 3 cases avec un autre segment de la même forme (`comparison.formula_min_block`).
- **Covariation** (dimension 20) : dans une famille mixte, une colonne où chaque forme a ses
  propres remplissages, jamais ceux de l'autre, sur au moins 3 segments (D-10), le
  remplissage dominant couvrant au moins 75 % de ses segments (D-09). Sans cette dernière
  condition, des colonnes très variables passaient pour des covariations.
- **Position du segment dans l'آية** (dimension 5) : أول الآية (commence au mot 1), آخر الآية
  (finit au dernier mot), آية كاملة, وسط الآية.
- **Ensembles fixes ou variables** (dimension 8) : pour chaque racine compagne (autre que la
  racine étudiée), les formes rencontrées et leur nombre.

### Q32 — Recherche en orthographe courante
Le texte ʿuthmānī écrit souvent l'alif long par un alif suscrit (`عَٰلِم`, `عَلَّٰم`). Taper
`عالم` ne trouvait rien. Ajout d'une colonne `units.spelling` (squelette avec l'alif suscrit
écrit en alif), utilisée **seulement** quand la recherche exacte ne trouve rien ; les formes
trouvées sont toujours listées à part, jamais fusionnées. Ce n'est qu'une aide à la saisie,
jamais une base de comparaison.

Correction au passage (niveau 0) : le وزن d'un nom avec alif suscrit après une shadda
(`عَلَّٰم`) n'était pas reconnu ; il l'est maintenant (`فَعَّال` → case « ملتبسة : صيغة مبالغة »).

---

## Lot F, téléchargements (2026-10-18)

- **Q28 — suite** : l'utilisateur a donné son accord pour le lot F et pour lisan345 sans
  licence déclarée (2026-10-18). Les dix dictionnaires de D-25 et lisan345 sont dans
  `data/raw/` (voir `data/SOURCES.md`, §7 et §8). Q28 reste ouverte jusqu'à l'extraction
  des articles : la table وزن → types n'est toujours pas complétée.
- Le générateur de تصريف (Qutrub) n'est **pas** encore téléchargé.

### Q33 — Les dictionnaires d'OpenITI n'ont aucune voyelle
Mesuré : 0 حركة dans les dix fichiers, et dans toutes leurs versions secondaires de
l'archive. Le SPEC (§2.0) prévoyait un texte « partiellement vocalisé » et une comparaison
« à plusieurs niveaux de الشكل ». Avec ces fichiers, seule la comparaison au niveau
`squelette sans الشكل` est possible : `قَدَر`, `قَدْر`, `قِدْر`, `قُدِرَ` ont le même
squelette `قدر` et ne se distinguent pas par simple correspondance.
- **Valeur par défaut prudente** (appliquée tant que l'auteur n'a pas tranché) : une
  correspondance de squelette seule donne « à vérifier », jamais « attestée » (règle du
  SPEC sur les correspondances partielles).
- **Piste, non appliquée** : les dictionnaires classiques décrivent souvent la vocalisation
  en toutes lettres (« بالتحريك »، « بالكسر »، « بالفتح »، « كزنجبيل »). Lire ces indications
  donnerait une vocalisation explicite, mais c'est une interprétation du texte de l'article :
  à valider par l'auteur avant tout code.
- **Autre piste** : chercher une édition vocalisée d'un des dix dictionnaires. Je n'en ai pas
  cherché ; rien n'est téléchargé dans ce sens.

### Q34 — Une seule version par dictionnaire : la version « primaire » d'OpenITI
OpenITI a 2 à 4 versions de chaque dictionnaire (éditions numériques différentes). J'ai pris
la version marquée `PRIMARY_VERSION`. Pour لسان العرب, c'est la seule dont les articles sont
balisés (`### $ racine:`), ce qui facilite le découpage. Les neuf autres n'ont aucune balise
d'article. Valeur par défaut : version primaire ; à revoir si une autre version s'avère
mieux découpable.

### Q35 — Écriture des racines faibles : OpenITI et lisan345 ne s'accordent pas
Contrôle croisé (titres d'articles de لسان العرب dans OpenITI / racines de lisan345) :
8 611 communes, 507 seulement dans OpenITI, 652 seulement dans lisan345. Les écarts portent
surtout sur la dernière lettre faible (`أتى` / `أتي`, `أخا` / `أخو`). Le corpus coranique
(QAC) écrit lui-même ses racines d'une troisième façon (`Aty`, `Axw` en translittération).
- **Valeur par défaut** : aucune correspondance n'est forcée. Le rapprochement des trois
  écritures sera une table explicite, documentée et testée (à faire avec l'extraction).

**Q31 — confirmée par l'utilisateur (2026-10-19)** : définition de la formule (bloc d'au
moins 3 cases partagé avec un autre segment de la même forme) et de la covariation
(remplissages propres à chaque forme, au moins 3 segments de chaque côté, remplissage
dominant à 75 % au moins) acceptées telles quelles.

---

## Dimensions du comportement : décisions de l'utilisateur (2026-10-19)
- **Dispersion** (1) : attribut de la forme, affiché avec elle (fiche, en-tête de comparaison),
  séparé de l'analyse globale du comportement.
- **Position du segment dans l'آية** (5) : secondaire ; affichée seulement au détail.
- **Dimensions du texte (★) gardées** ; 12 (cadre immédiat) et 16 (distance des changements)
  fusionnées en une dimension « الجوار » ; 17 (longueur des segments) retirée ; 21 (lectures)
  devient un statut (« ثابت في كل الروايات »), pas une dimension.
- **Noyau** toujours affiché : 4 موقع الصيغة، 7 أنواع الارتباطات، 11 التقديم والتأخير،
  2 التكرار، 14 أنواع العلاقة بين المقاطع، الجوار. Les autres au détail.
- Ces changements d'affichage ne sont pas encore faits dans le code.

Lot F : le travail de la session du 2026-10-18 (téléchargement des dictionnaires) est
commité (b8d0a2a) ; la session est fermée à la demande de l'utilisateur.
