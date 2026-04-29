from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import gradio as gr

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agent.graph import run_agent
from app.agent.nodes.save_and_display import save_reviewed_output
from app.llm.router import RoutedStage2Model
from app.utils.file_namer import build_log_stem
from app.utils.config import get_config, resolve_path
from app.utils.logger import get_logs_dir, log_error, log_status, write_run_log


def _read_uploaded_text(file_obj: Any) -> str:
    if not file_obj:
        return ""
    if isinstance(file_obj, str):
        path = Path(file_obj)
    else:
        path = Path(file_obj.name)
    return path.read_text(encoding="utf-8")


def _safe_file_output(path_str: str | None):
    if not path_str:
        return None
    path = Path(path_str)
    if path.exists() and path.is_file():
        return str(path)
    return None


def _score_badge_html(summary: str, score_data: dict) -> str:
    overall = int(score_data.get("overall", 0) or 0)
    label = summary or "ATS score unavailable"
    if overall >= 75:
        bg = "#d1fae5"
        fg = "#065f46"
    elif overall >= 50:
        bg = "#fef3c7"
        fg = "#92400e"
    else:
        bg = "#fee2e2"
        fg = "#991b1b"
    return (
        f"<div style='padding:14px 18px;border-radius:12px;background:{bg};color:{fg};"
        f"font-weight:700;font-size:22px;text-align:center'>{label}</div>"
    )


def _ats_analysis_markdown(score_data: dict, skills_gap: dict) -> str:
    if not score_data:
        return "ATS analysis unavailable."
    recommendations = score_data.get("recommendations", [])
    return "\n".join(
        [
            f"## Overall ATS Match: {score_data.get('overall', 'N/A')}%",
            "",
            "### Sub-scores",
            f"- Keyword Match: {score_data.get('keyword_match', {}).get('score', 'N/A')}%",
            f"- Semantic Context: {score_data.get('semantic_context', {}).get('score', 'N/A')}%",
            f"- Section Quality: {score_data.get('section_quality', {}).get('score', 'N/A')}%",
            f"- Keyword Placement: {score_data.get('keyword_placement', {}).get('score', 'N/A')}%",
            f"- Impact Metrics: {score_data.get('impact_metrics', {}).get('score', 'N/A')}%",
            "",
            "### Skills Gap",
            f"- Missing Required: {', '.join(skills_gap.get('missing_required', [])) or 'None'}",
            f"- Missing Nice-to-Have: {', '.join(skills_gap.get('missing_nice_to_have', [])) or 'None'}",
            f"- Missing Enriched: {', '.join(skills_gap.get('missing_enriched', [])) or 'None'}",
            "",
            "### Recommendations",
            *([f"- {item}" for item in recommendations] or ["- None"]),
        ]
    )


def _run_resumeforge(
    output_folder: str,
    stage1_model: str,
    stage2_model: str,
    enrich_with_web_search: bool,
):
    config = get_config()
    config["stage1_model"] = stage1_model
    config["stage2_model"] = stage2_model
    config["enrich_with_web_search"] = enrich_with_web_search
    logs_before = {path.name for path in get_logs_dir().glob("*.log")}
    session_state: dict[str, Any] = {"status_updates": [], "errors": []}
    log_status(session_state, "Starting ResumeForge preview generation...")

    initial_state = {
        "jd_text": resolve_path(config.get("default_jd_txt", "")).read_text(encoding="utf-8") if config.get("default_jd_txt", "") else "",
        "original_resume_tex": str(config["default_resume_tex"]),
        "skills_md": str(config["default_skills_md"]),
        "projects_context": str(config["default_projects_md"]),
        "output_folder": output_folder,
        "status_updates": session_state["status_updates"],
        "errors": session_state["errors"],
    }
    final_state = run_agent(initial_state)
    new_logs = sorted(path for path in get_logs_dir().glob("*.log") if path.name not in logs_before)
    run_log_content = _build_run_log_content(final_state, new_logs)
    company_name = str(final_state.get("jd_analysis", {}).get("company_name", "Company"))
    role_title = str(final_state.get("jd_analysis", {}).get("role_title", "Role"))
    run_log_name = f"{build_log_stem(company_name, role_title, suffix='run')}.log"
    run_log_path = write_run_log(run_log_name, run_log_content)
    final_state["run_log_path"] = str(run_log_path)
    final_state["run_log_paths"] = [str(path) for path in new_logs] + [str(run_log_path)]
    status_text = "\n".join(final_state["status_updates"]) or "No status updates."
    errors_text = "\n".join(final_state["errors"]) or "No errors."
    return (
        _score_badge_html(final_state.get("ats_score_summary", ""), final_state.get("ats_score", {})),
        _ats_analysis_markdown(final_state.get("ats_score", {}), final_state.get("skills_gap", {})),
        final_state["changes_report_md"],
        final_state["final_tex"],
        _safe_file_output(final_state.get("final_pdf_path")),
        status_text,
        errors_text,
        run_log_content,
        final_state,
    )


def _build_run_log_content(final_state: dict, new_logs: list[Path]) -> str:
    config = get_config()
    notes = final_state.get("personalization_notes", {}) or {}
    generated_skills = final_state.get("generated_skills", []) or []
    generated_projects = final_state.get("generated_projects", []) or []
    lines = [
        "ResumeForge Run Log",
        f"Generated: {datetime.now().isoformat()}",
        f"Company: {final_state.get('jd_analysis', {}).get('company_name', 'Company')}",
        f"Role: {final_state.get('jd_analysis', {}).get('role_title', 'Role')}",
        f"ATS Summary: {final_state.get('ats_score_summary', 'N/A')}",
        "",
        "Pipeline Configuration:",
        f"- Stage 1 (Selection): {config.get('stage1_model', 'unknown')} | Groq: {config.get('groq_reasoning_model', 'N/A')}",
        f"- Stage 2 (Writing): {config.get('stage2_model', 'unknown')} | Groq: {config.get('groq_fast_model', 'N/A')}",
        f"- Company Enrichment: {config.get('enrich_with_web_search', False)}",
        "",
        "Status Updates:",
        *([f"- {line}" for line in final_state.get("status_updates", [])] or ["- None"]),
        "",
        "Errors:",
        *([f"- {line}" for line in final_state.get("errors", [])] or ["- None"]),
        "",
        "AI Decision Notes:",
        f"- Drafting strategy: {notes.get('drafting_notes', '') or 'None'}",
        f"- Headline: {final_state.get('generated_headline', '') or 'None'}",
        f"- Headline rationale: {notes.get('headline_reason', '') or 'None'}",
        f"- Skills selection rationale: {notes.get('skills_reason', '') or 'None'}",
        *(
            [f"- Skill category: {category.get('category', '')} -> {', '.join(category.get('items', []))}" for category in generated_skills]
            or ["- Skill category: None"]
        ),
        f"- Project selection rationale: {notes.get('project_selection_reason', '') or 'None'}",
        *(
            [
                f"- Project: {project.get('title', '')} | Selection reasoning: {project.get('selection_reason', '') or 'No per-project rationale provided.'}"
                for project in generated_projects
            ]
            or ["- Project: None"]
        ),
        "",
        "Run Artifacts:",
        f"- Preview PDF: {final_state.get('final_pdf_path', '') or 'Not generated'}",
        "",
        "ATS Breakdown:",
        f"- Overall: {final_state.get('ats_score', {}).get('overall', 'N/A')}",
        f"- Keyword Match: {final_state.get('ats_score', {}).get('keyword_match', {}).get('score', 'N/A')}",
        f"- Semantic Context: {final_state.get('ats_score', {}).get('semantic_context', {}).get('score', 'N/A')}",
        f"- Section Quality: {final_state.get('ats_score', {}).get('section_quality', {}).get('score', 'N/A')}",
        f"- Keyword Placement: {final_state.get('ats_score', {}).get('keyword_placement', {}).get('score', 'N/A')}",
        f"- Impact Metrics: {final_state.get('ats_score', {}).get('impact_metrics', {}).get('score', 'N/A')}",
        "",
        "LLM Log Files:",
        *([f"- {path}" for path in new_logs] or ["- None"]),
    ]
    return "\n".join(lines)


def _apply_ai_edit_request(current_latex: str, edit_request: str, stage2_model: str) -> tuple[str, str]:
    if not current_latex.strip():
        return current_latex, "No LaTeX preview available yet."
    if not edit_request.strip():
        return current_latex, "Enter an edit request first."

    config = get_config()
    config["stage2_model"] = stage2_model
    skills_md = resolve_path(config["default_skills_md"]).read_text(encoding="utf-8")
    session_state: dict[str, Any] = {"status_updates": [], "errors": []}
    log_status(session_state, "Applying AI edit request to LaTeX preview...")
    system_prompt = (
        f"{skills_md}\n\n"
        "You are editing a LaTeX resume file. Return the full updated LaTeX only. "
        "Preserve structure unless the request explicitly changes it."
    )
    user_prompt = f"""
Edit request:
{edit_request}

Current LaTeX resume:
{current_latex}
""".strip()
    try:
        updated = RoutedStage2Model().call(system_prompt, user_prompt)
    except Exception as exc:
        log_error(session_state, f"AI edit request failed: {exc}")
        return current_latex, "\n".join(session_state["errors"])
    cleaned = updated.strip()
    if "```" in cleaned:
        cleaned = cleaned.replace("```latex", "").replace("```tex", "").replace("```", "").strip()
    log_status(session_state, "Applied AI edit request to the preview. Review the LaTeX before saving.")
    return cleaned, "\n".join(session_state["status_updates"])


def _save_preview(final_state: dict, reviewed_latex: str):
    if not final_state:
        return None, "No preview is loaded yet.", final_state

    updated_state = save_reviewed_output(final_state, reviewed_latex)
    saved_path = updated_state.get("saved_pdf_path", "")
    if not saved_path:
        errors = "\n".join(updated_state.get("errors", [])) or "Save failed."
        return None, errors, updated_state
    safe_path = _safe_file_output(saved_path)
    if not safe_path:
        return None, f"Expected a saved PDF file but got: {saved_path}", updated_state
    return safe_path, f"Saved approved PDF to {safe_path}", updated_state


def build_ui() -> gr.Blocks:
    config = get_config()
    with gr.Blocks(title="ResumeForge - Resume Tailoring Agent") as demo:
        gr.Markdown("# ResumeForge - Resume Tailoring Agent")
        gr.Markdown("Using static test inputs from the `test_files` folder for now. Generate a preview and review the filled LaTeX output.")

        with gr.Row():
            with gr.Column():
                gr.Markdown(f"JD: `{resolve_path(config.get('default_jd_txt', ''))}`")
                gr.Markdown(f"Template: `{resolve_path(config['default_resume_tex'])}`")
                gr.Markdown(f"Projects Inventory: `{resolve_path(config['default_projects_md'])}`")
                output_folder = gr.Textbox(
                    label="Output Folder",
                    value=str(resolve_path(config.get("default_output_folder", "outputs"))),
                )
                stage1_model = gr.Dropdown(
                    label="Stage 1 Model (Selection)",
                    choices=["groq", "openrouter", "cohere", "copilot"],
                    value=config.get("stage1_model", "groq"),
                )
                stage2_model = gr.Dropdown(
                    label="Stage 2 Model (Writing)",
                    choices=["groq", "cohere", "openrouter", "copilot"],
                    value=config.get("stage2_model", "groq"),
                )
                enrich_toggle = gr.Checkbox(
                    label="Enrich with web search",
                    value=bool(config.get("enrich_with_web_search", False)),
                )
                gr.Markdown(f"Using root skill file: `{resolve_path(config['default_skills_md'])}`")
                run_button = gr.Button("Generate Preview", variant="primary")

            with gr.Column():
                ats_badge = gr.HTML()
                with gr.Tabs():
                    with gr.Tab("ATS Analysis"):
                        ats_analysis = gr.Markdown()
                    with gr.Tab("Changes Made"):
                        changes_md = gr.Markdown()
                    with gr.Tab("LaTeX Preview"):
                        latex_preview = gr.Code(language="latex", lines=24)
                        edit_request = gr.Textbox(
                            label="Ask AI to edit this preview",
                            placeholder="Example: Make the bullets more concise and emphasize backend APIs.",
                            lines=3,
                        )
                        apply_edit_button = gr.Button("Apply AI Edit")
                        edit_status = gr.Textbox(label="Edit Status", lines=2)
                    with gr.Tab("Preview PDF"):
                        pdf_file = gr.File(label="Preview PDF", type="filepath")
                    with gr.Tab("Logs"):
                        log_preview = gr.Textbox(label="Run Log", lines=18)
                status_box = gr.Textbox(label="Status Log", lines=10)
                error_box = gr.Textbox(label="Errors", lines=8)
                save_button = gr.Button("Approve & Save PDF")
                save_status = gr.Textbox(label="Save Status", lines=2)
                saved_pdf_file = gr.File(label="Saved PDF", type="filepath")

        state_store = gr.State({})

        run_button.click(
            fn=_run_resumeforge,
            inputs=[output_folder, stage1_model, stage2_model, enrich_toggle],
            outputs=[ats_badge, ats_analysis, changes_md, latex_preview, pdf_file, status_box, error_box, log_preview, state_store],
        )
        apply_edit_button.click(
            fn=_apply_ai_edit_request,
            inputs=[latex_preview, edit_request, stage2_model],
            outputs=[latex_preview, edit_status],
        )
        save_button.click(
            fn=_save_preview,
            inputs=[state_store, latex_preview],
            outputs=[saved_pdf_file, save_status, state_store],
        )
    return demo


def run_test_mode() -> int:
    config = get_config()
    initial_state = {
        "jd_text": resolve_path(config.get("default_jd_txt", "test_files/jd.txt")).read_text(encoding="utf-8"),
        "original_resume_tex": str(config["default_resume_tex"]),
        "skills_md": str(config["default_skills_md"]),
        "projects_context": str(config["default_projects_md"]),
        "output_folder": str(resolve_path(config.get("default_output_folder", "outputs"))),
    }
    final_state = run_agent(initial_state)
    print("Status updates:")
    print("\n".join(final_state["status_updates"]))
    print("\nErrors:")
    print("\n".join(final_state["errors"]) or "None")
    print(f"\nPDF: {final_state['final_pdf_path'] or 'Not generated'}")
    print(f"Report length: {len(final_state['changes_report_md'])}")
    return 1 if final_state["errors"] else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="ResumeForge")
    parser.add_argument("--test", action="store_true", help="Run the agent on bundled sample files.")
    args = parser.parse_args()

    if args.test:
        return run_test_mode()

    demo = build_ui()
    config = get_config()
    demo.launch(
        inbrowser=bool(config.get("open_browser_on_launch", True)),
        server_name="0.0.0.0",
        server_port=int(config.get("gradio_port", 7860)),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
