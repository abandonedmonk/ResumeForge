"""MCP server smoke tests. Skipped entirely when the optional `mcp` extra is absent."""
from __future__ import annotations

import pytest

pytest.importorskip("mcp")

import anyio  # noqa: E402  (only meaningful once mcp is present)

from app import mcp_server  # noqa: E402

EXPECTED_TOOLS = [
    "cold_read",
    "compile_latex",
    "compression_receipt",
    "find_github_gap",
    "roast_resume",
    "tailor_resume",
]


def test_all_tools_registered():
    server = mcp_server.build_server()
    names = sorted(tool.name for tool in anyio.run(server.list_tools))
    assert names == EXPECTED_TOOLS


def test_is_path_distinguishes_files_from_text(tmp_path):
    resume = tmp_path / "cv.tex"
    resume.write_text("x", encoding="utf-8")
    assert mcp_server._is_path(str(resume)) is True
    assert mcp_server._is_path("just some pasted resume text") is False
    assert mcp_server._is_path("line1\nline2") is False  # multi-line = content, not a path
    assert mcp_server._is_path("") is False
