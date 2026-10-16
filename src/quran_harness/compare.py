"""Step 5: comparing two stretches of text (SPEC §2).

Two elements are equivalent at the lowest level that holds:

    0  same word as written, same lemma
    1  same word once the clitics are set aside, same lemma
    2  a lemma in common
    3  a root in common

The comparison first looks for identical blocks (runs of consecutive elements
identical at an identity level), wherever they stand in each stretch, so that the
same blocks in a different order are still found. What is left is then paired
element by element, strongest level first. The result is a description; the
relation (تطابق / تشابه / اختلاف) is read from it.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from .elements import Element

IDENTITY_TOTAL = "identity_total"
IDENTITY_PARTIAL = "identity_partial"
SIMILARITY = "similarity"
DIFFERENCE = "difference"

LABELS = {
    IDENTITY_TOTAL: "تطابق — identité totale",
    IDENTITY_PARTIAL: "تطابق — identité partielle",
    SIMILARITY: "تشابه — similarité",
    DIFFERENCE: "اختلاف — différence",
}
LEVEL_LABELS = {0: "même mot", 1: "même mot sans clitiques", 2: "même lemme", 3: "même racine"}


@dataclass(frozen=True)
class Settings:
    identity_levels: frozenset[int]
    similarity_levels: frozenset[int]
    min_identical_block: int
    min_common_elements: int
    reference_counts_as_element: bool

    @classmethod
    def from_config(cls, config: dict) -> Settings:
        equivalence, relations = config["equivalence"], config["relations"]
        return cls(
            frozenset(equivalence["identity_levels"]),
            frozenset(equivalence["similarity_levels"]),
            relations["min_identical_block"],
            relations["min_common_elements"],
            relations["reference_counts_as_element"],
        )


@dataclass(frozen=True)
class Block:
    """A run of consecutive identical elements: a[a_start:a_start+length] and b[b_start:...]."""

    a_start: int
    b_start: int
    length: int


@dataclass(frozen=True)
class Pair:
    """Two elements in common outside the blocks, with their equivalence level."""

    a_index: int
    b_index: int
    level: int


@dataclass(frozen=True)
class Comparison:
    relation: str
    blocks: tuple[Block, ...]
    pairs: tuple[Pair, ...]
    extra_a: tuple[int, ...]  # indexes of the elements of a with no counterpart in b
    extra_b: tuple[int, ...]
    same_order: bool  # the common parts follow each other in the same order in a and in b

    @property
    def common(self) -> int:
        return sum(block.length for block in self.blocks) + len(self.pairs)


def equivalence_level(a: Element, b: Element) -> int | None:
    if a.lemmas == b.lemmas:
        if a.written == b.written:
            return 0
        if a.core == b.core:
            return 1
    if a.lemmas & b.lemmas:
        return 2
    if a.roots & b.roots:
        return 3
    return None


def _identical_blocks(a: Sequence[Element], b: Sequence[Element], settings: Settings) -> list[Block]:
    """Longest common runs first, each element used once; ties go to the earliest run."""
    free_a, free_b = [True] * len(a), [True] * len(b)
    identical = [[equivalence_level(x, y) in settings.identity_levels for y in b] for x in a]
    blocks: list[Block] = []
    while True:
        best: Block | None = None
        for i in range(len(a)):
            for j in range(len(b)):
                length = 0
                while (
                    i + length < len(a)
                    and j + length < len(b)
                    and free_a[i + length]
                    and free_b[j + length]
                    and identical[i + length][j + length]
                ):
                    length += 1
                if length >= settings.min_identical_block and (best is None or length > best.length):
                    best = Block(i, j, length)
        if best is None:
            return sorted(blocks, key=lambda block: block.a_start)
        for k in range(best.length):
            free_a[best.a_start + k] = free_b[best.b_start + k] = False
        blocks.append(best)


def compare(a: Sequence[Element], b: Sequence[Element], settings: Settings) -> Comparison:
    blocks = _identical_blocks(a, b, settings)
    left_a = [i for i in range(len(a)) if not any(blk.a_start <= i < blk.a_start + blk.length for blk in blocks)]
    left_b = [j for j in range(len(b)) if not any(blk.b_start <= j < blk.b_start + blk.length for blk in blocks)]

    pairs: list[Pair] = []
    for level in sorted(settings.identity_levels | settings.similarity_levels):
        for i in list(left_a):
            match = next((j for j in left_b if equivalence_level(a[i], b[j]) == level), None)
            if match is not None:
                pairs.append(Pair(i, match, level))
                left_a.remove(i)
                left_b.remove(match)
    pairs.sort(key=lambda pair: pair.a_index)

    anchors = sorted([(blk.a_start, blk.b_start) for blk in blocks] + [(p.a_index, p.b_index) for p in pairs])
    same_order = all(first[1] < second[1] for first, second in zip(anchors, anchors[1:]))

    common = sum(block.length for block in blocks) + len(pairs)
    if not settings.reference_counts_as_element:
        common -= 1
    if len(blocks) == 1 and blocks[0].length == len(a) == len(b):
        relation = IDENTITY_TOTAL
    elif blocks:
        relation = IDENTITY_PARTIAL
    elif common >= settings.min_common_elements:
        relation = SIMILARITY
    else:
        relation = DIFFERENCE
    return Comparison(relation, tuple(blocks), tuple(pairs), tuple(left_a), tuple(left_b), same_order)
