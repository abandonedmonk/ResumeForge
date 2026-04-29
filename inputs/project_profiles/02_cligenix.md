1. CLIGenix: Natural Language to Bash Command Translator
[GitHub URL: https://github.com/abandonedmonk/CLIGenix]
[Tech Stack: Python, Typer, Ollama, Cohere, Hugging Face TRL, Unsloth, PEFT/LoRA, GGUF, Poetry, Serper]
[Keywords: CLI tooling, LLM inference, Typer, Ollama, Cohere, quantization, fine-tuning, PEFT, LoRA, shell command generation]
- Developed a Typer-based CLI tool translating natural language into safe, low-latency Bash commands to enhance accessibility for non-expert Linux users.
- Fine-tuned TinyLlama-1.1B, achieving **74\%** accuracy, and Llama-3.2-3B, achieving **52\%** accuracy, on the NL2SH dataset in Alpaca format using Unsloth and Hugging Face TRL.
- Optimized inference for resource-constrained devices with **16GB** RAM and an i7 CPU by integrating GGUF quantization with Ollama for fast CPU/GPU execution.

### What the repo actually contains
The repo packages a Python CLI around LLM-backed command generation. `cligenix/cli.py` exposes a Typer command that accepts natural-language queries, lets the user choose between Cohere and Ollama, and prints the generated shell command. `cligenix/llm.py` applies a constrained system prompt, routes queries to Cohere or a local Ollama model, and triggers a Serper-backed search fallback when the model is unsure.

### Core architecture
- `cligenix/cli.py` defines the `input-query` command and validates model choices.
- `cligenix/llm.py` contains the command-only system prompt, provider adapters, and search-enhanced retry path.
- `tests/` includes Typer CLI tests and package smoke checks.
- `pyproject.toml`, `poetry.lock`, and the `Dockerfile` show the project is intended to be packaged and reproducibly installed.

### Repo-backed implementation details
The CLI is intentionally minimal: it focuses on fast inference, deterministic command-only responses, and a fallback path for uncertain queries. The search fallback pattern is useful resume context because it shows retrieval-augmented command generation rather than plain prompt-response wrapping. The fine-tuning and benchmark metrics are not stored in this repo, so the top bullets should remain the source of truth for those numbers.

### Resume-safe metrics
Preserve **74\%**, **52\%**, and **16GB** exactly from the verified master inventory. Treat the repo as architectural proof for the CLI and local-inference workflow, not as the evidence source for the benchmark scores.

### ATS keywords
Typer, CLI tooling, Ollama, Cohere, quantization, PEFT, LoRA, fine-tuning, shell automation, local inference, prompt routing.
