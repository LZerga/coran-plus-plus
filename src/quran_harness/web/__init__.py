"""Step 8: a small web interface over the same functions as the command line.

    python -m quran_harness web        # then open http://127.0.0.1:8000

The server only reads the database. Every answer carries the parameters it was
computed with (reading, form level, segmentation, code version).
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, Response

from .. import __version__, assistant, export, fiche
from ..config import NIVEAUX, default_choices, form_level, load_config, pause_choices, with_choices

PAGE = Path(__file__).parent / "index.html"
MODES = ("forme", "racine")
LECTURES = ("hafs",)


def create_app(db_path: Path) -> FastAPI:
    app = FastAPI(title="Harnais d'étude des corrélations coraniques", version=__version__)

    def connect() -> sqlite3.Connection:
        if not db_path.is_file():
            raise HTTPException(503, "Base absente : lancer d'abord `python -m quran_harness build`.")
        return sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)

    def build(connection, text: str, mode: str, niveau: str, pause: str, lecture: str, stats: bool) -> list[fiche.Fiche]:
        if mode not in MODES:
            raise HTTPException(400, f"mode inconnu : {mode!r} (attendu : {', '.join(MODES)})")
        if lecture not in LECTURES:
            raise HTTPException(400, f"lecture indisponible : {lecture!r} (l'analyse ne porte que sur hafs)")
        try:
            config = with_choices(load_config(), niveau, pause)
        except ValueError as error:
            raise HTTPException(400, str(error)) from None
        text = text.strip()
        if not text:
            raise HTTPException(400, "Indiquer une forme ou une racine.")
        if mode == "racine":
            fiches = fiche.build_root(connection, text, config, with_stats=stats)
        else:
            fiches = fiche.build(connection, text, config, with_stats=stats)
        if not fiches:
            what = "la racine" if mode == "racine" else "la forme"
            raise HTTPException(404, f"Aucune occurrence portant une racine pour {what} {text} (niveau {niveau}).")
        return fiches

    def csv_response(text: str, name: str) -> Response:
        headers = {"Content-Disposition": f'attachment; filename="{name}.csv"'}
        return Response(text.encode("utf-8"), media_type="text/csv; charset=utf-8", headers=headers)

    niveau_default, pause_default = default_choices(load_config())

    @app.get("/", include_in_schema=False)
    def page() -> FileResponse:
        return FileResponse(PAGE, media_type="text/html; charset=utf-8")

    @app.get("/api/meta")
    def meta() -> dict:
        config = load_config()
        niveau, pause = default_choices(config)
        return {
            "version": __version__,
            "modes": list(MODES),
            "niveaux": [{"id": name, "label": label} for name, (_, label) in NIVEAUX.items()],
            "pauses": pause_choices(config),
            "lectures": list(LECTURES),
            "defaults": {"niveau": niveau, "pause": pause, "lecture": LECTURES[0]},
            "statistics": config["statistics"],
        }

    @app.get("/api/fiche")
    def get_fiche(
        q: str,
        mode: str = "forme",
        niveau: str = niveau_default,
        pause: str = pause_default,
        lecture: str = "hafs",
        stats: bool = False,
        paires: int = Query(200, ge=0, le=5000),
    ) -> dict:
        connection = connect()
        try:
            fiches = build(connection, q, mode, niveau, pause, lecture, stats)
            config = with_choices(load_config(), niveau, pause)
            cards = []
            for f in fiches:
                summary = assistant.summarise(connection, f, config, form_level(config))
                cards.append({**export.fiche_to_dict(f, paires), "summary": assistant.to_dict(summary)})
            return {"query": q.strip(), "mode": mode, "fiches": cards}
        finally:
            connection.close()

    @app.get("/api/resume")
    def get_summary(
        q: str,
        mode: str = "forme",
        niveau: str = niveau_default,
        pause: str = pause_default,
        lecture: str = "hafs",
        stats: bool = False,
        index: int = Query(0, ge=0),
        ia: bool = False,
    ) -> dict:
        """The summary of one fiche; with `ia`, rephrased by a model that is sent the facts only."""
        connection = connect()
        try:
            fiches = build(connection, q, mode, niveau, pause, lecture, stats)
            if index >= len(fiches):
                raise HTTPException(404, f"Fiche n° {index} absente : {len(fiches)} fiche(s) pour cette demande.")
            config = with_choices(load_config(), niveau, pause)
            completer = assistant.anthropic_completer(config) if ia else None
            return assistant.to_dict(assistant.summarise(connection, fiches[index], config, form_level(config), completer))
        finally:
            connection.close()

    @app.get("/api/fiche.csv")
    def get_fiche_csv(
        q: str,
        table: str,
        mode: str = "forme",
        niveau: str = niveau_default,
        pause: str = pause_default,
        lecture: str = "hafs",
        stats: bool = False,
        index: int = Query(0, ge=0),
    ) -> Response:
        if table not in export.CSV_TABLES:
            raise HTTPException(400, f"table inconnue : {table!r} (attendu : {', '.join(export.CSV_TABLES)})")
        connection = connect()
        try:
            fiches = build(connection, q, mode, niveau, pause, lecture, stats)
            if index >= len(fiches):
                raise HTTPException(404, f"Fiche n° {index} absente : {len(fiches)} fiche(s) pour cette demande.")
            return csv_response(export.fiche_to_csv(fiches[index], table), f"{table}_{mode}")
        finally:
            connection.close()

    def pair_of_fiches(connection, a: str, b: str, mode: str, niveau: str, pause: str, lecture: str):
        """For each side, the fiche of the lemma with the most occurrences, and the lemmas left aside."""
        chosen, notes = [], []
        for text in (a, b):
            fiches = build(connection, text, mode, niveau, pause, lecture, stats=False)
            best = max(fiches, key=lambda f: len(f.occurrences))
            if len(fiches) > 1:
                others = ", ".join(f.lemma for f in fiches if f is not best)
                notes.append(f"{text.strip()} : plusieurs lemmes ; retenu {best.lemma}, laissé de côté {others}.")
            chosen.append(best)
        return chosen, notes

    @app.get("/api/comparer")
    def get_comparison(
        a: str, b: str, mode: str = "forme", niveau: str = niveau_default, pause: str = pause_default, lecture: str = "hafs"
    ) -> dict:
        connection = connect()
        try:
            (first, second), notes = pair_of_fiches(connection, a, b, mode, niveau, pause, lecture)
            return {**export.companions_to_dict(first, second), "notes": notes, "mode": mode}
        finally:
            connection.close()

    @app.get("/api/comparer.csv")
    def get_comparison_csv(
        a: str, b: str, mode: str = "forme", niveau: str = niveau_default, pause: str = pause_default, lecture: str = "hafs"
    ) -> Response:
        connection = connect()
        try:
            (first, second), _ = pair_of_fiches(connection, a, b, mode, niveau, pause, lecture)
            return csv_response(export.companions_to_csv(first, second), f"compagnons_{mode}")
        finally:
            connection.close()

    return app
