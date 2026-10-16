# SPEC.md — Harnais d'étude des corrélations coraniques

## 0. En bref
Pour une forme (mot) du Coran, on trouve tous les segments où elle apparaît, on compare
ces segments deux à deux, on résume les associations, puis on mesure statistiquement
si ces associations dépassent le hasard. Le tout sur le texte Hafs d'abord, puis sur
les autres lectures sous forme de variantes.

---

## 1. Vocabulaire (défini par le document de recherche)

| Terme | Sens pour l'implémentation |
|---|---|
| **Forme (الصيغة)** | Un mot tel qu'écrit dans le texte, clitiques collés compris (لقادرون, له). Une seule case. |
| **Racine / lemme** | Fournis par le corpus annoté. Une racine = ensemble de ses formes attestées. |
| **Segment (المقطع)** | Partie de verset terminée par une pause (وقف). Unité d'analyse. |
| **Forme de référence** | La forme étudiée (ex. يقدر). Prise seule, puis comparée aux autres formes de sa racine. |
| **Associations** | Autres éléments du même segment : (a) formes de la même racine, (b) formes d'autres racines, (c) lettre/pronom seul ou ensemble. |
| **Position** | Début / milieu / fin de segment. |

## 2. Les trois relations entre deux segments

Les deux segments contiennent la même forme de référence. On classe leur relation :

- **تطابق (identité)** : au moins 2 éléments consécutifs identiques à l'identique.
  - totale : segments égaux ; partielle : un ou plusieurs blocs identiques.
- **تشابه (similarité)** : pas de bloc identique, mais au moins 2 éléments en commun
  (même forme, ou même racine, ou lettre + forme, ou forme + pronom) — y compris dans un
  ordre différent ou avec substitution à l'intérieur de la même racine.
- **اختلاف (différence)** : seule la forme de référence est commune.

### Échelle d'équivalence entre deux éléments (paramétrable)
```
niveau 0 : mot strictement identique
niveau 1 : même mot après retrait des clitiques (على ~ عليه)
niveau 2 : même lemme
niveau 3 : même racine
```
Par défaut : identité = niveau 0 ; similarité = niveaux 1 à 3.
C'est une interprétation de l'équipe du projet — à confirmer (voir QUESTIONS.md).

### Cas de test tirés du document (à reproduire exactement)
1. `قل إن ربي يبسط الرزق لمن يشاء من عباده ويقدر له` vs `قل إن ربي يبسط الرزق لمن يشاء ويقدر له` → identité partielle, 2 parties.
2. `قل إن ربي يبسط الرزق لمن يشاء ويقدر` vs `إن ربك يبسط الرزق لمن يشاء ويقدر` → identité partielle + similarité partielle (ربي/ربك, même racine) + un élément en plus.
3. `لا يقدرون مما كسبوا على شيء` vs `لا يقدرون على شيء مما كسبوا` → mêmes blocs, ordre différent.
4. `أيحسب أن لن يقدر عليه أحد` vs `عبدا مملوكا لا يقدر على شيء` → similarité partielle (على ~ عليه) + éléments différents.
(Les segments exacts du document : 8 comparaisons autour de `يبسط الرزق لمن يشاء من عباده ويقدر`.)

---

## 3. Données (à télécharger — Étape 1)

Claude Code doit **chercher, télécharger et vérifier** les ressources suivantes dans `data/raw/`.
Pour chacune : vérifier l'URL officielle, la licence, calculer le SHA-256, noter dans `data/SOURCES.md`.
Si un téléchargement exige un formulaire, une inscription ou une acceptation de licence faite à la main,
**s'arrêter et me demander** de le faire.

| Ressource | Usage | Source pressentie |
|---|---|---|
| Texte coranique ʿuthmānī (Hafs, éd. du Caire 1924) | Texte de base, jamais modifié | Tanzil (tanzil.net) |
| Annotation morphologique (racine, lemme, segmentation des clitiques) | Racines, lemmes, niveaux de similarité | Quranic Arabic Corpus (corpus.quran.com) — licence à lire, usage non commercial |
| Annotation alternative | Contrôle croisé des racines | MASAQ (Mendeley Data, DOI 10.17632/9yvrzxktmr), licence CC BY 3.0 |
| Variantes des lectures (القراءات) | Table de différences | **À rechercher.** Sources ouvertes à identifier (bases de données de qirāʾāt, API Coran). Ne rien inventer ; si introuvable, documenter et passer. |
| Mufahras (المعجم المفهرس) | Contrôle externe des comptages | Pas de version numérique connue : le reconstruire (étape 3) et valider avec les chiffres du document |

Remarques :
- Les annotations coupent les clitiques ; le harnais doit **les réassembler en mots entiers** (règle 3 de CLAUDE.md).
- Le texte ʿuthmānī contient des signes de récitation. Garder le texte intact et fournir une
  fonction de normalisation à niveaux (brut / sans signes de récitation / sans voyelles).
- Les identifiants de mots doivent être **stables** : `sourate:verset:position_mot`, avec
  une table de correspondance si la numérotation des versets diffère entre traditions.

---

## 4. Modèle de données (SQLite)

```
words(id, sura, aya, pos, text_raw, text_norm, root, lemma, clitics, segment_id)
segments(id, sura, aya, start_pos, end_pos, pause_level)
variants(word_id, reading, variant_text, variant_type, reciters)     # étape 7
riwayat(id, name, base)                                               # Hafs, Warsh, ...
relations(seg_a, seg_b, ref_form, rel_type, detail_json)
associations(ref_form, assoc_form, assoc_root, kind, position, count)
stats(ref_form, assoc, measure, value, p_value, baseline_info)
```

---

## 5. Étapes de construction

### Étape 1 — Mise en place et données
- Structure du projet, `pyproject.toml`, `config.yaml`, `CLAUDE.md`, `QUESTIONS.md`.
- Téléchargement et vérification des sources (§3). Remplir `data/SOURCES.md`.
- **Validation** : fichiers présents, hashes notés, nombre de sourates/versets/mots cohérent
  avec les sources (114 sourates, 6236 versets selon la numérotation Hafs).

### Étape 2 — Ingestion
- Charger texte + annotations, réassembler les mots, remplir `words`.
- Fonction de normalisation à niveaux.
- **Validation** : aucun mot perdu ni modifié ; un test compare le texte reconstruit
  au texte brut.

### Étape 3 — Index racine/forme + mufahras reconstruit
- Pour chaque racine : formes attestées et occurrences.
- **Validation** : `يقدر` apparaît dans 12 versets ; `قوم` environ 150 fois. Comparer avec le
  document ; si écart, **l'écrire dans QUESTIONS.md** au lieu de forcer le résultat.
- Comparer les deux annotations (QAC et MASAQ) et lister les désaccords de racines.

### Étape 4 — Segmentation
- Découper en segments aux marques de pause du texte ʿuthmānī et aux fins de verset.
- Paramètre `pause_level` : strict (seulement pauses obligatoires/préférables) ou souple (toutes).
- **Validation** : chaque mot appartient à exactement un segment ; résumé du nombre de
  segments par réglage.

### Étape 5 — Cœur de la méthode (MVP utilisateur)
- Pour une forme de référence : lister ses segments, extraire ses associations
  (a, b, c et position).
- Comparaison de segments deux à deux, classification تطابق/تشابه/اختلاف (§2),
  avec détail (blocs identiques, éléments en trop/manquants, ordre).
- **Algorithme conseillé** : alignement par plus longue sous-séquence commune pour les blocs
  identiques, puis appariement du reste par niveaux d'équivalence décroissants.
- **Validation** : les cas de test du §2 et les 8 comparaisons du document.
- Sortie : **fiche blocs A (carte d'identité) et B (compagnons)**.

### Étape 6 — Couche statistique
- Mesures de collocation : fréquence, PMI, log-likelihood (ou équivalent), pour chaque
  association de la forme de référence.
- **Contrôle aléatoire obligatoire** : permutation (mélange des mots entre segments en
  conservant la taille des segments) et p-valeur empirique. Seed fixe, résultats reproductibles.
- Signaler les associations dues seulement à la fréquence générale du mot (très fréquent partout).
- Ajouter blocs C (usages regroupés par ressemblance) et comparaison entre deux formes
  d'une même racine : même forme associée / même racine mais formes différentes / aucune.
- **Validation** : tests sur données jouets avec résultat connu ; reproductibilité à seed égale.

### Étape 7 — Les lectures
- Texte de base Hafs + table `variants`. Une lecture = texte de base + variantes appliquées
  (vue complète sur laquelle tout le pipeline tourne).
- Distinguer variantes **de mot ou de lettre** (analysées) et variantes **de prononciation**
  (stockées à part, ignorées par l'analyse).
- Bloc D : pour chaque association, présente dans X lectures sur N ; signaler les variantes
  qui la font disparaître.
- **Validation** : appliquer les variantes d'une lecture puis revenir au texte de base
  redonne le texte exact ; la numérotation de versets reste cohérente.
- Si les données de variantes ne sont pas obtenues à l'étape 1, cette étape reste en attente.

### Étape 8 — Interface utilisateur
- Commande `cli` (utile pour les tests) : `fiche <forme> --lecture hafs --pause strict`.
- Interface web simple (Streamlit ou FastAPI + page légère) : choisir une forme, une lecture,
  un seuil de pause ; afficher les blocs A à D ; comparer deux formes ou deux racines
  (ex. قلب / فؤاد) ; export CSV/PDF.
- Chaque ligne se déplie pour montrer le texte arabe et ses références.

### Étape 9 — Aide de l'IA (facultative)
- Résumer une fiche en langage simple, proposer des formes à comparer.
- L'IA lit uniquement des résultats déjà calculés. Elle n'écrit jamais de résultat qui
  ne vient pas du calcul. Les sorties distinguent : *calculé*, *cité d'une source*, *note humaine*.

---

## 6. Questions ouvertes (à copier dans QUESTIONS.md)
1. Définition exacte du segment : suivre strictement les marques de وقف du Mushaf ? Quel niveau de pause ?
2. Forme de référence : le document dit « comme dans le mufahras » mais garde les clitiques collés. Décision par défaut : mot écrit dans le texte ; mufahras utilisé comme contrôle.
3. L'échelle d'équivalence (niveaux 0 à 3) correspond-elle à l'intention de l'auteur ?
4. Cas non tranchés par le document : segments de longueurs différentes, ordre différent, comparaison vue comme fonction mathématique.
5. Relation entre analyse d'une forme seule et comparaison entre formes : le document dit qu'il n'y a pas encore de vision claire. Ne pas forcer de modèle.
6. Format et sources utilisables pour les variantes des 7 lectures.

## 7. Critères de réussite du MVP (étapes 1 à 5)
- Pour `يقدر` : 12 versets trouvés, ses associations avec `يشاء` et `شيء` sont retrouvées,
  les comparaisons du document sont classées comme dans le document.
- Tout est reproductible depuis zéro avec une seule commande.
- Aucun texte coranique modifié ; toutes les données ont une provenance notée.
