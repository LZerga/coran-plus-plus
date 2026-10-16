"""Step 8: the web interface, in Arabic, over the same functions as the command line.

    python -m quran_harness web        # then open http://127.0.0.1:8000

The server only reads the database. It renders the same Markdown as the command
line (`identite`, `fiche`, `paire`) and turns it into HTML: the page shows exactly
what the command prints. Every answer carries the reading and the code version.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from .. import __version__, comparison, pairs, root_identity, sheet
from ..config import default_pause, load_config, pause_choices, with_pause
from ..families import forms_for
from ..labels import t
from ..segmentation import selected_scheme
from ..units import FormSettings, forms_of_root
from .markdown import to_html

PAGE = Path(__file__).parent / "index.html"
PAUSE_LABELS = {"strict": "waqf-strict", "souple": "waqf-souple", "verset": "aya"}


def create_app(db_path: Path) -> FastAPI:
    app = FastAPI(title="Coran++", version=__version__)

    def connect() -> tuple[sqlite3.Connection, dict[str, str]]:
        if not db_path.is_file():
            raise HTTPException(503, t("no_database"))
        connection = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
        return connection, dict(connection.execute("SELECT key, value FROM meta"))

    def configured(pause: str | None) -> dict:
        try:
            return with_pause(load_config(), pause)
        except ValueError as error:
            raise HTTPException(400, str(error)) from None

    def required(text: str) -> str:
        text = text.strip()
        if not text:
            raise HTTPException(400, t("empty_query"))
        return text

    @app.get("/", include_in_schema=False)
    def page() -> FileResponse:
        # No cache: after an update, the browser takes the new page at once.
        return FileResponse(PAGE, media_type="text/html; charset=utf-8", headers={"Cache-Control": "no-cache"})

    @app.get("/api/meta")
    def meta() -> dict:
        config = load_config()
        return {
            "version": __version__,
            "pauses": [{"id": p, "label": t(PAUSE_LABELS.get(p, p))} for p in pause_choices(config)],
            "default_pause": default_pause(config),
        }

    @app.get("/api/racine")
    def racine(q: str) -> dict:
        """Home page of a root: its identity (level 0) and the forms one can open."""
        root = required(q)
        connection, meta = connect()
        try:
            found = root_identity.identity(connection, root)
            if found is None:
                raise HTTPException(404, t("no_root"))
            forms = [{"form": f.form, "occurrences": f.occurrences, "ayas": f.ayas} for f in forms_of_root(connection, root)]
            return {"root": found.root, "html": to_html(root_identity.render(found, meta)), "forms": forms}
        finally:
            connection.close()

    @app.get("/api/fiche")
    def fiche(q: str, pause: str | None = None, detail: bool = False) -> dict:
        """The sheet of a form. Typed without vowels, the most frequent form is shown and the others listed."""
        typed = required(q)
        config = configured(pause)
        connection, meta = connect()
        try:
            candidates = forms_for(connection, typed, FormSettings.from_config(config))
            if not candidates:
                raise HTTPException(404, t("no_occurrence"))
            form = next(iter(candidates))
            found = sheet.build(connection, form, selected_scheme(config), config)
            return {
                "form": form,
                "candidates": [{"form": f, "occurrences": n} for f, n in candidates.items()],
                "html": to_html(sheet.render(found, meta, config, detail=detail)),
            }
        finally:
            connection.close()

    @app.get("/api/comparer")
    def comparer(a: str, b: str, pause: str | None = None, detail: bool = False) -> dict:
        """Two forms of the same root compared (level 5). Typed without vowels: the most frequent form of each."""
        config = configured(pause)
        connection, meta = connect()
        try:
            chosen, notes = [], []
            for typed in (required(a), required(b)):
                candidates = forms_for(connection, typed, FormSettings.from_config(config))
                if not candidates:
                    raise HTTPException(404, f"{t('no_occurrence')} ({typed})")
                form = next(iter(candidates))
                if len(candidates) > 1:
                    others = "، ".join(f"{f} ({n})" for f, n in list(candidates.items())[1:])
                    notes.append(t("retained", typed=typed, form=form, n=candidates[form], others=others))
                chosen.append(form)
            try:
                found = comparison.compare_forms(connection, *chosen, selected_scheme(config), config)
            except ValueError:
                raise HTTPException(400, t("not_same_root")) from None
            return {"forms": chosen, "notes": notes, "html": to_html(comparison.render(found, meta, detail=detail))}
        finally:
            connection.close()

    @app.get("/api/paire")
    def paire(a: str, b: str, pivot: str) -> dict:
        """Two passages compared directly around a reference form (level 1)."""
        connection, meta = connect()
        try:
            try:
                first, second = (pairs.cells_of_span(connection, *pairs.parse_span(required(x))) for x in (a, b))
            except ValueError as error:
                raise HTTPException(400, str(error)) from None
            indexes = []
            for cells in (first, second):
                index = pairs.pivot_index(cells, required(pivot))
                if index is None:
                    raise HTTPException(404, t("not_in_span", form=pivot, text=" ".join(c.text for c in cells)))
                indexes.append(index)
            signature = pairs.compare(first, indexes[0], second, indexes[1], pairs.PairSettings.from_config(load_config()))
            return {"html": to_html(pairs.render_pair(first, second, signature, a, b, pivot, meta))}
        finally:
            connection.close()

    return app
