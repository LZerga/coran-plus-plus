"""Level 1 (SPEC §2.2, §2.3): two segments compared directly, each pair on its own.

The elements are the cells of `units` (D-02). Between two cells, a code E:

    E0  same form                       يقدر = يقدر
    E1  same base, something attached   على ~ عليه
        added or removed
    E2  same base, pronoun changed      ربي ~ ربك      (or a letter changed: noted)
    E3  same root, other form           يشاء ~ شيء
    E4  other root                      الله ~ ربك
    Ø   nothing on the other side

Alignment of a pair: the reference form (pivot) is anchored; blocks of at least
two consecutive E0 cells are found wherever they stand; what is left is paired
E0, then E1, E2, E3, preferring the pairing that keeps the distance to the pivot.
Cells left over in the same gap on both sides are replacements (O2-E4); the
others are additions or removals (O1). The signature lists the blocks, the
operations O1-O5 with their distance to the pivot, the order of the units and
the count of each code; the types R1 / R2 / R3 of the document are read from it.
"""

from __future__ import annotations

import json
import sqlite3
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field

from .labels import t

E0, E1, E2, E3, E4, ABSENT = "E0", "E1", "E2", "E3", "E4", "Ø"
COMMON = (E0, E1, E2, E3)
R1_TOTAL, R1_PARTIAL, R2, R3 = "R1 total", "R1 partiel", "R2", "R3"
TYPE_LABELS = {R1_TOTAL: "تطابق كلي", R1_PARTIAL: "تطابق جزئي", R2: "تشابه", R3: "اختلاف"}
LETTER_CHANGED = "lettre changée"


@dataclass(frozen=True)
class Cell:
    unit_id: int
    ref: str  # of the cell (34:36:8b)
    word_ref: str  # of its word (34:36:8)
    text: str  # as written
    form: str
    base: str
    attached: tuple[str, ...]
    roots: frozenset[str]
    letter: bool = False  # a letter or a pronoun: no root, not a noun or a verb (the detached waw is one)


def relation(a: Cell, b: Cell) -> tuple[str, str]:
    """(code, note) between two cells present on both sides."""
    if a.form == b.form:
        return E0, ""
    if a.base and a.base == b.base:
        mine, theirs = Counter(a.attached), Counter(b.attached)
        only_a, only_b = mine - theirs, theirs - mine
        if not only_a or not only_b:
            return E1, ""
        pronouns = all(":PRON:" in item for item in (*only_a, *only_b))
        return E2, "" if pronouns else LETTER_CHANGED
    if a.roots & b.roots:
        return E3, ""
    return E4, ""


@dataclass(frozen=True)
class PairSettings:
    min_block: int
    r2_min_common: int
    pivot_counts: bool

    @classmethod
    def from_config(cls, config: dict) -> PairSettings:
        pairs = config["pairs"]
        return cls(pairs["min_block"], pairs["r2_min_common"], pairs["pivot_counts"])


@dataclass(frozen=True)
class Block:
    a_start: int
    b_start: int
    length: int


@dataclass(frozen=True)
class Link:
    """One aligned position: a cell of A and a cell of B (one of them may be None: Ø)."""

    a: int | None
    b: int | None
    code: str
    note: str = ""
    block: int | None = None  # index of the block it belongs to


@dataclass(frozen=True)
class Operation:
    kind: str  # O1 … O5
    detail: str
    a: tuple[int, ...]
    b: tuple[int, ...]
    distance: str  # pivot | voisin | éloigné


@dataclass(frozen=True)
class Signature:
    types: tuple[str, ...]
    blocks: tuple[Block, ...]
    links: tuple[Link, ...]
    operations: tuple[Operation, ...]
    order: tuple[tuple[int, ...], tuple[int, ...]]  # rank of each unit in A and in B
    inversions: int
    codes: dict[str, int]
    common_outside_pivot: int  # cells of E0 to E3 besides the pivot (blocks included)
    filtered: bool = False  # classed R3 at once: nothing in common besides the pivot
    content_common_outside_pivot: int = 0  # the same, letters and pronouns left out (family links, Q36)

    def kinds(self) -> Counter:
        return Counter(op.kind for op in self.operations)

    def to_json(self) -> dict:
        return {
            "types": list(self.types),
            "blocks": [vars(b) for b in self.blocks],
            "operations": [vars(op) | {"a": list(op.a), "b": list(op.b)} for op in self.operations],
            "order": [list(self.order[0]), list(self.order[1])],
            "inversions": self.inversions,
            "codes": self.codes,
        }


def _blocks(a: Sequence[Cell], pa: int, b: Sequence[Cell], pb: int, min_block: int) -> list[Block]:
    """Longest runs of E0 cells first, each cell used once; the pivot only ever faces the pivot."""
    same = [[x.form == y.form and ((i == pa) == (j == pb)) for j, y in enumerate(b)] for i, x in enumerate(a)]
    free_a, free_b = [True] * len(a), [True] * len(b)
    found: list[Block] = []
    while True:
        best: Block | None = None
        for i in range(len(a)):
            for j in range(len(b)):
                n = 0
                while i + n < len(a) and j + n < len(b) and free_a[i + n] and free_b[j + n] and same[i + n][j + n]:
                    n += 1
                if n >= min_block and (best is None or n > best.length):
                    best = Block(i, j, n)
        if best is None:
            return sorted(found, key=lambda blk: blk.a_start)
        for k in range(best.length):
            free_a[best.a_start + k] = free_b[best.b_start + k] = False
        found.append(best)


def _position(index: int, length: int) -> str:
    if length == 1:
        return "seul"
    return "début" if index == 0 else "fin" if index == length - 1 else "milieu"


def _distance(cells_a: Sequence[int], cells_b: Sequence[int], pa: int, pb: int) -> str:
    gaps = [abs(i - pa) for i in cells_a] + [abs(j - pb) for j in cells_b]
    nearest = min(gaps, default=2)
    return "pivot" if nearest == 0 else "voisin" if nearest == 1 else "éloigné"


def _runs(indexes: list[int]) -> list[list[int]]:
    runs: list[list[int]] = []
    for i in sorted(indexes):
        if runs and runs[-1][-1] == i - 1:
            runs[-1].append(i)
        else:
            runs.append([i])
    return runs


def _shares_something(a: Sequence[Cell], pa: int, b: Sequence[Cell], pb: int) -> bool:
    """Is there any E0 to E3 between two cells other than the pivots? (the filter of SPEC §2.3)"""
    rest_b = [y for j, y in enumerate(b) if j != pb]
    forms = {y.form for y in rest_b}
    bases = {y.base for y in rest_b if y.base}
    roots = set().union(*(y.roots for y in rest_b)) if rest_b else set()
    return any(x.form in forms or x.base in bases or x.roots & roots for i, x in enumerate(a) if i != pa)


def compare(
    a: Sequence[Cell], pa: int, b: Sequence[Cell], pb: int, settings: PairSettings, pivot_code: str = E0
) -> Signature:
    """Compare segment `a` (pivot at index `pa`) with segment `b` (pivot at `pb`)."""
    if not _shares_something(a, pa, b, pb):
        codes = Counter({pivot_code: 1, ABSENT: len(a) + len(b) - 2})
        return Signature((R3,), (), (Link(pa, pb, pivot_code),), (), ((1,), (1,)), 0, dict(codes), 0, True)

    blocks = _blocks(a, pa, b, pb, settings.min_block)
    links: list[Link] = []
    used_a: set[int] = set()
    used_b: set[int] = set()
    for number, blk in enumerate(blocks):
        for k in range(blk.length):
            links.append(Link(blk.a_start + k, blk.b_start + k, E0, block=number))
            used_a.add(blk.a_start + k)
            used_b.add(blk.b_start + k)
    pivot_in_block = pa in used_a
    if not pivot_in_block:
        links.append(Link(pa, pb, pivot_code))
        used_a.add(pa)
        used_b.add(pb)

    for code in COMMON:  # proximity first (D-06), then closeness to the pivot
        for i in range(len(a)):
            if i in used_a:
                continue
            candidates = [j for j in range(len(b)) if j not in used_b and relation(a[i], b[j])[0] == code]
            if candidates:
                j = min(candidates, key=lambda j: (abs((i - pa) - (j - pb)), j))
                links.append(Link(i, j, code, relation(a[i], b[j])[1]))
                used_a.add(i)
                used_b.add(j)

    # Units: each block is one unit; each paired cell outside the blocks is one unit.
    units: list[tuple[list[int], list[int]]] = [
        ([blk.a_start + k for k in range(blk.length)], [blk.b_start + k for k in range(blk.length)]) for blk in blocks
    ]
    units += [([link.a], [link.b]) for link in links if link.block is None]
    units.sort(key=lambda unit: unit[0][0])
    b_rank = {u: r for r, u in enumerate(sorted(range(len(units)), key=lambda u: units[u][1][0]), start=1)}
    order_b = tuple(b_rank[u] for u in range(len(units)))
    inverted = [(u, v) for u in range(len(units)) for v in range(u + 1, len(units)) if order_b[u] > order_b[v]]

    # Cells left over: a replacement (O2-E4) when both sides have some in the same gap, else Ø.
    def gap(index: int, side: int) -> int:
        return sum(1 for unit in units if unit[side][0] < index)

    left_a = [i for i in range(len(a)) if i not in used_a]
    left_b = [j for j in range(len(b)) if j not in used_b]
    by_gap_b: dict[int, list[int]] = {}
    for j in left_b:
        by_gap_b.setdefault(gap(j, 1), []).append(j)
    replaced: list[Link] = []
    for i in left_a:
        waiting = by_gap_b.get(gap(i, 0))
        if waiting:
            j = waiting.pop(0)
            replaced.append(Link(i, j, *relation(a[i], b[j])))
    links += replaced
    absent_a = [i for i in left_a if i not in {link.a for link in replaced}]
    absent_b = [j for j in left_b if j not in {link.b for link in replaced}]
    links += [Link(i, None, ABSENT) for i in absent_a] + [Link(None, j, ABSENT) for j in absent_b]

    operations: list[Operation] = []
    for run in _runs(absent_a):
        operations.append(Operation("O1", "Ø dans B", tuple(run), (), _distance(run, [], pa, pb)))
    for run in _runs(absent_b):
        operations.append(Operation("O1", "Ø dans A", (), tuple(run), _distance([], run, pa, pb)))
    for link in sorted((x for x in links if x.block is None and x.code in (E1, E2, E3, E4)), key=lambda x: x.a):
        detail = link.code + (f" ({link.note})" if link.note else "")
        operations.append(Operation("O2", detail, (link.a,), (link.b,), _distance([link.a], [link.b], pa, pb)))
    if inverted:
        involved = sorted({u for pair in inverted for u in pair})
        cells_a = [i for u in involved for i in units[u][0]]
        cells_b = [j for u in involved for j in units[u][1]]
        operations.append(
            Operation("O3", f"{len(inverted)} paire(s) d'unités inversée(s)", tuple(cells_a), tuple(cells_b), _distance(cells_a, cells_b, pa, pb))
        )  # fmt: skip
    # O4: glued on one side, apart on the other. What stands between must explain nothing else:
    # not an addition (O1), not a unit moved by an inversion (O3).
    moved = [set(), set()]
    for u in {u for pair in inverted for u in pair}:
        moved[0].update(units[u][0])
        moved[1].update(units[u][1])
    explained = (set(absent_a) | moved[0], set(absent_b) | moved[1])
    for side, other in ((0, 1), (1, 0)):
        ordered = sorted(range(len(units)), key=lambda u: units[u][side][0])
        for u, v in zip(ordered, ordered[1:]):
            glued = units[u][side][-1] + 1 == units[v][side][0]
            gap_cells = range(units[u][other][-1] + 1, units[v][other][0])
            if glued and len(gap_cells) and not any(c in explained[other] for c in gap_cells):
                cells = (tuple(units[u][0] + units[v][0]), tuple(units[u][1] + units[v][1]))
                operations.append(Operation("O4", "collés dans " + "AB"[side], *cells, _distance(*cells, pa, pb)))
    position_a, position_b = _position(pa, len(a)), _position(pb, len(b))
    if position_a != position_b:
        operations.append(Operation("O5", f"{position_a} → {position_b}", (pa,), (pb,), "pivot"))

    codes = Counter(link.code for link in links)
    common = sum(1 for link in links if link.code in COMMON) - (pivot_code in COMMON)
    content_common = sum(
        1 for link in links
        if link.code in COMMON and link.a is not None and link.b is not None and link.a != pa and not a[link.a].letter
    )  # fmt: skip
    outside_blocks = sum(1 for link in links if link.block is None and link.code in COMMON and link.a != pa)
    if settings.pivot_counts and not pivot_in_block and pivot_code in COMMON:
        outside_blocks += 1
    if len(a) == len(b) and all(x.form == y.form for x, y in zip(a, b)):
        types: tuple[str, ...] = (R1_TOTAL,)
    else:
        found = [R1_PARTIAL] if blocks else []
        if outside_blocks >= settings.r2_min_common and operations:
            found.append(R2)
        types = tuple(found) or (R3,)
    return Signature(
        types,
        tuple(blocks),
        tuple(sorted(links, key=lambda x: (x.a is None, x.a if x.a is not None else x.b))),
        tuple(operations),
        (tuple(range(1, len(units) + 1)), order_b),
        len(inverted),
        dict(codes),
        common,
        False,
        content_common,
    )


# --- Loading cells ----------------------------------------------------------------


_CELLS = """SELECT u.id, u.ref, w.ref, u.text_raw, u.form, u.base, u.attached,
                   coalesce((SELECT group_concat(root, ' ') FROM unit_roots r WHERE r.unit_id = u.id), ''),
                   CASE WHEN u.part = 1 THEN 'CONJ' ELSE coalesce((SELECT s.tag FROM word_segments s
                        WHERE s.word_id = u.word_id AND s.kind = 'stem' ORDER BY s.seg_no LIMIT 1), '') END
            FROM units u JOIN words w ON w.id = u.word_id"""
CONTENT_TAGS = frozenset({"N", "PN", "ADJ", "V", "IMPN"})  # never a "letter", even without a root


def _cell(row) -> Cell:
    unit_id, ref, word_ref, text, form, base, attached, roots, tag = row
    letter = not roots and tag not in CONTENT_TAGS
    return Cell(unit_id, ref, word_ref, text, form, base, tuple(json.loads(attached)), frozenset(roots.split()), letter)


def cells_of_span(connection: sqlite3.Connection, sura: int, aya: int, start: int, end: int) -> list[Cell]:
    """The cells of the words start…end of an aya (word positions, as in sura:aya:word)."""
    rows = connection.execute(
        _CELLS + " WHERE w.sura = ? AND w.aya = ? AND w.pos BETWEEN ? AND ? ORDER BY u.id", (sura, aya, start, end)
    ).fetchall()
    if not rows:
        raise ValueError(f"passage {sura}:{aya}:{start}-{end} introuvable")
    return [_cell(row) for row in rows]


def cells_of_segment(connection: sqlite3.Connection, segment_id: int) -> list[Cell]:
    rows = connection.execute(
        _CELLS + " JOIN segment_units su ON su.unit_id = u.id WHERE su.segment_id = ? ORDER BY u.id", (segment_id,)
    ).fetchall()
    return [_cell(row) for row in rows]


def parse_span(text: str) -> tuple[int, int, int, int]:
    """`sura:aya:start-end` (word positions) → numbers."""
    try:
        sura, aya, positions = text.split(":")
        start, end = positions.split("-")
        return int(sura), int(aya), int(start), int(end)
    except ValueError:
        raise ValueError(f"passage attendu sous la forme sourate:verset:début-fin, reçu {text!r}") from None


# --- Rendering ------------------------------------------------------------------


def _detail(op: Operation) -> str:
    if op.kind == "O2":
        code, _, note = op.detail.partition(" (")
        return code + (f" ({t(note.rstrip(')'))})" if note else "")
    if op.kind == "O3":
        return f"{t('inverted')} : {op.detail.split()[0]}"
    if op.kind == "O5":
        before, _, after = op.detail.partition(" → ")
        return f"{t(before)} ← {t(after)}"
    return t(op.detail)


def describe(a: Sequence[Cell], b: Sequence[Cell], signature: Signature) -> dict[str, str]:
    """The parts of a signature, as short text, labelled in Arabic; codes kept beside the labels."""

    def text(cells: Sequence[Cell], indexes: Sequence[int]) -> str:
        return " ".join(cells[i].text for i in indexes)

    blocks = [text(a, range(blk.a_start, blk.a_start + blk.length)) for blk in signature.blocks]
    operations = []
    for op in signature.operations:
        if op.kind == "O2":
            what = f"{text(a, op.a)} ← {text(b, op.b)}"
        elif op.kind == "O1":
            what = text(a, op.a) or text(b, op.b)
        else:
            what = ""
        operations.append(f"{op.kind} {t(op.kind)} ، {_detail(op)}" + (f" : {what}" if what else "") + f" [{t(op.distance)}]")
    return {
        t("types"): " + ".join(f"{t(kind)} ({kind})" for kind in signature.types),
        t("blocks"): " | ".join(blocks) or "—",
        t("operations"): " ؛ ".join(operations) or "—",
        t("order"): " ".join(map(str, signature.order[1])) + f" ({t('inversions')} : {signature.inversions})",
        t("codes"): " ".join(f"{code}:{n}" for code, n in sorted(signature.codes.items())),
    }


def pivot_index(cells: Sequence[Cell], typed: str) -> int | None:
    """Where the typed reference form stands in a passage (matched without vowels)."""
    from .index import search_key
    from .normalize import Level, normalize

    key = search_key(typed)
    return next((i for i, cell in enumerate(cells) if normalize(cell.form, Level.NO_VOWELS).replace("ٱ", "ا") == key), None)


def render_pair(a: Sequence[Cell], b: Sequence[Cell], signature: Signature, span_a: str, span_b: str, pivot: str, meta: dict) -> str:
    """One pair, as the command `paire` prints it (Markdown, Arabic)."""
    from .labels import meta_line

    lines = [
        f"# {t('pair')} — {t('reference_form')} : {pivot}",
        "",
        meta_line(meta),
        "",
        f"- أ  {span_a}  {' '.join(c.text for c in a)}",
        f"- ب  {span_b}  {' '.join(c.text for c in b)}",
        *(f"- {label} : {value}" for label, value in describe(a, b, signature).items()),
    ]
    return "\n".join(lines) + "\n"
