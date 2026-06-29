# ResumeForge — Linux Setup Guide

## Fastest path: one command

```bash
git clone <your-repo-url>
cd ResumeForge
cp .env.example .env   # paste at least one key (e.g. GROQ_API_KEY)
./run.sh
```

`run.sh` creates the venv, installs dependencies, and — if `pdflatex` isn't
already present — installs a minimal **TinyTeX** (no sudo) with only the LaTeX
packages the templates need. Everything below is optional/manual.

---

## Prerequisites (manual route)

### 1. LaTeX Compiler (`pdflatex`) — optional, only if you skip `run.sh`'s auto-install

```bash
# Debian / Ubuntu
sudo apt update
sudo apt install texlive-latex-base texlive-fonts-recommended texlive-latex-extra -y

# Fedora / RHEL
sudo dnf install texlive-scheme-basic texlive-collection-latexrecommended
```

Verify:
```bash
pdflatex --version
```

> **Note:** `texlive-latex-extra` is required — resume templates use packages like `enumitem`, `geometry`, `titlesec`, and `hyperref` that are not in the base install. (TinyTeX via `run.sh` pulls exactly these and nothing more.)

---

## Setup

### 2. Clone & Create Conda Environment

```bash
git clone <your-repo-url>
cd ResumeForge

conda create -n resumeforge python=3.11 -y
conda activate resumeforge
```

### 3. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

```bash
cp .env.example .env
nano .env
```

Fill in the keys:

```env
GROQ_API_KEY=your_groq_key          # Required — default provider for both pipeline stages
GOOGLE_API_KEY=your_gemini_key      # Required — used for ATS semantic scoring
OPENROUTER_API_KEY=your_key         # Optional fallback
COHERE_API_KEY=your_key             # Optional fallback
GITHUB_TOKEN=your_github_pat        # Optional — Copilot model fallback
```

Get keys from:
- Groq: https://console.groq.com
- Google: https://aistudio.google.com/app/apikey
- OpenRouter: https://openrouter.ai/keys

### 5. Update `config.yaml` for Linux

The `dest_folder` is set to a Windows path by default. Update it:

```yaml
# Change this Windows path:
dest_folder: "G:/My Drive/Resumes/Applied"

# To a Linux path:
dest_folder: "/home/youruser/Documents/Resumes/Applied"

# Or leave empty to save to the local outputs/ folder:
dest_folder: ""
```

---

## Run

```bash
conda activate resumeforge
cd /path/to/ResumeForge
python -m app.main
```

The Gradio UI will open at `http://localhost:7860` in your browser.

### Test Mode (no UI)

```bash
python -m app.main --test
```

---

## Quick Reference

| Requirement | Source | Required? |
|---|---|---|
| `pdflatex` | `apt install texlive-latex-extra` | ✅ Yes |
| Python 3.11 | Conda | ✅ Yes |
| `GROQ_API_KEY` | console.groq.com | ✅ Yes (default config) |
| `GOOGLE_API_KEY` | aistudio.google.com | ✅ Yes (ATS scoring) |
| `OPENROUTER_API_KEY` | openrouter.ai | ⚡ Optional fallback |
| `COHERE_API_KEY` | cohere.com | ⚡ Optional fallback |
| `GITHUB_TOKEN` | github.com/settings/tokens | ⚡ Optional fallback |
