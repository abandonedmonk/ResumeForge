"""GitHub Gap-Finder — the delta between what you built and what your resume claims.

Three stages, only the last touches an LLM:

  Stage 1 (0 tokens)  pre-filter the user's repos by JD relevance, locally.
  Stage 2 (0 tokens)  summarise the top repos into a compact inventory (READMEs
                      fetched only for survivors — cheap on the GitHub rate limit).
  Stage 3 (~1.2k tok) one grounded gap-analysis call (Gemini Flash via task routing).

This is a second output of the GitHub ingestion that already exists (Phase 5),
not new infrastructure.
"""
from __future__ import annotations

import json
import re

from app.integrations.github import fetch_repo, fetch_user_repos
from app.llm.router import RoutedStage1Model
from app.prompts.gap import build_gap_prompt
from app.utils.json_utils import extract_json_blob
from app.utils.keyword_matcher import build_synonym_map, find_keyword_in_text

# Common JD words that carry no filtering signal.
_STOPWORDS = frozenset(
    {
        "and", "the", "for", "with", "you", "your", "our", "will", "are", "have", "has",
        "this", "that", "from", "who", "what", "work", "working", "team", "teams", "role",
        "experience", "years", "ability", "strong", "excellent", "including", "such", "using",
        "job", "candidate", "candidates", "must", "should", "plus", "etc", "responsibilities",
        "requirements", "preferred", "nice", "want", "looking", "join", "build",
    }
)


def extract_jd_keywords(jd_text: str, limit: int = 25) -> list[str]:
    """Local, 0-token keyword extraction from a JD: notable lowercased tokens ordered by
    frequency. Good enough to rank repo relevance without an LLM."""
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9+#.]{2,}", jd_text.lower())
    counts: dict[str, int] = {}
    for token in tokens:
        if token in _STOPWORDS:
            continue
        counts[token] = counts.get(token, 0) + 1
    ranked = sorted(counts, key=lambda word: (-counts[word], word))
    return ranked[:limit]


def _repo_haystack(repo: dict) -> str:
    parts = [repo.get("repo", ""), repo.get("description", ""), repo.get("language", "")]
    parts.extend(repo.get("topics", []) or [])
    return " ".join(str(part) for part in parts)


def prefilter_repos(repos: list[dict], jd_keywords: list[str], top_n: int = 5) -> list[dict]:
    """Score each (non-fork) repo by JD-keyword overlap in its name/description/topics/
    language, and keep the top ``top_n``. Ties break on stars then recency."""
    synonym_map = build_synonym_map()
    scored: list[tuple[int, dict]] = []
    for repo in repos:
        if repo.get("fork"):
            continue
        haystack = _repo_haystack(repo)
        score = sum(1 for keyword in jd_keywords if find_keyword_in_text(keyword, haystack, synonym_map))
        scored.append((score, repo))
    scored.sort(
        key=lambda item: (item[0], item[1].get("stargazers_count", 0), item[1].get("pushed_at", "")),
        reverse=True,
    )
    return [repo for _score, repo in scored[:top_n]]


def _first_sentences(readme_md: str, count: int = 2) -> str:
    """First ``count`` prose sentences of a README, stripped of markdown chrome."""
    text = readme_md or ""
    text = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)  # code blocks
    # Drop heading lines (they are labels, not prose) and image/badge lines.
    kept = [line for line in text.splitlines() if not line.strip().startswith(("#", "!["))]
    text = "\n".join(kept)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)  # inline images
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)  # links -> text
    text = re.sub(r"[#>*_`|-]+", " ", text)  # md punctuation
    text = re.sub(r"\s+", " ", text).strip()
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return " ".join(sentences[:count]).strip()


def summarize_repos(repos: list[dict], token: str = "") -> tuple[str, list[dict]]:
    """Fetch READMEs for the selected repos and build a compact inventory (~200 tokens).
    Returns ``(inventory_text, summaries)``. A repo that fails to fetch is skipped."""
    summaries: list[dict] = []
    lines: list[str] = []
    for repo in repos:
        try:
            full = fetch_repo(repo["owner"], repo["repo"], token)
        except Exception:
            continue
        blurb = _first_sentences(full.get("readme", "")) or full.get("description", "")
        summary = {
            "repo": repo["repo"],
            "language": full.get("language", "") or repo.get("language", ""),
            "date_range": full.get("date_range", "") or repo.get("date_range", ""),
            "stars": repo.get("stargazers_count", 0),
            "blurb": blurb,
        }
        summaries.append(summary)
        lines.append(
            f"Repo: {summary['repo']} | {summary['language'] or 'n/a'} | "
            f"{summary['date_range'] or 'n/a'} | stars {summary['stars']}\n\"{blurb}\""
        )
    return "\n".join(lines), summaries


def analyze_gap(inventory: str, resume_text: str) -> dict:
    """Stage 3: one grounded gap-analysis call. Returns the parsed schema, with empty
    lists on a malformed response so callers always get the full shape."""
    system_prompt, user_prompt = build_gap_prompt(inventory, resume_text)
    raw = RoutedStage1Model(task="gap_analysis").call(system_prompt, user_prompt)
    try:
        payload = json.loads(extract_json_blob(raw))
    except json.JSONDecodeError:
        payload = {}
    keys = ("missing", "undersold", "overclaimed", "suggested_bullets")
    return {key: [str(item) for item in (payload.get(key) or [])] for key in keys}


def run_gap_finder(
    username: str,
    resume_text: str,
    jd_text: str,
    token: str = "",
    top_n: int = 5,
) -> dict:
    """Full pipeline: list repos -> pre-filter by JD -> summarise -> analyse gap."""
    repos = fetch_user_repos(username, token)
    keywords = extract_jd_keywords(jd_text)
    selected = prefilter_repos(repos, keywords, top_n)
    inventory, summaries = summarize_repos(selected, token)
    analysis = analyze_gap(inventory, resume_text) if inventory else {
        "missing": [], "undersold": [], "overclaimed": [], "suggested_bullets": []
    }
    return {"repos": summaries, "inventory": inventory, "analysis": analysis}


def render_gap(result: dict) -> str:
    """Human-readable summary for the CLI."""
    analysis = result.get("analysis", {})

    def _block(title: str, items: list[str]) -> list[str]:
        if not items:
            return [f"{title}: none"]
        return [f"{title}:", *(f"  - {item}" for item in items)]

    repos = ", ".join(summary.get("repo", "") for summary in result.get("repos", [])) or "none"
    lines = [
        "GitHub Gap-Finder",
        "-----------------",
        f"Repos analysed: {repos}",
        "",
        *_block("Missing from resume", analysis.get("missing", [])),
        *_block("Undersold", analysis.get("undersold", [])),
        *_block("Overclaimed (verify)", analysis.get("overclaimed", [])),
        *_block("Suggested bullets", analysis.get("suggested_bullets", [])),
    ]
    return "\n".join(lines)
