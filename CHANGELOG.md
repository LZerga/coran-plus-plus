# CHANGELOG.md — Changements de la spécification

Ce fichier est mis à jour depuis la discussion de conception à chaque modification de
`SPEC.md`, `DECISIONS.md` ou `CLAUDE.md`. L'entrée la plus récente est en haut.
Claude Code le lit avant chaque étape (voir `CLAUDE.md`).

---

## 2026-10-12 — v12 : lettres collées au niveau 0 ; segments Hafs pour toutes les riwāyāt
- D-02 complétée : la فاء et les autres lettres collées ne sont **pas** séparées (seule la
  واو de conjonction l'est).
- SPEC §2.0 : au niveau 0, lettres et pronoms collés affichés en couleur et ignorés pour le
  classement dans les catégories du الصرف ; ils restent dans la forme aux niveaux 1 à 5.
- D-01 : les segments viennent du mushaf Hafs (marques Tanzil) et valent pour toutes les
  riwāyāt. Restent ouverts : strict/souple, et les deux extraits du document.
- Étapes touchées : 3b (affichage, classement), 4 (aucun changement de code attendu).

## 2026-10-12 — v11 : la واو de conjonction est un mot à part (D-02)
- D-02 tranchée : la forme est prise telle qu'écrite ; on ne retire **jamais** les pronoms
  ni les autres lettres collées. Seule exception : la واو de conjonction est un mot à part
  (ويقدر = و + يقدر). La واو radicale n'est pas touchée (s'appuyer sur l'annotation).
- Le réglage `match_level: 1` (« sans clitiques », QUESTIONS.md Q2) est écarté.
- Contrôle : يقدر doit se trouver dans 12 versets avec cette règle (liste dans D-02).
- La فاء de conjonction : non séparée pour l'instant (à confirmer).
- Étapes touchées : 2 (ingestion : découpage des mots), 3 (index, comptages), 4 et suivantes
  (le nombre de mots par segment change).

## 2026-10-12 — v10 : passage de la spécification v0 à la spécification actuelle
**À lire en premier.** Le code du projet a été construit sur la première spécification
(archivée dans `docs/archive/SPEC_v0.md` et `docs/archive/CLAUDE_v0.md`). Depuis, la
conception a beaucoup évolué (entrées v1 à v9 ci-dessous). Ce fichier remplace donc
`SPEC.md` et `CLAUDE.md` en entier.

**Organisation des fichiers :**
- `DECISIONS.md` (nouveau, identifiants D-nn) : questions de méthode et décisions de
  l'auteur, venant de la conception. Ne pas modifier.
- `QUESTIONS.md` (le tien, identifiants Qn) : conservé tel quel ; il reste ton journal.
  La correspondance Qn ↔ D-nn est dans `DECISIONS.md` §E.
- `docs/document_de_recherche.pdf` : le document de l'auteur, jusqu'ici absent du projet.
  Il permet de vérifier les « 8 comparaisons du document ».

**Ce que la nouvelle spécification change pour le code existant (à évaluer) :**
1. **Lemme supprimé** de l'analyse (règle 4 de CLAUDE.md, SPEC §2.2) : `compare.py` utilise
   le lemme aux niveaux 0 à 2 → remplacer par les codes E0–E4 ; le الشكل intérieur sépare
   les homographes (يَقْدِرُ / يُقَدِّرُ) sans lemme (D-03, D-04).
2. **Voyelle finale séparée** de la forme (D-04, `final_vowel_in_form = false`).
3. **Nouvelle méthode en niveaux** : paires comparées seules → familles tracées par la
   typologie → une matrice d'alignement par famille → contrôle de cohérence (SPEC §2.3 à §2.7).
   Les opérations O1–O5 et les types R1–R3 remplacent l'étiquette actuelle.
4. **Niveau 0, identité de la racine** (SPEC §2.0, étape 3b) : entièrement nouveau.
   Nouvelles données : générateur de تصريف, dictionnaires classiques (OpenITI, lisan345).
5. **Niveau 5** : toutes les formes de la racine, comparées par paires puis matrice globale.
6. **Statuts des résultats** (observé / décrit / établi / robuste, SPEC §2.9).
7. **Affichage** : tableaux allégés, formes proches regroupées (D-16), niveau 0 sans clic
   pour les formes employées.

**Ce qui ne change pas** : données déjà téléchargées (Tanzil, QAC, MASAQ, KFGQPC),
ingestion, index, segmentation (3 découpages), lectures, contrôle aléatoire, interface web
et ses scripts de lancement. Tes constats de `QUESTIONS.md` restent valables.

**Consigne** : ne réécris rien tout de suite. Produis d'abord un **plan d'adaptation**
(fichier `docs/PLAN_ADAPTATION.md`) : pour chaque point 1 à 7, ce qui est touché dans le code,
ce qui peut être gardé, l'ordre de travail proposé, et les tests à modifier. Attends
l'accord de l'utilisateur avant de coder.

## 2026-10-12 — v9 : voyelle finale (D-04)
- D-04 tranchée : la voyelle finale (الإعراب) est séparée de la forme : stockée et affichée,
  jamais utilisée pour les codes E ni les comparaisons (`final_vowel_in_form = false`).
  Un changement de lettres dû au mode (يقدرون → يقدروا) reste une différence de forme (E1).
- Étapes touchées : 2 (normalisation), 3b (affichage), 5 (comparaisons).

## 2026-10-12 — v8 : D-21 et D-23 tranchées
- D-21 : liste complète des catégories du niveau 0 validée.
- D-23 : les formes ambiguës restent dans une case « ambiguë ».
- Étapes touchées : 3b (aucun changement de méthode, défauts confirmés).

## 2026-10-12 — v7 : liste des dictionnaires classiques validée
- D-25 tranchée : les dix dictionnaires classiques proposés sont retenus, لسان العرب en
  priorité. Noter dans DECISIONS.md (section E) ceux qui manquent dans OpenITI.
- Étapes touchées : 1 (données) et 3b.

## 2026-10-12 — v6 : dictionnaires classiques uniquement
- D-24 tranchée : seuls les dictionnaires classiques comptent pour « attestée ».
- SPEC §3 : sources lexicales remplacées : OpenITI (textes intégraux des dictionnaires
  classiques, CC BY-NC-SA 4.0) + lisan345 (racines). Qabas et Arramooz écartés.
- SPEC §2.0 : méthode d'extraction des formes attestées depuis le texte des articles,
  avec contrôle manuel sur un échantillon ; formes douteuses « à vérifier ».
- Nouvelle question D-25 (liste des dictionnaires classiques).
- Étapes touchées : 1 (données) et 3b.

## 2026-10-12 — v5 : sources lexicales identifiées
- SPEC §3 : trois sources pour l'état « attestée » du niveau 0 : Qabas (principale),
  Arramooz (verbes : باب, transitivité), lisan345 (racines de لسان العرب, contrôle).
- SPEC §2.0 : la source s'affiche à côté de chaque forme « attestée ».
- Nouvelle question D-24 (classique ou arabe en général).
- Étapes touchées : 1 (données à télécharger, licences à vérifier) et 3b.

## 2026-10-12 — v4 : niveau 0, rôle du clic précisé
- Toutes les formes employées dans le Coran sont visibles directement dans les cases, avec
  leurs traits (personne, mode, nombre, genre…). Rien d'employé n'est caché.
- Le clic sert **uniquement** à montrer les formes du même genre non employées.
- Étapes touchées : 3b (affichage) et 8 (interface).

## 2026-10-12 — v3 : catégories complètes du niveau 0
- SPEC §2.0 : en-tête de la racine (ثلاثي/رباعي, nature des lettres) ; liste complète des
  أوزان verbaux (avec باب du ثلاثي، مزيد، رباعي، ملحقات) ; liste complète des types de noms
  (مصادر، مشتقات، جوامد، تصغير، نسبة) ; dimensions détaillées au clic (إسناد، حالة المضارع،
  توكيد ; عدد dont جمع التكسير، جنس، تعريف، إعراب).
- Case « ambiguë » pour les أوزان à plusieurs types (D-23).
- D-20 tranchée : dictionnaire d'abord, générateur théorique en complément.
- D-21 : liste complète proposée, à valider ; D-23 nouvelle.
- Étapes touchées : 3b seulement.

## 2026-10-12 — v2 : niveau 0, identité de la racine
- Nouveau niveau 0 (SPEC §2.0) : deux tableaux (الأفعال، الأسماء) des formes de la racine
  employées dans le Coran ; clic → formes du même genre non employées (attestées ou
  théoriques) ; ligne des catégories entièrement absentes.
- Exception à la règle 4 de CLAUDE.md : catégories du الصرف permises au niveau 0 seulement.
- Nouvelles données (§3) : générateur de تصريف, source lexicale à rechercher.
- Nouvelle étape 3b ; nouvelle table `root_identity` ; critères du MVP complétés.
- Questions : D-20, D-21 ouvertes ; D-22 tranchée.
- Étapes touchées : 1 (données à télécharger), 3b (nouvelle). Les étapes 2, 3, 4 et
  suivantes ne changent pas.

## 2026-10-12 — v1 (version de référence)
Première version complète. Points principaux :
- Méthode en cinq niveaux : paires de segments (typologie de l'auteur, codes R/E/O) →
  familles → matrices d'alignement → entre familles → toutes les formes de la racine
  (paires de formes d'abord, matrice globale ensuite).
- Seules les notions du document : forme et racine (pas de lemme).
- Couche statistique avec contrôle aléatoire ; statuts observé / décrit / établi / robuste.
- Tableaux allégés ; formes proches regroupées (même base toujours ; même racine seulement
  si présentes ensemble dans un segment de la forme étudiée).
- Formes à occurrence unique gardées, sans typologie interne ni statistique.
- Questions tranchées : D-16, D-17, D-18, D-19 (provisoire).
- Étapes touchées : toutes (version initiale).
