"""Reading the Quranic Arabic Corpus morphology file (version 0.4).

One line per segment: `(sura:aya:word:segment)<TAB>FORM<TAB>TAG<TAB>FEATURES`.
FORM, LEM and ROOT are in Buckwalter transliteration. FEATURES starts with the
kind of segment (PREFIX, STEM or SUFFIX).
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

from .buckwalter import to_arabic

LEMMA_PASSTHROUGH = " 0123456789"  # a digit distinguishes homograph lemmas


@dataclass(frozen=True)
class Segment:
    sura: int
    aya: int
    word: int
    seg: int
    form_bw: str
    tag: str
    features: str

    @property
    def location(self) -> str:
        return f"{self.sura}:{self.aya}:{self.word}:{self.seg}"

    @property
    def kind(self) -> str:
        return self.features.split("|", 1)[0].lower()

    @cached_property
    def form(self) -> str:
        return to_arabic(self.form_bw)

    def _feature(self, name: str) -> str | None:
        for feature in self.features.split("|"):
            if feature.startswith(name + ":"):
                return feature.split(":", 1)[1]
        return None

    @property
    def root(self) -> str | None:
        root = self._feature("ROOT")
        return to_arabic(root) if root else None

    @property
    def lemma(self) -> str | None:
        lemma = self._feature("LEM")
        return to_arabic(lemma, LEMMA_PASSTHROUGH) if lemma else None


QacWord = list[Segment]


def read_words(path: Path) -> dict[tuple[int, int], list[QacWord]]:
    """Words of each aya, in order; each word is the list of its segments."""
    ayas: dict[tuple[int, int], list[QacWord]] = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            if not line.startswith("("):
                continue
            location, form, tag, features = line.rstrip("\r\n").split("\t")
            sura, aya, word, seg = (int(n) for n in location.strip("()").split(":"))
            segment = Segment(sura, aya, word, seg, form, tag, features)
            words = ayas.setdefault((sura, aya), [])
            if seg == 1:
                if word != len(words) + 1:
                    raise ValueError(f"numérotation de mots discontinue à {segment.location}")
                words.append([])
            if seg != len(words[-1]) + 1:
                raise ValueError(f"numérotation de segments discontinue à {segment.location}")
            words[-1].append(segment)
    return ayas


def word_form(word: QacWord) -> str:
    return "".join(segment.form for segment in word)
