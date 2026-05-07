# Resume Style Guide — Anshuman Jena

## Who I Am (inject this context into every rewrite)

Computer Engineering final year student (May 2026), Mumbai. Core identity: **AI/ML engineer who ships real systems** — not a researcher who only reads papers. I build agents, fine-tune models, evaluate pipelines, and deploy on cloud. GATE AIR 1388 in DSAI (Top 2.4%) and 2763 in CSE

---

## What the LLM Is Allowed to Touch

| Section | Rule |
|---|---|
| Heading summary (one-liner) | **TAILOR** — rewrite for every role |
| Skills section | **TAILOR** — reorder, emphasize relevant ones first |
| Internship bullets | **TAILOR** — reword keywords, keep all metrics |
| Project bullets | **TAILOR** — reword keywords, reorder projects by relevance |
| Certifications | **TAILOR** — drop irrelevant ones, keep links |
| Education, Achievements, Contact | **FIXED** — never touch |
| Any `\textbf{}` wrapped metric | **FIXED** — never remove or change the number |
| Project GitHub links | **FIXED** — never change URLs, use the one provided |

---

## Bullet Writing Rules (Non-Negotiable)

### Structure: Impact → Method → Scale
Every bullet must follow: **what was achieved → how → how big**

❌ Bad: `Worked on building a RAG pipeline for document search.`  
✅ Good: `Built a dual-mode RAG pipeline (Bedrock KB + FAISS fallback) for SEC 10-K search, achieving faithfulness 0.85 over 37 evaluation queries.`

❌ Bad: `Used PyTorch to fine-tune a language model.`  
✅ Good: `Fine-tuned TinyLlama-1.1B on NL2SH dataset using Unsloth + HuggingFace TRL, achieving 74% accuracy on resource-constrained hardware (16GB RAM, i7 CPU).`

### Metrics & Contextual Bolding
- Every number in the original bullet MUST appear in the rewritten bullet. Never round, estimate, or change a metric.
- Do not enclose metrics or numbers in parentheses or brackets (e.g., write `achieved \textbf{74\% accuracy}` instead of `(\textbf{74\%} accuracy)`).
- If a bullet has no metric, don't fabricate one.
- **Contextual Bolding (Crucial):** Never wrap just a naked number in `\textbf{}`. You MUST bold the *entire outcome phrase* or tool name.
  - ❌ Weak: `...yielding a faithfulness score of \textbf{0.85}`
  - ✅ Strong: `...yielding a \textbf{faithfulness score of 0.85}`
  - ❌ Weak: `Optimized Monte Carlo engine to run \textbf{10,000} paths in \textbf{9.3ms}`
  - ✅ Strong: `Optimized Monte Carlo engine to run \textbf{10,000 paths in 9.3ms}`

### Action Verb Rules
- Start every bullet with a **strong, specific past-tense verb**
- Vary verbs across bullets — never repeat the same verb twice in one section
- Preferred verbs for my profile: `Built`, `Implemented`, `Fine-tuned`, `Evaluated`, `Designed`, `Engineered`, `Deployed`, `Benchmarked`, `Optimized`, `Developed`, `Integrated`, `Architected`
- Banned openers: `Worked on`, `Helped with`, `Was responsible for`, `Assisted in`, `Participated in`

### Length and Density
- Max 2 lines per bullet when rendered in LaTeX (roughly 200 characters)
- Pack technical specificity — model names, library names, dataset names, framework names
- No filler phrases: `leveraging cutting-edge`, `state-of-the-art`, `robust`, `scalable solution`, `innovative approach`
- One idea per bullet — don't combine two achievements into one run-on sentence

### Tone & Diction (The "Anti-Buzzword" Rule)
- Tone: **Senior Engineer**, direct, technical, pragmatic.
- **NEVER** use: "Spearheaded", "Leveraged", "Synergistic", "Cutting-edge", "Game-changer", "Innovative", "Passionately", "Proven track record", "Deep dive", "Thrive", "Unlock".
- **DO** use: "Built", "Optimized", "Integrated", "Evaluated", "Rewrote", "Fixed", "Scaled".
- **Style**: Use simple conjunctions ("by", "using", "via"). Keep sentences dense with technical nouns and light on descriptive adjectives. No exclamation marks. No first person.
- **Human-only tests**: If a sentence sounds like it could be in a startup's marketing pitch, it is a fail. If it sounds like an entry in a high-quality Engineering Changelog, it is a win.

---

## Keyword Injection Rules (ATS Optimization)

When tailoring for a JD, strictly follow these ATS scoring recommendations:
- **Strategic Placement:** Move the most important JD keywords into your heading summary, skills block, and the *very first bullet* under your most recent/relevant experience. ATS scanners weight these sections heavily.
- **Natural Integration:** Add more required JD keywords naturally into your experience and project bullets. If a keyword fits the bullet's existing meaning, swap in the JD's terminology.
- **Show, Don't Tell:** Never list a soft-skill or generic keyword (like "Scalability", "Leadership", "Optimization") by itself. You MUST anchor it to a specific tool, architecture, or metric (e.g., instead of writing "Ensured scalability", write "Engineered for scalability by optimizing Monte Carlo paths to run in \textbf{9.3ms}").
- **No Keyword Stuffing:** Never add keywords that misrepresent what was actually done.
- **Terminology Mapping:** Map vague JD concepts to your exact technical tools. (e.g., 'evals' → `Ragas`, 'agentic workflows' → `LangGraph / CrewAI`, 'cloud' → `AWS (Bedrock, S3, etc)`). Never write bland placeholders.

---

## Project Ordering & Selection Logic
* **Selection:** Pick exactly 3 projects from the pool below that best match the target role.
    * *SaaS/Enterprise AI roles:* Prioritize AskAlpha, CLIGenix, MLOps Pipeline.
    * *Academic/Research roles:* Prioritize FCOSCraterNet, Quantum Portfolio, AskAlpha (as Neurosymbolic).
    * *Computer Vision/Geospatial roles:* Prioritize FCOSCraterNet, Food Package VLM, Autonomous Navigation.
    * *Agent Infrastructure / AI Systems / Security roles:* Prioritize Ironclad Agent, AskAlpha, CLIGenix.
* **Ordering:** When reordering the selected 3 projects for a JD, rank by:
    1. Domain match — does the project's core problem match the JD's domain?
    2. Tech stack overlap — does the project use tech explicitly mentioned in the JD?
    3. Recency — newer projects preferred if domain match is equal.
    4. Metric impressiveness — prefer projects with stronger quantified results.

Current projects and their domain tags:
1. **AskAlpha:** Voice AI, RAG, AWS Bedrock, FastAPI, WebSocket, financial data, agentic evaluation (Ragas), Neurosymbolic AI, Monte Carlo simulations.
2. **CLIGenix:** Fine-tuning, LLM inference, quantization (GGUF/Ollama), CLI tooling, NLP, resource-constrained deployment, PEFT/LoRA.
3. **Hybrid Quantum-Classical Portfolio Optimization:** Quantum computing, VQE, mathematical optimization, financial modeling, Numba (JIT), CPLEX, QUBO, L-BFGS-B.
4. **FCOSCraterNet:** Computer Vision, Object Detection, PyTorch from scratch, Swin Transformers, BiFPN, ASPP, custom dynamic loss functions, geospatial/spatial data.
5. **Food Package and Freshness Detection:** Multimodal AI, Vision-Language Models (VLM), YOLO, LLaMA, OCR, structured data extraction, image processing.
6. **End-to-End MLOps Pipeline for Cardiovascular Disease:** MLOps, Docker, MLflow, FastAPI, Prefect, classical ML (Scikit-learn), tabular/healthcare data, reproducible workflows.
7. **Autonomous War-Torn Navigation System:** Robotics/Navigation, geospatial mapping, path planning/shortest path algorithms, IR sensors, OpenCV, real-time decision engines.
8. **Ironclad Agent:** AI agents, secure code execution, Rust, WebAssembly, Wasmtime, audit logging, sandboxing, systems programming.
---

## Skills Section Ordering

* Always lead with the skill category most relevant to the JD (e.g., put "Computer Vision" first for a CV role, or "Cloud & MLOps" first for a backend AI role).
* **Full skills inventory (use only what's genuine):**
    * **Languages:** Python, C++, C, Rust, SQL, CUDA C/C++, Shell Scripting
    * **Deep Learning & Frameworks:** PyTorch, OpenCV, Hugging Face (TRL, Unsloth), Accelerate, Scikit-Learn, NumPy, SciPy, Pandas, Qiskit
    * **Gen AI & LLM Engineering:** Agentic Workflows, CrewAI, LangGraph, LLM Quantization (GGUF), RAG Architectures, FAISS, Fine-Tuning (PEFT/LoRA), Model Evaluation (Ragas), Multimodal Fusion, Prompt Engineering
    * **Computer Vision & 3D Perception:** Object Detection (YOLO, FCOS), OCR, Semantic/Instance Segmentation, Swin Transformers, BiFPN, ASPP, Feature Extraction
    * **Systems, Optimization & MLOps:** AWS (Bedrock, S3, Lambda, API Gateway), GCP, FastAPI, Docker, MLflow, Prefect, Git, Numba (JIT compilation), CPU/GPU Inference, WebSockets, Typer, Poetry, WebAssembly, Wasmtime
* *Do not add skills not listed here. Do not fabricate tools I haven't used.*

---

## One-Line Summary Rules (Heading)

The summary under my name must:
- Be exactly one sentence, max 30 words
- Name the specific role domain (e.g., "AI Research", "MLOps", "LLM Engineering") — not generic "software engineering"
- Mention 1–2 concrete things I've built or done
- End with what I bring to the role

Template: `{Domain} engineer with hands-on experience {specific thing 1} and {specific thing 2}, seeking to {what I bring} at {company/role type}.`

❌ Bad: `Passionate computer engineering student looking for opportunities in AI.`  
✅ Good: `AI engineer with hands-on experience fine-tuning LLMs and building production RAG pipelines, seeking to accelerate research infrastructure at an AI-first lab.`

---

## What NOT to Do (Hard Rules)

- **Never hallucinate a project** — only use projects listed in this file or in the template
- **Never change a GitHub URL**
- **Never remove `\textbf{}` from a metric**
- **Never change Education, GATE ranks, CGPA, or Achievements section**
- **Never add a publication** unless one is explicitly provided — leave the Publications section out if no paper is given
- **Never change dates** on any experience or project
- **Never invent a new internship** to fill a placeholder — if no new internship details are provided, keep Team Infits as-is
- **Never use passive voice** (`was built`, `was implemented`, `was used`)

---

## Output Shape For ResumeForge Personalization

When generating JD-tailored resume content for this project:

- The AI should choose the headline summary, the skills ordering/content, and the project selection based on the JD
- The AI should not output LaTeX directly for those sections; Python will format and inject the final LaTeX
- For project bullets and skill items, use plain text with optional Markdown-style bold markers like `**RAG Architectures**` or `**FAISS**`
- **Bold Full Phrases:** Use `**` sparingly, but wrap the entire core achievement or outcome phrase rather than isolated numbers (e.g., use `**faithfulness score of 0.85**`, not just `**0.85**`).
- Keep all facts grounded in the supplied project inventory and skill inventory
- Skills should be returned as ordered categories with ordered items, not as one flat blob
- Project selection should explain briefly why each chosen project matches the JD
- The headline should be a single sentence tailored to the role, keeping my AI/ML builder identity intact
