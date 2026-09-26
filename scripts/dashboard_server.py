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
import time
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent.parent
DASHBOARD_DIR = ROOT / "dashboard"
sys.path.insert(0, str(ROOT / "scripts"))

from hyperliquid_executor import HyperliquidExecutor
from backtest_engine import run_backtest_pipeline

_MACRO_CACHE = {
    "last_fetched": 0,
    "data": None
}

_SYMBOLS_CACHE = {
    "last_fetched": 0,
    "symbols": []
}


def get_cached_symbols() -> list[dict]:
    now = time.time()
    if _SYMBOLS_CACHE["symbols"] and (now - _SYMBOLS_CACHE["last_fetched"] < 300):
        return _SYMBOLS_CACHE["symbols"]

    try:
        executor = HyperliquidExecutor()
        meta = executor.info.meta()
        all_mids = executor.info.all_mids()
        symbols = []
        for item in meta.get("universe", []):
            name = item["name"]
            px = float(all_mids.get(name, 0.0))
            symbols.append({
                "name": name,
                "max_leverage": item.get("maxLeverage", 10),
                "price": px
            })
        _SYMBOLS_CACHE["symbols"] = symbols
        _SYMBOLS_CACHE["last_fetched"] = now
        return symbols
    except Exception:
        fallback_names = ["SOL", "BTC", "ETH", "KAITO", "AVAX", "SUI", "DOGE", "PEPE", "NEAR", "LINK", "ARB", "OP", "RENDER", "INJ", "TIA", "WIF"]
        return [{"name": s, "max_leverage": 10, "price": 0.0} for s in fallback_names]


def get_cached_btc_macro_regime() -> dict:
    now = time.time()
    if _MACRO_CACHE["data"] and (now - _MACRO_CACHE["last_fetched"] < 90):
        return _MACRO_CACHE["data"]

    try:
        import urllib.request
        url = "https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1d&limit=250"
        req = urllib.request.Request(url, headers={"User-Agent": "Botrade/1.0"})
        with urllib.request.urlopen(req, timeout=4) as resp:
            raw = json.loads(resp.read().decode())

        closes = [float(k[4]) for k in raw]
        cur_price = closes[-1]

        # 20-day return
        ret_20d = ((cur_price - closes[-21]) / closes[-21]) * 100 if len(closes) >= 21 else 0.0

        # EMA 200
        period = min(200, len(closes))
        multiplier = 2 / (period + 1)
        ema = [sum(closes[:period]) / period]
        for p in closes[period:]:
            ema.append((p - ema[-1]) * multiplier + ema[-1])
        ema_val = ema[-1]
        above_ema = cur_price > ema_val

        # Markov 3-State Classification (0: Bull >= +5%, 1: Neutral -5% to +5%, 2: Bear <= -5%)
        states = []
        for i in range(20, len(closes)):
            r = ((closes[i] - closes[i-20]) / closes[i-20]) * 100
            if r >= 5.0:
                states.append(0)
            elif r <= -5.0:
                states.append(2)
            else:
                states.append(1)

        trans = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]
        for i in range(1, len(states)):
            trans[states[i-1]][states[i]] += 1

        probs = []
        for row in trans:
            s = sum(row)
            probs.append([round(x / s, 3) if s > 0 else 0.333 for x in row])

        cur_state = states[-1] if states else 1
        state_labels = ["BULL", "RANGE_NEUTRAL", "BEAR"]
        state_names = ["Bull Regime (Alta / Expansão)", "Range / Acumulação Neutra", "Bear Regime (Risco-Off / Queda)"]

        p_row = probs[cur_state] if cur_state < len(probs) else [0.333, 0.333, 0.333]
        p_stay = p_row[cur_state]
        p_bull = p_row[0]
        p_bear = p_row[2]

        allow_alt_longs = not (cur_state == 2 or (ret_20d <= -4.0 and not above_ema))

        res = {
            "symbol": "BTC/USDT",
            "current_price": cur_price,
            "return_20d_pct": round(ret_20d, 2),
            "ema_benchmark": round(ema_val, 2),
            "above_ema": above_ema,
            "regime_state": state_labels[cur_state],
            "regime_name": state_names[cur_state],
            "prob_stay_pct": round(p_stay * 100, 1),
            "prob_bull_pct": round(p_bull * 100, 1),
            "prob_bear_pct": round(p_bear * 100, 1),
            "allow_altcoin_longs": allow_alt_longs,
            "status_label": "🟢 AMBIENTE FAVORÁVEL" if allow_alt_longs else "🔴 DISJUNTOR MACRO ATIVADO",
            "timestamp": int(now)
        }
        _MACRO_CACHE["data"] = res
        _MACRO_CACHE["last_fetched"] = now
        return res
    except Exception as e:
        return {
            "symbol": "BTC/USDT",
            "current_price": 84000.0,
            "return_20d_pct": 4.5,
            "above_ema": True,
            "regime_state": "RANGE_NEUTRAL",
            "regime_name": "Range / Acumulação Neutra",
            "prob_stay_pct": 82.5,
            "prob_bull_pct": 11.7,
            "prob_bear_pct": 5.8,
            "allow_altcoin_longs": True,
            "status_label": "🟢 AMBIENTE FAVORÁVEL",
            "fallback": True,
            "error": str(e)
        }


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

        if path == "/api/sniper/pause":
            try:
                state_file = ROOT / "data" / "journal" / "auto_sniper_state.json"
                state_file.parent.mkdir(parents=True, exist_ok=True)
                cur_state = {}
                if state_file.exists():
                    try:
                        cur_state = json.loads(state_file.read_text(encoding="utf-8"))
                    except Exception:
                        pass
                cur_state["paused"] = True
                cur_state["updated_at"] = os.popen("date /T").read().strip() if os.name == "nt" else ""
                state_file.write_text(json.dumps(cur_state, indent=2), encoding="utf-8")

                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "ok", "paused": True, "message": "Sniper pausado com sucesso"}, ensure_ascii=False).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "error": str(e)}, ensure_ascii=False).encode("utf-8"))
            return

        if path == "/api/sniper/resume":
            try:
                state_file = ROOT / "data" / "journal" / "auto_sniper_state.json"
                state_file.parent.mkdir(parents=True, exist_ok=True)
                cur_state = {}
                if state_file.exists():
                    try:
                        cur_state = json.loads(state_file.read_text(encoding="utf-8"))
                    except Exception:
                        pass
                cur_state["paused"] = False
                state_file.write_text(json.dumps(cur_state, indent=2), encoding="utf-8")

                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "ok", "paused": False, "message": "Sniper retomado com sucesso"}, ensure_ascii=False).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "error": str(e)}, ensure_ascii=False).encode("utf-8"))
        if path == "/api/backtest/run":
            try:
                content_len = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_len).decode("utf-8") if content_len > 0 else "{}"
                data = json.loads(body)
                symbol = data.get("symbol", "SOL").upper()
                days = int(data.get("days", 720))
                timeframe = data.get("timeframe", "1d")
                strategy = data.get("strategy", "dual")
                margin = float(data.get("margin", 15.0))
                leverage = int(data.get("leverage", 10))

                res = run_backtest_pipeline(
                    symbol=symbol,
                    days=days,
                    timeframe=timeframe,
                    strategy=strategy,
                    margin_per_trade=margin,
                    leverage=leverage
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

        if parsed.path == "/api/sniper/status":
            try:
                state_file = ROOT / "data" / "journal" / "auto_sniper_state.json"
                paused = False
                data = {}
                if state_file.exists():
                    try:
                        data = json.loads(state_file.read_text(encoding="utf-8"))
                        paused = bool(data.get("paused", False))
                    except Exception:
                        pass
                
                resp_payload = {
                    "running": True,
                    "paused": paused,
                    "state": data
                }
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps(resp_payload, ensure_ascii=False).encode("utf-8"))
                return
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "error": str(e)}, ensure_ascii=False).encode("utf-8"))
                return

        if parsed.path == "/api/macro_regime":
            try:
                regime_data = get_cached_btc_macro_regime()
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps(regime_data, ensure_ascii=False).encode("utf-8"))
                return
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "error": str(e)}, ensure_ascii=False).encode("utf-8"))
                return

        if parsed.path == "/api/backtest/symbols":
            try:
                symbols = get_cached_symbols()
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps(symbols, ensure_ascii=False).encode("utf-8"))
                return
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "error": str(e)}, ensure_ascii=False).encode("utf-8"))
                return

        if parsed.path == "/api/backtest/run":
            try:
                query = parse_qs(parsed.query)
                symbol = query.get("symbol", ["SOL"])[0].upper()
                days = int(query.get("days", [720])[0])
                timeframe = query.get("timeframe", ["1d"])[0]
                strategy = query.get("strategy", ["dual"])[0]
                margin = float(query.get("margin", [15.0])[0])
                leverage = int(query.get("leverage", [10])[0])

                res = run_backtest_pipeline(
                    symbol=symbol,
                    days=days,
                    timeframe=timeframe,
                    strategy=strategy,
                    margin_per_trade=margin,
                    leverage=leverage
                )
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps(res, ensure_ascii=False).encode("utf-8"))
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
