#!/usr/bin/env python3
"""Update dashboard/data.json with QM-LSN-v1 backtest results."""

import json
import datetime
import os

data_json_path = "C:/Users/seares/Desktop/botrade/dashboard/data.json"

# Read current dashboard
with open(data_json_path, "r", encoding="utf-8") as f:
    dashboard = json.load(f)

# New rows for QM-LSN-v1
new_rows = [
    {
        "id": "qm-lsn-btc-1h",
        "name": "QM-LSN-v1",
        "symbol": "BTCUSDT",
        "timeframe": "1h",
        "source": "greenfield",
        "family": "lsn",
        "agent": "researcher",
        "net_profit_pct": -24.92,
        "profit_factor": 0.33,
        "max_drawdown_pct": 25.21,
        "win_rate_pct": 28.6,
        "trades": 192,
        "sharpe": -7.57,
        "result_id": "01M38M4KM36GTHB837CWMGTM4J",
        "view_url": "https://mcp-api.trader.dev/backtest/01M38M4KM36GTHB837CWMGTM4J",
        "curve": [],
        "verdict": "rejected",
        "status": "backtested",
        "last_backtest": "2026-09-24T02:32:00.000Z",
        "pine_key": "01M38M4KS4YAVKY7Y1RK836Q1G",
        "notes": "192 trades, PF 0.33, WR 28.6%. Shorts (123) lose -$2255. Longs near BE before comm. Cascade mild (1.07x). SL/TP too tight for BTC vol."
    },
    {
        "id": "qm-lsn-eth-1h",
        "name": "QM-LSN-v1",
        "symbol": "ETHUSDT",
        "timeframe": "1h",
        "source": "greenfield",
        "family": "lsn",
        "agent": "researcher",
        "net_profit_pct": -13.52,
        "profit_factor": 0.62,
        "max_drawdown_pct": 13.62,
        "win_rate_pct": 27.9,
        "trades": 244,
        "sharpe": -3.48,
        "result_id": "01M38M3ZXWK6YQ281Z0YN6MK32",
        "view_url": "https://mcp-api.trader.dev/backtest/01M38M3ZXWK6YQ281Z0YN6MK32",
        "curve": [],
        "verdict": "rejected",
        "status": "backtested",
        "last_backtest": "2026-09-24T02:32:00.000Z",
        "pine_key": "01M38M404BH6B5SR72FH2642SE",
        "notes": "244 trades, PF 0.62, WR 27.9%. Shorts (185 trades, -$1029) dominate losses. Longs (59) also negative. Cascade mild (1.55x)."
    },
    {
        "id": "qm-lsn-sol-1h",
        "name": "QM-LSN-v1",
        "symbol": "SOLUSDT",
        "timeframe": "1h",
        "source": "greenfield",
        "family": "lsn",
        "agent": "researcher",
        "net_profit_pct": -20.72,
        "profit_factor": 0.55,
        "max_drawdown_pct": 23.01,
        "win_rate_pct": 25.91,
        "trades": 274,
        "sharpe": -4.55,
        "result_id": "01M38M4WEQPEWFGTR5SSJRNVPP",
        "view_url": "https://mcp-api.trader.dev/backtest/01M38M4WEQPEWFGTR5SSJRNVPP",
        "curve": [],
        "verdict": "rejected",
        "status": "backtested",
        "last_backtest": "2026-09-24T02:32:00.000Z",
        "pine_key": "01M38M4WKD7S827K7VQWPK7ECA",
        "notes": "274 trades, PF 0.55, WR 25.9%. Shorts (199) 2.6x longs but both negative. Zero runup. Avg duration 2.1 bars - stops hit too fast."
    },
    {
        "id": "qm-lsn-xrp-1h",
        "name": "QM-LSN-v1",
        "symbol": "XRPUSDT",
        "timeframe": "1h",
        "source": "greenfield",
        "family": "lsn",
        "agent": "researcher",
        "net_profit_pct": -22.23,
        "profit_factor": 0.595,
        "max_drawdown_pct": 22.56,
        "win_rate_pct": 28.91,
        "trades": 256,
        "sharpe": -3.55,
        "result_id": "01M38M5288EEQ6R23Z7RPJDZFA",
        "view_url": "https://mcp-api.trader.dev/backtest/01M38M5288EEQ6R23Z7RPJDZFA",
        "curve": [],
        "verdict": "rejected",
        "status": "backtested",
        "last_backtest": "2026-09-24T02:32:00.000Z",
        "pine_key": "01M38M52CM2A62F326DTZ98DAR",
        "notes": "256 trades, PF 0.595, WR 28.9%. Shorts (167 trades, -$1311) dominate. Cascade mild (1.48x). Clean result, negative edge."
    },
    {
        "id": "qm-lsn-bnb-1h",
        "name": "QM-LSN-v1",
        "symbol": "BNBUSDT",
        "timeframe": "1h",
        "source": "greenfield",
        "family": "lsn",
        "agent": "researcher",
        "net_profit_pct": -21.88,
        "profit_factor": 0.28,
        "max_drawdown_pct": 22.02,
        "win_rate_pct": 22.37,
        "trades": 219,
        "sharpe": -9.11,
        "result_id": "01M38M4B6CSP4AZB9B99W1E6NZ",
        "view_url": "https://mcp-api.trader.dev/backtest/01M38M4B6CSP4AZB9B99W1E6NZ",
        "curve": [],
        "verdict": "rejected",
        "status": "backtested",
        "last_backtest": "2026-09-24T02:32:00.000Z",
        "pine_key": "01M38M4BBEJKY76DGYJQH16MNX",
        "notes": "219 trades, PF 0.28, WR 22.4%. Worst of group. Cascade warning (1.51x) but result usable. Shorts (154) lose more than longs (65)."
    }
]

# Extend strategies
dashboard["strategies"].extend(new_rows)
dashboard["stats"]["total"] = len(dashboard["strategies"])
dashboard["stats"]["detail_rows"] = len(dashboard["strategies"])
dashboard["updated"] = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M")

# Write back
with open(data_json_path, "w", encoding="utf-8") as f:
    json.dump(dashboard, f, indent=2, ensure_ascii=False)

print(f"Updated dashboard: added {len(new_rows)} rows. Total strategies: {len(dashboard['strategies'])}")
print(f"Path: {os.path.abspath(data_json_path)}")
