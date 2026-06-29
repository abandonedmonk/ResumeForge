"""Orchestrate: GitHub URL -> repo fetch -> LLM distill -> serialized profile.

Each repo is processed independently so one bad URL never fails the batch. A
self-check re-parses the serialized markdown through ``parse_projects_md`` and
skips (rather than writes) anything malformed.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

from app.integrations.github import fetch_repo, parse_repo_url
from app.integrations.profile_store import profile_filename
from app.llm.router import RoutedModel
from app.parsers.projects_parser import parse_projects_md
from app.prompts.profile_from_readme import build_profile_prompt, serialize_profile
from app.utils.exceptions import ResumeForgeError
from app.utils.json_utils import extract_json_blob


@dataclass
class ImportResult:
    url: str
    ok: bool
    message: str
    owner: str = ""
    repo: str = ""
    filename: str = ""
    content: str = ""


def build_profile_for_repo(url: str, token: str = "") -> ImportResult:
    """Fetch one repo and return a serialized, self-checked profile result."""
    owner, repo = parse_repo_url(url)
    meta = fetch_repo(owner, repo, token=token)
    system_prompt, user_prompt = build_profile_prompt(meta, meta.get("readme", ""))
    raw = RoutedModel("stage1").call(system_prompt, user_prompt)
    try:
        payload = json.loads(extract_json_blob(raw))
    except json.JSONDecodeError as exc:
        raise ResumeForgeError(f"LLM returned unparseable JSON for {owner}/{repo}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ResumeForgeError(f"LLM payload for {owner}/{repo} was not a JSON object.")

    content = serialize_profile(meta, payload)
    parsed = parse_projects_md(content)
    if not parsed:
        raise ResumeForgeError(
            f"Generated profile for {owner}/{repo} did not parse back into a project — skipped."
        )
    project = next(iter(parsed.values()))
    if not project.get("bullets"):
        raise ResumeForgeError(f"Generated profile for {owner}/{repo} had no bullets — skipped.")

    return ImportResult(
        url=url,
        ok=True,
        message=f"Imported {owner}/{repo}",
        owner=owner,
        repo=repo,
        filename=profile_filename(owner, repo),
        content=content,
    )


def import_profiles(urls: list[str], token: str = "") -> list[ImportResult]:
    """Process every URL, capturing per-repo failures instead of aborting the batch."""
    results: list[ImportResult] = []
    for url in urls:
        cleaned = url.strip()
        if not cleaned:
            continue
        try:
            results.append(build_profile_for_repo(cleaned, token=token))
        except ResumeForgeError as exc:
            results.append(ImportResult(url=cleaned, ok=False, message=str(exc)))
        except Exception as exc:  # network/SDK surprises shouldn't kill the batch
            results.append(ImportResult(url=cleaned, ok=False, message=f"Unexpected error: {exc}"))
    return results
