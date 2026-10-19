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


def _toy_zip(tmp_path, members: dict[str, bytes]):
    import zipfile

    archive = tmp_path / "toy.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
        for name, content in members.items():
            z.writestr(name, content)
    return archive


def test_read_archive_member_reads_only_the_named_member(tmp_path):
    from quran_harness.sources import read_archive_member

    archive = _toy_zip(tmp_path, {"a/book.txt": "لسان".encode(), "a/other.txt": b"x"})
    content = read_archive_member("https://example.invalid/toy.zip", "a/book.txt", opener=lambda _: open(archive, "rb"))
    assert content == "لسان".encode()


def test_fetch_extracts_archive_member_and_checks_hash(tmp_path, monkeypatch):
    from quran_harness import sources

    archive = _toy_zip(tmp_path, {"a/book.txt": b"abc"})
    monkeypatch.setattr(
        sources, "read_archive_member",
        lambda url, member: sources.zipfile.ZipFile(archive).read(member),
    )
    good = _source(tmp_path / "out" / "book.txt", b"abc", archive_member="a/book.txt")
    assert fetch(good) == "ok"
    assert is_read_only(good.path)
    bad = _source(tmp_path / "out2" / "book.txt", b"abd", archive_member="a/book.txt")
    assert fetch(bad) == "SHA-256 différent, fichier non conservé"
    assert not bad.path.exists()
