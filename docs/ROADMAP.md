# 🗺️ Roadmap — ResumeForge

Status of features by phase. Shipped items are merged to `main`; see [CHANGELOG.md](../CHANGELOG.md).

---

## ✅ Shipped

### Core pipeline
- [x] Two-stage tailoring (ATS reasoning → prose polish), section-by-section (no token overflow)
- [x] LaTeX → PDF, auto-named outputs, version history in `outputs/history/`
- [x] "What changed & why" report
- [x] Gradio UI + CLI/test mode (`python -m app.main --test`)

### Model access (Phase 2)
- [x] Free cascade across providers (Groq → OpenRouter → Gemini → Cohere → GitHub Models)
- [x] Multi-key rotation + backoff to dodge rate limits
- [x] Tiered chains: `free` / `premium` (BYO GPT/Claude/Gemini) / `custom`
- [x] In-UI session keys (never persisted or logged)

### Templates & one page (Phase 3)
- [x] Template registry (`classic`, `modern`) with per-template content budgets
- [x] Page-count parsing + deterministic condense-then-AI-polish one-page enforcement
- [x] Auto-2-page for 10+ years experience or explicit opt-in

### Optimization (Phase 4)
- [x] ATS scorer (keyword + semantic + section-quality + placement + impact)
- [x] Auto-optimize loop to a target score with before→after delta and a "best achievable" message
- [x] Grounded missing-keyword injection (never fabricated)

### Onboarding & ingestion (Phases 5–6)
- [x] GitHub profile builder (repo URL → README → reusable project profile)
- [x] Skills-gap analysis + lightweight skills refresh
- [x] Structured profile builder (identity / education / experience / certifications via forms)
- [x] Résumé-PDF auto-fill (link extraction + best-effort text parsing)

### Star features & packaging (Phase 7)
- [x] Optional cover letter
- [x] Clean ATS-friendly DOCX export
- [x] JD-from-URL fetch
- [x] One-command start with minimal TinyTeX auto-install
- [x] Docker / docker-compose

### Open-source readiness (Phase 8)
- [x] Root README, accurate docs, CHANGELOG
- [x] CI (ruff + pytest), backfilled unit tests, lint-green
- [x] Neutral examples; personal data gitignored

---

## 🔜 Deferred / planned

- [ ] **Side-by-side diff tab** — render `changes_log` as a green/red HTML diff (data already in state)
- [ ] **Real-time streaming progress** — stream node-by-node status to the UI
- [ ] **Batch mode** — tailor for multiple JDs in one run
- [ ] **Template gallery** — more vetted one-page layouts beyond `classic`/`modern`
- [ ] **GitHub signal enrichment** — fold stars/forks/topics into project bullets
- [ ] **RAG over résumé history** — reuse phrasing from past tailored runs
- [ ] **Settings tab** — edit config from the UI instead of YAML

---

## Extending ResumeForge

**Add a graph node:** create `app/agent/nodes/your_node.py` with `your_node(state) -> state`, register it in `app/agent/graph.py`, and wire its edges.

**Add an LLM provider:** create `app/llm/yourprovider.py` (mirror `groq.py` / `openai_gpt.py`), register it in `_PROVIDERS` (`app/llm/router.py`) and `PROVIDER_ENV` (`app/llm/keypool.py`), add its model key to `config.yaml`.

**Add a template:** drop `templates/<name>/template.tex` (with the `% PLACEHOLDER_*` markers) + optional `config.json`; set `resume_template: <name>`.
