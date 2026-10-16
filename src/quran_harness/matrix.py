"""Level 3 (SPEC §2.5, §2.6): one alignment matrix per family, and its check against the pairs.

The matrix sums up what the typology grouped; it never replaces the direct pairs.

Building (rules of §2.5, in that order):
1. the pivot is anchored: every row's reference form is in the pivot column, and the
   parts left and right of it are aligned apart;
2. the pairings of level 1 are kept: the matrix is built around a centre row, the
   row with the most elements in common with the others, and each row is placed
   along its own direct pairing with the centre;
3. between two anchors, a row's other cells fill the centre columns it leaves empty,
   from the pivot side (a replacement, O2-E4); the rest are inserted; in one gap,
   cells of the same form share a column (most E0), then free columns are shared (fewest columns);
4. a cell paired with the centre but in inverted order (O3) cannot keep its column
   without breaking the row: it is inserted instead, and the order stays in the pairs;
5. when two centres tie and give different templates, the matrix is marked ambiguous.

Columns: fixed (same form in every row), relatively fixed (same form in at least
`relative_min` of the rows), variable; a column with a Ø is also optional.

Check (§2.6): for every pair of the family, what the two rows face in the matrix is
compared with their direct pairing. The direct signature is authoritative; every
difference is recorded.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from . import pairs
from .families import Analysis, Family

FIXED, RELATIVE, VARIABLE = "fixe", "relativement fixe", "variable"


@dataclass(frozen=True)
class Column:
    cells: tuple[int | None, ...]  # per row of the family: index of the cell in its row, or None (Ø)
    is_pivot: bool


@dataclass(frozen=True)
class ColumnReading:
    kind: str  # fixe | relativement fixe | variable
    optional: bool
    fillers: tuple[tuple[str, int], ...]  # form -> number of rows, most frequent first; Ø counted as "Ø"


@dataclass(frozen=True)
class Difference:
    rows: tuple[int, int]  # indexes into Analysis.rows
    direct_only: tuple[tuple[int, int, str], ...]  # pairings (cell a, cell b, code) the matrix does not give
    matrix_only: tuple[tuple[int, int, str], ...]  # pairings the matrix gives and the direct comparison does not


@dataclass(frozen=True)
class Matrix:
    family: Family
    centre: int  # row of the analysis
    columns: tuple[Column, ...]
    readings: tuple[ColumnReading, ...]
    template: str
    ambiguous: bool
    moved: tuple[tuple[int, int], ...]  # (row, cell) inserted because their pairing with the centre is inverted
    differences: tuple[Difference, ...]

    @property
    def rows(self) -> list[int]:
        return self.family.rows


def _signature(analysis: Analysis, i: int, j: int) -> tuple[pairs.Signature, bool]:
    """The signature of rows i and j, and whether i is its side A."""
    return (analysis.signatures[i, j], True) if i < j else (analysis.signatures[j, i], False)


def _pairing(analysis: Analysis, i: int, j: int) -> dict[int, tuple[int, str]]:
    """Cells of row i paired (E0 to E3) with a cell of row j: index in i -> (index in j, code)."""
    signature, i_is_a = _signature(analysis, i, j)
    found = {}
    for link in signature.links:
        if link.a is not None and link.b is not None and link.code in pairs.COMMON:
            mine, theirs = (link.a, link.b) if i_is_a else (link.b, link.a)
            found[mine] = (theirs, link.code)
    return found


def _increasing(pairs_: list[tuple[int, int]]) -> set[tuple[int, int]]:
    """Longest chain of (centre cell, row cell) increasing on both sides (pairs given sorted by centre cell)."""
    best: list[list[tuple[int, int]]] = []
    for k, (c, r) in enumerate(pairs_):
        chain = max((best[m] for m in range(k) if best[m][-1][1] < r), key=len, default=[])
        best.append(chain + [(c, r)])
    return set(max(best, key=len, default=[]))


def _build(analysis: Analysis, family: Family, centre: int) -> tuple[list[Column], list[tuple[int, int]]]:
    rows = family.rows
    centre_row = analysis.rows[centre]
    # Placement of each row along the centre: centre cell -> row cell.
    placed: dict[int, dict[int, int]] = {}
    moved: list[tuple[int, int]] = []
    for r in rows:
        if r == centre:
            placed[r] = {k: k for k in range(len(centre_row.cells))}
            continue
        pairing = _pairing(analysis, centre, r)
        pc, pr = centre_row.pivot, analysis.rows[r].pivot
        pairing[pc] = (pr, pairs.E0)  # rule 1: the pivot faces the pivot
        # The left and the right of the pivot are aligned apart; a pairing across the pivot is an inversion.
        left = sorted((c, cell) for c, (cell, _) in pairing.items() if c < pc and cell < pr)
        right = sorted((c, cell) for c, (cell, _) in pairing.items() if c > pc and cell > pr)
        kept = _increasing(left) | _increasing(right) | {(pc, pr)}
        placed[r] = {c: cell for c, cell in kept}
        moved += [(r, cell) for c, (cell, _) in pairing.items() if (c, cell) not in kept]

    # Between two consecutive anchors, a row's other cells first fill the centre columns it leaves
    # empty, from the pivot side (a replacement, O2-E4, as at level 1); what is left is inserted.
    n = len(centre_row.cells)
    gaps: dict[int, dict[int, list[int]]] = {g: {} for g in range(n + 1)}  # cells inserted before centre column g
    for r in rows:
        if r == centre:
            continue
        row_cells, pr = len(analysis.rows[r].cells), analysis.rows[r].pivot
        anchors = [(-1, -1), *sorted(placed[r].items()), (n, row_cells)]
        for (cl, rl), (cr, rr) in zip(anchors, anchors[1:]):
            free_cells, free_columns = list(range(rl + 1, rr)), list(range(cl + 1, cr))
            k = min(len(free_cells), len(free_columns))
            if rr <= pr:  # left of the pivot: fill from the right
                assigned = list(zip(free_columns[len(free_columns) - k :], free_cells[len(free_cells) - k :]))
                rest, gap = free_cells[: len(free_cells) - k], free_columns[len(free_columns) - k] if k else cr
            else:  # right of the pivot: fill from the left
                assigned = list(zip(free_columns[:k], free_cells[:k]))
                rest, gap = free_cells[k:], free_columns[k - 1] + 1 if k else cl + 1
            placed[r].update(assigned)
            if rest:
                gaps[gap].setdefault(r, []).extend(rest)

    columns: list[Column] = []
    for g in range(n + 1):
        inserted: list[dict[int, int]] = []  # columns of this gap: row -> cell
        # Left of the pivot, inserted cells are aligned from the pivot side (right to left),
        # so that what stands next to the next column lines up (الله / ربك / ربي before يبسط).
        towards_pivot = g <= centre_row.pivot
        for r, cells in gaps[g].items():
            start = 0
            for cell in reversed(cells) if towards_pivot else cells:
                form = analysis.rows[r].cells[cell].form
                same = [k for k in range(start, len(inserted)) if r not in inserted[k]
                        and any(analysis.rows[o].cells[c].form == form for o, c in inserted[k].items())]
                free = [k for k in range(start, len(inserted)) if r not in inserted[k]]
                found = same[0] if same else free[0] if free else None  # most E0, then fewest columns
                if found is None:
                    inserted.append({})
                    found = len(inserted) - 1
                inserted[found][r] = cell
                start = found + 1
        if towards_pivot:
            inserted.reverse()
        columns += [Column(tuple(col.get(r) for r in rows), False) for col in inserted]
        if g < n:
            columns.append(
                Column(tuple(placed[r].get(g) for r in rows), g == centre_row.pivot)
            )
    return columns, moved


def _reading(analysis: Analysis, family: Family, column: Column, relative_min: float) -> ColumnReading:
    forms = Counter(
        analysis.rows[r].cells[cell].form if cell is not None else pairs.ABSENT for r, cell in zip(family.rows, column.cells)
    )
    present = Counter({form: n for form, n in forms.items() if form != pairs.ABSENT})
    total = len(family.rows)
    top = present.most_common(1)[0][1] if present else 0
    if len(present) == 1 and top == total:
        kind = FIXED
    elif top / total >= relative_min:
        kind = RELATIVE
    else:
        kind = VARIABLE
    return ColumnReading(kind, pairs.ABSENT in forms, tuple(forms.most_common()))


def template(readings: list[ColumnReading]) -> str:
    """Compact writing of a matrix: fixed forms as they are, [optional], {variable}, form* for relatively fixed."""
    parts: list[str] = []
    group: list[str] = []
    for reading in readings:
        present = [form for form, _ in reading.fillers if form != pairs.ABSENT]
        if reading.kind == FIXED:
            text = present[0]
        elif reading.kind == RELATIVE:
            text = present[0] + "*"
        else:
            text = "{" + "|".join(present[:3]) + ("|…" if len(present) > 3 else "") + "}"
        if reading.optional:
            group.append(text)
            continue
        if group:
            parts.append("[" + " ".join(group) + "]")
            group = []
        parts.append(text)
    if group:
        parts.append("[" + " ".join(group) + "]")
    return " ".join(parts)


def _differences(analysis: Analysis, family: Family, columns: list[Column]) -> list[Difference]:
    found = []
    for x, i in enumerate(family.rows):
        for y in range(x + 1, len(family.rows)):
            j = family.rows[y]
            direct = {(a, b, code) for a, (b, code) in _pairing(analysis, i, j).items()}
            induced = set()
            for column in columns:
                a, b = column.cells[x], column.cells[y]
                if a is not None and b is not None:
                    code, _ = pairs.relation(analysis.rows[i].cells[a], analysis.rows[j].cells[b])
                    if code in pairs.COMMON:
                        induced.add((a, b, code))
            if direct != induced:
                found.append(Difference((i, j), tuple(sorted(direct - induced)), tuple(sorted(induced - direct))))
    return found


def build(analysis: Analysis, family: Family, relative_min: float) -> Matrix:
    rows = family.rows
    scores = {
        r: sum(_signature(analysis, r, o)[0].common_outside_pivot for o in rows if o != r) for r in rows
    }
    best = max(scores.values())
    centres = [r for r in rows if scores[r] == best]

    def make(centre: int):
        columns, moved = _build(analysis, family, centre) if len(rows) > 1 else (
            [Column((k,), k == analysis.rows[centre].pivot) for k in range(len(analysis.rows[centre].cells))], []
        )
        readings = [_reading(analysis, family, column, relative_min) for column in columns]
        return columns, moved, readings, template(readings)

    columns, moved, readings, text = make(centres[0])
    ambiguous = any(make(other)[3] != text for other in centres[1:])
    differences = _differences(analysis, family, columns) if len(rows) > 1 else []
    return Matrix(family, centres[0], tuple(columns), tuple(readings), text, ambiguous, tuple(moved), tuple(differences))


def build_all(analysis: Analysis, relative_min: float) -> list[Matrix]:
    return [build(analysis, family, relative_min) for family in analysis.families]


# --- Rendering ------------------------------------------------------------------


def render(analysis: Analysis, matrices: list[Matrix], light: bool = False) -> list[str]:
    from .labels import t

    lines: list[str] = []
    for number, m in enumerate(matrices, start=1):
        if m.family.isolated:
            continue
        n_pairs = len(m.rows) * (len(m.rows) - 1) // 2
        lines += [
            "",
            f"## {t('matrix')} — {t('family')} {number}",
            "",
            f"{t('template')} : `{m.template}`" + (f" — **{t('ambiguous_matrix')}**" if m.ambiguous else ""),
            "",
            f"{t('centre')} : {analysis.rows[m.centre].segment_ref} ؛ {t('columns')} : {len(m.columns)} ؛ "
            f"{t('differences')} : {len(m.differences)} / {n_pairs}"
            + (f" ؛ {t('moved')} : {len(m.moved)}" if m.moved else ""),
            "",
        ]
        # Light view (SPEC step 8): columns filled by one row only are hidden and counted.
        shown = [
            k for k, c in enumerate(m.columns)
            if not light or c.is_pivot or sum(cell is not None for cell in c.cells) >= 2
        ]  # fmt: skip
        if len(shown) < len(m.columns):
            lines += [t("hidden_columns", n=len(m.columns) - len(shown)), ""]
        header = [t("segment")] + [(f"**{t('pivot')}**" if m.columns[k].is_pivot else str(k + 1)) for k in shown]
        lines += ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
        for x, r in enumerate(m.rows):
            row = analysis.rows[r]
            cells = [row.cells[m.columns[k].cells[x]].text if m.columns[k].cells[x] is not None else pairs.ABSENT for k in shown]
            lines.append(f"| {row.segment_ref} | " + " | ".join(cells) + " |")
        readings = [m.readings[k] for k in shown]
        kinds = [t("column_kind")] + [t(r.kind) + (f"، {t('optional')}" if r.optional else "") for r in readings]
        lines.append("| " + " | ".join(kinds) + " |")
    return lines
