"""tokencount — a token count both parties can recompute.

Three checkable accounting properties:

  1. DETERMINISM    the count is a pure function of (text, merge list)
  2. BYTE CEILING   count <= utf-8 byte length — the bound that refutes an inflated claim
                    with no tokenizer, no merge list, and no cooperation from the counterparty
  3. MERGE MONOTONE extending the merge list never increases the count

MEASURE-ONLY BY DESIGN
----------------------
Nothing here settles, bills, refunds, or blocks. Every entry point returns a verdict; the caller
decides. See CLAIMS-MAP.md.
"""
from __future__ import annotations

from . import bpe, properties, verify
from .bpe import byte_length, count, dump_merges, encode, learn_merges, load_merges
from .properties import run_all
from .verify import Verdict, check_claim, reconcile

__all__ = [
    "bpe", "verify", "properties",
    "encode", "count", "byte_length", "load_merges", "dump_merges", "learn_merges",
    "Verdict", "check_claim", "reconcile", "run_all",
]

__version__ = "0.1.0"
