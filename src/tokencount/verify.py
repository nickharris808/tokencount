"""tokencount.verify — refuse a claimed token count that arithmetic rules out.

TWO DIFFERENT QUESTIONS, KEPT SEPARATE
--------------------------------------
A dispute about a token bill is really two questions, and conflating them is how these arguments
go nowhere:

  Q1. Is the claimed count ARITHMETICALLY POSSIBLE?
      Answerable with no tokenizer at all. A byte-level BPE count can never exceed the utf-8
      byte length of the input, because every merge replaces two symbols with one. A claim above
      the byte ceiling is refuted outright — no merge list, no vendor cooperation, no trust.

  Q2. Does the claimed count MATCH a specific agreed tokenizer?
      Answerable only against that tokenizer's own merge list. Under an agreed merge list both
      parties compute the same number and the dispute ends.

`check_claim` answers Q1 always, and Q2 only when you supply a merge list. It labels which
question it answered, so a Q1 pass is never mistaken for a Q2 pass.

WHAT IT DOES NOT DO
-------------------
It refuses a *claim*. It does not settle, bill, refund, or block anything — it returns a verdict
and the caller decides. See CLAIMS-MAP.md.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from .bpe import Pair, byte_length, count


@dataclass
class Verdict:
    ok: bool
    question: str                 # "arithmetic" or "arithmetic+tokenizer"
    claimed: int
    byte_ceiling: int
    computed: int | None = None   # None when no merge list was supplied
    reasons: list[str] = field(default_factory=list)

    def __bool__(self) -> bool:
        return self.ok

    def explain(self) -> str:
        head = "ACCEPTED" if self.ok else "REFUSED"
        lines = [f"{head}  (question answered: {self.question})",
                 f"  claimed ........ {self.claimed}",
                 f"  byte ceiling ... {self.byte_ceiling}"]
        if self.computed is not None:
            lines.append(f"  computed ....... {self.computed}")
        for r in self.reasons:
            lines.append(f"  -> {r}")
        return "\n".join(lines)


def check_claim(text: str,
                claimed: int,
                merges: Sequence[Pair] | None = None,
                tolerance: int = 0) -> Verdict:
    """Check a claimed token count against the byte ceiling and, optionally, a merge list.

    ``tolerance`` allows a stated slack in the Q2 comparison, for the case where the two parties
    agree on a merge list but not on pre-tokenization details. It has no effect on Q1: the byte
    ceiling is arithmetic and is not negotiable.
    """
    ceiling = byte_length(text)
    reasons: list[str] = []
    ok = True

    if claimed < 0:
        ok = False
        reasons.append("a negative count is not a count")

    if claimed > ceiling:
        ok = False
        reasons.append(
            f"claimed {claimed} exceeds the utf-8 byte length {ceiling}; a byte-level BPE count "
            f"cannot exceed the byte length, because every merge replaces two symbols with one"
        )

    if merges is None:
        return Verdict(ok=ok, question="arithmetic", claimed=claimed,
                       byte_ceiling=ceiling, reasons=reasons)

    computed = count(text, merges)
    if abs(claimed - computed) > tolerance:
        ok = False
        reasons.append(
            f"claimed {claimed} differs from the count computed under the supplied merge list "
            f"({computed}) by more than the agreed tolerance ({tolerance})"
        )
    return Verdict(ok=ok, question="arithmetic+tokenizer", claimed=claimed,
                   byte_ceiling=ceiling, computed=computed, reasons=reasons)


def reconcile(text: str, claims: dict[str, int],
              merges: Sequence[Pair] | None = None) -> dict:
    """Reconcile several parties' claims about one input.

    Returns the per-party verdicts plus the spread, so a disagreement is localised to the parties
    that disagree rather than reported as a single opaque failure.
    """
    verdicts = {who: check_claim(text, n, merges) for who, n in claims.items()}
    values = sorted(set(claims.values()))
    return {
        "artifact": "tokencount_reconciliation",
        "byte_ceiling": byte_length(text),
        "computed": count(text, merges) if merges is not None else None,
        "n_parties": len(claims),
        "agreed": len(values) == 1,
        "spread": (max(values) - min(values)) if values else 0,
        "verdicts": {who: {"ok": v.ok, "claimed": v.claimed, "reasons": v.reasons}
                     for who, v in verdicts.items()},
        "all_accepted": all(v.ok for v in verdicts.values()),
    }


__all__ = ["Verdict", "check_claim", "reconcile"]
