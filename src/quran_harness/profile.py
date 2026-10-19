"""The profile of a form: its attributes and the dimensions of its behaviour (docs/DIMENSIONS.md).

    attributes   frequency, dispersion, place of the segment in the aya (detail)
    core         position in the segment, kinds of companions, order, repetition,
                 relations between segments, neighbourhood
    detail       contact, fixed or variable sets, letters attached to the form, forms of the
                 root in the segment, operations, families, template

Everything here is description or classification (layers وصف and تصنيف): counts read on
the segments and on the pairs of level 1. Nothing is validated here; the random controls
are in `validation.py`.
"""

from __future__ import annotations

import json
import sqlite3
from collections import Counter
from dataclasses import dataclass, field

from . import families, matrix, pairs, sheet


@dataclass(frozen=True)
class ProfileSettings:
    formula_min_block: int
    relative_min: float

    @classmethod
    def from_config(cls, config: dict) -> ProfileSettings:
        return cls(config["comparison"]["formula_min_block"], config["matrix"]["relative_min"])


@dataclass
class Profile:
    form: str
    roots: tuple[str, ...]
    analysis: families.Analysis
    matrices: tuple[matrix.Matrix, ...]
    companions: list[sheet.Companion]
    box: str
    # attributes
    suras: Counter = field(default_factory=Counter)
    aya_positions: Counter = field(default_factory=Counter)
    # core
    positions: Counter = field(default_factory=Counter)
    kinds: Counter = field(default_factory=Counter)  # by occurrences
    order: Counter = field(default_factory=Counter)  # always_before | always_after | variable, over companions in >= 2 segments
    formula_rows: int = 0
    formula_block: str = ""
    types: Counter = field(default_factory=Counter)
    left: Counter = field(default_factory=Counter)
    right: Counter = field(default_factory=Counter)
    distances: Counter = field(default_factory=Counter)  # operations of the pairs by distance to the form
    # detail
    contact: Counter = field(default_factory=Counter)  # companions' occurrences at distance 1 / farther
    root_sets: dict[str, Counter] = field(default_factory=dict)
    attached: Counter = field(default_factory=Counter)  # letters and pronouns attached to the form itself
    same_root_forms: Counter = field(default_factory=Counter)
    operations: Counter = field(default_factory=Counter)

    @property
    def rows(self) -> tuple[families.Row, ...]:
        return self.analysis.rows

    @property
    def unique(self) -> bool:
        return len(self.rows) < 2


def _aya_lengths(connection: sqlite3.Connection, rows) -> dict[tuple[int, int], int]:
    keys = {tuple(int(x) for x in row.segment_ref.split(":")[:2]) for row in rows}
    return {k: connection.execute("SELECT max(pos) FROM words WHERE sura = ? AND aya = ?", k).fetchone()[0] for k in keys}


def position_in_aya(segment_ref: str, aya_length: int) -> str:
    start, end = (int(x) for x in segment_ref.split(":")[2].split("-"))
    if start == 1 and end == aya_length:
        return "whole_aya"
    return "first_segment" if start == 1 else "last_segment" if end == aya_length else "middle_segment"


def _attached(connection: sqlite3.Connection, unit_ids: list[int]) -> Counter:
    found: Counter = Counter()
    for unit_id in unit_ids:
        (attached,) = connection.execute("SELECT attached FROM units WHERE id = ?", (unit_id,)).fetchone()
        for item in json.loads(attached):
            kind, tag, letters = item.split(":", 2)
            found[f"{letters} ({tag})"] += 1
        if not json.loads(attached):
            found["—"] += 1
    return found


def build(connection: sqlite3.Connection, form: str, scheme: str, config: dict) -> Profile:
    settings = ProfileSettings.from_config(config)
    analysis = families.analyse(
        connection, form, scheme, pairs.PairSettings.from_config(config), families.FamilySettings.from_config(config)
    )
    rows = analysis.rows
    roots = tuple(sorted(set().union(*(row.cells[row.pivot].roots for row in rows)))) if rows else ()
    found = Profile(
        form=form,
        roots=roots,
        analysis=analysis,
        matrices=tuple(matrix.build_all(analysis, settings.relative_min)),
        companions=sheet.companions(connection, analysis),
        box=sheet._box(connection, form, roots, {row.cells[row.pivot].word_ref for row in rows}),
    )
    lengths = _aya_lengths(connection, rows)
    for row in rows:
        sura, aya = (int(x) for x in row.segment_ref.split(":")[:2])
        found.suras[sura] += 1
        found.aya_positions[position_in_aya(row.segment_ref, lengths[sura, aya])] += 1
        found.positions[pairs._position(row.pivot, len(row.cells))] += 1
        found.left[row.cells[row.pivot - 1].form if row.pivot > 0 else "—"] += 1
        found.right[row.cells[row.pivot + 1].form if row.pivot + 1 < len(row.cells) else "—"] += 1
        pivot = row.cells[row.pivot]
        for index, cell in enumerate(row.cells):
            if index == row.pivot:
                continue
            found.contact["voisin" if abs(index - row.pivot) == 1 else "éloigné"] += 1
            for root in cell.roots - pivot.roots:
                found.root_sets.setdefault(root, Counter())[cell.form] += 1
            if cell.roots & pivot.roots:
                found.same_root_forms[cell.form] += 1
    found.attached = _attached(connection, [row.cells[row.pivot].unit_id for row in rows])
    for companion in found.companions:
        found.kinds[companion.kind] += len(companion.refs)
        if len(companion.segments) >= 2:
            found.order["always_before" if companion.after == 0 else "always_after" if companion.before == 0 else "variable"] += 1
    in_formula: set[int] = set()
    blocks: Counter = Counter()
    for (i, j), signature in analysis.signatures.items():
        found.types[" + ".join(signature.types)] += 1
        for op in signature.operations:
            found.operations[op.kind] += 1
            found.distances[op.distance] += 1
        for block in signature.blocks:
            if block.length >= settings.formula_min_block:
                in_formula |= {i, j}
                cells = rows[i].cells[block.a_start : block.a_start + block.length]
                blocks[" ".join(c.text for c in cells)] += 1
    found.formula_rows = len(in_formula)
    found.formula_block = max(blocks, key=lambda b: (blocks[b], len(b)), default="")
    return found


# --- Rendering helpers (Arabic) -------------------------------------------------------

from .labels import t  # noqa: E402


def share(n: int, total: int) -> str:
    return f"{n} ({n / total:.0%})" if total else "0"


def top(counter: Counter, limit: int = 4) -> str:
    return "، ".join(f"{k} ({v})" for k, v in counter.most_common(limit)) or "—"


def labelled(counter: Counter) -> str:
    return "، ".join(f"{t(k)} {v}" for k, v in counter.most_common()) or "—"


def described_rows(p: Profile) -> list[tuple[str, str]]:
    """Core dimensions read directly on the segments (layer وصف)."""
    total_kinds = sum(p.kinds.values())
    kinds = "، ".join(
        f"{t(name)} {share(p.kinds[key], total_kinds)}"
        for key, name in ((sheet.SAME_ROOT, "same_root"), (sheet.OTHER_ROOT, "other_roots"), (sheet.LETTER, "letters"))
    )
    return [
        (t("position"), labelled(p.positions)),
        (t("companion_kinds"), kinds),
        (t("order"), labelled(p.order)),
        (t("repetition"), share(p.formula_rows, len(p.rows)) + (f" : {p.formula_block}" if p.formula_block else "")),
        (t("neighbourhood"), f"{t('frame_before')} : {top(p.left, 2)} ؛ {t('frame_after')} : {top(p.right, 2)}"),
    ]


def classified_rows(p: Profile) -> list[tuple[str, str]]:
    """Core dimensions read on the pairs of level 1 (layer تصنيف)."""
    if p.unique:
        return [(t("internal_typology"), t("unique_short"))]
    types = "، ".join(f"{' + '.join(t(k) for k in kinds.split(' + '))} ({kinds}) : {v}" for kinds, v in p.types.most_common())
    return [
        (t("internal_typology"), types),
        (t("change_distance"), labelled(p.distances)),
    ]


def detail_rows(p: Profile) -> list[tuple[str, str]]:
    return [
        (t("aya_position"), labelled(p.aya_positions)),
        (t("contact"), labelled(p.contact)),
        (t("attached_to_form"), top(p.attached, 6)),
        (t("same_root_in_segment"), top(p.same_root_forms, 6)),
        (t("operations_profile"), "، ".join(f"{k} {t(k)} : {v}" for k, v in sorted(p.operations.items())) or "—"),
    ]


def table(rows: list[tuple[str, str]]) -> list[str]:
    return [f"| {t('dimension')} | {t('value')} |", "|---|---|", *(f"| {k} | {v} |" for k, v in rows)]
