"""The words of a stretch of text, as the elements the method compares.

An element is one word of the text, whole (CLAUDE.md rule 3). It carries what the
equivalence scale of SPEC §2 needs: its written form, its form without clitics,
its lemmas and its roots.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass

from .config import form_level

PRONOUN_TAGS = frozenset({"PRON", "DEM", "REL"})
CONTENT_TAGS = frozenset({"N", "PN", "ADJ", "V", "IMPN"})  # never a "letter", even without a root


@dataclass(frozen=True)
class Element:
    ref: str  # sura:aya:pos
    pos: int
    text: str  # as in the base text
    written: str  # the whole word, at the comparison level
    core: str  # the word without its clitics, at the comparison level
    lemmas: frozenset[str]
    roots: frozenset[str]
    tag: str | None
    attached: tuple[tuple[str, str, str], ...] = ()  # (form, tag, kind) of what the core leaves out
    word_id: int = 0

    @property
    def is_function_word(self) -> bool:
        """A "letter" or a pronoun: no root, and not a noun or a verb."""
        return not self.roots and self.tag not in CONTENT_TAGS

    @property
    def nature(self) -> str:
        if any(kind == "stem" for _, _, kind in self.attached):
            return "lettre + pronom"  # له, به: the core is the preposition, the pronoun is set aside
        return "pronom" if self.tag in PRONOUN_TAGS else "lettre"


def _columns(config: dict) -> tuple[str, str]:
    level = config["normalization"]["comparison_level"]
    if level not in (1, 2):
        raise ValueError(f"normalization.comparison_level doit valoir 1 ou 2, pas {level!r}")
    if form_level(config) == "bare":
        if level == 1:
            raise ValueError("article_is_clitic n'est disponible qu'avec comparison_level: 2")
        return "w.text_norm2", "f.bare_norm2"
    return f"w.text_norm{level}", f"f.core_norm{level}"


class ElementLoader:
    """Reads the elements of an aya once, then hands out any stretch of it."""

    def __init__(self, connection: sqlite3.Connection, config: dict):
        self.connection = connection
        self.written_column, self.core_column = _columns(config)
        self._ayas: dict[tuple[int, int], list[Element]] = {}

    def aya(self, sura: int, aya: int) -> list[Element]:
        key = (sura, aya)
        if key not in self._ayas:
            stems: dict[int, tuple[set[str], set[str]]] = {}
            query = """SELECT s.word_id, s.root, s.lemma FROM word_segments s JOIN words w ON w.id = s.word_id
                       WHERE s.kind = 'stem' AND w.sura = ? AND w.aya = ?"""
            for word_id, root, lemma in self.connection.execute(query, key):
                roots, lemmas = stems.setdefault(word_id, (set(), set()))
                if root:
                    roots.add(root)
                if lemma:
                    lemmas.add(lemma)
            rows = self.connection.execute(
                f"""SELECT w.id, w.ref, w.pos, w.text_raw, {self.written_column}, {self.core_column},
                           w.pos_tag, f.set_aside
                    FROM words w JOIN word_forms f ON f.word_id = w.id
                    WHERE w.sura = ? AND w.aya = ? ORDER BY w.pos""",
                key,
            )
            self._ayas[key] = [
                Element(
                    ref,
                    pos,
                    text,
                    written,
                    core,
                    frozenset(stems.get(word_id, ((), ()))[1]),
                    frozenset(stems.get(word_id, ((), ()))[0]),
                    tag,
                    tuple(tuple(item) for item in json.loads(set_aside)),
                    word_id,
                )
                for word_id, ref, pos, text, written, core, tag, set_aside in rows
            ]
        return self._ayas[key]

    def span(self, sura: int, aya: int, start: int, end: int) -> list[Element]:
        words = self.aya(sura, aya)
        if not 1 <= start <= end <= len(words):
            raise ValueError(f"passage {sura}:{aya}:{start}-{end} hors du verset ({len(words)} mots)")
        return words[start - 1 : end]


def parse_span(text: str) -> tuple[int, int, int, int]:
    """`sura:aya:start-end` → numbers."""
    try:
        sura, aya, positions = text.split(":")
        start, end = positions.split("-")
        return int(sura), int(aya), int(start), int(end)
    except ValueError:
        raise ValueError(f"passage attendu sous la forme sourate:verset:début-fin, reçu {text!r}") from None
