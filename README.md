# 🎯 ResumeForge

**An AI agent that tailors your résumé to any job description — strictly one page, fully free to run, and you never touch LaTeX.**

[![CI](https://github.com/abandonedmonk/ResumeForge/actions/workflows/ci.yml/badge.svg)](https://github.com/abandonedmonk/ResumeForge/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](pyproject.toml)

Paste a job description (or a posting URL). ResumeForge picks your most relevant projects and skills, rewrites your bullets for ATS, compiles a clean one-page PDF (and a `.docx`), scores the match, and auto-optimizes — then tells you exactly what changed and why.

<!-- TODO(hero): add a screenshot or GIF of the Gradio UI / a before→after PDF here -->

---

## Why ResumeForge

- **100% free to run** — cascades across free LLM providers (Groq → OpenRouter → Gemini → Cohere → GitHub Models) with **multi-key rotation + backoff** to dodge rate limits. No paid key required.
- **Smart, token-aware routing** — sends each task to the right model (Groq writes, Gemini scores ATS), auto-detected from the keys you have; oversized prompts skip to a bigger-context model and trim only as a last resort, so a free Groq key never hits its token cap. ([details](docs/PROVIDERS.md))
- **Premium-ready** — bring your own GPT / Claude / paid Gemini key (via `.env` or pasted in the UI) and flip `model_tier: premium`.
- **Strictly one page** — a deterministic condense loop trims to fit, then AI polishes; auto-allows a 2nd page only for 10+ years of experience or an explicit opt-in.
- **You never write LaTeX** — the AI emits content with `**bold**` markers; Python owns all LaTeX assembly. Vetted templates for every field: `classic`, `modern`, `cs`, `bio`, and a multi-page `academia` CV — pick one in the UI, via `resume_template` in `config.yaml`, or with `--template`.
- **Zero-friction onboarding** — build your profile from **GitHub repo URLs** (reads each README) or by **uploading an existing résumé PDF**; or fill simple forms. No hand-authored input files.
- **One-command setup** — `run.sh` / `run.bat` bootstraps the venv, installs deps, and installs a **minimal TinyTeX** (only the ~14 LaTeX packages used — no 4 GB distro), then launches.

## Feature matrix

| Area | What you get |
|---|---|
| LLM access | Free cascade + multi-key rotation · tiered **free / premium / custom** chains · session keys pasted in-UI (never persisted) |
| Tailoring | Two-stage rewrite (ATS reasoning → prose polish) · grounded, never fabricates · keeps every metric |
| ATS scoring | Keyword + semantic + section-quality + placement + impact sub-scores · **auto-optimize loop** to a target with before→after delta |
| Output | One-page **PDF** · clean ATS-friendly **DOCX** · optional **cover letter** · "what changed & why" report · version history |
| Ingestion | **GitHub** project import · **résumé-PDF** auto-fill · structured profile forms · **JD-from-URL** |
| CLI & standalone features | `resumeforge` binary · **roast** · **cold-read** · GitHub **gap**-finder · auditable **compression receipt** — all headless, reuse the free cascade |
| Run anywhere | One-command `run.sh`/`run.ps1`/`run.bat` · **Docker** (`docker compose up`) · minimal TinyTeX, no admin |

## Quick Start

```bash
git clone https://github.com/abandonedmonk/ResumeForge.git
cd ResumeForge
cp .env.example .env          # paste at least one key, e.g. GROQ_API_KEY

# Linux/macOS:
./run.sh
# Windows (or double-click run.bat):
powershell -ExecutionPolicy Bypass -File run.ps1
```

First run creates the venv, installs dependencies, and — if `pdflatex` isn't already present — installs a minimal TinyTeX (one-time). The UI opens at `http://localhost:7860`.

**Docker:** `cp .env.example .env` then `docker compose up --build` → `http://localhost:7860`.

Get a free key in ~1 minute: [Groq](https://console.groq.com) · [Google AI Studio](https://aistudio.google.com/apikey) · [OpenRouter](https://openrouter.ai/keys) · [Cohere](https://dashboard.cohere.com). One key is enough. You can also bring **Mistral, DeepSeek, Together, or xAI** keys, or run **fully offline with [Ollama](https://ollama.com)** (no key) — see **[which key to pick & how routing works](docs/PROVIDERS.md)**.

## CLI (headless)

Beyond the web UI, ResumeForge installs as a `resumeforge` command that runs the same engine headless:

```bash
pipx install resumeforge      # or: pip install -e .

resumeforge init                              # check LaTeX + provider keys, scaffold .env
resumeforge ui                                # launch the Gradio app (same as python -m app.main)

resumeforge tailor  --jd job.txt              # tailor to a JD (file, URL, or text); --resume <cv.tex> optional
resumeforge tailor  --jd job.txt --template cs   # choose a template: classic | modern | cs | bio | academia
resumeforge roast   --resume cv.pdf           # brutally honest [ROAST] → [FIX] feedback (add --jd for fit-scoped)
resumeforge cold-read --resume cv.pdf --jd job.txt   # zero-context recruiter read
resumeforge gap --github <user> --resume cv.pdf --jd job.txt   # what your résumé misses vs your GitHub
resumeforge receipt --last                    # compression receipt for the most recent run

# git for your résumé — keep tailored forks and diff them
resumeforge tailor --jd ml_job.txt --branch ml-research   # saves the result as a branch
resumeforge branch new quant --from ml-research           # fork (or --from-file cv.tex / --from-run <id>)
resumeforge branch list
resumeforge diff ml-research quant                        # unified diff of two branches' .tex
```

Each `tailor` run writes its artifacts (`resume.tex`, `resume.pdf`, `receipt.json`, optional `cold-read.json`) to `~/.resumeforge/runs/<run-id>/`. Every feature reuses the free multi-provider cascade — no paid key required.

Add `--json` to any result command (`tailor`, `roast`, `cold-read`, `gap`, `receipt`) to get a single machine-readable JSON object on stdout — this is what the agent skill parses.

## Use as an agent skill

ResumeForge ships an **Open-Agent-Skill** package (`skill/`) so Claude Code, Codex, Gemini CLI, and OpenCode can invoke it directly. The agent orchestrates (reads the JD, confirms paths, presents results); ResumeForge does the generation on its **free** cascade — so your paid subscription isn't spent on résumé writing.

```bash
bash skill/scripts/install.sh          # installs the CLI + copies the skill to ~/.claude/skills/
# or manually:
cp -r skill/ ~/.claude/skills/resumeforge/
```

Then just ask your agent: *"roast my resume"*, *"tailor my resume for this JD"*, *"what is my GitHub missing that this role wants"*. See [`skill/README.md`](skill/README.md) for Codex / Gemini setup.

## MCP server (optional)

For MCP clients (Claude Desktop, IDE MCP integrations) ResumeForge also ships a local **stdio MCP server** exposing typed tools — `compile_latex`, `tailor_resume`, `roast_resume`, `cold_read`, `find_github_gap`, `compression_receipt`:

```bash
pip install "resumeforge[mcp]"     # installs the optional MCP dependency
```

Then register it with your client:

```json
{ "mcpServers": { "resumeforge": { "command": "resumeforge-mcp" } } }
```

Same free cascade as everything else; `jd`/`resume` tool args accept raw text, a file path, or (for `jd`) a URL. This is an alternative to the CLI/skill — use whichever your agent speaks.

## How it works

```mermaid
flowchart TD
    A[load_inputs] --> B[parse_resume] --> C[analyze_jd] --> D[score_original]
    D --> E[enrich_company] --> F[generate_projects] --> G[tailor_sections]
    G --> H[validate_output] --> I[assemble_latex] --> J[compile_pdf]
    J -->|pdflatex error| Z([END])
    J -->|ok| K[enforce_one_page] --> L[score_resume]
    L -->|below target & gains left| F
    L -->|target met / plateau / max iters| M[generate_report]
    M --> N[generate_cover_letter] --> O[generate_docx] --> P[save_and_display] --> Z
```

The AI only writes **content**; `app/parsers/latex_assembler.py` converts `**bold**` → `\textbf{}` and injects it into the template's placeholder regions. The optimize loop re-tailors (grounded in each project's full body) until it hits the target ATS score, plateaus, or maxes out — so the loop always terminates.

## Build your profile (pick one)

- **From GitHub** — paste repo URLs in the *Build Profile from GitHub* tab; ResumeForge reads each README and writes a reusable project profile.
- **From an existing PDF** — upload your current résumé in *Build My Profile*; links are extracted reliably and text is parsed (best-effort) to pre-fill the forms.
- **By hand** — fill the contact/education/experience/certifications forms; ResumeForge renders your personal one-page template.

Your personal data stays local (gitignored `examples/my_profile/`); the repo ships only neutral examples.

## Documentation

- [Setup guide](docs/SETUP.md) · [Providers & API keys](docs/PROVIDERS.md) · [Linux setup](docs/linux_setup.md)
- [Architecture](docs/ARCHITECTURE.md) · [File structure](docs/FILE_STRUCTURE.md)
- [Roadmap](docs/ROADMAP.md) · [Changelog](CHANGELOG.md) · [Contributing](CONTRIBUTING.md)

## License

[MIT](LICENSE).
