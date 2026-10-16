"""Labels shown to the user. The interface is in Arabic (decision of the author, 2026-10-16).

Terms come from docs/GLOSSAIRE_INTERFACE.md; a term is corrected here, never in the
modules that compute. Short codes (E0–E4, O1–O5, R1–R3) are kept beside the labels,
and figures are written with Western digits.
"""

from __future__ import annotations

LABELS = {
    # Reading, settings, provenance
    "reading": "الرواية",
    "hafs": "حفص",
    "code": "نسخة البرنامج",
    "scheme": "التقطيع",
    "aya": "تقطيع بالآيات",
    "waqf-strict": "تقطيع صارم",
    "waqf-souple": "تقطيع مرن",
    "form_rule": "الصيغة كما كتبت، الواو منفصلة، دون الحركة الأخيرة",
    "categories": "التصنيف حسب تحليل المدونة (QAC)",
    # Method
    "form": "الصيغة",
    "forms": "الصيغ",
    "root": "الجذر",
    "reference_form": "الصيغة المرجعية",
    "segment": "المقطع",
    "segments": "المقاطع",
    "occurrences": "مرات الورود",
    "ayas": "آيات",
    "refs": "المواضع",
    "text": "النص",
    "none": "لا شيء",
    "total": "المجموع",
    # Root identity (level 0)
    "identity": "هوية الجذر",
    "verbs": "الأفعال",
    "nouns": "الأسماء",
    "verbs_count": "أفعال",
    "nouns_count": "أسماء",
    "wazn": "الوزن",
    "derivation": "وزن الاشتقاق",
    "kind": "النوع",
    "bab_line": "حركة عين الفعل في الوزن I (حسب الشكل)",
    "bab": "الباب",
    "absent": "غير مستعمل في القرآن",
    "absent_types": "أنواع تذكرها المدونة وغير مستعملة في القرآن",
    "unused_forms": "الصيغ الممكنة في العربية وغير المستعملة في القرآن (موثقة في المعاجم، نظرية)",
    "not_computed": "لم تحسب بعد، المصادر المعجمية لم تدمج (المرحلة F)",
    "ambiguous": "ملتبسة",
    "no_verb": "لا فعل من هذا الجذر في القرآن.",
    "no_noun": "لا اسم من هذا الجذر في القرآن.",
    # Typology (level 1)
    "R1 total": "تطابق كلي",
    "R1 partiel": "تطابق جزئي",
    "R2": "تشابه",
    "R3": "اختلاف",
    "E0": "نفس الصيغة",
    "E1": "نفس الأصل، بزيادة أو نقصان حرف أو ضمير",
    "E2": "نفس الأصل، بتغيير الضمير",
    "E3": "نفس الجذر، صيغة مختلفة",
    "E4": "جذر مختلف",
    "Ø": "غائب",
    "O1": "إضافة / حذف",
    "O2": "استبدال",
    "O3": "تقديم وتأخير",
    "O4": "فصل",
    "O5": "تغير موقع الصيغة المرجعية",
    "Ø dans A": "غائب في أ",
    "Ø dans B": "غائب في ب",
    "collés dans A": "متصلان في أ",
    "collés dans B": "متصلان في ب",
    "inverted": "زوج وحدات معكوس",
    "lettre changée": "تغيير الحرف",
    "pivot": "الصيغة المرجعية",
    "voisin": "متصلة",
    "éloigné": "منفصلة",
    "début": "في الأول",
    "milieu": "في الوسط",
    "fin": "في الأخير",
    "seul": "وحدها",
    "pair": "المقارنة الثنائية",
    "pairs": "المقارنات الثنائية",
    "types": "النوع",
    "blocks": "الأجزاء المتطابقة",
    "operations": "التغييرات",
    "order": "الترتيب",
    "inversions": "عدد الأزواج المعكوسة",
    "codes": "الرموز",
    "common_outside_pivot": "العناصر المشتركة غير الصيغة المرجعية",
    # Families and matrices (levels 2, 3)
    "families_title": "أنواع الاستعمال",
    "family": "نوع استعمال",
    "isolated": "استعمال منفرد",
    "cohesion": "التماسك",
    "cuts": "روابط مقطوعة",
    "rows": "الأسطر",
    "link_rule": "الرابط : تطابق أو تشابه، مع {n} عنصر مشترك على الأقل غير الصيغة المرجعية",
    "cohesion_min": "أدنى تماسك",
    "twins": "أزواج أسطر في مقطع واحد (تحسب مرة واحدة)",
    "matrix": "مصفوفة",
    "template": "القالب",
    "ambiguous_matrix": "مصفوفة غير محسومة",
    "centre": "السطر المركزي",
    "columns": "أعمدة",
    "differences": "فروق بين المقارنة الثنائية والمصفوفة",
    "moved": "خانات نقلت بسبب تقديم وتأخير",
    "fixe": "ثابت",
    "relativement fixe": "ثابت نسبيا",
    "variable": "متغير",
    "optional": "اختياري",
    "column_kind": "نوع العمود",
    # Messages
    "no_occurrence": "لا ورود لهذه الصيغة.",
    "no_root_form": "لا صيغة لهذا الجذر.",
    "no_root": "لا ورود لهذا الجذر.",
    "covers": "الكتابة دون شكل تشمل {n} صيغ، كل واحدة على حدة :",
    "retained": "{typed} تشمل عدة صيغ ؛ اختيرت : {form} ({n}) ؛ الصيغ الأخرى ({others}) تطلب بشكلها.",
    "not_in_span": "الصيغة {form} غير موجودة في المقطع : {text}",
    "written": "كتب في : {path}",
}


def t(key: str, **values) -> str:
    """The label of `key`; an unknown key is shown as it is, so that nothing is hidden."""
    text = LABELS.get(key, key)
    return text.format(**values) if values else text


def meta_line(meta: dict[str, str], *extra: str) -> str:
    """Reading and code version, the provenance line of every output (CLAUDE.md rule 6)."""
    parts = [f"{t('reading')} : {t(meta['reading'])}", *extra, f"{t('code')} {meta['code_version']}"]
    return " · ".join(parts)
