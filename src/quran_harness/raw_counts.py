"""Read-only counts of suras, ayas and words in each raw file (SPEC step 1 validation).

These functions only describe what each file contains, in its own format.
Nothing here normalises or compares Arabic text.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path

# Signs the Tanzil text writes as separate tokens: pause marks (U+06D6..U+06DC),
# rub-el-hizb (U+06DE) and sajdah (U+06E9). A token made only of these is not a word.
SEPARATE_SIGNS = frozenset("ۖۗۘۙۚۛۜ۞۩")


@dataclass(frozen=True)
class Counts:
    suras: int
    ayas: int
    words: int | None  # None when the format has no word-level unit


def _counts(ayas: set[tuple[int, int]], words: int | None) -> Counts:
    return Counts(suras=len({s for s, _ in ayas}), ayas=len(ayas), words=words)


def is_sign_token(token: str) -> bool:
    return all(ch in SEPARATE_SIGNS for ch in token)


def count_tanzil(path: Path) -> Counts:
    """Tanzil "text with aya numbers": `sura|aya|text`, then a `#` comment block."""
    ayas: set[tuple[int, int]] = set()
    words = 0
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line or line.startswith("#"):
                continue
            sura, aya, text = line.split("|", 2)
            ayas.add((int(sura), int(aya)))
            words += sum(1 for token in text.split() if not is_sign_token(token))
    return _counts(ayas, words)


def _count_locations(path: Path, parenthesised: bool) -> Counts:
    """Morphology files: one segment per line, located by `sura:aya:word:segment`."""
    words: set[tuple[int, int, int]] = set()
    with open(path, encoding="utf-8") as f:
        for line in f:
            location = line.split("\t", 1)[0]
            if parenthesised:
                if not location.startswith("("):
                    continue
                location = location.strip("()")
            parts = location.split(":")
            if len(parts) != 4 or not parts[0].isdigit():
                continue
            words.add((int(parts[0]), int(parts[1]), int(parts[2])))
    return _counts({(s, a) for s, a, _ in words}, len(words))


def count_qac(path: Path) -> Counts:
    return _count_locations(path, parenthesised=True)


def count_quran_morphology(path: Path) -> Counts:
    return _count_locations(path, parenthesised=False)


def count_masaq(path: Path) -> Counts:
    words: set[tuple[int, int, int]] = set()
    with open(path, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            words.add((int(row["Sura_No"]), int(row["Verse_No"]), int(row["Word_No"])))
    return _counts({(s, a) for s, a, _ in words}, len(words))


def count_kfgqpc(path: Path) -> Counts:
    """KFGQPC JSON: one record per aya; the sura key is `sura_no` or `sora`."""
    with open(path, encoding="utf-8-sig") as f:
        records = json.load(f)
    sura_key = "sura_no" if "sura_no" in records[0] else "sora"
    ayas = {(int(r[sura_key]), int(r["aya_no"])) for r in records}
    return _counts(ayas, None)


COUNTERS = {
    "tanzil-uthmani": count_tanzil,
    "tanzil-simple-clean": count_tanzil,
    "qac-morphology": count_qac,
    "quran-morphology-mustafa0x": count_quran_morphology,
    "masaq": count_masaq,
    "kfgqpc-hafs": count_kfgqpc,
    "kfgqpc-warsh": count_kfgqpc,
    "kfgqpc-qaloon": count_kfgqpc,
    "kfgqpc-shouba": count_kfgqpc,
    "kfgqpc-doori": count_kfgqpc,
    "kfgqpc-soosi": count_kfgqpc,
    "kfgqpc-bazzi": count_kfgqpc,
    "kfgqpc-qumbul": count_kfgqpc,
}
