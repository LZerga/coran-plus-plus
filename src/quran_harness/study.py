"""The complete study of a root, step by step (command `etude`; SPEC step 6b).

    0   root identity (level 0)
    1-3 every form of the root: pairs, families, matrices; its profile; its sheet
    E   random controls: companions and constraints of every form (shuffles shared)
    5a  every pair of forms, segment by segment; covariations tested
    5b  the families of the root: segments of all its forms together
    -   report, tables (CSV) and journal

Results go to one folder per study: sorties/<root>/<date>_<pause>_<settings hash>/. The
hash covers the configuration and the code version (SPEC §2.12-a): two studies are only
comparable if their hash is the same. A study interrupted and run again with the same
settings takes up where it stopped: finished steps are kept in `etat.sqlite`.

No comparison between roots (D-17): several roots give several studies.
"""

from __future__ import annotations

import csv
import hashlib
import json
import sqlite3
import time
from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import yaml

from . import __version__, comparison, concepts, families, frames, matrix, root_identity, sheet, validation
from . import profile as profiles
from .labels import meta_line, t
from .segmentation import selected_scheme
from .units import forms_of_root

CORE_DOMINANTS = ("positions", "order", "left", "right")  # dimensions read through their dominant value


@dataclass(frozen=True)
class StudySettings:
    pair_min_occurrences: int  # forms with fewer occurrences are left out of the pairs of forms
    detail_min_occurrences: int  # a comparison of two forms gets its own file from this many occurrences on each side

    @classmethod
    def from_config(cls, config: dict) -> StudySettings:
        s = config["study"]
        return cls(s["pair_min_occurrences"], s["detail_min_occurrences"])


def settings_hash(config: dict) -> str:
    text = json.dumps(config, sort_keys=True, ensure_ascii=False) + __version__
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:10]


class State:
    """Finished steps of a study, kept beside its results, so that a study can resume."""

    def __init__(self, path: Path):
        self.connection = sqlite3.connect(path)
        self.connection.execute("CREATE TABLE IF NOT EXISTS steps (name TEXT PRIMARY KEY, value TEXT NOT NULL)")

    def get(self, name: str):
        row = self.connection.execute("SELECT value FROM steps WHERE name = ?", (name,)).fetchone()
        return json.loads(row[0]) if row else None

    def put(self, name: str, value) -> None:
        self.connection.execute("INSERT OR REPLACE INTO steps VALUES (?, ?)", (name, json.dumps(value, ensure_ascii=False)))
        self.connection.commit()


def _finding_dict(f: validation.Finding) -> dict:
    return {"kind": f.kind, "what": f.what, "detail": f.detail, "support": f.support, "expected": f.expected,
            "p": f.p_value, "q": f.q_value, "status": f.status}  # fmt: skip


def _finding(d: dict) -> validation.Finding:
    return validation.Finding(d["kind"], d["what"], d["detail"], d["support"], d["expected"], d["p"], d["q"], d["status"])


def _file_name(form: str) -> str:
    """A file name for a form: its letters without vowels (easier to open than a vocalised name)."""
    from .normalize import Level, normalize

    return _safe(normalize(form, Level.NO_VOWELS).replace("ٱ", "ا"))


def _safe(name: str) -> str:
    return "".join(ch for ch in name if ch.isalnum() or ch in "-_") or "x"


def run(connection: sqlite3.Connection, root: str, config: dict, out_root: Path, with_stats: bool = True, say=print) -> Path:
    """Run the whole study of a root; returns the folder of its results."""
    started = time.time()
    timings: dict[str, float] = {}
    scheme = selected_scheme(config)
    meta = dict(connection.execute("SELECT key, value FROM meta"))
    found = root_identity.identity(connection, root)
    if found is None:
        raise ValueError("no_root")
    study_settings = StudySettings.from_config(config)
    pause = config["segmentation"]["pause_level"] if config["segmentation"]["scheme"] == "waqf" else "verset"
    folder = out_root / _safe(found.root) / f"{date.today().isoformat()}_{pause}_{'stats' if with_stats else 'sans-stats'}_{settings_hash(config)}"
    (folder / "fiches").mkdir(parents=True, exist_ok=True)
    (folder / "comparaisons").mkdir(exist_ok=True)
    state = State(folder / "etat.sqlite")

    def step(name: str):
        timings[name] = time.time()
        say(f"[{name}]")

    # 0. Root identity -----------------------------------------------------------------------
    step("0 هوية الجذر")
    (folder / "00_هوية_الجذر.md").write_text(root_identity.render(found, meta), encoding="utf-8")

    # 1-3. Every form: profile and sheet ----------------------------------------------------------
    step("1-3 الصيغ")
    forms = [f.form for f in forms_of_root(connection, found.root)]
    built: dict[str, profiles.Profile] = {}
    for number, form in enumerate(forms, start=1):
        built[form] = profiles.build(connection, form, scheme, config)
        if number % 10 == 0 or number == len(forms):
            say(f"  {number}/{len(forms)}")

    # E. Random controls -------------------------------------------------------------------------
    findings: dict[str, dict[str, list[validation.Finding]]] = {}
    if with_stats:
        step("E الخلط العشوائي")
        saved = state.get("findings")
        if saved is None:
            raw = sheet.validate(connection, list(built.values()), scheme, config)
            saved = {form: {kind: [_finding_dict(f) for f in items] for kind, items in kinds.items()} for form, kinds in raw.items()}
            state.put("findings", saved)
        findings = {form: {kind: [_finding(d) for d in items] for kind, items in kinds.items()} for form, kinds in saved.items()}
    for number, form in enumerate(forms, start=1):
        card = sheet.Sheet(built[form], findings.get(form) if with_stats else None)
        (folder / "fiches" / f"{number:03d}_{_file_name(form)}.md").write_text(sheet.render(card, meta, config), encoding="utf-8")

    # 5a. Every pair of forms -------------------------------------------------------------------
    step("5a مقارنة الصيغ")
    eligible = [f for f in forms if len(built[f].rows) >= study_settings.pair_min_occurrences]
    pair_rows: list[dict] = []
    total_pairs = len(eligible) * (len(eligible) - 1) // 2
    done = 0
    for i, form_a in enumerate(eligible):
        for form_b in eligible[i + 1 :]:
            done += 1
            key = f"pair:{form_a}|{form_b}"
            summary = state.get(key)
            if summary is None:
                found_pair = comparison.compare_profiles(connection, built[form_a], built[form_b], config, with_stats)
                cases = found_pair.case_counts()
                summary = {
                    "a": form_a, "b": form_b, "pairs": len(found_pair.cross),
                    "case_a": cases["أ"], "case_b": cases["ب"], "case_c": cases["ج"],
                    "types": dict(Counter(" + ".join(p.signature.types) for p in found_pair.cross)),
                    "mixed_families": len(found_pair.matrices),
                    "covariations": [
                        {"a": c.fillers[0].most_common(1)[0][0], "b": c.fillers[1].most_common(1)[0][0],
                         "status": c.finding.status if c.finding else validation.OBSERVED,
                         "p": c.finding.p_value if c.finding else None}
                        for c in found_pair.covariations
                    ],
                }  # fmt: skip
                if min(len(built[form_a].rows), len(built[form_b].rows)) >= study_settings.detail_min_occurrences:
                    name = f"{forms.index(form_a) + 1:03d}-{forms.index(form_b) + 1:03d}_{_file_name(form_a)}_{_file_name(form_b)}.md"
                    (folder / "comparaisons" / name).write_text(comparison.render(found_pair, meta), encoding="utf-8")
                state.put(key, summary)
            pair_rows.append(summary)
            if done % 50 == 0 or done == total_pairs:
                say(f"  {done}/{total_pairs}")

    # 5b. The families of the root --------------------------------------------------------------
    step("5b أنواع استعمال الجذر")
    root_families = _root_families(connection, [built[f] for f in forms], config)

    # Frames and slots (short window), formal concepts ---------------------------------------------
    step("القوالب والمفاهيم")
    root_frames = frames.build(connection, found.root, scheme, config["statistics"]["alpha"])
    context = concepts.table([built[f] for f in forms])
    root_concepts = concepts.concepts(context)

    # Tables, report, journal --------------------------------------------------------------------
    step("التقرير")
    _write_csv(folder, forms, built, pair_rows, findings)
    informative = _informative_dimensions([built[f] for f in forms if len(built[f].rows) >= 3])
    report = _report(found, forms, built, findings, pair_rows, root_families, informative, meta, config, scheme, with_stats,
                     root_frames, root_concepts, context)
    report += _file_list(folder, forms, built)
    (folder / "01_القوالب.md").write_text(frames.render(root_frames, meta, detail=True), encoding="utf-8")
    from . import visuals

    visuals.forms_pairs_page(folder)  # rule of the author: every study comes with its charts
    (folder / "00_التقرير.md").write_text(report, encoding="utf-8")
    timings["fin"] = time.time()
    _journal(folder, found.root, config, meta, connection, timings, started, with_stats, len(forms), total_pairs)
    say(t("written", path=str(folder)))
    return folder


def _root_families(connection: sqlite3.Connection, all_profiles: list[profiles.Profile], config: dict) -> dict:
    """Families of the segments of all the forms of the root (SPEC §2.12-e): which forms share a template."""
    rows, owner, signatures, offset = [], [], {}, 0
    starts = []
    for p in all_profiles:
        starts.append(offset)
        rows += list(p.rows)
        owner += [p.form] * len(p.rows)
        signatures |= {(offset + i, offset + j): s for (i, j), s in p.analysis.signatures.items()}
        offset += len(p.rows)
    from . import pairs as pairs_module

    pair_settings = pairs_module.PairSettings.from_config(config)
    for x, p in enumerate(all_profiles):
        for y in range(x + 1, len(all_profiles)):
            q = all_profiles[y]
            for i, a in enumerate(p.rows):
                for j, b in enumerate(q.rows):
                    signatures[starts[x] + i, starts[y] + j] = pairs_module.compare(
                        a.cells, a.pivot, b.cells, b.pivot, pair_settings, pivot_code=pairs_module.E3
                    )
    analysis = families.Analysis("root", all_profiles[0].analysis.scheme if all_profiles else "", tuple(rows), signatures,
                                 tuple(families.trace(rows, signatures, families.FamilySettings.from_config(config))), ())  # fmt: skip
    groups = []
    for family in analysis.families:
        members = Counter(owner[r] for r in family.rows)
        template = ""
        if len(members) >= 2:
            template = matrix.build(analysis, family, config["matrix"]["relative_min"]).template
        groups.append({"forms": dict(members.most_common()), "rows": len(family.rows), "cohesion": family.cohesion,
                       "template": template, "refs": [rows[r].segment_ref for r in family.rows]})  # fmt: skip
    isolated = Counter(owner[f.rows[0]] for f in analysis.families if f.isolated)
    totals = Counter(owner)
    return {
        "families": groups,
        "forms_alone": sorted(form for form, n in isolated.items() if n == totals[form]),
        "isolated_uses": {form: n for form, n in isolated.most_common() if n < totals[form]},
    }


def _dominant(counter: Counter) -> str:
    return counter.most_common(1)[0][0] if counter else "—"


def _informative_dimensions(eligible: list[profiles.Profile]) -> dict[str, int]:
    """For each core dimension read through its dominant value: how many different values the forms show."""
    return {name: len({_dominant(getattr(p, name)) for p in eligible}) for name in CORE_DOMINANTS} | {
        "repetition": len({p.formula_rows * 2 >= len(p.rows) for p in eligible}),
    }


def _write_csv(folder: Path, forms, built, pair_rows, findings) -> None:
    with open(folder / "profils.csv", "w", encoding="utf-8-sig", newline="") as f:
        out = csv.writer(f)
        out.writerow(["form", "occurrences", "suras", "position", "before", "after", "formula_rows", "families", "isolated"])
        for form in forms:
            p = built[form]
            real = [x for x in p.analysis.families if not x.isolated]
            out.writerow([form, len(p.rows), len(p.suras), _dominant(p.positions), _dominant(p.left), _dominant(p.right),
                          p.formula_rows, len(real), len(p.analysis.families) - len(real)])  # fmt: skip
    with open(folder / "paires_formes.csv", "w", encoding="utf-8-sig", newline="") as f:
        out = csv.writer(f)
        out.writerow(["form_a", "form_b", "pairs", "case_a", "case_b", "case_c", "mixed_families", "covariations"])
        for r in pair_rows:
            out.writerow([r["a"], r["b"], r["pairs"], r["case_a"], r["case_b"], r["case_c"], r["mixed_families"], len(r["covariations"])])
    with open(folder / "resultats.csv", "w", encoding="utf-8-sig", newline="") as f:
        out = csv.writer(f)
        out.writerow(["form", "kind", "what", "detail", "support", "expected", "p", "q", "status"])
        for form, kinds in findings.items():
            for items in kinds.values():
                for x in items:
                    out.writerow([form, x.kind, x.what, x.detail, x.support, x.expected, x.p_value, x.q_value, x.status])


def _synthesis(forms, built, findings, pair_rows, root_frames, root_concepts) -> list[str]:
    """The clearest regularities of the root, as short descriptive sentences, each with its status (Q41)."""
    from collections import Counter as _Counter

    def top(counter, n=3):
        return "، ".join(f"{k} ({v})" for k, v in _Counter(counter).most_common(n) if k != frames.EDGE)

    items: list[tuple[str, str]] = []
    for side, branches in (("after", root_frames.continuations), ("before", root_frames.antecedents)):
        chosen = [b for b in branches if b.cell != frames.EDGE and b.established and b.count >= 3]
        for b in sorted(chosen, key=lambda b: (b.expected / b.count, -b.count))[:3]:
            items.append((t(f"syn_frame_{side}", cell=b.cell, n=b.count, total=root_frames.occurrences,
                            expected=f"{b.expected:.2f}", second=top(b.second), forms=top(b.forms)), t("established")))  # fmt: skip
    for s in [s for s in root_frames.slots if sum(s.fillers.values()) >= 3][:2]:
        items.append((t("syn_slot", before=s.before, after=s.after, n=sum(s.fillers.values()), forms=top(s.fillers)), t("observed")))
    formulas = [built[f] for f in forms if len(built[f].rows) >= 3 and built[f].formula_rows * 2 >= len(built[f].rows)]
    for p in sorted(formulas, key=lambda p: -p.formula_rows)[:2]:
        items.append((t("syn_formula", form=p.form, n=p.formula_rows, total=len(p.rows), block=p.formula_block), t("described")))
    for r in pair_rows:
        for c in r["covariations"]:
            if c["status"] == validation.ESTABLISHED and sum(1 for x in items if x[0].startswith("«")) < 2:
                items.append((t("syn_covariation", a=r["a"], x=c["a"], b=r["b"], y=c["b"]), t("established")))
    associations = [(form, x) for form in forms for x in findings.get(form, {}).get(validation.ASSOCIATION, [])
                    if x.status == validation.ESTABLISHED and x.support >= 3]  # fmt: skip
    for form, x in sorted(associations, key=lambda fx: -fx[1].support)[:2]:
        items.append((t("syn_association", form=form, companion=x.what, n=x.support), t("established")))
    shared = [c for c in root_concepts if len(c.extent) >= 2 and len(c.intent) >= 2]
    for c in shared[:1]:
        items.append((t("syn_concept", forms="، ".join(sorted(c.extent)), companions="، ".join(sorted(c.intent))), t("described")))
    lines = [f"## {t('synthesis_title')}", "", t("synthesis_note"), ""]
    lines += [f"{k}. {text} — **{status}**" for k, (text, status) in enumerate(items[:10], start=1)] or [t("none")]
    return lines + [""]


def _report(found, forms, built, findings, pair_rows, root_families, informative, meta, config, scheme, with_stats,
            root_frames=None, root_concepts=None, context=None) -> str:  # fmt: skip
    lines = [
        f"# {t('study_title')} — {found.root}",
        "",
        meta_line(meta, f"{t('scheme')} : {t(scheme)}", t("form_rule")),
        "",
        f"- {found.letters} ؛ {found.nature} ؛ {t('occurrences')} : {found.total} ؛ {t('forms')} : {len(forms)}",
        f"- {t('study_files')}",
        "",
    ]
    if root_frames is not None:
        lines += _synthesis(forms, built, findings, pair_rows, root_frames, root_concepts or [])
    # ج. Analysis first (docs/DIMENSIONS.md, rule 4): established results, each with its sheet.
    lines += [f"## {t('analyse_section')}", ""]
    if not with_stats:
        lines += [t("stats_not_run"), ""]
    else:
        s = config["statistics"]
        lines += [t("stats_rule", n=s["permutations"], seed=s["seed"], alpha=s["alpha"]), ""]
        head = f"| {t('form')} | {t('kind')} | {t('result')} | {t('support')} | {t('q_value')} |"
        rows = []
        for form in forms:
            for kind, items in findings.get(form, {}).items():
                for x in items:
                    if x.status == validation.ESTABLISHED:
                        rows.append(f"| {form} | {t(kind)} | {x.what}{' (' + t(x.detail) + ')' if kind == 'constraint' else ''} | {x.support} | {x.q_value:.3f} |")
        cov = [(r, c) for r in pair_rows for c in r["covariations"] if c["status"] == validation.ESTABLISHED]
        lines += [f"### {t('established_results')}", "", head, "|---|---|---|---|---|", *rows[:80]]
        if len(rows) > 80:
            lines.append(f"\n{t('more_rows', n=len(rows) - 80)} (resultats.csv)")
        lines += ["", f"### {t('covariations_title')}", ""]
        if cov:
            lines += [f"| {t('form')} 1 | {t('form')} 2 | {t('result')} | p |", "|---|---|---|---|"]
            lines += [f"| {r['a']} | {r['b']} | {c['a']} / {c['b']} | {c['p']:.3f} |" for r, c in cov]
        else:
            lines.append(t("none"))
    if root_frames is not None:
        lines += ["", f"### {t('frames_title')}", "", *frames.render_section(root_frames)]
    lines += ["", f"### {t('informative_title')}", "", f"| {t('dimension')} | {t('distinct_values')} |", "|---|---|"]
    names = {"positions": t("position"), "order": t("order"), "left": t("frame_before"), "right": t("frame_after"), "repetition": t("repetition")}
    lines += [f"| {names[k]} | {v} |" for k, v in informative.items()]
    lines += ["", t("informative_note")]

    # ب. Classification: forms × forms, families of the root
    lines += ["", f"## {t('classify_section')}", "", f"### {t('forms_pairs_title')}", ""]
    ranked = sorted(pair_rows, key=lambda r: (-(r["pairs"] - r["case_c"]), -r["pairs"]))
    lines += [t("forms_pairs_note"), "",
              f"| {t('form')} 1 | {t('form')} 2 | {t('pairs')} | أ | ب | ج | {t('mixed_families')} |", "|---|---|---|---|---|---|---|"]
    for r in ranked[:40]:
        lines.append(f"| {r['a']} | {r['b']} | {r['pairs']} | {r['case_a']} | {r['case_b']} | {r['case_c']} | {r['mixed_families']} |")
    if len(ranked) > 40:
        lines.append(f"\n{t('more_rows', n=len(ranked) - 40)} (paires_formes.csv)")
    if context is not None:
        lines += ["", f"### {t('concepts_title')}", "", *concepts.render_section(root_concepts, context)]
    lines += ["", f"### {t('root_families_title')}", ""]
    shared = [g for g in root_families["families"] if len(g["forms"]) >= 2]
    lines += [f"| {t('forms')} | {t('rows')} | {t('cohesion')} | {t('template')} |", "|---|---|---|---|"]
    for g in shared[:30]:
        template = g["template"] if len(g["template"]) <= 160 else g["template"][:160] + " …"
        forms_text = "، ".join(f"{f} ({n})" for f, n in list(g["forms"].items())[:12])
        if len(g["forms"]) > 12:
            forms_text += f"، … (+{len(g['forms']) - 12})"
        lines.append(f"| {forms_text} | {g['rows']} | {g['cohesion']:.0%} | `{template}` |")
    if shared and shared[0]["rows"] > 0.8 * sum(g["rows"] for g in root_families["families"]):
        lines += ["", t("one_big_family")]
    alone = root_families["forms_alone"]
    lines += ["", f"{t('forms_alone')} : {'، '.join(alone) or '—'}"]
    some = root_families["isolated_uses"]
    if some:
        lines.append(f"{t('isolated_uses')} : " + "، ".join(f"{form} ({n})" for form, n in some.items()))

    # أ. Description: the forms and their core dimensions
    lines += ["", f"## {t('describe_section')}", "",
              f"| {t('form')} | {t('occurrences')} | {t('suras')} | {t('position')} | {t('frame_before')} | {t('frame_after')} | {t('repetition')} |",
              "|---|---|---|---|---|---|---|"]  # fmt: skip
    for form in forms:
        p = built[form]
        lines.append(
            f"| {form} | {len(p.rows)} | {len(p.suras)} | {t(_dominant(p.positions))} | {_dominant(p.left)} | "
            f"{_dominant(p.right)} | {profiles.share(p.formula_rows, len(p.rows))} |"
        )
    return "\n".join(lines) + "\n"


def _file_list(folder: Path, forms, built) -> str:
    """Links to the sheets and the comparisons, opened from the report (web tab الدراسات)."""
    lines = ["", f"## {t('files_title')}", "", f"- [{t('identity')}](00_هوية_الجذر.md)",
             f"- [{t('frames_title')}](01_القوالب.md)", f"- [Journal](journal.md)",
             "- " + t("visual_file"), "",
             f"### {t('sheets_title')}", ""]  # fmt: skip
    for number, form in enumerate(forms, start=1):
        name = f"{number:03d}_{_file_name(form)}.md"
        lines.append(f"- [{form}](fiches/{name}) — {t('occurrences')} {len(built[form].rows)}")
    comparisons = sorted((folder / "comparaisons").glob("*.md"))
    if comparisons:
        lines += ["", f"### {t('comparisons_title')}", ""]
        for path in comparisons:
            first, second = path.stem.split("_", 1)[0].split("-")
            label = f"{forms[int(first) - 1]} / {forms[int(second) - 1]}"
            lines.append(f"- [{label}](comparaisons/{path.name})")
    return "\n".join(lines) + "\n"


def _journal(folder, root, config, meta, connection, timings, started, with_stats, n_forms, n_pairs) -> None:
    names = list(timings)
    durations = [f"- {names[k]} : {timings[names[k + 1]] - timings[names[k]]:.1f} s" for k in range(len(names) - 1)]
    sources = {k: v for k, v in meta.items() if k.startswith("sha256:")}
    text = [
        f"# Journal de l'étude — {root}",
        "",
        f"- Date : {date.today().isoformat()}",
        f"- Code : {__version__} (base construite avec {meta.get('code_version')})",
        f"- Empreinte des réglages : {settings_hash(config)}",
        f"- Contrôle aléatoire : {'oui' if with_stats else 'non'}",
        f"- Formes : {n_forms} ; paires de formes comparées : {n_pairs}",
        f"- Durée totale : {time.time() - started:.0f} s",
        "",
        "## Durées par étape",
        "",
        *durations,
        "",
        "## Sources (SHA-256 des fichiers bruts)",
        "",
        *(f"- {k[7:]} : {v}" for k, v in sorted(sources.items())),
        "",
        "## Réglages (config.yaml, avec les choix de la commande)",
        "",
        "```yaml",
        yaml.safe_dump(config, allow_unicode=True, sort_keys=False).rstrip(),
        "```",
    ]
    (folder / "journal.md").write_text("\n".join(text) + "\n", encoding="utf-8")
