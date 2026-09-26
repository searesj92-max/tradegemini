"""Lightweight HTTP server for Botrade Cockpit and Real-time Hyperliquid Actions.
Serves static dashboard files and provides REST endpoints for instant 1-click execution:
- POST /api/close?coin=SOL -> Closes position immediately at market
- POST /api/trade -> Pre-flight / executes standard trade ($5 @ 10x)
- GET /api/status -> Live account status
"""
from __future__ import annotations

import json
import os
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent.parent
DASHBOARD_DIR = ROOT / "dashboard"
sys.path.insert(0, str(ROOT / "scripts"))

from hyperliquid_executor import HyperliquidExecutor


class BotradeDashboardHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DASHBOARD_DIR), **kwargs)

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        if path == "/api/close":
            coin = query.get("coin", ["SOL"])[0].upper()
            try:
                executor = HyperliquidExecutor()
                res = executor.close_position(coin)
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps(res, ensure_ascii=False).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "error": str(e)}, ensure_ascii=False).encode("utf-8"))
            return

        if path == "/api/trade":
            try:
                content_len = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_len).decode("utf-8") if content_len > 0 else "{}"
                data = json.loads(body)
                coin = data.get("symbol", "SOL").upper()
                side = data.get("side", "buy").lower()
                margin = float(data.get("margin", 5.0))
                leverage = int(data.get("leverage", 10))
                sl = float(data.get("sl", 0.0))
                tp = float(data.get("tp", 0.0))
                confirm = bool(data.get("confirm", False))

                executor = HyperliquidExecutor()
                res = executor.execute_trade(
                    coin=coin,
                    side=side,
                    usdc_margin=margin,
                    leverage=leverage,
                    sl_price=sl,
                    tp_price=tp,
                    confirm=confirm
                )
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps(res, ensure_ascii=False).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "error": str(e)}, ensure_ascii=False).encode("utf-8"))
            return

        self.send_response(404)
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/status":
            try:
                executor = HyperliquidExecutor()
                st = executor.get_account_status()
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps(st, ensure_ascii=False).encode("utf-8"))
                return
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "error": str(e)}, ensure_ascii=False).encode("utf-8"))
                return

        return super().do_GET()


def main():
    port = int(os.environ.get("PORT", 8765))
    server_address = ("0.0.0.0", port)
    httpd = HTTPServer(server_address, BotradeDashboardHandler)
    print(f"[*] Botrade Cockpit Server rodando em http://localhost:{port}/ (e na rede local)")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
