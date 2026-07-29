# CLAIMS-MAP — tokencount

**Tag: CLEAN. Licence: Apache-2.0.**

This file exists so the CLEAN tag is *auditable* rather than asserted.

## The line

Every independent claim in the corresponding filed specification terminates in a **physical
actuation** step. For the metering family the recited step is *writing a settlement record to a
durable store only upon a claimed count that is not refused* — and withholding it otherwise.

`tokencount` computes and refuses. It writes no settlement record and withholds none.

## Claims approached, and the step not performed

| Filed claim family | What it recites | What tokencount does instead |
|---|---|---|
| Deterministic token accounting as a settlement precondition | *(a)* compute a count by a procedure established deterministic; *(b)* receive a claimed count; *(c)* refuse a settlement in which the claimed count exceeds the computed count; **(d) write a settlement record to a durable store only upon a claimed count not refused by (c)** | Performs (a), (b) and the *comparison* in (c). Does **not** perform (d): there is no durable store, no settlement, and no record. `check_claim` returns a `Verdict` object. |
| Byte-length bound as the detectability mechanism | the computed count is bounded above by the byte length, whereby an inflated claim is detectable without re-executing the procedure | Implemented and property-checked. It is a bound, not an actuation. |
| Merge monotonicity | the count is monotone in the merge set, whereby it cannot be altered by adding or removing merges | Implemented and property-checked. |
| Binding count and claim into a chain | the computed and claimed counts are bound into an append-only chain, whereby a dispute is resolved by recomputation | **Not implemented here.** `reconcile` reports a disagreement; it writes nothing durable and binds nothing into a chain. |

## Enforcement

`oss/tools/check_measure_only.py` scans every CLEAN-tagged artifact and fails the build on an
actuation construct. Exit codes are deliberately not flagged — exiting non-zero to *report* a
refusal is not the claimed actuation.

## Why Apache-2.0

Apache-2.0 §3 grants an express patent licence to the claims a published implementation
practices. Because tokencount practices none of the filed claims, the licence grants nothing
away, and the package can carry the most permissive licence available.

## The commercial boundary, stated plainly

tokencount tells you **whether a claimed count is possible** and **what the count is under an
agreed merge list**.

It does not settle on the strength of that. A metering path that refuses to write a settlement
record when the claimed count exceeds the computed count, and binds both into a tamper-evident
chain so a dispute is resolved by recomputation rather than by trust, is a separate,
commercially licensed product covered by the filed claims above.
