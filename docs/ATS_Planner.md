# ATS Score Estimator — Implementation Plan

## Goal

Add a comprehensive ATS Score Estimator to ResumeForge that gives users **immediate, quantifiable feedback** on how well their tailored resume matches a Job Description. The score should reflect how a real ATS (like Workday, Greenhouse, Taleo) would rank the resume, not just a naive keyword count.

---

## Background & Research Summary

Modern ATS systems score resumes using multiple weighted factors, not just keyword frequency:

| Factor | Typical ATS Weight | What it measures |
|---|---|---|
| **Hard Keyword Match** | 30–40% | Exact terms from JD found in resume |
| **Contextual/Semantic Match** | 15–20% | Skills used in context, not just listed |
| **Section Completeness** | 20–30% | Standard headers, all fields present |
| **Keyword Placement** | 10–15% | Keywords in summary/titles vs. buried in old roles |
| **Quantified Impact** | 5–10% | Metrics and numbers backing up claims |

Our scoring system should mirror this multi-factor approach to be genuinely useful.

---

## User Review Required

> [!IMPORTANT]
> **Company Enrichment via DuckDuckGo — Worth the complexity?**
> 
> After research, here's the feasibility breakdown:
> - **Library**: `duckduckgo-search` (pip installable, free, no API key)
> - **What we can fetch**: Company mission/values, tech stack mentions, recent news, culture keywords
> - **Benefit**: Enriches the JD analysis with company-specific context (e.g., if the JD says "our platform" but DDG reveals the company uses Kubernetes heavily, we can check if the resume mentions that)
> - **Risk**: Adds ~3-5 seconds latency per run, results are unpredictable, and the JD usually already contains 90%+ of what matters
> 
> **My recommendation**: Make it **optional and off by default**. Add a `enrich_with_web_search: false` toggle in `config.yaml`. When enabled, it runs a quick DDG search during the `analyze_jd` step and appends extra keywords to `jd_analysis`. This way it's there when you want it but doesn't slow down the default flow.

> [!IMPORTANT]
> **Scoring: Hybrid approach (Deterministic + LLM)**
> 
> Rather than using a single Gemini call to produce an opaque "82%" score, I propose a **hybrid** approach:
> 1. **Deterministic scoring** (no LLM, instant): Keyword matching, keyword placement, section checks, metrics preservation — all computed locally with Python
> 2. **LLM semantic pass** (optional, 1 Gemini call): Checks if keywords are used **in context** vs. just keyword-stuffed, evaluates if bullet phrasing demonstrates vs. just lists skills
> 
> This gives a transparent, reproducible score that doesn't change every time you run it, while the LLM pass adds the "smart" layer on top.

---

## Open Questions

> [!IMPORTANT]
> **Q1: Should the ATS score block saving if it's below a threshold?**
> Currently thinking: No — just show it as advisory with color coding. The user decides. But if you want a "warning gate" before saving (e.g., "Your score is 45%, are you sure?"), let me know.

> [!NOTE]
> **Q2: Score visibility in history**
> Should we save the ATS score alongside each run in `outputs/history/`? I'm planning to include it in the changes report and the run log automatically. Let me know if you want it elsewhere too.

---

## Proposed Changes

### Scoring Algorithm Design

The ATS score will be a **weighted composite of 5 sub-scores**, each scored 0–100:

```
FINAL_SCORE = (
    keyword_match_score     * 0.35 +    # Hard keyword coverage
    semantic_context_score  * 0.20 +    # Keywords used in meaningful context (LLM)
    section_quality_score   * 0.15 +    # Section completeness & structure
    keyword_placement_score * 0.15 +    # Keywords in high-visibility spots
    impact_metrics_score    * 0.15      # Quantified achievements present
)
```

#### Sub-score breakdown:

**1. Keyword Match Score (35%)** — *Deterministic*
- Extract `jd_analysis.keywords` + `jd_analysis.required_skills` (already available from `analyze_jd` node)
- Normalize both JD keywords and resume text (lowercase, strip punctuation, handle common variations like "React.js" ↔ "React" ↔ "ReactJS")
- Count: `matched_keywords / total_jd_keywords * 100`
- Partial credit for synonyms via a small hardcoded synonym map (e.g., "ML" ↔ "Machine Learning")

**2. Semantic Context Score (20%)** — *LLM-powered (1 Gemini call)*
- Send the final resume bullets + JD keywords to Gemini
- Ask: "For each keyword, is it used in a meaningful achievement context, or is it just name-dropped?"
- Score: percentage of keywords that are contextually demonstrated
- Fallback: If LLM fails, default to 70% (neutral)

**3. Section Quality Score (15%)** — *Deterministic*
- Check for presence of standard sections: Experience, Education, Skills, Projects
- Check that each section has content (not empty)
- Check bullet count per section (too few = thin, too many = cluttered)
- Score based on completeness

**4. Keyword Placement Score (15%)** — *Deterministic*
- High-value zones: Headline/Summary (3x weight), Skills section (2x weight), first bullet of each experience entry (1.5x weight)
- Score: weighted count of keywords in high-value zones / total keyword mentions
- Rewards strategic placement over random scattering

**5. Impact Metrics Score (15%)** — *Deterministic*
- Count bullets with quantified metrics (regex: numbers, percentages, $, x)
- Target: at least 60% of experience bullets should have metrics
- Score: `min(metrics_bullets / (total_bullets * 0.6), 1.0) * 100`

---

### Company Enrichment (Optional Web Search)

When `enrich_with_web_search: true` in config:

1. During the `analyze_jd` node, after the LLM analysis completes
2. Use `duckduckgo-search` to search: `"{company_name} tech stack engineering blog"`
3. Extract top 3 result snippets
4. Send to Gemini: "Extract any additional technical keywords from these company descriptions that are relevant to a {role_title} position"
5. Append new keywords to `jd_analysis["enriched_keywords"]` (kept separate from JD-extracted keywords)
6. These enriched keywords are scored at **half weight** in the keyword match (bonus, not penalty)

---

### Skills Gap Analysis (Bundled Free)

Since we're already computing keyword match, we get skills gap for free:

- `missing_required`: Keywords from `jd_analysis.required_skills` NOT found in resume
- `missing_nice_to_have`: Keywords from `jd_analysis.nice_to_have` NOT found
- `missing_enriched`: Company-enriched keywords NOT found (if web search was enabled)

This gets displayed in the UI alongside the score.

---

### State Changes

#### [MODIFY] [state.py](file:///d:/Code/PROJECTS/ResumeForge/app/agent/state.py)

Add these new fields to `ResumeState`:

```python
# ATS Scoring
ats_score: dict[str, Any]          # Full score breakdown
ats_score_summary: str             # "82% Match" one-liner for UI
skills_gap: dict[str, list[str]]   # missing_required, missing_nice_to_have, missing_enriched
```

---

### New Files

#### [NEW] `app/agent/nodes/score_resume.py`

The main scoring node. Function `score_resume(state: ResumeState) -> ResumeState`:

1. Reads `state["jd_analysis"]` for keywords, required_skills, nice_to_have
2. Reads `state["final_tex"]` for the actual resume content  
3. Computes all 5 sub-scores
4. Computes weighted final score
5. Builds skills gap analysis
6. Stores results in `state["ats_score"]`, `state["ats_score_summary"]`, `state["skills_gap"]`

The `ats_score` dict will look like:
```python
{
    "overall": 82,
    "keyword_match": {"score": 85, "matched": [...], "total": 15},
    "semantic_context": {"score": 78, "contextual": [...], "name_dropped": [...]},
    "section_quality": {"score": 90, "sections_found": [...], "issues": [...]},
    "keyword_placement": {"score": 75, "high_value_hits": [...], "total_hits": 20},
    "impact_metrics": {"score": 80, "metrics_bullets": 12, "total_bullets": 15},
    "skills_gap": {
        "missing_required": ["Docker", "Kubernetes"],
        "missing_nice_to_have": ["GraphQL"],
        "missing_enriched": []
    }
}
```

---

#### [NEW] `app/prompts/score_resume.py`

Prompt template for the semantic context scoring LLM call:

```python
def build_semantic_score_prompt(keywords: list[str], resume_bullets: list[str]) -> tuple[str, str]:
    # System: "You are an ATS semantic analyzer..."
    # User: Asks to evaluate each keyword's contextual usage
    # Response format: JSON with keyword -> "contextual" | "name_dropped" | "absent"
```

---

#### [NEW] `app/utils/keyword_matcher.py`

Pure Python utility for deterministic keyword operations:

- `normalize_keyword(kw: str) -> str` — lowercase, strip punctuation
- `build_synonym_map() -> dict` — common tech synonyms (React.js/React/ReactJS, ML/Machine Learning, etc.)
- `find_keyword_in_text(keyword: str, text: str, synonym_map: dict) -> bool`
- `extract_metrics_from_bullet(bullet: str) -> bool` — regex for numbers/percentages/$
- `identify_high_value_zones(tex_content: str) -> dict[str, str]` — extract headline, skills section, first bullets

---

#### [NEW] `app/agent/nodes/enrich_company.py` (Optional)

The company enrichment node. Function `enrich_company(state: ResumeState) -> ResumeState`:

1. Checks `config["enrich_with_web_search"]` — if False, returns immediately
2. Uses `duckduckgo-search` to search for company info
3. Sends snippets to Gemini for keyword extraction
4. Appends to `state["jd_analysis"]["enriched_keywords"]`

---

### Modified Files

#### [MODIFY] [graph.py](file:///d:/Code/PROJECTS/ResumeForge/app/agent/graph.py)

Insert the new nodes into the pipeline:

```
Current:  ... -> compile_pdf -> generate_report -> save_and_display -> END
Proposed: ... -> compile_pdf -> score_resume -> generate_report -> save_and_display -> END
```

And optionally:
```
Current:  analyze_jd -> generate_projects -> ...
Proposed: analyze_jd -> enrich_company -> generate_projects -> ...
```

The `score_resume` node goes **after** `compile_pdf` (so we score the final output) and **before** `generate_report` (so the report can include the score).

---

#### [MODIFY] [generate_report.py](file:///d:/Code/PROJECTS/ResumeForge/app/agent/nodes/generate_report.py)

Update the report to include:
- Overall ATS score with color indicator
- Sub-score breakdown table
- Skills gap section ("You're missing these from the JD: ...")
- Actionable recommendations based on lowest sub-scores

---

#### [MODIFY] [main.py](file:///d:/Code/PROJECTS/ResumeForge/app/main.py)

Add to the Gradio UI:
1. **ATS Score Badge**: A large, color-coded score display at the top of the results panel
   - Green (≥75%): "Strong Match"
   - Yellow (50–74%): "Moderate Match"  
   - Red (<50%): "Needs Work"
2. **New Tab: "ATS Analysis"**: Contains:
   - Sub-score breakdown (5 horizontal bars or a radar chart via HTML)
   - Skills Gap list with "Required Missing" highlighted in red, "Nice-to-Have Missing" in yellow
   - Recommendations list
3. **Config toggle**: Add a checkbox for "Enrich with web search" in the inputs panel

Update `_run_resumeforge()` return values to include ATS score data.

---

#### [MODIFY] [config.yaml](file:///d:/Code/PROJECTS/ResumeForge/config.yaml)

Add:
```yaml
enrich_with_web_search: false
ats_semantic_scoring: true     # set false to skip the LLM call for scoring
```

---

#### [MODIFY] [requirements.txt](file:///d:/Code/PROJECTS/ResumeForge/requirements.txt)

Add:
```
duckduckgo-search>=7.0.0
```

---

### Summary of All File Changes

| File | Action | Description |
|---|---|---|
| `app/agent/state.py` | MODIFY | Add `ats_score`, `ats_score_summary`, `skills_gap` fields |
| `app/agent/nodes/score_resume.py` | NEW | Main scoring node with 5 sub-scores |
| `app/prompts/score_resume.py` | NEW | Semantic scoring prompt template |
| `app/utils/keyword_matcher.py` | NEW | Deterministic keyword matching utilities |
| `app/agent/nodes/enrich_company.py` | NEW | Optional DDG company enrichment node |
| `app/agent/graph.py` | MODIFY | Insert `score_resume` and optionally `enrich_company` into pipeline |
| `app/agent/nodes/generate_report.py` | MODIFY | Include ATS score in the changes report |
| `app/main.py` | MODIFY | Add ATS score UI badge, new "ATS Analysis" tab, web search toggle |
| `config.yaml` | MODIFY | Add `enrich_with_web_search` and `ats_semantic_scoring` toggles |
| `requirements.txt` | MODIFY | Add `duckduckgo-search` |

---

## Verification Plan

### Automated Tests
1. **Unit test `keyword_matcher.py`**: Test synonym matching, normalization, metrics detection against known inputs
2. **Unit test `score_resume` node**: Mock state with known keywords and resume content, verify score is within expected range
3. **Integration test**: Run full pipeline with `--test` flag and verify `ats_score` field is populated in final state
4. **Edge cases**: Test with empty JD, test with resume that has zero keyword matches, test with web search enabled/disabled

### Manual Verification
1. Run ResumeForge on a real JD, verify score looks reasonable
2. Compare score before/after tailoring to confirm tailoring actually improves it
3. Check that skills gap correctly identifies genuinely missing skills
4. Verify the UI renders the score badge and breakdown correctly
5. Test DDG enrichment with a real company name and verify it adds relevant keywords
