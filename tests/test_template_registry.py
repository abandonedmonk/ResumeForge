"""Unit tests for the template registry."""
from __future__ import annotations

from app.parsers.template_registry import TemplateConfig, list_templates, load_template


def test_load_classic_template():
    template = load_template("classic")
    assert isinstance(template, TemplateConfig)
    assert template.name == "classic"
    assert template.compiler == "pdflatex"
    assert isinstance(template.max_projects, int) and template.max_projects >= 1
    tex = template.tex
    assert "% PLACEHOLDER_SKILLS_START" in tex
    assert "% PLACEHOLDER_PROJECTS_START" in tex


def test_unknown_template_returns_none():
    assert load_template("does-not-exist") is None
    assert load_template(None) is None
    assert load_template("") is None


def test_classic_is_listed():
    assert "classic" in list_templates()
