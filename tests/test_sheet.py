"""Step 5 output: the sheet of a form, new method (blocs أ, ب, ج)."""

import pytest

from quran_harness import __main__ as cli
from quran_harness import ingest
from quran_harness.buckwalter import to_arabic
from quran_harness.config import load_config
from quran_harness.sheet import LETTER, OTHER_ROOT, SAME_ROOT, build, render

CONFIG = load_config()
META = {"reading": "hafs", "code_version": "test"}
YAQDIR, YUQADDIR = to_arabic("yaqodir"), to_arabic("yuqad~ir")


@pytest.fixture(scope="module")
def yaqdir(db):
    return build(db, YAQDIR, "waqf-souple", CONFIG)


def test_identity_card(yaqdir):
    assert len(yaqdir.occurrences) == 12 and yaqdir.roots == (to_arabic("qdr"),)
    assert yaqdir.box == "فَعَلَ — مضارع معلوم (12)"  # its box in the root identity (level 0)


def test_companions_in_three_kinds(yaqdir):
    by_form = {(c.kind, c.form): c for c in yaqdir.companions}
    yabsut = by_form[(OTHER_ROOT, to_arabic("yabosuT"))]
    assert (len(yabsut.segments), yabsut.before, yabsut.after) == (9, 9, 0)
    assert (LETTER, to_arabic("wa")) in by_form  # the detached waw is a letter
    assert not [c for c in yaqdir.companions if c.kind == SAME_ROOT]  # no other form of قدر in these segments


def test_light_sheet_hides_detail_and_the_full_one_shows_it(yaqdir):
    light = render(yaqdir, META, CONFIG)
    for section in ("أ. الهوية", "ب. الارتباطات", "ج. أنواع الاستعمال", "القالب", "الحالة : ملاحظ"):
        assert section in light
    assert "أعمدة لا يملؤها إلا سطر واحد أخفيت" in light and "13:26:1-6 / 16:75:1-19" not in light
    full = render(yaqdir, META, CONFIG, detail=True)
    assert "13:26:1-6 / 16:75:1-19" in full and "أخفيت" not in full


def test_single_occurrence_is_kept_and_says_so(db):
    """D-18: a form found once is not left out; no inner typology, no statistics."""
    found = build(db, YUQADDIR, "waqf-souple", CONFIG)
    assert found.occurrences == ["73:20:17"]
    assert "ورود وحيد" in render(found, META, CONFIG)


def test_command_line(built_db, monkeypatch, capsys):
    monkeypatch.setattr(ingest, "DB_PATH", built_db)
    assert cli.main(["fiche", to_arabic("yqdr"), "--pause", "souple"]) == 0
    output = capsys.readouterr().out
    assert "بطاقة الصيغة" in output and "اختيرت" in output
    assert cli.main(["fiche", "zzz"]) == 1
