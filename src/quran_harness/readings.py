"""Step 7: the other riwayat, as differences from the base text.

The files at hand (KFGQPC) are whole texts, one per riwaya, each written for its own
font: vowels, hamzas and small signs are not encoded the same way from one file to
the next. Only what can be compared safely is compared: the letters.

    skeleton   the letters of a word, spelling conventions folded (see `skeleton`)

Each riwaya is aligned with the base text, sura by sura, on the skeletons of the
words. What differs is recorded, with the words of both texts, as:

    lettres        one word, different letters
    mots           a group of words replaced by another group
    mot_en_plus    a word the riwaya has and the base text has not
    mot_en_moins   a word the base text has and the riwaya has not
    verset_absent  a whole aya missing from the file (a numbering matter, not a variant)

Two words spelt with or without a space (وَمَالِيَ / وَمَا لِيَ) are not a difference.

Not covered: differences in vowels only, and differences in pronunciation. They
cannot be read reliably from these files (QUESTIONS.md, Q6).
"""

from __future__ import annotations

import json
import re
import sqlite3
from collections import Counter
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path

from .ingest import DB_PATH, _verified
from .normalize import LETTERS
from .sources import load_manifest

# The KFGQPC Hafs file is not a reading to study: it is the same riwaya as the base
# text. Aligning it shows how much difference the method finds where there is none.
CALIBRATION = "hafs"
RIWAYAT = ["hafs", "shouba", "warsh", "qaloon", "doori", "soosi", "bazzi", "qumbul"]

LETTRES, MOTS, EN_PLUS, EN_MOINS, VERSET_ABSENT = "lettres", "mots", "mot_en_plus", "mot_en_moins", "verset_absent"
ANALYSED = (LETTRES, MOTS, EN_PLUS, EN_MOINS)

# Signs that stand for a letter the rasm leaves out, and letter shapes proper to one file.
_KEPT = LETTERS | {"ٰ", "ۧ", "ے", "ٮ"}
_FOLD = str.maketrans(
    {
        "أ": "ا",  # hamza on alef, under alef, madda, wasla -> alef
        "إ": "ا",
        "آ": "ا",
        "ٱ": "ا",
        "ؤ": "و",  # hamza on waw -> waw
        "ئ": "ي",  # hamza on yeh -> yeh
        "ء": None,  # hamza on the line: left out
        "ى": "ي",  # alef maksura, yeh barree, dotless beh (a hamza seat) -> yeh
        "ے": "ي",
        "ٮ": "ي",
        "ٰ": "ا",  # superscript alef -> alef
        "ۧ": "ي",  # small high yeh -> yeh
    }
)

SCHEMA = """
DROP TABLE IF EXISTS variants;
DROP TABLE IF EXISTS riwaya_ayas;
DROP TABLE IF EXISTS riwayat;

CREATE TABLE riwayat (
    id      TEXT PRIMARY KEY,
    source  TEXT NOT NULL,       -- id in data/sources.yaml
    role    TEXT NOT NULL,       -- calibration | reading
    ayas    INTEGER NOT NULL,    -- ayas in the file
    words   INTEGER NOT NULL     -- words in the file
);

-- A difference between a riwaya and the base text.
CREATE TABLE variants (
    id                INTEGER PRIMARY KEY,
    riwaya            TEXT NOT NULL REFERENCES riwayat (id),
    kind              TEXT NOT NULL,    -- lettres | mots | mot_en_plus | mot_en_moins | verset_absent
    sura              INTEGER NOT NULL,
    first_word_id     INTEGER,          -- base words concerned; for mot_en_plus, the word it follows
    last_word_id      INTEGER,          --   (NULL when it comes before the first word of the sura)
    riwaya_aya        INTEGER,          -- aya number in the riwaya's own numbering
    base_text         TEXT NOT NULL,    -- words of the base text, as written there
    variant_text      TEXT NOT NULL,    -- words of the riwaya, as written in its file
    base_skeleton     TEXT NOT NULL,
    variant_skeleton  TEXT NOT NULL
);
CREATE INDEX variants_by_word ON variants (first_word_id, last_word_id);

-- Each aya of a riwaya, in its own numbering, as a stretch of words of the base text.
CREATE TABLE riwaya_ayas (
    riwaya         TEXT NOT NULL REFERENCES riwayat (id),
    sura           INTEGER NOT NULL,
    aya            INTEGER NOT NULL,
    first_word_id  INTEGER,
    last_word_id   INTEGER,
    PRIMARY KEY (riwaya, sura, aya)
);
"""


_REPEATED_ALEF = re.compile("ا+")


def skeleton(text: str) -> str:
    """Letters of a word with spelling conventions folded; every other sign is left out.

    Alefs in a row count as one: an initial hamza followed by a long a is written
    ءَا in one file and اٰ in another.
    """
    return _REPEATED_ALEF.sub("ا", "".join(ch for ch in text if ch in _KEPT).translate(_FOLD))


@dataclass(frozen=True)
class Token:
    aya: int
    text: str


@dataclass(frozen=True)
class Variant:
    kind: str
    first: int | None  # index of the first base word concerned (of the word followed, for mot_en_plus)
    last: int | None
    riwaya_aya: int | None
    base_words: tuple[str, ...]
    variant_words: tuple[str, ...]


def read_tokens(path: Path) -> dict[int, list[Token]]:
    """Words of a KFGQPC file by sura. Tokens without a letter (aya numbers, signs) are left out."""
    with open(path, encoding="utf-8-sig") as f:
        records = json.load(f)
    sura_key = "sura_no" if "sura_no" in records[0] else "sora"
    suras: dict[int, list[Token]] = {}
    for record in records:
        tokens = suras.setdefault(int(record[sura_key]), [])
        for text in record["aya_text"].replace(" ", " ").replace("‏", "").split():
            if skeleton(text):
                tokens.append(Token(int(record["aya_no"]), text))
    return suras


def diff_sura(base: list[str], base_ayas: list[int], other: list[Token]) -> tuple[list[Variant], list[int | None]]:
    """Differences of one sura, and for each word of the riwaya the base word it stands for.

    `base` holds the words of the base text and `base_ayas` their aya numbers.
    """
    base_skeletons = [skeleton(word) for word in base]
    other_skeletons = [skeleton(token.text) for token in other]
    variants: list[Variant] = []
    stands_for: list[int | None] = [None] * len(other)
    matcher = SequenceMatcher(None, base_skeletons, other_skeletons, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        riwaya_aya = other[j1].aya if j1 < len(other) else (other[-1].aya if other else None)
        if tag == "equal" or i2 - i1 == j2 - j1:
            for i, j in zip(range(i1, i2), range(j1, j2)):
                stands_for[j] = i
                if base_skeletons[i] != other_skeletons[j]:
                    variants.append(Variant(LETTRES, i, i, other[j].aya, (base[i],), (other[j].text,)))
            continue
        for j in range(j1, j2):  # uneven stretch: every word stands for the nearest base word of it
            stands_for[j] = min(i1 + (j - j1), i2 - 1) if i2 > i1 else None
        if "".join(base_skeletons[i1:i2]) == "".join(other_skeletons[j1:j2]):
            continue  # the same letters, cut into words differently
        base_words, other_words = tuple(base[i1:i2]), tuple(token.text for token in other[j1:j2])
        if tag == "insert":
            anchor = i1 - 1 if i1 > 0 else None
            variants.append(Variant(EN_PLUS, anchor, anchor, riwaya_aya, (), other_words))
        elif tag == "delete":
            whole_ayas = (i1 == 0 or base_ayas[i1 - 1] != base_ayas[i1]) and (
                i2 == len(base) or base_ayas[i2] != base_ayas[i2 - 1]
            )
            variants.append(Variant(VERSET_ABSENT if whole_ayas else EN_MOINS, i1, i2 - 1, riwaya_aya, base_words, ()))
        else:
            variants.append(Variant(MOTS, i1, i2 - 1, riwaya_aya, base_words, other_words))
    return variants, stands_for


def apply_variants(base: list[str], variants: list[Variant]) -> list[tuple[str, int | None]]:
    """The riwaya as the base text with its variants applied: (word, index of the base word or None)."""
    replaced = {v.first: v for v in variants if v.kind in (LETTRES, MOTS, EN_MOINS, VERSET_ABSENT)}
    added_after: dict[int | None, list[Variant]] = {}
    for v in variants:
        if v.kind == EN_PLUS:
            added_after.setdefault(v.first, []).append(v)
    view: list[tuple[str, int | None]] = [(word, None) for v in added_after.get(None, []) for word in v.variant_words]
    i = 0
    while i < len(base):
        variant = replaced.get(i)
        if variant is None:
            view.append((base[i], i))
            last = i
        else:
            view += [(word, variant.first if n == 0 else None) for n, word in enumerate(variant.variant_words)]
            last = variant.last
        for added in added_after.get(last, []):
            view += [(word, None) for word in added.variant_words]
        i = last + 1
    return view


def revert_variants(view: list[tuple[str, int | None]], variants: list[Variant], n_base: int) -> list[str]:
    """The base text back from a riwaya view: the inverse of `apply_variants`."""
    base: list[str | None] = [None] * n_base
    for word, index in view:
        if index is not None:
            base[index] = word
    for v in variants:
        if v.kind != EN_PLUS:
            base[v.first : v.last + 1] = v.base_words
    if any(word is None for word in base):
        raise ValueError("vue incomplète : des mots du texte de base manquent")
    return base  # type: ignore[return-value]


def build(db_path: Path = DB_PATH) -> dict[str, int]:
    """Add the riwayat tables to an ingested database. Returns counts for the report."""
    sources = {s.id: s for s in load_manifest()}
    connection = sqlite3.connect(db_path)
    try:
        connection.executescript(SCHEMA)
        base: dict[int, list[tuple[int, int, str]]] = {}
        for word_id, sura, aya, text in connection.execute("SELECT id, sura, aya, text_raw FROM words WHERE aya > 0 ORDER BY id"):
            base.setdefault(sura, []).append((word_id, aya, text))

        report: dict[str, int] = {}
        for riwaya in RIWAYAT:
            source = _verified(sources, f"kfgqpc-{riwaya}")
            suras = read_tokens(source.path)
            role = "calibration" if riwaya == CALIBRATION else "reading"
            n_ayas = len({(sura, token.aya) for sura, tokens in suras.items() for token in tokens})
            n_words = sum(len(tokens) for tokens in suras.values())
            connection.execute("INSERT INTO riwayat VALUES (?,?,?,?,?)", (riwaya, source.id, role, n_ayas, n_words))
            kinds: Counter = Counter()
            for sura, words in base.items():
                word_ids = [word_id for word_id, _, _ in words]
                tokens = suras.get(sura, [])
                variants, stands_for = diff_sura([text for _, _, text in words], [aya for _, aya, _ in words], tokens)
                connection.executemany(
                    "INSERT INTO variants VALUES (NULL,?,?,?,?,?,?,?,?,?,?)",
                    [
                        (
                            riwaya,
                            v.kind,
                            sura,
                            None if v.first is None else word_ids[v.first],
                            None if v.last is None else word_ids[v.last],
                            v.riwaya_aya,
                            " ".join(v.base_words),
                            " ".join(v.variant_words),
                            " ".join(skeleton(w) for w in v.base_words),
                            " ".join(skeleton(w) for w in v.variant_words),
                        )
                        for v in variants
                    ],
                )
                kinds.update(v.kind for v in variants)
                spans: dict[int, list[int]] = {}
                for token, index in zip(tokens, stands_for):
                    span = spans.setdefault(token.aya, [])
                    if index is not None:
                        span.append(word_ids[index])
                connection.executemany(
                    "INSERT INTO riwaya_ayas VALUES (?,?,?,?,?)",
                    [(riwaya, sura, aya, min(ids, default=None), max(ids, default=None)) for aya, ids in spans.items()],
                )
            for kind in (LETTRES, MOTS, EN_PLUS, EN_MOINS, VERSET_ABSENT):
                report[f"{riwaya} : {kind}"] = kinds[kind]
        connection.commit()
    finally:
        connection.close()
    return report


# --- Queries ------------------------------------------------------------------


@dataclass(frozen=True)
class RecordedVariant:
    riwaya: str
    kind: str
    ref: str  # sura:aya:pos of the first base word concerned (of the word followed, for mot_en_plus)
    base_text: str
    variant_text: str
    first_word_id: int
    last_word_id: int

    @property
    def replaced_words(self) -> range:
        """Base words this variant changes or removes; an added word changes none."""
        return range(0) if self.kind == EN_PLUS else range(self.first_word_id, self.last_word_id + 1)


def is_built(connection: sqlite3.Connection) -> bool:
    return connection.execute("SELECT 1 FROM sqlite_master WHERE name = 'riwayat'").fetchone() is not None


def readings(connection: sqlite3.Connection) -> list[str]:
    """The riwayat studied (the calibration file is not one of them)."""
    return [r for (r,) in connection.execute("SELECT id FROM riwayat WHERE role = 'reading' ORDER BY rowid")]


def variants_on_words(connection: sqlite3.Connection, first_word_id: int, last_word_id: int) -> list[RecordedVariant]:
    """Analysed variants of the riwayat studied that touch a stretch of base words."""
    rows = connection.execute(
        f"""SELECT v.riwaya, v.kind, w.ref, v.base_text, v.variant_text, v.first_word_id, v.last_word_id
            FROM variants v JOIN riwayat r ON r.id = v.riwaya JOIN words w ON w.id = v.first_word_id
            WHERE r.role = 'reading' AND v.kind IN ({",".join("?" * len(ANALYSED))})
              AND v.first_word_id <= ? AND v.last_word_id >= ?
            ORDER BY v.first_word_id, r.rowid""",
        (*ANALYSED, last_word_id, first_word_id),
    )
    return [RecordedVariant(*row) for row in rows]
