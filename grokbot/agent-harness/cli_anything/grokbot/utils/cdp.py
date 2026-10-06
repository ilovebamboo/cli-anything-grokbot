"""Small loopback-only CDP transport; no browser/profile or app ownership."""
from __future__ import annotations
import json
import socket
import time
from urllib.parse import urlparse, unquote
from urllib.request import ProxyHandler, build_opener, HTTPRedirectHandler
import websocket

APP_URL = "file:///Applications/Grok Bot.app/Contents/Resources/app.asar/dist/renderer/index.html"

class ControlError(RuntimeError):
    pass

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ControlError("CDP endpoint must not redirect")

def validate_ws(url: str, port: int) -> str:
    u = urlparse(url)
    if (u.scheme != "ws" or u.hostname not in ("127.0.0.1", "localhost", "::1")
            or u.port != port or u.username or u.password or not u.path.startswith("/devtools/page/")):
        raise ControlError("Refusing a non-loopback or unexpected CDP target")
    return url

def discover(port: int = 9337) -> dict:
    if not 1024 <= port <= 65535:
        raise ControlError("CDP port must be 1024..65535")
    try:
        with build_opener(ProxyHandler({}), NoRedirect()).open(
                f"http://127.0.0.1:{port}/json/list", timeout=3) as response:
            targets = json.load(response)
    except (OSError, ValueError) as e:
        raise ControlError(f"Grok Bot CDP unavailable on 127.0.0.1:{port}. "
                           "Use 'app connect --restart' to relaunch with local debugging. "
                           "This briefly interrupts its desktop connection.") from e
    matches = [t for t in targets if t.get("type") == "page"
               and unquote(t.get("url", "")).split("?")[0] == APP_URL]
    if len(matches) != 1:
        raise ControlError(f"Expected exactly one Grok Bot main renderer, found {len(matches)}")
    target = matches[0]
    validate_ws(target["webSocketDebuggerUrl"], port)
    return target

class CDP:
    def __init__(self, port: int = 9337):
        self.target = discover(port)
        try:
            self.ws = websocket.create_connection(
                self.target["webSocketDebuggerUrl"], timeout=15,
                suppress_origin=True, http_no_proxy=["127.0.0.1", "localhost", "::1"])
        except (OSError, websocket.WebSocketException) as e:
            raise ControlError("Cannot connect to Grok Bot renderer") from e
        self.serial = 0

    def call(self, method: str, params: dict | None = None, timeout: float = 15):
        self.serial += 1
        key = self.serial
        try:
            self.ws.send(json.dumps({"id": key, "method": method, "params": params or {}}))
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                self.ws.settimeout(max(.1, deadline-time.monotonic()))
                msg = json.loads(self.ws.recv())
                if msg.get("id") != key:
                    continue
                if "error" in msg:
                    raise ControlError(f"CDP {method}: {msg['error'].get('message')}")
                return msg.get("result", {})
        except (OSError, ValueError, websocket.WebSocketException) as e:
            raise ControlError(f"CDP {method} disconnected/timed out; do not automatically retry a send") from e
        raise ControlError(f"CDP {method} timed out")

    def evaluate(self, expression: str, timeout: float = 15):
        result = self.call("Runtime.evaluate", {"expression": expression,
                            "returnByValue": True, "awaitPromise": True}, timeout=timeout)
        if result.get("exceptionDetails"):
            error = result["exceptionDetails"].get("exception", {}).get("description", "JS evaluation failed")
            raise ControlError(error.split("\n")[0])
        return result.get("result", {}).get("value")

    def close(self):
        self.ws.close()

    def __enter__(self): return self
    def __exit__(self, *_): self.close()
