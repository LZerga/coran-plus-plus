"""Step 3b, level 0: the identity of a root (هوية الجذر), Quran side (SPEC §2.0).

Two tables, verbs and nouns, hold every cell of the text that carries the root,
each in exactly one box. The categories of الصرف are used here and nowhere else
(DECISIONS.md, D-22). They come from the annotation of the corpus, not from a
comparison of letters. What the corpus does not say is not guessed: a noun the
corpus gives no type to goes to an « ambiguë » or « غير محدد » box (D-23).

Letters and pronouns attached to a form are ignored for the classification
(CHANGELOG v12): only the stem carrying the root is read.

The forms the language allows but the Quran does not use (attested, theoretical)
need a conjugator and the classical dictionaries: lot F, not built yet.
"""

from __future__ import annotations

import sqlite3
from collections import Counter
from dataclasses import dataclass, field

from . import alt_roots
from .index import search_key
from .labels import meta_line, t
from .normalize import LETTERS, TANWEEN_FATH, Level, drop_assimilation_shadda, normalize, split_final_vowel

# Verb forms as numbered by the corpus (corpus.quran.com/documentation/verbforms.jsp).
TRILITERAL_WAZN = {
    "I": "فَعَلَ", "II": "فَعَّلَ", "III": "فاعَلَ", "IV": "أَفْعَلَ", "V": "تَفَعَّلَ", "VI": "تَفاعَلَ",
    "VII": "انْفَعَلَ", "VIII": "افْتَعَلَ", "IX": "افْعَلَّ", "X": "اسْتَفْعَلَ", "XI": "افْعالَّ", "XII": "افْعَوْعَلَ",
}  # fmt: skip
QUADRILITERAL_WAZN = {"I": "فَعْلَلَ", "II": "تَفَعْلَلَ", "III": "افْعَنْلَلَ", "IV": "افْعَلَلَّ"}
VERB_COLUMNS = ("ماضٍ معلوم", "ماضٍ مجهول", "مضارع معلوم", "مضارع مجهول", "أمر")
TENSES = {"PERF": "ماضٍ", "IMPF": "مضارع", "IMPV": "أمر"}
PERSONS = {"1": "متكلم", "2": "مخاطب", "3": "غائب"}
GENDERS = {"M": "مذكر", "F": "مؤنث"}
NUMBERS = {"S": "مفرد", "D": "مثنى", "P": "جمع"}
MOODS = {"MOOD:SUBJ": "منصوب", "MOOD:JUS": "مجزوم"}  # the corpus leaves the indicative unmarked
CASES = {"NOM": "مرفوع", "ACC": "منصوب", "GEN": "مجرور"}
WEAK, HAMZA = frozenset("وي"), "ا"  # in the roots of the corpus, an alef stands for a hamza
RADICALS = "فعلل"
SHORT_VOWELS = {"َ": "فتحة", "ُ": "ضمة", "ِ": "كسرة"}

# Noun types the corpus states.
NOUN_TYPES = {"ACT": "اسم الفاعل", "PASS": "اسم المفعول", "VN": "مصدر"}
TAG_TYPES = {"PN": "اسم علم", "LOC": "ظرف مكان", "T": "ظرف زمان"}
UNSPECIFIED = "اسم — نوع غير محدد"
# Patterns the specification names as serving several types (SPEC §2.0, D-23). Nothing else is assumed.
AMBIGUOUS_PATTERNS = {
    "فَعِيل": ("صيغة مبالغة", "صفة مشبهة"),
    "مَفْعَل": ("مصدر ميمي", "اسم زمان", "اسم مكان"),
    "فَعَّال": ("صيغة مبالغة",),
    "مِفْعَال": ("صيغة مبالغة",),
    "فَعُول": ("صيغة مبالغة",),
    "فَعِل": ("صيغة مبالغة",),
}
UNDETERMINED = "غير محدد"


@dataclass
class Entry:
    """One form of the Quran in a box, with its traits."""

    form: str  # the cell as written (letters and pronouns attached), final vowel aside
    traits: str
    refs: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Identity:
    root: str
    letters: str  # ثلاثي | رباعي
    nature: str
    total: int
    verbs: dict[tuple[str, str], list[Entry]]  # (وزن, column) -> entries
    nouns: dict[tuple[str, str, str], list[Entry]]  # (type, derivation form, وزن) -> entries
    bab: dict[str, str]  # what the vowels say of the باب of form I
    absent_verbs: list[str]
    absent_nouns: list[str]

    @property
    def n_verbs(self) -> int:
        return sum(len(e.refs) for entries in self.verbs.values() for e in entries)

    @property
    def n_nouns(self) -> int:
        return sum(len(e.refs) for entries in self.nouns.values() for e in entries)


def nature_of(root: str) -> str:
    """صحيح (سالم، مهموز، مضعّف) or معتل (مثال، أجوف، ناقص، لفيف), read on the letters of the root."""
    weak = [i for i, letter in enumerate(root) if letter in WEAK]
    if len(root) == 3 and weak:
        names = {(0,): "مثال", (1,): "أجوف", (2,): "ناقص", (1, 2): "لفيف مقرون", (0, 2): "لفيف مفروق"}
        return "معتل — " + names.get(tuple(weak), "أكثر من حرف علة")
    if weak:
        return "معتل"
    kinds = [name for name, holds in (("مهموز", HAMZA in root), ("مضعّف", len(root) == 3 and root[1] == root[2])) if holds]
    return "صحيح — " + (" ، ".join(kinds) or "سالم")


def is_sound(root: str) -> bool:
    return nature_of(root) == "صحيح — سالم"


# Endings of number and of the tanween alef, set aside to read the وزن of the base (level 0 only).
_ENDINGS = ("ُون", "ِين", "َين", "َان", "َات", "َٰت")


def pattern_of(stem: str, root: str, noun: bool = False) -> str | None:
    """The وزن of a stem: its radicals replaced by ف ع ل. None unless the root is سالم and its letters are all found.

    For a noun, the endings of the sound plural and dual and the alef of the tanween
    are set aside, and the superscript alef is written as an alef, so that قَٰدِرُونَ
    and قَدِيرًا read فَاعِل and فَعِيل.
    """
    if not is_sound(root):
        return None
    text, removed = split_final_vowel(drop_assimilation_shadda(normalize(stem, Level.NO_RECITATION_MARKS)))
    if noun:
        if removed.startswith(TANWEEN_FATH) and text.endswith("ا"):
            text = text[:-1]
        text = next((text[: -len(e)] for e in _ENDINGS if text.endswith(e) and len(text) > len(e) + 2), text)
        text = text.replace("ٰ", "ا")
    out, radical = [], 0
    for ch in text:
        if radical < len(root) and ch == root[radical]:
            out.append(RADICALS[radical])
            radical += 1
        else:
            out.append(ch)
    return "".join(out).replace("ٱ", "ا") if radical == len(root) else None


def canonical(pattern: str) -> str:
    """The marks after each letter in one fixed order, so that two writings of a pattern compare equal."""
    out, marks = [], []
    for ch in pattern:
        if ch in LETTERS or ch in "فعل":
            out += sorted(marks)
            marks = []
            out.append(ch)
        else:
            marks.append(ch)
    return "".join(out + sorted(marks))


AMBIGUOUS_BY_CANON = {canonical(p): kinds for p, kinds in AMBIGUOUS_PATTERNS.items()}


def _vowel_of_second_radical(stem: str, root: str) -> str | None:
    pattern = pattern_of(stem, root)
    if pattern is None:
        return None
    after = pattern[pattern.index("ع") + 1 :]
    for ch in after:  # the first short vowel before the next letter; none (sukun, a letter) is not guessed
        if ch in SHORT_VOWELS:
            return SHORT_VOWELS[ch]
        if ch in LETTERS:
            return None
    return None


BAB_VOWELS = {"فتحة": "َ", "ضمة": "ُ", "كسرة": "ِ"}


def _bab(vowels: dict[str, Counter]) -> dict[str, str]:
    """What the vowels of the عين say of the باب of form I; the باب itself only when each tense shows one vowel."""
    seen = {tense: " / ".join(f"{v} ({n})" for v, n in counts.most_common()) for tense, counts in vowels.items() if counts}
    perfect, imperfect = vowels["ماضٍ"], vowels["مضارع"]
    if len(perfect) == 1 and len(imperfect) == 1 and UNDETERMINED not in perfect and UNDETERMINED not in imperfect:
        a, b = BAB_VOWELS[next(iter(perfect))], BAB_VOWELS[next(iter(imperfect))]
        seen["باب"] = f"فَع{a}لَ يَفْع{b}لُ"
    else:
        seen["باب"] = UNDETERMINED
    return seen


def _pgn(code: str) -> str:
    """3MS → غائب مفرد مذكر ; MP → جمع مذكر ; M → مذكر."""
    person = PERSONS.get(code[0]) if code[0] in PERSONS else None
    rest = code[1:] if person else code
    parts = [person, *(NUMBERS[ch] for ch in rest if ch in NUMBERS), *(GENDERS[ch] for ch in rest if ch in GENDERS)]
    return " ".join(part for part in parts if part)


def _is_pgn(feature: str) -> bool:
    return bool(feature) and all(ch in "123MFSDP" for ch in feature) and feature not in ("PASS",)


def identity(connection: sqlite3.Connection, root: str) -> Identity | None:
    root = alt_roots.fold_hamza(search_key(root))
    rows = connection.execute(
        """SELECT u.form, w.ref, s.tag, s.form, s.features,
                  EXISTS (SELECT 1 FROM word_segments p WHERE p.word_id = u.word_id AND p.features = 'PREFIX|Al+'),
                  EXISTS (SELECT 1 FROM word_segments p WHERE p.word_id = u.word_id AND p.kind = 'suffix' AND p.tag = 'PRON'
                          AND p.seg_no > s.seg_no),
                  EXISTS (SELECT 1 FROM word_segments p WHERE p.word_id = u.word_id AND p.tag = 'EMPH' AND p.kind = 'suffix')
           FROM units u JOIN word_segments s ON s.word_id = u.word_id
           JOIN words w ON w.id = u.word_id
           WHERE u.part != 1 AND u.aya > 0 AND s.kind = 'stem' AND s.root = ? ORDER BY u.id, s.seg_no""",
        (root,),
    ).fetchall()
    if not rows:
        return None
    wazn_names = TRILITERAL_WAZN if len(root) == 3 else QUADRILITERAL_WAZN
    verbs: dict[tuple[str, str], dict[tuple[str, str], Entry]] = {}
    nouns: dict[tuple[str, str, str], dict[tuple[str, str], Entry]] = {}
    bab_vowels: dict[str, Counter] = {"ماضٍ": Counter(), "مضارع": Counter()}

    for form, ref, tag, stem, feature_text, has_article, has_pronoun, has_emphasis in rows:
        features = feature_text.split("|")
        number = next((f.strip("()") for f in features if f.startswith("(")), "I")
        pgn = next((_pgn(f) for f in features if _is_pgn(f)), "")
        if tag == "V":
            tense = next(TENSES[f] for f in features if f in TENSES)
            passive = "PASS" in features
            column = tense if tense == "أمر" else f"{tense} {'مجهول' if passive else 'معلوم'}"
            wazn = wazn_names.get(number, f"({number})")
            traits = [pgn]
            if tense == "مضارع":
                traits.append(next((MOODS[f] for f in features if f in MOODS), "مرفوع"))
            if has_emphasis:
                traits.append("نون التوكيد")
            if number == "I" and not passive and tense in bab_vowels:
                bab_vowels[tense][_vowel_of_second_radical(stem, root) or UNDETERMINED] += 1
            box, key = verbs.setdefault((wazn, column), {}), (form, " ، ".join(t for t in traits if t))
        else:
            pattern = pattern_of(stem, root, noun=True) or UNDETERMINED
            kind = next((NOUN_TYPES[f] for f in features if f in NOUN_TYPES and (f == "VN" or "PCPL" in features)), None)
            kind = kind or TAG_TYPES.get(tag)
            if kind is None and canonical(pattern) in AMBIGUOUS_BY_CANON:
                kind = "ambiguë : " + " / ".join(AMBIGUOUS_BY_CANON[canonical(pattern)])
            if kind is None:
                kind = UNSPECIFIED if tag in ("N", "ADJ") else f"غير الاسم والفعل ({tag})"
            definite = "نكرة" if "INDEF" in features else "معرّف بأل" if has_article else "معرّف بالإضافة" if has_pronoun else ""
            case = next((CASES[f] for f in features if f in CASES), "")
            box, key = nouns.setdefault((kind, number, pattern), {}), (form, " ، ".join(t for t in (pgn, definite, case) if t))
        box.setdefault(key, Entry(*key)).refs.append(ref)

    def ordered(boxes: dict) -> dict:
        return {key: sorted(box.values(), key=lambda e: (-len(e.refs), e.form)) for key, box in boxes.items()}

    used_columns = {column for _, column in verbs}
    used_wazn = {wazn for wazn, _ in verbs}
    used_types = {kind for kind, _, _ in nouns}
    return Identity(
        root=root,
        letters={3: "ثلاثي", 4: "رباعي"}.get(len(root), f"{len(root)} lettres"),
        nature=nature_of(root),
        total=len(rows),
        verbs=ordered(verbs),
        nouns=ordered(nouns),
        bab=_bab(bab_vowels),
        absent_verbs=[c for c in VERB_COLUMNS if c not in used_columns] + [w for w in wazn_names.values() if w not in used_wazn],
        absent_nouns=[t for t in NOUN_TYPES.values() if t not in used_types],
    )


# --- Rendering (Markdown) -----------------------------------------------------

MAX_REFS = 6


def _entries(entries: list[Entry]) -> str:
    return "<br>".join(f"{e.form} ({len(e.refs)}){' — ' + e.traits if e.traits else ''}" for e in entries)


def _refs(entries: list[Entry]) -> str:
    refs = [ref for e in entries for ref in e.refs]
    return ", ".join(refs[:MAX_REFS]) + (f", … (+{len(refs) - MAX_REFS})" if len(refs) > MAX_REFS else "")


def _kind(kind: str) -> str:
    return kind.replace("ambiguë", t("ambiguous"), 1)


def render(found: Identity, meta: dict[str, str]) -> str:
    lines = [
        f"# {t('identity')} — {found.root}",
        "",
        meta_line(meta, t("categories")),
        "",
        f"- {found.letters} ؛ {found.nature}",
        f"- {t('occurrences')} : {found.total} ؛ {t('verbs')} : {found.n_verbs} ؛ {t('nouns')} : {found.n_nouns}",
    ]
    if found.bab:
        lines.append(f"- {t('bab_line')} : " + " ؛ ".join(f"{k} : {v}" for k, v in found.bab.items()))

    lines += ["", f"## {t('verbs')}", ""]
    if found.verbs:
        columns = [c for c in VERB_COLUMNS if any(column == c for _, column in found.verbs)]
        lines += [f"| {t('wazn')} | " + " | ".join(columns) + " |", "|---|" + "---|" * len(columns)]
        for wazn in dict.fromkeys(w for w, _ in found.verbs):
            cells = [_entries(found.verbs.get((wazn, c), [])) or "—" for c in columns]
            lines.append(f"| {wazn} | " + " | ".join(cells) + " |")
    else:
        lines.append(t("no_verb"))
    lines += ["", f"{t('absent')} : " + (" ، ".join(found.absent_verbs) or "—")]

    lines += ["", f"## {t('nouns')}", ""]
    if found.nouns:
        head = (t("kind"), t("derivation"), t("wazn"), t("forms"), t("refs"))
        lines += ["| " + " | ".join(head) + " |", "|---|---|---|---|---|"]
        for (kind, number, pattern), entries in sorted(found.nouns.items(), key=lambda item: -sum(len(e.refs) for e in item[1])):
            lines.append(f"| {_kind(kind)} | {number} | {pattern} | {_entries(entries)} | {_refs(entries)} |")
    else:
        lines.append(t("no_noun"))
    lines += [
        "",
        f"{t('absent_types')} : " + (" ، ".join(found.absent_nouns) or "—"),
        "",
        f"{t('unused_forms')} : {t('not_computed')}",
    ]
    return "\n".join(lines) + "\n"
