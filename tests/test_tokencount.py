"""Test suite for tokencount. The three properties are tested as properties, not as examples."""
from __future__ import annotations

import random

import pytest

from tokencount import (
    byte_length,
    check_claim,
    count,
    dump_merges,
    encode,
    learn_merges,
    load_merges,
    reconcile,
    run_all,
)
from tokencount.properties import check_byte_ceiling, check_determinism, check_merge_monotone

CORPUS = [
    "the quick brown fox jumps over the lazy dog",
    "the quick brown cat sleeps under the lazy sun",
    "a quick brown fox and a lazy dog",
    "the lazy dog sleeps and the quick fox jumps",
] * 5


# ---------------------------------------------------------------- encoder basics


def test_empty_text_is_zero_tokens():
    assert count("", []) == 0
    assert encode("", []) == []


def test_no_merges_is_the_byte_count():
    t = "hello"
    assert count(t, []) == byte_length(t) == 5


def test_multibyte_counts_bytes_not_characters():
    # A single emoji is 4 utf-8 bytes; with no merges that is 4 symbols, not 1.
    assert byte_length("🙂") == 4
    assert count("🙂", []) == 4


def test_a_single_merge_reduces_the_count_by_the_number_of_occurrences():
    t = "abab"
    m = [(b"a", b"b")]
    assert count(t, []) == 4
    assert count(t, m) == 2          # "ab" "ab"


def test_encode_returns_the_merged_symbols():
    assert encode("abab", [(b"a", b"b")]) == [b"ab", b"ab"]


def test_merge_priority_is_list_order_not_scan_order():
    t = "abc"
    # (b,c) first -> ["a", "bc"];  (a,b) first -> ["ab", "c"]. Both length 2, different symbols.
    assert encode(t, [(b"b", b"c"), (b"a", b"b")]) == [b"a", b"bc"]
    assert encode(t, [(b"a", b"b"), (b"b", b"c")]) == [b"ab", b"c"]


# ---------------------------------------------------------------- the three properties


def test_property_determinism():
    m = learn_merges(CORPUS, 30)
    r = check_determinism(random.Random(1), m, 300)
    assert r["ok"], r["failures"][:3]


def test_property_byte_ceiling():
    m = learn_merges(CORPUS, 30)
    r = check_byte_ceiling(random.Random(2), m, 300)
    assert r["ok"], r["failures"][:3]


def test_property_merge_monotone():
    m = learn_merges(CORPUS, 30)
    r = check_merge_monotone(random.Random(3), m, 300)
    assert r["ok"], r["failures"][:3]


def test_run_all_properties_hold():
    rep = run_all(trials=150)
    assert rep["ok"], rep
    assert len(rep["results"]) == 3


def test_byte_ceiling_holds_for_adversarial_multibyte_input():
    m = learn_merges(["漢字漢字漢字", "🙂🙂🙂"], 10)
    for t in ["漢字", "🙂🙂", "áéáé", "", "a"]:
        assert count(t, m) <= byte_length(t)


# ---------------------------------------------------------------- verification


def test_claim_above_the_byte_ceiling_is_refused_without_a_tokenizer():
    v = check_claim("hello", claimed=99)
    assert not v.ok
    assert v.question == "arithmetic"
    assert "exceeds the utf-8 byte length" in v.reasons[0]


def test_claim_within_the_ceiling_passes_the_arithmetic_question():
    v = check_claim("hello", claimed=3)
    assert v.ok
    assert v.question == "arithmetic"
    assert v.computed is None       # no merge list supplied -> Q2 not answered


def test_negative_claim_is_refused():
    assert not check_claim("hello", claimed=-1).ok


def test_claim_matching_the_merge_list_is_accepted():
    m = learn_merges(CORPUS, 30)
    t = "the quick brown fox"
    v = check_claim(t, claimed=count(t, m), merges=m)
    assert v.ok
    assert v.question == "arithmetic+tokenizer"
    assert v.computed == count(t, m)


def test_claim_mismatching_the_merge_list_is_refused():
    m = learn_merges(CORPUS, 30)
    t = "the quick brown fox"
    v = check_claim(t, claimed=count(t, m) + 1, merges=m)
    assert not v.ok
    assert "differs from the count computed" in v.reasons[-1]


def test_tolerance_permits_agreed_slack_but_not_the_ceiling():
    m = learn_merges(CORPUS, 30)
    t = "the quick brown fox"
    n = count(t, m)
    assert check_claim(t, n + 2, merges=m, tolerance=2).ok
    # tolerance never rescues a claim above the byte ceiling
    assert not check_claim(t, byte_length(t) + 1, merges=m, tolerance=1000).ok


def test_verdict_is_truthy_and_explains_itself():
    v = check_claim("hello", claimed=3)
    assert bool(v) is True
    assert "ACCEPTED" in v.explain()
    bad = check_claim("hello", claimed=99)
    assert bool(bad) is False
    assert "REFUSED" in bad.explain()


# ---------------------------------------------------------------- reconciliation


def test_reconcile_localises_disagreement():
    m = learn_merges(CORPUS, 30)
    t = "the quick brown fox"
    n = count(t, m)
    r = reconcile(t, {"vendor": n, "customer": n, "auditor": n + 5}, merges=m)
    assert r["agreed"] is False
    assert r["spread"] == 5
    assert r["verdicts"]["vendor"]["ok"] is True
    assert r["verdicts"]["auditor"]["ok"] is False
    assert r["all_accepted"] is False


def test_reconcile_when_everyone_agrees():
    m = learn_merges(CORPUS, 30)
    t = "the quick brown fox"
    n = count(t, m)
    r = reconcile(t, {"vendor": n, "customer": n}, merges=m)
    assert r["agreed"] is True
    assert r["spread"] == 0
    assert r["all_accepted"] is True


# ---------------------------------------------------------------- merge list io


def test_merges_roundtrip_through_the_on_disk_form():
    m = learn_merges(CORPUS, 20)
    assert load_merges(dump_merges(m).splitlines()) == m


def test_merges_roundtrip_when_a_symbol_contains_a_space():
    """Regression: 'the' + ' ' is one of the first merges any English corpus learns, and a bare
    space separator makes that line ambiguous. Caught by the round-trip test."""
    m = [(b"the", b" "), (b" ", b" "), (b"a", b"b")]
    assert load_merges(dump_merges(m).splitlines()) == m


def test_merges_roundtrip_when_a_symbol_contains_a_percent():
    m = [(b"100%", b" "), (b"%", b"%")]
    assert load_merges(dump_merges(m).splitlines()) == m


def test_merges_roundtrip_for_multibyte_symbols():
    m = [("漢".encode(), "字".encode()), ("🙂".encode(), b"!")]
    assert load_merges(dump_merges(m).splitlines()) == m


def test_load_merges_rejects_a_truncated_escape():
    with pytest.raises(ValueError):
        load_merges(["a%2 b"])


def test_load_merges_ignores_comments_and_blanks():
    text = "# a comment\n\na b\nc d\n"
    assert load_merges(text.splitlines()) == [(b"a", b"b"), (b"c", b"d")]


def test_load_merges_rejects_a_malformed_line():
    with pytest.raises(ValueError):
        load_merges(["a b c"])


def test_learn_merges_is_deterministic():
    assert learn_merges(CORPUS, 25) == learn_merges(CORPUS, 25)


def test_learn_merges_stops_when_no_pair_repeats():
    # A corpus with no repeated pair cannot yield merges with frequency >= 2.
    assert learn_merges(["abcdef"], 50) == []


# ---------------------------------------------------------------- CLI error paths
#
# Regression: `tokencount learn corpus.txt` on a missing file produced a raw traceback, and the
# README's quickstart never created the corpus, so a new user's first command crashed.


def test_learn_reports_a_missing_corpus_cleanly(tmp_path, capsys):
    from tokencount.cli import main
    with pytest.raises(SystemExit) as exc:
        main(["learn", str(tmp_path / "nope.txt")])
    assert "corpus not found" in str(exc.value)
    assert "one text per line" in str(exc.value)


def test_learn_reports_an_empty_corpus_cleanly(tmp_path):
    from tokencount.cli import main
    p = tmp_path / "empty.txt"
    p.write_text("\n\n  \n")
    with pytest.raises(SystemExit) as exc:
        main(["learn", str(p)])
    assert "empty" in str(exc.value)


def test_count_reports_a_missing_merge_list_cleanly(tmp_path):
    from tokencount.cli import main
    with pytest.raises(SystemExit) as exc:
        main(["count", "hello", "--merges", str(tmp_path / "nope.txt")])
    assert "merge list not found" in str(exc.value)
    assert "tokencount learn" in str(exc.value)      # tells the user how to make one


def test_count_reports_a_malformed_merge_list_cleanly(tmp_path):
    from tokencount.cli import main
    p = tmp_path / "bad.txt"
    p.write_text("a b c\n")
    with pytest.raises(SystemExit) as exc:
        main(["count", "hello", "--merges", str(p)])
    assert "malformed merge list" in str(exc.value)


def test_readme_quickstart_corpus_line_actually_produces_a_usable_corpus(tmp_path):
    """The README's quickstart printf must yield a corpus `learn` accepts."""
    from tokencount.cli import main
    corpus = tmp_path / "corpus.txt"
    corpus.write_text(
        "the quick brown fox jumps over the lazy dog\n"
        "the quick brown cat sleeps under the lazy sun\n"
        "a quick brown fox and a lazy dog\n"
        "the lazy dog sleeps and the quick fox jumps\n")
    out = tmp_path / "merges.txt"
    assert main(["learn", str(corpus), "--n", "40", "--out", str(out)]) == 0
    assert out.exists() and out.read_text().strip()
    assert main(["count", "the quick brown fox", "--merges", str(out)]) == 0
