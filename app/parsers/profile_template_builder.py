"""Render a structured profile into a personal LaTeX resume template.

Fills the ``% PLACEHOLDER_*`` regions of a template's ``scaffold.tex`` from
structured data, leaving the SKILLS/PROJECTS placeholders + summary line intact
for the per-run pipeline. Self-checks by compiling before the caller persists it
(mirrors Phase 5's serialize→parse round-trip check).
"""
from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from app.agent.nodes.compile_pdf import compile_tex_to_pdf
from app.parsers.latex_assembler import (
    PROJECTS_START,
    SKILLS_START,
    SUMMARY_PATTERN,
    _format_emphasis,
    _latex_url,
)
from app.profiles.schema import Certification, Contact, Education, Experience, Profile
from app.utils.config import resolve_path
from app.utils.exceptions import ResumeForgeError
from app.utils.validator import escape_latex

# Region markers (scaffold.tex). Skills/projects/summary are handled by the pipeline.
_REGIONS = {
    "header": ("% PLACEHOLDER_HEADER_START", "% PLACEHOLDER_HEADER_END"),
    "education": ("% PLACEHOLDER_EDUCATION_START", "% PLACEHOLDER_EDUCATION_END"),
    "experience": ("% PLACEHOLDER_EXPERIENCE_START", "% PLACEHOLDER_EXPERIENCE_END"),
    "certifications": ("% PLACEHOLDER_CERTIFICATIONS_START", "% PLACEHOLDER_CERTIFICATIONS_END"),
}
# Section banners, used to drop a whole \section when it has no content.
_EXPERIENCE_BANNER = "%-----------EXPERIENCE-----------"
_PROJECTS_BANNER = "%-----------PROJECTS-----------"
_CERTIFICATIONS_BANNER = "%-----------CERTIFICATIONS-----------"
_CLOSING_RULE = "%-------------------------------------------"


def _replace_region(tex: str, start_marker: str, end_marker: str, body: str) -> str:
    if start_marker not in tex or end_marker not in tex:
        return tex
    start = tex.index(start_marker) + len(start_marker)
    end = tex.index(end_marker)
    return f"{tex[:start]}\n{body}\n{tex[end:]}"


def _drop_section(tex: str, start_banner: str, end_banner: str) -> str:
    if start_banner not in tex:
        return tex
    start = tex.index(start_banner)
    try:
        end = tex.index(end_banner, start)
    except ValueError:
        return tex
    return tex[:start] + tex[end:]


def render_header(contact: Contact) -> str:
    name = escape_latex(contact.name) or "Your Name"
    lines = [rf"    {{\Huge \scshape \textbf{{{name}}}}} \\ \vspace{{4pt}}"]

    fragments: list[str] = []
    if contact.email:
        fragments.append(rf"\href{{mailto:{_latex_url(contact.email)}}}{{\ul{{{escape_latex(contact.email)}}}}}")
    if contact.linkedin:
        fragments.append(rf"\href{{{_latex_url(contact.linkedin)}}}{{\ul{{LinkedIn}}}}")
    if contact.github:
        fragments.append(rf"\href{{{_latex_url(contact.github)}}}{{\ul{{GitHub}}}}")
    if contact.website:
        fragments.append(rf"\href{{{_latex_url(contact.website)}}}{{\ul{{Portfolio}}}}")
    if contact.phone:
        fragments.append(escape_latex(contact.phone))
    if contact.location:
        fragments.append(escape_latex(contact.location))

    for index, fragment in enumerate(fragments):
        separator = r" $|$" if index < len(fragments) - 1 else ""
        lines.append(f"    {fragment}{separator}")
    return "\n".join(lines)


def _render_education_entry(entry: Education) -> str:
    location = escape_latex(entry.institution)
    if entry.city:
        location = f"{location}, {escape_latex(entry.city)}"
    gpa = escape_latex(entry.gpa)
    degree = escape_latex(entry.degree)
    dates = escape_latex(entry.dates)
    lines = [
        r"  \resumeSubheading",
        rf"    {{{location}}}{{{gpa}}}",
        rf"    {{{degree}}}{{\textit{{{dates}}}}}",
    ]
    if entry.coursework:
        lines[-1] = lines[-1] + r"  \vspace{-9pt}"
        lines.append(rf"  \item \small{{\textbf{{Relevant Coursework:}} {escape_latex(entry.coursework)}}}")
    return "\n".join(lines)


def render_education(education: list[Education]) -> str:
    rendered = [_render_education_entry(entry) for entry in education if entry.institution or entry.degree]
    return "\n".join(rendered)


def _render_experience_entry(entry: Experience) -> str:
    lines = [
        r"  \resumeSubheading",
        rf"    {{{escape_latex(entry.company)}}}{{{escape_latex(entry.location)}}}",
        rf"    {{{escape_latex(entry.role)}}}{{{escape_latex(entry.dates)}}}",
    ]
    bullets = [bullet for bullet in entry.bullets if bullet.strip()]
    if bullets:
        lines.append(r"    \resumeItemListStart")
        for bullet in bullets:
            lines.append(rf"      \resumeItem{{{_format_emphasis(bullet)}}}")
        lines.append(r"    \resumeItemListEnd")
    return "\n".join(lines)


def render_experience(experience: list[Experience]) -> str:
    rendered = [_render_experience_entry(entry) for entry in experience if entry.company or entry.role]
    return "\n".join(rendered)


def _render_certification_entry(entry: Certification) -> str:
    parts = escape_latex(entry.name)
    if entry.issuer:
        parts = f"{parts} --- {escape_latex(entry.issuer)}"
    if entry.url:
        parts = rf"{parts} $|$ \href{{{_latex_url(entry.url)}}}{{\underline{{Certificate Link}}}}"
    return rf"    \item {parts}"


def render_certifications(certifications: list[Certification]) -> str:
    rendered = [_render_certification_entry(entry) for entry in certifications if entry.name]
    return "\n".join(rendered)


def render_profile_template(profile: Profile, scaffold_tex: str) -> str:
    tex = scaffold_tex
    tex = _replace_region(tex, *_REGIONS["header"], render_header(profile.contact))
    tex = _replace_region(tex, *_REGIONS["education"], render_education(profile.education))

    experience_body = render_experience(profile.experience)
    if experience_body:
        tex = _replace_region(tex, *_REGIONS["experience"], experience_body)
    else:
        tex = _drop_section(tex, _EXPERIENCE_BANNER, _PROJECTS_BANNER)

    certifications_body = render_certifications(profile.certifications)
    if certifications_body:
        tex = _replace_region(tex, *_REGIONS["certifications"], certifications_body)
    else:
        tex = _drop_section(tex, _CERTIFICATIONS_BANNER, _CLOSING_RULE)

    return tex


def build_personal_template(profile: Profile, template_name: str = "classic") -> tuple[str, str]:
    """Render + self-check a personal template. Returns ``(tex, compile_log)``.

    Raises ``ResumeForgeError`` if the template is not renderable, loses an
    injection hook, or fails to compile — so a broken template is never persisted.
    """
    scaffold_path = resolve_path(f"templates/{template_name}/scaffold.tex")
    if not scaffold_path.is_file():
        raise ResumeForgeError(
            f"Template '{template_name}' is not renderable (no scaffold.tex). Use a renderable template."
        )
    tex = render_profile_template(profile, scaffold_path.read_text(encoding="utf-8"))

    if not SUMMARY_PATTERN.search(tex) or SKILLS_START not in tex or PROJECTS_START not in tex:
        raise ResumeForgeError(
            "Rendered template lost an injection hook (summary/skills/projects). Aborting."
        )

    temp_dir = Path(tempfile.mkdtemp(prefix="rf_profilecheck_"))
    try:
        log = compile_tex_to_pdf(tex, temp_dir / "check.pdf")
    except FileNotFoundError as exc:
        raise ResumeForgeError(
            "pdflatex was not found on PATH; cannot validate the template. Install MiKTeX/TeX Live."
        ) from exc
    except Exception as exc:
        raise ResumeForgeError(f"Rendered template failed to compile: {str(exc)[-800:]}") from exc
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

    return tex, log
