"""Invoke the installed Grok Bot.app. Do not reimplement the app."""

from __future__ import annotations

import json
import plistlib
import subprocess
import time
from pathlib import Path

APP_PATH = Path("/Applications/Grok Bot.app")
INFO_PLIST = APP_PATH / "Contents" / "Info.plist"
EXECUTABLE = APP_PATH / "Contents" / "MacOS" / "Grok Bot"
STATUS_PATH = Path.home() / "Library" / "Application Support" / "Grok Bot" / "desktop-status.json"
BUNDLE_ID = "com.anysphere.sand"
INSTALL_HINT = "Install Grok Bot at /Applications/Grok Bot.app. This CLI is useless without that app."


class GrokBotNotInstalled(RuntimeError):
    """Raised when the real desktop app is missing."""


def find_app() -> Path:
    if not EXECUTABLE.is_file():
        raise GrokBotNotInstalled(INSTALL_HINT)
    return APP_PATH


def app_info() -> dict:
    app = find_app()
    with INFO_PLIST.open("rb") as handle:
        info = plistlib.load(handle)
    return {
        "installed": True,
        "path": str(app),
        "executable": str(EXECUTABLE),
        "bundleId": info.get("CFBundleIdentifier"),
        "name": info.get("CFBundleDisplayName") or info.get("CFBundleName"),
        "version": info.get("CFBundleShortVersionString"),
        "build": info.get("CFBundleVersion"),
        "urlSchemes": _url_schemes(info),
        "backend": "grok-bot-app",
    }


def app_status() -> dict:
    info = app_info()
    running = _pids()
    desktop = _desktop_status()
    return {
        **info,
        "running": bool(running),
        "pids": running,
        "signedIn": desktop.get("signedIn"),
        "statusPid": desktop.get("pid"),
        "statusVersion": desktop.get("appVersion"),
        "statusPath": str(STATUS_PATH),
    }


def app_open() -> dict:
    find_app()
    before = _pids()
    completed = subprocess.run(
        ["open", "-a", "Grok Bot"],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or "open -a Grok Bot failed")
    deadline = time.time() + 8
    pids = _pids()
    while not pids and time.time() < deadline:
        time.sleep(0.2)
        pids = _pids()
    if not pids:
        raise RuntimeError("Grok Bot did not start after open -a")
    return {
        "action": "open",
        "alreadyRunning": bool(before),
        "running": True,
        "pids": pids,
        "method": "open -a Grok Bot",
    }


def app_focus() -> dict:
    find_app()
    if not _pids():
        app_open()
    completed = subprocess.run(
        ["osascript", "-e", 'tell application "Grok Bot" to activate'],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or "activate failed")
    front = subprocess.run(
        ["osascript", "-e", 'tell application "System Events" to get name of first process whose frontmost is true'],
        check=False,
        capture_output=True,
        text=True,
    )
    front_name = front.stdout.strip()
    return {
        "action": "focus",
        "method": "osascript activate",
        "frontmost": front_name,
        "verified": front_name == "Grok Bot",
    }


def _url_schemes(info: dict) -> list[str]:
    schemes: list[str] = []
    for item in info.get("CFBundleURLTypes") or []:
        schemes.extend(item.get("CFBundleURLSchemes") or [])
    return schemes


def _pids() -> list[int]:
    completed = subprocess.run(
        ["pgrep", "-f", r"^/Applications/Grok Bot\.app/Contents/MacOS/Grok Bot($| )"],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode not in (0, 1):
        raise RuntimeError(completed.stderr.strip() or "pgrep failed")
    return [int(line) for line in completed.stdout.split() if line.strip()]


def _desktop_status() -> dict:
    if not STATUS_PATH.is_file():
        return {}
    try:
        data = json.loads(STATUS_PATH.read_text())
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, dict):
        return {}
    return {
        "signedIn": data.get("signedIn"),
        "pid": data.get("pid"),
        "appVersion": data.get("appVersion"),
    }
