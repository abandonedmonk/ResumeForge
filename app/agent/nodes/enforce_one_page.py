"""Strict page-budget enforcement.

After the first compile we know the real page count. If the resume spills past
``max_pages`` (1 unless the candidate has 10+ years of experience or explicitly
opted into two pages), we trim deterministically — dropping the lowest-priority
project bullets, then whole projects, then trailing skill categories — and
recompile. Trimming spends zero tokens. Only if we hit the content floor and are
still slightly over do we ask the model to shorten the longest bullets. Every
trim is recorded in ``state['layout_notes']`` so nothing is silently dropped.
"""
from __future__ import annotations

from app.agent.nodes.compile_pdf import compile_final
from app.agent.state import ResumeState
from app.llm.router import RoutedModel
from app.parsers.latex_assembler import inject_resume_personalization, inject_sections
from app.utils.config import get_config
from app.utils.logger import log_error, log_status

MAX_TRIM_ITERATIONS = 16
MIN_PROJECTS = 1
MIN_SKILLS = 3
MIN_BULLETS_PER_PROJECT = 2


def _cap_to_budget(state: ResumeState) -> bool:
    """Collapse gross overflow in one shot by enforcing the template content budget."""
    budget = get_config()
    max_projects = int(budget.get("max_projects", 3))
    max_skills = int(budget.get("max_skills", 4))
    changed = False
    if len(state["generated_projects"]) > max_projects:
        for dropped in state["generated_projects"][max_projects:]:
            state["layout_notes"].append(f"Dropped project '{dropped.get('title', '?')}' (over budget) to fit one page.")
        state["generated_projects"] = state["generated_projects"][:max_projects]
        changed = True
    if len(state["generated_skills"]) > max_skills:
        state["generated_skills"] = state["generated_skills"][:max_skills]
        state["layout_notes"].append("Trimmed skill categories over budget to fit one page.")
        changed = True
    return changed


def _reassemble(state: ResumeState) -> None:
    final_tex = inject_sections(
        state["original_resume_tex"],
        state["resume_sections"],
        state["tailored_sections"],
    )
    state["final_tex"] = inject_resume_personalization(
        final_tex,
        state["generated_headline"],
        state["generated_skills"],
        state["generated_projects"],
    )


def _drop_project_bullet(state: ResumeState) -> bool:
    candidates = [p for p in state["generated_projects"] if len(p.get("bullets", [])) > MIN_BULLETS_PER_PROJECT]
    if not candidates:
        return False
    target = max(candidates, key=lambda p: len(p.get("bullets", [])))
    target["bullets"] = list(target["bullets"])[:-1]
    state["layout_notes"].append(f"Trimmed a bullet from project '{target.get('title', '?')}' to fit one page.")
    return True


def _drop_project(state: ResumeState) -> bool:
    if len(state["generated_projects"]) > MIN_PROJECTS:
        dropped = state["generated_projects"].pop()
        state["layout_notes"].append(f"Dropped lowest-priority project '{dropped.get('title', '?')}' to fit one page.")
        return True
    return False


def _drop_skill_category(state: ResumeState) -> bool:
    if len(state["generated_skills"]) > MIN_SKILLS:
        dropped = state["generated_skills"].pop()
        state["layout_notes"].append(f"Removed skill category '{dropped.get('category', '?')}' to fit one page.")
        return True
    return False


# Highest-priority trim first; each returns True if it changed anything.
_TRIM_STEPS = (_drop_project_bullet, _drop_project, _drop_skill_category)


def _apply_one_trim(state: ResumeState) -> bool:
    for step in _TRIM_STEPS:
        if step(state):
            return True
    return False


def _ai_polish_longest_bullets(state: ResumeState) -> bool:
    """Last resort: ask the model to shorten the two longest project bullets."""
    bullets: list[tuple[dict, int, str]] = []
    for project in state["generated_projects"]:
        for idx, text in enumerate(project.get("bullets", [])):
            bullets.append((project, idx, str(text)))
    bullets.sort(key=lambda item: len(item[2]), reverse=True)
    targets = bullets[:2]
    if not targets:
        return False
    changed = False
    for project, idx, text in targets:
        try:
            system = "You shorten resume bullets. Keep all metrics, keywords, and **bold** markers. Return ONE line only."
            user = f"Shorten this to about 70% length without losing impact:\n{text}"
            shorter = RoutedModel("stage2", task="tailor").call(system, user).strip().splitlines()[0].strip()
            if shorter and len(shorter) < len(text):
                project["bullets"][idx] = shorter
                changed = True
        except Exception as exc:  # pragma: no cover - provider specific
            log_error(state, f"One-page AI polish skipped a bullet: {exc}")
    if changed:
        state["layout_notes"].append("Asked the model to shorten the longest bullets to fit one page.")
    return changed


def enforce_one_page(state: ResumeState) -> ResumeState:
    max_pages = int(state.get("max_pages", 1) or 1)
    page_count = int(state.get("page_count", 1) or 1)
    if page_count <= max_pages:
        return state

    log_status(state, f"Resume is {page_count} pages; condensing to {max_pages}...")

    # Cheap first pass: collapse anything over the template's content budget.
    if _cap_to_budget(state):
        _reassemble(state)
        try:
            compile_final(state)
            page_count = int(state.get("page_count", 1) or 1)
        except Exception as exc:
            log_error(state, f"Recompile during budget cap failed: {exc}")

    iterations = 0
    while page_count > max_pages and iterations < MAX_TRIM_ITERATIONS:
        iterations += 1
        if not _apply_one_trim(state):
            break  # hit the content floor
        _reassemble(state)
        try:
            compile_final(state)
        except Exception as exc:
            log_error(state, f"Recompile during one-page enforcement failed: {exc}")
            break
        page_count = int(state.get("page_count", 1) or 1)

    # Floor reached but still slightly over -> one bounded AI polish pass.
    if page_count > max_pages and _ai_polish_longest_bullets(state):
        _reassemble(state)
        try:
            compile_final(state)
            page_count = int(state.get("page_count", 1) or 1)
        except Exception as exc:
            log_error(state, f"Recompile after AI polish failed: {exc}")

    if page_count > max_pages:
        state["layout_notes"].append(
            f"Could not reach {max_pages} page(s) without dropping core content; left at {page_count}."
        )
        log_status(state, f"Kept {page_count} pages — further trimming would remove essential content.")
    else:
        log_status(state, f"Condensed to {page_count} page(s).")
    return state
