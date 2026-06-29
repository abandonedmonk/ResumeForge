"""GitHub repo fetcher for the profile builder.

Reads public repo metadata + the raw README via the GitHub REST API (no auth
needed, 60 req/hr anon vs 5000/hr with a token). The token here is the
importer's own ``GITHUB_API_TOKEN`` — NOT an LLM key — so it is passed directly
to ``fetch_repo`` and never routed through the keypool/keystore (where
``GITHUB_TOKEN`` already means the Copilot provider).
"""
from __future__ import annotations

import re

import requests

from app.utils.exceptions import ResumeForgeError

GITHUB_API = "https://api.github.com"
_TIMEOUT = 15
_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def parse_repo_url(url: str) -> tuple[str, str]:
    """Extract ``(owner, repo)`` from any common GitHub reference.

    Accepts ``owner/repo``, ``github.com/owner/repo``, the full
    ``https://github.com/owner/repo`` URL, a trailing ``.git`` or ``/``, and
    deeper paths like ``.../tree/main`` (only the first two segments are used).
    """
    text = (url or "").strip()
    if not text:
        raise ResumeForgeError("Empty GitHub repo URL.")
    text = text.split("?", 1)[0].split("#", 1)[0]
    text = re.sub(r"^[a-zA-Z]+://", "", text)
    text = re.sub(r"^(www\.)?github\.com/", "", text)
    text = text.strip("/")
    if text.endswith(".git"):
        text = text[: -len(".git")]
    parts = [segment for segment in text.split("/") if segment]
    if len(parts) < 2:
        raise ResumeForgeError(
            f"Could not parse a GitHub repo from {url!r}. "
            "Use 'owner/repo' or 'https://github.com/owner/repo'."
        )
    return parts[0], parts[1]


def _headers(token: str, accept: str) -> dict[str, str]:
    headers = {"User-Agent": "ResumeForge", "Accept": accept}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _raise_for_status(resp: requests.Response, owner: str, repo: str) -> None:
    if resp.status_code == 200:
        return
    if resp.status_code == 404:
        raise ResumeForgeError(
            f"Repo not found or private: {owner}/{repo}. "
            "Check the URL, or supply a GitHub token with access to it."
        )
    if resp.status_code in (401,):
        raise ResumeForgeError("GitHub token rejected (401). Check your GITHUB_API_TOKEN.")
    if resp.status_code == 403 and resp.headers.get("X-RateLimit-Remaining") == "0":
        raise ResumeForgeError(
            "GitHub API rate limit reached (60 requests/hr without a token). "
            "Add a GitHub token to raise the limit to 5000/hr, or wait and retry."
        )
    raise ResumeForgeError(
        f"GitHub API error {resp.status_code} for {owner}/{repo}: {resp.text[:200]}"
    )


def _fmt_month(iso: str) -> str:
    match = re.match(r"^(\d{4})-(\d{2})", iso or "")
    if not match:
        return ""
    year, month = match.group(1), int(match.group(2))
    if not 1 <= month <= 12:
        return ""
    return f"{_MONTHS[month - 1]}'{year[2:]}"


def _default_date_range(created_at: str, pushed_at: str) -> str:
    start, end = _fmt_month(created_at), _fmt_month(pushed_at)
    if start and end and start != end:
        return f"{start} – {end}"
    return start or end or ""


def fetch_repo(owner: str, repo: str, token: str = "") -> dict:
    """Fetch repo metadata + raw README. Raises ``ResumeForgeError`` on failure.

    A missing README is non-fatal (returns an empty ``readme`` so the generator
    can still work from metadata); auth/404/rate-limit errors are surfaced.
    """
    meta_resp = requests.get(
        f"{GITHUB_API}/repos/{owner}/{repo}",
        headers=_headers(token, "application/vnd.github+json"),
        timeout=_TIMEOUT,
    )
    _raise_for_status(meta_resp, owner, repo)
    meta = meta_resp.json()

    readme_resp = requests.get(
        f"{GITHUB_API}/repos/{owner}/{repo}/readme",
        headers=_headers(token, "application/vnd.github.raw"),
        timeout=_TIMEOUT,
    )
    if readme_resp.status_code == 404:
        readme_md = ""  # repo has no README; metadata-only is acceptable
    else:
        _raise_for_status(readme_resp, owner, repo)
        readme_md = readme_resp.text

    created_at = meta.get("created_at", "") or ""
    pushed_at = meta.get("pushed_at", "") or ""
    return {
        "owner": owner,
        "repo": repo,
        "full_name": meta.get("full_name") or f"{owner}/{repo}",
        "description": meta.get("description") or "",
        "language": meta.get("language") or "",
        "topics": meta.get("topics") or [],
        "html_url": meta.get("html_url") or f"https://github.com/{owner}/{repo}",
        "created_at": created_at,
        "pushed_at": pushed_at,
        "date_range": _default_date_range(created_at, pushed_at),
        "readme": readme_md,
    }
