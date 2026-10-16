"""The word without its clitics (level 1 of the equivalence scale, SPEC §2).

A word of the text stays one word (CLAUDE.md rule 3). This module only works out,
for a word and its corpus segments, which part is left once the attached particles
and complement pronouns are set aside:

    core = word - proclitics (the article is kept) - complement pronouns
    bare = core - article

A subject pronoun is part of the verb form and is never removed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol

ARTICLE = "PREFIX|Al+"
# Prepositions written as one word with a pronoun (له, به): the corpus makes the
# pronoun the stem. Here the preposition is the word and the pronoun its complement.
PREPOSITIONS_BEFORE_PRONOUN = frozenset({"PREFIX|l:P+", "PREFIX|bi+"})

# Verb forms whose subject is not an attached pronoun.
NO_ATTACHED_SUBJECT = {
    "PERF": frozenset({"3MS", "3FS"}),
    "IMPF": frozenset({"1S", "1P", "2MS", "3MS", "3FS"}),
    "IMPV": frozenset({"2MS"}),
}
_PERSON_GENDER_NUMBER = re.compile(r"[123]?[MF]?[SDP]")

# Same writing, two encodings (see ingest._ENCODING_VARIANTS).
_ENCODING_VARIANTS = (("ـٔ", "ء"), ("ـۧ", "ۦ"), ("ـ", ""))


class SegmentLike(Protocol):
    kind: str  # prefix | stem | suffix
    tag: str
    form: str
    features: str


@dataclass(frozen=True)
class WordForm:
    core: str
    bare: str
    has_article: bool
    proclitics: int  # article not counted
    subject_pronouns: int
    complement_pronouns: int
    elided_pronouns: int = 0  # complement pronouns the corpus annotates but the text does not write
    set_aside: tuple[tuple[str, str, str], ...] = ()  # (form, tag, kind) of what the core leaves out
    core_end: int | None = None  # where the core ends in the word; None when nothing follows it


def has_attached_subject(verb_features: str) -> bool:
    features = verb_features.split("|")
    aspect = next((f for f in features if f in NO_ATTACHED_SUBJECT), None)
    pgn = next((f for f in features if _PERSON_GENDER_NUMBER.fullmatch(f)), None)
    return aspect is not None and pgn is not None and pgn not in NO_ATTACHED_SUBJECT[aspect]


def _neutral(text: str) -> str:
    for variant, common in _ENCODING_VARIANTS:
        text = text.replace(variant, common)
    return text


def cut_span(text: str, lead: str, trail: str) -> tuple[int, int]:
    """Where a word of the base text starts once `lead` is removed, and where `trail` starts.

    The corpus forms may encode a hamza differently from the base text, so the
    boundaries are looked for in the base text itself.
    """
    if text.startswith(lead) and text.endswith(trail) and len(lead) + len(trail) <= len(text):
        return len(lead), len(text) - len(trail)
    lead, trail = _neutral(lead), _neutral(trail)
    start = next((i for i in range(len(text) + 1) if _neutral(text[:i]) == lead), None)
    end = next((j for j in range(len(text), -1, -1) if _neutral(text[j:]) == trail), None)
    if start is None or end is None or start > end:
        raise ValueError(f"impossible de retirer {lead!r} et {trail!r} de {text!r}")
    return start, end


def _cut(text: str, lead: str, trail: str) -> str:
    """Remove `lead` from the start and `trail` from the end of a word of the base text."""
    start, end = cut_span(text, lead, trail)
    return text[start:end]


def _set_aside(segments: list[SegmentLike]) -> tuple[tuple[str, str, str], ...]:
    return tuple((s.form, s.tag, s.kind) for s in segments if s.form)


def analyse(text: str, segments: list[SegmentLike]) -> WordForm:
    if not segments:  # word without annotation
        return WordForm(text, text, False, 0, 0, 0)
    prefixes = [s for s in segments if s.kind == "prefix"]
    stems = [s for s in segments if s.kind == "stem"]
    suffixes = [s for s in segments if s.kind == "suffix"]

    if (
        len(stems) == 1
        and stems[0].tag == "PRON"
        and not suffixes
        and prefixes
        and prefixes[-1].features in PREPOSITIONS_BEFORE_PRONOUN
    ):
        lead = "".join(s.form for s in prefixes[:-1])
        start, end = cut_span(text, lead, stems[0].form)
        core = text[start:end]
        return WordForm(core, core, False, len(prefixes) - 1, 0, 1, 0, _set_aside(prefixes[:-1] + stems), end)

    article = prefixes[-1] if prefixes and prefixes[-1].features == ARTICLE else None
    proclitics = prefixes[:-1] if article else prefixes

    host = stems[-1]
    subject = bool(suffixes) and suffixes[0].tag == "PRON" and host.tag == "V" and has_attached_subject(host.features)
    after_subject = suffixes[1:] if subject else suffixes
    kept = [s for s in after_subject if s.tag != "PRON"]
    complements = after_subject[len(kept) :]
    if any(s.tag != "PRON" for s in complements) or after_subject[: len(kept)] != kept:
        raise ValueError(f"ordre de suffixes inattendu dans {text!r}")

    lead = "".join(s.form for s in proclitics)
    trail = "".join(s.form for s in complements)
    start, end = cut_span(text, lead, trail)
    core = text[start:end]
    bare = _cut(text, lead + article.form, trail) if article else core
    elided = sum(1 for s in complements if not s.form)
    return WordForm(
        core,
        bare,
        article is not None,
        len(proclitics),
        int(subject),
        len(complements),
        elided,
        _set_aside(proclitics + complements),
        end if end < len(text) else None,
    )
