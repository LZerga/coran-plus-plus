"""The cells (cases) the method works on, and the index of forms without lemma (D-02, D-03, D-04).

A word of the text stays one row of `words`, never modified. A cell ("unit") is
what the analysis compares: the word as written, letters and pronouns attached.
One exception (D-02): a word starting with a waw of conjunction gives two cells,
the waw and the rest of the word. Which waw counts is read from the annotation
of the corpus and from config.yaml (QUESTIONS.md, Q20).

The form of a cell is its text with its inner vowels, without recitation marks
(D-03) and without the vowel of الإعراب (D-04): the marks of the last letter, and
those of the last letter before attached complement pronouns. What is removed is
stored beside the form. Two different words written alike are kept apart by
their vowels alone; the lemma of the corpus is not read.
"""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from . import alt_roots
from .config import load_config
from .index import ALEF, ALEF_WASLA, _word_forms, search_key
from .ingest import DB_PATH
from .normalize import LETTERS, VOWEL_MARKS, Level, drop_assimilation_shadda, drop_liaison_alef, normalize, split_final_vowel

WHOLE, WAW, REST = 0, 1, 2  # units.part
_WAW_PREFIX = re.compile(r"PREFIX\|w:(\w+)\+")

SCHEMA = """
DROP VIEW IF EXISTS segment_units;
DROP VIEW IF EXISTS unit_roots;
DROP TABLE IF EXISTS units;

CREATE TABLE units (
    id           INTEGER PRIMARY KEY,
    word_id      INTEGER NOT NULL REFERENCES words (id),
    part         INTEGER NOT NULL,       -- 0 whole word | 1 detached waw | 2 rest of the word
    ref          TEXT NOT NULL UNIQUE,   -- sura:aya:word, followed by a or b when the word gives two cells
    sura         INTEGER NOT NULL,
    aya          INTEGER NOT NULL,
    pos          INTEGER NOT NULL,       -- position of the cell in its aya
    text_raw     TEXT NOT NULL,          -- piece of words.text_raw, unchanged
    form         TEXT NOT NULL,          -- what "the same form" is compared on
    skeleton     TEXT NOT NULL,          -- letters only (normalisation level 2)
    spelling     TEXT NOT NULL,          -- skeleton with the superscript alef written as an alef (typing aid)
    stem_vowel   TEXT NOT NULL,          -- marks removed before attached complement pronouns
    final_vowel  TEXT NOT NULL,          -- marks removed from the last letter
    base         TEXT NOT NULL,          -- the cell without attached letters and pronouns (codes E1, E2; Q22)
    attached     TEXT NOT NULL           -- JSON list of "kind:tag:letters" of what is attached to the base
);
CREATE INDEX units_by_word ON units (word_id);
CREATE INDEX units_by_aya ON units (sura, aya, pos);
CREATE INDEX units_by_form ON units (form);
CREATE INDEX units_by_skeleton ON units (skeleton);
CREATE INDEX units_by_spelling ON units (spelling);

-- One row per cell and per root it carries. A detached waw carries none.
CREATE VIEW unit_roots AS
SELECT DISTINCT u.id AS unit_id, s.root
FROM units u JOIN word_segments s ON s.word_id = u.word_id
WHERE u.part != 1 AND s.kind = 'stem' AND s.root IS NOT NULL;

-- A cell belongs to the segment of its word.
CREATE VIEW segment_units AS
SELECT sw.segmentation_id, u.id AS unit_id, sw.segment_id
FROM units u JOIN segment_words sw ON sw.word_id = u.word_id;
"""


@dataclass(frozen=True)
class FormSettings:
    detached_waw_tags: frozenset[str]
    assimilation_marks_in_form: bool
    final_vowel_in_form: bool
    pronoun_vowel_in_form: bool = False

    @classmethod
    def from_config(cls, config: dict) -> FormSettings:
        form = config["form"]
        return cls(
            frozenset(form["detached_waw_tags"]),
            form["assimilation_marks_in_form"],
            form["final_vowel_in_form"],
            form.get("pronoun_vowel_in_form", False),
        )


def form_of(text: str, core_end: int | None, settings: FormSettings) -> tuple[str, str, str]:
    """(form, stem vowel, final vowel) of a cell. `core_end`: where its attached complement pronouns start."""
    form, stem_vowel, final_vowel = _form_of(text, core_end, settings)
    if not settings.assimilation_marks_in_form:
        form = drop_liaison_alef(form)
    return form, stem_vowel, final_vowel


def _form_of(text: str, core_end: int | None, settings: FormSettings) -> tuple[str, str, str]:
    head, tail = (text, "") if core_end is None else (text[:core_end], text[core_end:])
    head, tail = normalize(head, Level.NO_RECITATION_MARKS), normalize(tail, Level.NO_RECITATION_MARKS)
    if not settings.assimilation_marks_in_form:
        head = drop_assimilation_shadda(head)
    if settings.final_vowel_in_form:
        return head + tail, "", ""
    # The vowel of a single letter is not الإعراب: the waw itself, or the preposition of لَهُ.
    head, stem_vowel = (head, "") if _single_letter(head) else split_final_vowel(head)
    if not tail:
        return head, "", stem_vowel
    tail, final_vowel = split_final_vowel(tail)
    # The vowel of an attached pronoun in ه (هُم / هِم، هُما / هِما، هُنّ / هِنّ) follows the case vowel
    # before it (قُلُوبُهُم / قُلُوبِهِم): it is set aside with it (D-04, Q42).
    if not settings.pronoun_vowel_in_form and len(tail) > 1 and tail[0] == "ه" and tail[1] in "ُِ":
        stem_vowel += tail[1]
        tail = tail[0] + tail[2:]
    return head + tail, stem_vowel, final_vowel


def base_of(bare: str) -> str:
    """The base of a word (QUESTIONS.md, Q22): what is left once attached letters, article and pronouns
    are set aside (`forms.WordForm.bare`), at level 1, without the marks of its last letter nor the
    alef of a tanween, a final ى and ي taken as one."""
    text = drop_assimilation_shadda(normalize(bare, Level.NO_RECITATION_MARKS))
    if not _single_letter(text):
        text, removed = split_final_vowel(text)
        if removed.startswith("ً") and text.endswith("ا"):
            text = text[:-1]
    text = drop_liaison_alef(text)
    return text[:-1] + "ى" if text.endswith("ي") else text


def _single_letter(text: str) -> bool:
    return sum(ch in LETTERS for ch in text) <= 1


def build(db_path: Path = DB_PATH, config: dict | None = None) -> dict[str, int]:
    """Add the cells to an ingested database. Returns counts for the report."""
    settings = FormSettings.from_config(config or load_config())
    connection = sqlite3.connect(db_path)
    try:
        connection.executescript(SCHEMA)
        word_forms = _word_forms(connection)
        first_prefix = {
            word_id: (form, match.group(1))
            for word_id, form, features in connection.execute(
                "SELECT word_id, form, features FROM word_segments WHERE seg_no = 1 AND kind = 'prefix'"
            )
            if (match := _WAW_PREFIX.fullmatch(features))
        }
        rows: list[tuple] = []
        detached = 0
        position: dict[tuple[int, int], int] = {}
        words = connection.execute("SELECT id, ref, sura, aya, text_raw FROM words ORDER BY id").fetchall()
        for word_id, ref, sura, aya, text in words:
            core_end = word_forms[word_id].core_end
            pieces = [(WHOLE, ref, text, core_end)]
            prefix = first_prefix.get(word_id)
            if prefix and prefix[1] in settings.detached_waw_tags:
                cut = next((i for i in range(1, len(text)) if _same_writing(text[:i], prefix[0])), None)
                if cut is None:
                    raise ValueError(f"{ref} : la واو annotée par le corpus n'est pas au début de {text!r}")
                rest_end = None if core_end is None else core_end - cut
                pieces = [(WAW, ref + "a", text[:cut], None), (REST, ref + "b", text[cut:], rest_end)]
                detached += 1
            word_form = word_forms[word_id]
            for part, unit_ref, piece, end in pieces:
                form, stem_vowel, final_vowel = form_of(piece, end, settings)
                if part == WAW:
                    base, attached = form, []
                else:
                    base = base_of(word_form.bare)
                    attached = [f"{kind}:{tag}:{normalize(text_, Level.NO_VOWELS)}" for text_, tag, kind in word_form.set_aside]
                    if part == REST:
                        attached = attached[1:]  # the detached waw is a cell of its own
                    if word_form.has_article:
                        attached.insert(0, "prefix:DET:ال")
                position[sura, aya] = position.get((sura, aya), 0) + 1
                rows.append(
                    (len(rows) + 1, word_id, part, unit_ref, sura, aya, position[sura, aya], piece, form,
                     normalize(piece, Level.NO_VOWELS), spelling_of(piece), stem_vowel, final_vowel, base,
                     json.dumps(attached, ensure_ascii=False))
                )  # fmt: skip
        connection.executemany("INSERT INTO units VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
        broken = connection.execute(
            """SELECT count(*) FROM words w WHERE w.text_raw !=
               (SELECT group_concat(text_raw, '') FROM (SELECT text_raw FROM units WHERE word_id = w.id ORDER BY id))"""
        ).fetchone()[0]
        if broken:
            raise ValueError(f"{broken} mot(s) ne sont pas redonnés par leurs cases")
        connection.execute("INSERT OR REPLACE INTO meta VALUES ('form_settings', ?)", (repr(sorted(vars(settings).items())),))
        connection.commit()
        distinct = connection.execute("SELECT count(DISTINCT form), count(DISTINCT skeleton) FROM units WHERE aya > 0").fetchone()
    finally:
        connection.close()
    return {
        "cases": len(rows),
        "واو de conjonction mises à part": detached,
        "formes distinctes (الشكل intérieur, sans voyelle finale)": distinct[0],
        "squelettes distincts": distinct[1],
    }


def _same_writing(piece: str, corpus_form: str) -> bool:
    from .forms import _neutral

    return _neutral(piece) == _neutral(corpus_form)


# --- Queries ------------------------------------------------------------------


@dataclass(frozen=True)
class FormCount:
    form: str
    occurrences: int
    ayas: int


@dataclass(frozen=True)
class Occurrence:
    unit_id: int
    ref: str  # of the cell
    word_ref: str  # sura:aya:word, the reference shown to the user
    form: str
    text: str
    roots: str  # space-separated; empty for a cell without root

    @property
    def aya_ref(self) -> str:
        return self.word_ref.rsplit(":", 1)[0]


def forms_of_root(connection: sqlite3.Connection, root: str) -> list[FormCount]:
    """Forms attested for a root, with their numbers of occurrences and of ayas. Basmalas of aya 0 left out."""
    rows = connection.execute(
        """SELECT u.form, count(*), count(DISTINCT u.sura || ':' || u.aya)
           FROM units u JOIN unit_roots r ON r.unit_id = u.id
           WHERE r.root = ? AND u.aya > 0 GROUP BY u.form ORDER BY count(*) DESC, u.form""",
        (alt_roots.fold_hamza(search_key(root)),),
    )
    return [FormCount(*row) for row in rows]


SUPERSCRIPT_ALEF = "ٰ"


def spelling_of(text: str) -> str:
    """The letters as one types them in common spelling: the superscript alef becomes an alef
    (عَٰلِمُ → عالم). Only a typing aid: never used to compare forms."""
    return search_key(text.replace(SUPERSCRIPT_ALEF, ALEF))


def _comparable(form: str) -> str:
    return form.replace(ALEF_WASLA, ALEF)


def _loose(form: str) -> str:
    return _comparable(form).replace(SUPERSCRIPT_ALEF, ALEF)


def occurrences_of_form(connection: sqlite3.Connection, typed: str, settings: FormSettings) -> list[Occurrence]:
    """Every cell that is the typed form, in text order.

    Typed without vowels, the form may cover several vocalised forms: all are
    returned, for the caller to list side by side (no silent merge). Typed with
    vowels, only the cells with that very form are returned.

    The Uthmani text often writes a long ā with a superscript alef (عَٰلِم) where common
    spelling writes an alef (عالم). When the letters typed match nothing, they are
    looked for once more with the superscript alef read as an alef.
    """
    query = """SELECT u.id, u.ref, w.ref, u.form, u.text_raw,
                      coalesce((SELECT group_concat(root, ' ') FROM unit_roots r WHERE r.unit_id = u.id), '')
               FROM units u JOIN words w ON w.id = u.word_id
               WHERE {column} = ? AND u.aya > 0 ORDER BY u.id"""
    found = [Occurrence(*row) for row in connection.execute(query.format(column="replace(u.skeleton, ?, ?)"),
                                                            (ALEF_WASLA, ALEF, search_key(typed)))]  # fmt: skip
    loose = not found
    if loose:
        found = [Occurrence(*row) for row in connection.execute(query.format(column="u.spelling"), (spelling_of(typed),))]
    if any(ch in VOWEL_MARKS for ch in typed):
        compare = _loose if loose else _comparable
        wanted = compare(form_of(typed, None, settings)[0])
        found = [o for o in found if compare(o.form) == wanted]
    return found


def by_form(occurrences: list[Occurrence]) -> dict[str, list[Occurrence]]:
    """Occurrences grouped by vocalised form, most frequent first."""
    groups: dict[str, list[Occurrence]] = {}
    for occurrence in occurrences:
        groups.setdefault(occurrence.form, []).append(occurrence)
    return dict(sorted(groups.items(), key=lambda item: -len(item[1])))


def segment_sizes(connection: sqlite3.Connection, scheme: str) -> list[int]:
    """Number of cells of each segment of a scheme, sura-opening basmalas left out."""
    rows = connection.execute(
        """SELECT count(*) FROM segment_units su
           JOIN segmentations n ON n.id = su.segmentation_id
           JOIN units u ON u.id = su.unit_id
           WHERE n.name = ? AND u.aya > 0 GROUP BY su.segment_id""",
        (scheme,),
    )
    return sorted(size for (size,) in rows)
