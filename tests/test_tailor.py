"""Unit tests for the shared tailor orchestration (used by both CLI and MCP).

`run_agent` and the run-store are stubbed, so no LLM/LaTeX runs.
"""
from __future__ import annotations

from app.features import tailor


def _fake_state(**over):
    base = {
        "final_tex": r"\resumeItem{Led team to ship X, cutting cost by 20\%}",
        "final_pdf_path": "",
        "ats_score_summary": "80% strong match",
        "ats_score": {"overall": 80},
        "errors": [],
        "jd_analysis": {"role_title": "ML Engineer", "company_name": "Acme"},
        "original_resume_tex": r"\resumeItem{Responsible for stuff and things}",
    }
    base.update(over)
    return base


def _stub_run(monkeypatch, tmp_path, state=None):
    run = tmp_path / "run1"
    monkeypatch.setattr(tailor, "new_run_dir", lambda label="": (run.mkdir(parents=True, exist_ok=True) or run))
    monkeypatch.setattr(tailor, "run_agent", lambda initial_state: state or _fake_state())
    return run


def test_run_tailor_writes_artifacts_and_payload(monkeypatch, tmp_path):
    run = _stub_run(monkeypatch, tmp_path)
    payload = tailor.run_tailor("jd text here")
    assert (run / "resume.tex").exists()
    assert (run / "receipt.json").exists()
    assert payload["run_dir"] == str(run)
    assert payload["ats_summary"] == "80% strong match"
    assert payload["branch"] is None and payload["cold_read"] is None
    assert set(payload) >= {"run_dir", "receipt", "artifacts", "errors", "ats_score"}


def test_run_tailor_cold_read(monkeypatch, tmp_path):
    run = _stub_run(monkeypatch, tmp_path)
    monkeypatch.setattr(
        "app.features.cold_read.run_cold_read",
        lambda resume, jd: {"targeted_role": "ML", "strongest_qualification": "x", "biggest_gap": "y"},
    )
    payload = tailor.run_tailor("jd", cold_read=True)
    assert payload["cold_read"]["targeted_role"] == "ML"
    assert (run / "cold-read.json").exists()
    assert payload["artifacts"]["cold_read"].endswith("cold-read.json")


def test_run_tailor_persists_branch(monkeypatch, tmp_path):
    _stub_run(monkeypatch, tmp_path)
    from app.features import branches

    monkeypatch.setattr(branches, "BRANCHES_DIR", tmp_path / "branches")
    payload = tailor.run_tailor("jd", branch="ML Research")
    assert payload["branch"] == "ml-research"
    assert (tmp_path / "branches" / "ml-research" / "resume.tex").exists()


def test_render_tailor_is_readable():
    text = tailor.render_tailor(
        {"run_dir": "/x", "ats_summary": "80%", "receipt": {}, "cold_read": None, "branch": None, "errors": []}
    )
    assert "Run:" in text and "ATS:" in text
