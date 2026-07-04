"""Unit tests for LaTeX semantic branching (pure storage + diff, no LLM/network)."""
from __future__ import annotations

import pytest

from app.features import branches


@pytest.fixture(autouse=True)
def _tmp_branches(monkeypatch, tmp_path):
    """Point the branch store at a throwaway dir so tests never touch ~/.resumeforge."""
    monkeypatch.setattr(branches, "BRANCHES_DIR", tmp_path / "branches")


def test_valid_name_slugifies_and_rejects_empty():
    assert branches.valid_name("ML Research!") == "ml-research"
    with pytest.raises(ValueError):
        branches.valid_name("   ")


def test_save_read_roundtrip():
    branches.save_branch("ml-research", "line1\nline2", {"jd_role": "ML Engineer"})
    assert branches.read_branch_tex("ml-research") == "line1\nline2"
    meta = branches.branch_meta("ml-research")
    assert meta["name"] == "ml-research"
    assert meta["jd_role"] == "ML Engineer"
    assert meta["created_at"] and meta["updated_at"]


def test_overwrite_keeps_created_at():
    branches.save_branch("quant", "v1")
    created = branches.branch_meta("quant")["created_at"]
    branches.save_branch("quant", "v2 changed")
    meta = branches.branch_meta("quant")
    assert branches.read_branch_tex("quant") == "v2 changed"
    assert meta["created_at"] == created  # preserved across overwrite


def test_list_sorted_and_delete():
    branches.save_branch("a", "x")
    branches.save_branch("b", "y")
    names = [meta["name"] for meta in branches.list_branches()]
    assert set(names) == {"a", "b"}
    assert branches.delete_branch("a") is True
    assert branches.delete_branch("a") is False  # already gone
    assert {meta["name"] for meta in branches.list_branches()} == {"b"}


def test_read_and_meta_missing_branch():
    assert branches.read_branch_tex("nope") is None
    assert branches.branch_meta("nope") == {}


def test_diff_counts_added_removed():
    branches.save_branch("base", "alpha\nbeta\ngamma")
    branches.save_branch("fork", "alpha\nBETA\ngamma\ndelta")
    result = branches.diff_branches("base", "fork")
    assert result["a"] == "base" and result["b"] == "fork"
    assert result["added"] == 2      # BETA + delta
    assert result["removed"] == 1    # beta
    assert "unified" in result and result["unified"]


def test_diff_missing_branch_raises():
    branches.save_branch("only", "x")
    with pytest.raises(ValueError):
        branches.diff_branches("only", "ghost")


def test_render_helpers():
    assert "No branches yet" in branches.render_branch_list([])
    branches.save_branch("ml-research", "x", {"jd_role": "ML Engineer"})
    listing = branches.render_branch_list(branches.list_branches())
    assert "ml-research" in listing
    diff_text = branches.render_diff({"a": "x", "b": "y", "added": 1, "removed": 0, "unified": "+new"})
    assert "diff x -> y" in diff_text and "+1" in diff_text
