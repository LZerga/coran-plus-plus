"""Step 6 (lot E): the random controls that turn an observation into an established result.

Layer تحليل of docs/DIMENSIONS.md. Three kinds of results are tested (CLAUDE.md rule 7):

    association   a companion found with the form in more segments than chance gives
                  (cells shuffled between segments, segment sizes kept; QUESTIONS.md, Q10)
    constraint    two optional columns of a matrix present together, never together, or one
                  implying the other (SPEC §2.7: fillers permuted between rows)
    covariation   in a family two forms share, a column where each form has its own filler
                  (the forms permuted between rows)

Every p-value is empirical, with a fixed seed. Associations are corrected for the number of
companions tested (Benjamini-Hochberg). A result is « مثبت إحصائيا » when its corrected
p-value is at most `statistics.alpha`, « ملاحظ » otherwise.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

import numpy as np

from . import stats
from .families import Analysis
from .matrix import Matrix

ASSOCIATION, CONSTRAINT, COVARIATION = "association", "constraint", "covariation"
EQUIVALENCE, IMPLICATION, EXCLUSION = "equivalence", "implication", "exclusion"
ESTABLISHED, OBSERVED = "established", "observed"


@dataclass(frozen=True)
class StatsSettings:
    seed: int
    permutations: int
    controls: tuple[str, ...]
    alpha: float
    min_cooccurrence: int
    support_min: int
    relative_min: float = 0.75

    @classmethod
    def from_config(cls, config: dict) -> StatsSettings:
        s = config["statistics"]
        return cls(s["seed"], s["permutations"], tuple(s["controls"]), s["alpha"], s["min_cooccurrence"],
                   config["comparison"]["support_min"], config["matrix"]["relative_min"])  # fmt: skip


@dataclass(frozen=True)
class Finding:
    kind: str  # association | constraint | covariation
    what: str  # short text: the companion, the two columns, the fillers
    detail: str  # e.g. the kind of constraint, the control that failed
    support: int  # number of segments the result rests on
    expected: float | None  # mean under the random control
    p_value: float
    q_value: float  # corrected (associations) or equal to p
    status: str  # established | observed
    refs: tuple[str, ...] = ()


# --- The cells as a corpus ----------------------------------------------------------------

_CORPORA: dict[tuple[str, str], stats.Corpus] = {}


def corpus(connection: sqlite3.Connection, scheme: str) -> stats.Corpus:
    """Every cell of the text (sura-opening basmalas left out), keyed by its form. Built once per base and scheme."""
    (path,) = [row[2] for row in connection.execute("PRAGMA database_list") if row[1] == "main"]
    key = (path, scheme)
    if key not in _CORPORA:
        rows = connection.execute(
            """SELECT u.ref, u.form, u.sura, su.segment_id FROM units u
               JOIN segment_units su ON su.unit_id = u.id
               JOIN segmentations n ON n.id = su.segmentation_id AND n.name = ?
               WHERE u.aya > 0 ORDER BY u.id""",
            (scheme,),
        ).fetchall()
        _CORPORA[key] = stats.Corpus([r[1] for r in rows], [r[3] for r in rows], [r[2] for r in rows], [r[0] for r in rows])
    return _CORPORA[key]


@dataclass(frozen=True)
class AssociationRequest:
    name: str  # the reference form
    reference_refs: tuple[str, ...]  # cell references of its occurrences
    companions: tuple[str, ...]  # companion forms to test


def associations(
    data: stats.Corpus, requests: list[AssociationRequest], settings: StatsSettings
) -> dict[str, list[Finding]]:
    """Association of each companion with its reference form. The shuffles are shared by all requests."""
    prepared = []
    for request in requests:
        reference = np.array([data.token_of_ref[r] for r in request.reference_refs], dtype=np.int64)
        companions = np.array([data.keys[c] for c in request.companions], dtype=np.int64)
        tokens, which = data._companion_tokens(reference, companions)
        observed = data._cooccurrences(reference, tokens, which, len(companions), data.segment)
        prepared.append((reference, companions, tokens, which, observed))
    results: dict[str, dict[str, tuple]] = {r.name: {} for r in requests}
    for number, control in enumerate(settings.controls):
        rng = np.random.default_rng([settings.seed, number])
        at_least = [np.zeros(len(p[1]), dtype=np.int64) for p in prepared]
        total = [np.zeros(len(p[1]), dtype=np.int64) for p in prepared]
        for _ in range(settings.permutations):
            shuffled = data._shuffled_segments(rng, control)
            for k, (reference, companions, tokens, which, observed) in enumerate(prepared):
                counts = data._cooccurrences(reference, tokens, which, len(companions), shuffled)
                at_least[k] += counts >= observed
                total[k] += counts
        for k, request in enumerate(requests):
            p_values = ((at_least[k] + 1) / (settings.permutations + 1)).tolist()
            results[request.name][control] = (total[k] / settings.permutations, p_values, stats.benjamini_hochberg(p_values))
    found: dict[str, list[Finding]] = {}
    for k, request in enumerate(requests):
        observed = prepared[k][4]
        first = settings.controls[0]
        rows = []
        for c, companion in enumerate(request.companions):
            if observed[c] < settings.min_cooccurrence:
                continue
            expected, p_values, q_values = results[request.name][first]
            failed = [ctl for ctl in settings.controls[1:] if results[request.name][ctl][2][c] > settings.alpha]
            status = ESTABLISHED if q_values[c] <= settings.alpha else OBSERVED
            rows.append(Finding(ASSOCIATION, companion, ",".join(failed), int(observed[c]), float(expected[c]),
                                p_values[c], q_values[c], status))  # fmt: skip
        found[request.name] = sorted(rows, key=lambda f: (f.status != ESTABLISHED, f.q_value, -f.support))
    return found


# --- Constraints and covariations in matrices ---------------------------------------------


def _p_value(observed: float, simulated: np.ndarray) -> float:
    return float((np.sum(simulated >= observed) + 1) / (len(simulated) + 1))


def constraints(analysis: Analysis, m: Matrix, settings: StatsSettings) -> list[Finding]:
    """Constraints between the optional parts of a matrix (SPEC §2.7), with a permutation test.

    Columns present in exactly the same rows form one group: inside a run of adjacent columns
    that is simply a block, not a constraint. A group made of several runs apart is an
    equivalence (من عباده … له: present or absent together). Between groups: exclusion (never
    together) and implication (one present only with the other). Each tested on at least
    `support_min` rows; p-values corrected within the matrix (Benjamini-Hochberg).
    """
    rows = m.rows
    if len(rows) < 2 * settings.support_min:
        return []
    groups: dict[tuple[bool, ...], list[int]] = {}
    for k, column in enumerate(m.columns):
        presence = tuple(cell is not None for cell in column.cells)
        if not column.is_pivot and 0 < sum(presence) < len(rows) and _concrete(analysis, m, k, settings.relative_min):
            groups.setdefault(presence, []).append(k)
    rng = np.random.default_rng([settings.seed, 7])
    tests: list[tuple[str, str, int, float]] = []

    def test(pa: np.ndarray, pb: np.ndarray, score) -> float:
        observed = score(pa, pb)
        simulated = np.array([score(pa, rng.permutation(pb)) for _ in range(settings.permutations)])
        return _p_value(observed, simulated)

    vectors = [(np.array(presence), columns) for presence, columns in groups.items()]
    for presence, columns in vectors:
        runs = _runs(columns)
        if len(runs) >= 2 and presence.sum() >= settings.support_min:
            p = test(presence, presence.copy(), lambda u, v: np.sum(u == v))
            what = " ⇔ ".join(_run_text(analysis, m, run) for run in runs)
            tests.append((what, EQUIVALENCE, int(presence.sum()), p))
    for x, (pa, ca) in enumerate(vectors):
        for pb, cb in vectors[x + 1 :]:
            both, only_a, only_b = int((pa & pb).sum()), int((pa & ~pb).sum()), int((~pa & pb).sum())
            a_text, b_text = _run_text(analysis, m, _runs(ca)[0]), _run_text(analysis, m, _runs(cb)[0])
            if both == 0 and pa.sum() >= settings.support_min and pb.sum() >= settings.support_min:
                tests.append((f"{a_text} / {b_text}", EXCLUSION, int(pa.sum() + pb.sum()),
                              test(pa, pb, lambda u, v: np.sum(~(u & v)))))  # fmt: skip
            elif both >= settings.support_min and only_b == 0 and only_a > 0:
                tests.append((f"{b_text} ⇒ {a_text}", IMPLICATION, both, test(pa, pb, lambda u, v: np.sum(~v | u))))
            elif both >= settings.support_min and only_a == 0 and only_b > 0:
                tests.append((f"{a_text} ⇒ {b_text}", IMPLICATION, both, test(pa, pb, lambda u, v: np.sum(~u | v))))
    if not tests:
        return []
    q_values = stats.benjamini_hochberg([p for *_, p in tests])
    found = [
        Finding(CONSTRAINT, what, kind, support, None, p, q, ESTABLISHED if q <= settings.alpha else OBSERVED)
        for (what, kind, support, p), q in zip(tests, q_values)
    ]
    return sorted(found, key=lambda f: (f.status != ESTABLISHED, f.q_value))


def _runs(columns: list[int]) -> list[list[int]]:
    runs: list[list[int]] = []
    for k in sorted(columns):
        if runs and runs[-1][-1] == k - 1:
            runs[-1].append(k)
        else:
            runs.append([k])
    return runs


def _run_text(analysis: Analysis, m: Matrix, run: list[int]) -> str:
    return " ".join(_filler(analysis, m, k) for k in run)


def _concrete(analysis: Analysis, m: Matrix, k: int, relative_min: float) -> bool:
    """A column one form fills (in at least `relative_min` of the rows where it is present): an element,
    not a mere position holding different words from row to row (Q37)."""
    forms = [analysis.rows[r].cells[c].form for r, c in zip(m.rows, m.columns[k].cells) if c is not None]
    return bool(forms) and max(forms.count(f) for f in set(forms)) / len(forms) >= relative_min


def _filler(analysis: Analysis, m: Matrix, k: int) -> str:
    forms = [analysis.rows[r].cells[c].text for r, c in zip(m.rows, m.columns[k].cells) if c is not None]
    common = max(set(forms), key=forms.count)
    return common + ("…" if len(set(forms)) > 1 else "")


def covariation(fillers: list[str | None], sides: list[int], settings: StatsSettings) -> tuple[float, float, float]:
    """(observed, expected, p) for a column: purity of the fillers within each form, forms permuted between rows."""
    present = [(f, s) for f, s in zip(fillers, sides) if f is not None]
    forms = np.array([f for f, _ in present])
    labels = np.array([s for _, s in present])

    def purity(lab: np.ndarray) -> int:
        total = 0
        for side in (0, 1):
            chosen = forms[lab == side]
            if len(chosen):
                values, counts = np.unique(chosen, return_counts=True)
                total += counts.max()
        return total

    rng = np.random.default_rng([settings.seed, 11])
    observed = purity(labels)
    simulated = np.array([purity(rng.permutation(labels)) for _ in range(settings.permutations)])
    return float(observed), float(simulated.mean()), _p_value(observed, simulated)


def status_label(status: str) -> str:
    from .labels import t

    return t(status)

