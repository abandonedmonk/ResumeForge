"""Unit tests for LaTeX escaping / number-preservation validators."""
from __future__ import annotations

from app.utils import validator as v


def test_escape_latex_specials():
    out = v.escape_latex("a & b % c $ d # e _ f { g } h")
    assert r"\&" in out and r"\%" in out and r"\$" in out
    assert r"\#" in out and r"\_" in out and r"\{" in out and r"\}" in out


def test_escape_latex_backslash_and_caret():
    out = v.escape_latex("x \\ y ~ z ^")
    assert r"\textbackslash{}" in out
    assert r"\textasciitilde{}" in out
    assert r"\textasciicircum{}" in out


def test_normalize_latex_text_smart_punctuation():
    assert v.normalize_latex_text("“smart” — dash ’s") == '"smart" - dash \'s'


def test_extract_numbers():
    assert v.extract_numbers(["latency 25ms over 2.5 runs"]) == {"25", "2.5"}


def test_preserves_numbers():
    assert v.preserves_numbers(["improved 25%"], ["boosted by 25% overall"])
    assert not v.preserves_numbers(["25"], ["thirty"])
    assert v.preserves_numbers(["no metric"], ["still no metric"])  # nothing to preserve


def test_count_is_valid():
    assert v.count_is_valid(["a", "b"], ["x", "y"])
    assert not v.count_is_valid(["a"], ["x", "y"])
