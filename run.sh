#!/usr/bin/env bash
# One-command start for Linux/macOS: venv + deps + minimal TeX (TinyTeX) + launch.
set -e
cd "$(dirname "$0")"

# 1. Virtual environment
if [ ! -d ".venv" ]; then
  echo "Creating virtual environment..."
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

# 2. Python dependencies (first run only)
if [ ! -f ".venv/.installed" ]; then
  echo "Installing Python dependencies..."
  python -m pip install --upgrade pip
  python -m pip install -r requirements.txt
  touch .venv/.installed
fi

# 3. Minimal TeX toolchain (TinyTeX) — only if pdflatex is missing
if [ ! -f ".venv/.tex_ready" ]; then
  echo "Ensuring a minimal TeX toolchain (TinyTeX); this is a one-time step..."
  python -m app.utils.tex_bootstrap || echo "TeX bootstrap incomplete — PDF generation may not work until LaTeX is available."
fi

# 4. Launch
python -m app.main "$@"
