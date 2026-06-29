# 🎯 ResumeForge — Automated Resume Tailoring Agent

> Upload a JD. Get a tailored PDF. Know exactly what changed and why.  
> No copy-pasting. No reformatting. No token limits. Fully free APIs.

---

## The Problem You're Solving

Your current workflow is a **3-tool relay race**:

```
JD → Gemini (rewrites bullets) → Claude (improves prose, but hits token limit)
   → you manually copy-paste → Word (reformat) → Save as PDF → rename file → done
```

**Pain points:**
- Gemini bullets are ATS-optimized but sound robotic
- Claude runs out of context on a full resume
- Manual copy-paste breaks formatting every time
- You rename files manually
- You have no record of what changed between versions

---

## The Solution

```
JD (.txt) ──┐
skills.md ──┤
projects.md ─┤──► ResumeForge Agent ──► tailored PDF (auto-named, auto-saved)
resume.tex ──┘                       └──► "What changed & why" report
                                     └──► LaTeX diff (optional)
```

One command. Four files in. One PDF out. Full change log.

---

## What Makes This Better Than The Previous Plan

| Old Plan | ResumeForge |
|---|---|
| Claude Haiku (paid API) | Gemini Flash free tier + Cohere fallback |
| Single LLM pass | **Two-stage pipeline**: Gemini for ATS logic, second model for prose quality |
| No token limit handling | Section-by-section processing → no token overflow ever |
| Manual file naming | Auto-parses company + role from JD → `Google_SWE_2026-04.pdf` |
| No version history | Every run saved with timestamp in `outputs/history/` |
| Gradio only | Gradio UI **+** a clean CLI mode for power users |

### Key Insight: Two-Stage LLM Pipeline

The reason you need Gemini *and* Claude is that they do different things well:

- **Stage 1 — ATS Brain (Gemini Flash free)**: Reads JD, extracts keywords, identifies gaps, rewrites bullets to pass ATS. Fast, structured, logical.
- **Stage 2 — Prose Polish (OpenRouter free tier / Cohere)**: Takes Stage 1 output and makes it sound human, punchy, and impressive. Fixes the "too plain" problem.

This mirrors what you do manually — but automatically, section by section, so you never hit a token limit.

---

## Free API Strategy

| Provider | Model | Use | Free Tier |
|---|---|---|---|
| **Google AI Studio** | Gemini 2.0 Flash | Stage 1: ATS analysis + bullet rewrite | 1500 req/day free |
| **OpenRouter** | Mistral 7B / Llama 3.1 | Stage 2: Prose polish | Free tier available |
| **Cohere** | Command R | Fallback for Stage 2 | 1000 req/month free |
| **GitHub Copilot** | GPT-4o / Claude Sonnet | Optional: final quality check | Your Pro subscription |

> **GitHub Copilot note**: Copilot Pro gives you access to Claude Sonnet and GPT-4o inside VS Code. While there's no official API for custom agents, you can use it as a manual "last mile" quality checker in your IDE after the agent runs — or use the OpenAI-compatible GitHub Models API endpoint (beta, available to Copilot Pro users) which does support programmatic access.

---

## How It Works (User Flow)

1. **Launch**: `./run.sh` or `run.bat` → browser opens at `localhost:7860`
2. **Upload** four files (or use defaults from `inputs/` folder)
3. **Click "Tailor Resume"**
4. **Watch** the live progress log as each section is processed
5. **Get**:
   - PDF auto-saved to your chosen folder as `Company_Role_YYYY-MM.pdf`
   - "Changes Made" tab: before/after for every bullet with reasoning
   - Download button as backup
6. **Done** in ~45 seconds

---

## Project Structure

See `FILE_STRUCTURE.md` for the full layout.  
See `ARCHITECTURE.md` for the technical deep-dive.  
See `IMPLEMENTATION_GUIDE.md` for vibe-coding instructions.

---

## Getting Started

See `SETUP.md`.
