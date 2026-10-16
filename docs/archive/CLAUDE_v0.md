# CLAUDE.md — Harnais d'étude des corrélations coraniques

Lis ce fichier en entier avant toute action, puis lis `SPEC.md`.

## Objectif du projet
Outil Python qui implémente la méthode décrite dans le document de recherche
« ملاحظات نقدية عامة حول العقل اللغوي العربي » : étudier chaque forme du Coran
à partir de ses associations dans les segments (مقاطع) du texte, comparer les
segments (تطابق / تشابه / اختلاف), puis ajouter une couche statistique de contrôle.

## Règles non négociables
1. **Le texte coranique n'est jamais modifié.** Le texte brut reste en lecture seule
   dans `data/raw/`. Toute transformation produit un nouveau fichier dans `data/processed/`.
2. **Aucune donnée inventée.** Si une source de données est introuvable, inaccessible
   ou de licence peu claire, tu t'arrêtes et tu me le dis. Tu ne reconstruis pas
   de mémoire du texte, des racines ou des variantes de lectures.
3. **Les formes sont prises telles qu'écrites dans le texte** : un mot avec clitique
   collé (ex. لقادرون, له) reste UN seul mot. On ne le coupe pas pour la comparaison
   de formes ; les clitiques ne servent qu'à calculer un niveau de similarité.
4. **Pas d'interprétation.** Le programme décrit ce qu'il observe. Il ne produit
   jamais de phrase du type « ce mot signifie X ».
5. **Toute sortie est traçable** : chaque chiffre renvoie à des références
   (sourate:verset:mot), à la lecture utilisée et à la version du code.
6. **Tout résultat statistique est comparé à un contrôle aléatoire** avant d'être
   présenté comme significatif.
7. **Provenance et licences** : chaque jeu de données téléchargé est noté dans
   `data/SOURCES.md` (URL, date, licence, hash SHA-256). Respecter les licences
   (certaines interdisent l'usage commercial).

## Conventions
- Python 3.11+, gestionnaire `uv` (sinon `pip` + venv), tests avec `pytest`.
- Stockage : SQLite (`data/processed/quran.db`).
- Code et noms de variables en anglais ; documentation et messages utilisateur en français ;
  les termes techniques arabes gardent leur graphie arabe.
- Unicode : normalisation explicite et documentée. Ne jamais comparer du texte
  arabe sans préciser le niveau de normalisation (voir SPEC §3).
- Chaque étape se termine par : tests verts, résumé de ce qui a été fait,
  liste de ce qui reste incertain.

## Façon de travailler
- Avance étape par étape (voir `SPEC.md`). Ne passe pas à l'étape suivante
  tant que les critères de validation de l'étape en cours ne sont pas remplis.
- En cas de doute sur une définition de la méthode, ne tranche pas seul :
  note la question dans `QUESTIONS.md` et applique le paramètre par défaut du SPEC.
- Garde les choix de méthode sous forme de **paramètres de configuration**
  (`config.yaml`), pas codés en dur.
