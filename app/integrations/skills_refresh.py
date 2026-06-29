"""Suggest skill additions from imported profiles — additive, never destructive.

Unions the ``tech_stack``/``keywords`` across imported profiles, buckets them
into the category vocabulary already used in ``skills.md``, and surfaces only
items not already present. The append helper adds a clearly-marked block under a
dedicated heading; it never rewrites or removes existing lines.
"""
from __future__ import annotations

from pathlib import Path

# Maps a skills.md-style category -> substrings that indicate membership.
# Mirrors the "Full skills inventory" headings in skills.md.
_CATEGORY_HINTS: dict[str, tuple[str, ...]] = {
    "Languages": ("python", "c++", "rust", "sql", "cuda", "shell", "bash", "java", "go", "typescript", "javascript"),
    "Deep Learning & Frameworks": ("pytorch", "tensorflow", "opencv", "hugging", "sklearn", "scikit", "numpy", "scipy", "pandas", "qiskit", "keras"),
    "Gen AI & LLM Engineering": ("rag", "langchain", "langgraph", "crewai", "llm", "faiss", "peft", "lora", "ragas", "prompt", "agent", "embedding", "vector"),
    "Computer Vision & 3D Perception": ("yolo", "fcos", "ocr", "segmentation", "detection", "swin", "bifpn", "aspp", "vision"),
    "Systems, Optimization & MLOps": ("aws", "gcp", "azure", "fastapi", "docker", "mlflow", "prefect", "git", "numba", "websocket", "kubernetes", "wasm", "poetry", "typer", "ci/cd", "kafka"),
}
_FALLBACK_CATEGORY = "Other (review & re-categorize)"


def _all_tech(profiles: list[dict]) -> list[str]:
    seen: dict[str, str] = {}  # lower -> original casing (first wins)
    for profile in profiles:
        for bucket in ("tech_stack", "keywords"):
            for item in profile.get(bucket, []) or []:
                text = str(item).strip()
                key = text.lower()
                if text and key not in seen:
                    seen[key] = text
    return list(seen.values())


def _classify(term: str) -> str:
    lowered = term.lower()
    for category, hints in _CATEGORY_HINTS.items():
        if any(hint in lowered for hint in hints):
            return category
    return _FALLBACK_CATEGORY


def aggregate_tech(profiles: list[dict]) -> dict[str, list[str]]:
    """Union all tech across profiles, bucketed into suggested categories."""
    buckets: dict[str, list[str]] = {}
    for term in _all_tech(profiles):
        buckets.setdefault(_classify(term), []).append(term)
    return {category: sorted(items, key=str.lower) for category, items in buckets.items()}


def missing_against(profiles: list[dict], skills_md_text: str) -> dict[str, list[str]]:
    """Suggested categories filtered to terms not already present in skills.md."""
    present = skills_md_text.lower()
    result: dict[str, list[str]] = {}
    for category, items in aggregate_tech(profiles).items():
        fresh = [item for item in items if item.lower() not in present]
        if fresh:
            result[category] = fresh
    return result


def suggestions_markdown(missing: dict[str, list[str]]) -> str:
    if not missing:
        return "No new skills found — your imported profiles are already covered by `skills.md`."
    lines = ["Suggested additions (review before appending — nothing is added automatically):", ""]
    for category, items in missing.items():
        lines.append(f"- **{category}:** {', '.join(items)}")
    return "\n".join(lines)


def append_missing(skills_path: str | Path, missing: dict[str, list[str]]) -> int:
    """Append only the missing items under a dedicated heading. Returns count added.

    Purely additive: existing content is left byte-for-byte intact; suggestions
    are written under an '## Imported Skills (suggested additions)' section.
    """
    if not missing:
        return 0
    path = Path(skills_path)
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    added = 0
    block = ["", "## Imported Skills (suggested additions)", ""]
    for category, items in missing.items():
        block.append(f"* **{category}:** {', '.join(items)}")
        added += len(items)
    text = existing.rstrip("\n") + "\n" + "\n".join(block) + "\n"
    path.write_text(text, encoding="utf-8")
    return added
