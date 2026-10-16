# Coran++

**قواعد انتظام الجذر في القرآن — The regularities of Quranic roots**

A descriptive toolkit for studying how the word forms of a Quranic root associate with
other forms, letters and pronouns within verse segments. The method comes from the
author's research notes (`docs/document_de_recherche.pdf`).

Author: Lotfi Zerga.

The tool describes what it observes, without interpretation:

0. **Root identity** (هوية الجذر): the forms of a root used in the Quran, arranged by the
   categories of الصرف.
1. **Pairs**: every pair of segments containing a given form is compared on its own and
   classified as تطابق / تشابه / اختلاف.
2. **Families**: the typology groups the segments.
3. **Alignment matrices** per family (in progress).

The Quranic text (Tanzil, Hafs reading) is never modified. Every result points back to its
references (sura:aya:word), the reading used and the code version.

## Documents

The working documentation is in French; the research is written in Arabic.

| File | Role |
|---|---|
| `SPEC.md` | specification of the method |
| `DECISIONS.md` | method decisions by the author |
| `QUESTIONS.md` | development log: findings, open questions, settings |
| `CHANGELOG.md` | changes to the specification |
| `data/SOURCES.md` | provenance, licences and hashes of the data |

## Setup and commands

Python 3.11 or later and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run python -m quran_harness sources fetch    # downloads the data into data/raw/
uv run python -m quran_harness build            # builds data/processed/quran.db
uv run python -m quran_harness identite قدر     # level 0
uv run python -m quran_harness familles يقدر    # levels 1 and 2
uv run pytest                                   # tests
```

Downloaded data and the built database are not versioned: the first two commands rebuild
them. Some sources forbid commercial use (see `data/SOURCES.md`).
