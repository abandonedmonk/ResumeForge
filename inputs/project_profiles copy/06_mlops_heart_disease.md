1. End-to-End MLOps Pipeline for Cardiovascular Disease Prediction
[GitHub URL: https://github.com/abandonedmonk/End-to-End-MLOps-Pipeline-for-Cardiovascular-Disease-Prediction]
[Tech Stack: Python, Scikit-Learn, MLflow, Prefect, FastAPI, Docker, Pandas, NumPy, Poetry]
[Keywords: MLOps, MLflow, Prefect, FastAPI, Docker, model registry, experiment tracking, healthcare ML, orchestration]
- Built an end-to-end MLOps pipeline for heart disease prediction using the UCI Cleveland dataset with **303** records and **13** features, achieving **85\%** accuracy.
- Implemented a reproducible automated workflow using MLflow for experiment tracking, Prefect for orchestration, FastAPI for serving, and Docker for containerization.
- Automated the full model lifecycle across continuous training, registry management, and deployment to ensure a scalable, production-ready architecture.

### What the repo actually contains
The repository follows a cookiecutter-style MLOps layout with separate API, training, data, models, notebooks, and tests directories. The pipeline loads and preprocesses the Cleveland heart-disease dataset, trains multiple classical ML models, logs runs into MLflow, registers the best model, downloads the chosen artifact, and serves predictions through FastAPI and Docker.

### Core architecture
- `heart_disease_prediction/data.py` handles data loading and preprocessing.
- `heart_disease_prediction/train.py` trains multiple scikit-learn models inside a preprocessing pipeline and logs metrics and artifacts to MLflow.
- `heart_disease_prediction/register.py` and `load_model.py` manage model selection, registry interaction, and artifact download.
- `heart_disease_prediction/prefect_flow.py` stitches the end-to-end workflow into a Prefect flow.
- `api/main.py` loads the exported pipeline and exposes a `/predict` endpoint with Pydantic validation from `api/schema.py`.
- `tests/` covers API and data logic.

### Repo-backed implementation details
The training code compares Logistic Regression, Random Forest, HistGradientBoosting, and Decision Tree models under a shared `Pipeline` plus `ColumnTransformer` preprocessing path. MLflow uses a local SQLite backend and file-based artifact storage. The README also documents weekly Prefect deployment scheduling and Dockerized FastAPI inference, which is solid resume evidence for orchestration and serving.

### Resume-safe metrics
Use **303**, **13**, and **85\%** exactly from the verified master inventory. The repo README independently confirms the dataset size and feature count.

### ATS keywords
MLflow, Prefect, FastAPI, Docker, Scikit-Learn, model registry, orchestration, experiment tracking, healthcare machine learning, API serving.
