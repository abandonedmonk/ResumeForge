1. Ironclad Agent: Secure WebAssembly Runtime for AI Agents
[GitHub URL: https://github.com/abandonedmonk/Ironclad-Agent]
[Tech Stack: Rust, WebAssembly, Wasmtime, WASI, Python, Rig, Cohere, SHA-256, ReAct agents]
[Keywords: AI agents, Rust, WebAssembly, Wasmtime, WASI, secure sandboxing, audit logs, code execution, systems programming]
- Built a zero-trust agent runtime that executes LLM-generated Python inside a WebAssembly sandbox with network isolation, filesystem confinement, and tamper-evident audit logging.
- Implemented a Rust-based Wasmtime runtime that hashes every script with SHA-256, enforces fuel-based execution budgets, and returns structured execution output for agent-side reasoning loops.
- Benchmarked the sandbox against Docker, documenting **4.26x** median speedup and roughly **90\%** lower per-execution memory overhead through Wasmtime caching.

### What the repo actually contains
Ironclad is a systems-heavy agent project split between a Rust sandbox runtime and an agent layer. The runtime loads a prebuilt Python 3.12 WASM interpreter, mounts a constrained WASI context, meters CPU fuel, blocks network access, appends JSON audit records, and supports offline verification of prior executions. The agent side implements a ReAct-style loop that can generate code, persist it to a sandbox script, call the runtime, and reason over the result.

### Core architecture
- `src/main.rs` is the main Rust runtime with CLI parsing, Wasmtime engine configuration, entrypoint discovery, fuel handling, script hashing, and sandbox execution.
- `src/audit.rs`, `src/crypto.rs`, and `src/verify.rs` implement append-only audit logging, SHA-256 hashing, and execution verification.
- `agent/src/main.rs` contains the reasoning loop, response parsing, tool definition, and subprocess invocation of the sandbox runtime.
- `tests/smoke/` covers normal execution, network isolation, filesystem escape attempts, infinite loops, and audit behavior.
- `tests/benchmarks/` measures warm-start benchmark performance and compares it with Docker.

### Repo-backed implementation details
The runtime explicitly distinguishes supported WASM entrypoints, classifies out-of-fuel traps, and serializes execution results as JSON with stdout, stderr, exit code, and error fields. The audit log stores script hash, ISO timestamp, duration, exit code, and output preview. The benchmark narrative is part of the repo’s README and benchmark harness, making this a strong systems/security project for AI infrastructure roles.

### Resume-safe metrics
The repo itself documents **4.26x** speedup and about **90\%** lower memory overhead, so these metrics can be used directly. Do not invent extra runtime-security numbers beyond what the README and code already support.

### ATS keywords
Rust, WebAssembly, Wasmtime, WASI, sandboxing, secure code execution, audit logging, SHA-256, ReAct agents, systems programming.
