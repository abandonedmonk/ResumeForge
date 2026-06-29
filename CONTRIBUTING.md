# Contributing to ResumeForge

Thanks for your interest in improving ResumeForge! This guide covers how to get set up and the conventions we follow.

## Getting Started

1. **Fork & clone** the repository.
2. **Create a virtual environment** and install dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate        # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   pip install ruff pytest          # dev tools
   ```
3. **Copy `.env.example` to `.env`** and add at least one provider API key (Groq is the recommended free default).
4. **Install a LaTeX distribution** (TeX Live, MiKTeX, or MacTeX) so `pdflatex` is on your PATH.
5. Run the app: `bash run.sh` (or `run.bat` on Windows).

## Project Layout

- `app/agent/` — LangGraph state machine (`graph.py`, `state.py`) and pipeline `nodes/`.
- `app/llm/` — provider adapters behind a single `RoutedModel` router. **Never call a provider directly from a node** — always go through `RoutedModel`.
- `app/parsers/` — LaTeX/JD/project parsing and assembly.
- `app/prompts/` — prompt builders.
- `app/utils/` — config, logging, validation, keyword matching, JSON extraction.
- `tests/` — pytest suite (mock the LLM layer; no network in tests).

## Conventions

- **Style:** `ruff check .` must pass. Line length is 120.
- **Config:** add new tunables to `config.yaml` with a sensible default and read them via `get_config()`. Keep personal values in a gitignored `config.local.yaml`.
- **No personal data** in committed code — names, emails, and URLs come from config.
- **State:** every node takes and returns a `ResumeState`; add new fields to both `ResumeState` and `default_state()`.

## Submitting Changes

1. Create a feature branch.
2. Run `ruff check .` and `pytest tests/ -v` locally.
3. Open a pull request describing the change and how you tested it.

CI runs lint + tests on every push and pull request.
