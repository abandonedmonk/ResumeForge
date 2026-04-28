Anshuman Jena - Detailed Master Project Inventory
(Generated according to Resume Style Guide)

1. AskAlpha: Voice-Native Financial Research Agent
[Tech Stack: Python, AWS Bedrock (Nova Sonic 2), FastAPI, WebSockets, RAG, FAISS, Ragas, NumPy, Financial Data]
- Built a real-time voice agent orchestrating \textbf{4} financial backends over a single bidirectional WebSocket stream with native mid-sentence interruption.
- Engineered a dual-mode RAG pipeline (Bedrock KB + FAISS fallback) indexing \textbf{320} pages of SEC 10-K filings, tracking session state with a FastAPI Event Router.
- Evaluated RAG pipeline with Ragas over \textbf{37} queries, achieving faithfulness \textbf{0.85}, identifying a \textbf{27\%} zero-retrieval rate; optimized Monte Carlo engine to run \textbf{10,000} paths in \textbf{9.3ms} via NumPy vectorization.

2. CLIGenix: Natural Language to Bash Command Translator
[Tech Stack: Python, Hugging Face TRL, Unsloth, Ollama, GGUF Quantization, Typer, PEFT/LoRA, Llama-3.2]
- Developed a Typer-based CLI tool translating natural language into safe, low-latency Bash commands to enhance accessibility for non-expert Linux users.
- Fine-tuned TinyLlama-1.1B, achieving \textbf{74\%} accuracy, and Llama-3.2-3B, achieving \textbf{52\%} accuracy, on the NL2SH dataset in Alpaca format using Unsloth and Hugging Face TRL.
- Optimized inference for resource-constrained devices with \textbf{16GB} RAM and an i7 CPU by integrating GGUF quantization with Ollama for fast CPU/GPU execution.

3. Hybrid Quantum-Classical Portfolio Optimization
[Tech Stack: Python, Qiskit/PennyLane, VQE, Numba (JIT compilation), SciPy (L-BFGS-B), CPLEX, QUBO]
- Tackled a real-world portfolio optimization problem with \textbf{31} financial constraints to maximize returns using hybrid quantum-classical methods.
- Converted .lp formulations into QUBO models and implemented a Variational Quantum Eigensolver (VQE) using parameter-shift gradients JIT-compiled with Numba.
- Integrated L-BFGS-B classical convex optimization to update ansatz parameters, achieving theoretical allocations matching enterprise CPLEX solvers.

4. FCOSCraterNet: Dense Lunar Crater Detection
[Tech Stack: Python, PyTorch, Swin Transformers, BiFPN, ASPP, DeepMoon Dataset, OpenCV, CUDA]
- Architected a dense object detection model from scratch, integrating a Swin Transformer backbone with Atrous Spatial Pyramid Pooling (ASPP) and a BiFPN decoder.
- Engineered a \textbf{6}-stage dynamic loss schedule coupling Balanced L1 and DIoU objectives, using size-stratified gradient weighting to counteract target under-representation.
- Achieved a \textbf{68.8\%} F1 score on the DeepMoon benchmark dataset, driving a substantial precision increase from \textbf{72\%} to \textbf{77\%} by algorithmically suppressing false positives.

5. Food Package and Freshness Detection
[Tech Stack: Python, PyTorch, YOLO, LLaMA, Vision-Language Models (VLM), OpenCV, OCR]
- Built a cross-modal computer vision system integrating YOLO object detection and LLaMA to analyze raw food freshness and product packaging, achieving \textbf{90\%} accuracy.
- Engineered an interactive multimodal pipeline to bridge visual classification of ripeness stages with generative NLP for structured data extraction.
- Extracted key product details including brand, ingredients, nutrition, expiry dates, and allergen warnings from complex, unstructured visual inputs.

6. End-to-End MLOps Pipeline for Cardiovascular Disease Prediction
[Tech Stack: Python, MLflow, Prefect, FastAPI, Docker, Scikit-Learn, Pandas, Tabular Data]
- Built an end-to-end MLOps pipeline for heart disease prediction using the UCI Cleveland dataset with \textbf{303} records and \textbf{13} features, achieving \textbf{85\%} accuracy.
- Implemented a reproducible automated workflow using MLflow for experiment tracking, Prefect for orchestration, FastAPI for serving, and Docker for containerization.
- Automated the full model lifecycle across continuous training, registry management, and deployment to ensure a scalable, production-ready architecture.

7. Autonomous War-Torn Navigation System
[Tech Stack: Python, C++, PyTorch, OpenCV, GIS Dashboards, Shortest Path Algorithms, Hardware/IoT]
- Built an autonomous rescue system for unmanned vehicles in war-torn environments using PyTorch and OpenCV, achieving \textbf{80\%} obstacle detection accuracy.
- Designed a multi-stage pipeline processing IR sensor and camera module inputs, computing the safest routing via a shortest path planning algorithm.
- Deployed optimized paths to a ground bot via Bluetooth and integrated a GIS dashboard for live remote monitoring across dynamic hazardous terrains.
