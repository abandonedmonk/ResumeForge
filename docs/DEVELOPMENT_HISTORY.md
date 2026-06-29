# 🎮 Development History — How ResumeForge Was Built

> **Historical build log.** This documents how the project was originally vibe-coded with an AI assistant. For the current feature set and how to extend it, see [ROADMAP.md](ROADMAP.md) and [ARCHITECTURE.md](ARCHITECTURE.md).

> This guide is written for someone who will use an AI coding assistant (Cursor, Copilot, Claude) to build this. Each section is a prompt you give your AI, in order. Don't skip ahead.

---

## How to Use This Guide

1. Open your project folder in **Cursor** (or VS Code with Copilot)
2. Follow each step in order
3. Copy the prompt under each step → paste into the AI chat
4. Let the AI write the code
5. Run it, check it works, move to the next step
6. When stuck, paste the error into the AI and say "fix this"

**Golden rule**: Get each step working before moving to the next one.

---

## Phase 0: Project Scaffold (10 min)

### Step 0.1 — Create the folder structure

**Prompt to AI**:
```
Create the following folder and file structure for a Python project called resume-forge. 
Create empty placeholder files (just a comment saying "# TODO" in each .py file).

Structure:
app/
  main.py
  agent/
    graph.py
    state.py
    nodes/
      load_inputs.py
      parse_resume.py
      analyze_jd.py
      tailor_section.py
      validate_output.py
      assemble_latex.py
      compile_pdf.py
      generate_report.py
      save_and_display.py
  llm/
    router.py
    gemini.py
    openrouter.py
    cohere.py
    copilot.py
  prompts/
    stage1_ats.py
    stage2_polish.py
    analyze_jd.py
    generate_report.py
  parsers/
    latex_parser.py
    latex_assembler.py
    jd_parser.py
    projects_parser.py
  utils/
    validator.py
    file_namer.py
    logger.py
inputs/
outputs/
  history/
tests/
logs/
```

### Step 0.2 — Create config and env files

**Prompt to AI**:
```
Create these files in the project root:

1. config.yaml with these settings:
   - stage1_model: "gemini-flash"
   - stage2_model: "openrouter"
   - openrouter_model: "mistralai/mistral-7b-instruct:free"
   - default_skills_md: "inputs/skills.md"
   - default_projects_md: "inputs/projects.md"
   - default_resume_tex: "inputs/base_resume.tex"
   - default_output_folder: "outputs/"
   - save_history: true
   - open_browser_on_launch: true
   - log_prompts: true
   - auto_name_pdf: true
   - fallback_name: "Tailored_Resume"
   - keyword_coverage_threshold: 0.70
   - max_retries_per_section: 2

2. .env.example with placeholder keys:
   GOOGLE_API_KEY=your_gemini_key_here
   OPENROUTER_API_KEY=your_openrouter_key_here
   COHERE_API_KEY=your_cohere_key_here
   GITHUB_TOKEN=your_github_pat_here

3. requirements.txt with:
   langgraph>=0.2.0
   langchain>=0.3.0
   langchain-google-genai>=2.0.0
   langchain-cohere>=0.3.0
   gradio>=5.0.0
   python-dotenv>=1.0.0
   pyyaml>=6.0
   openai>=1.0.0
   requests>=2.31.0

4. .gitignore that ignores: .env, .venv/, __pycache__/, outputs/, logs/, *.pdf, *.aux, *.log
```

---

## Phase 1: State and Parsers (20 min)

### Step 1.1 — The State definition

**Prompt to AI**:
```
In app/agent/state.py, create a TypedDict called ResumeState with these fields:

Inputs:
- jd_text: str
- skills_md: str
- projects_context: dict  (project_name -> description string)
- original_resume_tex: str
- output_folder: str

Intermediate:
- jd_analysis: dict  (keys: keywords, required_skills, nice_to_have, tone, company_name, role_title, role_level)
- resume_sections: dict  (section_name -> dict with keys: header, bullets as list of str, raw_tex as str)
- tailored_sections: dict  (section_name -> dict with keys: new_bullets as list of str, reasoning as str)
- changes_log: list  (each item: dict with keys section, old_bullets, new_bullets, reasoning)

Outputs:
- final_tex: str
- final_pdf_path: str
- changes_report_md: str
- errors: list of str

Also add a default_state() function that returns a ResumeState with all fields initialized 
to empty strings, empty dicts, empty lists as appropriate.
```

### Step 1.2 — LaTeX Parser

**Prompt to AI**:
```
In app/parsers/latex_parser.py, write a function parse_latex_resume(tex_content: str) -> dict

It should split a LaTeX resume into sections. Each section is identified by a \section{} or \subsection{} command.

For each section, extract:
- "header": the section name
- "raw_tex": the full raw LaTeX string for that section
- "bullets": a list of strings, where each string is the content of one \item line 
  (strip the \item prefix, strip leading/trailing whitespace)

Return a dict where keys are section names and values are the above dicts.

Handle edge cases: 
- sections with no \item lines (e.g., Education with tabular format) should still be included, with bullets as empty list
- nested environments like \begin{itemize}...\end{itemize} should be handled correctly

Include a simple test at the bottom under if __name__ == "__main__" that tests with a small sample LaTeX string.
```

### Step 1.3 — Projects Parser

**Prompt to AI**:
```
In app/parsers/projects_parser.py, write a function parse_projects_md(md_content: str) -> dict

It reads a markdown file where each project is a ## heading followed by key-value fields and description.

Return a dict: {project_name: full_text_description}
where full_text_description is everything under that heading concatenated.

Also write a function match_project(section_text: str, projects_dict: dict) -> str | None
that checks if any project name appears in section_text (case-insensitive) and returns 
the project description if found, otherwise None.
```

### Step 1.4 — JD Parser

**Prompt to AI**:
```
In app/parsers/jd_parser.py, write a function extract_company_role(jd_text: str) -> tuple[str, str]
that uses simple text heuristics (not LLM) to extract the company name and job title from a JD.

Common patterns to look for:
- "at [Company]", "join [Company]", "[Company] is looking"
- Lines that look like job titles (contain words like Engineer, Developer, Analyst, Manager, etc.)
- "Position:", "Role:", "Title:" labels

Return (company_name, role_title). If extraction fails, return ("Company", "Role").

Also include basic cleaning: remove special chars from names that would break a filename.
```

---

## Phase 2: LLM Wrappers (30 min)

### Step 2.1 — Gemini wrapper

**Prompt to AI**:
```
In app/llm/gemini.py, create a class GeminiFlash with:
- __init__ that loads GOOGLE_API_KEY from environment and sets up the langchain-google-genai ChatGoogleGenerativeAI client with model "gemini-2.0-flash"
- A method call(system_prompt: str, user_prompt: str, temperature: float = 0.3) -> str
  that sends a message and returns the response text
- Basic error handling: catch rate limit errors and raise a RateLimitError, catch other errors and raise a LLMError
- Log the prompt and response to a file in logs/ if log_prompts is True in config

Use langchain-google-genai. Load config from config.yaml using PyYAML.
```

### Step 2.2 — OpenRouter wrapper

**Prompt to AI**:
```
In app/llm/openrouter.py, create a class OpenRouterFree with:
- __init__ that loads OPENROUTER_API_KEY from environment
  OpenRouter is OpenAI-compatible, so use the openai Python SDK with:
    base_url="https://openrouter.ai/api/v1"
    api_key=OPENROUTER_API_KEY
- Load the model name from config.yaml (openrouter_model field)
- A method call(system_prompt: str, user_prompt: str, temperature: float = 0.4) -> str
- Same error handling and logging as GeminiFlash
```

### Step 2.3 — Cohere wrapper

**Prompt to AI**:
```
In app/llm/cohere.py, create a class CohereCommandR with:
- __init__ that loads COHERE_API_KEY from environment using the cohere Python SDK
- A method call(system_prompt: str, user_prompt: str, temperature: float = 0.4) -> str
  using cohere's chat endpoint with model "command-r"
- Same error handling and logging
```

### Step 2.4 — GitHub Copilot wrapper

**Prompt to AI**:
```
In app/llm/copilot.py, create a class CopilotModels with:
- __init__ that loads GITHUB_TOKEN from environment
  GitHub Models API is OpenAI-compatible:
    base_url="https://models.inference.ai.azure.com"
    api_key=GITHUB_TOKEN
  Default model: "gpt-4o" (can be overridden)
- A method call(system_prompt: str, user_prompt: str, temperature: float = 0.4) -> str
- If GITHUB_TOKEN is not set, raise a clear ConfigError with message explaining how to get a token
- Same error handling and logging
```

### Step 2.5 — Router

**Prompt to AI**:
```
In app/llm/router.py, create a function get_stage2_model() that:
1. Reads stage2_model from config.yaml
2. Returns the appropriate LLM instance:
   - "openrouter" -> OpenRouterFree()
   - "cohere" -> CohereCommandR()
   - "copilot" -> CopilotModels()
3. If the selected model raises RateLimitError on a call, automatically retry with the next fallback:
   openrouter -> cohere -> copilot -> raise error

Also create get_stage1_model() that always returns GeminiFlash().
```

---

## Phase 3: Prompts (15 min)

### Step 3.1 — All prompt templates

**Prompt to AI**:
```
In app/prompts/, create the following prompt template strings.
Each file should export a function that takes parameters and returns a formatted string.

app/prompts/analyze_jd.py — function build_analyze_jd_prompt(jd_text: str, skills_md: str) -> tuple[str, str]
Returns (system_prompt, user_prompt) where:
System: "You are a JD analysis expert. {skills_md}"
User: Asks to extract from the JD:
  - required_skills: list of technical skills explicitly mentioned
  - nice_to_have: list of skills mentioned as "preferred" or "bonus"
  - keywords: top 15 ATS keywords
  - tone: one of [startup_casual, enterprise_formal, research_academic, consulting_professional]
  - role_level: one of [intern, junior, mid, senior, lead]
  - company_name: extracted company name
  - role_title: exact job title
  Output format: JSON only, no markdown fences

app/prompts/stage1_ats.py — function build_stage1_prompt(skills_md, jd_analysis, section_name, bullets, project_context) -> tuple[str, str]
System: skills_md + instruction that this is ATS optimization only, prose quality handled separately
User: Provides JD keywords, section bullets, project context, rules (same count, no hallucination, preserve metrics)

app/prompts/stage2_polish.py — function build_stage2_prompt(skills_md, jd_analysis, stage1_bullets, section_name) -> tuple[str, str]  
System: skills_md + instruction that this is prose quality improvement
User: Provides robotic stage1 bullets, company tone, rules (keep all keywords, vary action verbs, max 2 lines)

app/prompts/generate_report.py — function build_report_prompt(changes_log: list) -> tuple[str, str]
System: "You are a clear technical writer."
User: Formats the changes_log into a readable markdown report with sections per resume section, before/after bullets, and reasoning summary
```

---

## Phase 4: Agent Nodes (45 min)

### Step 4.1 — LoadInputs and ParseResume nodes

**Prompt to AI**:
```
In app/agent/nodes/load_inputs.py, write a LangGraph node function load_inputs(state: ResumeState) -> ResumeState that:
- Reads files from state fields (jd_text already in state, but skills_md/projects_context/original_resume_tex might be file paths)
- If a field contains a file path string ending in .md or .tex, reads the file content
- If a field is already file content (multi-line string), uses it directly
- Updates state with the loaded content
- Appends any file-not-found errors to state["errors"]

In app/agent/nodes/parse_resume.py, write a node function parse_resume(state: ResumeState) -> ResumeState that:
- Calls parse_latex_resume() on state["original_resume_tex"]
- Calls parse_projects_md() on state["projects_context"] if it's a string (the raw markdown)
- Stores results back in state
```

### Step 4.2 — AnalyzeJD node

**Prompt to AI**:
```
In app/agent/nodes/analyze_jd.py, write a node function analyze_jd(state: ResumeState) -> ResumeState that:
- Gets the Stage 1 model (GeminiFlash)
- Builds the JD analysis prompt using build_analyze_jd_prompt()
- Calls the model
- Parses the JSON response (handle malformed JSON gracefully)
- Also calls extract_company_role() from jd_parser as a fallback for company/role names
- Stores result in state["jd_analysis"]
- Appends any errors to state["errors"]
```

### Step 4.3 — TailorSection node (the core node)

**Prompt to AI**:
```
In app/agent/nodes/tailor_section.py, write a node function tailor_sections(state: ResumeState) -> ResumeState that:

Loops over every section in state["resume_sections"]:
  - Skip sections with empty bullets list (e.g., Education header-only sections)
  - Find any matching project context using match_project()
  - Stage 1: Call GeminiFlash with build_stage1_prompt(), parse response into list of bullet strings
  - Stage 2: Call get_stage2_model() with build_stage2_prompt() on Stage 1 output, parse response
  - Store in state["tailored_sections"][section_name] = {new_bullets, reasoning}
  - Append to state["changes_log"]
  
Handle retries: if either stage raises RateLimitError, wait 2 seconds and retry once.
Handle failures: if a section fails after retries, keep the original bullets and note the failure in errors.

This node should yield progress updates — use a generator or callback pattern compatible with Gradio's progress tracking.
```

### Step 4.4 — Validate, Assemble, Compile nodes

**Prompt to AI**:
```
In app/agent/nodes/validate_output.py, write a node that runs these checks on state["tailored_sections"]:
1. Bullet count: new count must equal original count (±1 allowed for flexibility)  
2. No new project names that aren't in state["projects_context"]
3. Numbers from original bullets must appear in new bullets (regex for digits)
4. Check for unescaped LaTeX special chars in new bullets: &, %, $, #, _, {, }, ~, ^, \
   Auto-escape any that are found
If any section fails checks 1 or 2 after auto-fix attempts, flag it in state["errors"] and revert to original bullets for that section.

In app/agent/nodes/assemble_latex.py, write a node that:
- Calls latex_assembler.inject_sections(original_tex, tailored_sections) 
- In latex_assembler.py, write inject_sections() that replaces \item lines in each section with the new bullets
- Stores result in state["final_tex"]

In app/agent/nodes/compile_pdf.py, write a node that:
- Writes state["final_tex"] to a temp .tex file
- Runs pdflatex -interaction=nonstopmode on it twice (twice is standard for refs)
- If compilation fails, stores the pdflatex error log in state["errors"]
- Moves the output .pdf to a temp location and stores path in state
```

### Step 4.5 — Report, Save nodes

**Prompt to AI**:
```
In app/agent/nodes/generate_report.py, write a node that:
- Calls get_stage2_model() with build_report_prompt(state["changes_log"])
- Stores the markdown string in state["changes_report_md"]
- Falls back to a simple programmatic diff if LLM call fails

In app/agent/nodes/save_and_display.py, write a node that:
- Uses file_namer.py to generate filename: "{company}_{role}_{YYYY-MM}.pdf"
  company and role come from state["jd_analysis"], sanitized for filesystem
- Saves PDF to state["output_folder"] with that name
- If config.save_history is True: creates outputs/history/{timestamp}_{company}_{role}/ 
  and saves .pdf, .tex, and changes_report.md there
- Stores final path in state["final_pdf_path"]
```

---

## Phase 5: Graph Assembly (15 min)

### Step 5.1 — Build the graph

**Prompt to AI**:
```
In app/agent/graph.py, build a LangGraph StateGraph using ResumeState.

Add these nodes in order:
load_inputs -> parse_resume -> analyze_jd -> tailor_sections -> validate_output -> assemble_latex -> compile_pdf -> generate_report -> save_and_display

Add a conditional edge after compile_pdf: 
- If state["errors"] contains a PDF compilation error, route to an "error" END state
- Otherwise continue to generate_report

Set load_inputs as the entry point.
Compile and return the graph.

Export a function run_agent(initial_state: dict) -> ResumeState that invokes the graph and returns final state.
```

---

## Phase 6: Gradio UI (30 min)

### Step 6.1 — Build the UI

**Prompt to AI**:
```
In app/main.py, build a Gradio UI for the resume tailoring agent.

Layout:
- Title: "ResumeForge — Resume Tailoring Agent"  
- Subtitle: "Upload a JD. Get a tailored PDF. See exactly what changed."

Left panel (inputs):
- File upload for JD (.txt) — required
- File upload for resume (.tex) — optional, uses default from config if not uploaded
- File upload for skills.md — optional, uses default
- File upload for projects.md — optional, uses default
- Text input for output folder path — pre-filled from config default
- Dropdown for Stage 2 model: ["openrouter", "cohere", "copilot"] — pre-selected from config
- Big button: "🚀 Tailor My Resume"

Right panel (outputs, shown after run):
- Tabs:
  Tab 1 "📋 Changes Made": Markdown component showing changes_report_md
  Tab 2 "📄 LaTeX Preview": Code component (language="latex") showing final_tex
  Tab 3 "⬇️ Download PDF": File component for downloading the PDF
- Status/log area: Textbox that updates during processing showing which section is being processed
- Error display: shows state["errors"] if any, in a warning box

Wire up the button to call run_agent() with the uploaded files.
Show a loading spinner during processing.
After completion, populate all three tabs.

At the bottom of the file:
if __name__ == "__main__":
    demo.launch(inbrowser=True, server_name="0.0.0.0")
```

---

## Phase 7: Launch Scripts and Polish (10 min)

### Step 7.1 — Launch scripts

**Prompt to AI**:
```
Create these files in the project root:

run.bat (Windows):
- Activate .venv\Scripts\activate
- Run python app/main.py
- If .venv doesn't exist, create it first and install requirements.txt

run.sh (Linux/Mac):
- #!/bin/bash
- Same logic as run.bat but for Linux paths

Also add a --test flag to app/main.py that:
- Skips the Gradio UI
- Runs the agent on tests/sample_jd.txt and inputs/base_resume.tex
- Prints a summary of results
- Exits with code 0 if success, 1 if any errors
```

---

## Phase 8: Testing and Debugging

### Step 8.1 — When something breaks

**Prompt to AI (paste this + the error)**:
```
I'm getting this error when running ResumeForge:
[paste full error traceback here]

The relevant file is [filename]. Here's the current content:
[paste file content]

Fix the error. Explain what caused it in one sentence.
```

### Step 8.2 — When bullets are bad quality

If Stage 1 bullets are ATS-correct but still robotic, and Stage 2 isn't fixing them:

**Prompt to AI**:
```
The Stage 2 prose polish prompt in app/prompts/stage2_polish.py isn't producing good results.
Here's the current prompt: [paste it]
Here's an example of bad output: [paste a bullet]
Here's what I want it to sound like: [paste a good bullet]
Rewrite the Stage 2 prompt to produce the second style consistently.
```

---

## Milestones Checklist

- [ ] Phase 0: Project created, requirements installed, API keys in .env
- [ ] Phase 1: Can parse a real .tex resume into sections dict  
- [ ] Phase 2: Can make a successful API call to Gemini and OpenRouter
- [ ] Phase 3: Prompts look reasonable when printed
- [ ] Phase 4: Agent processes one section end-to-end
- [ ] Phase 5: Full graph runs on a test resume, produces PDF
- [ ] Phase 6: Gradio UI opens, processes a file, shows results
- [ ] Phase 7: run.sh / run.bat works with one double-click

**You're done when Phase 6 works.** Everything else is polish.
