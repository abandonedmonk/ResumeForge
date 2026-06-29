# 📁 File Structure — ResumeForge

```
ResumeForge/
├── app/
│   ├── main.py                     # Gradio UI + CLI (`python -m app.main [--test]`)
│   ├── agent/
│   │   ├── graph.py                # LangGraph build + run_agent()
│   │   ├── state.py                # ResumeState TypedDict + default_state()
│   │   └── nodes/                  # one file per pipeline node (see ARCHITECTURE.md)
│   │       ├── load_inputs.py  parse_resume.py  analyze_jd.py
│   │       ├── score_original.py  enrich_company.py  generate_projects.py
│   │       ├── tailor_section.py  validate_output.py  assemble_latex.py
│   │       ├── compile_pdf.py  enforce_one_page.py  score_resume.py
│   │       └── generate_report.py  generate_cover_letter.py  generate_docx.py  save_and_display.py
│   ├── llm/                        # provider layer
│   │   ├── base.py  router.py      # BaseLLM + RoutedModel (tiered chains)
│   │   ├── keypool.py  keystore.py # multi-key rotation + session keys
│   │   └── groq.py openrouter.py gemini.py cohere.py copilot.py openai_gpt.py anthropic_claude.py
│   ├── parsers/
│   │   ├── template_registry.py    # load templates/<name>/
│   │   ├── projects_parser.py      # project-profile .md → structured data
│   │   ├── jd_parser.py            # company/role extraction + fetch_jd_from_url
│   │   ├── latex_parser.py  latex_assembler.py   # parse / inject LaTeX
│   │   ├── profile_template_builder.py           # Profile → personal template.tex
│   │   └── docx_builder.py         # final content → clean ATS .docx
│   ├── prompts/                    # build_*_prompt(...) -> (system, user)
│   │   ├── analyze_jd.py  stage1_ats.py  stage2_polish.py  score_resume.py
│   │   ├── generate_personalization.py  generate_report.py  cover_letter.py
│   │   └── profile_from_readme.py  profile_from_resume.py
│   ├── integrations/               # Phase 5–7 ingestion
│   │   ├── github.py  profile_builder.py  profile_store.py  skills_refresh.py
│   │   └── resume_pdf.py  resume_import.py
│   ├── profiles/                   # structured candidate profile (Phase 6)
│   │   ├── schema.py               # Contact/Education/Experience/Certification/Profile
│   │   └── profile_store.py        # load/save profile.yaml + personal template resolver
│   └── utils/
│       ├── config.py  exceptions.py  logger.py
│       ├── file_namer.py  json_utils.py  keyword_matcher.py  validator.py
│       └── tex_bootstrap.py        # minimal TinyTeX install + tlmgr package set
├── templates/
│   ├── classic/   template.tex  scaffold.tex  config.json
│   └── modern/    template.tex  config.json
├── inputs/                         # bundled sample projects (showcase)
│   └── project_profiles/*.md
├── test_files/                     # sample JD + example résumés
├── examples/
│   ├── skills.md.example           # neutral starter style guide (copy this)
│   └── my_profile/                 # YOUR personal data (gitignored)
├── tests/                          # pytest suite (mocked LLM/network)
├── docs/                           # this folder
├── .github/workflows/ci.yml        # ruff + pytest
├── config.yaml                     # tracked defaults
├── config.local.yaml               # personal overrides (gitignored)
├── requirements.txt  requirements-dev.txt
├── Dockerfile  docker-compose.yml
├── run.sh  run.ps1  run.bat         # one-command bootstrap launchers
└── README.md  CHANGELOG.md  CONTRIBUTING.md  LICENSE
```

**Where things live:** new pipeline step → `app/agent/nodes/` (+ wire in `graph.py`); new provider → `app/llm/`; new input format → `app/parsers/` (+ `load_inputs.py`); new template → `templates/<name>/`. Personal data and outputs are gitignored (`examples/my_profile/`, `config.local.yaml`, `.env`, `outputs/`).
