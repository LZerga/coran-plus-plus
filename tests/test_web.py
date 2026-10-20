"""Step 8: the web interface, in Arabic, over the same functions as the command line."""

import pytest
from fastapi.testclient import TestClient

from quran_harness import __version__, root_identity, sheet
from quran_harness.buckwalter import to_arabic
from quran_harness.config import load_config
from quran_harness.web import create_app
from quran_harness.web.markdown import to_html


@pytest.fixture(scope="module")
def client(built_db):
    return TestClient(create_app(built_db))


def test_markdown_subset_becomes_escaped_html():
    text = "# T\n\n- a **b**\n\n| x | y |\n|---|---|\n| 1<br>2 | <i> |\n\nfin `c` [l](d/e.md)"
    assert to_html(text) == (
        "<h2>T</h2>\n<ul><li>a <strong>b</strong></li></ul>\n"
        '<div class="scroll"><table><tr><th>x</th><th>y</th></tr><tr><td>1<br>2</td><td>&lt;i&gt;</td></tr></table></div>\n'
        '<p>fin <code>c</code> <a href="d/e.md" data-file="d/e.md">l</a></p>'
    )


def test_page_is_served_in_arabic_from_right_to_left(client):
    response = client.get("/")
    assert response.status_code == 200
    assert 'lang="ar" dir="rtl"' in response.text and "Coran++" in response.text


def test_meta_gives_the_pause_choices_in_arabic(client):
    meta = client.get("/api/meta").json()
    assert meta["version"] == __version__
    assert [p["label"] for p in meta["pauses"]] == ["تقطيع صارم", "تقطيع مرن", "تقطيع بالآيات"]
    assert meta["default_pause"] == "strict"


def test_home_page_of_a_root_is_its_identity_and_its_forms(client, db):
    body = client.get("/api/racine", params={"q": to_arabic("qdr")}).json()
    assert len(body["forms"]) == 46 and sum(f["occurrences"] for f in body["forms"]) == 132
    found = root_identity.identity(db, to_arabic("qdr"))
    meta = dict(db.execute("SELECT key, value FROM meta"))
    assert body["html"] == to_html(root_identity.render(found, meta))  # the page shows what the command prints


def test_sheet_of_a_form_typed_without_vowels(client, db):
    body = client.get("/api/fiche", params={"q": to_arabic("yqdr"), "pause": "souple"}).json()
    assert body["form"] == to_arabic("yaqodir")
    assert [c["occurrences"] for c in body["candidates"]] == [12, 1]
    config = load_config()
    config["segmentation"]["pause_level"] = "souple"
    meta = dict(db.execute("SELECT key, value FROM meta"))
    expected = sheet.render(sheet.build(db, to_arabic("yaqodir"), "waqf-souple", config), meta, config)
    assert body["html"] == to_html(expected)


def test_a_form_opened_with_its_vowels_is_that_form_only(client):
    body = client.get("/api/fiche", params={"q": to_arabic("yuqad~ir")}).json()
    assert [c["form"] for c in body["candidates"]] == [to_arabic("yuqad~ir")]
    assert "ورود وحيد" in body["html"]


def test_detail_shows_the_pairs(client):
    light = client.get("/api/fiche", params={"q": to_arabic("yqdr"), "pause": "souple"}).json()["html"]
    full = client.get("/api/fiche", params={"q": to_arabic("yqdr"), "pause": "souple", "detail": True}).json()["html"]
    assert "13:26:1-6 / 16:75:1-19" in full and "13:26:1-6 / 16:75:1-19" not in light


def test_comparison_of_two_forms(client):
    body = client.get("/api/comparer", params={"a": to_arabic("EAlm"), "b": to_arabic("ElAm"), "pause": "souple"}).json()
    assert "مقارنة صيغتين" in body["html"] and "تغاير" in body["html"]
    response = client.get("/api/comparer", params={"a": to_arabic("yqdr"), "b": to_arabic("EAlm")})
    assert response.status_code == 400


def test_studies_are_listed_and_opened(built_db, tmp_path, db):
    from quran_harness import study
    from quran_harness.config import load_config, with_pause

    study.run(db, to_arabic("bsT"), with_pause(load_config(), "souple"), tmp_path, with_stats=False, say=lambda *_: None)
    client = TestClient(create_app(built_db, tmp_path))
    (found,) = client.get("/api/etudes").json()["studies"]
    report = client.get("/api/etude", params={"chemin": found["path"] + "/00_التقرير.md"}).json()
    assert "دراسة الجذر" in report["html"] and 'data-file="fiches/' in report["html"]
    sheet_link = report["html"].split('data-file="')[1].split('"')[0]
    while not sheet_link.startswith("fiches/"):
        sheet_link = report["html"].split(f'data-file="{sheet_link}"')[1].split('data-file="')[1].split('"')[0]
    opened = client.get("/api/etude", params={"chemin": found["path"] + "/" + sheet_link}).json()
    assert "بطاقة الصيغة" in opened["html"]
    assert client.get("/api/etude", params={"chemin": "../config.yaml"}).status_code == 404  # never outside the studies


def test_pair(client):
    body = client.get("/api/paire", params={"a": "34:36:1-8", "b": "17:30:1-7", "pivot": to_arabic("yqdr")}).json()
    assert "تطابق جزئي (R1 partiel)" in body["html"] and "O2 استبدال" in body["html"]


@pytest.mark.parametrize(
    "url, params, status",
    [
        ("/api/racine", {"q": " "}, 400),
        ("/api/racine", {"q": "zzz"}, 404),
        ("/api/fiche", {"q": "zzz"}, 404),
        ("/api/fiche", {"q": to_arabic("yqdr"), "pause": "xyz"}, 400),
        ("/api/paire", {"a": "1:1", "b": "17:30:1-7", "pivot": "x"}, 400),
        ("/api/paire", {"a": "34:36:1-8", "b": "17:30:1-7", "pivot": to_arabic("Aldyn")}, 404),
    ],
)
def test_wrong_requests_get_a_clear_answer(client, url, params, status):
    assert client.get(url, params=params).status_code == status


def test_missing_database_is_reported(tmp_path):
    response = TestClient(create_app(tmp_path / "absent.db")).get("/api/racine", params={"q": "x"})
    assert response.status_code == 503 and "build" in response.json()["detail"]
