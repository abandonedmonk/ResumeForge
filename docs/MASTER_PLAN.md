# ResumeForge — Master Plan (Execution-Ready)

> **Historical** — this was the original Phase 1–5 execution plan. Phases 6–8 shipped afterward; see [ROADMAP.md](ROADMAP.md) for current status and [../CHANGELOG.md](../CHANGELOG.md) for what landed.

> **Goal:** Turn ResumeForge into a GitHub-star-worthy repo.
> **Principle:** Free-tier only. Zero GPU. Zero cost. Works for everyone.
> **Audience for this doc:** Another AI agent or developer picking this up to execute.

---

## Codebase Overview (Read This First)

**Architecture:** LangGraph state machine. Each node is a Python function in `app/agent/nodes/` that receives a `ResumeState` TypedDict and returns an updated copy. The graph is defined in `app/agent/graph.py`.

**Current pipeline order:**
```
load_inputs → parse_resume → analyze_jd → enrich_company → generate_projects
→ tailor_sections → validate_output → assemble_latex → compile_pdf
→ score_resume → generate_report → save_and_display → END
```

**Key conventions:**
- State is a `TypedDict` defined in `app/agent/state.py` with a `default_state()` factory
- LLM calls go through `app/llm/router.py` which has `RoutedStage1Model` (reasoning) and `RoutedStage2Model` (writing)
- Config is loaded from `config.yaml` at project root via `app/utils/config.py`
- Status messages use `log_status(state, "message")` and `log_error(state, "message")` from `app/utils/logger.py`
- JSON extraction from LLM responses uses a regex `_extract_json_blob()` — currently duplicated in 4 files

**Key files by size (largest = most complex):**
- `app/agent/nodes/score_resume.py` — 224 lines (ATS scoring engine)
- `app/agent/nodes/generate_projects.py` — 196 lines (project selection + rewriting)
- `app/parsers/latex_assembler.py` — 149 lines (LaTeX injection)
- `app/parsers/projects_parser.py` — 154 lines (markdown project parsing)
- `app/llm/router.py` — 124 lines (LLM provider routing)
- `app/main.py` — Gradio UI (not audited for line count but large)

---

## Table of Contents

- [Phase 1 — Foundation Fixes](#phase-1--foundation-fixes)
- [Phase 2 — The Optimization Loop](#phase-2--the-optimization-loop)
- [Phase 3 — UI & Experience](#phase-3--ui--experience)
- [Phase 4 — New Features](#phase-4--new-features)
- [Phase 5 — Open-Source Readiness](#phase-5--open-source-readiness)

---

## Phase 1 — Foundation Fixes

### 1.1 Delete Dead Files

| Action | Path | Reason |
|---|---|---|
| DELETE | `test.py` (root) | Not a test — it's an unrelated arXiv paper downloader script. Zero relation to ResumeForge. |
| DELETE | `inputs/project_profiles copy/` | Accidental duplicate of `inputs/project_profiles/` |

---

### 1.2 Extract Shared JSON Utility

**Problem:** `_extract_json_blob()` is copy-pasted in 4 files with identical code:
```python
def _extract_json_blob(text: str) -> str:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    return match.group(0) if match else "{}"
```

**Files containing duplicates:**
- `app/agent/nodes/analyze_jd.py`
- `app/agent/nodes/enrich_company.py`
- `app/agent/nodes/generate_projects.py`
- `app/agent/nodes/score_resume.py`

**Action:**
1. CREATE `app/utils/json_utils.py` with an improved version that uses bracket-counting instead of greedy regex:
   ```python
   def extract_json_blob(text: str) -> str:
       """Extract the first valid JSON object from LLM response text."""
       # Use json.JSONDecoder().raw_decode() for robustness
       # Fallback to regex if raw_decode fails
       # Return "{}" if nothing found
   ```
2. In each of the 4 files above, replace `from ... import _extract_json_blob` → `from app.utils.json_utils import extract_json_blob` and delete the local `_extract_json_blob` function.

---

### 1.3 Rewrite LLM Router (Cascading Fallback)

**Current code in `app/llm/router.py` (124 lines):**
- `RoutedStage1Model` (lines 86-123) and `RoutedStage2Model` (lines 46-83) are 95% identical — the only differences are: default temperature (0.2 vs 0.4), config keys for model names, and the stage label string.
- `gemini` is in `_provider_map()` (line 21) but NOT in `self.order` (lines 56, 96) — Gemini is unreachable.
- Unknown provider names silently default to OpenRouter: `providers.get(name, OpenRouterFree)` (line 27). Should raise `ConfigError`.
- Config has `groq_fallback_fast_model` and `groq_fallback_reasoning_model` — the Groq inner loop on lines 68-74 and 108-114 DOES try them, but `gemini` is never attempted.

**Action — rewrite `app/llm/router.py`:**
```python
class RoutedModel:
    """Single parameterized router for both stages."""
    def __init__(self, stage: str) -> None:
        # stage is "stage1" or "stage2"
        config = get_config()
        self.stage = stage
        # Read preferred provider and model names from config
        self.preferred = config.get(f"{stage}_model", "groq")
        # Build fallback chain from config, default: ["groq", "openrouter", "gemini", "cohere", "copilot"]
        self.chain = config.get("fallback_chain", ["groq", "openrouter", "gemini", "cohere", "copilot"])
        # Move preferred to front
        if self.preferred in self.chain:
            self.chain.remove(self.preferred)
            self.chain.insert(0, self.preferred)
        # Read Groq model names for this stage
        if stage == "stage1":
            self.groq_models = [
                config.get("groq_reasoning_model", "llama-3.3-70b-versatile"),
                config.get("groq_fallback_reasoning_model", "meta-llama/llama-4-maverick-17b-128e-instruct"),
            ]
            self.default_temp = 0.2
        else:
            self.groq_models = [
                config.get("groq_fast_model", "llama-3.3-70b-versatile"),
                config.get("groq_fallback_fast_model", "meta-llama/llama-4-maverick-17b-128e-instruct"),
            ]
            self.default_temp = 0.4

    def call(self, system_prompt: str, user_prompt: str, temperature: float | None = None) -> str:
        temp = temperature if temperature is not None else self.default_temp
        errors = []
        for provider_name in self.chain:
            try:
                if provider_name == "groq":
                    # Try each Groq model in sequence
                    for model_name in self.groq_models:
                        try:
                            return _get_provider("groq", model_name).call(system_prompt, user_prompt, temp)
                        except (RateLimitError, LLMError, ConfigError) as exc:
                            errors.append(f"groq:{model_name} -> {exc}")
                    continue
                return _get_provider(provider_name).call(system_prompt, user_prompt, temp)
            except (RateLimitError, LLMError, ConfigError) as exc:
                errors.append(f"{provider_name} -> {exc}")
        raise LLMError(f"All {self.stage} providers failed: " + " | ".join(errors))


def _get_provider(name: str, model_name: str | None = None) -> BaseLLM:
    providers = {"groq": GroqModel, "openrouter": OpenRouterFree, "cohere": CohereCommandR, "copilot": CopilotModels, "gemini": GeminiFlash}
    cls = providers.get(name)
    if cls is None:
        raise ConfigError(f"Unknown LLM provider: '{name}'. Valid: {list(providers.keys())}")
    if name == "groq" and model_name:
        return GroqModel(model_name=model_name)
    if name == "gemini" and model_name:
        return GeminiFlash(model_name=model_name)
    return cls()
```

**Also update all call sites.** Search the codebase for `RoutedStage1Model` and `RoutedStage2Model`:
- Replace `RoutedStage1Model()` → `RoutedModel("stage1")`
- Replace `RoutedStage2Model()` → `RoutedModel("stage2")`

**Add to `config.yaml`:**
```yaml
fallback_chain: ["groq", "openrouter", "gemini", "cohere", "copilot"]
```

---

### 1.4 Fix Direct GeminiFlash Bypass

**Problem:** Two nodes bypass the router and call `GeminiFlash()` directly:

1. **`app/agent/nodes/score_resume.py` line 7 and 59:**
   ```python
   from app.llm.gemini import GeminiFlash  # line 7
   response = GeminiFlash(model_name=...).call(...)  # line 59
   ```

2. **`app/agent/nodes/enrich_company.py`** — same pattern, imports and calls `GeminiFlash` directly.

**Action:** In both files:
- Replace `from app.llm.gemini import GeminiFlash` → `from app.llm.router import RoutedModel`
- Replace `GeminiFlash(...).call(...)` → `RoutedModel("stage1").call(...)`
- This way Gemini calls also get fallback protection.

---

### 1.5 Fix LLM Provider Bugs

**All 5 provider files need these fixes:**

#### `app/llm/groq.py` (39 lines)
- **Line 22:** Remove `temperature=0.3` from `ChatGroq()` constructor — it conflicts with the `temperature` parameter passed in `call()`. The `call()` parameter should be the sole source.
- **Line 34:** `text = str(response.content).strip()` — add null check: if `response.content is None`, raise `LLMError("Groq returned empty response")`.

#### `app/llm/gemini.py` (38 lines)
- **Line 21:** Remove `temperature=0.3` from constructor — same bug.
- **Line 33:** Same null-check fix.
- **Line 17:** Config key `gemini_semantic_model` is misleadingly specific. Change to `gemini_model`. Also update `config.yaml` line 29: `gemini_semantic_model` → `gemini_model`.

#### `app/llm/openrouter.py` (38 lines)
- **Lines 18-21:** Simplify the 3-level config fallback: `self.config.get("openrouter_model") or self.config.get("openrouter_free_model", ...)`. Replace with:
  ```python
  self.model = self.config.get("openrouter_model", "openai/gpt-oss-20b:free")
  ```
- **Line 33:** `response.choices[0].message.content.strip()` — add null check. If `content` is None, `None.strip()` throws `AttributeError`.

#### `app/llm/copilot.py` (36 lines)
- **Line 30:** Same null-check fix as openrouter.
- (Error message for missing GITHUB_TOKEN is already good on line 15.)

#### `app/llm/cohere.py` (35 lines)
- **Line 18:** Remove `temperature=0.4` from `ChatCohere()` constructor — same dual-temperature bug.
- Add `model_name: str | None = None` parameter to `__init__` for consistency:
  ```python
  def __init__(self, model_name: str | None = None) -> None:
      super().__init__()
      ...
      self.model = model_name or self.config.get("cohere_model", "command-r")
  ```

#### `app/llm/base.py` (38 lines)
- **Line 4:** Remove unused `from typing import Any`.
- **Line 36:** Change `raise NotImplementedError` to proper `@abc.abstractmethod`.

---

### 1.6 Fix Global Mutable Config

**Problem in `app/utils/config.py`:**
`get_config()` is wrapped in `@lru_cache(maxsize=1)` — returns the SAME dict object every time. `app/main.py` then mutates it: `config["stage1_model"] = stage1_model`. In concurrent Gradio sessions, this causes session A's settings to bleed into session B.

**Action:** Remove `@lru_cache`. Load config once at module level into a private `_config` variable. Have `get_config()` return `copy.deepcopy(_config)`:

```python
import copy

_config: dict[str, Any] | None = None

def get_config() -> dict[str, Any]:
    global _config
    if _config is None:
        load_dotenv(ROOT_DIR / ".env")
        if not CONFIG_PATH.exists():
            raise FileNotFoundError(f"Missing config file at {CONFIG_PATH}")
        with CONFIG_PATH.open("r", encoding="utf-8") as handle:
            _config = yaml.safe_load(handle) or {}
    return copy.deepcopy(_config)
```

---

### 1.7 De-personalize Hardcoded Values

These files contain the author's personal data:

| File | Line(s) | Current Value | Fix |
|---|---|---|---|
| `app/utils/file_namer.py` | L21 | `f"Anshuman Jena {company} {role}"` | `f"{config.get('candidate_name', 'Resume')} {company} {role}"` |
| `app/utils/file_namer.py` | L27 | `"Anshuman Jena Tailored Resume"` | `config.get("fallback_name", "Tailored Resume")` |
| `config.yaml` | L22 | `fallback_name: "Anshuman Jena Tailored Resume"` | `fallback_name: "Tailored Resume"` |
| `config.yaml` | L15 | `dest_folder: "G:/My Drive/Resumes/Applied"` | `dest_folder: ""` |
| `app/parsers/latex_assembler.py` | ~L16 | `DEFAULT_PROJECT_URL = "https://github.com/abandonedmonk"` | `DEFAULT_PROJECT_URL = ""` or read from config |
| `app/prompts/generate_personalization.py` | multiple | Hardcoded "Anshuman Jena" and personal project names | Replace with `{candidate_name}` parameter pulled from config |
| `app/agent/nodes/generate_projects.py` | ~L159 | Fallback headline: `"AI engineer with experience building production RAG systems."` | Generic: `"Software engineer experienced in building production systems."` |
| `app/agent/nodes/generate_projects.py` | L18-35 | `_fallback_skills()` returns specific personal skills | Return empty or generic skills |

**Add to `config.yaml`:**
```yaml
candidate_name: ""  # Your full name, used in PDF filenames
```

---

### 1.8 Fix Pipeline Node Issues

#### `app/agent/nodes/compile_pdf.py`
- Add `timeout=60` to `subprocess.run()` calls
- Wrap temp directory usage in `try/finally` with `shutil.rmtree(tmpdir)` in `finally`
- Replace overly broad warning detection with pdflatex-specific patterns

#### `app/agent/nodes/load_inputs.py`
- After loading `jd_text`, check: `if not state["jd_text"].strip(): raise ResumeForgeError("Job description is empty — cannot proceed.")`
- Add `Path.exists()` checks before reading files

#### `app/agent/nodes/assemble_latex.py`
- Add `try/except` wrapping the assembler call with `log_error(state, ...)`
- Add `log_status(state, "Assembling final LaTeX document...")`

#### `app/agent/nodes/parse_resume.py`
- Add `try/except` wrapping the parser call
- Add `log_status(state, "Parsing resume template...")`
- Move the reset of `generated_headline`, `generated_skills`, etc. (lines 14-17) into `default_state()` in `state.py` (they're already there, so just delete lines 14-17)

#### `app/agent/nodes/validate_output.py`
- Delete dead code: `known_projects = set(...); _ = known_projects`
- When reverting bullets, also update `changes_log` to reflect reversion

#### `app/agent/nodes/score_resume.py`
- **Line 157:** Delete `_ = keyword_frequency(...)` — dead code
- **Lines 172-179:** Move hardcoded weights `0.35, 0.20, 0.15, 0.15, 0.15` to config:
  ```yaml
  # config.yaml
  ats_score_weights:
    keyword_match: 0.35
    semantic_context: 0.20
    section_quality: 0.15
    keyword_placement: 0.15
    impact_metrics: 0.15
  ```
- **Line 201:** Don't store full zone text in state. Replace `"zones": zones` with `"zones": list(zones.keys())`

#### `app/agent/nodes/tailor_section.py`
- Add progress logging: `log_status(state, f"Tailoring section {i+1}/{total}: {section_name}...")`
- Replace `time.sleep(2)` with exponential backoff: `time.sleep(min(2 ** attempt, 8))`

---

### 1.9 Project Hygiene Files

#### CREATE `run.sh` (project root):
```bash
#!/usr/bin/env bash
set -e
# Auto-detect venv or conda
if [ -d ".venv" ]; then source .venv/bin/activate;
elif command -v conda &>/dev/null; then conda activate resumeforge 2>/dev/null || true; fi
python -m app.main "$@"
```

#### REWRITE `.env.example`:
```env
# === REQUIRED (at least one) ===
GROQ_API_KEY=           # https://console.groq.com — primary free provider
GOOGLE_API_KEY=         # https://aistudio.google.com/apikey — ATS semantic scoring

# === OPTIONAL FALLBACKS ===
OPENROUTER_API_KEY=     # https://openrouter.ai/keys — free model access
COHERE_API_KEY=         # https://dashboard.cohere.com/api-keys
GITHUB_TOKEN=           # https://github.com/settings/tokens — Copilot models
```

#### REWRITE `.gitignore` — expand to include:
```gitignore
# Python
__pycache__/
*.py[cod]
*.egg-info/
dist/
build/
.mypy_cache/
.pytest_cache/
.ruff_cache/

# Environment
.env
.venv/

# LaTeX build artifacts
*.aux
*.log
*.synctex*
*.fls
*.fdb_latexmk

# Project outputs
outputs/
.preview/
.log/
scratch/

# IDE
.idea/
.vscode/
*.swp
```

#### CREATE `LICENSE` (MIT) at project root.

#### CREATE `CONTRIBUTING.md` at project root — standard open-source contribution guide.

#### CREATE `pyproject.toml` at project root:
```toml
[project]
name = "resumeforge"
version = "1.0.0"
requires-python = ">=3.11"

[tool.ruff]
line-length = 120
target-version = "py311"

[tool.pytest.ini_options]
testpaths = ["tests"]
```

---

## Phase 2 — The Optimization Loop

### 2.1 Auto-Heal Loop in LangGraph

**Current graph flow (in `app/agent/graph.py`):**
```python
graph.add_edge("score_resume", "generate_report")  # line 58 — always goes to report
```

**New flow:** After `score_resume`, check the score. If below threshold AND iterations remain, loop back.

**Changes to `app/agent/state.py`:**
Add these fields to `ResumeState` and `default_state()`:
```python
optimization_iteration: int      # default: 0
original_ats_score: dict[str, Any]  # default: {}
```

**Changes to `app/agent/graph.py`:**
1. Add a routing function:
```python
def _should_optimize(state: ResumeState) -> str:
    config = get_config()
    if not config.get("auto_optimize", True):
        return "done"
    threshold = config.get("auto_optimize_threshold", 80)
    max_iter = config.get("max_optimize_iterations", 3)
    score = state.get("ats_score", {}).get("overall", 100)
    iteration = state.get("optimization_iteration", 0)
    if score < threshold and iteration < max_iter:
        return "retry"
    return "done"
```
2. Replace line 58 (`graph.add_edge("score_resume", "generate_report")`) with:
```python
graph.add_conditional_edges(
    "score_resume",
    _should_optimize,
    {"retry": "tailor_sections", "done": "generate_report"},
)
```

**Changes to `app/agent/nodes/tailor_section.py`:**
At the start of the function, check `state["optimization_iteration"]`. If > 0, inject the `skills_gap` and `recommendations` into the rewrite prompt so the LLM knows what to fix.

Increment the counter: `state["optimization_iteration"] = state.get("optimization_iteration", 0) + 1`

**Changes to `app/prompts/stage1_ats.py` and `stage2_polish.py`:**
Add an optional "retry context" block to the prompt templates. When `skills_gap` is non-empty, append:
```
IMPORTANT: The following keywords are MISSING from the current resume and MUST be naturally integrated:
Required: {missing_required}
Nice-to-have: {missing_nice_to_have}
```

**Add to `config.yaml`:**
```yaml
auto_optimize: true
auto_optimize_threshold: 80
max_optimize_iterations: 3
```

---

### 2.2 Before vs After ATS Score

**Action:** Score the ORIGINAL resume before tailoring, so the user sees "Before: 42% → After: 87%".

**Changes to `app/agent/nodes/score_resume.py`:**
Extract the main scoring logic (lines 110-222) into a standalone function:
```python
def compute_ats_score(resume_tex: str, jd_analysis: dict, state: ResumeState) -> dict:
    # ... all the existing scoring logic, but operating on the passed-in tex
    # instead of state["final_tex"]
```

**Changes to `app/agent/graph.py`:**
Add a new node `score_original` between `analyze_jd` and `enrich_company`:
```python
def score_original(state: ResumeState) -> ResumeState:
    log_status(state, "Scoring original resume for baseline...")
    state["original_ats_score"] = compute_ats_score(state["original_resume_tex"], state["jd_analysis"], state)
    return state

# In build_graph():
graph.add_node("score_original", score_original)
graph.add_edge("analyze_jd", "score_original")
graph.add_edge("score_original", "enrich_company")
# Remove: graph.add_edge("analyze_jd", "enrich_company")
```

---

### 2.3 Improve Prompts

For each prompt file in `app/prompts/`, add:
1. **Explicit JSON schema** in the prompt text showing the exact expected output structure
2. **One few-shot example** of input → output
3. **Null-handling instructions:** "If a field cannot be determined, return an empty list/string."

**Priority files:**
- `app/prompts/analyze_jd.py` — add JSON schema example
- `app/prompts/score_resume.py` — add 2 examples of contextual vs name_dropped classification
- `app/prompts/stage1_ats.py` — replace `project_context or "None"` with `"No additional context."`; add `tone` and `nice_to_have` fields from JD analysis

---

## Phase 3 — UI & Experience

### 3.1 Side-by-Side Diff View

**In `app/main.py`:** Replace the Changes tab's `gr.Markdown` output with `gr.HTML`. Build an HTML diff table from `state["changes_log"]`. Each entry has `section`, `original`, `tailored` — render with `<span style="background:#d4edda">` for additions and `<span style="background:#f8d7da">` for deletions. Use Python's `difflib.HtmlDiff` or a simple line-by-line comparison.

### 3.2 Real-Time Progress

**In `app/main.py`:** The pipeline function currently blocks until complete. Change it to use Gradio's `yield`-based streaming pattern. After each node completes, yield a status update to the UI. This requires refactoring `run_agent()` to be a generator, or polling `state["status_updates"]` in a separate thread.

### 3.3 Resume History Browser

**In `app/main.py`:** Add a "History" tab that:
1. Scans `outputs/history/` for subdirectories
2. Parses folder names (format: `YYYY-MM-DD_HHMMSS_Company_Role`)
3. Displays a Gradio Dataframe with columns: Date, Company, Role, Download Link

### 3.4 Gradio Theme

**In `app/main.py`:** Add custom CSS for a premium dark-mode look. Use `gr.Blocks(theme=gr.themes.Soft(), css=custom_css)`. Add a logo/banner at the top.

---

## Phase 4 — New Features

### 4.1 Cover Letter Generator

CREATE `app/agent/nodes/generate_cover_letter.py`:
- Use `RoutedModel("stage2")` to generate a cover letter
- Input: `jd_analysis`, `skills_md`, `generated_projects`, `personalization_notes`
- Output: `state["cover_letter_md"]` (markdown text)
- Add `generate_cover_letter: bool` to `ResumeState` and `config.yaml`

CREATE `app/prompts/cover_letter.py`:
- Structure: Opening hook → Why this company → What I bring (2-3 paragraphs matching top JD requirements to projects) → Closing

In `app/agent/graph.py`: Add optional branch — if `config.get("generate_cover_letter")`, add node after `generate_projects`.

In `app/main.py`: Add toggle checkbox and a "Cover Letter" output tab.

### 4.2 DOCX Output

CREATE `app/parsers/docx_builder.py`:
- Use `python-docx` library
- Convert the structured resume data (sections, bullets, skills) into a styled `.docx`
- Match the PDF styling as closely as possible (fonts, spacing, section headers)

In `app/agent/nodes/save_and_display.py`: After PDF compilation, also call `build_docx(state)` and save `state["final_docx_path"]`.

In `app/main.py`: Add a second download button for `.docx`.

Add `python-docx>=1.0.0` to `requirements.txt`.

### 4.3 Template Gallery

CREATE `app/parsers/template_registry.py`:
```python
@dataclass
class TemplateConfig:
    name: str
    section_pattern: str  # regex to find section headers, e.g. r"\\section\{(.+?)\}"
    skills_start_marker: str  # e.g. "\\resumeSubHeadingListStart"
    skills_end_marker: str
    project_start_marker: str
    project_end_marker: str
    summary_pattern: str  # regex to find the summary/headline area
    compiler: str  # "pdflatex", "xelatex", or "lualatex"

TEMPLATES = {
    "default": TemplateConfig(...),
    "jake_resume": TemplateConfig(...),
    # etc.
}
```

Update `app/parsers/latex_parser.py` and `app/parsers/latex_assembler.py` to accept a `TemplateConfig` parameter instead of hardcoding patterns.

CREATE `templates/` directory with subdirectories for each template, containing the `.tex` file and a `config.json`.

### 4.4 GitHub Signal Enrichment

CREATE `app/agent/nodes/enrich_github.py`:
- Use `requests.get(f"https://api.github.com/users/{username}/repos?sort=updated&per_page=10")` (no auth needed for public repos)
- Extract: repo name, stars, forks, primary language, description, last commit date
- Match repos to projects in `state["generated_projects"]` by name
- Store in `state["github_signals"]`

In `app/agent/graph.py`: Insert between `generate_projects` and `tailor_sections` (conditional on `config.get("enrich_with_github")`).

Add to `config.yaml`:
```yaml
github_username: ""
enrich_with_github: false
```

### 4.5 Docker Setup

CREATE `Dockerfile`:
```dockerfile
FROM python:3.11-slim
RUN apt-get update && apt-get install -y texlive-latex-base texlive-fonts-recommended texlive-latex-extra && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 7860
CMD ["python", "-m", "app.main"]
```

CREATE `docker-compose.yml`:
```yaml
services:
  resumeforge:
    build: .
    ports: ["7860:7860"]
    env_file: .env
    volumes:
      - ./config.yaml:/app/config.yaml
      - ./inputs:/app/inputs
      - ./outputs:/app/outputs
```

CREATE `.dockerignore`: `.venv`, `outputs/`, `.env`, `__pycache__/`, `.git/`

### 4.6 Batch Mode

In `app/main.py`: Add a "Batch Mode" tab where users can upload multiple `.txt` JD files. Loop through each, calling `run_agent()` with per-JD state, and collect all output PDFs. Show progress bar with `gr.Progress`.

### 4.7 JD URL Auto-Fetch

In `app/parsers/jd_parser.py`: Add a function `fetch_jd_from_url(url: str) -> str` that:
1. Detects if input is a URL (starts with `http`)
2. Uses `requests.get(url)` to fetch the page
3. Uses `BeautifulSoup` to extract the main text content
4. Returns cleaned text

In `app/main.py`: In the JD input textbox, check if the input looks like a URL and auto-fetch.

---

## Phase 5 — Open-Source Readiness

### 5.1 Root README

CREATE `README.md` at project root (currently only exists at `docs/README.md`). Structure:

```markdown
# 🔥 ResumeForge — AI Resume Tailoring Agent

[badges: python version, license, stars, forks]

[Hero screenshot/GIF of Gradio UI]

## Why ResumeForge?
- 🆓 **100% Free** — cascading proxy across Groq, Gemini, OpenRouter free tiers
- 🤖 **Autonomous** — auto-optimizes until ATS score > 80%
- 📄 **PDF + DOCX** — LaTeX-compiled PDF and Word doc output

## Quick Start
[4 lines: clone, .env, pip install, run]

## Docker
[2 lines: docker compose up]

## Architecture
[Mermaid diagram of the pipeline]

## Features
[Checklist table]

## Contributing
[Link to CONTRIBUTING.md]
```

### 5.2 De-personalize

1. CREATE `examples/` directory with:
   - `examples/skills.md.example` — anonymized template with instructions
   - `examples/project_profile.example.md` — blank template showing expected format
   - `examples/resume.example.tex` — anonymized LaTeX template
2. MOVE `skills.md` → `examples/my_profile/skills.md` (gitignored)
3. MOVE personal project profiles → `examples/my_profile/project_profiles/`
4. UPDATE `config.yaml` defaults to point to example files
5. ADD `.gitignore` entry: `examples/my_profile/`
6. In `app/main.py`: If no `skills.md` exists at the configured path, show a "Setup Wizard" dialog

### 5.3 Testing

1. CREATE `tests/` directory
2. CREATE `tests/test_json_utils.py` — test `extract_json_blob` with various LLM response formats
3. CREATE `tests/test_keyword_matcher.py` — test synonym matching, keyword extraction
4. CREATE `tests/test_file_namer.py` — test sanitization edge cases
5. CREATE `tests/test_validator.py` — test brace balancing, number preservation
6. CREATE `tests/conftest.py` — shared fixtures with mock LLM responses

### 5.4 CI/CD

CREATE `.github/workflows/ci.yml`:
```yaml
name: CI
on: [push, pull_request]
jobs:
  lint-and-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install ruff pytest
      - run: ruff check .
      - run: pytest tests/ -v
```

### 5.5 Documentation Overhaul

After all code changes are done, regenerate these docs from actual code:

| File | Action |
|---|---|
| `docs/ARCHITECTURE.md` | Rewrite with current 13+ node pipeline, Mermaid diagram, actual state fields, actual model routing |
| `docs/FILE_STRUCTURE.md` | Regenerate entire file tree from `tree` command output, document all config keys |
| `docs/SETUP.md` | Add Groq instructions, Docker section, macOS section |
| `docs/ROADMAP.md` | Update all checkboxes to reflect implemented features |
| `docs/ATS_Planner.md` | Convert from planning doc to feature documentation |
| `docs/IMPLEMENTATION_GUIDE.md` | Rename to `DEVELOPMENT_HISTORY.md` |
