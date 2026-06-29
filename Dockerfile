# ResumeForge — minimal image: Python + TinyTeX (only the LaTeX packages we use).
FROM python:3.11-slim

# TinyTeX prerequisites (perl) + a downloader + fonts. --no-install-recommends keeps it lean.
RUN apt-get update && apt-get install -y --no-install-recommends \
        perl wget ca-certificates fontconfig \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first for layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Install TinyTeX + the required LaTeX packages into the image (same bootstrap as run.sh).
RUN python -m app.utils.tex_bootstrap

# Make the TinyTeX binaries available at runtime (compile_pdf also self-heals PATH).
ENV PATH="/root/.TinyTeX/bin/x86_64-linux:${PATH}"

EXPOSE 7860
CMD ["python", "-m", "app.main"]
