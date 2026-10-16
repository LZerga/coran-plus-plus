"""Reading the Tanzil base text as words, without changing a single character.

File format ("text with aya numbers"): one line `sura|aya|text` per aya, then a
comment block. Tokens are separated by single spaces. Pause marks are tokens of
their own; they are kept with the word they follow.

Tanzil writes the basmala in front of aya 1 of every sura except 1 and 9. Those
four words are kept apart under aya number 0 (see QUESTIONS.md, Q11).
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path

from .normalize import Level, normalize
from .raw_counts import is_sign_token

BASMALA_AYA = 0
SURAS_WITHOUT_BASMALA_PREFIX = frozenset({1, 9})


@dataclass(frozen=True)
class Word:
    sura: int
    aya: int  # 0 for the basmala written before aya 1
    pos: int  # 1-based position among the words of the aya
    text: str
    sign_after: str = ""  # pause mark tokens that follow the word, space-separated

    @property
    def ref(self) -> str:
        return f"{self.sura}:{self.aya}:{self.pos}"


def read_lines(path: Path) -> Iterator[tuple[int, int, str]]:
    with open(path, encoding="utf-8", newline="") as f:
        for line in f:
            line = line.rstrip("\r\n")
            if not line or line.startswith("#"):
                continue
            sura, aya, text = line.split("|", 2)
            yield int(sura), int(aya), text


def _words(sura: int, aya: int, tokens: list[str]) -> list[Word]:
    words: list[Word] = []
    for token in tokens:
        if not is_sign_token(token):
            words.append(Word(sura, aya, len(words) + 1, token))
        elif not words:
            raise ValueError(f"{sura}:{aya} : signe {token!r} sans mot qui le précède")
        else:
            last = words[-1]
            signs = f"{last.sign_after} {token}".strip()
            words[-1] = Word(last.sura, last.aya, last.pos, last.text, signs)
    return words


def split_lines(lines: Iterable[tuple[int, int, str]]) -> list[Word]:
    words: list[Word] = []
    basmala_key: list[str] | None = None
    for sura, aya, text in lines:
        tokens = text.split(" ")
        if (sura, aya) == (1, 1):
            basmala_key = [normalize(t, Level.NO_VOWELS) for t in tokens]
        if aya == 1 and sura not in SURAS_WITHOUT_BASMALA_PREFIX:
            if basmala_key is None:
                raise ValueError("le verset 1:1 doit précéder les autres sourates")
            prefix, tokens = tokens[: len(basmala_key)], tokens[len(basmala_key) :]
            if [normalize(t, Level.NO_VOWELS) for t in prefix] != basmala_key:
                raise ValueError(f"{sura}:1 ne commence pas par la basmala : {' '.join(prefix)!r}")
            words.extend(_words(sura, BASMALA_AYA, prefix))
        words.extend(_words(sura, aya, tokens))
    return words


def read_words(path: Path) -> list[Word]:
    return split_lines(read_lines(path))


def rebuild_lines(words: Iterable[Word]) -> dict[tuple[int, int], str]:
    """Inverse of `split_lines`: the text of each aya exactly as in the file."""
    tokens: dict[tuple[int, int], list[str]] = {}
    for word in words:
        aya = 1 if word.aya == BASMALA_AYA else word.aya
        line = tokens.setdefault((word.sura, aya), [])
        line.append(word.text)
        if word.sign_after:
            line.append(word.sign_after)
    return {key: " ".join(line) for key, line in tokens.items()}
