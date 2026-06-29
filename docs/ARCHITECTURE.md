# 🏗️ Architecture — ResumeForge

## The Two-Stage LLM Pipeline (Core Insight)

Your original manual workflow already had the right idea — two models, two jobs. ResumeForge automates exactly that.

```
                        ┌─────────────────────────────┐
                        │      STAGE 1: ATS BRAIN      │
                        │   Gemini 2.0 Flash (Free)    │
                        │                              │
                        │  • Parse JD → extract        │
                        │    keywords, skills, tone    │
                        │  • Score each existing       │
                        │    bullet vs JD              │
                        │  • Rewrite weak bullets      │
                        │    with ATS keyword          │
                        │    injection                 │
                        └──────────┬──────────────────┘
                                   │
                                   ▼
                        ┌─────────────────────────────┐
                        │     STAGE 2: PROSE POLISH    │
                        │  OpenRouter / Cohere (Free)  │
                        │                              │
                        │  • Takes Stage 1 bullets     │
                        │  • Applies your skills.md    │
                        │    style guide               │
                        │  • Makes them sound human,   │
                        │    punchy, impressive        │
                        │  • Removes Gemini's          │
                        │    "corporate robot" tone    │
                        └──────────┬──────────────────┘
                                   │
                                   ▼
                        ┌─────────────────────────────┐
                        │      LATEX ASSEMBLER         │
                        │         (No LLM)             │
                        │                              │
                        │  • Injects polished bullets  │
                        │    back into .tex template   │
                        │  • Preserves all formatting  │
                        │  • Runs pdflatex             │
                        │  • Auto-names + saves PDF    │
                        └─────────────────────────────┘
```

### Why section-by-section processing?

This is how you never hit a token limit again. Instead of feeding the entire resume + JD + skills file + projects file to one model in one shot, each **section** (Experience 1, Experience 2, Project 1, etc.) is processed independently:

```
Full Resume
    │
    ├── Experience: Internship at X  ──► Stage1 ──► Stage2 ──► polished bullets
    ├── Experience: Project at Y     ──► Stage1 ──► Stage2 ──► polished bullets  
    ├── Project: Project A           ──► Stage1 ──► Stage2 ──► polished bullets
    └── Project: Project B           ──► Stage1 ──► Stage2 ──► polished bullets
```

Each call is tiny. Each call stays well within free tier limits. Parallelizable later.

---

## LangGraph State Machine

```
[LoadInputs]
     │
     ▼
[ParseResume]  ← splits .tex into sections dict
     │
     ▼
[AnalyzeJD]    ← single Gemini call: extract keywords, role level, company tone
     │          → outputs: jd_keywords[], required_skills[], nice_to_have[], tone
     ▼
[TailorSection] ← loops over each section
     │   ┌────────────────────────────────────┐
     │   │  For each section:                 │
     │   │   1. Gemini Flash → ATS rewrite    │
     │   │   2. OpenRouter  → prose polish    │
     │   │   3. Store diff (old vs new)       │
     │   └────────────────────────────────────┘
     │
     ▼
[ValidateOutput]  ← sanity checks: bullet count, LaTeX syntax, no hallucinated projects
     │
     ▼
[AssembleLaTeX]   ← injects new bullets into original .tex
     │
     ▼
[CompilePDF]      ← pdflatex subprocess
     │
     ▼
[GenerateReport]  ← one LLM call: turn diffs into readable "what changed & why" markdown
     │
     ▼
[SaveAndDisplay]  ← auto-name, save to output folder, return to Gradio
```

### LangGraph State (what travels between nodes)

```python
class ResumeState(TypedDict):
    # Inputs
    jd_text: str
    skills_md: str                    # Your style guide / skills file
    projects_context: dict            # Name → description mapping
    original_resume_tex: str
    output_folder: str
    
    # Intermediate
    jd_analysis: dict                 # keywords, tone, role_level, company_name, role_title
    resume_sections: dict             # section_name → {header, bullets, raw_tex}
    tailored_sections: dict           # section_name → {new_bullets, reasoning}
    changes_log: list[dict]           # [{section, old, new, reasoning}]
    
    # Outputs
    final_tex: str
    final_pdf_path: str
    changes_report_md: str
    errors: list[str]
```

---

## Prompt Architecture

### System Prompt (injected into EVERY call)
Your `skills.md` is the foundation. It goes into the system prompt of every single LLM call, not just one. This is the "secret sauce" from the original plan — it ensures consistent voice regardless of which model is doing the writing.

### Stage 1 Prompt Template (Gemini)
```
SYSTEM: {skills_md contents}

You are an ATS optimization expert. Your job is ONLY to ensure keyword coverage 
and relevance — not to write beautifully. Another model will handle prose quality.

JD KEYWORDS REQUIRED: {jd_analysis.keywords}
ROLE LEVEL: {jd_analysis.role_level}

SECTION TO REWRITE:
{current_section_bullets}

PROJECT CONTEXT (if relevant):
{matched_project_context}

Rules:
- Keep exact same number of bullets
- Inject keywords naturally — no keyword stuffing
- Preserve all numbers/metrics from original
- Flag any bullet you're uncertain about with [UNCERTAIN]
- Return ONLY the rewritten bullets, one per line
```

### Stage 2 Prompt Template (OpenRouter/Cohere)
```
SYSTEM: {skills_md contents}

You are a technical resume writer known for punchy, impressive bullet points.
The bullets below are ATS-optimized but sound robotic. Make them sound like 
a top-tier engineer wrote them — specific, impactful, human.

COMPANY TONE: {jd_analysis.tone}  (e.g., "startup casual", "enterprise formal", "research academic")

ROBOTIC BULLETS FROM STAGE 1:
{stage1_output}

Rules:
- Keep all keywords from Stage 1 — do not remove any
- Keep all numbers/metrics — do not change them  
- Make each bullet start with a strong, varied action verb
- Max 2 lines per bullet
- Return ONLY the final bullets, one per line
```

---

## Free API Routing Logic

```python
def get_model_for_stage(stage: int, fallback: bool = False):
    if stage == 1:
        return GeminiFlash()          # Always Gemini for ATS logic
    
    if stage == 2 and not fallback:
        return OpenRouterFree()       # Mistral/Llama via OpenRouter
    
    if stage == 2 and fallback:
        return CohereCommandR()       # Fallback if OpenRouter rate-limited
```

The agent automatically falls back if a rate limit is hit. You never need to think about it.

---

## GitHub Copilot Integration (Optional)

GitHub Copilot Pro gives access to the **GitHub Models API** — an OpenAI-compatible endpoint that lets you call GPT-4o, Claude Sonnet, and others programmatically using your Copilot Pro token.

**Endpoint**: `https://models.inference.ai.azure.com`  
**Auth**: Your GitHub Personal Access Token (same one Copilot uses)  
**Compatible with**: OpenAI Python SDK (just change `base_url`)

This can be used as an **optional Stage 2 upgrade** — if you want GPT-4o or Claude Sonnet quality for prose polishing at zero extra cost:

```python
# In config.yaml
stage2_model: "copilot"   # Uses GitHub Models API with your PAT
# or
stage2_model: "openrouter" # Default free tier
```

The agent checks which is configured and routes accordingly.

---

## Validation Layer (Prevents Hallucination)

Before any LaTeX is assembled, the agent runs a fast validation pass:

1. **Bullet count check**: New section must have same number of bullets as original
2. **Project name check**: No project names in output that weren't in `projects.md`  
3. **Metrics preservation**: Every number from the original must appear in the output
4. **LaTeX syntax check**: No unescaped special characters (`&`, `%`, `_`, `#`)
5. **Keyword coverage**: At least 70% of required JD keywords present in final output

If validation fails → the agent retries that section once with a stricter prompt.  
If it fails again → it keeps the original section and flags it in the report.

---

## Output File Naming

The `AnalyzeJD` node extracts company name and role title from the JD text.

```
Google_Software_Engineer_2026-04.pdf
Microsoft_Data_Scientist_2026-04.pdf  
Flipkart_Backend_Engineer_2026-04.pdf
```

Saved to: `{your_output_folder}/` and also `outputs/history/` for version tracking.
