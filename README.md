# Coran++

Harnais d'étude des corrélations coraniques, d'après le document de recherche
« ملاحظات نقدية عامة حول العقل اللغوي العربي » (`docs/document_de_recherche.pdf`).

Auteur : Lotfi Zerga.

L'outil décrit ce qu'il observe, sans interprétation :

0. **Identité de la racine** (هوية الجذر) : formes de la racine employées dans le Coran,
   rangées selon les catégories du الصرف.
1. **Paires** : chaque paire de segments où apparaît une forme est comparée seule, et
   classée en تطابق / تشابه / اختلاف.
2. **Familles** : la typologie regroupe les segments.
3. **Matrices** d'alignement par famille (en cours).

Le texte coranique (Tanzil, lecture Hafs) n'est jamais modifié. Chaque résultat renvoie à
ses références (sourate:verset:mot), à la lecture et à la version du code.

## Documents

| Fichier | Rôle |
|---|---|
| `SPEC.md` | spécification de la méthode |
| `DECISIONS.md` | décisions de méthode de l'auteur |
| `QUESTIONS.md` | journal de développement : constats, questions, réglages |
| `CHANGELOG.md` | évolutions de la spécification |
| `data/SOURCES.md` | provenance, licences et hashes des données |

## Installation et commandes

Python 3.11 ou plus et [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run python -m quran_harness sources fetch    # télécharge les données dans data/raw/
uv run python -m quran_harness build            # construit data/processed/quran.db
uv run python -m quran_harness identite قدر     # niveau 0
uv run python -m quran_harness familles يقدر    # niveaux 1 et 2
uv run pytest                                   # tests
```

Les données téléchargées et la base construite ne sont pas versionnées : elles se
reconstruisent avec les deux premières commandes. Certaines sources interdisent l'usage
commercial (voir `data/SOURCES.md`).
