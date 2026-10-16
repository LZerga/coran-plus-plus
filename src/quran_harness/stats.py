"""Step 6: is a companion of a form found with it more often than chance would give?

The unit is the segment. For a reference form X and a companion Y:

    n     segments of the text
    n_x   segments holding X
    n_y   segments holding Y
    n_xy  segments holding both

Two measures describe the association (PMI and log-likelihood). Neither says
whether it is above chance: that is the job of the random control (CLAUDE.md
rule 6). The words of the text are shuffled between the segments, the segments
keeping their sizes, and n_xy is counted again; the p-value is the share of
shuffles that give at least the observed count.

    corpus  words shuffled across the whole text (the control asked by the SPEC)
    sura    words shuffled inside each sura (a stricter control: it keeps what each
            sura talks about, so a companion that only shares a sura fails it)
"""

from __future__ import annotations

import math
import sqlite3
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

CONTROLS = ("corpus", "sura")
ItemKey = tuple  # what makes two words the same companion (rebuilt on the cells at lot E)


@dataclass(frozen=True)
class Control:
    expected: float  # mean of n_xy over the shuffles
    p_value: float
    q_value: float  # p-value corrected for the number of companions tested (Benjamini-Hochberg)


@dataclass(frozen=True)
class Association:
    n_xy: int
    n_x: int
    n_y: int
    n: int
    pmi: float
    log_likelihood: float
    controls: dict[str, Control]

    def reading(self, alpha: float, min_cooccurrence: int) -> str:
        """What the control allows one to say. Descriptive wording only."""
        if self.n_xy < min_cooccurrence:
            return "trop rare pour conclure"
        names = list(self.controls)
        if self.controls[names[0]].q_value > alpha:
            return "attendu par la seule fréquence du mot"
        failed = [name for name in names[1:] if self.controls[name].q_value > alpha]
        return "au-dessus du hasard" + (f" (pas sous le contrôle {', '.join(failed)})" if failed else "")


def pmi(n_xy: int, n_x: int, n_y: int, n: int) -> float:
    """Pointwise mutual information, in bits. 0 when X and Y are independent."""
    if n_xy == 0:
        return -math.inf
    return math.log2(n_xy * n / (n_x * n_y))


def log_likelihood(n_xy: int, n_x: int, n_y: int, n: int) -> float:
    """Dunning's G² on the 2x2 table of the segments (with or without X, with or without Y)."""
    observed = (n_xy, n_x - n_xy, n_y - n_xy, n - n_x - n_y + n_xy)
    expected = (n_x * n_y / n, n_x * (n - n_y) / n, (n - n_x) * n_y / n, (n - n_x) * (n - n_y) / n)
    return 2 * sum(o * math.log(o / e) for o, e in zip(observed, expected) if o > 0)


def benjamini_hochberg(p_values: Sequence[float]) -> list[float]:
    """q-values: for each test, the smallest false discovery rate at which it is kept."""
    m = len(p_values)
    order = sorted(range(m), key=lambda i: p_values[i])
    q_values = [0.0] * m
    smallest = 1.0
    for rank in range(m, 0, -1):
        i = order[rank - 1]
        smallest = min(smallest, p_values[i] * m / rank)
        q_values[i] = smallest
    return q_values


class Corpus:
    """The words of the text as arrays: which companion each one is, in which segment, in which sura."""

    def __init__(self, items: Sequence[ItemKey], segments: Sequence[int], suras: Sequence[int], refs: Sequence[str] = ()):
        keys = {key: i for i, key in enumerate(dict.fromkeys(items))}
        self.keys = keys
        self.item = np.array([keys[key] for key in items], dtype=np.int64)
        _, self.segment = np.unique(np.array(segments), return_inverse=True)
        self.sura = np.array(suras, dtype=np.int64)
        self.n_segments = int(self.segment.max()) + 1 if len(items) else 0
        self.token_of_ref = {ref: i for i, ref in enumerate(refs)}
        if np.any(np.diff(self.sura) < 0):
            raise ValueError("les mots doivent être donnés dans l'ordre du texte")
        pairs = np.unique(self.item * self.n_segments + self.segment)
        self.segments_per_item = np.bincount(pairs // self.n_segments, minlength=len(keys))

    def _shuffled_segments(self, rng: np.random.Generator, control: str) -> np.ndarray:
        """Segment of each word once the words are shuffled between the slots of the text."""
        if control == "corpus":
            order = rng.permutation(len(self.item))
        elif control == "sura":
            order = np.lexsort((rng.random(len(self.item)), self.sura))  # a shuffle inside each sura
        else:
            raise ValueError(f"contrôle inconnu : {control!r} (attendu : {', '.join(CONTROLS)})")
        shuffled = np.empty_like(self.segment)
        shuffled[order] = self.segment
        return shuffled

    def _companion_tokens(self, reference_tokens: np.ndarray, companions: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """The words that are one of the companions (reference words left out), and which companion each is."""
        position = np.full(len(self.keys), -1, dtype=np.int64)
        position[companions] = np.arange(len(companions))
        token_position = position[self.item]
        token_position[reference_tokens] = -1
        tokens = np.flatnonzero(token_position >= 0)
        return tokens, token_position[tokens]

    def _cooccurrences(
        self, reference_tokens: np.ndarray, tokens: np.ndarray, which: np.ndarray, n_companions: int, segment: np.ndarray
    ) -> np.ndarray:
        with_reference = np.zeros(self.n_segments, dtype=bool)
        with_reference[segment[reference_tokens]] = True
        token_segments = segment[tokens]
        hit = with_reference[token_segments]
        pairs = np.unique(which[hit] * self.n_segments + token_segments[hit])
        return np.bincount(pairs // self.n_segments, minlength=n_companions)

    def cooccurrences(self, reference_tokens: np.ndarray, companions: np.ndarray) -> np.ndarray:
        """For each companion, the number of segments holding it together with a reference word."""
        tokens, which = self._companion_tokens(reference_tokens, companions)
        return self._cooccurrences(reference_tokens, tokens, which, len(companions), self.segment)

    def associations(
        self,
        reference_refs: Sequence[str],
        companion_keys: Sequence[ItemKey],
        controls: Sequence[str],
        permutations: int,
        seed: int,
    ) -> list[Association]:
        """Measures and random controls for each companion of the words at `reference_refs`."""
        reference = np.array([self.token_of_ref[ref] for ref in reference_refs], dtype=np.int64)
        companions = np.array([self.keys[key] for key in companion_keys], dtype=np.int64)
        tokens, which = self._companion_tokens(reference, companions)
        observed = self._cooccurrences(reference, tokens, which, len(companions), self.segment)
        n_x = len(np.unique(self.segment[reference]))

        results: dict[str, tuple[np.ndarray, list[float], list[float]]] = {}
        for number, control in enumerate(controls):
            rng = np.random.default_rng([seed, number])
            at_least, total = np.zeros(len(companions), dtype=np.int64), np.zeros(len(companions), dtype=np.int64)
            for _ in range(permutations):
                shuffled = self._shuffled_segments(rng, control)
                counts = self._cooccurrences(reference, tokens, which, len(companions), shuffled)
                at_least += counts >= observed
                total += counts
            p_values = ((at_least + 1) / (permutations + 1)).tolist()
            results[control] = (total / permutations, p_values, benjamini_hochberg(p_values))

        return [
            Association(
                n_xy=int(observed[k]),
                n_x=n_x,
                n_y=int(self.segments_per_item[item]),
                n=self.n_segments,
                pmi=pmi(int(observed[k]), n_x, int(self.segments_per_item[item]), self.n_segments),
                log_likelihood=log_likelihood(int(observed[k]), n_x, int(self.segments_per_item[item]), self.n_segments),
                controls={
                    control: Control(float(expected[k]), p_values[k], q_values[k])
                    for control, (expected, p_values, q_values) in results.items()
                },
            )
            for k, item in enumerate(companions)
        ]
