from __future__ import annotations

from datetime import datetime
from pathlib import Path
from textwrap import shorten

from app.utils.config import ROOT_DIR, get_config


def get_logs_dir() -> Path:
    config = get_config()
    logs_dir = ROOT_DIR / config.get("log_dir", ".log")
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir


def log_llm_interaction(provider: str, system_prompt: str, user_prompt: str, response_text: str) -> None:
    config = get_config()
    if not config.get("log_prompts", False):
        return

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S_%f")
    log_path = get_logs_dir() / f"{timestamp}_{provider}.log"
    preview = shorten(response_text.replace("\n", " "), width=160, placeholder="...")
    body = "\n".join(
        [
            f"Provider: {provider}",
            f"Timestamp: {datetime.now().isoformat()}",
            "",
            "=== SYSTEM PROMPT ===",
            system_prompt,
            "",
            "=== USER PROMPT ===",
            user_prompt,
            "",
            "=== RESPONSE ===",
            response_text,
            "",
            f"=== PREVIEW ===\n{preview}",
        ]
    )
    log_path.write_text(body, encoding="utf-8")


def write_run_log(filename: str, content: str) -> Path:
    log_path = get_logs_dir() / filename
    log_path.write_text(content, encoding="utf-8")
    return log_path


def timestamped_message(level: str, message: str) -> str:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"[{timestamp}] [{level}] {message}"


def log_status(state: dict, message: str) -> None:
    entry = timestamped_message("INFO", message)
    print(entry, flush=True)
    state.setdefault("status_updates", []).append(entry)


def log_error(state: dict, message: str) -> None:
    entry = timestamped_message("ERROR", message)
    print(entry, flush=True)
    state.setdefault("errors", []).append(entry)
