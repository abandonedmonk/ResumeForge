# ⚙️ Setup Guide — ResumeForge

## Prerequisites

Install these once. Then never again.

### 1. Python 3.11+
- **Windows**: Download from https://python.org → check "Add to PATH" during install
- **Linux**: `sudo apt install python3.11 python3.11-venv`

### 2. LaTeX (for PDF compilation) — installed automatically
You no longer need to install a multi-GB TeX distribution. The one-command start
(`run.sh` / `run.bat`) detects whether `pdflatex` is present and, if not,
installs **TinyTeX** (~150–300MB, no admin) and pulls only the ~14 LaTeX packages
the templates use. Nothing to do here unless you prefer to manage TeX yourself.

- **Manual fallback** (optional): if you already have/ want a system TeX —
  Windows: [MiKTeX](https://miktex.org/download); Linux: `sudo apt install texlive-latex-base texlive-latex-recommended texlive-latex-extra texlive-fonts-recommended`.
- **Verify**: `pdflatex --version` shows a version number.

### 3. Git (optional but recommended)
- https://git-scm.com/downloads

---

## Getting Your Free API Keys

### 🔑 Gemini Flash (Required — Stage 1 ATS brain)
1. Go to https://aistudio.google.com/apikey
2. Sign in with Google account
3. Click "Create API Key"
4. Copy it → paste into `.env` as `GOOGLE_API_KEY=...`
5. Free tier: **1,500 requests/day**, **1 million tokens/minute** — more than enough

### 🔑 OpenRouter (Required — Stage 2 prose polish)
1. Go to https://openrouter.ai/
2. Sign up (free)
3. Go to Keys → Create Key
4. Copy it → paste into `.env` as `OPENROUTER_API_KEY=...`
5. Free tier: Free models available (Mistral 7B, Llama 3.1, Gemma 2) — no credit card needed
   - Look for models with `:free` suffix at https://openrouter.ai/models?q=free

### 🔑 Cohere (Optional — fallback if OpenRouter is rate-limited)
1. Go to https://dashboard.cohere.com/
2. Sign up → verify email
3. Go to API Keys → copy trial key
4. Paste into `.env` as `COHERE_API_KEY=...`
5. Free trial: **1,000 API calls/month**

### 🔑 GitHub Models API (Optional — Copilot Pro upgrade)
> Use this if you want GPT-4o or Claude Sonnet quality for Stage 2 using your existing Copilot Pro subscription

1. Go to https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Scopes: check `models:read` (under "GitHub Models" section — may show as "Access GitHub Models APIs")
4. Generate → copy token
5. Paste into `.env` as `GITHUB_TOKEN=ghp_...`
6. In `config.yaml`: set `stage2_model: "copilot"`
7. This gives you access to: GPT-4o, Claude Sonnet 4.5, Mistral Large — free with your Pro plan

### Free vs Premium tier

- **Free (default, `model_tier: free`):** any one free key works; ResumeForge cascades across providers and rotates multiple keys (`GROQ_API_KEY`, `GROQ_API_KEY_1`, …) to dodge rate limits.
- **Premium (`model_tier: premium`):** add `OPENAI_API_KEY` and/or `ANTHROPIC_API_KEY` (in `.env` or pasted into the UI — session keys are never persisted). The premium chain prefers GPT/Claude, then falls back to free providers.

### Building your profile (no input files to hand-edit)

You don't need to author `skills.md`/projects/résumé by hand. In the app:
- **Build Profile from GitHub** — paste repo URLs; ResumeForge reads each README into a project profile.
- **Build My Profile** — fill the forms, or upload an existing résumé **PDF** to auto-fill them.

Copy `examples/skills.md.example` to your own gitignored `examples/my_profile/skills.md` and point `default_skills_md` at it in `config.local.yaml` to customize the writing style.

---

## First-Time Setup (one command)

```bash
# 1. Clone the project
git clone <repo-url>
cd resume-forge

# 2. Add your API keys
cp .env.example .env      # then open .env and paste at least one key (e.g. GROQ_API_KEY)

# 3. Start it — this creates the venv, installs deps, and installs minimal TeX on first run
#    Linux/macOS:
./run.sh
#    Windows (double-click run.bat, or):
powershell -ExecutionPolicy Bypass -File run.ps1
```

The first run takes a few minutes (venv + dependencies + a one-time minimal TinyTeX
install if `pdflatex` isn't already present). Subsequent runs start instantly.
Browser opens at `http://localhost:7860` automatically.

> **Docker alternative:** `cp .env.example .env` then `docker compose up --build` → serves on `http://localhost:7860`.

You can build your profile (identity, projects, education, experience, certs)
right in the UI — no need to hand-place input files.

---

## `requirements.txt`

```
langgraph>=0.2.0
langchain>=0.3.0
langchain-google-genai>=2.0.0
langchain-cohere>=0.3.0
gradio>=5.0.0
python-dotenv>=1.0.0
pyyaml>=6.0
openai>=1.0.0          # used for OpenRouter (OpenAI-compatible) + GitHub Models
requests>=2.31.0
```

---

## Verifying Everything Works

After setup, run the test mode:

```bash
python app/main.py --test
```

This runs the agent on `tests/sample_jd.txt` + `tests/sample_resume.tex` and should:
- Print "All API connections OK ✅"
- Generate a test PDF in `outputs/`
- Print a sample changes report

If something fails, the error message will tell you exactly which API key is missing or wrong.

---

## Launchers

`run.sh` (Linux/macOS) and `run.ps1`/`run.bat` (Windows) are **one-command bootstrappers**:
they create `.venv`, install dependencies on first run, ensure a minimal TeX
toolchain (TinyTeX) is present, then launch the app. Re-running them is cheap —
the venv/TeX steps are skipped once their markers (`.venv/.installed`,
`.venv/.tex_ready`) exist. On Linux make it executable once: `chmod +x run.sh`.

---

## Common Issues

| Issue | Fix |
|---|---|
| `pdflatex: command not found` | Re-run `./run.sh` (or `run.bat`) to auto-install TinyTeX, or run `python -m app.utils.tex_bootstrap`. Restart the terminal afterward so PATH updates |
| `GOOGLE_API_KEY not found` | Check `.env` file exists and key has no spaces around `=` |
| `Port 7860 already in use` | Another Gradio app is running. Close it or change port in `config.yaml` |
| OpenRouter returns 429 | Rate limited. Switch `stage2_model` to `cohere` in `config.yaml` |
| PDF compiles but looks wrong | LaTeX injection issue. Check `logs/` for the generated `.tex` file |
| Bullets sound like Gemini (robotic) | Stage 2 model might be failing silently. Check `logs/` for Stage 2 errors |
