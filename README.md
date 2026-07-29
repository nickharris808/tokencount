# tokencount

**Your provider says 4,182 tokens. Your log says 3,916. Who is right?**

[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)
[![Dependencies](https://img.shields.io/badge/dependencies-none-brightgreen.svg)](pyproject.toml)

A token count both parties can recompute — and a refusal for claims that arithmetic rules out.

```bash
pip install tokencount-verify
```

> **Install name vs import name.** The distribution is `tokencount-verify`; the module you import
> is `tokencount`. PyPI rejects the bare name `tokencount` as too similar to an unrelated project
> (`token-count`), which collapses to the same name once separators are removed.

## Why this exists

Token billing disputes are unresolvable in practice because there is nothing to check against.
The provider has the tokenizer, you have a number on an invoice, and the conversation ends
there.

But one half of the dispute needs no tokenizer at all. In byte-level BPE, **every merge replaces
two symbols with one**, so the count starts at the UTF-8 byte length and only ever goes down. A
claim above the byte length is not a disagreement — it is arithmetic being wrong, and you can
show that with no cooperation from the counterparty whatsoever.

`tokencount` separates the two questions and never lets a pass on one be mistaken for a pass on
the other:

| | Question | What you need |
|---|---|---|
| **Q1** | Is the claim *arithmetically possible*? | Nothing. Just the text. |
| **Q2** | Does the claim match a *specific tokenizer*? | An agreed merge list. |

## Install

```bash
pip install tokencount-verify        # zero runtime dependencies
```

## 30-second quickstart

```bash
# Q1 — refute an impossible claim with no tokenizer at all. No setup needed.
tokencount verify "the quick brown fox" --claimed 99

# Q2 — settle it against an agreed merge list.
#      A corpus is one text per line; any text file will do.
printf 'the quick brown fox jumps over the lazy dog\nthe quick brown cat sleeps under the lazy sun\na quick brown fox and a lazy dog\nthe lazy dog sleeps and the quick fox jumps\n' > corpus.txt
tokencount learn corpus.txt --n 40 --out merges.txt
tokencount count "the quick brown fox" --merges merges.txt

# Confirm the encoder has the properties this README claims
tokencount properties
```

> The `--claimed` value in the worked examples below (4) is what *this* corpus produces. Your
> corpus will learn different merges and give a different count — `tokencount count` tells you
> what yours is.

## Worked example — refuting an inflated claim

No tokenizer. No merge list. No cooperation required.

```console
$ tokencount verify "the quick brown fox" --claimed 99
REFUSED  (question answered: arithmetic)
  claimed ........ 99
  byte ceiling ... 19
  -> claimed 99 exceeds the utf-8 byte length 19; a byte-level BPE count cannot exceed
     the byte length, because every merge replaces two symbols with one
```

A claim *within* the ceiling passes Q1 — and the output says plainly that Q2 was not answered,
so nobody mistakes it for a settlement:

```console
$ tokencount verify "the quick brown fox" --claimed 6
ACCEPTED  (question answered: arithmetic)
  claimed ........ 6
  byte ceiling ... 19
```

## Worked example — settling against an agreed tokenizer

```console
$ tokencount learn corpus.txt --n 40 --out merges.txt
learned 40 merges -> merges.txt

$ tokencount count "the quick brown fox" --merges merges.txt
tokens ......... 4
byte ceiling ... 19
merges used .... 40

$ tokencount verify "the quick brown fox" --claimed 4 --merges merges.txt
ACCEPTED  (question answered: arithmetic+tokenizer)
  claimed ........ 4
  byte ceiling ... 19
  computed ....... 4

$ tokencount verify "the quick brown fox" --claimed 7 --merges merges.txt
REFUSED  (question answered: arithmetic+tokenizer)
  claimed ........ 7
  byte ceiling ... 19
  computed ....... 4
  -> claimed 7 differs from the count computed under the supplied merge list (4)
     by more than the agreed tolerance (0)
```

## Reconciling three parties at once

```python
from tokencount import reconcile, count, learn_merges

corpus = [line.strip() for line in open("corpus.txt") if line.strip()]
merges = learn_merges(corpus, 40)

text = "the quick brown fox"
count(text, merges)            # 4 — what this corpus produces

r = reconcile(text, {"vendor": 4, "customer": 4, "auditor": 9}, merges=merges)

r["agreed"]                    # False
r["spread"]                    # 5
r["verdicts"]["auditor"]["ok"] # False  <- disagreement localised to one party
```

## The three properties, checkable on your machine

A property asserted in prose and never executed is a promise, not a guarantee. So they run:

```console
$ tokencount properties
tokencount properties   (seed 20260729, 40 learned merges)
  [ok ] determinism       200 trials   count(text, merges) is a pure function of its arguments
  [ok ] byte_ceiling      200 trials   count(text, merges) <= len(text.encode('utf-8'))
  [ok ] merge_monotone    200 trials   count is non-increasing as merges are appended

  RESULT: all properties hold
```

1. **Determinism** — same inputs, same count, any machine, any process.
2. **Byte ceiling** — the bound that makes an inflated claim refutable without a tokenizer.
3. **Merge monotone** — a vendor cannot raise your bill by adding merges, or lower it by
   removing them.

Seeded, so a failure is reproducible.

## Honest limits — read before you accuse anyone

- This implements **byte-level BPE with a priority-ordered merge list**, the family most
  contemporary tokenizers belong to. It is **not bit-identical to any particular vendor's
  tokenizer**: real tokenizers add pre-tokenization regexes, special tokens, and byte-fallback
  rules that differ between vendors.
- So: use Q1 freely — it is arithmetic and holds against every byte-level BPE tokenizer. Use Q2
  **only when you are running the counterparty's own merge list**. A Q2 mismatch under *your*
  merge list against *their* tokenizer means the merge lists differ, not that they are
  overcharging.
- `--tolerance` exists for the case where two parties agree on a merge list but not on
  pre-tokenization. It never rescues a claim above the byte ceiling; that bound is not
  negotiable.
- `learn` uses the standard most-frequent-pair rule with a deterministic byte-order tie-break.
  It is a real learner, not a toy, but it is not tuned to match any published vocabulary.

## What this does not do

`tokencount` **measures**. It never settles, bills, refunds, blocks, or writes a payment
record — every entry point returns a verdict and the caller decides. That boundary is deliberate
and enforced in CI (see [`CLAIMS-MAP.md`](CLAIMS-MAP.md)).

If you need the *enforcing* side — a metering path that refuses to settle a claimed count above
the computed count and binds both into a tamper-evident record — that is a separate,
commercially licensed product. See [CLAIMS-MAP.md](CLAIMS-MAP.md).

## Development

```bash
pip install -e ".[dev]"
python -m pytest -q          # 29 tests
tokencount properties        # the accounting properties
```

## License

Apache-2.0. See [LICENSE](LICENSE) and [CONTRIBUTING.md](CONTRIBUTING.md).

<!-- HONEST-SCOPE -->
## Honest scope — what a passing run proves, and what it does not

The two halves are inseparable. A tool that states only the first half is marketing.

**It proves:**

- a token count both parties can recompute from the same tokenizer and input
- that a claimed count above the UTF-8 byte length is impossible for a byte-level BPE

**It does NOT prove:**

- which tokenizer your provider actually used — you supply that
- that a count within the ceiling is CORRECT; the ceiling refutes, it does not confirm
- anything about billing terms, only about arithmetic

Full CLI reference, generated from `--help`: [`docs/CLI.md`](docs/CLI.md)
<!-- /HONEST-SCOPE -->

**Citing this?** Metadata is in [CITATION.cff](CITATION.cff) — GitHub's "Cite this repository" button reads it directly.

<!-- PORTFOLIO -->
---

## The rest of the portfolio

25 artifacts, one idea: **a measurement you cannot check is a press release.** Every tool
here reports; none of them gates.

**Tools**

| | |
|---|---|
| [`abstain-bench`](https://github.com/nickharris808/abstain-bench) | how often does a verifier pass input it could not check? |
| [`evidence`](https://github.com/nickharris808/evidence) | run the whole portfolio over your repo — the weakest leg, never the mean |
| [`floorgen`](https://github.com/nickharris808/floorgen) | what must your system remember? an exact lower bound |
| [`formal-proof-mcp`](https://github.com/nickharris808/formal-proof-mcp) | a proof kernel for your coding agent |
| [`gatecount`](https://github.com/nickharris808/gatecount) | exactly how many states does removing this check admit? |
| [`gridlock`](https://github.com/nickharris808/gridlock) | certify a wait-for relation cannot wedge |
| [`honestbench`](https://github.com/nickharris808/honestbench) | measure your CI's escape rate |
| [`kvleak`](https://github.com/nickharris808/kvleak) | cross-tenant leak scanner |
| [`kvprobe`](https://github.com/nickharris808/kvprobe) | model-substitution detector with a measured FPR |
| [`preregister`](https://github.com/nickharris808/preregister) | refuses to seal a plan whose conclusion is already fixed |
| [`proof-carrying-ci`](https://github.com/nickharris808/proof-carrying-ci) | the whole portfolio as one CI check, with SARIF |
| [`proof-to-code-drift`](https://github.com/nickharris808/proof-to-code-drift) | fail the build when the proof stops matching |
| [`sf-verify`](https://github.com/nickharris808/sf-verify) | re-derive admission decisions offline |
| [`signoff-cert`](https://github.com/nickharris808/signoff-cert) | certificates that carry their own false-pass bound |
| [`tokencount`](https://github.com/nickharris808/tokencount) | a token count both parties can recompute ← you are here |

**Benchmarks** — each recomputes one of our own published numbers from its certificate

| | |
|---|---|
| [`illusion-bench`](https://github.com/nickharris808/illusion-bench) | how many broken kernels does your oracle admit? |
| [`kv-reuse-econ-bench`](https://github.com/nickharris808/kv-reuse-econ-bench) | recompute our economics headline |
| [`llm-tenant-isolation-bench`](https://github.com/nickharris808/llm-tenant-isolation-bench) | recompute our isolation figures |

**Datasets**

| | |
|---|---|
| [`abstain-corpus`](https://huggingface.co/datasets/nickh007/abstain-corpus) | 32 inputs a verifier must NOT pass |
| [`kv-reuse-econ-traces`](https://huggingface.co/datasets/nickh007/kv-reuse-econ-traces) | per-workload reuse accounting + the closed form |
| [`kv-tenant-isolation-bench`](https://huggingface.co/datasets/nickh007/kv-tenant-isolation-bench) | isolation observations, uninterpretable rows included |
| [`llm-precision-fingerprints`](https://huggingface.co/datasets/nickh007/llm-precision-fingerprints) | precision-labelled logprobs with a negative control |

**Try it in a browser** — no install, no GPU

| | |
|---|---|
| [`negative-results-atlas`](https://huggingface.co/spaces/nickh007/negative-results-atlas) | ten claims we took back |
| [`tenant-leak-demo`](https://huggingface.co/spaces/nickh007/tenant-leak-demo) | the residency calculator |
| [`wait-for-visualiser`](https://huggingface.co/spaces/nickh007/wait-for-visualiser) | paste a wait-for graph, see the cycle |

### Documentation

Everything above, explained in one place: **<https://nickharris808.github.io/evidence-docs/>** —
the [tutorial](https://nickharris808.github.io/evidence-docs/start/tutorial/),
[what this proves and what it does not](https://nickharris808.github.io/evidence-docs/concepts/what-this-proves/),
and a [CLI reference](https://nickharris808.github.io/evidence-docs/reference/cli/) generated by
running `--help` on every published command.

### The commercial edition

Everything above is **measure-only** and Apache-2.0: it tells you what is true and never acts on
it. The **enforcement** side — binding a partition key at the admission decision, the compiled gate
corpus, and the certificate-*issuing* faucet — is covered by filed patents and licensed separately.

**Reading is free. Enforcing is licensed.**
<!-- /PORTFOLIO -->
