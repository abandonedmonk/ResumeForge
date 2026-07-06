"""Unit tests for extract_json_blob and parse_json_object."""
from __future__ import annotations

from app.utils.json_utils import extract_json_blob, parse_json_object


def test_plain_object():
    assert extract_json_blob('{"a": 1}') == '{"a": 1}'


def test_prose_wrapped():
    assert extract_json_blob('Here you go: {"a": 1} — done.') == '{"a": 1}'


def test_markdown_fenced():
    blob = extract_json_blob('```json\n{"a": 1, "b": "x"}\n```')
    assert blob == '{"a": 1, "b": "x"}'


def test_nested_object():
    assert extract_json_blob('x {"a": {"b": [1, 2]}} y') == '{"a": {"b": [1, 2]}}'


def test_garbage_returns_empty_object():
    assert extract_json_blob("no json at all") == "{}"


def test_empty_returns_empty_object():
    assert extract_json_blob("") == "{}"


def test_parse_json_object_plain():
    assert parse_json_object('{"a": 1, "b": "x"}') == {"a": 1, "b": "x"}


def test_parse_json_object_prose_wrapped():
    assert parse_json_object('Sure: {"a": [1, 2]} done') == {"a": [1, 2]}


def test_parse_json_object_garbage_returns_empty_dict():
    assert parse_json_object("no json here") == {}


def test_parse_json_object_empty_returns_empty_dict():
    assert parse_json_object("") == {}
