# 📁 File Structure — ResumeForge

```
resume-forge/
│
├── 📄 README.md
├── 📄 ARCHITECTURE.md
├── 📄 FILE_STRUCTURE.md          ← this file
├── 📄 IMPLEMENTATION_GUIDE.md
├── 📄 SETUP.md
│
├── 🚀 run.bat                    ← Windows: double-click to launch
├── 🚀 run.sh                     ← Linux/Mac: ./run.sh to launch
│
├── ⚙️  config.yaml               ← all user settings in one place
├── 🔒 .env                       ← API keys (never commit this)
├── 🔒 .env.example               ← template for .env (safe to commit)
├── 📄 .gitignore
│
├── 📂 app/                       ← all Python source code
│   │
│   ├── 📄 main.py                ← Gradio UI entry point
│   │
│   ├── 📂 agent/                 ← LangGraph agent
│   │   ├── 📄 graph.py           ← graph definition (nodes + edges)
│   │   ├── 📄 state.py           ← ResumeState TypedDict
│   │   └── 📄 nodes/
│   │       ├── 📄 load_inputs.py
│   │       ├── 📄 parse_resume.py
│   │       ├── 📄 analyze_jd.py
│   │       ├── 📄 tailor_section.py
│   │       ├── 📄 validate_output.py
│   │       ├── 📄 assemble_latex.py
│   │       ├── 📄 compile_pdf.py
│   │       ├── 📄 generate_report.py
│   │       └── 📄 save_and_display.py
│   │
│   ├── 📂 llm/                   ← LLM provider wrappers
│   │   ├── 📄 router.py          ← picks which model based on config + fallback
│   │   ├── 📄 gemini.py          ← Gemini Flash (Stage 1)
│   │   ├── 📄 openrouter.py      ← OpenRouter free models (Stage 2)
│   │   ├── 📄 cohere.py          ← Cohere Command R (fallback)
│   │   └── 📄 copilot.py         ← GitHub Models API (optional upgrade)
│   │
│   ├── 📂 prompts/               ← all prompt templates as strings
│   │   ├── 📄 stage1_ats.py
│   │   ├── 📄 stage2_polish.py
│   │   ├── 📄 analyze_jd.py
│   │   └── 📄 generate_report.py
│   │
│   ├── 📂 parsers/               ← file parsing utilities
│   │   ├── 📄 latex_parser.py    ← splits .tex into sections dict
│   │   ├── 📄 latex_assembler.py ← injects new bullets back into .tex
│   │   ├── 📄 jd_parser.py       ← extracts company/role from JD text
│   │   └── 📄 projects_parser.py ← reads projects.md → dict
│   │
│   └── 📂 utils/
│       ├── 📄 validator.py       ← validation checks before PDF compile
│       ├── 📄 file_namer.py      ← smart PDF naming logic
│       └── 📄 logger.py          ← logs every prompt/response for debugging
│
├── 📂 inputs/                    ← default input files (your base files)
│   ├── 📄 skills.md              ← YOUR style guide (most important file)
│   ├── 📄 projects.md            ← all your projects with descriptions
│   └── 📄 base_resume.tex        ← your master LaTeX resume template
│
├── 📂 outputs/                   ← all generated files land here
│   ├── 📄 .gitkeep
│   └── 📂 history/               ← timestamped copies of every run
│       └── 📄 2026-04-19_Google_SWE/
│           ├── 📄 Google_SWE_2026-04.pdf
│           ├── 📄 Google_SWE_2026-04.tex
│           └── 📄 changes_report.md
│
├── 📂 tests/                     ← optional: sample files for testing
│   ├── 📄 sample_jd.txt
│   └── 📄 sample_resume.tex
│
└── 📂 logs/                      ← prompt/response logs per run
    └── 📄 .gitkeep
```

---

## Key Files Explained

### `config.yaml` — Your control panel
```yaml
# Model settings
stage1_model: "gemini-flash"       # Options: gemini-flash
stage2_model: "openrouter"         # Options: openrouter, cohere, copilot

# OpenRouter model (free tier options)
openrouter_model: "mistralai/mistral-7b-instruct:free"
# Other free options:
# "meta-llama/llama-3.1-8b-instruct:free"
# "google/gemma-2-9b-it:free"

# Default file paths (so you don't re-upload every time)
default_skills_md: "inputs/skills.md"
default_projects_md: "inputs/projects.md"  
default_resume_tex: "inputs/base_resume.tex"
default_output_folder: "outputs/"

# Behavior
save_history: true                  # Keep timestamped copies of every run
open_browser_on_launch: true
log_prompts: true                   # Save all prompts/responses to logs/

# PDF naming
auto_name_pdf: true                 # Google_SWE_2026-04.pdf
fallback_name: "Tailored_Resume"    # Used if company/role extraction fails

# Validation thresholds
keyword_coverage_threshold: 0.70   # 70% of JD keywords must appear in output
max_retries_per_section: 2
```

### `.env` — API Keys
```bash
# Required
GOOGLE_API_KEY=your_gemini_key_here

# Choose one for Stage 2 (or both for fallback)
OPENROUTER_API_KEY=your_openrouter_key_here
COHERE_API_KEY=your_cohere_key_here

# Optional: GitHub Copilot Pro upgrade
GITHUB_TOKEN=your_github_pat_here
```

### `inputs/skills.md` — The Most Important File
This is injected into every LLM call as the system prompt foundation.  
It should contain:
- How your bullets should sound (tone, voice, style)
- What to emphasize (impact > tasks)
- Your technical depth preferences
- Example bullets (good vs bad)
- Domain-specific terminology you use

The better this file, the better every output will be.

### `inputs/projects.md` — Project Context
```markdown
# Projects

## ProjectName1
**Tech stack**: Python, FastAPI, PostgreSQL
**What it does**: [2-3 sentence description]
**Key achievements**: [metrics, impact, scale]
**Keywords**: [terms that describe it]

## ProjectName2
...
```

The agent uses this to inject accurate context when a section mentions a project by name — preventing hallucination and enabling richer, more specific bullets.
