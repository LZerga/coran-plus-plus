# SOURCES.md — Provenance des données

Dernière mise à jour : 2026-10-18 (lot F : dictionnaires classiques).
Règle : tout fichier de `data/raw/` est en lecture seule et figure ici avec URL, date,
licence et SHA-256 (CLAUDE.md, règle 7). Le manifeste lu par le code est
`data/sources.yaml` ; il contient les URL exactes et les empreintes de chaque fichier.

Cadre d'usage décidé par l'équipe (2026-10-10) : projet de recherche open source, sans
usage commercial. Les clauses « pas d'usage commercial » ne sont donc pas bloquantes.
Les autres obligations (mention de la source, pas de modification) restent à respecter.

Vérifier : `uv run python -m quran_harness sources verify`
Retélécharger : `uv run python -m quran_harness sources fetch --accept-terms`

## Résumé

| Ressource | État | Dossier | Licence |
|---|---|---|---|
| Texte ʿuthmānī Hafs (Tanzil 1.1) | Téléchargé, vérifié | `data/raw/tanzil/` | CC BY 3.0 + conditions |
| Texte simple sans signes (Tanzil 1.1) | Téléchargé, vérifié | `data/raw/tanzil/` | CC BY 3.0 + conditions |
| Quranic Arabic Corpus, morphologie 0.4 | Téléchargé **depuis un miroir**, vérifié | `data/raw/qac/` | GNU GPL + conditions |
| quran-morphology (dérivé du QAC) | Téléchargé, vérifié | `data/raw/quran-morphology-mustafa0x/` | **non déclarée** |
| MASAQ version 6 | Téléchargé, vérifié | `data/raw/masaq/` | CC BY-NC 3.0 |
| Textes de 8 riwāyāt (KFGQPC) | Téléchargé, vérifié | `data/raw/kfgqpc/` | **non déclarée** |
| Document de recherche | **Introuvable en ligne** | `docs/` (vide) | — |
| Mufahras (المعجم المفهرس) | Pas de version numérique ; à reconstruire (étape 3) | — | — |
| Dix dictionnaires classiques de D-25 (OpenITI 2025.1.9) | Extraits de l'archive, vérifiés | `data/raw/openiti/` | CC BY-NC-SA 4.0 |
| Racines de لسان العرب (lisan345) | Téléchargé, vérifié | `data/raw/lisan345/` | **non déclarée** (accord de l'utilisateur) |

## Comptages à la réception

Comptages bruts, sans transformation (`uv run python -m quran_harness counts`).

| Source | Sourates | Versets | Mots |
|---|---|---|---|
| tanzil-uthmani | 114 | 6 236 | 77 881 |
| tanzil-simple-clean | 114 | 6 236 | 78 248 |
| qac-morphology | 114 | 6 236 | 77 429 |
| quran-morphology-mustafa0x | 114 | 6 236 | 77 429 |
| masaq | 114 | 6 236 | 77 411 |
| kfgqpc-hafs | 114 | 6 236 | — |
| kfgqpc-shouba | 114 | 6 236 | — |
| kfgqpc-warsh | 114 | 6 214 | — |
| kfgqpc-qaloon | 114 | 6 214 | — |
| kfgqpc-doori | 114 | 6 217 | — |
| kfgqpc-soosi | 114 | 6 217 | — |
| kfgqpc-bazzi | 114 | 6 220 | — |
| kfgqpc-qumbul | 114 | 6 220 | — |

### Pourquoi les nombres de mots diffèrent
Ces écarts sont constatés, pas corrigés. Ils seront traités à l'étape 2 (voir QUESTIONS.md, Q11).

- **Basmala** : les fichiers Tanzil placent la basmala (4 mots) au début du verset 1 de
  112 sourates (toutes sauf 1 et 9). Elle n'est pas comptée par le QAC.
  77 881 − 448 = 77 433 mots.
- **Découpage du QAC** : après retrait de la basmala, il reste 4 mots d'écart, dans 4
  versets. Le QAC y compte un seul mot là où le texte en écrit deux : `بَعْدَ مَا` (2:181,
  8:6, 13:37) et `إِلْ يَاسِينَ` (37:130). La position des mots suivants y est décalée
  d'un rang.
- **Tanzil 1.1 contre QAC (bâti sur Tanzil 1.0.2)** : comparés mot à mot et caractère
  par caractère, seuls 319 mots sur 77 433 diffèrent :
  - 317 écarts d'encodage : hamza ou petit yāʾ porté par un tatweel dans la version 1.1
    (`ـٔ`, `ـۧ`), caractère nu dans le corpus (`ء`, `ۦ`). Même texte, autre codage.
  - 2 écarts de lettres : `يَٰصَٰحِبَىِ` (12:39 et 12:41), écrit avec un `ى` de plus dans
    le corpus.
  Ces écarts sont enregistrés dans la table `alignment_notes`, pas corrigés.
- **Orthographe simple** : 77 800 mots hors basmala. 363 versets ont un mot de plus qu'en
  graphie ʿuthmānī, par exemple `يا أيها` (deux mots) contre `يَٰٓأَيُّهَا` (un mot).
- **MASAQ** : découpe comme la graphie ʿuthmānī (`يَاأَيُّهَا` = un mot à deux radicaux).
  77 411 mots distincts, mais la somme des plus grands numéros de mot par verset donne
  77 421 : la numérotation a des trous. 386 mots portent deux lignes `Stem`.

---

## 1. Tanzil — texte du Coran

- **Site** : https://tanzil.net/download/ — version 1.1 (février 2021)
- **Date de téléchargement** : 2026-10-10
- **Licence** (bloc recopié du fichier) : Creative Commons Attribution 3.0, avec ces
  conditions : copie et diffusion à l'identique autorisées, **modification interdite** ;
  utilisation libre à condition d'indiquer la source (Tanzil Project) et de mettre un
  lien vers tanzil.net ; le bloc de copyright doit rester dans toute copie et être
  reproduit dans les fichiers dérivés.
- **Acceptation des conditions** : le formulaire exige de cocher « I agree with Terms of
  Use ». Fait le 2026-10-10 sur instruction de l'équipe (paramètre `agree=true`).

| Fichier | Options | Taille | SHA-256 |
|---|---|---|---|
| `tanzil/quran-uthmani.txt` | type Uthmani, marques de pause incluses ; sans signes de sajda, de rubʿ, ni tatweel ; format « Text (with aya numbers) » | 1 383 970 | `54ea3b2f689f39dec2808361fec957f62a965ae029dcde7f9f21d65a844448e5` |
| `tanzil/quran-simple-clean.txt` | type Simple (Clean) ; même format | 781 176 | `228df2a717671aeb9d2ff573002bd28d6b3f973f4bc7153554e3a81663d67610` |

Remarques :
- Tanzil décrit son texte ʿuthmānī comme conforme au Mushaf de Médine (le SPEC parle de
  l'« éd. du Caire 1924 »).
- Les marques de pause sont des jetons séparés par une espace. Relevé : U+06DA (1 972),
  U+06D6 (1 682), U+06D7 (603), U+06D9 (68), U+06D8 (22), U+06DB (12), U+06DC (5).
- ⚠ Le bloc de copyright en fin de fichier contient l'année en cours (« 2007-2026 »).
  Un téléchargement fait une autre année aura donc une empreinte différente alors que le
  texte est le même.

---

## 2. Quranic Arabic Corpus — morphologie 0.4

- **Auteur** : Kais Dukes, 2011 — https://corpus.quran.com
- **Fichier** : `qac/quranic-corpus-morphology-0.4.txt` — 6 309 503 octets
- **SHA-256** : `a1d12923815341face765083805d2148ed2d9f5cc3f7d6665219d887675d8c46`
- **Date de téléchargement** : 2026-10-10
- **Licence** (bloc recopié du fichier) : GNU General Public License, avec ces
  conditions : copie à l'identique autorisée, **modification du fichier interdite** ;
  mention du Quranic Arabic Corpus et lien vers corpus.quran.com obligatoires.
  Aucune clause « non commercial » dans le fichier (le SPEC §3 en mentionnait une).
- **Texte de base** : Tanzil Uthmani **version 1.0.2**, d'après l'en-tête du fichier.
  Notre texte Tanzil est en version 1.1.

⚠ **Téléchargé depuis un miroir, pas depuis le site officiel.** Le site officiel
(https://corpus.quran.com/download/) exige une adresse e-mail, que je n'ai pas saisie.
- Miroir utilisé : dépôt `alstat/QuranTree.jl`, commit `d7a0fe9c`.
- Contrôle : un second miroir indépendant (`cltk/arabic_morphology_quranic-corpus`,
  commit `b5abd4d8`) donne exactement la même empreinte.
- Reste à faire par l'équipe pour lever le doute : télécharger le fichier officiel et
  comparer son empreinte à celle ci-dessus.

---

## 3. quran-morphology (mustafa0x) — dérivé du QAC

- **Dépôt** : https://github.com/mustafa0x/quran-morphology — commit `8f38b390`
- **Fichiers** : `quran-morphology-mustafa0x/quran-morphology.txt` (6 322 866 octets,
  SHA-256 `742bfac59941b2cb09736d5b7aae694af50792261fb8450cbf6afafcc340645f`) et son
  `README.md` (SHA-256 `caec314d4c64cc26e27b3c45c12a33be7059a83fc3db385c43615d6a5792ba5f`)
- **Date de téléchargement** : 2026-10-10
- **Licence** : **non déclarée** dans le dépôt. C'est une œuvre dérivée du QAC 0.4.
- **Contenu** : le QAC 0.4 converti en écriture arabe, avec des corrections de racines
  et de lemmes listées dans son README. Même nombre de mots que le QAC (77 429).
- **Usage prévu** : comparaison des racines avec le QAC. Ce n'est **pas une source
  indépendante** : un accord entre les deux ne prouve rien, seuls les désaccords
  (les corrections) sont informatifs.

---

## 4. MASAQ

- **Nom** : MASAQ: Morphologically-Analyzed and Syntactically-Annotated Quran Dataset
- **Auteurs** : Majdi Sawalha, Sane Yagi, Faisal Alshargi, Bassam Hammo, Abdallah Alshdaifat
- **Version** : 6, publiée le 2024-12-09 — DOI `10.17632/9yvrzxktmr.6`
- **Page** : https://data.mendeley.com/datasets/9yvrzxktmr/6
- **Fichier** : `masaq/MASAQ.csv` — 18 650 409 octets, UTF-8
- **SHA-256** : `777d0cc8f24f4c17d07ad83a522056fe7ebd5c83dbbae86161f1fdc95aaca900`
  (identique à l'empreinte publiée par l'API Mendeley Data)
- **Date de téléchargement** : 2026-10-10
- **Licence** : CC BY-NC 3.0 (le SPEC §3 indiquait CC BY 3.0).

Constats :
- 157 676 lignes (une par segment de mot), 19 colonnes.
- **Pas de colonne racine ni lemme** : MASAQ ne peut pas servir au contrôle croisé des
  racines prévu au SPEC §3. Il peut contrôler le découpage des clitiques
  (`Prefix` / `Stem` / `Suffix`). Voir QUESTIONS.md, Q9.
- Texte en orthographe courante (ex. `الرَّحْمَنِ`).
- Colonne `Punctuation_Mark` vide sauf 5 lignes : aucune marque de pause exploitable.

Les formats `MASAQ.tsv`, `MASAQ.json` et `MASAQ.db` contiennent les mêmes données et
n'ont pas été téléchargés.

---

## 5. Textes des riwāyāt — KFGQPC

- **Dépôt** : https://github.com/ibnhazm/KFGQPC — commit `25f2f888`
- **Origine déclarée** : Complexe du Roi Fahd pour l'impression du Coran
  (https://qurancomplex.gov.sa)
- **Date de téléchargement** : 2026-10-10
- **Licence** : **non déclarée** dans le dépôt. Les conditions du Complexe du Roi Fahd
  n'ont pas été vérifiées. À ne pas rediffuser avant vérification.

| Riwāya | Fichier | Versets | SHA-256 |
|---|---|---|---|
| Hafs | `kfgqpc/hafs/hafsData_v18.json` | 6 236 | `5d8bb91726e482839d0057633cb1973031e4d706fa9604eea5e08892f20ba140` |
| Shuʿba | `kfgqpc/shouba/ShoubaData08.json` | 6 236 | `f105da3949e0b8092e3abcd23a539c9bef4c9b7474f15d29848471f150ade667` |
| Warsh | `kfgqpc/warsh/warshData_v10.json` | 6 214 | `f05d0dc652fd46b38563cacb13242f76f80db4cc64d25873da0bce157253872f` |
| Qālūn | `kfgqpc/qaloon/QaloonData_v10.json` | 6 214 | `18465c40ebeec40a92eb98745c9b89796ac6e31f6e93988883dfb6602faaea95` |
| al-Dūrī | `kfgqpc/doori/DooriData_v09.json` | 6 217 | `169b949d6cedd93ddb21728c16057d5ac7faf673ac10e0f213bb5dec1dc90d7d` |
| al-Sūsī | `kfgqpc/soosi/SoosiData09.json` | 6 217 | `81af638398efa88308803c06a961d7019daf2e87e822b8acae24df05a82aa81b` |
| al-Bazzī | `kfgqpc/bazzi/BazziData_v07.json` | 6 220 | `2ff11a126e0f15f161b88f83528c0b11d24f69f474baabf02d8864cd93ed15ce` |
| Qunbul | `kfgqpc/qumbul/QumbulData_v07.json` | 6 220 | `3a0377bd943def12711b15cc71a65214fb902a5df70240b87df13c7b516a7888` |

Le `README.md` de chaque riwāya est conservé à côté du fichier (empreintes dans
`data/sources.yaml`).

Usage (étape 7) : chaque fichier est aligné sur le texte de base au niveau des lettres ;
le fichier Hafs sert d'étalonnage et ne montre aucun écart avec le texte Tanzil. Détail
et limites dans QUESTIONS.md, Q6.

Constats :
- Ce sont des **textes complets**, un enregistrement par verset, pas des tables de
  variantes. La table `variants` est calculée par différence.
- Chaque fichier code à sa façon les voyelles, les hamzas et les petits signes (sukūn
  en U+06E1 dans le fichier Hafs et en U+0652 dans le fichier Warsh, yāʾ final en
  U+06D2 chez Warsh et Qālūn, etc.). Seules les lettres sont comparables d'un fichier à
  l'autre.
- Les jetons sans lettre (numéros de verset, signes) sont ignorés à la lecture.
- **La numérotation des versets diffère** : seules Hafs et Shuʿba ont 6 236 versets.
  Une table de correspondance sera nécessaire.
- Le champ `aya_text` est prévu pour une police propre à chaque riwāya
  (« UthmanicHafs », « UthmanicWarsh »…). Son encodage n'est pas forcément comparable
  caractère par caractère à celui de Tanzil : à examiner avant toute comparaison.
- Seul le fichier Hafs a une colonne en orthographe courante (`aya_text_emlaey`).
- Les fichiers ne couvrent que 4 des 7 lecteurs (Nāfiʿ, Ibn Kathīr, Abū ʿAmr, ʿĀṣim),
  deux transmissions chacun. Voir QUESTIONS.md, Q6.

---

## 6. Document de recherche — introuvable

« ملاحظات نقدية عامة حول العقل اللغوي العربي » : trois recherches (titre exact, titre et
termes de la méthode, titre partiel et « pdf ») n'ont donné aucun résultat
correspondant. Les résultats portent sur d'autres ouvrages (Jabri, Tarabishi, thèses
sans rapport). Rien n'a été téléchargé. Le document doit être fourni par l'équipe et
déposé dans `docs/`.

---

## 7. Dictionnaires classiques — OpenITI (lot F)

- **Notice** : OpenITI, *a Machine-Readable Corpus of Islamicate Texts*, version 2025.1.9
  (30/12/2025), DOI 10.5281/zenodo.17767721, https://zenodo.org/records/17767721.
  Dernière version publiée à la date du téléchargement.
- **Licence** : CC BY-NC-SA 4.0 (attribution, pas d'usage commercial, partage dans les
  mêmes conditions). Compatible avec le cadre d'usage du projet.
- **Téléchargé le** : 2026-10-18.
- **Méthode** : l'archive `OpenITI_data_2025-1-9.zip` fait 5,9 Go. Seuls les fichiers
  utiles en ont été extraits, par lecture partielle HTTP (`sources.read_archive_member`).
  Le CRC-32 de chaque fichier est contrôlé par `zipfile` à l'extraction, puis le SHA-256
  est noté dans `data/sources.yaml` (champ `archive_member`). Le fichier de notice
  `OpenITI_metadata_2025-1-9.tsv` est gardé tel quel (MD5 identique à celui de Zenodo).
- **Choix de version** : pour chaque ouvrage, la version marquée « primaire »
  (`PRIMARY_VERSION`) par OpenITI, avec sa fiche `.yml`.

| Dictionnaire (D-25) | Fichier OpenITI | Mots (notice) |
|---|---|---|
| كتاب العين (الخليل) | `0170KhalilFarahidi.Cayn.JK000930-ara1` | 352 061 |
| جمهرة اللغة (ابن دريد) | `0321IbnDuraydAzdi.JamharatLugha.JK007100-ara1` | 394 391 |
| تهذيب اللغة (الأزهري) | `0370AbuMansurAzhari.TahdhibLugha.JK007040-ara1` | 1 352 464 |
| الصحاح (الجوهري) | `0393IbnHammadJawhari.SihahTajLugha.Masaha000955Vols-ara1` | 510 108 |
| مقاييس اللغة (ابن فارس) | `0395IbnFarisQazwini.MucjamMaqayis.JK008008-ara1` | 362 165 |
| المحكم (ابن سيده) | `0458IbnSidaMursi.MuhkamWaMuhit.JK006962-ara1` | 1 024 053 |
| أساس البلاغة (الزمخشري) | `0538JarAllahZamakhshari.AsasBalagha.JK007032-ara1` | 293 416 |
| **لسان العرب (ابن منظور)** | `0711IbnManzurIfriqi.LisanCarab.Shamela0001687-ara1.mARkdown` | 3 009 681 |
| القاموس المحيط (الفيروزآبادي) | `0817MajdDinFiruzabadi.QamusMuhit.JK001437-ara1` | 568 993 |
| تاج العروس (الزبيدي) | `1205MurtadaZabidi.TajCarus.JK007140-ara1` | 3 882 381 |

Constats à la réception :
- **Aucun texte ne porte الشكل** (0 حركة sur tous les fichiers, versions secondaires de
  l'archive comprises, mesuré sur leurs premiers 400 Ko). OpenITI publie des versions
  « nettoyées ». Conséquence pour l'état « attestée » : voir QUESTIONS.md, Q33.
- **Seul لسان العرب a ses articles balisés** (`### $ racine:` ; 9 155 articles, 9 118
  titres distincts). Les neuf autres n'ont pas de balise d'article : le découpage
  (SPEC §2.0, étape 1 de la méthode d'extraction) devra s'appuyer sur la mise en page
  propre à chacun (ex. `( أكف )` dans مقاييس اللغة).
- L'édition de لسان العرب suit Dār Ṣādir (notice OpenITI : collationnée sur la 1re édition,
  même pagination ; « quelques sous-titres manquent »).

## 8. Racines de لسان العرب — lisan345

- **Dépôt** : https://github.com/git85hub/lisan345, épinglé sur le commit
  `013c33d389c2c42f62dfeed3beaafcf7d5aad952` (2026-06-02).
- **Licence** : **non déclarée**. Usage accepté par l'utilisateur le 2026-10-18.
  Citation demandée par l'auteur : Elmaz, Orhan. 2026. *Lisan345*.
  http://github.com/git85hub/lisan345.
- **Téléchargé le** : 2026-10-18. Fichiers : `README.md`, `lisan3.csv`, `lisan4.csv`,
  `lisan5.csv`.
- **Contenu** : 6 529 racines trilitères, 2 551 quadrilitères, 183 quintilitères
  (conforme au README), tirées de l'édition numérique d'al-Warrāq (alwaraq.net/book-view/89),
  pas de celle d'OpenITI.
- **Contrôle croisé avec OpenITI** : 8 611 racines communes ; 507 titres seulement dans
  OpenITI, 652 racines seulement dans lisan345. Les écarts observés portent surtout sur
  l'écriture des racines à dernière lettre faible (OpenITI `أتى`, `أخا` ; lisan345 `أتي`,
  `أخو`). Non corrigé : constat seulement.

