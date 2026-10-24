"""Visual analyses (charts) of a study, as one self-contained HTML page per question.

Rule of the author (2026-10-21): every experiment comes with a visual analysis, to see the
patterns instead of only reading tables. Charts are drawn as inline SVG: the browser shapes
the Arabic labels correctly, and the page works offline. Descriptive only (CLAUDE.md rule 5).

    forms_pairs_page   the table « مقارنة الصيغ مثنى مثنى » of a study, seen three ways:
                       a heatmap forms × forms, a scatter of case أ against case ب, and how
                       connected each form is to the others
"""

from __future__ import annotations

import html
from pathlib import Path

import numpy as np
import pandas as pd

BLUE = ["#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec", "#5598e7", "#3987e5", "#2a78d6", "#256abf",
        "#1c5cab", "#184f95", "#104281", "#0d366b"]  # fmt: skip

STYLE = """
:root { --surface:#fcfcfb; --plane:#f9f9f7; --ink:#0b0b0b; --ink2:#52514e; --muted:#898781; --grid:#e1e0d9;
        --axis:#c3c2b7; --mark:#2a78d6; --ring:rgba(11,11,11,0.10); }
@media (prefers-color-scheme: dark) {
  :root { --surface:#1a1a19; --plane:#0d0d0d; --ink:#f0efec; --ink2:#c3c2b7; --muted:#898781; --grid:#2c2c2a;
          --axis:#383835; --mark:#3987e5; --ring:rgba(255,255,255,0.10); }
}
* { box-sizing: border-box; }
body { margin:0; background:var(--plane); color:var(--ink);
       font:16px/1.6 "Amiri","Scheherazade New","Traditional Arabic","Segoe UI",Tahoma,sans-serif; }
main { max-width:1180px; margin:0 auto; padding:16px; }
h1 { font-size:24px; margin:8px 0 2px; } h2 { font-size:20px; margin:0 0 4px; }
.sub { color:var(--ink2); margin:0 0 14px; }
section { background:var(--surface); border:1px solid var(--ring); border-radius:10px; padding:16px; margin:16px 0; }
.read { color:var(--ink2); font-size:15px; margin:6px 0 0; }
.scroll { overflow-x:auto; }
svg text { fill:var(--ink2); font-family:inherit; }
svg .muted { fill:var(--muted); font-size:12px; }
svg .grid { stroke:var(--grid); stroke-width:1; }
svg .axis { stroke:var(--axis); stroke-width:1; }
svg .cell:hover, svg .dot:hover, svg .bar:hover { stroke:var(--ink); stroke-width:1.5; }
svg .dot { fill:var(--mark); stroke:var(--surface); stroke-width:2; }
svg .bar { fill:var(--mark); }
.legend { display:flex; align-items:center; gap:8px; color:var(--ink2); font-size:14px; margin-top:8px; }
.ramp { display:flex; } .ramp span { width:22px; height:12px; }
table { border-collapse:collapse; font-size:14px; } th, td { padding:3px 8px; border-bottom:1px solid var(--grid); text-align:right; }
details { margin-top:10px; color:var(--ink2); }
"""


def _ramp(value: float) -> str:
    return BLUE[min(len(BLUE) - 1, int(value * (len(BLUE) - 1) + 0.5))] if value == value else "transparent"


def _order(matrix: np.ndarray) -> list[int]:
    """Spectral ordering: forms that cross with the same others end up side by side."""
    m = np.nan_to_num(matrix)
    laplacian = np.diag(m.sum(axis=1)) - m
    values, vectors = np.linalg.eigh(laplacian)
    fiedler = vectors[:, 1] if len(values) > 1 else np.zeros(len(m))
    return list(np.argsort(fiedler))


def forms_pairs_page(study: Path, min_occurrences: int = 3) -> Path:
    """Charts of `paires_formes.csv` for forms with at least `min_occurrences` occurrences."""
    pairs = pd.read_csv(study / "paires_formes.csv", encoding="utf-8-sig")
    profiles = pd.read_csv(study / "profils.csv", encoding="utf-8-sig")
    occurrences = dict(zip(profiles["form"], profiles["occurrences"]))
    kept = [f for f in profiles["form"] if occurrences[f] >= min_occurrences]
    pairs = pairs[pairs["form_a"].isin(kept) & pairs["form_b"].isin(kept)].copy()
    pairs["crossing"] = (pairs["pairs"] - pairs["case_c"]) / pairs["pairs"]
    pairs["share_a"] = pairs["case_a"] / pairs["pairs"]
    pairs["share_b"] = pairs["case_b"] / pairs["pairs"]

    index = {f: k for k, f in enumerate(kept)}
    matrix = np.full((len(kept), len(kept)), np.nan)
    for row in pairs.itertuples():
        matrix[index[row.form_a], index[row.form_b]] = matrix[index[row.form_b], index[row.form_a]] = row.crossing
    order = _order(matrix)
    ordered = [kept[k] for k in order]
    detail = {(r.form_a, r.form_b): r for r in pairs.itertuples()} | {(r.form_b, r.form_a): r for r in pairs.itertuples()}

    root = study.parent.name
    parts = [f"<!doctype html><html lang='ar' dir='rtl'><head><meta charset='utf-8'>"
             f"<meta name='viewport' content='width=device-width, initial-scale=1'><title>Coran++ — مقارنة الصيغ مثنى مثنى — {root}</title>"
             f"<style>{STYLE}</style></head><body><main>",
             f"<h1>مقارنة الصيغ مثنى مثنى — جذر {html.escape(root)}</h1>",
             f"<p class='sub'>الصيغ ذات {min_occurrences} ورود فأكثر ({len(kept)} صيغة). المصدر : paires_formes.csv ({study.name}). "
             "وصف فقط، دون تأويل ؛ لا مقارنة بالصدفة بعد.</p>"]  # fmt: skip

    # 1. Heatmap
    cell, label = 34, 120
    size = label + cell * len(ordered)
    svg = [f"<svg width='{size + 10}' height='{size + 10}' role='img' aria-label='heatmap' style='direction:ltr'>"]
    for k, form in enumerate(ordered):
        x = label + k * cell + cell / 2
        svg.append(f"<text x='{x}' y='{label - 6}' text-anchor='start' transform='rotate(-50 {x} {label - 6})' font-size='14'>{html.escape(form)}</text>")
        svg.append(f"<text x='{label - 6}' y='{label + k * cell + cell / 2 + 5}' text-anchor='end' font-size='14'>{html.escape(form)}</text>")
    for i, fi in enumerate(ordered):
        for j, fj in enumerate(ordered):
            x, y = label + j * cell, label + i * cell
            if i == j:
                svg.append(f"<rect x='{x + 1}' y='{y + 1}' width='{cell - 2}' height='{cell - 2}' rx='3' fill='var(--grid)'/>")
                continue
            r = detail.get((fi, fj))
            if r is None:
                continue
            tip = (f"{fi} × {fj}\nمقارنات المقاطع : {r.pairs}\nتتقاطع (أ أو ب) : {r.pairs - r.case_c} ({r.crossing:.0%})"
                   f"\nأ نفس الصيغة : {r.case_a} ؛ ب نفس الجذر : {r.case_b} ؛ ج : {r.case_c}")  # fmt: skip
            svg.append(f"<rect class='cell' x='{x + 1}' y='{y + 1}' width='{cell - 2}' height='{cell - 2}' rx='3' "
                       f"fill='{_ramp(r.crossing)}'><title>{html.escape(tip)}</title></rect>")  # fmt: skip
    svg.append("</svg>")
    ramp = "".join(f"<span style='background:{c}'></span>" for c in BLUE)
    parts.append("<section><h2>1. خريطة التقاطع : أي الصيغ تتقاسم السياقات ؟</h2>"
                 "<p class='sub'>كل خانة : نسبة مقارنات المقاطع التي تتقاطع (أ أو ب) بين الصيغتين. الترتيب يقرب الصيغ المتشابهة في تقاطعاتها.</p>"
                 f"<div class='scroll' dir='ltr'>{''.join(svg)}</div>"
                 f"<div class='legend'>0%<div class='ramp'>{ramp}</div>100%</div>"
                 "<p class='read'>القراءة : الكتل الداكنة على القطر مجموعات صيغ تتقاسم كلماتها المحيطة ؛ الصفوف الفاتحة صيغ معزولة عن غيرها. "
                 "مرر الفأرة على خانة لرؤية الأعداد.</p></section>")  # fmt: skip

    # 2. Scatter: share أ against share ب
    w, h, pad = 640, 440, 56
    top = max(0.05, float(max(pairs["share_a"].max(), pairs["share_b"].max())) * 1.1)
    def sx(v): return pad + v / top * (w - 2 * pad)  # noqa: E704
    def sy(v): return h - pad - v / top * (h - 2 * pad)  # noqa: E704
    svg = [f"<svg width='{w}' height='{h}' role='img' aria-label='scatter' style='direction:ltr'>"]
    for t in np.linspace(0, top, 5):
        svg.append(f"<line class='grid' x1='{pad}' x2='{w - pad}' y1='{sy(t)}' y2='{sy(t)}'/>")
        svg.append(f"<text class='muted' x='{pad - 8}' y='{sy(t) + 4}' text-anchor='end'>{t:.0%}</text>")
        svg.append(f"<text class='muted' x='{sx(t)}' y='{h - pad + 18}' text-anchor='middle'>{t:.0%}</text>")
    svg.append(f"<line class='axis' x1='{sx(0)}' y1='{sy(0)}' x2='{sx(top)}' y2='{sy(top)}' stroke-dasharray='4 4'/>")
    labelled = set(pairs.nlargest(6, "crossing").index)
    for idx, r in pairs.iterrows():
        tip = f"{r.form_a} × {r.form_b}\nأ : {r.share_a:.0%} ؛ ب : {r.share_b:.0%} ؛ مقارنات : {r.pairs}"
        svg.append(f"<circle class='dot' cx='{sx(r.share_a):.1f}' cy='{sy(r.share_b):.1f}' r='5'><title>{html.escape(tip)}</title></circle>")
        if idx in labelled:
            svg.append(f"<text x='{sx(r.share_a) + 8:.1f}' y='{sy(r.share_b) - 6:.1f}' font-size='13'>{html.escape(r.form_a)} / {html.escape(r.form_b)}</text>")
    svg.append(f"<text x='{w / 2}' y='{h - 12}' text-anchor='middle'>أ : نفس الصيغة في المقطعين</text>")
    svg.append(f"<text x='16' y='{h / 2}' text-anchor='middle' transform='rotate(-90 16 {h / 2})'>ب : نفس الجذر بصيغتين</text>")
    svg.append("</svg>")
    parts.append("<section><h2>2. نوع التقاطع : نفس الصيغة (أ) أم نفس الجذر (ب) ؟</h2>"
                 "<p class='sub'>كل نقطة زوج صيغ. فوق الخط المنقط : يغلب التقاطع بصيغتين مختلفتين من جذر واحد ؛ تحته : يغلب تكرار الصيغة نفسها.</p>"
                 f"<div class='scroll' dir='ltr'>{''.join(svg)}</div>"
                 "<p class='read'>القراءة : الأزواج البعيدة فوق الخط تشبه حالة « عالم الغيب / علام الغيوب » ؛ القريبة من الأصل لا تتقاطع إلا قليلا.</p></section>")  # fmt: skip

    # 3. Connectedness of each form
    mean = np.nanmean(matrix, axis=1)
    ranking = sorted(zip(kept, mean), key=lambda x: -x[1])
    bh, bw, lab = 26, 520, 130
    svg = [f"<svg width='{lab + bw + 70}' height='{bh * len(ranking) + 20}' role='img' aria-label='bars'>"]
    for k, (form, value) in enumerate(ranking):
        y = 10 + k * bh
        length = max(2, value * bw)
        svg.append(f"<text x='{lab + bw + 64}' y='{y + 17}' text-anchor='end' font-size='14'>{html.escape(form)}</text>")
        svg.append(f"<rect class='bar' x='{lab + bw - length}' y='{y + 4}' width='{length:.1f}' height='{bh - 10}' rx='4'>"
                   f"<title>{html.escape(form)} : {value:.0%} ({occurrences[form]} ورود)</title></rect>")  # fmt: skip
        svg.append(f"<text class='muted' x='{lab + bw - length - 6:.1f}' y='{y + 17}' text-anchor='end'>{value:.0%}</text>")
    svg.append("</svg>")
    parts.append("<section><h2>3. ارتباط كل صيغة بأخواتها</h2>"
                 "<p class='sub'>متوسط نسبة التقاطع بين الصيغة وكل الصيغ الأخرى.</p>"
                 f"<div class='scroll' dir='ltr'>{''.join(svg)}</div>"
                 "<p class='read'>القراءة : أعلى القائمة صيغ تشارك أخواتها سياقاتها ؛ أسفلها صيغ لها سياقات خاصة بها.</p>"
                 "<details><summary>تنبيه منهجي</summary>المقاطع الطويلة تتقاطع أكثر بطبيعتها (فيها كلمات أكثر). هذه النسب لم تقارن بعد "
                 "بما يعطيه خلط المقاطع بين الصيغ بالصدفة ؛ هي ملاحظات (الحالة : ملاحظ).</details></section>")  # fmt: skip

    parts += structure_sections(kept, matrix, occurrences)

    # Table view
    rows = "".join(f"<tr><td>{html.escape(r.form_a)}</td><td>{html.escape(r.form_b)}</td><td>{r.pairs}</td><td>{r.case_a}</td>"
                   f"<td>{r.case_b}</td><td>{r.case_c}</td><td>{r.crossing:.0%}</td></tr>"
                   for r in pairs.sort_values("crossing", ascending=False).itertuples())  # fmt: skip
    parts.append(f"<section><details><summary>الجدول</summary><table><tr><th>الصيغة 1</th><th>الصيغة 2</th><th>مقارنات</th>"
                 f"<th>أ</th><th>ب</th><th>ج</th><th>تقاطع</th></tr>{rows}</table></details></section></main></body></html>")  # fmt: skip
    out = study / "visuel_paires_formes.html"
    out.write_text("".join(parts), encoding="utf-8")
    return out


# --- Structure of the forms × forms table: non-statistical readings ----------------------------
# Topology (groups across every threshold), graph theory (skeleton, bridges), geometry (a map).

CATEGORICAL = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]


def _edges(similarity: np.ndarray) -> list[tuple[float, int, int]]:
    n = len(similarity)
    found = [(float(similarity[i, j]), i, j) for i in range(n) for j in range(i + 1, n) if similarity[i, j] == similarity[i, j]]
    return sorted(found, reverse=True)


def single_linkage(similarity: np.ndarray) -> list[tuple[int, int, float, int]]:
    """Merges (cluster a, cluster b, level, new cluster), strongest link first.

    Single linkage is the 0-dimensional persistent homology of the threshold graph: at level s,
    two forms are in one group when a chain of crossings >= s joins them.
    """
    n = len(similarity)
    parent = list(range(n))
    cluster_of = list(range(n))
    merges, next_id = [], n

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for s, i, j in _edges(similarity):
        a, b = find(i), find(j)
        if a != b:
            merges.append((cluster_of[a], cluster_of[b], s, next_id))
            parent[b] = a
            cluster_of[a] = next_id
            next_id += 1
    return merges


def maximum_spanning_tree(similarity: np.ndarray) -> list[tuple[int, int, float]]:
    parent = list(range(len(similarity)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    tree = []
    for s, i, j in _edges(similarity):
        a, b = find(i), find(j)
        if a != b:
            parent[b] = a
            tree.append((i, j, s))
    return tree


def articulation_points(adjacency: list[set[int]]) -> set[int]:
    """Vertices whose removal disconnects the graph (Tarjan)."""
    n, counter = len(adjacency), [0]
    order, low, found = [-1] * n, [0] * n, set()

    def visit(u, parent):
        order[u] = low[u] = counter[0]
        counter[0] += 1
        children = 0
        for v in adjacency[u]:
            if order[v] == -1:
                children += 1
                visit(v, u)
                low[u] = min(low[u], low[v])
                if parent != -1 and low[v] >= order[u]:
                    found.add(u)
            elif v != parent:
                low[u] = min(low[u], order[v])
        if parent == -1 and children > 1:
            found.add(u)

    for u in range(n):
        if order[u] == -1:
            visit(u, -1)
    return found


def classical_mds(distance: np.ndarray) -> tuple[np.ndarray, list[float]]:
    """Coordinates in 2 dimensions, and the share of structure each axis carries (positive eigenvalues)."""
    n = len(distance)
    j = np.eye(n) - np.ones((n, n)) / n
    b = -0.5 * j @ (distance**2) @ j
    values, vectors = np.linalg.eigh(b)
    order = np.argsort(values)[::-1]
    values, vectors = values[order], vectors[:, order]
    positive = values[values > 1e-12]
    shares = (positive / positive.sum()).tolist() if len(positive) else []
    coords = vectors[:, :2] * np.sqrt(np.maximum(values[:2], 0))
    return coords, shares


def structure_sections(forms: list[str], similarity: np.ndarray, occurrences: dict) -> list[str]:
    n = len(forms)
    if n < 3:
        return []
    sim = similarity.copy()
    np.fill_diagonal(sim, np.nan)
    merges = single_linkage(sim)
    if not merges:
        return []
    members = {k: [k] for k in range(n)}
    level = {k: 1.0 for k in range(n)}
    absorbed: dict[int, float] = {}
    for a, b, s, new in merges:
        members[new] = members[a] + members[b]
        level[new] = s
        absorbed[a] = absorbed[b] = s
    root = merges[-1][3]

    # Groups: cut at the largest gap between consecutive merge levels (the most persistent split).
    levels = [m[2] for m in merges]
    gaps = [(levels[k] - levels[k + 1], k) for k in range(len(levels) - 1)]
    cut = levels[max(gaps)[1]] if gaps else 0.0
    group_of = {}
    for k in range(n):
        node = k
        for a, b, s, new in merges:
            if node in (a, b) and s >= cut:
                node = new
        group_of[k] = node
    groups = list(dict.fromkeys(group_of[k] for k in range(n)))
    colour = {g: CATEGORICAL[i % len(CATEGORICAL)] for i, g in enumerate(sorted(groups, key=lambda g: -len(members[g])))}

    # Persistent groups: formed at level h, absorbed at level h'; persistence h - h'.
    persistent = sorted(
        ((level[node] - absorbed.get(node, 0.0), node) for node in members if len(members[node]) >= 2 and node != root),
        reverse=True,
    )[:4]

    # 4. Dendrogram
    leaf_order: list[int] = []
    children = {new: (a, b) for a, b, s, new in merges}

    def walk(node):
        if node < n:
            leaf_order.append(node)
        else:
            walk(children[node][0])
            walk(children[node][1])

    walk(root)
    row, width, label = 30, 560, 130
    y_of = {leaf: 14 + k * row for k, leaf in enumerate(leaf_order)}
    lo = min(levels)

    def x(s):  # 1.0 (the leaves) on the right, the weakest merge on the left
        return 20 + (s - lo) / max(1e-9, 1.0 - lo) * (width - 40)

    svg = [f"<svg width='{width + label}' height='{row * n + 40}' role='img' aria-label='dendrogram'>"]
    for t in np.linspace(lo, 1.0, 5):
        svg.append(f"<line class='grid' x1='{x(t):.1f}' x2='{x(t):.1f}' y1='6' y2='{row * n + 6}'/>")
        svg.append(f"<text class='muted' x='{x(t):.1f}' y='{row * n + 24}' text-anchor='middle'>{t:.0%}</text>")
    pos = {leaf: (x(1.0), y_of[leaf]) for leaf in range(n)}
    for a, b, s, new in merges:
        (xa, ya), (xb, yb) = pos[a], pos[b]
        xn = x(s)
        stroke = colour[group_of[members[new][0]]] if s >= cut else "var(--muted)"
        names = html.escape("، ".join(forms[k] for k in members[new]))
        svg.append(f"<path d='M{xa:.1f},{ya:.1f} H{xn:.1f} V{yb:.1f} H{xb:.1f}' fill='none' stroke='{stroke}' "
                   f"stroke-width='2'><title>{names} : {s:.0%}</title></path>")  # fmt: skip
        pos[new] = (xn, (ya + yb) / 2)
    for leaf in range(n):
        svg.append(f"<text x='{x(1.0) + 8:.1f}' y='{y_of[leaf] + 5}' font-size='14' text-anchor='start' "
                   f"style='fill:{colour[group_of[leaf]]}'>{html.escape(forms[leaf])}</text>")  # fmt: skip
    svg.append(f"<line class='axis' x1='{x(cut):.1f}' x2='{x(cut):.1f}' y1='6' y2='{row * n + 6}' stroke-dasharray='4 4'/></svg>")
    robust = "".join(
        f"<li>{html.escape('، '.join(sorted(forms[k] for k in members[node])))} : تتكون عند {level[node]:.0%} "
        f"وتبقى منفصلة حتى {absorbed.get(node, 0):.0%} (المدى {p:.0%})</li>"
        for p, node in persistent
    )
    out = [
        "<section><h2>4. المجموعات عبر كل العتبات (طوبولوجيا : الاستمرار)</h2>"
        "<p class='sub'>بدل اختيار عتبة واحدة : كلما نزلت عتبة التقاطع (من اليمين إلى اليسار) اندمجت الصيغ في مجموعات. "
        "المجموعة التي تبقى منفصلة على مدى واسع متينة لا تتعلق باختيار العتبة. الخط المنقط : أوسع فجوة، وعندها تلون المجموعات.</p>"
        f"<div class='scroll' dir='ltr'>{''.join(svg)}</div>"
        f"<p class='read'>أمتن المجموعات :</p><ul class='read'>{robust}</ul></section>"
    ]

    # 5. Map (classical MDS) with the skeleton (maximum spanning tree) and the bridges
    distance = 1.0 - np.nan_to_num(similarity, nan=0.0)
    np.fill_diagonal(distance, 0.0)
    coords, shares = classical_mds(distance)
    tree = maximum_spanning_tree(sim)
    bottleneck = min(s for *_, s in tree)
    adjacency = [{j for j in range(n) if j != i and sim[i, j] == sim[i, j] and sim[i, j] >= bottleneck} for i in range(n)]
    bridges = articulation_points(adjacency)
    w, h, pad = 680, 520, 60
    span = np.ptp(coords, axis=0)
    span[span == 0] = 1
    low = coords.min(axis=0)

    def px(i):
        return pad + (coords[i, 0] - low[0]) / span[0] * (w - 2 * pad)

    def py(i):
        return pad + (coords[i, 1] - low[1]) / span[1] * (h - 2 * pad)

    svg = [f"<svg width='{w}' height='{h}' role='img' aria-label='map'>"]
    for i, j, s in tree:
        svg.append(f"<line x1='{px(i):.1f}' y1='{py(i):.1f}' x2='{px(j):.1f}' y2='{py(j):.1f}' stroke='var(--axis)' "
                   f"stroke-width='{1 + 5 * s:.1f}'><title>{html.escape(forms[i])} — {html.escape(forms[j])} : {s:.0%}</title></line>")  # fmt: skip
    for i in range(n):
        r = 5 + 2.2 * np.sqrt(occurrences.get(forms[i], 1))
        ring = " stroke='var(--ink)' stroke-width='3'" if i in bridges else " stroke='var(--surface)' stroke-width='2'"
        svg.append(f"<circle cx='{px(i):.1f}' cy='{py(i):.1f}' r='{r:.1f}' fill='{colour[group_of[i]]}'{ring}>"
                   f"<title>{html.escape(forms[i])} ({occurrences.get(forms[i], '?')} ورود)</title></circle>")  # fmt: skip
        svg.append(f"<text x='{px(i):.1f}' y='{py(i) - r - 6:.1f}' text-anchor='middle' font-size='14'>"
                   f"{html.escape(forms[i])}{' ◆' if i in bridges else ''}</text>")  # fmt: skip
    svg.append("</svg>")
    axes = "، ".join(f"المحور {k + 1} : {v:.0%}" for k, v in enumerate(shares[:4]))
    bridge_text = "، ".join(forms[i] for i in sorted(bridges)) or "لا شيء"
    out.append(
        "<section><h2>5. خريطة الصيغ وهيكل الروابط (هندسة ونظرية البيان)</h2>"
        "<p class='sub'>الصيغ المتقاربة في الجدول متقاربة على الخريطة (إسقاط في بعدين). الخطوط : الهيكل، أي أقوى الروابط التي تصل كل الصيغ "
        "دون حلقة (كلما غلظ الخط قوي التقاطع). حجم الدائرة : عدد الورود. اللون : المجموعات المستخرجة أعلاه.</p>"
        f"<div class='scroll' dir='ltr'>{''.join(svg)}</div>"
        f"<p class='read'>الجسور (◆) : صيغ إذا حذفت انفصلت الصيغ الأخرى إلى مجموعات لا يصل بينها رابط عند عتبة {bottleneck:.0%} : "
        f"<strong>{html.escape(bridge_text)}</strong>.</p>"
        f"<p class='read'>أبعاد البنية (نصيب كل محور) : {axes}. محور أول كبير يعني أن تقسيما واحدا يغلب على الجذر.</p>"
        "<details><summary>تنبيه</summary>قراءات بنيوية للجدول نفسه، لا اختبارات إحصائية : تصف شكل الروابط، ولا تقول إنها أكثر من "
        "الصدفة.</details></section>"
    )
    return out
