"""Step 8: fiches as plain data, for the web page (JSON) and for export (CSV).

Nothing is computed here: every value comes from a `Fiche`. Each CSV row carries
the parameters it was computed with, so that an exported file stays traceable.
"""

from __future__ import annotations

import csv
import io
from collections import Counter

from . import compare
from .fiche import SAME_FORM, Fiche, PairResult, compare_companions

CSV_TABLES = ("segments", "compagnons", "paires", "lectures")


def _roles(n: int, comparison: compare.Comparison, side: str) -> list[str]:
    """What each word of one side of a comparison is: in block k, common, or extra."""
    roles = ["en plus"] * n
    for number, block in enumerate(comparison.blocks, start=1):
        start = block.a_start if side == "a" else block.b_start
        for k in range(block.length):
            roles[start + k] = f"bloc {number}"
    for pair in comparison.pairs:
        roles[pair.a_index if side == "a" else pair.b_index] = f"commun, {compare.LEVEL_LABELS[pair.level]}"
    return roles


def _pair(pair: PairResult) -> dict:
    a, b, c = pair.a.elements, pair.b.elements, pair.comparison
    return {
        "a": pair.a.ref,
        "b": pair.b.ref,
        "relation": c.relation,
        "relation_label": compare.LABELS[c.relation],
        "blocks": [" ".join(e.text for e in a[blk.a_start : blk.a_start + blk.length]) for blk in c.blocks],
        "common": [
            {"a": a[p.a_index].text, "b": b[p.b_index].text, "level": compare.LEVEL_LABELS[p.level]} for p in c.pairs
        ],
        "extra_a": [a[i].text for i in c.extra_a],
        "extra_b": [b[i].text for i in c.extra_b],
        "same_order": c.same_order,
        "a_roles": _roles(len(a), c, "a"),
        "b_roles": _roles(len(b), c, "b"),
    }


def _ranked(pairs: list[PairResult]) -> list[PairResult]:
    order = list(compare.LABELS)
    return sorted(pairs, key=lambda pair: (order.index(pair.comparison.relation), -pair.comparison.common))


def _variant(variant) -> dict:
    return {
        "riwaya": variant.riwaya,
        "ref": variant.ref,
        "kind": variant.kind,
        "base_text": variant.base_text,
        "variant_text": variant.variant_text,
    }


def fiche_to_dict(fiche: Fiche, max_pairs: int = 200) -> dict:
    statistics = fiche.statistics
    segment_order = {use.ref: number for number, use in enumerate(fiche.uses)}
    companions = []
    for c in fiche.companions:
        stats = None
        if c.stats and statistics:
            stats = {
                "n_y": c.stats.n_y,
                "pmi": round(c.stats.pmi, 3),
                "log_likelihood": round(c.stats.log_likelihood, 2),
                "controls": {
                    name: {"expected": round(k.expected, 3), "p": round(k.p_value, 4), "q": round(k.q_value, 4)}
                    for name, k in c.stats.controls.items()
                },
                "reading": c.stats.reading(statistics["alpha"], statistics["min_cooccurrence"]),
            }
        companions.append(
            {
                "kind": c.kind,
                "form": c.form,
                "lemma": c.lemma,
                "root": c.root,
                "nature": c.nature,
                "occurrences": len(c.refs),
                "segments": len(c.segments),
                "before": c.before,
                "after": c.after,
                "refs": c.refs,
                "segment_refs": sorted(c.segments, key=segment_order.__getitem__),
                "stats": stats,
            }
        )

    block = fiche.readings
    readings = None
    if block:
        touched = []
        for c in fiche.companions:
            per_riwaya = block.touched.get(c.key)
            if per_riwaya:
                touched.append(
                    {
                        "form": c.form,
                        "lemma": c.lemma,
                        "segments": len(c.segments),
                        "unchanged": len(block.riwayat) - len(per_riwaya),
                        "per_riwaya": per_riwaya,
                    }
                )
        readings = {
            "riwayat": list(block.riwayat),
            "on_reference": [_variant(v) for v in block.on_reference],
            "in_segments": [_variant(v) for v in block.in_segments],
            "touched": touched,
            "companions_unchanged": len(fiche.companions) - len(block.touched),
        }

    relations = Counter(pair.comparison.relation for pair in fiche.pairs)
    return {
        "form": fiche.form,
        "lemma": fiche.lemma,
        "root": fiche.root,
        "parameters": fiche.parameters,
        "occurrences": fiche.occurrences,
        "ayas": len({ref.rsplit(":", 1)[0] for ref in fiche.occurrences}),
        "writings": fiche.writings.most_common(),
        "positions": dict(Counter(use.position for use in fiche.uses)),
        "segments": [
            {
                "ref": use.ref,
                "position": use.position,
                "words": [
                    {"ref": e.ref, "text": e.text, "reference": i in use.ref_indexes} for i, e in enumerate(use.elements)
                ],
            }
            for use in fiche.uses
        ],
        "companions": companions,
        "attached": [
            {"form": form, "tag": tag, "refs": refs}
            for (form, tag), refs in sorted(fiche.attached.items(), key=lambda item: -len(item[1]))
        ],
        "pairs": {
            "total": len(fiche.pairs),
            "skipped": fiche.pairs_skipped,
            "counts": [{"relation": r, "label": compare.LABELS[r], "count": relations[r]} for r in compare.LABELS if relations[r]],
            "rows": [_pair(pair) for pair in _ranked(fiche.pairs)[:max_pairs]],
        },
        "groups": [
            {
                "members": [use.ref for use in group.members],
                "shared_block": group.shared_block,
                "shared_in": group.shared_in,
                "pairs": group.pairs,
            }
            for group in fiche.groups
        ],
        "statistics": statistics,
        "readings": readings,
    }


def companions_to_dict(first: Fiche, second: Fiche) -> dict:
    rows = compare_companions(first, second)
    counts = Counter(row.category for row in rows)
    return {
        "parameters": first.parameters,
        "first": {"form": first.form, "lemma": first.lemma, "occurrences": len(first.occurrences), "segments": len(first.uses), "companions": len(first.companions)},
        "second": {"form": second.form, "lemma": second.lemma, "occurrences": len(second.occurrences), "segments": len(second.uses), "companions": len(second.companions)},
        "counts": dict(counts),
        "shared": counts[SAME_FORM],
        "rows": [
            {
                "category": row.category,
                "side": row.side,
                "form": row.form,
                "lemma": row.lemma,
                "root": row.root,
                "segments_first": row.segments[0],
                "segments_second": row.segments[1],
                "other_forms": list(row.other_forms),
            }
            for row in rows
        ],
    }


# --- CSV ----------------------------------------------------------------------


def _csv(header: list[str], rows: list[list], parameters: dict[str, str]) -> str:
    """CSV text with a byte order mark, so that spreadsheet programs read the Arabic correctly."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(header + list(parameters))
    for row in rows:
        writer.writerow(list(row) + list(parameters.values()))
    return "﻿" + buffer.getvalue()


def fiche_to_csv(fiche: Fiche, table: str) -> str:
    identity = [fiche.form, fiche.lemma, fiche.root]
    if table == "segments":
        header = ["forme", "lemme", "racine", "segment", "position", "mots", "texte", "mots de la forme"]
        rows = [
            identity
            + [
                use.ref,
                use.position,
                len(use.elements),
                " ".join(e.text for e in use.elements),
                " ".join(use.elements[i].ref for i in use.ref_indexes),
            ]
            for use in fiche.uses
        ]
    elif table == "compagnons":
        controls = list(fiche.statistics["controls"]) if fiche.statistics else []
        header = ["forme", "lemme", "racine", "famille", "compagnon", "lemme du compagnon", "racine du compagnon"]
        header += ["nature", "occurrences", "segments", "avant", "après"]
        if fiche.statistics:
            header += ["segments du mot dans le texte", "PMI", "G2"]
            for control in controls:
                header += [f"attendu ({control})", f"p ({control})", f"p corrigée ({control})"]
            header += ["lecture du contrôle"]
        header += ["références"]
        rows = []
        for c in fiche.companions:
            row = identity + [c.kind, c.form, c.lemma, c.root, c.nature, len(c.refs), len(c.segments), c.before, c.after]
            if fiche.statistics:
                s = c.stats
                row += [s.n_y, round(s.pmi, 3), round(s.log_likelihood, 2)]
                for control in controls:
                    k = s.controls[control]
                    row += [round(k.expected, 3), round(k.p_value, 4), round(k.q_value, 4)]
                row += [s.reading(fiche.statistics["alpha"], fiche.statistics["min_cooccurrence"])]
            rows.append(row + [" ".join(c.refs)])
    elif table == "paires":
        header = ["forme", "lemme", "racine", "segment A", "segment B", "relation", "blocs identiques"]
        header += ["éléments communs hors blocs", "en plus dans A", "en plus dans B", "ordre"]
        rows = []
        for pair in _ranked(fiche.pairs):
            p = _pair(pair)
            rows.append(
                identity
                + [
                    p["a"],
                    p["b"],
                    p["relation_label"],
                    " | ".join(p["blocks"]),
                    " ; ".join(f"{c['a']} ~ {c['b']} ({c['level']})" for c in p["common"]),
                    " ".join(p["extra_a"]),
                    " ".join(p["extra_b"]),
                    "même ordre" if p["same_order"] else "ordre différent",
                ]
            )
    elif table == "lectures":
        header = ["forme", "lemme", "racine", "riwaya", "mot", "nature", "texte de base", "texte de la riwaya", "sur la forme"]
        on_reference = set(fiche.readings.on_reference) if fiche.readings else set()
        rows = [
            identity + [v.riwaya, v.ref, v.kind, v.base_text, v.variant_text, "oui" if v in on_reference else "non"]
            for v in (fiche.readings.in_segments if fiche.readings else ())
        ]
    else:
        raise ValueError(f"table inconnue : {table!r} (attendu : {', '.join(CSV_TABLES)})")
    return _csv(header, rows, fiche.parameters)


def companions_to_csv(first: Fiche, second: Fiche) -> str:
    header = ["catégorie", "chez", "compagnon", "lemme", "racine"]
    header += [f"segments avec {first.form}", f"segments avec {second.form}", "formes de la même racine chez l'autre"]
    rows = [
        [row.category, row.side, row.form, row.lemma, row.root, row.segments[0], row.segments[1], " ".join(row.other_forms)]
        for row in compare_companions(first, second)
    ]
    return _csv(header, rows, first.parameters)
