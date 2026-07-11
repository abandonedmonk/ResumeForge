from __future__ import annotations

import argparse
import sys
from pathlib import Path

import gradio as gr

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agent.graph import run_agent
from app.parsers.template_registry import list_templates
from app.ui.actions import (
    _append_skills_to_file,
    _apply_ai_edit_request,
    _import_github_profiles,
    _list_imported_markdown,
    _profile_autofill_from_pdf,
    _profile_generate,
    _profile_initial_contact,
    _profile_initial_yaml,
    _profile_store_assets,
    _profile_sync_contact,
    _quick_match_jd,
    _refresh_skills_suggestions,
    _run_resumeforge,
    _save_github_profiles,
    _save_preview,
)
from app.ui.render import _routing_markdown
from app.utils.config import get_config, resolve_path


def build_ui() -> gr.Blocks:
    config = get_config()
    with gr.Blocks(title="ResumeForge - Resume Tailoring Agent") as demo:
        gr.Markdown("# ResumeForge - Resume Tailoring Agent")

        with gr.Tabs():
            with gr.Tab("Archetype Matcher (Quick)"):
                gr.Markdown("Skip the generation. Paste a JD and instantly find out which of your 5 pre-made resumes to submit.")
                with gr.Row():
                    with gr.Column(scale=1):
                        matcher_jd = gr.Textbox(label="Paste Job Description", lines=15, max_lines=30)
                        matcher_model = gr.Dropdown(
                            label="Reasoning Model",
                            choices=["groq", "openrouter", "cohere", "copilot"],
                            value=config.get("stage1_model", "groq"),
                        )
                        match_btn = gr.Button("Find Matching Resume", variant="primary")
                    with gr.Column(scale=1):
                        matcher_output = gr.Markdown("Waiting for JD...")

            with gr.Tab("Full Generator (Custom PDF)"):
                gr.Markdown("Generate a fully custom LaTeX resume tailored line-by-line to a JD.")
                with gr.Row():
                    with gr.Column():
                        # ── Job Description input ──────────────────────────────────
                        with gr.Accordion("📋 Paste Job Description", open=False):
                            gr.Markdown(
                                "Paste the full JD text here. Leave blank to use the default JD file from config: "
                                f"`{resolve_path(config.get('default_jd_txt', 'N/A'))}`"
                            )
                            jd_text_input = gr.Textbox(
                                label="Job Description (paste text, or a posting URL)",
                                placeholder="Paste the job description here… or paste a https://… job posting URL",
                                lines=14,
                                max_lines=40,
                            )
                            clear_jd_button = gr.Button("🗑️ Clear JD", size="sm", variant="secondary")
                            clear_jd_button.click(fn=lambda: "", outputs=jd_text_input)

                        # ── Other inputs ───────────────────────────────────────────
                        _templates = list_templates()
                        _tpl_default = config.get("resume_template", "classic")
                        resume_template = gr.Dropdown(
                            label="Resume Template",
                            choices=_templates or [_tpl_default],
                            value=_tpl_default if _tpl_default in _templates else (_templates[0] if _templates else _tpl_default),
                            info="Layout under templates/. Ignored if a personal/custom .tex template is configured.",
                        )
                        gr.Markdown(f"Projects Inventory: `{resolve_path(config['default_projects_md'])}`")
                        output_folder = gr.Textbox(
                            label="Output Folder",
                            value=str(resolve_path(config.get("default_output_folder", "outputs"))),
                        )
                        stage1_model = gr.Dropdown(
                            label="Stage 1 Model (Selection)",
                            choices=["groq", "openrouter", "gemini", "cohere", "copilot", "openai", "anthropic", "mistral", "deepseek", "together", "xai", "ollama"],
                            value=config.get("stage1_model", "groq"),
                        )
                        stage2_model = gr.Dropdown(
                            label="Stage 2 Model (Writing)",
                            choices=["groq", "cohere", "openrouter", "gemini", "copilot", "openai", "anthropic", "mistral", "deepseek", "together", "xai", "ollama"],
                            value=config.get("stage2_model", "groq"),
                        )
                        enrich_toggle = gr.Checkbox(
                            label="Enrich with web search",
                            value=bool(config.get("enrich_with_web_search", False)),
                        )
                        cover_letter_toggle = gr.Checkbox(
                            label="Generate cover letter (extra LLM call)",
                            value=bool(config.get("generate_cover_letter", False)),
                        )
                        model_tier = gr.Dropdown(
                            label="Model Tier",
                            choices=["free", "premium", "custom"],
                            value=config.get("model_tier", "free"),
                            info="free = cascade across free providers · premium = your GPT/Claude/Gemini keys",
                        )
                        with gr.Accordion("🔑 Premium keys (optional, not stored)", open=False):
                            openai_key = gr.Textbox(
                                label="OpenAI API key", type="password", placeholder="sk-…"
                            )
                            anthropic_key = gr.Textbox(
                                label="Anthropic API key", type="password", placeholder="sk-ant-…"
                            )
                        with gr.Accordion("🧭 Providers & Routing", open=False):
                            routing_status = gr.Markdown(_routing_markdown())
                            refresh_routing = gr.Button("Refresh", size="sm")
                            refresh_routing.click(fn=_routing_markdown, inputs=None, outputs=routing_status)
                        gr.Markdown(f"Using root skill file: `{resolve_path(config['default_skills_md'])}`")
                        run_button = gr.Button("Generate Preview", variant="primary")

                    with gr.Column():
                        ats_badge = gr.HTML()
                        ats_delta = gr.HTML()
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
                            with gr.Tab("Cover Letter"):
                                cover_letter_md = gr.Markdown("_Enable \"Generate cover letter\" before running._")
                            with gr.Tab("Preview PDF"):
                                pdf_file = gr.File(label="Preview PDF", type="filepath")
                                docx_file = gr.File(label="Resume (.docx)", type="filepath")
                            with gr.Tab("Logs"):
                                log_preview = gr.Textbox(label="Run Log", lines=18)
                        status_box = gr.Textbox(label="Status Log", lines=10)
                        error_box = gr.Textbox(label="Errors", lines=8)
                        save_button = gr.Button("Approve & Save PDF")
                        save_status = gr.Textbox(label="Save Status", lines=2)
                        saved_pdf_file = gr.File(label="Saved PDF", type="filepath")

            with gr.Tab("Build Profile from GitHub"):
                gr.Markdown(
                    "Paste GitHub repo URLs (one per line). ResumeForge reads each README + "
                    "metadata via the public GitHub API and distills a truthful, reusable project "
                    "profile. Once you save any profile, the imported set replaces the bundled "
                    "examples as your projects source.\n\n"
                    "_Anonymous GitHub API allows ~60 requests/hr; add a token below (or set "
                    "`GITHUB_API_TOKEN`) to raise it to 5000/hr._"
                )
                with gr.Row():
                    with gr.Column(scale=1):
                        repos_input = gr.Textbox(
                            label="GitHub repo URLs (one per line)",
                            placeholder="https://github.com/owner/repo\nowner/another-repo",
                            lines=8,
                        )
                        with gr.Accordion("🔑 GitHub token (optional, not stored)", open=False):
                            github_token_input = gr.Textbox(
                                label="GitHub API token",
                                type="password",
                                placeholder="github_pat_… or ghp_…",
                            )
                        import_btn = gr.Button("Import Repos", variant="primary")
                        import_status = gr.Markdown()
                        gr.Markdown("---")
                        refresh_skills_btn = gr.Button("Suggest Skills from Imports", size="sm")
                        append_skills_btn = gr.Button("Append New Skills to skills.md", size="sm", variant="secondary")
                        skills_suggestions = gr.Markdown()
                        append_skills_status = gr.Markdown()
                    with gr.Column(scale=1):
                        profiles_preview = gr.Code(
                            label="Generated profiles (editable — edits are saved)",
                            language="markdown",
                            lines=24,
                        )
                        save_profiles_btn = gr.Button("Save Profiles", variant="primary")
                        save_profiles_status = gr.Markdown()
                        imported_listing = gr.Markdown(_list_imported_markdown())

            with gr.Tab("Build My Profile"):
                gr.Markdown(
                    "Enter your identity, education, experience, and certifications — or upload an "
                    "existing resume PDF to auto-fill (embedded links extract reliably; text is "
                    "best-effort). ResumeForge renders a personal one-page LaTeX template from this and "
                    "uses it automatically as your resume layout. Certifications appear as text with an "
                    "optional link; uploaded cert files are stored locally as your own evidence."
                )
                _contact_init = _profile_initial_contact()
                with gr.Row():
                    with gr.Column(scale=1):
                        with gr.Accordion("📄 Auto-fill from an existing resume PDF", open=False):
                            resume_pdf_input = gr.File(label="Resume PDF", type="filepath", file_types=[".pdf"])
                            autofill_btn = gr.Button("Auto-fill from PDF")
                            autofill_status = gr.Markdown()
                        gr.Markdown("**Contact**")
                        pf_name = gr.Textbox(label="Full name", value=_contact_init[0])
                        pf_email = gr.Textbox(label="Email", value=_contact_init[1])
                        pf_phone = gr.Textbox(label="Phone", value=_contact_init[2])
                        pf_linkedin = gr.Textbox(label="LinkedIn URL", value=_contact_init[3])
                        pf_github = gr.Textbox(label="GitHub URL", value=_contact_init[4])
                        pf_website = gr.Textbox(label="Website / Portfolio URL", value=_contact_init[5])
                        pf_location = gr.Textbox(label="Location", value=_contact_init[6])
                        sync_contact_btn = gr.Button("Apply contact → profile")
                        with gr.Accordion("📎 Certificate files (stored locally as evidence)", open=False):
                            cert_files = gr.File(
                                label="Cert PDFs / images",
                                type="filepath",
                                file_count="multiple",
                                file_types=[".pdf", ".jpg", ".jpeg", ".png"],
                            )
                            store_assets_btn = gr.Button("Store cert files")
                            assets_status = gr.Markdown()
                    with gr.Column(scale=1):
                        profile_yaml = gr.Code(
                            label="Profile (editable) — edit education / experience / certifications here",
                            language="yaml",
                            lines=24,
                            value=_profile_initial_yaml(),
                        )
                        generate_template_btn = gr.Button("Generate My Template", variant="primary")
                        generate_status = gr.Markdown()
                        rendered_tex_preview = gr.Code(label="Rendered template (.tex)", language="latex", lines=14)

        state_store = gr.State({})

        autofill_btn.click(
            fn=_profile_autofill_from_pdf,
            inputs=[resume_pdf_input],
            outputs=[profile_yaml, pf_name, pf_email, pf_phone, pf_linkedin, pf_github, pf_website, pf_location, autofill_status],
        )
        sync_contact_btn.click(
            fn=_profile_sync_contact,
            inputs=[profile_yaml, pf_name, pf_email, pf_phone, pf_linkedin, pf_github, pf_website, pf_location],
            outputs=[profile_yaml, generate_status],
        )
        store_assets_btn.click(
            fn=_profile_store_assets,
            inputs=[cert_files],
            outputs=[assets_status],
        )
        generate_template_btn.click(
            fn=_profile_generate,
            inputs=[profile_yaml],
            outputs=[generate_status, rendered_tex_preview],
        )

        import_btn.click(
            fn=_import_github_profiles,
            inputs=[repos_input, github_token_input],
            outputs=[profiles_preview, import_status],
        )
        save_profiles_btn.click(
            fn=_save_github_profiles,
            inputs=[profiles_preview],
            outputs=[save_profiles_status, imported_listing],
        )
        refresh_skills_btn.click(
            fn=_refresh_skills_suggestions,
            inputs=[],
            outputs=[skills_suggestions],
        )
        append_skills_btn.click(
            fn=_append_skills_to_file,
            inputs=[],
            outputs=[append_skills_status],
        )

        match_btn.click(
            fn=_quick_match_jd,
            inputs=[matcher_jd, matcher_model],
            outputs=[matcher_output],
        )

        run_button.click(
            fn=_run_resumeforge,
            inputs=[output_folder, stage1_model, stage2_model, enrich_toggle, jd_text_input, model_tier, openai_key, anthropic_key, cover_letter_toggle, resume_template],
            outputs=[ats_badge, ats_delta, ats_analysis, changes_md, latex_preview, pdf_file, status_box, error_box, log_preview, state_store, cover_letter_md, docx_file],
        )
        apply_edit_button.click(
            fn=_apply_ai_edit_request,
            inputs=[latex_preview, edit_request, stage2_model, output_folder],
            outputs=[latex_preview, edit_status, pdf_file],
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
        theme=gr.themes.Soft(),
        inbrowser=bool(config.get("open_browser_on_launch", True)),
        server_name="0.0.0.0",
        server_port=int(config.get("gradio_port", 7860)),
        allowed_paths=[config["dest_folder"]] if config.get("dest_folder") else [],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
