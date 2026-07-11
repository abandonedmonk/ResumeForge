"""Unit tests for the template registry."""
from __future__ import annotations

import pytest

from app.parsers.latex_assembler import (
    PROJECTS_START,
    SKILLS_START,
    SUMMARY_PATTERN,
)
from app.parsers.template_registry import TemplateConfig, list_templates, load_template

# Every bundled template must keep the injection hooks the pipeline writes into.
DISCIPLINE_TEMPLATES = ["cs", "bio", "academia"]
ALL_TEMPLATES = ["classic", "modern", *DISCIPLINE_TEMPLATES]


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


def test_discipline_templates_are_listed():
    listed = list_templates()
    for name in DISCIPLINE_TEMPLATES:
        assert name in listed, f"{name} should be auto-discovered under templates/"


@pytest.mark.parametrize("name", ALL_TEMPLATES)
def test_template_preserves_injection_hooks(name):
    template = load_template(name)
    assert template is not None
    tex = template.tex
    assert SKILLS_START in tex
    assert PROJECTS_START in tex
    assert SUMMARY_PATTERN.search(tex), f"{name} must keep the summary line for headline injection"


def test_academia_opts_into_two_pages():
    assert load_template("academia").allow_two_pages is True


@pytest.mark.parametrize("name", ["classic", "modern", "cs", "bio"])
def test_non_academia_templates_stay_one_page(name):
    assert load_template(name).allow_two_pages is False
