# ⚙️ Setup Guide — ResumeForge

## Prerequisites

Install these once. Then never again.

### 1. Python 3.11+
- **Windows**: Download from https://python.org → check "Add to PATH" during install
- **Linux**: `sudo apt install python3.11 python3.11-venv`

### 2. LaTeX (for PDF compilation)
- **Windows**: Install MiKTeX → https://miktex.org/download (choose "Install for all users")
- **Linux**: `sudo apt install texlive-full` (large download, ~4GB, worth it)
- **Verify**: Open terminal → `pdflatex --version` → should show version number

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

---

## First-Time Setup (5 minutes)

```bash
# 1. Clone or download the project
git clone <repo-url>
cd resume-forge

# 2. Create virtual environment
python -m venv .venv

# 3. Activate it
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Set up your .env file
cp .env.example .env
# Open .env and paste your API keys

# 6. Set up your input files
# Copy your skills.md to inputs/skills.md
# Copy your projects file to inputs/projects.md
# Copy your resume to inputs/base_resume.tex

# 7. Run!
# Windows: double-click run.bat
# Linux:
./run.sh
```

Browser opens at `http://localhost:7860` automatically.

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

## run.bat (Windows)

```bat
@echo off
call .venv\Scripts\activate
python app/main.py
pause
```

## run.sh (Linux/Mac)

```bash
#!/bin/bash
source .venv/bin/activate
python app/main.py
```

Make it executable once: `chmod +x run.sh`

---

## Common Issues

| Issue | Fix |
|---|---|
| `pdflatex: command not found` | LaTeX not installed or not on PATH. Restart terminal after installing MiKTeX/texlive |
| `GOOGLE_API_KEY not found` | Check `.env` file exists and key has no spaces around `=` |
| `Port 7860 already in use` | Another Gradio app is running. Close it or change port in `config.yaml` |
| OpenRouter returns 429 | Rate limited. Switch `stage2_model` to `cohere` in `config.yaml` |
| PDF compiles but looks wrong | LaTeX injection issue. Check `logs/` for the generated `.tex` file |
| Bullets sound like Gemini (robotic) | Stage 2 model might be failing silently. Check `logs/` for Stage 2 errors |
