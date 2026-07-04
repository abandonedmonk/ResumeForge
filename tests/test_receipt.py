"""Unit tests for the Compression Receipt (pure, no LLM)."""
from __future__ import annotations

from app.features.receipt import build_receipt, render_receipt

ORIGINAL = r"""
\resumeItem{Responsible for managing team deliverables and coordinating with stakeholders across the org}
\resumeItem{Worked on backend systems using Python and relational databases}
"""

TAILORED = r"""
\resumeItem{Led 4-person team to ship analytics platform, reducing latency by 30\%}
\resumeItem{Built backend microservices in Python and PostgreSQL}
"""

JD = {"keywords": ["PostgreSQL", "microservices", "stakeholders"], "required_skills": []}


def test_bullet_counts_match():
    receipt = build_receipt(ORIGINAL, TAILORED, JD)
    assert receipt["bullets_before"] == 2
    assert receipt["bullets_after"] == 2


def test_strengthened_detects_action_verbs_and_metrics():
    receipt = build_receipt(ORIGINAL, TAILORED, JD)
    # Both rewrites gain an action-verb lead ("Led"/"Built"); first also gains a metric.
    assert receipt["bullets_strengthened"] == 2


def test_keyword_delta_added_and_removed():
    receipt = build_receipt(ORIGINAL, TAILORED, JD)
    assert "PostgreSQL" in receipt["keywords_added"]
    assert "microservices" in receipt["keywords_added"]
    assert "stakeholders" in receipt["keywords_removed"]


def test_similarity_is_bounded_int():
    receipt = build_receipt(ORIGINAL, TAILORED, JD)
    assert isinstance(receipt["semantic_similarity"], int)
    assert 0 <= receipt["semantic_similarity"] <= 100


def test_condensed_pct_non_negative():
    receipt = build_receipt(ORIGINAL, TAILORED, JD)
    assert receipt["avg_condense_pct"] >= 0
    assert receipt["bullets_condensed"] >= 0


def test_render_is_readable():
    text = render_receipt(build_receipt(ORIGINAL, TAILORED, JD))
    assert "Compression Receipt" in text
    assert "Similarity:" in text


def test_empty_inputs_do_not_crash():
    receipt = build_receipt("", "", {})
    assert receipt["words_removed"] == 0
    assert receipt["semantic_similarity"] in (0, 100)
