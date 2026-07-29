# Contributing to tokencount

## The one rule

**tokencount measures. It never settles.**

No entry point may settle, bill, refund, block a payment, or write a payment record. Every
function returns a verdict; the caller decides. This boundary is enforced in CI. A pull request
that adds an actuation path will be rejected regardless of usefulness — the correct home for
that behaviour is a downstream billing system that consumes our verdicts.

## The second rule

**Keep Q1 and Q2 separate.**

Q1 (is the claim arithmetically possible?) needs no tokenizer and holds against every
byte-level BPE tokenizer. Q2 (does it match a specific tokenizer?) holds only under an agreed
merge list. Any change that lets a Q1 pass be mistaken for a Q2 pass is a correctness bug, not
a UX simplification.

## The third rule

**A property ships with a runnable check.**

The three accounting properties live in `src/tokencount/properties.py` and run over seeded
random inputs. If you add a property, add its check. If you change the encoder, the existing
checks must still pass — and if they do not, the encoder is wrong, not the checks.

## Practicalities

```bash
pip install -e ".[dev]"
python -m pytest -q
tokencount properties
```

- Zero runtime dependencies. Hard constraint.
- Python 3.9+.
- The merge-file format percent-escapes symbols. This is not decoration: `"the" + " "` is among
  the first merges any English corpus learns, and a bare space separator makes that line
  ambiguous. A round-trip test caught it. Do not "simplify" it back.

## Licence

By contributing you agree your contributions are licensed under Apache-2.0.
