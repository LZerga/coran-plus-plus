"""Where the phrases quoted by the SPEC stand in the text, and how they fit the segments.

The SPEC quotes its test cases in everyday spelling, without vowels or references
(QUESTIONS.md, Q8). Each phrase is looked up, word for word, in the "simple clean"
text of Tanzil; the place found is then compared with the segments of each scheme.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

import yaml

from . import tanzil
from .normalize import letters_only
from .segmentation import scheme_names, segments_of_aya
from .sources import PROJECT_ROOT

EXAMPLES_PATH = PROJECT_ROOT / "data" / "reference" / "spec_examples.yaml"

EQUAL, INSIDE, ACROSS = "égal à un segment", "à l'intérieur d'un segment", "à cheval sur plusieurs segments"


@dataclass(frozen=True)
class Example:
    id: str
    case: int
    text: str


@dataclass(frozen=True)
class Location:
    example: Example
    sura: int
    aya: int
    start_pos: int
    end_pos: int
    fits: dict[str, tuple[str, list[str]]]  # scheme -> (relation, references of the segments touched)

    @property
    def ref(self) -> str:
        return f"{self.sura}:{self.aya}:{self.start_pos}-{self.end_pos}"


def load_examples(path: Path = EXAMPLES_PATH) -> list[Example]:
    with open(path, encoding="utf-8") as f:
        return [Example(str(e["id"]), e["case"], e["text"]) for e in yaml.safe_load(f)["examples"]]


def _simple_words(connection: sqlite3.Connection) -> dict[tuple[int, int], list[str]]:
    lines = connection.execute("SELECT sura, aya, text_simple_clean FROM ayas ORDER BY sura, aya")
    ayas: dict[tuple[int, int], list[str]] = {}
    for word in tanzil.split_lines(lines):
        ayas.setdefault((word.sura, word.aya), []).append(word.text)
    return ayas


def _fit(connection: sqlite3.Connection, scheme: str, sura: int, aya: int, start: int, end: int) -> tuple[str, list[str]]:
    touched = [s for s in segments_of_aya(connection, scheme, sura, aya) if s.start_pos <= end and s.end_pos >= start]
    if len(touched) > 1:
        relation = ACROSS
    elif (touched[0].start_pos, touched[0].end_pos) == (start, end):
        relation = EQUAL
    else:
        relation = INSIDE
    return relation, [s.ref for s in touched]


# What two spellings of a word still share: consonants, with alefs and hamzas left out.
_LEFT_OUT = frozenset("اٱأإآء")
_SAME_LETTER = str.maketrans({"ى": "ي", "ؤ": "و", "ئ": "ي"})


def _consonants(text: str) -> str:
    return "".join(ch for ch in letters_only(text).translate(_SAME_LETTER) if ch not in _LEFT_OUT)


def align_spellings(simple: list[str], base: list[str]) -> list[int] | None:
    """For each word of an aya in everyday spelling, the position of the base word that holds it.

    The everyday spelling writes some base words as two (يا أيها for يَٰٓأَيُّهَا). Words go
    one to one, except where two of them make up one base word. Returns None when
    the aya cannot be explained that way, rather than guessing.
    """
    positions: list[int] = []
    i = j = 0
    while i < len(simple) and j < len(base):
        target = _consonants(base[j])
        pair_expected = len(simple) - i > len(base) - j and i + 1 < len(simple)
        if pair_expected and _consonants(simple[i]) != target and _consonants(simple[i] + simple[i + 1]) == target:
            positions += [j + 1, j + 1]
            i += 2
        else:  # one to one, even when the two spellings of the word differ
            positions.append(j + 1)
            i += 1
        j += 1
    return positions if i == len(simple) and j == len(base) else None


def locate(connection: sqlite3.Connection, examples: list[Example]) -> tuple[list[Location], list[tuple[Example, str]]]:
    """Find every place where each phrase stands.

    Returns the places found, and the phrases that could not be placed with the reason.
    """
    simple = _simple_words(connection)
    base: dict[tuple[int, int], list[str]] = {}
    for sura, aya, text in connection.execute("SELECT sura, aya, text_raw FROM words WHERE aya > 0 ORDER BY id"):
        base.setdefault((sura, aya), []).append(text)
    schemes = scheme_names(connection)
    found: list[Location] = []
    missing: list[tuple[Example, str]] = []
    for example in examples:
        tokens = example.text.split()
        places = [
            (sura, aya, i + 1)
            for (sura, aya), words in simple.items()
            if aya > 0
            for i in range(len(words) - len(tokens) + 1)
            if words[i : i + len(tokens)] == tokens
        ]
        if not places:
            missing.append((example, "introuvable dans le texte"))
        for sura, aya, first in places:
            positions = align_spellings(simple[(sura, aya)], base[(sura, aya)])
            if positions is None:
                missing.append((example, f"trouvée en {sura}:{aya}, mais ce verset ne s'aligne pas entre les deux graphies"))
                continue
            start, end = positions[first - 1], positions[first + len(tokens) - 2]
            fits = {scheme: _fit(connection, scheme, sura, aya, start, end) for scheme in schemes}
            found.append(Location(example, sura, aya, start, end, fits))
    return found, missing
