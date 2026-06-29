# Changelog

All notable changes to ResumeForge. This project was built in phases; each entry
maps to a merged phase on `main`.

## [Unreleased]

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
