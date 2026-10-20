"""Frames and slots of a root (« قالب وخانة »), read on a short window around its forms.

The segment stays the unit of analysis; this is one more reading of it, limited to the
cells right next to the form (decision of the author, 2026-10-20). All the forms of the
root are taken together (level 5: the root as the set of its forms), so that a frame
spread over many rare forms (ينقلب، انقلبوا، فتنقلبوا… followed by على / إلى) shows.

    continuations   what comes right after the forms of the root (first cell, then second),
                    as a tree: على → عقبيه، أعقابكم، وجهه
    antecedents     the same, right before
    slots           frames (cell before, cell after) that come back, and the forms of the
                    root that fill them: في ___ مرض ← قلوبهم
    openness        for each form: how many different cells follow it (a closed or an open slot)

Every first cell is tested against chance: is it found next to the root more often than its
frequency in the text predicts? Under random placement the count follows a Poisson law
with mean (occurrences of the root) × (share of that cell among all cells); p-values are
corrected for the number of cells tested (Benjamini-Hochberg).
"""

from __future__ import annotations

import math
import sqlite3
from collections import Counter
from dataclasses import dataclass, field

from . import stats
from .labels import t
from .units import forms_of_root

EDGE = "|"  # the segment ends here


@dataclass
class Branch:
    cell: str  # the first cell after (or before) the root
    count: int
    expected: float
    p_value: float
    q_value: float = 1.0
    forms: Counter = field(default_factory=Counter)  # forms of the root it follows
    second: Counter = field(default_factory=Counter)  # the cell after it (before it, for antecedents)
    refs: list[str] = field(default_factory=list)

    @property
    def established(self) -> bool:
        return self.q_value <= 0.05


@dataclass(frozen=True)
class Slot:
    before: str
    after: str
    fillers: Counter  # forms of the root filling the slot
    refs: tuple[str, ...]


@dataclass(frozen=True)
class Frames:
    root: str
    occurrences: int
    continuations: list[Branch]
    antecedents: list[Branch]
    slots: list[Slot]
    openness: dict[str, tuple[int, int]]  # form -> (occurrences, distinct following cells)


def _poisson_tail(k: int, mean: float) -> float:
    """P(X >= k) for X ~ Poisson(mean)."""
    if k <= 0:
        return 1.0
    term = math.exp(-mean)
    below = term
    for i in range(1, k):
        term *= mean / i
        below += term
    return max(0.0, min(1.0, 1.0 - below))


def _segment_cells(connection: sqlite3.Connection, scheme: str) -> dict[int, list[tuple[int, str, str]]]:
    """Every segment of a scheme as its cells (unit id, form, ref), in order; aya 0 left out."""
    rows = connection.execute(
        """SELECT su.segment_id, u.id, u.form, u.ref FROM units u
           JOIN segment_units su ON su.unit_id = u.id
           JOIN segmentations n ON n.id = su.segmentation_id AND n.name = ?
           WHERE u.aya > 0 ORDER BY u.id""",
        (scheme,),
    )
    segments: dict[int, list[tuple[int, str, str]]] = {}
    for segment_id, unit_id, form, ref in rows:
        segments.setdefault(segment_id, []).append((unit_id, form, ref))
    return segments


_SEGMENTS: dict[tuple[str, str], dict] = {}


def build(connection: sqlite3.Connection, root: str, scheme: str, alpha: float = 0.05, min_count: int = 2) -> Frames:
    (path,) = [row[2] for row in connection.execute("PRAGMA database_list") if row[1] == "main"]
    if (path, scheme) not in _SEGMENTS:
        _SEGMENTS[path, scheme] = _segment_cells(connection, scheme)
    segments = _SEGMENTS[path, scheme]
    root_units = {
        unit_id for (unit_id,) in connection.execute("SELECT unit_id FROM unit_roots WHERE root = ?", (root,))
    }
    frequency: Counter = Counter()
    total = 0
    after: dict[str, Branch] = {}
    before: dict[str, Branch] = {}
    slots: dict[tuple[str, str], list] = {}
    follows: dict[str, Counter] = {}
    occurrences = 0
    for cells in segments.values():
        for k, (unit_id, form, ref) in enumerate(cells):
            frequency[form] += 1
            total += 1
            if unit_id not in root_units:
                continue
            occurrences += 1
            nxt = cells[k + 1][1] if k + 1 < len(cells) else EDGE
            nxt2 = cells[k + 2][1] if k + 2 < len(cells) else EDGE
            prv = cells[k - 1][1] if k > 0 else EDGE
            prv2 = cells[k - 2][1] if k > 1 else EDGE
            for table, first, second in ((after, nxt, nxt2), (before, prv, prv2)):
                branch = table.setdefault(first, Branch(first, 0, 0.0, 1.0))
                branch.count += 1
                branch.forms[form] += 1
                if first != EDGE:
                    branch.second[second] += 1
                branch.refs.append(ref)
            follows.setdefault(form, Counter())[nxt] += 1
            if prv != EDGE and nxt != EDGE:
                slots.setdefault((prv, nxt), []).append((form, ref))

    def finish(table: dict[str, Branch]) -> list[Branch]:
        tested = [b for b in table.values() if b.cell != EDGE and b.count >= min_count]
        for b in tested:
            b.expected = occurrences * frequency[b.cell] / total
            b.p_value = _poisson_tail(b.count, b.expected)
        for b, q in zip(tested, stats.benjamini_hochberg([b.p_value for b in tested]) if tested else []):
            b.q_value = q
        return sorted(table.values(), key=lambda b: (-b.count, b.cell))

    slot_list = [
        Slot(b, a, Counter(f for f, _ in items), tuple(r for _, r in items))
        for (b, a), items in slots.items()
        if len(items) >= min_count
    ]
    slot_list.sort(key=lambda s: (-sum(s.fillers.values()), s.before, s.after))
    return Frames(
        root=root,
        occurrences=occurrences,
        continuations=finish(after),
        antecedents=finish(before),
        slots=slot_list,
        openness={form: (sum(c.values()), len(c)) for form, c in follows.items()},
    )


# --- Rendering (Markdown, Arabic) ---------------------------------------------------


def _top(counter: Counter, limit: int = 5) -> str:
    return "، ".join(f"{k} ({v})" for k, v in counter.most_common(limit)) or "—"


def _cell(cell: str) -> str:
    return t("segment_edge") if cell == EDGE else cell


def render_section(found: Frames, detail: bool = False, limit: int = 15) -> list[str]:
    lines = [f"### {t('frames_after')}", "", t("frames_note", n=found.occurrences), "",
             f"| {t('first_cell')} | {t('count')} | {t('expected')} | {t('status')} | {t('second_cell')} | {t('root_forms')} |",
             "|---|---|---|---|---|---|"]  # fmt: skip
    for b in [b for b in found.continuations if b.count >= 2][: None if detail else limit]:
        status = "—" if b.cell == EDGE else t("established") if b.established else t("observed")
        expected = "—" if b.cell == EDGE else f"{b.expected:.2f}"
        lines.append(f"| {_cell(b.cell)} | {b.count} | {expected} | {status} | {_top(b.second, 4)} | {_top(b.forms, 4)} |")
    lines += ["", f"### {t('frames_before')}", "",
              f"| {t('first_cell')} | {t('count')} | {t('expected')} | {t('status')} | {t('second_cell_before')} | {t('root_forms')} |",
              "|---|---|---|---|---|---|"]  # fmt: skip
    for b in [b for b in found.antecedents if b.count >= 2][: None if detail else limit]:
        status = "—" if b.cell == EDGE else t("established") if b.established else t("observed")
        expected = "—" if b.cell == EDGE else f"{b.expected:.2f}"
        lines.append(f"| {_cell(b.cell)} | {b.count} | {expected} | {status} | {_top(b.second, 4)} | {_top(b.forms, 4)} |")
    lines += ["", f"### {t('slots_title')}", "", f"| {t('slot_frame')} | {t('count')} | {t('root_forms')} |", "|---|---|---|"]
    for s in found.slots[: None if detail else limit]:
        lines.append(f"| {s.before} ___ {s.after} | {sum(s.fillers.values())} | {_top(s.fillers, 4)} |")
    if not found.slots:
        lines.append(f"| — | 0 | — |")
    lines += ["", f"### {t('openness_title')}", "", f"| {t('form')} | {t('occurrences')} | {t('distinct_after')} |", "|---|---|---|"]
    ranked = sorted(found.openness.items(), key=lambda item: (-item[1][0], item[0]))
    for form, (n, distinct) in [x for x in ranked if x[1][0] >= 3][: None if detail else limit]:
        lines.append(f"| {form} | {n} | {distinct} |")
    return lines


def render(found: Frames, meta: dict[str, str], detail: bool = False) -> str:
    from .labels import meta_line

    lines = [f"# {t('frames_title')} — {found.root}", "", meta_line(meta), "", *render_section(found, detail)]
    return "\n".join(lines) + "\n"


def forms_count(connection: sqlite3.Connection, root: str) -> int:
    return len(forms_of_root(connection, root))
