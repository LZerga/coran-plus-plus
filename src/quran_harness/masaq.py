"""Reading MASAQ as a second opinion on attached pronouns.

MASAQ has no root and no lemma. It does say, for each pronoun attached to a word,
whether it is a subject or a complement, which the Quranic Arabic Corpus does not.

Its morphological tags are irregular (the same subject pronoun is tagged SUBJ_PRON,
POSS_PRON or NSUFF_MASC_PL_NOM from one word to the next), so the kind of pronoun is
read from the syntactic role, which is consistent.
"""

from __future__ import annotations

import csv
from pathlib import Path

SUBJECT_ROLES = frozenset({"AGNT", "PASS_SUBJ", "SUBJ_COP_V"})
COMPLEMENT_ROLES = frozenset({"OBJ", "GEN_CONS", "PREP_OBJ", "SUBJ_COP_PART"})
NO_SEGMENT = frozenset({"", "None", "(null)"})


def pronoun_kind(row: dict[str, str]) -> str | None:
    """"subject", "complement", or None when the row is not an attached pronoun."""
    if row["Segmented_Word"] in NO_SEGMENT:
        return None
    tag, role = row["Morph_Tag"], row["Syntactic_Role"]
    if row["Morph_Type"] == "Suffix" and tag != "REL_PRON":
        if role in SUBJECT_ROLES:
            return "subject"
        if role in COMPLEMENT_ROLES:
            return "complement"
    # له, به: here the pronoun is the stem and the preposition a prefix
    if row["Morph_Type"] == "Stem" and tag.startswith("PRON") and role == "PREP_OBJ":
        return "complement"
    return None


def read_pronoun_counts(path: Path) -> dict[tuple[int, int], list[tuple[int, int]]]:
    """For each aya, in word order: (subject pronouns, complement pronouns) of each word."""
    words: dict[tuple[int, int], dict[int, list[int]]] = {}
    with open(path, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            aya = words.setdefault((int(row["Sura_No"]), int(row["Verse_No"])), {})
            counts = aya.setdefault(int(row["Word_No"]), [0, 0])
            kind = pronoun_kind(row)
            if kind:
                counts[kind == "complement"] += 1
    return {key: [tuple(aya[n]) for n in sorted(aya)] for key, aya in words.items()}
