"""Step 1 validation: every raw file is present, unchanged, read-only and documented."""

import pytest

from quran_harness.sources import RAW_DIR, Source, check, fetch, is_read_only, load_manifest, sha256_of

SOURCES = load_manifest()


@pytest.mark.parametrize("source", SOURCES, ids=lambda s: s.id)
def test_file_matches_manifest(source):
    assert check(source) == "ok"


@pytest.mark.parametrize("source", SOURCES, ids=lambda s: s.id)
def test_raw_file_is_read_only(source):
    assert is_read_only(source.path)


@pytest.mark.parametrize("source", SOURCES, ids=lambda s: s.id)
def test_provenance_is_recorded(source):
    assert source.url.startswith("https://")
    assert source.license
    assert source.retrieved
    assert len(source.sha256) == 64


def test_no_undocumented_file_in_raw():
    documented = {s.path for s in SOURCES}
    present = {p for p in RAW_DIR.rglob("*") if p.is_file()}
    assert present == documented


def test_manifest_ids_are_unique():
    ids = [s.id for s in SOURCES]
    assert len(ids) == len(set(ids))


def _source(path, content: bytes, **overrides) -> Source:
    import hashlib

    fields = dict(
        id="toy",
        path=path,
        url="https://example.invalid/toy",
        sha256=hashlib.sha256(content).hexdigest(),
        size=len(content),
        license="test",
        retrieved="2026-10-10",
    )
    fields.update(overrides)
    return Source(**fields)


def test_check_reports_each_kind_of_mismatch(tmp_path):
    path = tmp_path / "toy.txt"
    assert check(_source(path, b"abc")) == "absent"
    path.write_bytes(b"abc")
    assert check(_source(path, b"abc")) == "ok"
    assert sha256_of(path) == _source(path, b"abc").sha256
    assert check(_source(path, b"abcd")) == "taille différente"
    assert check(_source(path, b"abd")) == "SHA-256 différent"


def test_fetch_refuses_terms_without_explicit_acceptance(tmp_path):
    source = _source(tmp_path / "toy.txt", b"abc", requires_terms_acceptance=True)
    assert "conditions" in fetch(source)
    assert not source.path.exists()
