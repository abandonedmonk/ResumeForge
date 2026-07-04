"""Compression Receipt — an auditable, mostly-local diff of a tailoring run.

After tailoring, this surfaces *what actually changed*: words removed, bullets
strengthened / condensed, keyword deltas against the JD, and an overall semantic
similarity. It is deterministic and 0-token — pure string work reusing the ATS
keyword utilities. A hook is left to upgrade ``semantic_similarity`` to an
embedding comparison later, but the default stays local as the plan specifies.
"""
from __future__ import annotations

import re
from difflib import SequenceMatcher

from app.utils.keyword_matcher import (
    build_synonym_map,
    extract_metrics_from_bullet,
    extract_resume_bullets,
    find_keyword_in_text,
    strip_latex_commands,
)

# Strong action verbs — a bullet that gains one (or a metric) counts as strengthened.
ACTION_VERBS = frozenset(
    {
        "led", "built", "designed", "developed", "shipped", "launched", "reduced",
        "improved", "increased", "optimized", "architected", "implemented", "automated",
        "scaled", "drove", "delivered", "created", "engineered", "accelerated",
        "streamlined", "spearheaded", "orchestrated", "migrated", "refactored",
        "deployed", "cut", "boosted", "generated", "produced", "owned",
    }
)


def _word_tokens(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9+#.]+", text.lower())


def _starts_with_action_verb(bullet: str) -> bool:
    tokens = _word_tokens(bullet)
    return bool(tokens) and tokens[0] in ACTION_VERBS


def _count_strengthened(orig_bullets: list[str], new_bullets: list[str]) -> int:
    """Aligned bullet pairs where the rewrite gained an action-verb lead or a metric
    the original lacked."""
    strengthened = 0
    for original, new in zip(orig_bullets, new_bullets, strict=False):
        gained_verb = _starts_with_action_verb(new) and not _starts_with_action_verb(original)
        gained_metric = extract_metrics_from_bullet(new) and not extract_metrics_from_bullet(original)
        if gained_verb or gained_metric:
            strengthened += 1
    return strengthened


def _keyword_delta(keywords: list[str], before: str, after: str, synonym_map: dict) -> dict[str, list[str]]:
    added: list[str] = []
    removed: list[str] = []
    seen: set[str] = set()
    for keyword in keywords:
        key = keyword.strip()
        if not key or key.lower() in seen:
            continue
        seen.add(key.lower())
        in_before = find_keyword_in_text(key, before, synonym_map)
        in_after = find_keyword_in_text(key, after, synonym_map)
        if in_after and not in_before:
            added.append(key)
        elif in_before and not in_after:
            removed.append(key)
    return {"added": added, "removed": removed}


def build_receipt(original_tex: str, tailored_tex: str, jd_analysis: dict | None = None) -> dict:
    """Compute the compression receipt comparing original vs tailored LaTeX."""
    jd_analysis = jd_analysis or {}
    synonym_map = build_synonym_map()

    orig_bullets = extract_resume_bullets(original_tex)
    new_bullets = extract_resume_bullets(tailored_tex)
    orig_text = " ".join(orig_bullets) if orig_bullets else strip_latex_commands(original_tex)
    new_text = " ".join(new_bullets) if new_bullets else strip_latex_commands(tailored_tex)

    words_before = _word_tokens(orig_text)
    words_after = _word_tokens(new_text)

    reductions: list[float] = []
    for original, new in zip(orig_bullets, new_bullets, strict=False):
        len_before, len_after = len(original.split()), len(new.split())
        if len_before > 0 and len_after < len_before:
            reductions.append((len_before - len_after) / len_before)

    keywords = [str(k) for k in (jd_analysis.get("keywords") or [])]
    keywords += [str(k) for k in (jd_analysis.get("required_skills") or [])]
    delta = _keyword_delta(keywords, orig_text, new_text, synonym_map)

    return {
        "words_before": len(words_before),
        "words_after": len(words_after),
        "words_removed": max(0, len(words_before) - len(words_after)),
        "bullets_before": len(orig_bullets),
        "bullets_after": len(new_bullets),
        "bullets_strengthened": _count_strengthened(orig_bullets, new_bullets),
        "bullets_condensed": len(reductions),
        "avg_condense_pct": round(sum(reductions) / len(reductions) * 100) if reductions else 0,
        "semantic_similarity": round(SequenceMatcher(None, orig_text, new_text).ratio() * 100),
        "keywords_added": delta["added"],
        "keywords_removed": delta["removed"],
    }


def build_receipt_from_state(state: dict) -> dict:
    """Convenience wrapper: build a receipt from a finished pipeline state."""
    return build_receipt(
        state.get("original_resume_tex", ""),
        state.get("final_tex", ""),
        state.get("jd_analysis", {}),
    )


def render_receipt(receipt: dict) -> str:
    """Human-readable summary for the CLI."""
    added = ", ".join(receipt.get("keywords_added", [])) or "none"
    removed = ", ".join(receipt.get("keywords_removed", [])) or "none"
    return "\n".join(
        [
            "Compression Receipt",
            "-------------------",
            f"Words:        {receipt.get('words_before', 0)} -> {receipt.get('words_after', 0)} "
            f"({receipt.get('words_removed', 0)} removed)",
            f"Strengthened: {receipt.get('bullets_strengthened', 0)} bullets (action verbs / metrics)",
            f"Condensed:    {receipt.get('bullets_condensed', 0)} bullets by avg {receipt.get('avg_condense_pct', 0)}%",
            f"Similarity:   {receipt.get('semantic_similarity', 0)}% semantic overlap with original",
            f"Keywords +:   {added}",
            f"Keywords -:   {removed}",
        ]
    )
