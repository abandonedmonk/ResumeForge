"""Minimal, cross-platform TeX bootstrap.

Installs TinyTeX (~150-300MB, no admin) only when ``pdflatex`` is missing, then
``tlmgr install``s just the packages ResumeForge's templates need — avoiding a
multi-GB TeX Live / MiKTeX. Used by run.sh / run.ps1 and the Dockerfile via
``python -m app.utils.tex_bootstrap``; also importable so the app can self-heal
its PATH when launched directly.

Idempotent: skips install when ``pdflatex`` is already on PATH; ``tlmgr`` skips
already-present packages. All network/tlmgr failures are non-fatal and logged.
"""
from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

from app.utils.config import ROOT_DIR

# LaTeX packages the templates use that may not be in the TinyTeX base. tlmgr
# skips any already installed; unknown names are reported but don't abort the rest.
REQUIRED_PACKAGES = [
    "anyfontsize", "titlesec", "marvosym", "xcolor", "enumitem", "hyperref",
    "fancyhdr", "babel", "babel-english", "geometry", "soul", "preprint",
    "tools", "latexsym",
]

_UNIX_INSTALLER = "https://yihui.org/tinytex/install-bin-unix.sh"
_WIN_INSTALLER = "https://yihui.org/tinytex/install-bin-windows.bat"
_READY_MARKER = ROOT_DIR / ".venv" / ".tex_ready"


def _is_windows() -> bool:
    return platform.system().lower().startswith("win")


def tinytex_root() -> Path:
    if _is_windows():
        base = os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))
        return Path(base) / "TinyTeX"
    return Path.home() / ".TinyTeX"


def tinytex_bin_dirs() -> list[Path]:
    """Candidate TinyTeX ``bin`` directories (layout is ``<root>/bin/<arch>``)."""
    root = tinytex_root()
    bin_root = root / "bin"
    if not bin_root.is_dir():
        return []
    return [d for d in bin_root.iterdir() if d.is_dir()]


def _find_on_path(name: str) -> str | None:
    return shutil.which(name)


def _find_in_tinytex(name: str) -> str | None:
    exe = f"{name}.exe" if _is_windows() else name
    for bin_dir in tinytex_bin_dirs():
        candidate = bin_dir / exe
        if candidate.exists():
            return str(candidate)
    return None


def pdflatex_available() -> bool:
    return _find_on_path("pdflatex") is not None or _find_in_tinytex("pdflatex") is not None


def add_tinytex_to_path() -> str | None:
    """Prepend the TinyTeX bin dir to ``os.environ['PATH']`` if pdflatex isn't found.

    Lets ``python -m app.main`` locate a TinyTeX install even when launched
    without the run script. Returns the bin dir added, or None.
    """
    if _find_on_path("pdflatex"):
        return None
    for bin_dir in tinytex_bin_dirs():
        if (bin_dir / ("pdflatex.exe" if _is_windows() else "pdflatex")).exists():
            os.environ["PATH"] = str(bin_dir) + os.pathsep + os.environ.get("PATH", "")
            return str(bin_dir)
    return None


def _run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    print(f"[tex-bootstrap] $ {' '.join(cmd)}")
    return subprocess.run(cmd, check=False, **kwargs)


def install_tinytex() -> bool:
    """Install TinyTeX for the current OS. Returns True on apparent success."""
    print("[tex-bootstrap] pdflatex not found — installing TinyTeX (minimal, no admin)...")
    try:
        if _is_windows():
            bat = Path(tempfile.gettempdir()) / "install-tinytex.bat"
            urllib.request.urlretrieve(_WIN_INSTALLER, bat)  # noqa: S310 (trusted URL)
            _run(["cmd", "/c", str(bat)])
        else:
            script = Path(tempfile.gettempdir()) / "install-tinytex.sh"
            urllib.request.urlretrieve(_UNIX_INSTALLER, script)  # noqa: S310
            _run(["sh", str(script)])
    except Exception as exc:  # network / installer failure
        print(f"[tex-bootstrap] TinyTeX install failed: {exc}")
        return False
    return bool(tinytex_bin_dirs())


def _tlmgr() -> str | None:
    return _find_on_path("tlmgr") or _find_in_tinytex("tlmgr")


def ensure_packages() -> None:
    """Install the required LaTeX packages via tlmgr (no-op without tlmgr, e.g. MiKTeX)."""
    tlmgr = _tlmgr()
    if not tlmgr:
        print("[tex-bootstrap] tlmgr not available (non-TinyTeX TeX?) — skipping package install.")
        return
    result = _run([tlmgr, "install", *REQUIRED_PACKAGES], capture_output=True, text=True)
    output = (result.stdout or "") + (result.stderr or "")
    if result.returncode != 0:
        print(f"[tex-bootstrap] tlmgr reported issues (non-fatal):\n{output.strip()[-1000:]}")
    else:
        print("[tex-bootstrap] LaTeX packages ensured.")


def ensure_tex(auto_install: bool = True) -> str | None:
    """Ensure pdflatex + required packages. Returns the TeX bin dir, or None.

    - pdflatex already present -> ensure packages, return its dir.
    - missing + auto_install   -> install TinyTeX, ensure packages.
    - missing + no auto_install -> return None (caller prints instructions).
    """
    if not pdflatex_available():
        if not auto_install:
            return None
        if not install_tinytex():
            return None

    add_tinytex_to_path()
    ensure_packages()

    found = _find_on_path("pdflatex") or _find_in_tinytex("pdflatex")
    return str(Path(found).parent) if found else None


def main() -> int:
    bin_dir = ensure_tex(auto_install="--no-install" not in sys.argv)
    if not bin_dir:
        print(
            "[tex-bootstrap] No TeX toolchain available. Install TinyTeX "
            "(https://yihui.org/tinytex/) or a LaTeX distribution providing pdflatex."
        )
        return 1
    print(f"[tex-bootstrap] Ready. pdflatex at: {bin_dir}")
    try:
        _READY_MARKER.parent.mkdir(parents=True, exist_ok=True)
        _READY_MARKER.write_text(bin_dir, encoding="utf-8")
    except OSError:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
