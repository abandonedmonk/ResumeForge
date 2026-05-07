1. AskAlpha: Voice-Native Financial Research Agent
[GitHub URL: https://github.com/abandonedmonk/AskAlpha-Nova-Sonic-Financial-Research-Analyst]
[Tech Stack: Python, AWS Bedrock Nova Sonic 2, FastAPI, WebSockets, React, TypeScript, FAISS, Ragas, NumPy, Finnhub, Polygon, Groq]
[Keywords: Voice AI, AWS Bedrock, Nova Sonic, FastAPI, WebSockets, RAG, FAISS, SEC filings, Monte Carlo, React, TypeScript, agentic tools]
- Built a real-time voice agent orchestrating **4** financial backends over a single bidirectional WebSocket stream with native mid-sentence interruption.
- Engineered a dual-mode RAG pipeline (Bedrock KB + FAISS fallback) indexing **320** pages of SEC 10-K filings, tracking session state with a FastAPI Event Router.
- Evaluated RAG pipeline with Ragas over **37** queries, achieving faithfulness **0.85**, identifying a **27\%** zero-retrieval rate; optimized Monte Carlo engine to run **10,000** paths in **9.3ms** via NumPy vectorization.

### What the repo actually contains
The repository implements a voice-native financial research assistant with a FastAPI backend, a React + Vite frontend, a Nova Sonic session layer, and four tool backends exposed through a single event router. The backend accepts microphone audio over `/ws/voice`, forwards it to Bedrock Nova Sonic, receives tool-call events, dispatches them into Python handlers, and streams synthesized speech back to the browser.

### Core architecture
- `main.py` boots the FastAPI app and mounts the event router.
- `event_router/router.py` is the dispatch hub for the four tools and owns the WebSocket control/audio flow.
- `nova_sonic/session.py` and `nova_sonic/client.py` manage bidirectional Bedrock streaming, transcripts, tool events, and response completion events.
- `tools/market_data.py`, `tools/sec_rag.py`, `tools/quant_model.py`, and `tools/vault_logger.py` implement live quotes, SEC filing retrieval, Monte Carlo simulations, and Obsidian-compatible note logging.
- `compute/monte_carlo.py` contains the GBM simulator with NumPy and pure-Python fallback paths.
- `frontend/` contains the React 19 + TypeScript UI, voice interface, visualizer, and vault viewer.

### Repo-backed implementation details
The SEC filing tool prefers AWS Bedrock Knowledge Base retrieval and falls back to a local FAISS index when the KB is unavailable. The Monte Carlo path simulates Geometric Brownian Motion and returns percentile bands plus mean projection. The vault logger stores structured markdown notes with front matter, evidence, risks, and next steps. Tests cover the event router, Nova Sonic session handling, market data, SEC RAG, Monte Carlo, vault logging, and end-to-end tool smoke flows.

### Resume-safe metrics
Use the numeric claims in the top three bullets exactly as written. The repo README independently supports the existence of the **4** tools and the **10,000**-path simulation flow, while the evaluation numbers come from the verified master inventory.

### ATS keywords
AWS Bedrock, Nova Sonic, FastAPI, WebSockets, RAG, FAISS, evaluation, Monte Carlo simulation, React, TypeScript, voice interface, agentic workflows.
