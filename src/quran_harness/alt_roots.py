"""Roots of the `quran-morphology` file (mustafa0x), a corrected fork of the corpus.

Same word numbering as the Quranic Arabic Corpus. It is not an independent source:
where both agree nothing is proven; only its corrections are informative.
"""

from __future__ import annotations

from pathlib import Path

# The corpus writes a hamza radical as an alef (اله); the fork writes the hamza (أله).
_HAMZAS = str.maketrans(dict.fromkeys("ءآأؤإئ", "ا"))


def fold_hamza(root: str) -> str:
    """Root label with every hamza written as an alef, to compare labels of two sources."""
    return root.translate(_HAMZAS)


def read_roots(path: Path) -> dict[str, list[str]]:
    """Roots of each word, keyed by `sura:aya:word`, in segment order."""
    roots: dict[str, list[str]] = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            location, _form, _tag, features = line.rstrip("\r\n").split("\t")
            word = location.rsplit(":", 1)[0]
            for feature in features.split("|"):
                if feature.startswith("ROOT:"):
                    roots.setdefault(word, []).append(feature[5:])
    return roots
