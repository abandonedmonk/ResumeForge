1. Hybrid Quantum-Classical Portfolio Optimization
[GitHub URL: https://github.com/abandonedmonk/Hybrid-Quantum-Classical-approach-for-Portfolio-Optimization]
[Tech Stack: Python, Qiskit, Qiskit Aer, Docplex, CPLEX, Numba, SciPy, VQE, QUBO, L-BFGS-B]
[Keywords: quantum computing, VQE, QUBO, portfolio optimization, Qiskit, Numba, L-BFGS-B, CPLEX, mathematical optimization]
- Tackled a real-world portfolio optimization problem with **31** financial constraints to maximize returns using hybrid quantum-classical methods.
- Converted .lp formulations into QUBO models and implemented a Variational Quantum Eigensolver (VQE) using parameter-shift gradients JIT-compiled with Numba.
- Integrated L-BFGS-B classical convex optimization to update ansatz parameters, achieving theoretical allocations matching enterprise CPLEX solvers.

### What the repo actually contains
The repository centers on a hybrid workflow for a `31bonds` optimization instance. It starts from `.lp` formulations, converts them into objective functions and QUBO-style embeddings, compiles ansatz circuits, executes hardware or simulator runs, and performs post-processing/local search. The repo also contains experiment notebooks, figures for convergence analysis, and a presentation deck.

### Core architecture
- `src/model_to_qubo.py` parses Docplex models, extracts quadratic objectives and constraints, rescales constraint matrices, and embeds penalties into the optimization objective.
- `src/steps1to3.py` performs problem mapping, prepares an ISA ansatz, and launches repeated VQE executions with configurable backends, shots, and optimizer settings.
- `src/optimizer/` contains wrappers, monitors, and local-search utilities for classical post-processing.
- `src/step4.py` and `src/doe*.py` continue the workflow with design-of-experiments and local-search refinement.

### Repo-backed implementation details
The code explicitly uses Qiskit Aer simulators, generated pass managers, serialized ansatz artifacts, and hardware-executor abstractions for experiment runs. `model_to_qubo.py` uses Numba JIT to speed constraint-embedded objective evaluation, which is strong evidence for the optimization-heavy bullet. The README also states the solution matches a classical CPLEX reference, which supports the benchmarking claim.

### Resume-safe metrics
Keep **31** exactly from the verified master inventory. The repo itself also references a `31bonds` problem instance, so the project has numeric grounding even where the resume metric is phrased differently.

### ATS keywords
Qiskit, VQE, QUBO, CPLEX, Docplex, Numba, L-BFGS-B, portfolio optimization, quantum-classical hybrid, experiment tracking.
