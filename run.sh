#!/usr/bin/env bash
set -e

# Activate a local virtualenv or conda env if present, then launch the app.
if [ -d ".venv" ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
elif command -v conda >/dev/null 2>&1; then
  conda activate resumeforge 2>/dev/null || true
fi

python -m app.main "$@"
