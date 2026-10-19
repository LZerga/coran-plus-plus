"""Step 5 output: the sheet (بطاقة) of a reference form, new method (SPEC §2.3 to §2.5, step 5).

    أ  identity card   the form, its root and its box at level 0, occurrences, segments, positions
    ب  companions      the other cells of its segments: (a) same root, (b) other roots, (c) letters
                       and pronouns (SPEC §1)
    ج  uses            pairs (level 1), families (level 2), matrices and templates (level 3)

Everything is computed from the database; nothing is interpreted. Tables are light by
default (SPEC step 8): references, pairs one by one and matrix columns filled by one row
only are shown with `detail=True`. The statistical layer (step 6) is not built yet: the
counts are observations, and the sheet says so.
"""

from __future__ import annotations

import sqlite3
from collections import Counter
from dataclasses import dataclass, field

from . import families, matrix, pairs, root_identity
from .labels import meta_line, t

profile_module = None  # set lazily: profile imports this module

CONTENT_TAGS = frozenset({"N", "PN", "ADJ", "V", "IMPN"})  # never a "letter", even without a root
SAME_ROOT, OTHER_ROOT, LETTER = "a", "b", "c"


@dataclass
class Companion:
    kind: str
    form: str
    refs: list[str] = field(default_factory=list)
    segments: set[int] = field(default_factory=set)
    before: int = 0
    after: int = 0


@dataclass(frozen=True)
class Sheet:
    profile: "profile_module.Profile"
    findings: dict[str, list] | None = None  # kind -> findings of validation.py; None when the controls were not run

    @property
    def form(self) -> str:
        return self.profile.form

    @property
    def roots(self) -> tuple[str, ...]:
        return self.profile.roots

    @property
    def box(self) -> str:
        return self.profile.box

    @property
    def analysis(self) -> families.Analysis:
        return self.profile.analysis

    @property
    def matrices(self) -> tuple[matrix.Matrix, ...]:
        return self.profile.matrices

    @property
    def companions(self) -> list[Companion]:
        return self.profile.companions

    @property
    def occurrences(self) -> list[str]:
        return [row.cells[row.pivot].word_ref for row in self.analysis.rows]


def _tags(connection: sqlite3.Connection, unit_ids: set[int]) -> dict[int, str]:
    """Tag of the first stem of each cell's word; a detached waw is a conjunction."""
    if not unit_ids:
        return {}
    marks = ",".join("?" * len(unit_ids))
    rows = connection.execute(
        f"""SELECT u.id, CASE WHEN u.part = 1 THEN 'CONJ' ELSE
                   (SELECT s.tag FROM word_segments s WHERE s.word_id = u.word_id AND s.kind = 'stem'
                    ORDER BY s.seg_no LIMIT 1) END
            FROM units u WHERE u.id IN ({marks})""",
        tuple(unit_ids),
    )
    return {unit_id: tag or "" for unit_id, tag in rows}


def companions(connection: sqlite3.Connection, analysis: families.Analysis) -> list[Companion]:
    rows = analysis.rows
    tags = _tags(connection, {cell.unit_id for row in rows for cell in row.cells})
    found: dict[tuple[str, str], Companion] = {}
    seen: set[tuple[int, int]] = set()  # (segment, cell): a segment holding the form twice counts once
    for row in rows:
        pivot = row.cells[row.pivot]
        for index, cell in enumerate(row.cells):
            if index == row.pivot or (row.segment_id, cell.unit_id) in seen:
                continue
            seen.add((row.segment_id, cell.unit_id))
            if cell.roots & pivot.roots:
                kind = SAME_ROOT
            elif not cell.roots and tags.get(cell.unit_id) not in CONTENT_TAGS:
                kind = LETTER
            else:
                kind = OTHER_ROOT
            companion = found.setdefault((kind, cell.form), Companion(kind, cell.form))
            companion.refs.append(cell.ref)
            companion.segments.add(row.segment_id)
            if index < row.pivot:
                companion.before += 1
            else:
                companion.after += 1
    return sorted(found.values(), key=lambda c: (c.kind, -len(c.segments), -len(c.refs), c.form))


def _box(connection: sqlite3.Connection, form: str, roots: tuple[str, ...], refs: set[str]) -> str:
    """Where the form stands in the root identity tables (level 0)."""
    if not roots:
        return "—"
    found = root_identity.identity(connection, roots[0])
    boxes = Counter()
    for (wazn, column), entries in found.verbs.items():
        boxes[f"{wazn} — {column}"] += sum(1 for e in entries for ref in e.refs if ref in refs)
    for (kind, number, pattern), entries in found.nouns.items():
        label = kind.replace("ambiguë", t("ambiguous"), 1)
        boxes[f"{label} — {pattern}"] += sum(1 for e in entries for ref in e.refs if ref in refs)
    return " ؛ ".join(f"{box} ({n})" for box, n in boxes.most_common() if n) or "—"


def build(connection: sqlite3.Connection, form: str, scheme: str, config: dict, with_stats: bool = False) -> Sheet:
    """The sheet of a form given with its vowels as stored (`units.form`)."""
    from . import profile as profile_module
    from . import validation

    found = profile_module.build(connection, form, scheme, config)
    if not with_stats:
        return Sheet(found)
    return Sheet(found, validate(connection, [found], scheme, config)[form])


def validate(connection: sqlite3.Connection, profiles: list, scheme: str, config: dict) -> dict[str, dict[str, list]]:
    """Random controls for several forms at once (associations share their shuffles)."""
    from . import validation

    settings = validation.StatsSettings.from_config(config)
    data = validation.corpus(connection, scheme)
    requests = [
        validation.AssociationRequest(
            p.form, tuple(row.cells[row.pivot].ref for row in p.rows), tuple(c.form for c in p.companions)
        )
        for p in profiles
        if p.rows
    ]
    associations = validation.associations(data, requests, settings)
    found = {}
    for p in profiles:
        constraints = [f for m in p.matrices for f in validation.constraints(p.analysis, m, settings)]
        found[p.form] = {validation.ASSOCIATION: associations.get(p.form, []), validation.CONSTRAINT: constraints}
    return found


# --- Rendering (Markdown, Arabic) ---------------------------------------------------


def _position(index: int, length: int) -> str:
    return pairs._position(index, length)


def _refs(refs: list[str], limit: int = 12) -> str:
    shown = "، ".join(refs[:limit])
    return shown if len(refs) <= limit else f"{shown}، … (+{len(refs) - limit})"


def findings_table(findings: list, with_expected: bool = True) -> list[str]:
    head = [t("form"), t("status"), t("support")] + ([t("expected")] if with_expected else []) + [t("q_value")]
    lines = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for f in findings:
        cells = [f.what + (f" ({t(f.detail)})" if f.kind == "constraint" else ""), t(f.status), str(f.support)]
        cells += [f"{f.expected:.2f}"] if with_expected and f.expected is not None else ([""] if with_expected else [])
        cells += [f"{f.q_value:.3f}"]
        lines.append("| " + " | ".join(cells) + " |")
    return lines


def render(sheet: Sheet, meta: dict[str, str], config: dict, detail: bool = False) -> str:
    from . import profile as profile_module

    p = sheet.profile
    analysis, rows = p.analysis, p.rows
    settings = families.FamilySettings.from_config(config)
    ayas = {ref.rsplit(":", 1)[0] for ref in sheet.occurrences}
    lines = [
        f"# {t('sheet_title')} — {sheet.form}",
        "",
        meta_line(meta, f"{t('scheme')} : {t(analysis.scheme)}", t("form_rule")),
        "",
        # --- أ. الوصف -------------------------------------------------------------------
        f"## {t('describe_section')}",
        "",
        f"- {t('root')} : {'، '.join(sheet.roots) or '—'} ؛ {t('box')} : {sheet.box}",
        f"- {t('frequency')} : {t('occurrences')} {len(rows)} ؛ {t('ayas')} {len(ayas)} ؛ "
        f"{t('segments')} {len({r.segment_id for r in rows})}",
        f"- {t('dispersion')} : {len(p.suras)} {t('suras')} ؛ {profile_module.top(p.suras, 3)}",
        "",
        f"| | {t('segment')} | {t('position')} | {t('text')} |",
        "|---|---|---|---|",
    ]
    for number, row in enumerate(rows, start=1):
        text = " ".join(f"**{c.text}**" if k == row.pivot else c.text for k, c in enumerate(row.cells))
        lines.append(f"| {number} | {row.segment_ref} | {t(_position(row.pivot, len(row.cells)))} | {text} |")
    lines += ["", f"### {t('core')}", "", *profile_module.table(profile_module.described_rows(p))]
    if detail:
        lines += ["", f"### {t('details')}", "", *profile_module.table(profile_module.detail_rows(p))]
    for kind, title in ((SAME_ROOT, t("same_root")), (OTHER_ROOT, t("other_roots")), (LETTER, t("letters"))):
        group = [c for c in p.companions if c.kind == kind]
        lines += ["", f"### {t('companions_section')} — {title}", ""]
        if not group:
            lines.append(t("none"))
            continue
        head = [t("form"), t("segments"), t("before"), t("after")] + ([t("refs")] if detail else [])
        lines += ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
        for c in group[: None if detail else 15]:
            cells = [c.form, str(len(c.segments)), str(c.before), str(c.after)] + ([_refs(c.refs)] if detail else [])
            lines.append("| " + " | ".join(cells) + " |")
        if not detail and len(group) > 15:
            lines.append(f"\n{t('more_rows', n=len(group) - 15)}")

    # --- ب. التصنيف والتمثيل ---------------------------------------------------------------
    lines += ["", f"## {t('classify_section')}", ""]
    if p.unique:
        lines.append(t("unique"))
    else:
        lines += [*profile_module.table(profile_module.classified_rows(p)), ""]
        real = [f for f in analysis.families if not f.isolated]
        lines += [
            f"- {t('link_rule', n=settings.link_min_common)} ؛ {t('cohesion_min')} : {settings.cohesion_min:.0%}",
            f"- {t('families_title')} : {len(real)} ؛ {t('isolated')} : {len(analysis.families) - len(real)}",
            "",
            f"| {t('family')} | {t('rows')} | {t('cohesion')} | {t('cuts')} | {t('segments')} |",
            "|---|---|---|---|---|",
        ]
        for number, family in enumerate(analysis.families, start=1):
            name = t("isolated") if family.isolated else str(number)
            cuts = "، ".join(f"{rows[i].segment_ref}–{rows[j].segment_ref}" for i, j, _ in family.cuts) or "—"
            lines.append(
                f"| {name} | {len(family.rows)} | {family.cohesion:.0%} | {cuts} | "
                + "، ".join(rows[i].segment_ref for i in family.rows) + " |"
            )
        lines += matrix.render(analysis, list(p.matrices), light=not detail)
        if detail:
            lines += ["", f"### {t('pairs')}", ""]
            for (i, j), signature in sorted(analysis.signatures.items()):
                parts = pairs.describe(rows[i].cells, rows[j].cells, signature)
                lines.append(f"- **{rows[i].segment_ref} / {rows[j].segment_ref}** : " + " ؛ ".join(f"{k} : {v}" for k, v in parts.items()))
        else:
            lines += ["", t("pairs_detail")]

    # --- ج. التحليل ---------------------------------------------------------------------
    lines += ["", f"## {t('analyse_section')}", ""]
    if sheet.findings is None:
        lines.append(t("stats_not_run"))
        return "\n".join(lines) + "\n"
    s = config["statistics"]
    lines += [t("stats_rule", n=s["permutations"], seed=s["seed"], alpha=s["alpha"]), ""]
    for kind, title in (("association", t("associations_title")), ("constraint", t("constraints_title"))):
        found = sheet.findings.get(kind, [])
        established = [f for f in found if f.status == "established"]
        lines += [f"### {title}", "", t("established_count", n=len(established), m=len(found) - len(established)), ""]
        shown = found if detail else established
        if shown:
            lines += [*findings_table(shown, with_expected=kind == "association"), ""]
    return "\n".join(lines) + "\n"
