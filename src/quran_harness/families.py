"""Level 2 (SPEC §2.4): families traced by the typology, for one reference form.

Every segment holding the form is a row (one row per occurrence, §2.10). Every
pair of rows is compared on its own (level 1). A pair R1 or R2 links its two rows
when they share at least `families.link_min_common` elements besides the pivot;
an R3 pair links nothing. A family is a connected group of rows; a row without
link is an isolated use. When a family holds together by chaining (A like B, B
like C, A unlike C), its cohesion — the share of its inner pairs that are R1 or
R2 — falls below `cohesion_min`: its weakest links are cut, one at a time, and
every cut is recorded.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field

from . import pairs
from .units import FormSettings, occurrences_of_form

LINKING = (pairs.R1_TOTAL, pairs.R1_PARTIAL, pairs.R2)


@dataclass(frozen=True)
class FamilySettings:
    link_min_common: int
    cohesion_min: float
    letters_link: bool = False  # letters and pronouns count among the elements that link two segments (Q36)

    @classmethod
    def from_config(cls, config: dict) -> FamilySettings:
        families = config["families"]
        return cls(families["link_min_common"], families["cohesion_min"], families["letters_link"])


@dataclass(frozen=True)
class Row:
    """One occurrence of the reference form, in its segment."""

    segment_id: int
    segment_ref: str  # sura:aya:first word-last word
    cells: tuple[pairs.Cell, ...]
    pivot: int  # index of the reference form in `cells`

    @property
    def text(self) -> str:
        return " ".join(cell.text for cell in self.cells)


@dataclass
class Family:
    rows: list[int]  # indexes into Analysis.rows
    cohesion: float  # 1.0 for an isolated use
    cuts: list[tuple[int, int, int]] = field(default_factory=list)  # (row, row, weight) of the links cut

    @property
    def isolated(self) -> bool:
        return len(self.rows) == 1


@dataclass(frozen=True)
class Analysis:
    form: str
    scheme: str
    rows: tuple[Row, ...]
    signatures: dict[tuple[int, int], pairs.Signature]  # (i, j) with i < j
    families: tuple[Family, ...]
    twins: tuple[tuple[int, int], ...]  # rows sharing one segment: never counted twice

    def is_link(self, i: int, j: int, settings: FamilySettings) -> bool:
        return is_link(self.signatures[min(i, j), max(i, j)], settings)


def is_link(signature: pairs.Signature, settings: FamilySettings) -> bool:
    return any(t in LINKING for t in signature.types) and weight(signature, settings) >= settings.link_min_common


def weight(signature: pairs.Signature, settings: FamilySettings) -> int:
    """Elements two segments share besides the pivot; letters and pronouns only if `letters_link` (Q36)."""
    return signature.common_outside_pivot if settings.letters_link else signature.content_common_outside_pivot


def rows_of_form(connection: sqlite3.Connection, form: str, scheme: str) -> list[Row]:
    """The rows of a form given with its vowels as stored (`units.form`), in text order."""
    occurrences = connection.execute(
        """SELECT u.id, su.segment_id, s.sura, s.aya, s.start_pos, s.end_pos
           FROM units u JOIN segment_units su ON su.unit_id = u.id
           JOIN segmentations n ON n.id = su.segmentation_id AND n.name = ?
           JOIN segments s ON s.id = su.segment_id
           WHERE u.form = ? AND u.aya > 0 ORDER BY u.id""",
        (scheme, form),
    ).fetchall()
    rows, loaded = [], {}
    for unit_id, segment_id, sura, aya, start, end in occurrences:
        cells = loaded.setdefault(segment_id, tuple(pairs.cells_of_segment(connection, segment_id)))
        pivot = next(i for i, cell in enumerate(cells) if cell.unit_id == unit_id)
        rows.append(Row(segment_id, f"{sura}:{aya}:{start}-{end}", cells, pivot))
    return rows


def trace(rows: list[Row], signatures: dict[tuple[int, int], pairs.Signature], settings: FamilySettings) -> list[Family]:
    links = {key: weight(signature, settings) for key, signature in signatures.items() if is_link(signature, settings)}
    linking_pairs = {key for key, signature in signatures.items() if any(t in LINKING for t in signature.types)}

    def components(edges: dict[tuple[int, int], int], members: list[int]) -> list[list[int]]:
        parent = {m: m for m in members}

        def find(x: int) -> int:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        for i, j in edges:
            if i in parent and j in parent:
                parent[find(j)] = find(i)
        groups: dict[int, list[int]] = {}
        for m in members:
            groups.setdefault(find(m), []).append(m)
        return list(groups.values())

    def cohesion(members: list[int]) -> float:
        inner = [(i, j) for k, i in enumerate(members) for j in members[k + 1 :]]
        return sum(1 for pair in inner if pair in linking_pairs) / len(inner) if inner else 1.0

    families: list[Family] = []
    pending = [(group, []) for group in components(links, list(range(len(rows))))]
    while pending:
        members, cuts = pending.pop(0)
        value = cohesion(members)
        inner_links = {key: w for key, w in links.items() if key[0] in members and key[1] in members}
        if value >= settings.cohesion_min or not inner_links:
            families.append(Family(sorted(members), value, cuts))
            continue
        weakest = min(inner_links, key=lambda key: (inner_links[key], key))
        cut = (*weakest, links.pop(weakest))
        remaining = {key: w for key, w in links.items() if key[0] in members and key[1] in members}
        for group in components(remaining, members):
            pending.append((group, cuts + [cut] if weakest[0] in group or weakest[1] in group else list(cuts)))
    return sorted(families, key=lambda f: (-len(f.rows), f.rows[0]))


def analyse(
    connection: sqlite3.Connection, form: str, scheme: str, pair_settings: pairs.PairSettings, settings: FamilySettings
) -> Analysis:
    rows = rows_of_form(connection, form, scheme)
    signatures = {
        (i, j): pairs.compare(rows[i].cells, rows[i].pivot, rows[j].cells, rows[j].pivot, pair_settings)
        for i in range(len(rows))
        for j in range(i + 1, len(rows))
    }
    twins = tuple((i, j) for (i, j) in signatures if rows[i].segment_id == rows[j].segment_id)
    return Analysis(form, scheme, tuple(rows), signatures, tuple(trace(rows, signatures, settings)), twins)


def forms_for(connection: sqlite3.Connection, typed: str, form_settings: FormSettings) -> dict[str, int]:
    """Vocalised forms a typed form covers, with their numbers of occurrences."""
    counts: dict[str, int] = {}
    for occurrence in occurrences_of_form(connection, typed, form_settings):
        counts[occurrence.form] = counts.get(occurrence.form, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: -item[1]))


# --- Rendering (Markdown, light tables) -------------------------------------------


def render(analysis: Analysis, meta: dict[str, str], settings: FamilySettings, matrices: list | None = None) -> str:
    from collections import Counter

    from .labels import meta_line, t

    rows = analysis.rows
    types = Counter(" + ".join(s.types) for s in analysis.signatures.values())
    families = [f for f in analysis.families if not f.isolated]
    lines = [
        f"# {t('families_title')} — {t('form')} {analysis.form}",
        "",
        meta_line(meta, f"{t('scheme')} : {t(analysis.scheme)}"),
        "",
        f"- {t('link_rule', n=settings.link_min_common)} ؛ {t('cohesion_min')} : {settings.cohesion_min:.0%}",
        f"- {t('rows')} : {len(rows)} ؛ {t('pairs')} : {len(analysis.signatures)} ("
        + "، ".join(f"{' + '.join(t(k) for k in kinds.split(' + '))} ({kinds}) : {n}" for kinds, n in types.most_common())
        + ")",
        f"- {t('families_title')} : {len(families)} ؛ {t('isolated')} : {len(analysis.families) - len(families)}",
    ]
    if analysis.twins:
        lines.append(f"- {t('twins')} : {len(analysis.twins)}")
    head = (t("family"), t("rows"), t("cohesion"), t("cuts"), t("segments"))
    lines += ["", "| " + " | ".join(head) + " |", "|---|---|---|---|---|"]
    for number, family in enumerate(analysis.families, start=1):
        name = t("isolated") if family.isolated else str(number)
        cuts = "، ".join(f"{rows[i].segment_ref}–{rows[j].segment_ref} ({w})" for i, j, w in family.cuts) or "—"
        lines.append(
            f"| {name} | {len(family.rows)} | {family.cohesion:.0%} | {cuts} | "
            + "، ".join(rows[i].segment_ref for i in family.rows) + " |"
        )
    lines += ["", f"## {t('rows')}", "", f"| | {t('segment')} | {t('text')} |", "|---|---|---|"]
    for number, row in enumerate(rows, start=1):
        text = " ".join(f"**{c.text}**" if k == row.pivot else c.text for k, c in enumerate(row.cells))
        lines.append(f"| {number} | {row.segment_ref} | {text} |")
    if matrices:
        from .matrix import render as render_matrices

        lines += render_matrices(analysis, matrices)
    head = ("أ", "ب", t("types"), t("common_outside_pivot"), t("operations"))
    lines += ["", f"## {t('pairs')}", "", "| " + " | ".join(head) + " |", "|---|---|---|---|---|"]
    for (i, j), signature in sorted(analysis.signatures.items()):
        operations = " ".join(f"{k}×{n}" for k, n in sorted(signature.kinds().items())) or "—"
        kinds = " + ".join(f"{t(k)} ({k})" for k in signature.types)
        lines.append(
            f"| {rows[i].segment_ref} | {rows[j].segment_ref} | {kinds} | {signature.common_outside_pivot} | {operations} |"
        )
    return "\n".join(lines) + "\n"
