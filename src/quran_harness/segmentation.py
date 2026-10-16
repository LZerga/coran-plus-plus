"""Step 4: cutting each aya into segments (مقاطع) at the pause marks of the text.

Several ways of cutting are stored side by side, because the definition of the
segment is an open question (QUESTIONS.md, Q1). Each is a "scheme":

    aya           one segment per aya
    waqf-<level>  one segment per stretch closed by a pause mark of that level

The end of an aya always closes a segment. Which marks close one at each level
comes from config.yaml. Meaning of the marks: https://tanzil.net/docs/pause_marks
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from .config import load_config
from .ingest import DB_PATH

PAUSE_MARKS = {
    "sala": "ۖ",  # صلى : continuing is preferred
    "qala": "ۗ",  # قلى : pausing is preferred
    "lazim": "ۘ",  # م : compulsory pause
    "la": "ۙ",  # لا : pausing is not allowed
    "jaiz": "ۚ",  # ج : pausing and continuing are equally permissible
}
MUANAQA = "ۛ"  # ∴ ∴ : pause on one of the two marks, not on both
# U+06DC (small high seen, a short silence without breath) never closes a segment.

SCHEMA = """
DROP TABLE IF EXISTS segment_words;
DROP TABLE IF EXISTS segments;
DROP TABLE IF EXISTS segmentations;

CREATE TABLE segmentations (
    id      INTEGER PRIMARY KEY,
    name    TEXT NOT NULL UNIQUE,     -- aya | waqf-strict | waqf-souple
    params  TEXT NOT NULL             -- JSON: marks that close a segment, mu'anaqa choice
);

CREATE TABLE segments (
    id               INTEGER PRIMARY KEY,
    segmentation_id  INTEGER NOT NULL REFERENCES segmentations (id),
    sura             INTEGER NOT NULL,
    aya              INTEGER NOT NULL,   -- 0 = basmala written before aya 1
    seg_no           INTEGER NOT NULL,   -- 1-based position of the segment in its aya
    start_pos        INTEGER NOT NULL,   -- position in the aya of its first word
    end_pos          INTEGER NOT NULL,   -- position in the aya of its last word
    closing_mark     TEXT NOT NULL,      -- pause mark that closes it; empty at the end of an aya
    UNIQUE (segmentation_id, sura, aya, seg_no)
);

CREATE TABLE segment_words (
    segmentation_id  INTEGER NOT NULL REFERENCES segmentations (id),
    word_id          INTEGER NOT NULL REFERENCES words (id),
    segment_id       INTEGER NOT NULL REFERENCES segments (id),
    PRIMARY KEY (segmentation_id, word_id)
);
CREATE INDEX segment_words_by_segment ON segment_words (segment_id);
"""


@dataclass(frozen=True)
class Scheme:
    name: str
    closing_marks: frozenset[str] = frozenset()
    muanaqa: str = "none"  # none | first | second

    @property
    def params(self) -> str:
        names = sorted(name for name, mark in PAUSE_MARKS.items() if mark in self.closing_marks)
        return json.dumps({"closing_marks": names, "muanaqa": self.muanaqa})


def schemes_from_config(config: dict) -> list[Scheme]:
    settings = config["segmentation"]
    muanaqa = settings["muanaqa"]
    if muanaqa not in ("none", "first", "second"):
        raise ValueError(f"segmentation.muanaqa inconnu : {muanaqa!r}")
    schemes = [Scheme("aya")]
    for level, names in settings["pause_levels"].items():
        if "la" in names:
            raise ValueError("la marque « la » interdit la pause : elle ne peut pas fermer un segment")
        schemes.append(Scheme(f"waqf-{level}", frozenset(PAUSE_MARKS[name] for name in names), muanaqa))
    return schemes


def selected_scheme(config: dict) -> str:
    """Name of the scheme the configuration asks the analyses to use."""
    settings = config["segmentation"]
    return "aya" if settings["scheme"] == "aya" else f"waqf-{settings['pause_level']}"


def split_aya(signs: Sequence[str], scheme: Scheme) -> list[tuple[int, int]]:
    """Cut one aya. `signs[i]` holds the pause marks written after word i (0-based).

    Returns the segments as (first word, last word), 0-based and inclusive.
    """
    segments: list[tuple[int, int]] = []
    start, muanaqa_seen = 0, 0
    for i, sign in enumerate(signs):
        closes = any(mark in scheme.closing_marks for mark in sign)
        if MUANAQA in sign:
            muanaqa_seen += 1
            is_first = muanaqa_seen % 2 == 1
            closes = closes or scheme.muanaqa == ("first" if is_first else "second")
        if closes or i == len(signs) - 1:
            segments.append((start, i))
            start = i + 1
    return segments


def build(db_path: Path = DB_PATH, config: dict | None = None) -> dict[str, int]:
    """Add the segmentation tables to an ingested database. Returns the number of segments per scheme."""
    schemes = schemes_from_config(config or load_config())
    connection = sqlite3.connect(db_path)
    try:
        connection.executescript(SCHEMA)
        ayas: dict[tuple[int, int], list[tuple[int, int, str]]] = {}
        for word_id, sura, aya, pos, sign in connection.execute("SELECT id, sura, aya, pos, sign_after FROM words ORDER BY id"):
            ayas.setdefault((sura, aya), []).append((word_id, pos, sign))

        report: dict[str, int] = {}
        segment_id = 0
        for scheme_id, scheme in enumerate(schemes, start=1):
            connection.execute("INSERT INTO segmentations VALUES (?, ?, ?)", (scheme_id, scheme.name, scheme.params))
            segment_rows, word_rows = [], []
            for (sura, aya), words in ayas.items():
                pieces = split_aya([sign for _, _, sign in words], scheme)
                for seg_no, (first, last) in enumerate(pieces, start=1):
                    segment_id += 1
                    closing = words[last][2] if last < len(words) - 1 else ""
                    segment_rows.append((segment_id, scheme_id, sura, aya, seg_no, words[first][1], words[last][1], closing))
                    word_rows += [(scheme_id, word_id, segment_id) for word_id, _, _ in words[first : last + 1]]
            connection.executemany("INSERT INTO segments VALUES (?,?,?,?,?,?,?,?)", segment_rows)
            connection.executemany("INSERT INTO segment_words VALUES (?,?,?)", word_rows)
            report[f"segments, découpage {scheme.name}"] = len(segment_rows)
        connection.commit()
    finally:
        connection.close()
    return report


# --- Queries ------------------------------------------------------------------


@dataclass(frozen=True)
class Segment:
    scheme: str
    sura: int
    aya: int
    seg_no: int
    start_pos: int
    end_pos: int
    closing_mark: str

    @property
    def ref(self) -> str:
        return f"{self.sura}:{self.aya}:{self.start_pos}-{self.end_pos}"

    @property
    def length(self) -> int:
        return self.end_pos - self.start_pos + 1


def segments_of_aya(connection: sqlite3.Connection, scheme: str, sura: int, aya: int) -> list[Segment]:
    rows = connection.execute(
        """SELECT n.name, s.sura, s.aya, s.seg_no, s.start_pos, s.end_pos, s.closing_mark
           FROM segments s JOIN segmentations n ON n.id = s.segmentation_id
           WHERE n.name = ? AND s.sura = ? AND s.aya = ? ORDER BY s.seg_no""",
        (scheme, sura, aya),
    )
    return [Segment(*row) for row in rows]


def scheme_names(connection: sqlite3.Connection) -> list[str]:
    return [name for (name,) in connection.execute("SELECT name FROM segmentations ORDER BY id")]


def summary(connection: sqlite3.Connection, scheme: str) -> dict[str, float]:
    """Size of the segments of a scheme, sura-opening basmalas left out."""
    lengths = sorted(
        length
        for (length,) in connection.execute(
            """SELECT s.end_pos - s.start_pos + 1 FROM segments s
               JOIN segmentations n ON n.id = s.segmentation_id WHERE n.name = ? AND s.aya > 0""",
            (scheme,),
        )
    )
    return {
        "segments": len(lengths),
        "mots par segment (moyenne)": round(sum(lengths) / len(lengths), 1),
        "mots par segment (médiane)": lengths[len(lengths) // 2],
        "segment le plus long": lengths[-1],
        "segments d'un seul mot": sum(1 for n in lengths if n == 1),
    }
