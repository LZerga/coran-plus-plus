"""Level 5, first part (SPEC §2.12-c, D-17): two forms of the same root, compared.

The comparison starts from the segments: every segment of the first form is compared
directly with every segment of the second (level 1, the two forms as pivots paired by
their root, code E3). Each pair is read in the three cases of the research notes:

    أ  the same form beside both                 يقدر and قدير with شيء
    ب  forms of one root, different forms        عالم with الغيب, علام with الغيوب
    ج  neither

Letters and pronouns are counted apart: the detached waw would otherwise be shared by
almost every pair. Then the behaviour of each form is set side by side, along the
dimensions chosen by the author (2026-10-16): dispersion (1), formulas (2), position
in the segment (4), position of the segment in the aya (5), kinds of companions (7),
fixed or variable sets (8), shared and proper companions (9), order (11), immediate
frame (12), typology (14), and covariations in the families the two forms share (20).

Nothing is interpreted, and no random control is run yet (step 6): every figure is an
observation.
"""

from __future__ import annotations

import sqlite3
from collections import Counter
from dataclasses import dataclass, field

from . import families, matrix, pairs, sheet
from .labels import meta_line, t

LETTER, CONTENT = sheet.LETTER, "content"


@dataclass(frozen=True)
class ComparisonSettings:
    formula_min_block: int
    support_min: int

    @classmethod
    def from_config(cls, config: dict) -> ComparisonSettings:
        section = config["comparison"]
        return cls(section["formula_min_block"], section["support_min"])


@dataclass
class Profile:
    """The behaviour of one form, along the chosen dimensions."""

    form: str
    analysis: families.Analysis
    companions: list[sheet.Companion]
    box: str
    suras: Counter = field(default_factory=Counter)  # 1
    formula_rows: int = 0  # 2
    formula_block: str = ""
    positions: Counter = field(default_factory=Counter)  # 4
    aya_positions: Counter = field(default_factory=Counter)  # 5
    kinds: Counter = field(default_factory=Counter)  # 7, by occurrences
    root_sets: dict[str, Counter] = field(default_factory=dict)  # 8: companion root -> its forms
    left: Counter = field(default_factory=Counter)  # 12: neighbour before the form
    right: Counter = field(default_factory=Counter)  # 12: neighbour after the form
    types: Counter = field(default_factory=Counter)  # 14

    @property
    def rows(self) -> tuple[families.Row, ...]:
        return self.analysis.rows


@dataclass(frozen=True)
class CrossPair:
    first: int  # row of the first form
    second: int  # row of the second form
    signature: pairs.Signature
    same_form: tuple[tuple[pairs.Cell, pairs.Cell], ...]  # case أ (letters and pronouns left out)
    same_root: tuple[tuple[pairs.Cell, pairs.Cell], ...]  # case ب
    letters: tuple[tuple[pairs.Cell, pairs.Cell], ...]  # letters and pronouns found on both sides

    @property
    def cases(self) -> tuple[str, ...]:
        found = (["أ"] if self.same_form else []) + (["ب"] if self.same_root else [])
        return tuple(found) or ("ج",)


@dataclass(frozen=True)
class Covariation:
    family: int
    column: int
    fillers: tuple[Counter, Counter]  # forms beside the first form, beside the second


@dataclass(frozen=True)
class Comparison:
    first: Profile
    second: Profile
    roots: tuple[str, ...]
    cross: tuple[CrossPair, ...]
    mixed: families.Analysis  # the rows of both forms together
    matrices: tuple[matrix.Matrix, ...]  # of the families holding segments of both forms
    covariations: tuple[Covariation, ...]

    def is_mixed(self, family: families.Family) -> bool:
        n = len(self.first.rows)
        return any(r < n for r in family.rows) and any(r >= n for r in family.rows)


def _aya_lengths(connection: sqlite3.Connection, rows) -> dict[tuple[int, int], int]:
    keys = {tuple(int(x) for x in row.segment_ref.split(":")[:2]) for row in rows}
    return {
        key: connection.execute("SELECT max(pos) FROM words WHERE sura = ? AND aya = ?", key).fetchone()[0] for key in keys
    }


def _position_in_aya(segment_ref: str, aya_length: int) -> str:
    start, end = (int(x) for x in segment_ref.split(":")[2].split("-"))
    if start == 1 and end == aya_length:
        return "whole_aya"
    return "first_segment" if start == 1 else "last_segment" if end == aya_length else "middle_segment"


def profile(connection: sqlite3.Connection, form: str, scheme: str, config: dict, settings: ComparisonSettings) -> Profile:
    analysis = families.analyse(
        connection, form, scheme, pairs.PairSettings.from_config(config), families.FamilySettings.from_config(config)
    )
    rows = analysis.rows
    roots = tuple(sorted(set().union(*(row.cells[row.pivot].roots for row in rows)))) if rows else ()
    found = Profile(
        form=form,
        analysis=analysis,
        companions=sheet.companions(connection, analysis),
        box=sheet._box(connection, form, roots, {row.cells[row.pivot].word_ref for row in rows}),
    )
    lengths = _aya_lengths(connection, rows)
    for row in rows:
        found.suras[int(row.segment_ref.split(":")[0])] += 1
        found.positions[pairs._position(row.pivot, len(row.cells))] += 1
        sura, aya = (int(x) for x in row.segment_ref.split(":")[:2])
        found.aya_positions[_position_in_aya(row.segment_ref, lengths[sura, aya])] += 1
        found.left[row.cells[row.pivot - 1].form if row.pivot > 0 else "—"] += 1
        found.right[row.cells[row.pivot + 1].form if row.pivot + 1 < len(row.cells) else "—"] += 1
        pivot_roots = row.cells[row.pivot].roots
        for index, cell in enumerate(row.cells):
            if index == row.pivot:
                continue
            for root in cell.roots - pivot_roots:
                found.root_sets.setdefault(root, Counter())[cell.form] += 1
    for companion in found.companions:
        found.kinds[companion.kind] += len(companion.refs)
    in_formula: set[int] = set()
    blocks: Counter = Counter()
    for (i, j), signature in analysis.signatures.items():
        for block in signature.blocks:
            if block.length >= settings.formula_min_block:
                in_formula |= {i, j}
                cells = rows[i].cells[block.a_start : block.a_start + block.length]
                blocks[" ".join(c.text for c in cells)] += 1
    found.formula_rows = len(in_formula)
    found.formula_block = max(blocks, key=lambda b: (blocks[b], len(b)), default="")
    found.types = Counter(" + ".join(s.types) for s in analysis.signatures.values())
    return found


def _is_letter(cell: pairs.Cell, tags: dict[int, str]) -> bool:
    return not cell.roots and tags.get(cell.unit_id) not in sheet.CONTENT_TAGS


def compare_forms(
    connection: sqlite3.Connection, form_a: str, form_b: str, scheme: str, config: dict
) -> Comparison:
    settings = ComparisonSettings.from_config(config)
    pair_settings = pairs.PairSettings.from_config(config)
    family_settings = families.FamilySettings.from_config(config)
    first = profile(connection, form_a, scheme, config, settings)
    second = profile(connection, form_b, scheme, config, settings)
    roots_a = set().union(*(r.cells[r.pivot].roots for r in first.rows)) if first.rows else set()
    roots_b = set().union(*(r.cells[r.pivot].roots for r in second.rows)) if second.rows else set()
    if not roots_a & roots_b:
        raise ValueError("not_same_root")  # D-17: no comparison between roots
    tags = sheet._tags(connection, {c.unit_id for p in (first, second) for row in p.rows for c in row.cells})

    cross: list[CrossPair] = []
    n = len(first.rows)
    signatures: dict[tuple[int, int], pairs.Signature] = dict(first.analysis.signatures)
    signatures |= {(n + i, n + j): s for (i, j), s in second.analysis.signatures.items()}
    for i, a in enumerate(first.rows):
        for j, b in enumerate(second.rows):
            signature = pairs.compare(a.cells, a.pivot, b.cells, b.pivot, pair_settings, pivot_code=pairs.E3)
            signatures[i, n + j] = signature
            same_form, same_root, letters = [], [], []
            for link in signature.links:
                if link.a is None or link.b is None or link.a == a.pivot or link.code not in pairs.COMMON:
                    continue
                pair = (a.cells[link.a], b.cells[link.b])
                if _is_letter(pair[0], tags) and _is_letter(pair[1], tags):
                    letters.append(pair)
                elif link.code == pairs.E0:
                    same_form.append(pair)
                else:
                    same_root.append(pair)
            cross.append(CrossPair(i, j, signature, tuple(same_form), tuple(same_root), tuple(letters)))

    rows = first.rows + second.rows
    mixed = families.Analysis(
        f"{form_a} / {form_b}", scheme, rows, signatures, tuple(families.trace(list(rows), signatures, family_settings)), ()
    )
    # Only the families holding segments of both forms have a matrix here.
    matrices = tuple(
        matrix.build(mixed, family, config["matrix"]["relative_min"])
        for family in mixed.families
        if any(r < n for r in family.rows) and any(r >= n for r in family.rows)
    )
    covariations = []
    relative_min = config["matrix"]["relative_min"]
    for number, m in enumerate(matrices):
        for k, column in enumerate(m.columns):
            if column.is_pivot:
                continue
            sides = (Counter(), Counter())
            for r, cell in zip(m.rows, column.cells):
                if cell is not None:
                    sides[r >= n][rows[r].cells[cell].form] += 1
            # Each form has its own filler, never the other's, on enough rows (D-10), and that filler
            # fills most of its rows (as a relatively fixed column, D-09): عالم → الغيب, علام → الغيوب.
            enough = all(sum(s.values()) >= settings.support_min for s in sides)
            dominant = all(s.most_common(1)[0][1] / sum(s.values()) >= relative_min for s in sides if s)
            if enough and dominant and not set(sides[0]) & set(sides[1]):
                covariations.append(Covariation(number, k, sides))
    return Comparison(first, second, tuple(sorted(roots_a & roots_b)), tuple(cross), mixed, matrices, tuple(covariations))


# --- Rendering (Markdown, Arabic) ---------------------------------------------------


def _share(n: int, total: int) -> str:
    return f"{n} ({n / total:.0%})" if total else "0"


def _top(counter: Counter, limit: int = 4) -> str:
    return "، ".join(f"{k} ({v})" for k, v in counter.most_common(limit)) or "—"


def _order(companion: sheet.Companion | None) -> str:
    if companion is None:
        return "—"
    if companion.after == 0:
        return f"{t('always_before')} ({companion.before})"
    if companion.before == 0:
        return f"{t('always_after')} ({companion.after})"
    return f"{t('before')} {companion.before} ، {t('after')} {companion.after}"


def render(found: Comparison, meta: dict[str, str], detail: bool = False) -> str:
    a, b = found.first, found.second
    na, nb = len(a.rows), len(b.rows)
    lines = [
        f"# {t('comparison_title')} — {a.form} / {b.form}",
        "",
        meta_line(meta, f"{t('scheme')} : {t(found.mixed.scheme)}", t("form_rule")),
        "",
        t("stats_pending"),
        "",
        f"- {t('root')} : {'، '.join(found.roots)}",
        f"- {a.form} : {t('occurrences')} {na} ؛ {t('box')} : {a.box}",
        f"- {b.form} : {t('occurrences')} {nb} ؛ {t('box')} : {b.box}",
    ]

    # أ. segment by segment
    total = len(found.cross)
    cases = Counter(case for pair in found.cross for case in pair.cases)
    both = sum(1 for pair in found.cross if pair.same_form and pair.same_root)
    types = Counter(" + ".join(pair.signature.types) for pair in found.cross)
    lines += [
        "",
        f"## {t('cross_section')}",
        "",
        f"- {t('pairs')} : {total} ({na} × {nb}) ؛ "
        + "، ".join(f"{' + '.join(t(k) for k in kinds.split(' + '))} ({kinds}) : {n}" for kinds, n in types.most_common()),
        f"- {t('case_a')} : {_share(cases['أ'], total)}",
        f"- {t('case_b')} : {_share(cases['ب'], total)}",
        f"- {t('case_both')} : {_share(both, total)}",
        f"- {t('case_c')} : {_share(cases['ج'], total)}",
    ]
    same_form = Counter(x.form for pair in found.cross for x, _ in pair.same_form)
    same_root = Counter(f"{x.form} ~ {y.form}" for pair in found.cross for x, y in pair.same_root)
    letters = Counter(x.form for pair in found.cross for x, _ in pair.letters)
    lines += [
        "",
        f"| {t('case_a_short')} | {t('pairs')} | {t('case_b_short')} | {t('pairs')} |",
        "|---|---|---|---|",
    ]
    left, right = same_form.most_common(10), same_root.most_common(10)
    for k in range(max(len(left), len(right))):
        x = left[k] if k < len(left) else ("", "")
        y = right[k] if k < len(right) else ("", "")
        lines.append(f"| {x[0]} | {x[1]} | {y[0]} | {y[1]} |")
    lines += ["", f"{t('letters_shared')} : {_top(letters, 8)}"]

    # ب. behaviour, side by side
    def row(label: str, x: str, y: str) -> str:
        return f"| {label} | {x} | {y} |"

    def positions(p: Profile) -> str:
        return "، ".join(f"{t(k)} {v}" for k, v in p.positions.most_common())

    def aya_positions(p: Profile) -> str:
        return "، ".join(f"{t(k)} {v}" for k, v in p.aya_positions.most_common())

    def kinds(p: Profile) -> str:
        total_ = sum(p.kinds.values())
        return "، ".join(f"{t(name)} {_share(p.kinds[key], total_)}" for key, name in
                         ((sheet.SAME_ROOT, "same_root"), (sheet.OTHER_ROOT, "other_roots"), (LETTER, "letters")))  # fmt: skip

    def formulas(p: Profile) -> str:
        return f"{_share(p.formula_rows, len(p.rows))}" + (f" : {p.formula_block}" if p.formula_block else "")

    def typology(p: Profile) -> str:
        if len(p.rows) < 2:
            return t("unique_short")
        return "، ".join(f"{k} : {v}" for k, v in p.types.most_common())

    lines += [
        "",
        f"## {t('behaviour_section')}",
        "",
        f"| {t('dimension')} | {a.form} | {b.form} |",
        "|---|---|---|",
        row(f"1. {t('dispersion')}", f"{len(a.suras)} {t('suras')} ؛ {_top(a.suras, 3)}", f"{len(b.suras)} {t('suras')} ؛ {_top(b.suras, 3)}"),
        row(f"2. {t('formulas')}", formulas(a), formulas(b)),
        row(f"4. {t('position')}", positions(a), positions(b)),
        row(f"5. {t('aya_position')}", aya_positions(a), aya_positions(b)),
        row(f"7. {t('companion_kinds')}", kinds(a), kinds(b)),
        row(f"12. {t('frame_before')}", _top(a.left), _top(b.left)),
        row(f"12. {t('frame_after')}", _top(a.right), _top(b.right)),
        row(f"14. {t('internal_typology')}", typology(a), typology(b)),
    ]

    # 8. fixed or variable sets
    lines += ["", f"### 8. {t('sets')}", "", f"| {t('root')} | {a.form} | {b.form} |", "|---|---|---|"]
    shared_roots = sorted(set(a.root_sets) | set(b.root_sets),
                          key=lambda r: -(sum(a.root_sets.get(r, Counter()).values()) + sum(b.root_sets.get(r, Counter()).values())))  # fmt: skip
    for root in shared_roots[: None if detail else 12]:
        lines.append(row(root, _top(a.root_sets.get(root, Counter())), _top(b.root_sets.get(root, Counter()))))

    # 9 and 11. companions, shared and proper, with their order
    by_form = [{c.form: c for c in p.companions if c.kind != LETTER} for p in (a, b)]
    roots_of = [{}, {}]
    for side, p in enumerate((a, b)):
        for row_ in p.rows:
            for cell in row_.cells:
                roots_of[side].setdefault(cell.form, cell.roots)
    lines += [
        "",
        f"### 9. {t('shared_companions')} — 11. {t('order')}",
        "",
        f"| {t('case')} | {t('form')} | {t('segments')} ({a.form}) | {t('order')} ({a.form}) | "
        f"{t('segments')} ({b.form}) | {t('order')} ({b.form}) | {t('same_root_other')} |",
        "|---|---|---|---|---|---|---|",
    ]
    entries = []
    for form in set(by_form[0]) | set(by_form[1]):
        ca, cb = by_form[0].get(form), by_form[1].get(form)
        roots = roots_of[0].get(form) or roots_of[1].get(form) or frozenset()
        if ca and cb:
            case, others = "أ", ""
        else:
            other = 1 if ca else 0
            relatives = sorted(f for f, c in by_form[other].items() if f != form and roots & roots_of[other].get(f, frozenset()))
            case, others = ("ب", "، ".join(relatives)) if relatives else ("ج", "")
        weight = (len(ca.segments) if ca else 0) + (len(cb.segments) if cb else 0)
        entries.append((case, -weight, form, ca, cb, others))
    entries.sort()
    for case, _, form, ca, cb, others in entries[: None if detail else 25]:
        lines.append(
            f"| {case} | {form} | {len(ca.segments) if ca else 0} | {_order(ca)} | "
            f"{len(cb.segments) if cb else 0} | {_order(cb)} | {others or '—'} |"
        )
    if not detail and len(entries) > 25:
        lines.append(f"\n{t('more_rows', n=len(entries) - 25)}")

    # ج. families the two forms share, and covariations (20)
    mixed = [f for f in found.mixed.families if found.is_mixed(f)]
    lines += [
        "",
        f"## {t('mixed_section')}",
        "",
        f"- {t('families_title')} : {len([f for f in found.mixed.families if not f.isolated])} ؛ "
        f"{t('mixed_families')} : {len(mixed)}",
    ]
    if found.covariations:
        lines += ["", f"### 20. {t('covariations')}", "", f"| {t('family')} | {a.form} | {b.form} |", "|---|---|---|"]
        for cov in found.covariations:
            lines.append(f"| {cov.family + 1} | {_top(cov.fillers[0])} | {_top(cov.fillers[1])} |")
    else:
        lines += ["", f"20. {t('covariations')} : {t('none')}"]
    lines += matrix.render(found.mixed, list(found.matrices), light=not detail)
    return "\n".join(lines) + "\n"
