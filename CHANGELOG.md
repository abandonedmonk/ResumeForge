# Changelog

All notable changes to ResumeForge. This project was built in phases; each entry
maps to a merged phase on `main`.

## [Unreleased]

### Phase 12 — LaTeX semantic branching
- **"git for your résumé"** — keep named tailored forks of your `.tex` and diff them:
  `resumeforge branch new/list/show/delete`, `resumeforge diff <a> <b>` (unified diff, `--json`),
  and `tailor --branch <name>` now persists the result as a branch. Branches live in
  `~/.resumeforge/branches/<name>/` (built on the Phase 10 run-store); `new` seeds from another
  branch, a run, or a `.tex` file. Lightweight (versioned saves + diff) — no fork/merge semantics.
- CLI output now forced to **UTF-8** on every platform (fixes a Windows cp1252 crash on non-Latin-1
  résumé text and keeps `--json` clean).

### Phase 11 — Agent-skill distribution + JSON CLI output
- **`--json` on every result command** (`tailor`, `roast`, `cold-read`, `gap`, `receipt`) — a single machine-readable JSON object on stdout, so agents (and scripts) can parse results. Human text stays the default.
- **Open-Agent-Skill package** (`skill/`): `SKILL.md` (when-to-use triggers + per-command `--json` invocation + output schemas), `agents/claude.yaml` + `agents/openai.yaml`, one-command `scripts/install.sh`, and a per-agent `README.md`. Makes ResumeForge invocable from Claude Code / Codex / Gemini CLI / OpenCode — the résumé-generation upgrade that runs on the free cascade instead of the host agent's paid model.

### Phase 10 — CLI + standalone features
- **Installable CLI** (`pipx install resumeforge`): `resumeforge {ui,init,tailor,cold-read,roast,gap,receipt}`. Runs the existing pipeline headless; the Gradio app is now `resumeforge ui`. Packaging via a proper `[build-system]` + `[project.scripts]` entry point.
- **Compression Receipt** — every `tailor` run emits an auditable `receipt.json` (words removed, bullets strengthened/condensed, keyword deltas, semantic similarity). 0-token, local.
- **Cold Read Simulator** (`cold-read`) — adversarial zero-context read: targeted role / strongest qualification / biggest gap.
- **Resume Roaster** (`roast`) — brutally honest, shareable `[ROAST] → [FIX]` feedback; optional JD-scoped.
- **GitHub Gap-Finder** (`gap`) — 3-stage (local pre-filter → local summarise → one grounded LLM call) delta between what you built on GitHub and what your résumé claims.
- Run artifacts written to `~/.resumeforge/runs/<run-id>/`. New task routes (`cold_read`, `roast`, `gap_analysis`) + `fetch_user_repos`. Test + lint green (`pytest`, `ruff`).

### Phase 9 — Smart task-aware, token-budget routing
- Route each task to its best provider (Groq writes, Gemini scores ATS), auto-detected from available keys; oversized prompts skip to a bigger-context model and trim only as a last resort. Provider guide in `docs/PROVIDERS.md`.

### Phase 8 — Open-source readiness
- Root `README.md` with feature matrix, quick start, and a Mermaid architecture diagram.
- GitHub Actions CI (`ruff` + `pytest` on Python 3.11 & 3.12); `requirements-dev.txt`.
- Unit-test backfill for core utilities (json, keyword matcher, file namer, validator, key-pool rotation, template registry, page-count parser); shared `tests/conftest.py`.
- Repo is lint-clean (`ruff check .`).
- Neutral `examples/skills.md.example`; the owner's personal style guide is now gitignored. Docs overhaul (ROADMAP/ARCHITECTURE/FILE_STRUCTURE refreshed; build history split out).

### Phase 7 — Star features + one-command minimal-TeX start
- One-command bootstrap (`run.sh` / `run.ps1` / `run.bat`) that installs a minimal **TinyTeX** (only the LaTeX packages the templates use) when `pdflatex` is missing.
- Optional **cover letter**, clean ATS **DOCX** export, **JD-from-URL** fetch, and **Docker** packaging.

### Phase 6 — Profile ingestion + light UI
- Build a personal résumé from structured **identity / education / experience / certifications** (forms or résumé-PDF auto-fill) — no hand-written LaTeX.
- Soft theme + before→after ATS banner. Experience bullets are now JD-tailored (parser fix).

### Phase 5 — GitHub profile builder
- Import projects from **GitHub repo URLs** (README → grounded project profile); reusable, gitignored profiles; lightweight skills refresh.

### Phase 4 — Smart optimization loop
- Reusable scorer, before→after baseline, auto-optimize loop with grounded missing-keyword injection and a "best achievable" message.

### Phase 3 — Templates & strict one page
- Template registry (`classic`, `modern`), page-count parsing, deterministic condense-then-polish one-page enforcement.

### Phase 2 — Tiered model access
- Free cascade + multi-key rotation/backoff, premium BYO-key adapters (OpenAI, Anthropic), in-UI session keys.

### Phase 1 — Foundation
- Single routed model layer, config layering with gitignored overrides, de-personalization, node hardening, hygiene files.
