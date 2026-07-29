"""tokencount.properties — the three accounting properties, as runnable checks.

Each property is stated once and checked over randomised inputs, so a user can confirm on their
own machine that the encoder they are about to trust actually has the properties the README
claims. A property asserted in prose and never executed is a promise, not a guarantee.

    from tokencount.properties import run_all
    report = run_all(trials=500)
    assert report["ok"]

The randomisation is seeded and the seed is reported, so a failure is reproducible.
"""
from __future__ import annotations

import random
import string
from typing import Sequence

from .bpe import Pair, byte_length, count, learn_merges

_ALPHABET = string.ascii_lowercase + " " + string.digits + "áé漢🙂"


def _random_text(rng: random.Random, max_len: int = 60) -> str:
    return "".join(rng.choice(_ALPHABET) for _ in range(rng.randint(0, max_len)))


def check_determinism(rng: random.Random, merges: Sequence[Pair], trials: int) -> dict:
    """Property 1: the count is a pure function of (text, merges)."""
    failures = []
    for _ in range(trials):
        t = _random_text(rng)
        a, b, c = count(t, merges), count(t, merges), count(t, list(merges))
        if not (a == b == c):
            failures.append({"text": t, "counts": [a, b, c]})
    return {"property": "determinism",
            "statement": "count(text, merges) is a pure function of its arguments",
            "trials": trials, "failures": failures, "ok": not failures}


def check_byte_ceiling(rng: random.Random, merges: Sequence[Pair], trials: int) -> dict:
    """Property 2: count <= utf-8 byte length. The bound that refutes an inflated claim."""
    failures = []
    for _ in range(trials):
        t = _random_text(rng)
        n, ceiling = count(t, merges), byte_length(t)
        if n > ceiling:
            failures.append({"text": t, "count": n, "ceiling": ceiling})
    return {"property": "byte_ceiling",
            "statement": "count(text, merges) <= len(text.encode('utf-8'))",
            "trials": trials, "failures": failures, "ok": not failures}


def check_merge_monotone(rng: random.Random, merges: Sequence[Pair], trials: int) -> dict:
    """Property 3: extending the merge list never increases the count."""
    failures = []
    if len(merges) < 2:
        return {"property": "merge_monotone", "trials": 0, "failures": [],
                "ok": True, "note": "merge list too short to extend; check skipped",
                "statement": "count is non-increasing as merges are appended"}
    for _ in range(trials):
        t = _random_text(rng)
        k = rng.randint(1, len(merges) - 1)
        short, long = list(merges[:k]), list(merges)
        n_short, n_long = count(t, short), count(t, long)
        if n_long > n_short:
            failures.append({"text": t, "k": k, "short": n_short, "long": n_long})
    return {"property": "merge_monotone",
            "statement": "count is non-increasing as merges are appended",
            "trials": trials, "failures": failures, "ok": not failures}


def run_all(trials: int = 200, seed: int = 20260729,
            merges: Sequence[Pair] | None = None) -> dict:
    """Run all three property checks. Seeded, so a failure is reproducible."""
    rng = random.Random(seed)
    if merges is None:
        corpus = [_random_text(random.Random(seed + i), 120) for i in range(60)]
        merges = learn_merges(corpus, 40)
    results = [
        check_determinism(rng, merges, trials),
        check_byte_ceiling(rng, merges, trials),
        check_merge_monotone(rng, merges, trials),
    ]
    return {
        "artifact": "tokencount_properties",
        "seed": seed,
        "n_merges": len(merges),
        "results": results,
        "ok": all(r["ok"] for r in results),
    }


__all__ = ["check_determinism", "check_byte_ceiling", "check_merge_monotone", "run_all"]
