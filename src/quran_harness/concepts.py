"""Formal concept analysis (Ganter & Wille) of a root: its forms × their companions.

A set-theory reading of the research notes (الجذر مجموعة؛ الارتباطات علاقات). From the
table « which form is found with which companion », every concept is a pair:

    extent   a set of forms
    intent   the set of companions all these forms share, and that no other form shares with all of them

Concepts are ordered by inclusion: the fewer the shared companions, the more forms. No
statistics, no threshold beyond the table itself: only sets and their intersections.

Kept in the table (docs/DIMENSIONS.md, Q36): forms with at least `min_form` occurrences,
companions that are not letters or pronouns, found with the form in at least
`min_segments` segments.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import sheet
from .labels import t


@dataclass(frozen=True)
class Concept:
    extent: frozenset[str]  # forms
    intent: frozenset[str]  # companions


def table(profiles: list, min_form: int = 2, min_segments: int = 2) -> dict[str, frozenset[str]]:
    """form -> companions (content only) found with it in at least `min_segments` segments."""
    found = {}
    for p in profiles:
        if len(p.rows) < min_form:
            continue
        companions = frozenset(c.form for c in p.companions if c.kind != sheet.LETTER and len(c.segments) >= min_segments)
        if companions:
            found[p.form] = companions
    return found


def concepts(context: dict[str, frozenset[str]]) -> list[Concept]:
    """All formal concepts: the intents are the intersections of the forms' companion sets."""
    intents: set[frozenset[str]] = set()
    for companions in context.values():
        new = {companions}
        for known in intents:
            new.add(known & companions)
        intents |= new
    result = []
    for intent in intents:
        extent = frozenset(form for form, companions in context.items() if intent <= companions)
        if extent:
            result.append(Concept(extent, intent))
    return sorted(result, key=lambda c: (-len(c.extent), -len(c.intent), sorted(c.extent)))


def render_section(found: list[Concept], context: dict[str, frozenset[str]], limit: int = 15) -> list[str]:
    shared = [c for c in found if len(c.extent) >= 2 and c.intent]
    lines = [t("concepts_note", forms=len(context)), "",
             f"| {t('forms')} | {t('shared_companions_set')} |", "|---|---|"]  # fmt: skip
    for c in shared[:limit]:
        lines.append(f"| {'، '.join(sorted(c.extent))} | {'، '.join(sorted(c.intent))} |")
    if not shared:
        lines.append("| — | — |")
    return lines
