# 🗺️ Roadmap — ResumeForge

All features are modular. Add them one at a time. Each is a self-contained change.

---

## V1 — Core (What You're Building Now)

- [x] Two-stage LLM pipeline (ATS brain + prose polish)
- [x] Section-by-section processing (no token limits ever)
- [x] Free APIs only (Gemini Flash + OpenRouter + Cohere)
- [x] GitHub Copilot Pro integration (optional Stage 2 upgrade)
- [x] LaTeX → PDF pipeline
- [x] Auto-named output files
- [x] "What changed & why" report
- [x] Version history in outputs/history/
- [x] One-click launch (run.bat / run.sh)
- [x] Gradio UI that feels like a desktop app

---

## V1.1 — Quick Wins (1–2 hours each, add right after V1 works)

### ATS Score Estimator
**What**: After tailoring, show a score: "This resume matches ~82% of the JD keywords"  
**How**: Add a `score_resume` node at the end. Single Gemini call comparing final bullets vs jd_keywords.  
**UI**: Add a big score number to the results panel with color coding (green ≥ 75%, yellow 50–75%, red < 50%)

### Docx Input Support  
**What**: Accept .docx resume files in addition to .tex  
**How**: Use `python-docx` to extract text → convert to a pseudo-LaTeX format → process normally → output still as PDF  
**Why**: Not everyone has a LaTeX resume yet. This makes the tool useful immediately.

### Side-by-Side Diff View  
**What**: Show original bullets vs new bullets in a visual two-column diff  
**How**: In Gradio, render the changes_log as an HTML table with red/green highlighting  
**Note**: The data is already there in changes_log — just a UI change

### Config UI Tab  
**What**: A "Settings" tab in the Gradio UI to change config without editing YAML  
**How**: Gradio form that reads/writes config.yaml  
**Fields**: Stage 2 model, output folder, keyword threshold

---

## V1.2 — Power Features (2–4 hours each)

### Batch Mode — Tailor for 5 JDs at Once  
**What**: Upload multiple JDs → get one PDF per JD  
**How**: Wrap the graph in a loop. Run sequentially (respects free API rate limits).  
**UI**: Replace single JD upload with a multi-file upload. Show a progress bar per JD.

### Resume Versioning + Revert  
**What**: Browse past runs, see all tailored versions, revert to any previous version  
**How**: outputs/history/ already saves everything. Add a "History" tab that lists past runs with company/role/date. Click any to view or re-download.

### Skills Gap Analysis  
**What**: "Your resume is missing these required skills from the JD: Docker, Kubernetes"  
**How**: After AnalyzeJD, compare jd_analysis.required_skills vs your skills.md. Show gaps clearly.  
**Value**: Tells you what to add to your resume or what to learn next

### Multi-Format Output  
**What**: Output both PDF and a clean .docx  
**How**: After LaTeX assembly, also run a LaTeX→HTML→docx pipeline using pandoc  
**When to add**: When you need to submit resumes in Word format (some companies require it)

---

## V2 — Advanced (1–2 days each, add when you have time)

### RAG Over Your Resume History  
**What**: "Generate bullets using insights from my 15 previous tailored resumes"  
**How**: Store all generated bullets in a Chroma vector store. At tailor time, retrieve similar bullets from past runs as additional context for the polish stage.  
**Why**: The longer you use ResumeForge, the better it gets at writing in your specific voice

### Smart Project Matcher  
**What**: Automatically suggest which of your projects are most relevant for a given JD  
**How**: Embed all project descriptions + JD using Gemini embeddings (free). Cosine similarity ranking.  
**Output**: "For this ML Engineer role, your top 3 relevant projects are: X, Y, Z"

### Cover Letter Generator  
**What**: Generate a tailored cover letter alongside the resume  
**How**: New graph branch after AnalyzeJD. Single-shot generation using full JD + skills.md + top 3 projects.  
**Output**: cover_letter.docx saved alongside the resume PDF

### LinkedIn Headline + Summary Tailorer  
**What**: Also rewrite your LinkedIn headline and "About" section for the target role  
**How**: New Gradio tab. Paste your current LinkedIn text. Get role-specific rewrites.

---

## Architecture Notes for Future Features

### Adding a new node to the graph
1. Create `app/agent/nodes/your_node.py` with a function `your_node(state: ResumeState) -> ResumeState`
2. Import it in `app/agent/graph.py`
3. Add `graph.add_node("your_node", your_node)` 
4. Add edge: `graph.add_edge("previous_node", "your_node")`
5. Add edge: `graph.add_edge("your_node", "next_node")`

That's it. The state travels through automatically.

### Adding a new LLM provider
1. Create `app/llm/yourprovider.py` following the same pattern as `gemini.py`
2. Add it to the router in `app/llm/router.py`
3. Add the option to config.yaml

### Adding a new input format
1. Create a parser in `app/parsers/`
2. Update `load_inputs.py` to detect the format and call the right parser
3. Everything downstream stays the same

---

## Free Tier Limits Reference

| Provider | Limit | Resets | Sufficient for ResumeForge? |
|---|---|---|---|
| Gemini Flash | 1,500 req/day, 1M tokens/min | Daily | Yes — 1 resume = ~10 calls |
| OpenRouter (free models) | Varies by model, ~20 req/min typical | Per minute | Yes with rate limiting |
| Cohere Command R | 1,000 req/month | Monthly | Yes as fallback |
| GitHub Models (Copilot Pro) | 50 req/day for premium models | Daily | Yes for occasional use |

For daily heavy use (10+ resumes/day), Gemini Flash is the only bottleneck, and even then 1,500 requests is ~150 resumes/day worth of Stage 1 calls.
