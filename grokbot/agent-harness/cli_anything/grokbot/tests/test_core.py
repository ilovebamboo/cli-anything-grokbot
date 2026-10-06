"""Unit tests. No Grok Bot process required."""

from pathlib import Path

import pytest

from cli_anything.grokbot.utils import grokbot_backend as backend


def test_find_app_missing(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(backend, "EXECUTABLE", tmp_path / "missing")
    with pytest.raises(backend.GrokBotNotInstalled):
        backend.find_app()


def test_url_schemes():
    info = {"CFBundleURLTypes": [{"CFBundleURLSchemes": ["grokbot", "sand"]}]}
    assert backend._url_schemes(info) == ["grokbot", "sand"]


def test_desktop_status_missing(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(backend, "STATUS_PATH", tmp_path / "nope.json")
    assert backend._desktop_status() == {}


def test_desktop_status_ignores_non_object(monkeypatch, tmp_path: Path):
    path = tmp_path / "desktop-status.json"
    path.write_text("[]")
    monkeypatch.setattr(backend, "STATUS_PATH", path)
    assert backend._desktop_status() == {}
