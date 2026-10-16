"""Step 2: load the base text and its morphological annotation into SQLite.

The words and their positions come from the Tanzil text (base text, never
modified). The Quranic Arabic Corpus only brings annotations, attached to those
words. The corpus was built on an older edition of the text, so every word is
compared with its annotated form and each difference is recorded, not corrected.
"""

from __future__ import annotations

import json
import os
import sqlite3
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from . import __version__, qac, tanzil
from .normalize import Level, letters_only, normalize, unknown_characters
from .sources import PROJECT_ROOT, Source, check, load_manifest

DB_PATH = PROJECT_ROOT / "data" / "processed" / "quran.db"

SCHEMA = """
CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);

-- aya 0 = basmala written before aya 1 (every sura except 1 and 9)
CREATE TABLE words (
    id          INTEGER PRIMARY KEY,
    ref         TEXT NOT NULL UNIQUE,   -- sura:aya:pos
    sura        INTEGER NOT NULL,
    aya         INTEGER NOT NULL,
    pos         INTEGER NOT NULL,
    text_raw    TEXT NOT NULL,          -- level 0: as in the Tanzil file
    text_norm1  TEXT NOT NULL,          -- level 1: without recitation marks
    text_norm2  TEXT NOT NULL,          -- level 2: without vowels
    sign_after  TEXT NOT NULL,          -- pause marks following the word
    qac_ref     TEXT,                   -- sura:aya:word in the Quranic Arabic Corpus
    root        TEXT,                   -- first root among the stems of the word
    lemma       TEXT,                   -- first lemma among the stems of the word
    pos_tag     TEXT,                   -- tag of the first stem
    stem_count  INTEGER NOT NULL,
    clitics     TEXT NOT NULL           -- JSON list of the prefix and suffix segments
);
CREATE INDEX words_by_aya ON words (sura, aya, pos);
CREATE INDEX words_by_root ON words (root);
CREATE INDEX words_by_lemma ON words (lemma);
CREATE INDEX words_by_norm2 ON words (text_norm2);

CREATE TABLE word_segments (
    word_id       INTEGER NOT NULL REFERENCES words (id),
    seg_no        INTEGER NOT NULL,
    qac_location  TEXT NOT NULL,        -- sura:aya:word:segment in the corpus
    kind          TEXT NOT NULL,        -- prefix | stem | suffix
    tag           TEXT NOT NULL,
    form          TEXT NOT NULL,        -- corpus form, converted to Arabic script
    form_bw       TEXT NOT NULL,        -- corpus form, as in the file
    root          TEXT,
    lemma         TEXT,
    features      TEXT NOT NULL,        -- as in the file
    PRIMARY KEY (word_id, seg_no)
);

-- Differences between a word of the base text and its form in the corpus.
CREATE TABLE alignment_notes (
    word_id   INTEGER NOT NULL REFERENCES words (id),
    kind      TEXT NOT NULL,            -- encoding | marks | letters | split | shared
    qac_form  TEXT NOT NULL
);

CREATE TABLE ayas (
    sura               INTEGER NOT NULL,
    aya                INTEGER NOT NULL,
    text_simple_clean  TEXT NOT NULL,   -- Tanzil "simple clean" line, as in the file
    PRIMARY KEY (sura, aya)
);
"""


class AlignmentError(ValueError):
    pass


@dataclass(frozen=True)
class Alignment:
    segments: qac.QacWord
    note: str | None  # None when the base word and the corpus form are identical


# The two editions of the text encode the same writing differently: a hamza or a
# small yeh carried by a tatweel in the base text is a bare character in the corpus.
_ENCODING_VARIANTS = (("ـٔ", "ء"), ("ـۧ", "ۦ"), ("ـ", ""))


def _edition_neutral(text: str) -> str:
    for variant, common in _ENCODING_VARIANTS:
        text = text.replace(variant, common)
    return text


def _note(text: str, segments: qac.QacWord) -> str | None:
    form = qac.word_form(segments)
    if text == form:
        return None
    if _edition_neutral(text) == _edition_neutral(form):
        return "encoding"
    return "marks" if letters_only(text) == letters_only(form) else "letters"


def _split(segments: qac.QacWord, first_text: str) -> tuple[qac.QacWord, qac.QacWord, str]:
    """Share the segments of one corpus word between the two base words it covers."""
    target = letters_only(first_text)
    for k in range(1, len(segments)):
        if letters_only(qac.word_form(segments[:k])) == target:
            return segments[:k], segments[k:], "split"
    return segments, segments, "shared"


def align_aya(texts: list[str], qac_words: list[qac.QacWord]) -> list[Alignment]:
    """Attach corpus words to the words of one aya.

    Words go one to one by position. Where the corpus counts one word for two of
    the base text, the letters decide where. Anything else stops the ingestion.
    """
    result: list[Alignment] = []
    i = j = 0
    while i < len(texts):
        if j == len(qac_words):
            raise AlignmentError(f"plus de mot dans le corpus pour {texts[i]!r}")
        segments = qac_words[j]
        target = letters_only(qac.word_form(segments))
        same_count_left = len(texts) - i == len(qac_words) - j
        if same_count_left or letters_only(texts[i]) == target:
            result.append(Alignment(segments, _note(texts[i], segments)))
            i += 1
        elif i + 1 < len(texts) and letters_only(texts[i] + texts[i + 1]) == target:
            first, second, note = _split(segments, texts[i])
            result += [Alignment(first, note), Alignment(second, note)]
            i += 2
        else:
            raise AlignmentError(f"{texts[i]!r} ne correspond pas à {qac.word_form(segments)!r}")
        j += 1
    if j != len(qac_words):
        raise AlignmentError(f"{len(qac_words) - j} mot(s) du corpus sans mot dans le texte")
    return result


def _first(values) -> str | None:
    return next((v for v in values if v), None)


def _verified(sources: dict[str, Source], source_id: str) -> Source:
    source = sources[source_id]
    status = check(source)
    if status != "ok":
        raise ValueError(f"source {source_id} : {status}")
    return source


def build(db_path: Path = DB_PATH) -> dict[str, int]:
    """Rebuild the database from the raw files. Returns counts for the report."""
    sources = {s.id: s for s in load_manifest()}
    text_source = _verified(sources, "tanzil-uthmani")
    simple_source = _verified(sources, "tanzil-simple-clean")
    qac_source = _verified(sources, "qac-morphology")

    words = tanzil.read_words(text_source.path)
    unknown = set().union(*(unknown_characters(w.text) for w in words))
    if unknown:
        raise ValueError(f"caractères non classés dans le texte : {sorted(hex(ord(c)) for c in unknown)}")

    by_aya: dict[tuple[int, int], list[tanzil.Word]] = {}
    for word in words:
        by_aya.setdefault((word.sura, word.aya), []).append(word)
    qac_ayas = qac.read_words(qac_source.path)
    alignments: dict[str, Alignment] = {}
    for key, qac_words in qac_ayas.items():
        aya_words = by_aya.get(key)
        if aya_words is None:
            raise AlignmentError(f"verset {key} absent du texte")
        try:
            aligned = align_aya([w.text for w in aya_words], qac_words)
        except AlignmentError as error:
            raise AlignmentError(f"verset {key[0]}:{key[1]} : {error}") from None
        alignments.update({w.ref: a for w, a in zip(aya_words, aligned)})

    word_rows, segment_rows, note_rows = [], [], []
    for word_id, word in enumerate(words, start=1):
        alignment = alignments.get(word.ref)
        segments = alignment.segments if alignment else []
        stems = [s for s in segments if s.kind == "stem"]
        clitics = [{"kind": s.kind, "form": s.form, "tag": s.tag} for s in segments if s.kind != "stem"]
        word_rows.append(
            (
                word_id,
                word.ref,
                word.sura,
                word.aya,
                word.pos,
                word.text,
                normalize(word.text, Level.NO_RECITATION_MARKS),
                normalize(word.text, Level.NO_VOWELS),
                word.sign_after,
                f"{segments[0].sura}:{segments[0].aya}:{segments[0].word}" if segments else None,
                _first(s.root for s in stems),
                _first(s.lemma for s in stems),
                stems[0].tag if stems else None,
                len(stems),
                json.dumps(clitics, ensure_ascii=False),
            )
        )
        segment_rows += [
            (word_id, n, s.location, s.kind, s.tag, s.form, s.form_bw, s.root, s.lemma, s.features)
            for n, s in enumerate(segments, start=1)
        ]
        if alignment and alignment.note:
            note_rows.append((word_id, alignment.note, qac.word_form(alignment.segments)))

    aya_rows = list(tanzil.read_lines(simple_source.path))
    meta_rows = [
        ("code_version", __version__),
        ("base_text", "tanzil-uthmani"),
        ("reading", "hafs"),
        *((f"sha256:{s.id}", s.sha256) for s in (text_source, simple_source, qac_source)),
    ]

    db_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = db_path.with_suffix(".tmp")
    tmp_path.unlink(missing_ok=True)
    connection = sqlite3.connect(tmp_path)
    try:
        connection.executescript(SCHEMA)
        connection.executemany("INSERT INTO meta VALUES (?, ?)", meta_rows)
        connection.executemany("INSERT INTO words VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", word_rows)
        connection.executemany("INSERT INTO word_segments VALUES (?,?,?,?,?,?,?,?,?,?)", segment_rows)
        connection.executemany("INSERT INTO alignment_notes VALUES (?,?,?)", note_rows)
        connection.executemany("INSERT INTO ayas VALUES (?,?,?)", aya_rows)
        connection.commit()
    finally:
        connection.close()
    os.replace(tmp_path, db_path)

    notes = Counter(kind for _, kind, _ in note_rows)
    return {
        "mots": len(word_rows),
        "mots de basmala (verset 0)": sum(1 for w in words if w.aya == tanzil.BASMALA_AYA),
        "mots annotés": sum(1 for row in word_rows if row[9]),
        "mots avec racine": sum(1 for row in word_rows if row[10]),
        "segments du corpus": len({row[2] for row in segment_rows}),
        "écarts d'encodage avec le corpus": notes["encoding"],
        "écarts de signes avec le corpus": notes["marks"],
        "écarts de lettres avec le corpus": notes["letters"],
        "mots du corpus répartis sur deux mots": notes["split"] // 2,
        "mots du corpus partagés par deux mots": notes["shared"] // 2,
    }
