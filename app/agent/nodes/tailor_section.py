from __future__ import annotations

import time

from app.agent.state import ResumeState
from app.llm.router import RoutedStage1Model, RoutedStage2Model
from app.parsers.projects_parser import match_project
from app.prompts.stage1_ats import build_stage1_prompt
from app.prompts.stage2_polish import build_stage2_prompt
from app.utils.config import get_config
from app.utils.exceptions import LLMError, RateLimitError
from app.utils.logger import log_error, log_status

FIXED_SECTIONS = {
    "Education",
    "Projects",
    "Certifications",
    "Achievements and Extracurricular Engagement",
}


def _parse_bullets(response_text: str, expected_count: int) -> list[str]:
    bullets = [line.strip().lstrip("-* ").strip() for line in response_text.splitlines() if line.strip()]
    if len(bullets) != expected_count:
        raise LLMError(f"Expected {expected_count} bullets, got {len(bullets)}")
    return bullets


def tailor_sections(state: ResumeState) -> ResumeState:
    config = get_config()
    stage1_model = RoutedStage1Model()
    stage2_model = RoutedStage2Model()

    tailorable = [
        (name, sec) for name, sec in state["resume_sections"].items()
        if name not in FIXED_SECTIONS and sec.get("bullets")
    ]
    total = len(tailorable)

    for index, (section_name, section) in enumerate(tailorable):
        bullets = list(section.get("bullets", []))

        log_status(state, f"Tailoring section {index + 1}/{total}: {section_name}...")
        section_text = "\n".join(bullets)
        project_context = match_project(section_text, state["projects_context"])
        rewritten = bullets
        reasoning = "Kept original bullets."

        for attempt in range(config.get("max_retries_per_section", 2)):
            try:
                system_prompt, user_prompt = build_stage1_prompt(
                    state["skills_md"],
                    state["jd_analysis"],
                    section_name,
                    bullets,
                    project_context,
                )
                stage1_response = stage1_model.call(system_prompt, user_prompt)
                stage1_bullets = _parse_bullets(stage1_response, len(bullets))

                system_prompt, user_prompt = build_stage2_prompt(
                    state["skills_md"],
                    state["jd_analysis"],
                    stage1_bullets,
                    section_name,
                )
                stage2_response = stage2_model.call(system_prompt, user_prompt)
                rewritten = _parse_bullets(stage2_response, len(bullets))
                reasoning = "ATS keywords strengthened in Stage 1 and prose polished in Stage 2."
                break
            except RateLimitError:
                if attempt + 1 >= config.get("max_retries_per_section", 2):
                    log_error(state, f"Rate limit while processing section '{section_name}'. Original bullets kept.")
                time.sleep(min(2 ** attempt, 8))
            except Exception as exc:
                log_error(state, f"Section '{section_name}' failed: {exc}. Original bullets kept.")
                rewritten = bullets
                reasoning = "Original bullets kept because tailoring failed."
                break

        state["tailored_sections"][section_name] = {
            "new_bullets": rewritten,
            "reasoning": reasoning,
        }
        state["changes_log"].append(
            {
                "section": section_name,
                "old_bullets": bullets,
                "new_bullets": rewritten,
                "reasoning": reasoning,
            }
        )

    return state
