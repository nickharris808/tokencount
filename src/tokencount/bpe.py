"""tokencount.bpe — a byte-level BPE encoder with three checkable accounting properties.

WHY A SEPARATE ENCODER
----------------------
This is not a faster tokenizer and does not try to be. It is an encoder whose *accounting*
properties are stated and checkable, so that two parties who disagree about a token bill can
recompute the number instead of arguing about it.

THE THREE PROPERTIES
--------------------
1. DETERMINISM      the count is a pure function of (text, merge list). Same inputs, same count,
                    on any machine, in any process, in any order.
2. BYTE CEILING     count <= len(utf8_bytes). Every merge replaces two symbols with one, so the
                    count starts at the byte length and only ever decreases. This is the bound
                    that makes an inflated claim detectable WITHOUT re-running the encoder.
3. MERGE MONOTONE   extending the merge list (appending lower-priority merges) never increases
                    the count. So a vendor cannot raise your bill by adding merges, and cannot
                    lower it by removing them.

Property 2 is the load-bearing one commercially: a counterparty who claims more tokens than the
input has bytes is refuted by arithmetic alone.

SCOPE, STATED HONESTLY
----------------------
* This implements *byte-level BPE with a priority-ordered merge list*, the family used by most
  contemporary tokenizers. It is NOT bit-identical to any particular vendor's tokenizer: real
  tokenizers add a pre-tokenization regex, special tokens, and byte-fallback rules that differ
  between vendors and are not part of the accounting properties above.
* Therefore: use this to check that a claimed count is ARITHMETICALLY POSSIBLE (property 2) and
  to compute a reproducible count under an AGREED merge list. Do not use it to assert that a
  vendor's own count is wrong unless you are running the vendor's own merge list.
* `verify` is explicit about which of those two questions it is answering.
"""
from __future__ import annotations

from typing import Iterable, Sequence

Pair = tuple[bytes, bytes]


def _pairs(symbols: Sequence[bytes]) -> set[Pair]:
    return {(symbols[i], symbols[i + 1]) for i in range(len(symbols) - 1)}


def encode(text: str, merges: Sequence[Pair]) -> list[bytes]:
    """Encode ``text`` to a list of byte-symbols under a priority-ordered ``merges`` list.

    Priority is the index in ``merges``: earlier means higher priority. The algorithm repeatedly
    applies the single highest-priority merge present anywhere in the sequence, which is the
    standard BPE rule and is what makes the result independent of scan order.
    """
    if not text:
        return []
    symbols: list[bytes] = [bytes([b]) for b in text.encode("utf-8")]
    if not merges:
        return symbols

    rank = {pair: i for i, pair in enumerate(merges)}

    while len(symbols) > 1:
        present = _pairs(symbols)
        best: Pair | None = None
        best_rank = None
        for p in present:
            r = rank.get(p)
            if r is not None and (best_rank is None or r < best_rank):
                best, best_rank = p, r
        if best is None:
            break

        a, b = best
        merged: list[bytes] = []
        i = 0
        while i < len(symbols):
            if i < len(symbols) - 1 and symbols[i] == a and symbols[i + 1] == b:
                merged.append(a + b)
                i += 2
            else:
                merged.append(symbols[i])
                i += 1
        symbols = merged
    return symbols


def count(text: str, merges: Sequence[Pair] = ()) -> int:
    """The token count. A pure function of its arguments — property 1."""
    return len(encode(text, merges))


def byte_length(text: str) -> int:
    """The utf-8 byte length: the ceiling from property 2."""
    return len(text.encode("utf-8"))


def _esc(sym: bytes) -> str:
    """Percent-escape a symbol so the space separator is unambiguous.

    The conventional ``<a> <b>`` merge-file format uses a bare space separator, which is
    AMBIGUOUS the moment a symbol itself contains a space — and in byte-level BPE that happens
    almost immediately, because ``"the" + " "`` is one of the first merges any English corpus
    learns. A round-trip test caught exactly that case here.

    So: ``%`` and space are percent-escaped, and every byte outside printable ASCII is escaped
    too. Readable for ordinary symbols, unambiguous for all of them.
    """
    out = []
    for byte in sym:
        if byte == 0x25:           # '%'
            out.append("%25")
        elif byte == 0x20:         # ' '
            out.append("%20")
        elif 0x21 <= byte <= 0x7E:
            out.append(chr(byte))
        else:
            out.append(f"%{byte:02X}")
    return "".join(out)


def _unesc(text: str) -> bytes:
    out = bytearray()
    i = 0
    while i < len(text):
        ch = text[i]
        if ch == "%":
            if i + 2 >= len(text):
                raise ValueError(f"truncated percent-escape in merge symbol: {text!r}")
            try:
                out.append(int(text[i + 1:i + 3], 16))
            except ValueError as exc:
                raise ValueError(f"bad percent-escape in merge symbol: {text!r}") from exc
            i += 3
        else:
            out.append(ord(ch))
            i += 1
    return bytes(out)


def load_merges(lines: Iterable[str]) -> list[Pair]:
    """Parse a merge list in the ``<a> <b>`` per-line form, with percent-escaped symbols.

    Blank lines and ``#`` comments are ignored. See ``_esc`` for why symbols are escaped rather
    than written raw.
    """
    out: list[Pair] = []
    for raw in lines:
        line = raw.rstrip("\n")
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        parts = line.split(" ")
        if len(parts) != 2:
            raise ValueError(
                f"malformed merge line (expected two space-separated escaped symbols): {line!r}")
        a, b = parts
        out.append((_unesc(a), _unesc(b)))
    return out


def dump_merges(merges: Sequence[Pair]) -> str:
    """Render a merge list to the on-disk form. ``load_merges(dump_merges(m)) == m`` always."""
    return "".join(f"{_esc(a)} {_esc(b)}\n" for a, b in merges)


def learn_merges(corpus: Sequence[str], n_merges: int) -> list[Pair]:
    """Learn a merge list from a corpus by the standard most-frequent-pair rule.

    Included so the package is usable end to end without shipping someone else's vocabulary,
    and so the property tests have a realistic merge list to run against. Ties are broken by
    the pair's byte ordering, which keeps learning deterministic — an arbitrary tie-break would
    silently violate property 1 for the learned list.
    """
    seqs: list[list[bytes]] = [[bytes([b]) for b in s.encode("utf-8")] for s in corpus]
    merges: list[Pair] = []

    for _ in range(n_merges):
        freq: dict[Pair, int] = {}
        for sym in seqs:
            for i in range(len(sym) - 1):
                p = (sym[i], sym[i + 1])
                freq[p] = freq.get(p, 0) + 1
        if not freq:
            break
        best = max(freq.items(), key=lambda kv: (kv[1], kv[0]))[0]
        if freq[best] < 2:
            break
        merges.append(best)

        a, b = best
        new_seqs = []
        for sym in seqs:
            out: list[bytes] = []
            i = 0
            while i < len(sym):
                if i < len(sym) - 1 and sym[i] == a and sym[i + 1] == b:
                    out.append(a + b)
                    i += 2
                else:
                    out.append(sym[i])
                    i += 1
            new_seqs.append(out)
        seqs = new_seqs
    return merges


__all__ = ["encode", "count", "byte_length", "load_merges", "dump_merges", "learn_merges", "Pair"]
