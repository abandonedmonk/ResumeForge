---
name: resumeforge
description: >-
  LaTeX resume engine. Use when the user wants to tailor a resume to a job description,
  roast a resume for brutally honest feedback, cold-read a resume the way a recruiter
  would, or find what their resume is missing versus their GitHub. Triggers: "tailor my
  resume", "update my CV for this JD", "roast my resume", "what is my resume missing",
  "cold read my resume", "generate a LaTeX resume". Free to run — uses a cascade of free
  LLM providers, so it does not consume the host agent's paid model for generation.
---

# ResumeForge

ResumeForge tailors, roasts, cold-reads, and gap-analyses resumes against job
descriptions, and compiles a clean one-page LaTeX PDF. It runs as a local `resumeforge`
CLI. **You (the agent) orchestrate; ResumeForge does the generation** on its own free
provider cascade — so the user's paid subscription is not spent on resume bullet writing.

## Prerequisite

`resumeforge` must be installed and on PATH. If `resumeforge --help` fails, run the
installer at `skill/scripts/install.sh` (or tell the user: `pipx install resumeforge`).
LaTeX (`pdflatex`) is only needed for `tailor`; run `resumeforge init` to check/setup.

## How to invoke

**Always pass `--json`** and parse stdout — every result command prints a single JSON
object and nothing else. Do not parse the human-readable (no-`--json`) output.

Inputs are flexible:
- `--resume` accepts `.pdf`, `.tex`, `.md`, or `.txt`.
- `--jd` accepts a file path, a posting URL, or raw JD text.

### Commands

```bash
# Tailor a resume to a JD -> compiled PDF + auditable compression receipt
resumeforge tailor --jd <file|url|text> [--resume cv.tex] [--cold-read] --json
# --resume for tailor must be a .tex template (or omit to use the configured template).

# Brutally honest, shareable feedback (each roast paired with a fix)
resumeforge roast --resume <cv.pdf> [--jd <file|url|text>] --json

# Zero-context recruiter read: targeted role / strongest fit / biggest gap
resumeforge cold-read --resume <cv.pdf> --jd <file|url|text> --json

# What the resume is missing vs the user's actual GitHub work
resumeforge gap --github <username> --resume <cv.pdf> --jd <file|url|text> --json

# Re-print the compression receipt for the most recent (or a specific) tailor run
resumeforge receipt [--run-id <id>] --json
```

## Output schemas (stdout, `--json`)

- **tailor** →
  ```json
  {"run_dir": "...", "ats_summary": "...", "ats_score": {}, "receipt": {},
   "cold_read": null, "errors": [],
   "artifacts": {"tex": "...", "pdf": "...", "receipt": "...", "cold_read": ""}}
  ```
- **roast** → `{"roast_text": "...", "items": [{"roast": "...", "fix": "..."}]}`
- **cold-read** → `{"targeted_role": "...", "strongest_qualification": "...", "biggest_gap": "..."}`
- **gap** → `{"repos": [...], "inventory": "...", "analysis": {"missing": [], "undersold": [], "overclaimed": [], "suggested_bullets": []}}`
- **receipt** → `{"run": "...", "receipt": {"words_removed": 0, "bullets_strengthened": 0, "semantic_similarity": 0, "keywords_added": [], "keywords_removed": [], ...}}`

## Steps for a typical request

1. Confirm the resume path and JD source (file, URL, or pasted text).
2. Pick the command that matches intent (tailor / roast / cold-read / gap).
3. Run `resumeforge <command> ... --json` and parse stdout.
4. For `tailor`, the compiled artifacts are written under the returned `run_dir`
   (`~/.resumeforge/runs/<id>/`): `resume.pdf`, `resume.tex`, `receipt.json`.
5. Summarise the JSON for the user; surface the PDF path and, for tailor, the
   compression receipt (what changed) and any `errors`.

## Notes

- A non-zero exit code on `tailor` means the run produced `errors` (still check the JSON).
- No paid key required; add one provider key (e.g. `GROQ_API_KEY`) to the user's `.env`.
  Run `resumeforge init` to scaffold `.env` and verify keys + LaTeX.
