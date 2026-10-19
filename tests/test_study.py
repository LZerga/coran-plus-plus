"""The complete study of a root (command `etude`)."""

import pytest

from quran_harness import __main__ as cli
from quran_harness import ingest, study
from quran_harness.buckwalter import to_arabic
from quran_harness.config import load_config, with_pause


def small_config():
    config = with_pause(load_config(), "souple")
    config["statistics"]["permutations"] = 50  # enough to exercise the controls in a test
    return config


@pytest.fixture(scope="module")
def folder(db, tmp_path_factory):
    out = tmp_path_factory.mktemp("sorties")
    return study.run(db, to_arabic("bsT"), small_config(), out, with_stats=True, say=lambda *_: None)


def test_study_writes_every_part(folder):
    names = {p.name for p in folder.iterdir()}
    assert {"00_التقرير.md", "00_هوية_الجذر.md", "journal.md", "profils.csv", "paires_formes.csv", "resultats.csv",
            "etat.sqlite", "fiches", "comparaisons"} <= names  # fmt: skip
    assert len(list((folder / "fiches").iterdir())) >= 5


def test_report_puts_analysis_first_then_classification_then_description(folder):
    report = (folder / "00_التقرير.md").read_text(encoding="utf-8")
    assert report.index("## ج. التحليل") < report.index("## ب. التصنيف والتمثيل") < report.index("## أ. الوصف")
    assert "الخلط العشوائي : 50 مرة" in report


def test_journal_records_settings_and_sources(folder):
    journal = (folder / "journal.md").read_text(encoding="utf-8")
    assert "Empreinte des réglages" in journal and "tanzil-uthmani" in journal and "permutations: 50" in journal


def test_study_resumes_from_its_state(db, folder):
    """Run again with the same settings: the pairs of forms and the controls are read back, not recomputed."""
    state = study.State(folder / "etat.sqlite")
    assert state.get("findings") is not None
    assert any(state.get(name) for (name,) in state.connection.execute("SELECT name FROM steps WHERE name LIKE 'pair:%'"))
    again = study.run(db, to_arabic("bsT"), small_config(), folder.parent.parent, with_stats=True, say=lambda *_: None)
    assert again == folder


def test_settings_hash_changes_with_the_settings():
    one, other = small_config(), small_config()
    other["families"]["link_min_common"] = 2
    assert study.settings_hash(one) != study.settings_hash(other)


def test_command_line(built_db, monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(ingest, "DB_PATH", built_db)
    assert cli.main(["etude", to_arabic("bsT"), "--sans-stats", "--pause", "souple", "--sortie", str(tmp_path)]) == 0
    assert list(tmp_path.glob("*/*/00_التقرير.md"))
    assert cli.main(["etude", "zzz", "--sans-stats", "--sortie", str(tmp_path)]) == 1
