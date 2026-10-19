"""Level 5, first part (SPEC §2.12-c, D-17): two forms of the same root, compared.

The comparison starts from the segments: every segment of the first form is compared
directly with every segment of the second (level 1, the two forms as pivots paired by
their root, code E3). Each pair is read in the three cases of the research notes:

    أ  the same form beside both                 يقدر and قدير with شيء
    ب  forms of one root, different forms        عالم with الغيب, علام with الغيوب
    ج  neither

Letters and pronouns are counted apart: the detached waw would otherwise be shared by
almost every pair. The two profiles (profile.py) are then set side by side, and the
families the two forms share get a matrix and their covariations.

Three layers (docs/DIMENSIONS.md): وصف (profiles side by side), تصنيف (pairs in the three
cases, shared families and matrices), تحليل (covariations tested against chance).
"""

from __future__ import annotations

import sqlite3
from collections import Counter
from dataclasses import dataclass

from . import families, matrix, pairs, sheet, validation
from . import profile as profiles
from .labels import meta_line, t

LETTER = sheet.LETTER


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
    family: int  # index in Comparison.matrices
    column: int
    fillers: tuple[Counter, Counter]  # forms beside the first form, beside the second
    finding: validation.Finding | None = None  # the random control, when run


@dataclass(frozen=True)
class Comparison:
    first: profiles.Profile
    second: profiles.Profile
    roots: tuple[str, ...]
    cross: tuple[CrossPair, ...]
    mixed: families.Analysis  # the rows of both forms together
    matrices: tuple[matrix.Matrix, ...]  # of the families holding segments of both forms
    covariations: tuple[Covariation, ...]
    validated: bool = False

    def case_counts(self) -> Counter:
        return Counter(case for pair in self.cross for case in pair.cases)


def _is_letter(cell: pairs.Cell, tags: dict[int, str]) -> bool:
    return not cell.roots and tags.get(cell.unit_id) not in sheet.CONTENT_TAGS


def compare_profiles(
    connection: sqlite3.Connection, first: profiles.Profile, second: profiles.Profile, config: dict, with_stats: bool = False
) -> Comparison:
    """Compare two forms whose profiles are built (a study builds each profile once)."""
    if not set(first.roots) & set(second.roots):
        raise ValueError("not_same_root")  # D-17: no comparison between roots
    pair_settings = pairs.PairSettings.from_config(config)
    tags = sheet._tags(connection, {c.unit_id for p in (first, second) for row in p.rows for c in row.cells})
    n = len(first.rows)
    cross: list[CrossPair] = []
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
        f"{first.form} / {second.form}", first.analysis.scheme, rows, signatures,
        tuple(families.trace(list(rows), signatures, families.FamilySettings.from_config(config))), (),
    )  # fmt: skip
    relative_min = config["matrix"]["relative_min"]
    support_min = config["comparison"]["support_min"]
    matrices = tuple(
        matrix.build(mixed, family, relative_min)
        for family in mixed.families
        if any(r < n for r in family.rows) and any(r >= n for r in family.rows)
    )
    stats_settings = validation.StatsSettings.from_config(config) if with_stats else None
    covariations = []
    for number, m in enumerate(matrices):
        for k, column in enumerate(m.columns):
            if column.is_pivot:
                continue
            sides = (Counter(), Counter())
            for r, cell in zip(m.rows, column.cells):
                if cell is not None:
                    sides[r >= n][rows[r].cells[cell].form] += 1
            # Each form has its own filler, never the other's, on enough rows (D-10), and that filler
            # fills most of its rows (as a relatively fixed column, D-09): عالم → الغيب, علام → الغيوب (Q31).
            enough = all(sum(s.values()) >= support_min for s in sides)
            dominant = all(s.most_common(1)[0][1] / sum(s.values()) >= relative_min for s in sides if s)
            if not (enough and dominant and not set(sides[0]) & set(sides[1])):
                continue
            finding = None
            if stats_settings:
                fillers = [rows[r].cells[cell].form if cell is not None else None for r, cell in zip(m.rows, column.cells)]
                observed, expected, p = validation.covariation(fillers, [int(r >= n) for r in m.rows], stats_settings)
                what = f"{sides[0].most_common(1)[0][0]} / {sides[1].most_common(1)[0][0]}"
                status = validation.ESTABLISHED if p <= stats_settings.alpha else validation.OBSERVED
                finding = validation.Finding(validation.COVARIATION, what, "", int(observed), expected, p, p, status)
            covariations.append(Covariation(number, k, sides, finding))
    return Comparison(first, second, tuple(sorted(set(first.roots) & set(second.roots))), tuple(cross), mixed,
                      matrices, tuple(covariations), with_stats)  # fmt: skip


def compare_forms(
    connection: sqlite3.Connection, form_a: str, form_b: str, scheme: str, config: dict, with_stats: bool = False
) -> Comparison:
    first = profiles.build(connection, form_a, scheme, config)
    second = profiles.build(connection, form_b, scheme, config)
    return compare_profiles(connection, first, second, config, with_stats)


# --- Rendering (Markdown, Arabic) ---------------------------------------------------

share, top = profiles.share, profiles.top


def _order(companion: sheet.Companion | None) -> str:
    if companion is None:
        return "—"
    if companion.after == 0:
        return f"{t('always_before')} ({companion.before})"
    if companion.before == 0:
        return f"{t('always_after')} ({companion.after})"
    return f"{t('before')} {companion.before} ، {t('after')} {companion.after}"


def _side_by_side(a: profiles.Profile, b: profiles.Profile, rows_a, rows_b) -> list[str]:
    lines = [f"| {t('dimension')} | {a.form} | {b.form} |", "|---|---|---|"]
    lines += [f"| {x[0]} | {x[1]} | {y[1]} |" for x, y in zip(rows_a, rows_b)]
    return lines


def render(found: Comparison, meta: dict[str, str], detail: bool = False) -> str:
    a, b = found.first, found.second
    na, nb = len(a.rows), len(b.rows)
    lines = [
        f"# {t('comparison_title')} — {a.form} / {b.form}",
        "",
        meta_line(meta, f"{t('scheme')} : {t(found.mixed.scheme)}", t("form_rule")),
        "",
        # --- أ. الوصف -------------------------------------------------------------------
        f"## {t('describe_section')}",
        "",
        f"- {t('root')} : {'، '.join(found.roots)}",
    ]
    for p in (a, b):
        lines.append(
            f"- {p.form} : {t('occurrences')} {len(p.rows)} ؛ {t('dispersion')} {len(p.suras)} {t('suras')} ؛ {t('box')} : {p.box}"
        )
    lines += ["", f"### {t('core')}", "", *_side_by_side(a, b, profiles.described_rows(a), profiles.described_rows(b))]
    if detail:
        lines += ["", f"### {t('details')}", "", *_side_by_side(a, b, profiles.detail_rows(a), profiles.detail_rows(b))]

    lines += ["", f"### {t('sets')}", "", f"| {t('root')} | {a.form} | {b.form} |", "|---|---|---|"]
    roots = sorted(set(a.root_sets) | set(b.root_sets),
                   key=lambda r: -(sum(a.root_sets.get(r, Counter()).values()) + sum(b.root_sets.get(r, Counter()).values())))  # fmt: skip
    for root in roots[: None if detail else 12]:
        lines.append(f"| {root} | {top(a.root_sets.get(root, Counter()))} | {top(b.root_sets.get(root, Counter()))} |")

    # --- ب. التصنيف والتمثيل ---------------------------------------------------------------
    total = len(found.cross)
    cases = found.case_counts()
    both = sum(1 for pair in found.cross if pair.same_form and pair.same_root)
    types = Counter(" + ".join(pair.signature.types) for pair in found.cross)
    lines += [
        "",
        f"## {t('classify_section')}",
        "",
        f"### {t('cross_section')}",
        "",
        f"- {t('pairs')} : {total} ({na} × {nb}) ؛ "
        + "، ".join(f"{' + '.join(t(k) for k in kinds.split(' + '))} ({kinds}) : {n}" for kinds, n in types.most_common()),
        f"- {t('case_a')} : {share(cases['أ'], total)}",
        f"- {t('case_b')} : {share(cases['ب'], total)}",
        f"- {t('case_both')} : {share(both, total)}",
        f"- {t('case_c')} : {share(cases['ج'], total)}",
        "",
        f"| {t('case_a_short')} | {t('pairs')} | {t('case_b_short')} | {t('pairs')} |",
        "|---|---|---|---|",
    ]
    left = Counter(x.form for pair in found.cross for x, _ in pair.same_form).most_common(10)
    right = Counter(f"{x.form} ~ {y.form}" for pair in found.cross for x, y in pair.same_root).most_common(10)
    for k in range(max(len(left), len(right))):
        x = left[k] if k < len(left) else ("", "")
        y = right[k] if k < len(right) else ("", "")
        lines.append(f"| {x[0]} | {x[1]} | {y[0]} | {y[1]} |")
    letters = Counter(x.form for pair in found.cross for x, _ in pair.letters)
    lines += ["", f"{t('letters_shared')} : {top(letters, 8)}"]
    lines += ["", f"### {t('internal_typology')}", "", *_side_by_side(a, b, profiles.classified_rows(a), profiles.classified_rows(b))]

    by_form = [{c.form: c for c in p.companions if c.kind != LETTER} for p in (a, b)]
    roots_of: list[dict] = [{}, {}]
    for side, p in enumerate((a, b)):
        for row_ in p.rows:
            for cell in row_.cells:
                roots_of[side].setdefault(cell.form, cell.roots)
    entries = []
    for form in set(by_form[0]) | set(by_form[1]):
        ca, cb = by_form[0].get(form), by_form[1].get(form)
        form_roots = roots_of[0].get(form) or roots_of[1].get(form) or frozenset()
        if ca and cb:
            case, others = "أ", ""
        else:
            other = 1 if ca else 0
            relatives = sorted(f for f in by_form[other] if f != form and form_roots & roots_of[other].get(f, frozenset()))
            case, others = ("ب", "، ".join(relatives)) if relatives else ("ج", "")
        weight = (len(ca.segments) if ca else 0) + (len(cb.segments) if cb else 0)
        entries.append((case, -weight, form, ca, cb, others))
    entries.sort()
    lines += [
        "",
        f"### {t('shared_companions')} — {t('order')}",
        "",
        f"| {t('case')} | {t('form')} | {t('segments')} ({a.form}) | {t('order')} ({a.form}) | "
        f"{t('segments')} ({b.form}) | {t('order')} ({b.form}) | {t('same_root_other')} |",
        "|---|---|---|---|---|---|---|",
    ]
    for case, _, form, ca, cb, others in entries[: None if detail else 25]:
        lines.append(
            f"| {case} | {form} | {len(ca.segments) if ca else 0} | {_order(ca)} | "
            f"{len(cb.segments) if cb else 0} | {_order(cb)} | {others or '—'} |"
        )
    if not detail and len(entries) > 25:
        lines.append(f"\n{t('more_rows', n=len(entries) - 25)}")

    lines += [
        "",
        f"### {t('mixed_section')}",
        "",
        f"- {t('families_title')} : {len([f for f in found.mixed.families if not f.isolated])} ؛ "
        f"{t('mixed_families')} : {len(found.matrices)}",
    ]
    lines += matrix.render(found.mixed, list(found.matrices), light=not detail)

    # --- ج. التحليل ---------------------------------------------------------------------
    lines += ["", f"## {t('analyse_section')}", "", f"### {t('covariations_title')}", ""]
    if not found.covariations:
        lines.append(t("none"))
    else:
        lines += [f"| {t('family')} | {a.form} | {b.form} | {t('status')} | p |", "|---|---|---|---|---|"]
        for cov in found.covariations:
            status = t(cov.finding.status) if cov.finding else t("observed")
            p = f"{cov.finding.p_value:.3f}" if cov.finding else "—"
            lines.append(f"| {cov.family + 1} | {top(cov.fillers[0])} | {top(cov.fillers[1])} | {status} | {p} |")
    if not found.validated:
        lines += ["", t("stats_not_run")]
    return "\n".join(lines) + "\n"
