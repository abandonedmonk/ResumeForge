"""Unit tests for multi-key collection + round-robin rotation."""
from __future__ import annotations

from app.llm import keypool
from app.llm.keystore import clear_session_keys, set_session_keys


def test_collect_env_and_numbered(monkeypatch):
    clear_session_keys()
    monkeypatch.setenv("FOO_KEY", "primary")
    monkeypatch.setenv("FOO_KEY_1", "first")
    monkeypatch.setenv("FOO_KEY_2", "second")
    monkeypatch.delenv("FOO_KEY_3", raising=False)
    assert keypool._collect("FOO_KEY") == ["primary", "first", "second"]


def test_collect_session_key_first(monkeypatch):
    monkeypatch.setenv("FOO_KEY", "primary")
    monkeypatch.delenv("FOO_KEY_1", raising=False)
    set_session_keys({"FOO_KEY": "session"})
    try:
        assert keypool._collect("FOO_KEY") == ["session", "primary"]
    finally:
        clear_session_keys()


def test_collect_dedupes(monkeypatch):
    clear_session_keys()
    monkeypatch.setenv("FOO_KEY", "same")
    monkeypatch.setenv("FOO_KEY_1", "same")
    assert keypool._collect("FOO_KEY") == ["same"]


def test_ordered_keys_rotates(monkeypatch):
    monkeypatch.setattr(keypool, "_collect", lambda base: ["k1", "k2", "k3"])
    keypool._rotation.pop("ROT", None)
    assert keypool.ordered_keys("ROT") == ["k1", "k2", "k3"]
    assert keypool.ordered_keys("ROT") == ["k2", "k3", "k1"]
    assert keypool.ordered_keys("ROT") == ["k3", "k1", "k2"]


def test_ordered_keys_single_no_rotation(monkeypatch):
    monkeypatch.setattr(keypool, "_collect", lambda base: ["only"])
    assert keypool.ordered_keys("ONE") == ["only"]
    assert keypool.ordered_keys("ONE") == ["only"]


def test_ordered_keys_empty(monkeypatch):
    monkeypatch.setattr(keypool, "_collect", lambda base: [])
    assert keypool.ordered_keys("NONE") == []
