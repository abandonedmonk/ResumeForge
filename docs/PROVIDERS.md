# Providers, API keys & smart routing

ResumeForge runs on **free** LLM providers by default and is **premium-ready** if you bring a paid key. You only need **one** key to start. This page explains which key to get, what each provider is best at, and how ResumeForge decides which model does which job.

> TL;DR: get a **Groq** key (fast, free) and a **Gemini** key (huge context, free). Groq writes your résumé; Gemini scores it. Paste them in `.env` and run.

## Which key does what

| Provider | Best at | Free tier | Get a key | `.env` variable |
|---|---|---|---|---|
| **Groq** | Writing & tailoring (fast) — the default workhorse | Generous; ~12k tokens **per request** | [console.groq.com](https://console.groq.com) | `GROQ_API_KEY` |
| **Gemini** (Google AI Studio) | ATS semantic scoring + **big prompts** (1M-token context) | 1,500 requests/day | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) | `GOOGLE_API_KEY` |
| **OpenRouter** | Extra free fallback models | Free models (no card) | [openrouter.ai/keys](https://openrouter.ai/keys) | `OPENROUTER_API_KEY` |
| **Cohere** | Fallback (Command-R) | ~1,000 calls/month trial | [dashboard.cohere.com](https://dashboard.cohere.com) | `COHERE_API_KEY` |
| **GitHub Models** | GPT-4o via a GitHub token (Copilot/Pro) | With eligible plan | [github.com/settings/tokens](https://github.com/settings/tokens) (models access) | `GITHUB_TOKEN` |
| **OpenAI** (premium) | Highest-quality writing | Paid | [platform.openai.com](https://platform.openai.com) | `OPENAI_API_KEY` |
| **Anthropic** (premium) | Highest-quality writing | Paid | [console.anthropic.com](https://console.anthropic.com) | `ANTHROPIC_API_KEY` |

## Recipes — pick one

**Minimal free** (works out of the box):
```env
GROQ_API_KEY=gsk_...
```
Groq does everything. ATS scoring also runs on Groq since no Gemini key is present.

**Best free** (recommended):
```env
GROQ_API_KEY=gsk_...
GOOGLE_API_KEY=AIza...
OPENROUTER_API_KEY=sk-or-...
# Optional: rotate multiple Groq keys to dodge rate limits
GROQ_API_KEY_1=gsk_second
GROQ_API_KEY_2=gsk_third
```
Groq writes; **Gemini** scores ATS and absorbs any oversized prompt; OpenRouter is a third fallback. Numbered keys (`GROQ_API_KEY_1`, `_2`, …) are rotated round-robin so you spread load across keys.

**Premium** (bring your own paid key):
```env
OPENAI_API_KEY=sk-...
# and/or
ANTHROPIC_API_KEY=sk-ant-...
```
Set `model_tier: premium` in `config.yaml` (or pick it in the UI). The premium chain prefers GPT/Claude, then falls back to the free providers you've configured. You can also paste premium keys directly in the UI — **session keys are never written to disk**.

## How routing decides

ResumeForge sends each **task** to the best provider that actually has a key:

| Task | Default provider |
|---|---|
| JD analysis | Groq |
| ATS scoring | **Gemini** (semantic, big context) |
| Project selection | Groq |
| Writing (headline/bullets/skills) | Groq |
| Section tailoring | Groq |
| Cover letter / report | Groq |

If a task's preferred provider has no key, it automatically falls back to whatever you *do* have, then to the full tier cascade — so nothing ever dead-ends. The live routing is printed in the run **Logs** and shown in the UI under **🧭 Providers & Routing**.

Override any task in `config.yaml`:
```yaml
task_routing:
  ats_scoring: gemini
  project_generation: gemini   # e.g. let Gemini write when project bodies are long
```

## Token limits & overflow

Free models have small per-request budgets — Groq's free tier caps a request at roughly **12k total tokens** (input **and** output). ResumeForge is aware of this:

1. **Estimate** the prompt size before each call.
2. **Skip to a bigger-context model** in the chain if the prompt won't fit the preferred one (e.g. a long README routes the writing step to Gemini).
3. **Trim as a last resort** — only if nothing in the chain can hold it, the input is truncated on a clean boundary with a visible `…[trimmed]` marker (never silent), and a warning is logged.
4. **Cap output tokens** per model so the *total* stays under the limit.

The heaviest step (writing, which embeds your project bodies) also budgets each project body to the writer's limit up front, so a Groq-only run won't fail on long projects.

Tune any model's budget without touching code:
```yaml
model_limits:
  llama-3.3-70b-versatile: { max_input_tokens: 10000, max_output_tokens: 2048 }
  gemini-2.5-flash: { max_input_tokens: 120000, max_output_tokens: 4096 }
```

See [SETUP.md](SETUP.md) for full installation and [ARCHITECTURE.md](ARCHITECTURE.md) for where routing sits in the pipeline.
