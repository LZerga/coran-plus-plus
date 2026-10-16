# CLAUDE.md — Harnais d'étude des corrélations coraniques

Lis ce fichier en entier avant toute action, puis `CHANGELOG.md`, `SPEC.md`, `DECISIONS.md`
et `QUESTIONS.md`.

**Deux fichiers de questions, deux rôles :**
- `DECISIONS.md` (identifiants **D-01, D-02…**) vient de la conception : questions de méthode
  et décisions de l'auteur. Tu ne le modifies pas.
- `QUESTIONS.md` (identifiants **Q1, Q2…**) est ton journal de développement : constats,
  écarts, questions nées du code. Tu le tiens à jour.
- En cas de contradiction, **`DECISIONS.md` l'emporte**. Indique alors dans `QUESTIONS.md`
  quelle question Qn est réglée par quelle décision D-nn.

## Objectif du projet
Outil Python qui implémente la méthode décrite dans le document de recherche
« ملاحظات نقدية عامة حول العقل اللغوي العربي » : décrire d'abord l'identité de la racine
(formes employées dans le Coran par rapport aux formes possibles en arabe), puis, pour chaque
forme, comparer d'abord ses segments (مقاطع) deux à deux selon la typologie de l'auteur
(تطابق / تشابه / اختلاف), en déduire des familles, puis résumer chaque famille par une
matrice d'alignement (gabarit, contraintes), avec une couche statistique de contrôle.
**La typologie est première, la matrice est seconde** (SPEC §2.1).

## Règles non négociables
1. **Le texte coranique n'est jamais modifié.** Le texte brut reste en lecture seule
   dans `data/raw/`. Toute transformation produit un nouveau fichier dans `data/processed/`.
2. **Aucune donnée inventée.** Si une source de données est introuvable, inaccessible
   ou de licence peu claire, tu t'arrêtes et tu me le dis. Tu ne reconstruis pas
   de mémoire du texte, des racines ou des variantes de lectures.
3. **Les formes sont prises telles qu'écrites dans le texte** : un mot avec pronom ou
   lettre collés (ex. لقادرون, له, عليه) reste UN seul mot. On ne retire **jamais** les
   pronoms ni les autres lettres collées. **Seule exception (D-02)** : la واو de
   conjonction (وَ العاطفة) est un mot à part : ويقدر = و + يقدر, deux cases. La واو qui
   fait partie de la racine (وجد، ورث…) n'est évidemment pas séparée : on s'appuie sur
   l'annotation du corpus pour les distinguer.
4. **Seulement les notions du document : forme et racine.** Ne pas ajouter de catégories
   grammaticales (lemme, partie du discours, schème…) dans l'analyse, même si les corpus
   les fournissent. Toute nouvelle notion doit d'abord être validée et notée dans QUESTIONS.md.
   **Seule exception** : le niveau 0 (identité de la racine, SPEC §2.0) range les formes
   selon les catégories du الصرف. Ces catégories ne sont jamais utilisées aux niveaux 1 à 5.
5. **Pas d'interprétation.** Le programme décrit ce qu'il observe. Il ne produit
   jamais de phrase du type « ce mot signifie X ».
6. **Toute sortie est traçable** : chaque chiffre renvoie à des références
   (sourate:verset:mot), à la lecture utilisée et à la version du code.
7. **Tout résultat statistique est comparé à un contrôle aléatoire** avant d'être
   présenté comme significatif.
8. **Provenance et licences** : chaque jeu de données téléchargé est noté dans
   `data/SOURCES.md` (URL, date, licence, hash SHA-256). Respecter les licences
   (certaines interdisent l'usage commercial).

## Conventions
- Python 3.11+, gestionnaire `uv` (sinon `pip` + venv), tests avec `pytest`.
- Stockage : SQLite (`data/processed/quran.db`).
- Code et noms de variables en anglais ; documentation et messages utilisateur en français ;
  les termes techniques arabes gardent leur graphie arabe.
- Unicode : normalisation explicite et documentée. Ne jamais comparer du texte
  arabe sans préciser le niveau de normalisation (voir SPEC §3).
- Sorties pour l'utilisateur : tableaux allégés, colonnes essentielles seulement
  (voir SPEC, étape 8). Le détail est disponible sur demande, jamais par défaut.
- Chaque étape se termine par : tests verts, résumé de ce qui a été fait,
  liste de ce qui reste incertain.

## Façon de travailler
- **Avant chaque étape** (et au début de chaque session), lis `CHANGELOG.md`. Les fichiers
  de spécification sont mis à jour depuis une discussion de conception séparée. Si une
  entrée est plus récente que ta dernière lecture :
  1. relis `SPEC.md`, `DECISIONS.md` et ce fichier ;
  2. vérifie si le travail déjà fait est touché par les « étapes touchées » ;
  3. dis-le-moi et attends mon accord avant de modifier du code existant.
  Note dans `data/LAST_SPEC_READ.txt` la date de la dernière entrée lue.
- Tu ne modifies jamais `SPEC.md`, `CHANGELOG.md` ni `DECISIONS.md` : ils viennent de la
  conception. Tes propres questions et constats vont dans `QUESTIONS.md`.
- Avance étape par étape (voir `SPEC.md`). Ne passe pas à l'étape suivante
  tant que les critères de validation de l'étape en cours ne sont pas remplis.
- En cas de doute sur une définition de la méthode, ne tranche pas seul :
  applique la valeur par défaut de `DECISIONS.md`, ou ajoute une nouvelle question dans
  `QUESTIONS.md` avec une valeur par défaut prudente.
- Garde les choix de méthode sous forme de **paramètres de configuration**
  (`config.yaml`), pas codés en dur.
