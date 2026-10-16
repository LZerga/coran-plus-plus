"""Step 5: the fiche of a reference form — identity card (A), companions (B), segment comparisons.

Everything here is computed from the database; nothing is interpreted. Each figure
comes with the references (sura:aya:word) it was counted from.
"""

from __future__ import annotations

import sqlite3
from collections import Counter
from dataclasses import dataclass, field

from . import compare, readings
from .config import form_level
from .elements import Element, ElementLoader
from .index import occurrences_of_form, occurrences_of_root
from .segmentation import selected_scheme
from .stats import Association, Corpus

POSITIONS = ("début", "milieu", "fin", "seul")
FORM_LEVELS = {"written": "mot écrit", "core": "sans clitiques", "bare": "sans clitiques ni article"}
MAX_REFS_SHOWN = 12


@dataclass(frozen=True)
class SegmentUse:
    """One segment holding the reference form."""

    ref: str  # sura:aya:start-end
    elements: tuple[Element, ...]
    ref_indexes: tuple[int, ...]  # where the reference form stands in `elements`

    @property
    def position(self) -> str:
        if len(self.elements) == 1:
            return "seul"
        first = self.ref_indexes[0]
        return "début" if first == 0 else "fin" if first == len(self.elements) - 1 else "milieu"


@dataclass
class Companion:
    kind: str  # a: same root | b: another root, or a noun or verb without root | c: letter or pronoun
    form: str
    lemma: str
    root: str
    nature: str
    refs: list[str] = field(default_factory=list)
    segments: set[str] = field(default_factory=set)
    before: int = 0
    after: int = 0
    stats: Association | None = None  # step 6: measures and random controls

    @property
    def key(self) -> tuple[str, str, str]:
        return self.form, self.lemma, self.root


@dataclass(frozen=True)
class PairResult:
    a: SegmentUse
    b: SegmentUse
    comparison: compare.Comparison


@dataclass(frozen=True)
class UsageGroup:
    """Segments of the form that resemble each other (bloc C)."""

    members: tuple[SegmentUse, ...]
    shared_block: str  # the identical block found in the most pairs of the group
    shared_in: int  # number of pairs of the group that have it
    pairs: int  # number of pairs of the group


@dataclass(frozen=True)
class ReadingsBlock:
    """What the other riwayat change in the segments of the form (bloc D). Letters only."""

    riwayat: tuple[str, ...]
    on_reference: tuple[readings.RecordedVariant, ...]  # variants on an occurrence of the form itself
    in_segments: tuple[readings.RecordedVariant, ...]  # every variant inside the segments of the form
    # companion key -> riwaya -> number of shared segments where the form or the companion is changed
    touched: dict[tuple[str, str, str], dict[str, int]]


def readings_block(connection: sqlite3.Connection, uses: list[SegmentUse], companions: list[Companion]) -> ReadingsBlock:
    in_segments: list[readings.RecordedVariant] = []
    changed: dict[str, set[int]] = {}  # riwaya -> base words it changes or removes
    for use in uses:
        for variant in readings.variants_on_words(connection, use.elements[0].word_id, use.elements[-1].word_id):
            in_segments.append(variant)
            changed.setdefault(variant.riwaya, set()).update(variant.replaced_words)

    reference_words = {use.elements[i].word_id for use in uses for i in use.ref_indexes}
    touched: dict[tuple[str, str, str], dict[str, int]] = {}
    for companion in companions:
        companion_refs = set(companion.refs)
        for use in uses:
            if use.ref not in companion.segments:
                continue
            involved = {use.elements[i].word_id for i in use.ref_indexes}
            involved |= {e.word_id for e in use.elements if e.ref in companion_refs}
            for riwaya, words in changed.items():
                if involved & words:
                    per_riwaya = touched.setdefault(companion.key, {})
                    per_riwaya[riwaya] = per_riwaya.get(riwaya, 0) + 1
    in_segments = list(dict.fromkeys(in_segments))  # a variant across two segments is listed once
    on_reference = [v for v in in_segments if reference_words & set(v.replaced_words)]
    return ReadingsBlock(tuple(readings.readings(connection)), tuple(on_reference), tuple(in_segments), touched)


def usage_groups(uses: list[SegmentUse], pairs: list[PairResult], links: frozenset[str]) -> list[UsageGroup]:
    """Connected groups: two segments are together when a chain of linked pairs joins them."""
    group_of = {use.ref: use.ref for use in uses}

    def find(ref: str) -> str:
        while group_of[ref] != ref:
            group_of[ref] = group_of[group_of[ref]]
            ref = group_of[ref]
        return ref

    for pair in pairs:
        if pair.comparison.relation in links:
            group_of[find(pair.b.ref)] = find(pair.a.ref)

    members: dict[str, list[SegmentUse]] = {}
    for use in uses:
        members.setdefault(find(use.ref), []).append(use)
    groups = []
    for root, group in members.items():
        inside = [pair for pair in pairs if find(pair.a.ref) == root and find(pair.b.ref) == root]
        blocks: Counter = Counter()
        texts: dict[tuple, str] = {}
        for pair in inside:
            for block in pair.comparison.blocks:
                elements = pair.a.elements[block.a_start : block.a_start + block.length]
                signature = tuple(e.written for e in elements)
                blocks[signature] += 1
                texts.setdefault(signature, " ".join(e.text for e in elements))
        best = max(blocks, key=lambda s: (blocks[s], len(s)), default=None)
        groups.append(UsageGroup(tuple(group), texts.get(best, ""), blocks.get(best, 0), len(inside)))
    return sorted(groups, key=lambda g: -len(g.members))


@dataclass(frozen=True)
class Fiche:
    form: str
    lemma: str
    root: str
    parameters: dict[str, str]
    occurrences: list[str]  # references of the words
    writings: Counter  # the word as written (with vowels) -> count
    uses: list[SegmentUse]
    companions: list[Companion]
    attached: dict[tuple[str, str], list[str]]  # (form, tag) of what is attached to the reference word -> references
    pairs: list[PairResult]
    pairs_skipped: int  # number of pairs not compared because there were too many
    groups: list[UsageGroup] = field(default_factory=list)
    statistics: dict | None = None  # settings of the random control, when it was run
    readings: ReadingsBlock | None = None  # None when the riwayat tables are not built


def _segment_of(connection: sqlite3.Connection, scheme: str, sura: int, aya: int, pos: int) -> tuple[int, int]:
    return connection.execute(
        """SELECT s.start_pos, s.end_pos FROM segments s JOIN segmentations n ON n.id = s.segmentation_id
           WHERE n.name = ? AND s.sura = ? AND s.aya = ? AND s.start_pos <= ? AND s.end_pos >= ?""",
        (scheme, sura, aya, pos, pos),
    ).fetchone()


def _companions(uses: list[SegmentUse]) -> list[Companion]:
    found: dict[tuple, Companion] = {}
    for use in uses:
        reference = use.elements[use.ref_indexes[0]]
        for index, element in enumerate(use.elements):
            if index in use.ref_indexes:
                continue
            if element.roots & reference.roots:
                kind = "a"
            elif element.is_function_word:
                kind = "c"
            else:
                kind = "b"
            lemma, root = " ".join(sorted(element.lemmas)), " ".join(sorted(element.roots))
            key = (kind, element.core, lemma, root)
            companion = found.setdefault(key, Companion(kind, element.core, lemma, root, element.nature if kind == "c" else ""))
            companion.refs.append(element.ref)
            companion.segments.add(use.ref)
            if index < use.ref_indexes[0]:
                companion.before += 1
            else:
                companion.after += 1
    return sorted(found.values(), key=lambda c: (c.kind, -len(c.segments), -len(c.refs), c.form))


class _Builder:
    """What the fiches of one request share: settings, loaded words, and the corpus when statistics are asked."""

    def __init__(self, connection: sqlite3.Connection, config: dict, scheme: str | None, level: str | None, with_stats: bool):
        self.connection = connection
        self.config = config
        self.level = level or form_level(config)
        self.scheme = scheme or selected_scheme(config)
        self.settings = compare.Settings.from_config(config)
        self.loader = ElementLoader(connection, config)
        self.statistics = dict(config["statistics"]) if with_stats else None
        self.corpus: Corpus | None = None
        code_version, reading = (
            connection.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()[0] for key in ("code_version", "reading")
        )
        self.parameters = {
            "lecture": reading,
            "forme": FORM_LEVELS[self.level],
            "découpage": self.scheme,
            "comparaison": "sans voyelles" if config["normalization"]["comparison_level"] == 2 else "avec voyelles",
            "code": code_version,
        }

    def fiche(self, form: str, lemma: str, root: str, occurrences: list) -> Fiche:
        connection, config = self.connection, self.config
        positions: dict[tuple[int, int, int, int], list[int]] = {}
        for occurrence in occurrences:
            sura, aya, pos = (int(n) for n in occurrence.ref.split(":"))
            start, end = _segment_of(connection, self.scheme, sura, aya, pos)
            positions.setdefault((sura, aya, start, end), []).append(pos - start)
        uses = [
            SegmentUse(f"{sura}:{aya}:{start}-{end}", tuple(self.loader.span(sura, aya, start, end)), tuple(indexes))
            for (sura, aya, start, end), indexes in positions.items()
        ]

        attached: dict[tuple[str, str], list[str]] = {}
        for use in uses:
            for index in use.ref_indexes:
                for form_, tag, _kind in use.elements[index].attached:
                    attached.setdefault((form_, tag), []).append(use.elements[index].ref)

        n_pairs = len(uses) * (len(uses) - 1) // 2
        pairs: list[PairResult] = []
        if n_pairs <= config["relations"]["max_pairs"]:
            pairs = [
                PairResult(a, b, compare.compare(a.elements, b.elements, self.settings))
                for i, a in enumerate(uses)
                for b in uses[i + 1 :]
            ]
        companions = _companions(uses)
        if self.statistics and companions:
            self.corpus = self.corpus or Corpus.load(connection, config, self.scheme)
            associations = self.corpus.associations(
                [o.ref for o in occurrences],
                [c.key for c in companions],
                self.statistics["controls"],
                self.statistics["permutations"],
                self.statistics["seed"],
            )
            for companion, association in zip(companions, associations):
                companion.stats = association
        return Fiche(
            form=form,
            lemma=lemma,
            root=root,
            parameters=self.parameters,
            occurrences=[o.ref for o in occurrences],
            writings=Counter(o.text for o in occurrences),
            uses=uses,
            companions=companions,
            attached=attached,
            pairs=pairs,
            pairs_skipped=0 if pairs or n_pairs == 0 else n_pairs,
            groups=usage_groups(uses, pairs, frozenset(config["usage_groups"]["links"])) if pairs else [],
            statistics=self.statistics,
            readings=readings_block(connection, uses, companions) if readings.is_built(connection) else None,
        )


def build(
    connection: sqlite3.Connection,
    form: str,
    config: dict,
    scheme: str | None = None,
    level: str | None = None,
    with_stats: bool = True,
) -> list[Fiche]:
    """One fiche per lemma written as `form` (two different words written alike are never merged)."""
    builder = _Builder(connection, config, scheme, level, with_stats)
    by_lemma: dict[tuple[str, str], list] = {}
    for occurrence in occurrences_of_form(connection, form, builder.level):
        by_lemma.setdefault((occurrence.lemma, occurrence.root), []).append(occurrence)
    return [builder.fiche(form, lemma, root, occurrences) for (lemma, root), occurrences in by_lemma.items()]


def build_root(
    connection: sqlite3.Connection, root: str, config: dict, scheme: str | None = None, with_stats: bool = True
) -> list[Fiche]:
    """One fiche for every word of a root, all its forms and lemmas together."""
    builder = _Builder(connection, config, scheme, None, with_stats)
    occurrences = occurrences_of_root(connection, root)
    if not occurrences:
        return []
    lemmas = Counter(occurrence.lemma for occurrence in occurrences)
    summary = f"{len(lemmas)} lemmes" if len(lemmas) > 1 else next(iter(lemmas))
    return [builder.fiche(f"racine {occurrences[0].root}", summary, occurrences[0].root, occurrences)]


# --- Rendering (Markdown) -----------------------------------------------------


def _refs(refs: list[str]) -> str:
    shown = ", ".join(refs[:MAX_REFS_SHOWN])
    return shown if len(refs) <= MAX_REFS_SHOWN else f"{shown}, … (+{len(refs) - MAX_REFS_SHOWN})"


def _text(elements, marked: tuple[int, ...] = ()) -> str:
    return " ".join(f"**{e.text}**" if i in marked else e.text for i, e in enumerate(elements))


def describe(a, b, comparison: compare.Comparison) -> dict[str, str]:
    """The parts of a comparison, as text. `a` and `b` are the two sequences of elements."""
    blocks = [_text(a[blk.a_start : blk.a_start + blk.length]) for blk in comparison.blocks]
    pairs = [
        f"{a[p.a_index].text} ~ {b[p.b_index].text} ({compare.LEVEL_LABELS[p.level]})" for p in comparison.pairs
    ]
    return {
        "relation": compare.LABELS[comparison.relation],
        "blocs identiques": " | ".join(blocks) or "—",
        "éléments communs hors blocs": " ; ".join(pairs) or "—",
        "en plus dans A": _text([a[i] for i in comparison.extra_a]) or "—",
        "en plus dans B": _text([b[i] for i in comparison.extra_b]) or "—",
        "ordre": "même ordre" if comparison.same_order else "ordre différent",
    }


def _companion_table(companions: list[Companion], with_root: bool, statistics: dict | None) -> list[str]:
    head = ["Forme", "Lemme", "Racine"] if with_root else ["Forme", "Nature", "Lemme"]
    head += ["Occurrences", "Segments", "Avant", "Après"]
    if statistics:
        head += ["Segments du mot dans le texte", "PMI", "G²"]
        head += [f"Attendu, p, p corrigée ({control})" for control in statistics["controls"]]
        head += ["Lecture"]
    head += ["Références"]
    lines = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for c in companions:
        cells = [c.form, *((c.lemma or "—", c.root or "—") if with_root else (c.nature, c.lemma or "—"))]
        cells += [len(c.refs), len(c.segments), c.before, c.after]
        if statistics and c.stats:
            s = c.stats
            cells += [s.n_y, f"{s.pmi:.2f}", f"{s.log_likelihood:.1f}"]
            cells += [f"{k.expected:.2f}, {k.p_value:.3f}, {k.q_value:.3f}" for k in s.controls.values()]
            cells += [s.reading(statistics["alpha"], statistics["min_cooccurrence"])]
        cells += [_refs(c.refs)]
        lines.append("| " + " | ".join(str(cell) for cell in cells) + " |")
    return lines


def render(fiche: Fiche, max_pairs_shown: int = 100) -> str:
    parameters = " · ".join(f"{key} : {value}" for key, value in fiche.parameters.items())
    ayas = {ref.rsplit(":", 1)[0] for ref in fiche.occurrences}
    lines = [
        f"# Fiche — forme {fiche.form}, lemme {fiche.lemma}, racine {fiche.root}",
        "",
        parameters,
        "",
        "## A. Carte d'identité",
        "",
        f"- Occurrences : {len(fiche.occurrences)}, dans {len(ayas)} versets et {len(fiche.uses)} segments",
        f"- Références : {_refs(fiche.occurrences)}",
        "- Graphies : " + ", ".join(f"{text} ({count})" for text, count in fiche.writings.most_common()),
    ]
    positions = Counter(use.position for use in fiche.uses)
    lines.append("- Position dans le segment : " + ", ".join(f"{name} {positions[name]}" for name in POSITIONS if positions[name]))
    lines += ["", "| n° | Segment | Position | Mots | Texte |", "|---|---|---|---|---|"]
    for number, use in enumerate(fiche.uses, start=1):
        lines.append(f"| {number} | {use.ref} | {use.position} | {len(use.elements)} | {_text(use.elements, use.ref_indexes)} |")

    lines += ["", "## B. Compagnons", ""]
    if fiche.statistics:
        s = fiche.statistics
        lines += [
            f"Contrôle aléatoire : les mots sont mélangés entre les segments, qui gardent leur taille "
            f"({', '.join(s['controls'])} ; {s['permutations']} permutations ; graine {s['seed']}). "
            f"« Attendu » est le nombre moyen de segments communs après mélange ; p est la part des mélanges "
            f"qui en donnent au moins autant qu'observé ; la p corrigée tient compte des "
            f"{len(fiche.companions)} compagnons testés (Benjamini-Hochberg). Seuil : {s['alpha']}.",
            "",
        ]
    sections = [
        ("a", "a. Formes de la même racine", True),
        ("b", "b. Formes d'autres racines", True),
        ("c", "c. Lettres et pronoms", False),
    ]
    for kind, title, with_root in sections:
        companions = [c for c in fiche.companions if c.kind == kind]
        lines += [f"### {title}", ""]
        lines += _companion_table(companions, with_root, fiche.statistics) if companions else ["Aucun."]
        lines.append("")
    lines += ["### Collés à la forme", ""]
    if fiche.attached:
        lines += ["| Élément | Étiquette | Occurrences | Références |", "|---|---|---|---|"]
        for (form, tag), refs in sorted(fiche.attached.items(), key=lambda item: -len(item[1])):
            lines.append(f"| {form} | {tag} | {len(refs)} | {_refs(refs)} |")
    else:
        lines.append("Aucun.")

    lines += ["", "## Comparaison des segments deux à deux", ""]
    if fiche.pairs_skipped:
        lines.append(f"Non calculée : {fiche.pairs_skipped} paires, au-delà de la limite `relations.max_pairs`.")
    elif not fiche.pairs:
        lines.append("Un seul segment : rien à comparer.")
    else:
        relations = Counter(pair.comparison.relation for pair in fiche.pairs)
        lines.append(f"{len(fiche.pairs)} paires : " + ", ".join(f"{compare.LABELS[r]} {relations[r]}" for r in compare.LABELS if relations[r]))
        lines += ["", "| A | B | Relation | Blocs identiques | Éléments communs hors blocs | En plus dans A | En plus dans B | Ordre |", "|" + "---|" * 8]
        order = list(compare.LABELS)
        ranked = sorted(fiche.pairs, key=lambda pair: (order.index(pair.comparison.relation), -pair.comparison.common))
        for pair in ranked[:max_pairs_shown]:
            parts = describe(pair.a.elements, pair.b.elements, pair.comparison)
            lines.append(f"| {pair.a.ref} | {pair.b.ref} | " + " | ".join(parts.values()) + " |")
        if len(ranked) > max_pairs_shown:
            lines.append(f"\n… {len(ranked) - max_pairs_shown} paires non affichées.")

    if fiche.groups:
        lines += [
            "",
            "## C. Usages regroupés par ressemblance",
            "",
            "Deux segments sont dans le même groupe quand une identité (totale ou partielle) les relie, "
            "directement ou par l'intermédiaire d'autres segments du groupe.",
            "",
            "| Groupe | Segments | Bloc identique le plus partagé | Paires qui le portent | Références |",
            "|---|---|---|---|---|",
        ]
        for number, group in enumerate(fiche.groups, start=1):
            shared = f"{group.shared_in} sur {group.pairs}" if group.pairs else "—"
            lines.append(
                f"| {number} | {len(group.members)} | {group.shared_block or '—'} | {shared} | "
                f"{_refs([use.ref for use in group.members])} |"
            )

    if fiche.readings:
        lines += _readings_section(fiche)
    return "\n".join(lines) + "\n"


def _variant_rows(variants) -> list[str]:
    lines = ["| Riwāya | Mot | Nature | Texte de base | Texte de la riwāya |", "|---|---|---|---|---|"]
    lines += [f"| {v.riwaya} | {v.ref} | {v.kind} | {v.base_text or '—'} | {v.variant_text or '—'} |" for v in variants]
    return lines


def _readings_section(fiche: Fiche) -> list[str]:
    block = fiche.readings
    n = len(block.riwayat)
    unchanged = len(fiche.companions) - len(block.touched)
    lines = [
        "",
        "## D. Selon les lectures",
        "",
        f"Texte de base (Hafs) comparé à {n} autres riwāyāt : {', '.join(block.riwayat)}. "
        "Seuls les écarts de lettres et de mots sont relevés ; les écarts de voyelles et de prononciation "
        "ne le sont pas. Les segments sont ceux du texte de base.",
        "",
        f"- Forme de référence : {len(block.on_reference)} écart(s) sur ses occurrences.",
        f"- Compagnons : {unchanged} sur {len(fiche.companions)} ont leur association inchangée dans les {n} riwāyāt.",
    ]
    if block.on_reference:
        lines += ["", "### Écarts sur la forme elle-même", "", *_variant_rows(block.on_reference)]
    if block.touched:
        lines += [
            "",
            "### Associations touchées",
            "",
            "| Compagnon | Lemme | Segments communs | Riwāyāt où l'association est inchangée | Segments touchés, par riwāya |",
            "|---|---|---|---|---|",
        ]
        for companion in fiche.companions:
            per_riwaya = block.touched.get(companion.key)
            if per_riwaya:
                detail = ", ".join(f"{riwaya} {count}" for riwaya, count in per_riwaya.items())
                lines.append(
                    f"| {companion.form} | {companion.lemma or '—'} | {len(companion.segments)} | "
                    f"{n - len(per_riwaya)} sur {n} | {detail} |"
                )
    lines += ["", "### Tous les écarts dans les segments de la forme", ""]
    lines += _variant_rows(block.in_segments) if block.in_segments else ["Aucun."]
    return lines


# --- Two forms side by side ---------------------------------------------------

SAME_FORM = "même forme associée"
SAME_ROOT = "même racine, formes différentes"
NO_COUNTERPART = "aucune"


@dataclass(frozen=True)
class SharedCompanion:
    category: str
    side: str  # "les deux", or the form that alone has this companion
    form: str
    lemma: str
    root: str
    segments: tuple[int, int]  # segments shared with the first form, with the second
    other_forms: tuple[str, ...]  # for SAME_ROOT: the forms of that root beside the other form


def compare_companions(first: Fiche, second: Fiche) -> list[SharedCompanion]:
    """Sort the companions of two forms: same companion, companion of the same root, or none (SPEC step 6)."""
    rows = []
    for mine, theirs, side, flip in ((first, second, first.form, False), (second, first, second.form, True)):
        their_keys = {c.key: c for c in theirs.companions}
        for companion in mine.companions:
            other = their_keys.get(companion.key)
            if other is not None:
                if flip:
                    continue  # already listed from the first form
                rows.append(
                    SharedCompanion(SAME_FORM, "les deux", *companion.key, (len(companion.segments), len(other.segments)), ())
                )
                continue
            relatives = tuple(sorted(c.form for c in theirs.companions if companion.root and c.root == companion.root))
            counts = (0, len(companion.segments)) if flip else (len(companion.segments), 0)
            rows.append(SharedCompanion(SAME_ROOT if relatives else NO_COUNTERPART, side, *companion.key, counts, relatives))
    order = [SAME_FORM, SAME_ROOT, NO_COUNTERPART]
    return sorted(rows, key=lambda r: (order.index(r.category), -sum(r.segments), r.form))


def render_companion_comparison(first: Fiche, second: Fiche) -> str:
    rows = compare_companions(first, second)
    counts = Counter(row.category for row in rows)
    parameters = " · ".join(f"{key} : {value}" for key, value in first.parameters.items())
    lines = [
        f"# Compagnons de {first.form} ({first.lemma}) et de {second.form} ({second.lemma})",
        "",
        parameters,
        "",
        f"- {first.form} : {len(first.occurrences)} occurrences, {len(first.uses)} segments, {len(first.companions)} compagnons",
        f"- {second.form} : {len(second.occurrences)} occurrences, {len(second.uses)} segments, {len(second.companions)} compagnons",
        "- " + ", ".join(f"{category} : {counts[category]}" for category in (SAME_FORM, SAME_ROOT, NO_COUNTERPART)),
        "",
        f"| Catégorie | Chez | Forme | Lemme | Racine | Segments avec {first.form} | Segments avec {second.form} | Formes de la même racine chez l'autre |",
        "|" + "---|" * 8,
    ]
    for row in rows:
        lines.append(
            f"| {row.category} | {row.side} | {row.form} | {row.lemma or '—'} | {row.root or '—'} | "
            f"{row.segments[0]} | {row.segments[1]} | {', '.join(row.other_forms) or '—'} |"
        )
    return "\n".join(lines) + "\n"
