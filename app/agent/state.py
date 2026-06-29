from __future__ import annotations

from typing import Any, TypedDict


class ResumeState(TypedDict):
    jd_text: str
    skills_md: str
    projects_context: dict[str, dict[str, Any]] | str
    original_resume_tex: str
    output_folder: str
    jd_analysis: dict[str, Any]
    resume_sections: dict[str, dict[str, Any]]
    generated_headline: str
    generated_skills: list[dict[str, Any]]
    generated_projects: list[dict[str, Any]]
    personalization_notes: dict[str, Any]
    tailored_sections: dict[str, dict[str, Any]]
    changes_log: list[dict[str, Any]]
    final_tex: str
    final_pdf_path: str
    saved_pdf_path: str
    ats_score: dict[str, Any]
    ats_score_summary: str
    skills_gap: dict[str, list[str]]
    changes_report_md: str
    errors: list[str]
    status_updates: list[str]
    run_log_path: str
    run_log_paths: list[str]
    # Template & one-page enforcement
    resume_template: str
    page_count: int
    max_pages: int
    allow_two_pages: bool
    candidate_years_experience: int
    layout_notes: list[str]


def default_state() -> ResumeState:
    return ResumeState(
        jd_text="",
        skills_md="",
        projects_context={},
        original_resume_tex="",
        output_folder="",
        jd_analysis={},
        resume_sections={},
        generated_headline="",
        generated_skills=[],
        generated_projects=[],
        personalization_notes={},
        tailored_sections={},
        changes_log=[],
        final_tex="",
        final_pdf_path="",
        saved_pdf_path="",
        ats_score={},
        ats_score_summary="",
        skills_gap={},
        changes_report_md="",
        errors=[],
        status_updates=[],
        run_log_path="",
        run_log_paths=[],
        resume_template="",
        page_count=0,
        max_pages=1,
        allow_two_pages=False,
        candidate_years_experience=0,
        layout_notes=[],
    )
