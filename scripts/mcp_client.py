"""Minimal streamable-HTTP MCP client for Trader Dev (botrade desk)."""
from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from typing import Any

DEFAULT_URL = "https://mcp.trader.dev/mcp"


class McpError(RuntimeError):
    pass


class TraderDevClient:
    def __init__(self, key: str, base_url: str = DEFAULT_URL, timeout: float = 120.0):
        self.key = key
        self.base_url = base_url
        self.timeout = timeout
        self.session_id: str | None = None
        self._id = 0
        self._initialize()

    def _url(self) -> str:
        sep = "&" if "?" in self.base_url else "?"
        if "key=" in self.base_url:
            return self.base_url
        return f"{self.base_url}{sep}key={self.key}"

    def _post(self, payload: dict[str, Any], expect_session: bool = True) -> tuple[str, dict[str, Any] | None]:
        data = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
            "Origin": "https://mcp.trader.dev",
            "Referer": "https://mcp.trader.dev/",
        }
        if self.session_id:
            headers["mcp-session-id"] = self.session_id
        req = urllib.request.Request(self._url(), data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                sid = resp.headers.get("mcp-session-id")
                if sid:
                    self.session_id = sid
                body = resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")[:500]
            raise McpError(f"HTTP {e.code}: {detail}") from e
        except Exception as e:
            raise McpError(str(e)) from e

        payload_out = self._parse_body(body)
        return body, payload_out

    @staticmethod
    def _parse_body(body: str) -> dict[str, Any] | None:
        if not body.strip():
            return None
        # SSE multi-line
        if "data:" in body:
            chunks = []
            for line in body.splitlines():
                if line.startswith("data:"):
                    chunks.append(line[5:].strip())
            for chunk in reversed(chunks):
                if not chunk:
                    continue
                try:
                    return json.loads(chunk)
                except json.JSONDecodeError:
                    continue
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return None

    def _rpc(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        self._id += 1
        payload = {"jsonrpc": "2.0", "id": self._id, "method": method, "params": params or {}}
        _, parsed = self._post(payload)
        if not parsed:
            raise McpError(f"empty response for {method}")
        if "error" in parsed:
            raise McpError(f"{method}: {parsed['error']}")
        return parsed.get("result", {})

    def _notify(self, method: str) -> None:
        self._post({"jsonrpc": "2.0", "method": method})

    def _initialize(self) -> None:
        self._rpc(
            "initialize",
            {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "botrade-mission-control", "version": "1.0"},
            },
        )
        self._notify("notifications/initialized")
        self.authenticate()

    def authenticate(self) -> Any:
        result = self.call("authenticate", {"key": self.key})
        self._authed = True
        return result

    def list_tools(self) -> list[dict[str, Any]]:
        return self._rpc("tools/list").get("tools", [])

    def call(self, name: str, arguments: dict[str, Any] | None = None) -> Any:
        try:
            return self._call_once(name, arguments)
        except McpError as e:
            if "no API key" in str(e) and not getattr(self, "_reauthed", False):
                self._reauthed = True
                self.authenticate()
                return self._call_once(name, arguments)
            raise

    def _call_once(self, name: str, arguments: dict[str, Any] | None = None) -> Any:
        result = self._rpc("tools/call", {"name": name, "arguments": arguments or {}})
        if result.get("isError"):
            text = self._text_content(result)
            raise McpError(f"{name}: {text}")
        text = self._text_content(result)
        if not text:
            return result
        return self._loads_lenient(text)

    @staticmethod
    def _loads_lenient(text: str) -> Any:
        text = text.strip()
        if not text:
            return text
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        # embedded JSON after prose (quick_backtest tip banner, etc.)
        for start_char, end_char in (("{", "}"), ("[", "]")):
            start = text.find(start_char)
            if start < 0:
                continue
            depth = 0
            in_str = False
            esc = False
            for i in range(start, len(text)):
                ch = text[i]
                if in_str:
                    if esc:
                        esc = False
                    elif ch == "\\":
                        esc = True
                    elif ch == '"':
                        in_str = False
                    continue
                if ch == '"':
                    in_str = True
                elif ch == start_char:
                    depth += 1
                elif ch == end_char:
                    depth -= 1
                    if depth == 0:
                        try:
                            return json.loads(text[start : i + 1])
                        except json.JSONDecodeError:
                            break
        return text

    @staticmethod
    def _text_content(result: dict[str, Any]) -> str:
        parts = []
        for c in result.get("content") or []:
            if isinstance(c, dict) and c.get("type") == "text":
                parts.append(c.get("text") or "")
        return "\n".join(parts).strip()

    def close(self) -> None:
        if not self.session_id:
            return
        try:
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
                "mcp-session-id": self.session_id,
            }
            req = urllib.request.Request(self._url(), data=b"", headers=headers, method="DELETE")
            urllib.request.urlopen(req, timeout=15).read()
        except Exception:
            pass
        self.session_id = None


def load_key(path: str | None = None) -> str:
    import os

    if path is None:
        path = os.path.expandvars(r"%LOCALAPPDATA%\hermes\.env")
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if line.startswith("TRADER_DEV_API_KEY="):
                val = line.split("=", 1)[1].strip().strip('"').strip("'")
                if val:
                    return val
    # fallback: scrape from hermes config
    cfg = os.path.expandvars(r"%LOCALAPPDATA%\hermes\config.yaml")
    if os.path.exists(cfg):
        raw = open(cfg, encoding="utf-8", errors="replace").read()
        m = re.search(r"mcp\.trader\.dev/mcp\?key=(pk_[A-Za-z0-9_-]+)", raw)
        if m:
            return m.group(1)
    raise McpError("TRADER_DEV_API_KEY not found")
