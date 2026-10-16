"""Step 3: index of roots and forms (a rebuilt mufahras), and annotation checks.

Three ways of saying "the same form" are kept side by side (QUESTIONS.md, Q2, Q14):

    written  the word as written, clitics attached
    core     without proclitics and complement pronouns, article kept
    bare     core without the article

Forms are compared without vowels (normalisation level 2) and always kept apart
by lemma, so that two different words written alike are never merged (Q7, Q12).
The basmala written before aya 1 (aya 0) is left out of every count (Q11).
"""

from __future__ import annotations

import json
import sqlite3
from collections import Counter
from pathlib import Path
from typing import NamedTuple

from . import alt_roots, forms, masaq
from .ingest import DB_PATH, _verified
from .normalize import Level, normalize
from .sources import load_manifest

ALEF_WASLA, ALEF = "ٱ", "ا"

SCHEMA = """
DROP VIEW IF EXISTS root_index;
DROP TABLE IF EXISTS word_forms;
DROP TABLE IF EXISTS root_differences;
DROP TABLE IF EXISTS pronoun_checks;

CREATE TABLE word_forms (
    word_id              INTEGER PRIMARY KEY REFERENCES words (id),
    core_raw             TEXT NOT NULL,
    core_norm1           TEXT NOT NULL,
    core_norm2           TEXT NOT NULL,
    bare_norm2           TEXT NOT NULL,
    has_article          INTEGER NOT NULL,
    proclitics           INTEGER NOT NULL,   -- article not counted
    subject_pronouns     INTEGER NOT NULL,
    complement_pronouns  INTEGER NOT NULL,
    elided_pronouns      INTEGER NOT NULL,   -- complement pronouns annotated but not written
    set_aside            TEXT NOT NULL       -- JSON list of [form, tag, kind] the core leaves out
);
CREATE INDEX word_forms_by_core ON word_forms (core_norm2);
CREATE INDEX word_forms_by_bare ON word_forms (bare_norm2);

-- One row per word and per root it carries (a word with two stems may carry two).
CREATE VIEW root_index AS
SELECT s.root, w.id AS word_id, w.ref, w.sura, w.aya, w.text_raw,
       w.text_norm2 AS written, f.core_norm2 AS core, f.bare_norm2 AS bare
FROM (SELECT DISTINCT word_id, root FROM word_segments
      WHERE kind = 'stem' AND root IS NOT NULL) s
JOIN words w ON w.id = s.word_id
JOIN word_forms f ON f.word_id = w.id
WHERE w.aya > 0;

-- Words whose roots differ between the corpus and its corrected fork.
CREATE TABLE root_differences (
    word_id    INTEGER NOT NULL REFERENCES words (id),
    kind       TEXT NOT NULL,          -- added | removed | changed
    qac_roots  TEXT NOT NULL,          -- space-separated, as in the corpus
    alt_roots  TEXT NOT NULL           -- space-separated, as in the fork
);

-- Words where MASAQ and the corpus-based rule count attached pronouns differently.
CREATE TABLE pronoun_checks (
    word_id            INTEGER PRIMARY KEY REFERENCES words (id),
    subject_ours       INTEGER NOT NULL,
    complement_ours    INTEGER NOT NULL,   -- written ones only
    subject_masaq      INTEGER NOT NULL,
    complement_masaq   INTEGER NOT NULL
);
"""


class _Segment(NamedTuple):
    kind: str
    tag: str
    form: str
    features: str


def _word_forms(connection: sqlite3.Connection) -> dict[int, forms.WordForm]:
    segments: dict[int, list[_Segment]] = {}
    query = "SELECT word_id, kind, tag, form, features FROM word_segments ORDER BY word_id, seg_no"
    for word_id, *segment in connection.execute(query):
        segments.setdefault(word_id, []).append(_Segment(*segment))
    return {
        word_id: forms.analyse(text, segments.get(word_id, []))
        for word_id, text in connection.execute("SELECT id, text_raw FROM words")
    }


def _root_differences(connection: sqlite3.Connection, alt: dict[str, list[str]]) -> list[tuple]:
    """Compare roots word by word. A corpus word spread over two base words is taken once."""
    qac: dict[str, list[str]] = {}
    word_of: dict[str, int] = {}
    query = """SELECT w.id, w.qac_ref, s.qac_location, s.root FROM words w
               LEFT JOIN word_segments s ON s.word_id = w.id AND s.root IS NOT NULL
               WHERE w.qac_ref IS NOT NULL ORDER BY w.id, s.seg_no"""
    seen: set[str] = set()
    for word_id, qac_ref, location, root in connection.execute(query):
        word_of.setdefault(qac_ref, word_id)
        qac.setdefault(qac_ref, [])
        if root and location not in seen:
            seen.add(location)
            qac[qac_ref].append(root)
    rows = []
    for qac_ref, ours in qac.items():
        theirs = alt.get(qac_ref, [])
        if ours == [alt_roots.fold_hamza(r) for r in theirs]:
            continue
        kind = "added" if not ours else "removed" if not theirs else "changed"
        rows.append((word_of[qac_ref], kind, " ".join(ours), " ".join(theirs)))
    return rows


def _pronoun_checks(
    connection: sqlite3.Connection,
    word_forms: dict[int, forms.WordForm],
    masaq_counts: dict[tuple[int, int], list[tuple[int, int]]],
) -> tuple[list[tuple], Counter]:
    """Compare word by word, in the ayas where both sources count the same number of words."""
    ayas: dict[tuple[int, int], list[int]] = {}
    for word_id, sura, aya in connection.execute("SELECT id, sura, aya FROM words WHERE aya > 0 ORDER BY id"):
        ayas.setdefault((sura, aya), []).append(word_id)
    rows, summary = [], Counter()
    for key, word_ids in ayas.items():
        theirs = masaq_counts.get(key, [])
        if len(theirs) != len(word_ids):
            summary["ayas_not_compared"] += 1
            continue
        for word_id, (subject, complement) in zip(word_ids, theirs):
            form = word_forms[word_id]
            written = form.complement_pronouns - form.elided_pronouns
            summary["words_compared"] += 1
            if (form.subject_pronouns, written) != (subject, complement):
                rows.append((word_id, form.subject_pronouns, written, subject, complement))
    return rows, summary


def build(db_path: Path = DB_PATH) -> dict[str, int]:
    """Add the step 3 tables to an ingested database. Returns counts for the report."""
    sources = {s.id: s for s in load_manifest()}
    alt_source = _verified(sources, "quran-morphology-mustafa0x")
    masaq_source = _verified(sources, "masaq")

    connection = sqlite3.connect(db_path)
    try:
        connection.executescript(SCHEMA)
        word_forms = _word_forms(connection)
        connection.executemany(
            "INSERT INTO word_forms VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            [
                (
                    word_id,
                    f.core,
                    normalize(f.core, Level.NO_RECITATION_MARKS),
                    normalize(f.core, Level.NO_VOWELS),
                    normalize(f.bare, Level.NO_VOWELS),
                    int(f.has_article),
                    f.proclitics,
                    f.subject_pronouns,
                    f.complement_pronouns,
                    f.elided_pronouns,
                    json.dumps(f.set_aside, ensure_ascii=False),
                )
                for word_id, f in word_forms.items()
            ],
        )
        differences = _root_differences(connection, alt_roots.read_roots(alt_source.path))
        connection.executemany("INSERT INTO root_differences VALUES (?,?,?,?)", differences)
        checks, summary = _pronoun_checks(connection, word_forms, masaq.read_pronoun_counts(masaq_source.path))
        connection.executemany("INSERT INTO pronoun_checks VALUES (?,?,?,?,?)", checks)
        connection.executemany(
            "INSERT OR REPLACE INTO meta VALUES (?, ?)",
            [(f"sha256:{s.id}", s.sha256) for s in (alt_source, masaq_source)],
        )
        connection.commit()
        kinds = Counter(kind for _, kind, _, _ in differences)
        roots = connection.execute("SELECT count(DISTINCT root) FROM root_index").fetchone()[0]
    finally:
        connection.close()
    return {
        "racines": roots,
        "racines ajoutées par la version corrigée": kinds["added"],
        "racines retirées par la version corrigée": kinds["removed"],
        "racines changées par la version corrigée": kinds["changed"],
        "mots comparés avec MASAQ (pronoms)": summary["words_compared"],
        "désaccords avec MASAQ (pronoms)": len(checks),
        "versets non comparés avec MASAQ": summary["ayas_not_compared"],
    }


# --- Queries ------------------------------------------------------------------


def search_key(text: str) -> str:
    """What a typed form is matched on: no vowels, alef wasla typed as a plain alef."""
    return normalize(text, Level.NO_VOWELS).replace(ALEF_WASLA, ALEF)
