"""Lot F reception checks: classical dictionaries (OpenITI) and the لسان العرب root list (lisan345).

These tests only describe the files as received; nothing is normalised or extracted here.
"""

import csv
import re

import pytest

from quran_harness.sources import load_manifest

SOURCES = {s.id: s for s in load_manifest()}

# The ten dictionaries of D-25, one OpenITI primary version each.
DICTIONARIES = ["cayn", "jamhara", "tahdhib", "sihah", "maqayis", "muhkam", "asas", "lisan", "qamus", "taj"]

# Root counts announced in the lisan345 README (Statistics section).
LISAN345_ROOTS = {"lisan345-lisan3": 6529, "lisan345-lisan4": 2551, "lisan345-lisan5": 183}

# Observed: entries tagged `### $` in the OpenITI لسان العرب (Shamela0001687, mARkdown).
LISAN_TAGGED_ENTRIES = 9155


def _read(sid: str) -> str:
    return SOURCES[sid].path.read_text(encoding="utf-8-sig")


@pytest.mark.parametrize("key", DICTIONARIES)
def test_each_dictionary_has_its_text_and_metadata(key):
    text_id, yml_id = f"openiti-{key}", f"openiti-{key}-yml"
    assert text_id in SOURCES and yml_id in SOURCES
    assert _read(text_id).startswith("######OpenITI#")
    uri = re.search(r"#VERS#URI#+: (\S+)", _read(yml_id)).group(1)
    assert SOURCES[text_id].path.name.startswith(uri)
    assert "PRIMARY_VERSION" in _read(yml_id)


@pytest.mark.parametrize("key", DICTIONARIES)
def test_openiti_text_has_no_vowel_marks(key):
    # Recorded fact (QUESTIONS.md Q33): OpenITI publishes its texts without الشكل.
    assert not re.search("[ً-ْ]", _read(f"openiti-{key}"))


def test_lisan_entries_are_tagged_and_include_qdr():
    heads = re.findall(r"^### \$ ([^:\n]+):", _read("openiti-lisan"), flags=re.M)
    assert len(re.findall(r"^### \$", _read("openiti-lisan"), flags=re.M)) == LISAN_TAGGED_ENTRIES
    assert "قدر" in heads


@pytest.mark.parametrize("sid", LISAN345_ROOTS)
def test_lisan345_root_counts_match_its_readme(sid):
    with open(SOURCES[sid].path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == LISAN345_ROOTS[sid]
    assert len({r["LAB_ar"] for r in rows}) == len(rows)


def test_lisan345_contains_qdr():
    with open(SOURCES["lisan345-lisan3"].path, encoding="utf-8-sig", newline="") as f:
        assert "قدر" in {r["LAB_ar"] for r in csv.DictReader(f)}
