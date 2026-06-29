# One-command start for Windows: venv + deps + minimal TeX (TinyTeX) + launch.
$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

# 1. Virtual environment
if (-not (Test-Path ".venv")) {
    Write-Host "Creating virtual environment..."
    if (Get-Command py -ErrorAction SilentlyContinue) { py -3 -m venv .venv } else { python -m venv .venv }
}
& ".\.venv\Scripts\Activate.ps1"

# 2. Python dependencies (first run only)
if (-not (Test-Path ".venv\.installed")) {
    Write-Host "Installing Python dependencies..."
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt
    New-Item -ItemType File -Path ".venv\.installed" | Out-Null
}

# 3. Minimal TeX toolchain (TinyTeX) — only if pdflatex is missing
if (-not (Test-Path ".venv\.tex_ready")) {
    Write-Host "Ensuring a minimal TeX toolchain (TinyTeX); this is a one-time step..."
    python -m app.utils.tex_bootstrap
}

# 4. Launch
python -m app.main @args
