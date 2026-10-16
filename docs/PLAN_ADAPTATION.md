# PLAN_ADAPTATION.md — Passage du code v0 à la spécification v12

Rédigé le 2026-10-12, après lecture de `CHANGELOG.md` (entrées v1 à v12), `SPEC.md`,
`DECISIONS.md`, `CLAUDE.md`, `QUESTIONS.md` et de `docs/document_de_recherche.pdf`.
**Aucun code n'a été modifié.** Ce plan attend l'accord de l'utilisateur.

État de départ : code 0.9.0, 406 tests verts, base `data/processed/quran.db` construite
(étapes 1 à 9 de la spécification v0).

---

## 1. Résumé

| Point du CHANGELOG | Ampleur | Ce qui est gardé |
|---|---|---|
| v11/v12 — واو de conjonction à part (D-02) | moyenne : nouvelle couche « cases » | `words` et le texte brut, inchangés |
| 1 — Lemme supprimé | forte : 250 mentions dans 24 fichiers | l'annotation brute (colonnes non lues) |
| 2 — Voyelle finale séparée (D-04) | moyenne : nouvelle clé de forme | `normalize.py`, étendu d'un niveau |
| 3 — Méthode en niveaux (R, E, O, familles, matrices) | forte : `compare.py` réécrit, 3 modules neufs | recherche des blocs, union-find des groupes |
| 4 — Niveau 0, identité de la racine | neuf ; dépend de données à télécharger | lecture du QAC (les traits sont déjà en base) |
| 5 — Niveau 5, toutes les formes | neuf | `compare_companions` (trois cas du document) |
| 6 — Statuts des résultats | faible à moyenne | contrôle aléatoire de `stats.py` |
| 7 — Affichage | moyenne | FastAPI, page unique, exports, scripts `.bat` |

Non touchés : `sources.py`, `tanzil.py`, `qac.py`, `buckwalter.py`, `masaq.py`,
`alt_roots.py`, `raw_counts.py`, `readings.py` (alignement des riwāyāt), `segmentation.py`
(règles de coupe), les fichiers de `data/raw/`.

---

## 2. Constats faits pendant la lecture (à trancher avant de coder)

Ces points sont repris dans `QUESTIONS.md` (Q20 à Q26). Les quatre premiers bloquent
les cas de test du SPEC §2.11 ; je propose un défaut pour chacun.

**C1 — Le contrôle de D-02 est vérifié.** Avec « و à part + الشكل intérieur + voyelle finale
séparée », la forme يَقْدِر se trouve dans 12 versets, ceux de la liste de D-02
(9 × وَيَقْدِرُ, 16:75, 16:76, et 90:5 يَقْدِرَ). 73:20 يُقَدِّرُ est écarté par le الشكل seul,
sans lemme. Vérifié par requête en lecture seule sur la base actuelle.

**C2 — Quelle واو est « de conjonction » ? (Q20)** Le corpus étiquette la واو collée de six
façons :

| Étiquette du corpus | Mots | En tête du mot | À l'intérieur (أَوَلَمْ…) |
|---|---|---|---|
| CONJ (عاطفة) | 8 177 | 8 173 | 4 |
| REM (استئنافية) | 1 034 | 1 034 | 0 |
| CIRC (حالية) | 293 | 292 | 1 |
| SUP (زائدة) | 59 | 8 | 51 |
| P (واو القسم) | 28 | 25 | 3 |
| COM (معية) | 3 | 3 | 0 |

Défaut proposé : séparer **CONJ seulement** (lecture littérale de D-02), et seulement quand
la واو est la première lettre du mot (`أَوَلَمْ` reste un mot). Paramètre
`form.detached_waw_tags: [CONJ]`. Les 9 ويقدر sont tous CONJ : C1 ne dépend pas du choix.

**C3 — Les signes d'assimilation cassent l'identité (Q21, suite de Q12).** Avec le الشكل
intérieur, `مِمَّا` (14:18) et `مِّمَّا` (2:264) sont deux formes ; de même `لَا` / `لَّا`,
`مِنْ` / `مِن`. Le cas 3 du §2.11 (trois blocs identiques) ne passe alors pas.
Défaut proposé : la shadda d'assimilation sur la première lettre et le sukūn de la dernière
sont rangés parmi les **signes de récitation** (exclus de la forme, D-03). Paramètre
`form.assimilation_marks_in_form: false`. Mesure faite à l'étape 3 : 619 graphies fusionnent.

**C4 — « Même base » sans lemme (Q22).** `على` / `عليه` : le corpus donne les bases `عَلَىٰ`
et `عَلَيْ`, différentes par les lettres. `ربي` / `ربك` : bases `رَبِّ` et `رَبَّ`, différentes
par la voyelle de cas, qui est ici **à l'intérieur** du mot écrit. `الرزق` / `رزقا` : article
d'un côté, tanwīn et alif de l'autre.
Défaut proposé : la **base** est le radical du corpus (sans article, sans lettres ni
pronoms collés), comparé avec son الشكل sauf les signes de sa dernière lettre (voyelle de
cas, tanwīn et son alif), `ى` et `ي` finaux tenus pour égaux. Ensuite :
E1 = même base, un côté a quelque chose de collé en plus ; E2 = même base, pronoms
différents. Cas non prévu par le SPEC : même base, **lettre** collée différente
(`بربك` / `لربك`) → rangé E2 avec la mention « lettre changée », à confirmer.

**C5 — Les cas 4 et 5 du §2.11 contredisent la règle R2 du §2.3 (Q23).**
La règle : R2 = au moins 2 éléments communs **hors pivot**. Or :
- cas 4 (`أيحسب أن لن يقدر عليه أحد` / `عبدا مملوكا لا يقدر على شيء`) : un seul élément
  commun hors pivot (على ~ عليه) ;
- cas 5 (`لا يقدر على شيء` / `ما يشاء ويقدر`) : un seul (شيء ~ يشاء).
La règle les classe donc R3, alors que le tableau attend R2. Le document, lui, compte la
forme de référence parmi les deux éléments. Mais si le pivot compte, 90:5 est relié à
16:75 et l'usage de سورة البلد n'est plus isolé, ce qui contredit l'autre test du §2.11
et le document (« إستعمال واحد مختلف عن غيره »).
Défaut proposé : appliquer la règle du §2.3 (`relations.pivot_counts: false`,
`relations.r2_min_common: 2`) ; les cas 4 et 5 sont testés sur leurs **opérations**
(O2-E1, O2-E3, O5) et leur type R est affiché sous les deux réglages, sans en forcer un.

**C6 — Le cas 1 du §2.11 n'existe pas dans le texte (Q8, confirmé par le document).**
La phrase `قل إن ربي يبسط الرزق لمن يشاء ويقدر له` n'est dans aucun verset. Dans le
document, l'exemple correspondant (exemple 3) compare 34:39 à 34:36 : deux blocs
identiques, `من عباده` en plus et `له` en plus. Défaut : le cas 1 est testé sur
34:39:1-11 / 34:36:1-8, signature attendue R1 partiel ; O1 (من عباده) ; O1 (له).

**C7 — Les « 8 comparaisons » du document (Q24).** Le document les écrit toutes avec
`من عباده`, y compris pour des versets qui ne l'ont pas (13:26, 17:30, 30:37, 39:52,
42:12). Ce sont des citations approximatives. Défaut : les 8 comparaisons sont stockées par
références (13:26 contre les 8 autres segments de la formule) ; le libellé du document
n'est qu'un libellé (règle de Q8).

**C8 — Le gabarit attendu dépend de D-01 (Q25).** Avec le découpage souple, le segment de
34:36 est 1-13 : il continue par `ولكن أكثر الناس لا يعلمون`. Le gabarit aura donc une
colonne facultative de plus à gauche que `[intro] [ذات] يبسط الرزق لمن يشاء [من عباده]
ويقدر [له]`. Avec le découpage strict (défaut), les segments sont encore plus longs.
Le test du gabarit sera écrit sur les colonnes attendues, et toute colonne en plus sera
listée, pas masquée. La décision sur les « extraits » (D-01) reste à l'auteur.

**C9 — باب du ثلاثي مجرد (Q26).** Le corpus donne le وزن (II à X), le temps, la voix, le
mode, la personne, les participes et le مصدر. Il ne donne pas le باب (فَعَلَ يَفْعِلُ…) ni
le وزن précis des noms. Le باب se lit sur le الشكل quand le ماضي et le مضارع sont tous deux
employés ; sinon il vient du dictionnaire, ou la case le dit « non déterminé ».

---

## 3. Point par point

### 3.0 واو de conjonction à part (v11, v12 — D-02)

- **Touché** : `ingest.py` (ou un module neuf `units.py`), `index.py`, `elements.py`,
  `segmentation.py` (table `segment_words`), `stats.py` (jetons), `fiche.py`, `config.yaml`.
- **Proposition** : ne pas toucher à la table `words` (un mot du texte = une ligne,
  référence `sourate:verset:mot` stable, reconstruction du texte brut inchangée, règle 1).
  Ajouter une table dérivée **`units`** (les « cases ») : une ligne par mot, deux lignes
  quand le mot commence par une واو de conjonction (`34:36:8a` = وَ, `34:36:8b` = يَقْدِرُ).
  Toute l'analyse lit `units` ; toute référence affichée reste celle du mot.
- **Gardé** : `forms._cut` sait déjà couper un préfixe du corpus dans le texte de base.
- **Écarté** : `match_level`, `article_is_clitic`, les niveaux `noyau` / `nu`, l'option
  `--niveau` (CHANGELOG v11).
- **Validation** : texte reconstruit depuis `units` = texte brut ; يَقْدِر dans 12 versets.
- **Tests** : `test_ingest.py` (ajouts), `test_forms.py` et `test_index.py` (réécrits pour
  la nouvelle clé), `test_segmentation.py` (un mot = un segment → une case = un segment).

### 3.1 Lemme supprimé (point 1)

- **Touché** : `compare.py` (niveaux 0 à 2), `elements.py` (`Element.lemmas`), `index.py`
  (vue `root_index`, `FormCount.lemma`, regroupements par lemme), `fiche.py` (une fiche par
  lemme, clé des compagnons), `stats.py` (`ItemKey`), `export.py`, `assistant.py`,
  `web/`, `__main__.py` (affichages « lemme », option `--lemme` de `note`).
- **Remplacement** : la clé d'une forme devient (forme avec الشكل intérieur, racine). Les
  homographes sont séparés par le الشكل (D-03). Une saisie sans voyelles qui recouvre
  plusieurs formes vocalisées liste les candidates, sans fusion (défaut de Q7 conservé).
- **Gardé** : les colonnes `lemma` de `words` et `word_segments` restent en base comme
  annotation brute (l'ingestion ne change pas), mais plus aucun module d'analyse ne les
  lit. Un test le vérifiera (recherche du mot `lemma` hors de `ingest.py` et `qac.py`).
- **Tests** : `test_compare.py`, `test_index.py`, `test_fiche.py`, `test_fiche_stats.py`,
  `test_stats.py`, `test_web.py`, `test_assistant.py`.

### 3.2 Voyelle finale séparée (point 2 — D-04)

- **Touché** : `normalize.py` (nouveau niveau), `docs/NORMALISATION.md`, `config.yaml`.
- **Niveaux après changement** (SPEC §3) : `brut` / `sans signes de récitation` /
  `sans voyelle finale` (**clé de forme par défaut**) / `squelette`.
- La voyelle retirée est stockée à part (`units.final_vowel`) et affichée.
- Un changement de lettres (يقدرون → يقدروا) reste dans la forme (E1).
- Dépend de C3 (signes d'assimilation) et de C4 (voyelle de cas à l'intérieur du mot).
- **Tests** : `test_normalize.py` (ajouts), contrôle « rien n'est substitué, tout est
  seulement retiré » conservé.

### 3.3 Méthode en niveaux (point 3 — SPEC §2.2 à §2.8)

- **`compare.py` → réécrit** en niveau 1 :
  codes E0–E4 et Ø ; alignement d'une paire (pivot ancré, blocs E0, appariement E0 → E3,
  préférence à l'ordre) ; opérations O1–O5 avec distance au pivot ; vecteur d'ordre et
  nombre de paires inversées ; signature ; types R1 / R2 / R3 ; filtre R3 direct.
  *Gardé* : `_identical_blocks` (blocs cherchés où qu'ils soient, du plus long au plus court).
- **`families.py` (neuf)** : graphe, composantes, usages isolés, cohésion et coupures
  tracées (`cohesion_min`). *Gardé* : l'union-find de `fiche.usage_groups`.
- **`matrix.py` (neuf)** : alignement d'une famille autour du pivot, colonnes (fixe,
  relativement fixe, variable, facultative), gabarit, matrices « ambiguës », contrôle de
  cohérence paires ↔ matrice (§2.6).
- **Stockage** : tables `pair_signatures`, `families`, `matrix_cells`, `columns`,
  `templates`, `pair_matrix_diff`, `family_links` (SPEC §4), avec `config_hash`.
  Aujourd'hui rien n'est stocké (limite notée en Q17).
- **`config.yaml`** : sections `equivalence` et `usage_groups` remplacées par
  `r2_min_common`, `pivot_counts`, `cohesion_min: 0.5`, `seuil_relatif: 0.75`,
  `support_min: 3`, `occ_min_stats: 3`, `final_vowel_in_form: false`.
- **Tests** : `test_compare.py` réécrit sur les cinq cas du §2.11 (stockés par références,
  voir C5, C6) ; `test_families.py` et `test_matrix.py` neufs (famille unique autour de
  `يبسط الرزق لمن يشاء … ويقدر`, usage isolé de 90:5, gabarit, zéro écart §2.6) ;
  cas abstraits pour O3, O4, O5 et pour le « تشابه كلي » (D-07).

### 3.4 Niveau 0, identité de la racine (point 4 — SPEC §2.0, étape 3b)

- **Neuf** : `root_identity.py`, table `root_identity`, commande `identite <racine>`.
- **Côté Coran, faisable tout de suite** (aucune donnée nouvelle) : les traits du corpus
  sont déjà dans `word_segments.features`. Classement des 132 occurrences de قدر dans les
  cases ; lettres et pronoms collés affichés en couleur et ignorés pour le classement
  (v12) ; case « ambiguë » (D-23) ; validation : somme des cases = occurrences de la racine.
- **Côté « possible », dépend de téléchargements** (étape 1, voir §5 ci-dessous) :
  générateur de تصريف (état « théorique »), dictionnaires classiques (état « attestée »).
  Sans eux, la colonne « non employées » est vide et le dit.
- **Tests** : `test_root_identity.py` neuf.

### 3.5 Niveau 5, toutes les formes de la racine (point 5 — SPEC §2.12)

- **Neuf** : `root_analysis.py` — analyse de chaque forme avec le même `config_hash`,
  profils (`form_profiles`), comparaison des formes deux à deux (`form_comparisons`),
  familles et matrices globales, traitement par lots avec reprise.
- **Gardé** : `fiche.compare_companions` classe déjà les compagnons selon les trois cas du
  document (même forme / même racine, formes différentes / rien).
- **Retiré** : la comparaison de deux racines de l'interface (`قلب` / `فؤاد`, Q18) — D-17
  écarte toute comparaison entre racines. À confirmer : le document, lui, la cite.
- **Tests** : `test_root_analysis.py` neuf (يقدر / قدير ; عالم الغيب / علام الغيوب ;
  reproductibilité).

### 3.6 Statuts des résultats (point 6 — SPEC §2.7, §2.9)

- **Touché** : `stats.py` (clé des compagnons sans lemme ; jetons = cases).
- **Neuf** : contraintes entre colonnes avec permutation des remplissages ; table
  `findings` ; statuts observé / décrit / établi / robuste ; matrice des familles (§2.8).
- **Gardé** : PMI, G², permutations, graine, Benjamini-Hochberg, contrôle par sourate.
- **Tests** : `test_stats.py` adapté ; `test_constraints.py` neuf (données jouets).

### 3.7 Affichage (point 7 — étape 8)

- **Touché** : `fiche.py` (rendu), `export.py`, `web/__init__.py`, `web/index.html`,
  `assistant.py` (faits F1… sans lemme ; candidates tirées de la racine).
- **Changements** : colonnes « Lemme » et « Racine » retirées des tableaux par défaut ;
  formes proches regroupées (D-16) ; page d'accueil d'une racine = niveau 0 ; matrice,
  gabarit, contraintes ; signalement des matrices ambiguës et des écarts §2.6 ; statut
  sur chaque résultat.
- **Gardé** : FastAPI, page unique hors ligne, lignes dépliables, export CSV, impression
  PDF, scripts `.bat`.
- **Tests** : `test_web.py`, `test_fiche.py`, `test_assistant.py` adaptés.

---

## 4. Ordre de travail proposé

Chaque lot se termine par : tests verts, résumé, liste de ce qui reste incertain.

| Lot | Étape du SPEC | Contenu | Dépend de |
|---|---|---|---|
| A | 2, 3 | Cases (`units`, واو à part), clé de forme (D-03, D-04), index sans lemme. Validation : 12 versets | Q20, Q21 |
| B | 4 | Segments sur les cases ; trois découpages reconstruits | A |
| C | 3b (Coran) | Niveau 0, côté Coran, racine قدر | A |
| D | 5 | Codes E, niveau 1, familles, matrices, cohérence ; fiche A, B, C. **Fin du MVP** | A, B, Q22, Q23 |
| E | 6 | Statistique sur les cases, contraintes, statuts, niveau 4 | D |
| F | 1, 3b (possible) | Téléchargements, générateur, dictionnaires, états attestée / théorique | accord sur les sources |
| G | 6b | Niveau 5 | E |
| H | 7, 8, 9 | Bloc D sur la nouvelle fiche, interface, aide de l'IA | D à G |

Pendant les lots A à D, l'interface web et la commande `resume` ne fonctionneront plus
avec la base reconstruite. Je propose de les laisser cassées le moins longtemps possible
en adaptant un affichage minimal dès le lot D, plutôt que de maintenir deux chemins.

Version du code : 0.10.0 au lot A (la base doit être reconstruite).

---

## 5. Données à télécharger (lot F) — accord demandé avant tout téléchargement

| Ressource | Licence annoncée | Point à vérifier |
|---|---|---|
| Qutrub / libqutrub (générateur de تصريف) | à lire dans le dépôt | couverture : verbes seulement ? les noms dérivés demanderaient autre chose |
| OpenITI (zenodo.org/records/17767721) | CC BY-NC-SA 4.0 | taille de l'archive ; présence des dix dictionnaires de D-25 |
| lisan345 | **non indiquée** | le SPEC dit « demander avant usage » : je ne télécharge pas sans accord |

Rien n'a été téléchargé à ce jour pour le niveau 0.

---

## 6. Tests : vue d'ensemble

| Fichier | Sort |
|---|---|
| `test_sources`, `test_raw_counts`, `test_tanzil`, `test_buckwalter`, `test_readings` | inchangés |
| `test_ingest`, `test_normalize`, `test_segmentation` | gardés, complétés |
| `test_forms`, `test_index` | réécrits (nouvelle clé de forme, plus de niveaux `noyau` / `nu`) |
| `test_compare` | réécrit (codes E, O, R ; cas du §2.11) |
| `test_fiche`, `test_fiche_stats`, `test_stats`, `test_web`, `test_assistant` | adaptés |
| `test_units`, `test_families`, `test_matrix`, `test_root_identity`, `test_constraints`, `test_root_analysis` | neufs |

---

## 7. Ce que j'attends de l'utilisateur

1. Accord sur ce plan et sur l'ordre des lots.
2. Réponse, ou accord sur le défaut proposé, pour Q20 (quelle واو), Q21 (signes
   d'assimilation), Q22 (« même base »), Q23 (cas 4 et 5 contre la règle R2).
3. Accord pour télécharger Qutrub et OpenITI ; décision sur lisan345 (licence absente).
