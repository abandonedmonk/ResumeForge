"""Unit tests for the TeX bootstrap (no actual install / network)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.utils import tex_bootstrap as tb


def test_required_packages_cover_template_needs():
    for pkg in ("titlesec", "marvosym", "enumitem", "hyperref", "fancyhdr", "geometry", "soul", "xcolor"):
        assert pkg in tb.REQUIRED_PACKAGES


def test_tinytex_root_per_platform(monkeypatch):
    monkeypatch.setattr(tb.platform, "system", lambda: "Linux")
    assert tb.tinytex_root().name == ".TinyTeX"
    monkeypatch.setattr(tb.platform, "system", lambda: "Windows")
    monkeypatch.setenv("APPDATA", str(Path("/fake/appdata")))
    assert tb.tinytex_root().name == "TinyTeX"


def test_bin_dirs_empty_when_absent(monkeypatch, tmp_path):
    monkeypatch.setattr(tb, "tinytex_root", lambda: tmp_path / "nope")
    assert tb.tinytex_bin_dirs() == []


def test_pdflatex_available_via_path(monkeypatch):
    monkeypatch.setattr(tb.shutil, "which", lambda name: "/usr/bin/pdflatex" if name == "pdflatex" else None)
    assert tb.pdflatex_available() is True


def test_add_to_path_noop_when_on_path(monkeypatch):
    monkeypatch.setattr(tb.shutil, "which", lambda name: "/usr/bin/pdflatex")
    assert tb.add_tinytex_to_path() is None


def test_add_to_path_prepends_tinytex(monkeypatch, tmp_path):
    monkeypatch.setattr(tb.shutil, "which", lambda name: None)  # not on PATH
    bin_dir = tmp_path / "TinyTeX" / "bin" / "x86_64-linux"
    bin_dir.mkdir(parents=True)
    (bin_dir / "pdflatex").write_text("", encoding="utf-8")
    monkeypatch.setattr(tb, "tinytex_bin_dirs", lambda: [bin_dir])
    monkeypatch.setattr(tb, "_is_windows", lambda: False)
    added = tb.add_tinytex_to_path()
    assert added == str(bin_dir)
    assert str(bin_dir) in tb.os.environ["PATH"]
