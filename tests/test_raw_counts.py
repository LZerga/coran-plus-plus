"""Step 1 validation: sura / aya / word counts of the raw files."""

import json

import pytest

from quran_harness.raw_counts import (
    COUNTERS,
    Counts,
    count_kfgqpc,
    count_masaq,
    count_qac,
    count_quran_morphology,
    count_tanzil,
    is_sign_token,
)
from quran_harness.sources import load_manifest

SOURCES = {s.id: s for s in load_manifest()}

# Sources that follow the Hafs (Kufan) verse numbering.
HAFS_NUMBERED = [
    "tanzil-uthmani",
    "tanzil-simple-clean",
    "qac-morphology",
    "quran-morphology-mustafa0x",
    "masaq",
    "kfgqpc-hafs",
    "kfgqpc-shouba",
]

# Observed on the files pinned in data/sources.yaml. The differences between
# sources are explained in data/SOURCES.md; they are recorded, not corrected.
OBSERVED_WORDS = {
    "tanzil-uthmani": 77881,
    "tanzil-simple-clean": 78248,
    "qac-morphology": 77429,
    "quran-morphology-mustafa0x": 77429,
    "masaq": 77411,
}
OBSERVED_AYAS_OTHER_NUMBERINGS = {
    "kfgqpc-warsh": 6214,
    "kfgqpc-qaloon": 6214,
    "kfgqpc-doori": 6217,
    "kfgqpc-soosi": 6217,
    "kfgqpc-bazzi": 6220,
    "kfgqpc-qumbul": 6220,
}


@pytest.fixture(scope="module")
def counts() -> dict[str, Counts]:
    return {sid: counter(SOURCES[sid].path) for sid, counter in COUNTERS.items()}


@pytest.mark.parametrize("sid", HAFS_NUMBERED)
def test_hafs_numbering_has_114_suras_and_6236_ayas(counts, sid):
    assert (counts[sid].suras, counts[sid].ayas) == (114, 6236)


@pytest.mark.parametrize("sid", OBSERVED_AYAS_OTHER_NUMBERINGS)
def test_other_numberings_have_114_suras(counts, sid):
    assert counts[sid].suras == 114
    assert counts[sid].ayas == OBSERVED_AYAS_OTHER_NUMBERINGS[sid]


@pytest.mark.parametrize("sid", OBSERVED_WORDS)
def test_word_counts_are_the_documented_ones(counts, sid):
    assert counts[sid].words == OBSERVED_WORDS[sid]


# Dictionaries (lot F) have no sura / aya structure: checked in test_lexicon_sources.py.
LEXICON_PREFIXES = ("openiti-", "lisan345-")


def test_every_data_file_has_a_counter():
    data_files = {
        sid for sid in SOURCES if not sid.endswith("-readme") and not sid.startswith(LEXICON_PREFIXES)
    }
    assert data_files == set(COUNTERS)


# --- Parsers on toy files with known content ---------------------------------


def test_sign_tokens():
    assert is_sign_token("ۚ")
    assert not is_sign_token("abc")
    assert not is_sign_token("aۚ")


def test_count_tanzil_skips_signs_and_comment_block(tmp_path):
    path = tmp_path / "t.txt"
    path.write_text("1|1|a b ۚ c\n1|2|d\n2|1|e f\n\n# comment | with | pipes\n", encoding="utf-8")
    assert count_tanzil(path) == Counts(suras=2, ayas=3, words=6)


def test_count_qac_counts_words_not_segments(tmp_path):
    path = tmp_path / "q.txt"
    path.write_text(
        "# header\nLOCATION\tFORM\tTAG\tFEATURES\n"
        "(1:1:1:1)\tbi\tP\tPREFIX|bi+\n(1:1:1:2)\tsomi\tN\tSTEM\n(1:1:2:1)\tx\tN\tSTEM\n(2:1:1:1)\ty\tN\tSTEM\n",
        encoding="utf-8",
    )
    assert count_qac(path) == Counts(suras=2, ayas=2, words=3)


def test_count_quran_morphology(tmp_path):
    path = tmp_path / "m.txt"
    path.write_text("1:1:1:1\tx\tP\tP\n1:1:1:2\ty\tN\tN\n1:2:1:1\tz\tN\tN\n", encoding="utf-8")
    assert count_quran_morphology(path) == Counts(suras=1, ayas=2, words=2)


def test_count_masaq_handles_quoted_commas(tmp_path):
    path = tmp_path / "m.csv"
    path.write_text(
        'ID,Sura_No,Verse_No,Word_No,Segment_No,Gloss\n1,1,1,1,1,"a, b"\n1,1,1,1,2,c\n2,1,1,2,1,d\n',
        encoding="utf-8",
    )
    assert count_masaq(path) == Counts(suras=1, ayas=1, words=2)


@pytest.mark.parametrize("sura_key", ["sura_no", "sora"])
def test_count_kfgqpc_accepts_both_sura_keys(tmp_path, sura_key):
    path = tmp_path / "k.json"
    path.write_text(
        json.dumps([{sura_key: 1, "aya_no": 1}, {sura_key: 1, "aya_no": 2}, {sura_key: 2, "aya_no": 1}]),
        encoding="utf-8",
    )
    assert count_kfgqpc(path) == Counts(suras=2, ayas=3, words=None)
