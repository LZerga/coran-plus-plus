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

    # Table view
    rows = "".join(f"<tr><td>{html.escape(r.form_a)}</td><td>{html.escape(r.form_b)}</td><td>{r.pairs}</td><td>{r.case_a}</td>"
                   f"<td>{r.case_b}</td><td>{r.case_c}</td><td>{r.crossing:.0%}</td></tr>"
                   for r in pairs.sort_values("crossing", ascending=False).itertuples())  # fmt: skip
    parts.append(f"<section><details><summary>الجدول</summary><table><tr><th>الصيغة 1</th><th>الصيغة 2</th><th>مقارنات</th>"
                 f"<th>أ</th><th>ب</th><th>ج</th><th>تقاطع</th></tr>{rows}</table></details></section></main></body></html>")  # fmt: skip
    out = study / "visuel_paires_formes.html"
    out.write_text("".join(parts), encoding="utf-8")
    return out
