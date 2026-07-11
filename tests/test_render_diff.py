"""Unit tests for the side-by-side Diff tab renderer (`_changes_diff_html`)."""
from __future__ import annotations

from app.ui.render import _changes_diff_html, _diff_bullet_html


def test_empty_log_returns_placeholder():
    out = _changes_diff_html([])
    assert "No changes to diff yet" in out
    assert "<ins" not in out and "<del" not in out


def test_reworded_bullet_shows_ins_and_del():
    log = [
        {
            "section": "Experience",
            "old_bullets": ["Managed a team of five engineers"],
            "new_bullets": ["Led a team of five engineers"],
            "reasoning": "Stronger action verb.",
        }
    ]
    out = _changes_diff_html(log)
    assert "<ins" in out and "<del" in out
    assert "Managed" in out and "Led" in out
    # Unchanged words are not wrapped in ins/del.
    assert "<del style='background:#fee2e2;color:#991b1b;border-radius:3px;padding:0 2px'>engineers" not in out
    assert "Experience" in out
    assert "Stronger action verb." in out


def test_identical_bullet_has_no_highlight():
    log = [
        {
            "section": "Summary",
            "old_bullets": ["Backend engineer with 5 years experience"],
            "new_bullets": ["Backend engineer with 5 years experience"],
            "reasoning": "Kept original bullets.",
        }
    ]
    out = _changes_diff_html(log)
    assert "<ins" not in out and "<del" not in out
    assert "Backend engineer with 5 years experience" in out


def test_section_name_is_escaped():
    log = [
        {
            "section": "R&D <team>",
            "old_bullets": ["did a"],
            "new_bullets": ["did b"],
            "reasoning": "",
        }
    ]
    out = _changes_diff_html(log)
    assert "R&amp;D &lt;team&gt;" in out
    assert "<team>" not in out


def test_diff_bullet_escapes_content():
    # Angle brackets in the text must not leak raw into the HTML.
    out = _diff_bullet_html("used <script>", "used <b>tag</b>")
    assert "<script>" not in out
    assert "&lt;script&gt;" in out


def test_multiple_sections_all_rendered():
    log = [
        {"section": "Experience", "old_bullets": ["a old"], "new_bullets": ["a new"], "reasoning": ""},
        {"section": "Projects", "old_bullets": ["b old"], "new_bullets": ["b new"], "reasoning": ""},
    ]
    out = _changes_diff_html(log)
    assert "Experience" in out and "Projects" in out
