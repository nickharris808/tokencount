"""tokencount.cli — the command-line surface.

    tokencount count   TEXT|-  [--merges FILE]        compute the count
    tokencount verify  TEXT|-  --claimed N [--merges FILE] [--tolerance T]
    tokencount learn   CORPUS_FILE --n 200 [--out FILE]
    tokencount properties [--trials 200] [--seed N]   run the three property checks

Every subcommand PRINTS a verdict. None of them settles, bills, refunds, or blocks anything.
"""
from __future__ import annotations

import argparse
import json
import sys

from . import __version__
from .bpe import byte_length, count, dump_merges, learn_merges, load_merges
from .properties import run_all
from .verify import check_claim


def _text(arg: str) -> str:
    if arg == "-":
        return sys.stdin.read()
    return arg


def _merges(path: str | None):
    if not path:
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            return load_merges(fh)
    except FileNotFoundError:
        raise SystemExit(
            f"merge list not found: {path}\n"
            f"  Create one with:  tokencount learn <corpus.txt> --n 40 --out {path}")
    except ValueError as exc:
        raise SystemExit(f"malformed merge list {path}: {exc}")


def _cmd_count(a) -> int:
    text = _text(a.text)
    m = _merges(a.merges) or []
    n = count(text, m)
    print(f"tokens ......... {n}")
    print(f"byte ceiling ... {byte_length(text)}")
    print(f"merges used .... {len(m)}")
    if not m:
        print("note: no merge list supplied, so this is the raw utf-8 byte count "
              "(the ceiling, not a tokenizer count)")
    return 0


def _cmd_verify(a) -> int:
    text = _text(a.text)
    v = check_claim(text, a.claimed, _merges(a.merges), a.tolerance)
    print(v.explain())
    return 0 if v.ok else 1


def _cmd_learn(a) -> int:
    try:
        with open(a.corpus, encoding="utf-8") as fh:
            corpus = [ln.rstrip("\n") for ln in fh if ln.strip()]
    except FileNotFoundError:
        raise SystemExit(
            f"corpus not found: {a.corpus}\n"
            f"  A corpus is one text per line. To make a small one:\n"
            f"    printf 'the quick brown fox\\nthe lazy dog\\n' > {a.corpus}")
    if not corpus:
        raise SystemExit(f"corpus {a.corpus} is empty; nothing to learn from")
    m = learn_merges(corpus, a.n)
    out = dump_merges(m)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as fh:
            fh.write(out)
        print(f"learned {len(m)} merges -> {a.out}")
    else:
        sys.stdout.write(out)
    return 0


def _cmd_properties(a) -> int:
    rep = run_all(trials=a.trials, seed=a.seed)
    if a.json:
        print(json.dumps(rep, indent=2))
        return 0 if rep["ok"] else 1
    print(f"tokencount properties   (seed {rep['seed']}, {rep['n_merges']} learned merges)")
    for r in rep["results"]:
        mark = "ok " if r["ok"] else "FAIL"
        print(f"  [{mark}] {r['property']:<16} {r['trials']:>4} trials   {r['statement']}")
        for f in r["failures"][:3]:
            print(f"         counterexample: {f}")
    print(f"\n  RESULT: {'all properties hold' if rep['ok'] else 'A PROPERTY FAILED'}")
    return 0 if rep["ok"] else 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="tokencount",
        description="a token count both parties can recompute (measure-only)")
    ap.add_argument("--version", action="version", version=f"tokencount {__version__}")
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("count", help="compute the token count")
    c.add_argument("text", help="the text, or - for stdin")
    c.add_argument("--merges")
    c.set_defaults(fn=_cmd_count)

    v = sub.add_parser("verify", help="check a claimed count")
    v.add_argument("text", help="the text, or - for stdin")
    v.add_argument("--claimed", type=int, required=True)
    v.add_argument("--merges")
    v.add_argument("--tolerance", type=int, default=0)
    v.set_defaults(fn=_cmd_verify)

    l = sub.add_parser("learn", help="learn a merge list from a corpus")
    l.add_argument("corpus")
    l.add_argument("--n", type=int, default=200)
    l.add_argument("--out")
    l.set_defaults(fn=_cmd_learn)

    p = sub.add_parser("properties", help="run the three accounting property checks")
    p.add_argument("--trials", type=int, default=200)
    p.add_argument("--seed", type=int, default=20260729)
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=_cmd_properties)

    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
