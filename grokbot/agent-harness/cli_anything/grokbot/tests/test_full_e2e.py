"""E2E tests against the installed Grok Bot.app. Do not skip."""

import json
import os
import shutil
import subprocess
import sys

from cli_anything.grokbot.utils.grokbot_backend import app_info, app_open, app_status


def _resolve_cli(name):
    force = os.environ.get("CLI_ANYTHING_FORCE_INSTALLED", "").strip() == "1"
    path = shutil.which(name)
    if path:
        print(f"[_resolve_cli] Using installed command: {path}")
        return [path]
    if force:
        raise RuntimeError(f"{name} not found in PATH. Install with: pip install -e .")
    print(f"[_resolve_cli] Falling back to: {sys.executable} -m cli_anything.grokbot")
    return [sys.executable, "-m", "cli_anything.grokbot"]


def test_real_app_info():
    info = app_info()
    print(f"\n  APP: {info['path']} version={info['version']}")
    assert info["bundleId"] == "com.anysphere.sand"
    assert info["version"]
    assert info["executable"].endswith("/Contents/MacOS/Grok Bot")


def test_real_app_status():
    status = app_status()
    print(f"\n  STATUS: running={status['running']} pids={status['pids']}")
    assert status["installed"] is True
    assert status["bundleId"] == "com.anysphere.sand"


def test_real_app_open():
    opened = app_open()
    print(f"\n  OPEN: {opened}")
    assert opened["running"] is True
    assert opened["pids"]
    assert opened["method"] == "open -a Grok Bot"


class TestCLISubprocess:
    CLI_BASE = _resolve_cli("cli-anything-grokbot")

    def _run(self, args, check=True):
        return subprocess.run(self.CLI_BASE + args, capture_output=True, text=True, check=check)

    def test_help(self):
        result = self._run(["--help"])
        assert result.returncode == 0
        assert "app" in result.stdout

    def test_app_info_json(self):
        result = self._run(["--json", "app", "info"])
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["bundleId"] == "com.anysphere.sand"
