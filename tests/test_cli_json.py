"""The CLI's --json mode must emit a single valid JSON object to stdout (nothing else).

Feature functions are monkeypatched so no network/LLM is touched; we assert the JSON
shape each command produces for agent consumption.
"""
from __future__ import annotations

import json

import pytest

from app import cli


def _capture_json(capsys):
    out = capsys.readouterr().out
    return json.loads(out)  # raises if stdout is not pure JSON


def test_cold_read_json(monkeypatch, capsys, tmp_path):
    resume = tmp_path / "cv.tex"
    resume.write_text("resume", encoding="utf-8")
    monkeypatch.setattr(
        "app.features.cold_read.run_cold_read",
        lambda r, j: {"targeted_role": "ML", "strongest_qualification": "X", "biggest_gap": "Y"},
    )
    rc = cli.main(["cold-read", "--resume", str(resume), "--jd", "some jd text", "--json"])
    assert rc == 0
    payload = _capture_json(capsys)
    assert payload["targeted_role"] == "ML"
    assert set(payload) == {"targeted_role", "strongest_qualification", "biggest_gap"}


def test_roast_json(monkeypatch, capsys, tmp_path):
    resume = tmp_path / "cv.tex"
    resume.write_text("resume", encoding="utf-8")
    sample = "[ROAST] vague line\n[FIX] concrete fix\n"
    monkeypatch.setattr("app.features.roast.run_roast", lambda r, j="": sample)
    rc = cli.main(["roast", "--resume", str(resume), "--json"])
    assert rc == 0
    payload = _capture_json(capsys)
    assert payload["roast_text"] == sample
    assert payload["items"] == [{"roast": "vague line", "fix": "concrete fix"}]


def test_gap_json(monkeypatch, capsys, tmp_path):
    resume = tmp_path / "cv.tex"
    resume.write_text("resume", encoding="utf-8")
    result = {"repos": [{"repo": "a"}], "inventory": "Repo: a", "analysis": {"missing": ["m"]}}
    monkeypatch.setattr("app.features.gap_finder.run_gap_finder", lambda *a, **k: result)
    rc = cli.main(["gap", "--github", "u", "--resume", str(resume), "--jd", "jd", "--json"])
    assert rc == 0
    payload = _capture_json(capsys)
    assert payload["analysis"]["missing"] == ["m"]


def test_receipt_json(monkeypatch, capsys, tmp_path):
    run = tmp_path / "run1"
    run.mkdir()
    (run / "receipt.json").write_text(json.dumps({"words_removed": 5}), encoding="utf-8")
    monkeypatch.setattr("app.utils.run_store.latest_run_dir", lambda: run)
    rc = cli.main(["receipt", "--json"])
    assert rc == 0
    payload = _capture_json(capsys)
    assert payload["receipt"]["words_removed"] == 5
    assert payload["run"] == str(run)


def test_human_mode_is_not_json(monkeypatch, capsys, tmp_path):
    resume = tmp_path / "cv.tex"
    resume.write_text("resume", encoding="utf-8")
    monkeypatch.setattr(
        "app.features.cold_read.run_cold_read",
        lambda r, j: {"targeted_role": "ML", "strongest_qualification": "X", "biggest_gap": "Y"},
    )
    cli.main(["cold-read", "--resume", str(resume), "--jd", "jd"])  # no --json
    out = capsys.readouterr().out
    assert "Cold Read" in out
    with pytest.raises(json.JSONDecodeError):
        json.loads(out)
