import json, sys, re

data_path = r"C:\Users\seares\Desktop\botrade\dashboard\data.json"
with open(data_path, "r", encoding="utf-8") as f:
    data = json.load(f)

strategies = data.get("strategies", [])

# Remove existing entries for this cycle family
to_remove_ids = {
    "vee-btc-1h", "vee-eth-1h", "vee-sol-1h", "vee-xrp-1h", "vee-bnb-1h",
    "vee-btc-1h-lo", "vee-eth-1h-lo", "vee-sol-1h-lo", "vee-xrp-1h-lo", "vee-bnb-1h-lo",
}
strategies = [s for s in strategies if s.get("id") not in to_remove_ids]

new_rows = [
    {
        "id": "vee-btc-1h",
        "name": "VEE-v3 — Pure Breakout Continuation",
        "symbol": "BTCUSDT",
        "timeframe": "1h",
        "source": "trader-dev-mcp",
        "family": "vee-v3",
        "agent": "researcher",
        "net_profit_pct": -9.73,
        "profit_factor": 0.75,
        "max_drawdown_pct": 10.79,
        "win_rate_pct": 30.77,
        "trades": 104,
        "long_trades": 49,
        "short_trades": 55,
        "long_winning": 24,
        "short_winning": 8,
        "long_net_profit": 400.93,
        "short_net_profit": -1374.03,
        "avg_trade": -9.36,
        "result_id": "01M3902ME75KN3YY2GMTQTBTAT",
        "view_url": "https://mcp-api.trader.dev/backtest/01M3902ME75KN3YY2GMTQTBTAT",
        "pine_key": "qm_vee_v3",
        "verdict": "Watchlist",
        "status": "watchlist",
        "last_backtest": "2026-09-24",
        "notes": "cycle 1 · PF 0.75 · DD 10.8% · WR 30.8% · longs +, shorts -"
    },
    {
        "id": "vee-eth-1h",
        "name": "VEE-v3 — Pure Breakout Continuation",
        "symbol": "ETHUSDT",
        "timeframe": "1h",
        "source": "trader-dev-mcp",
        "family": "vee-v3",
        "agent": "researcher",
        "net_profit_pct": 6.16,
        "profit_factor": 1.16,
        "max_drawdown_pct": 5.67,
        "win_rate_pct": 35.79,
        "trades": 95,
        "long_trades": 36,
        "short_trades": 59,
        "long_winning": 22,
        "short_winning": 12,
        "long_net_profit": 1236.86,
        "short_net_profit": -621.21,
        "avg_trade": 6.48,
        "result_id": "01M38ZZ0DGXS76H4709WV9TS22",
        "view_url": "https://mcp-api.trader.dev/backtest/01M38ZZ0DGXS76H4709WV9TS22",
        "pine_key": "qm_vee_v3",
        "verdict": "Watchlist",
        "status": "watchlist",
        "last_backtest": "2026-09-24",
        "notes": "cycle 1 · PF 1.16 · DD 5.7% · WR 35.8% · longs +1237, shorts -621"
    },
    {
        "id": "vee-sol-1h",
        "name": "VEE-v3 — Pure Breakout Continuation",
        "symbol": "SOLUSDT",
        "timeframe": "1h",
        "source": "trader-dev-mcp",
        "family": "vee-v3",
        "agent": "researcher",
        "net_profit_pct": 14.51,
        "profit_factor": 1.30,
        "max_drawdown_pct": 16.79,
        "win_rate_pct": 31.97,
        "trades": 122,
        "long_trades": 51,
        "short_trades": 71,
        "long_winning": 27,
        "short_winning": 12,
        "long_net_profit": 1746.51,
        "short_net_profit": -295.10,
        "avg_trade": 11.90,
        "result_id": "01M38ZZFF3249S523053BSZBJD",
        "view_url": "https://mcp-api.trader.dev/backtest/01M38ZZFF3249S523053BSZBJD",
        "pine_key": "qm_vee_v3",
        "verdict": "Watchlist",
        "status": "watchlist",
        "last_backtest": "2026-09-24",
        "notes": "cycle 1 · PF 1.30 · DD 16.8% · WR 32.0% · longs +1747, shorts -295"
    },
    {
        "id": "vee-xrp-1h",
        "name": "VEE-v3 — Pure Breakout Continuation",
        "symbol": "XRPUSDT",
        "timeframe": "1h",
        "source": "trader-dev-mcp",
        "family": "vee-v3",
        "agent": "researcher",
        "net_profit_pct": -1.65,
        "profit_factor": 0.97,
        "max_drawdown_pct": 16.78,
        "win_rate_pct": 28.68,
        "trades": 129,
        "long_trades": 46,
        "short_trades": 83,
        "long_winning": 20,
        "short_winning": 17,
        "long_net_profit": -155.57,
        "short_net_profit": -9.30,
        "avg_trade": -1.28,
        "result_id": "01M3901ZT0W35V4EVYK6V0TE3V",
        "view_url": "https://mcp-api.trader.dev/backtest/01M3901ZT0W35V4EVYK6V0TE3V",
        "pine_key": "qm_vee_v3",
        "verdict": "Watchlist",
        "status": "watchlist",
        "last_backtest": "2026-09-24",
        "notes": "cycle 1 · PF 0.97 · DD 16.8% · WR 28.7% · quasi-zero, longs -156, shorts -9"
    },
    {
        "id": "vee-bnb-1h",
        "name": "VEE-v3 — Pure Breakout Continuation",
        "symbol": "BNBUSDT",
        "timeframe": "1h",
        "source": "trader-dev-mcp",
        "family": "vee-v3",
        "agent": "researcher",
        "net_profit_pct": -5.70,
        "profit_factor": 0.85,
        "max_drawdown_pct": 10.86,
        "win_rate_pct": 31.25,
        "trades": 112,
        "long_trades": 45,
        "short_trades": 67,
        "long_winning": 21,
        "short_winning": 14,
        "long_net_profit": -165.96,
        "short_net_profit": -403.56,
        "avg_trade": -5.08,
        "result_id": "01M390268AWFQMSTWAH7VC4EYR",
        "view_url": "https://mcp-api.trader.dev/backtest/01M390268AWFQMSTWAH7VC4EYR",
        "pine_key": "qm_vee_v3",
        "verdict": "Watchlist",
        "status": "watchlist",
        "last_backtest": "2026-09-24",
        "notes": "cycle 1 · PF 0.85 · DD 10.9% · WR 31.3% · longs -166, shorts -404"
    },
]

data["strategies"] = strategies + new_rows
data["updated"] = "2026-09-24 06:02 UTC"

with open(data_path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

# Generate data.js
js_content = f"""// AUTO-GENERATED — do not edit manually
// Generated: 2026-09-24 06:02 UTC
window.MISSION_DATA = {json.dumps(data, indent=2, ensure_ascii=False)};
"""

js_path = r"C:\Users\seares\Desktop\botrade\dashboard\data.js"
with open(js_path, "w", encoding="utf-8") as f:
    f.write(js_content)

print(f"Updated data.json: {len(strategies)} existing + {len(new_rows)} new rows")
print(f"Updated data.js: written")
print(f"New rows: {[r['id'] for r in new_rows]}")
