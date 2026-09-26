import json, datetime

path = "C:/Users/seares/Desktop/botrade/dashboard/data.json"
with open(path, "r", encoding="utf-8") as f:
    data = json.load(f)

now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

new_rows = [
    {
        "id": "ved1-btc-1h",
        "name": "VED-1 — Displacement Reversion v1",
        "symbol": "BTCUSDT",
        "timeframe": "1h",
        "source": "trader-dev-mcp",
        "family": "ved-1",
        "agent": "researcher",
        "net_profit_pct": -46.7555,
        "profit_factor": 0.4625,
        "max_drawdown_pct": 46.9050,
        "win_rate_pct": 35.9375,
        "trades": 448,
        "long_trades": 222,
        "short_trades": 226,
        "long_winning": 84,
        "short_winning": 77,
        "long_net_profit": -1888.47,
        "short_net_profit": -2787.08,
        "avg_trade": -10.44,
        "sharpe": -4.918,
        "result_id": "01M38RAZNWXAJ0NK54TF2BP46K",
        "view_url": "https://mcp-api.trader.dev/backtest/01M38RAZNWXAJ0NK54TF2BP46K",
        "pine_key": "ved1_v1",
        "verdict": "Reject",
        "status": "rejected",
        "last_backtest": "2026-09-24",
        "notes": "cycle 1 · PF 0.46 · DD 47% · WR 36% · rejeitado"
    },
    {
        "id": "ved1-eth-1h",
        "name": "VED-1 — Displacement Reversion v1",
        "symbol": "ETHUSDT",
        "timeframe": "1h",
        "source": "trader-dev-mcp",
        "family": "ved-1",
        "agent": "researcher",
        "net_profit_pct": -59.1844,
        "profit_factor": 0.3934,
        "max_drawdown_pct": 59.3010,
        "win_rate_pct": 25.7343,
        "trades": 715,
        "long_trades": 252,
        "short_trades": 463,
        "long_winning": 92,
        "short_winning": 92,
        "long_net_profit": -2549.58,
        "short_net_profit": -3368.85,
        "avg_trade": -8.28,
        "sharpe": -5.935,
        "result_id": "01M38RFPZVJA1P9DC1HP66NKWF",
        "view_url": "https://mcp-api.trader.dev/backtest/01M38RFPZVJA1P9DC1HP66NKWF",
        "pine_key": "ved1_v1",
        "verdict": "Reject",
        "status": "rejected",
        "last_backtest": "2026-09-24",
        "notes": "cycle 1 · PF 0.39 · DD 59% · WR 26% · rejeitado"
    },
    {
        "id": "ved1-sol-1h",
        "name": "VED-1 — Displacement Reversion v1",
        "symbol": "SOLUSDT",
        "timeframe": "1h",
        "source": "trader-dev-mcp",
        "family": "ved-1",
        "agent": "researcher",
        "net_profit_pct": -49.2860,
        "profit_factor": 0.5812,
        "max_drawdown_pct": 50.0539,
        "win_rate_pct": 28.0549,
        "trades": 802,
        "long_trades": 255,
        "short_trades": 547,
        "long_winning": 111,
        "short_winning": 114,
        "long_net_profit": -1492.62,
        "short_net_profit": -3435.97,
        "avg_trade": -6.15,
        "sharpe": -3.670,
        "result_id": "01M38RGKAETRA46E4PTYVAASJD",
        "view_url": "https://mcp-api.trader.dev/backtest/01M38RGKAETRA46E4PTYVAASJD",
        "pine_key": "ved1_v1",
        "verdict": "Reject",
        "status": "rejected",
        "last_backtest": "2026-09-24",
        "notes": "cycle 1 · PF 0.58 · DD 50% · WR 28% · rejeitado"
    },
    {
        "id": "ved1-xrp-1h",
        "name": "VED-1 — Displacement Reversion v1",
        "symbol": "XRPUSDT",
        "timeframe": "1h",
        "source": "trader-dev-mcp",
        "family": "ved-1",
        "agent": "researcher",
        "net_profit_pct": -53.2647,
        "profit_factor": 0.4738,
        "max_drawdown_pct": 54.4182,
        "win_rate_pct": 26.3523,
        "trades": 721,
        "long_trades": 189,
        "short_trades": 532,
        "long_winning": 79,
        "short_winning": 111,
        "long_net_profit": -1265.61,
        "short_net_profit": -4060.86,
        "avg_trade": -7.39,
        "sharpe": -4.207,
        "result_id": "01M38RHBNGJFD8C94VHWWA2411",
        "view_url": "https://mcp-api.trader.dev/backtest/01M38RHBNGJFD8C94VHWWA2411",
        "pine_key": "ved1_v1",
        "verdict": "Reject",
        "status": "rejected",
        "last_backtest": "2026-09-24",
        "notes": "cycle 1 · PF 0.47 · DD 54% · WR 26% · rejeitado"
    }
]

# Adicionar novas linhas ao início do array strategies (após families/rollups existentes,
# mas mais legíveis se adicionarmos antes das estratégias de leaderboard detalhadas)
# Inserimos após os rollup families (índice ~22) para manter as familias no topo
strategies = data["strategies"]
# Encontrar onde começam os detalhados (com "id" que não é familia-rollup)
insert_at = 0
for i, s in enumerate(strategies):
    if s.get("source") in ("trader-dev-mcp", "local-ohlcv") and not s.get("is_rollup"):
        insert_at = i
        break
else:
    insert_at = len(strategies)

strategies[insert_at:insert_at] = new_rows

# Atualizar stats
data["stats"]["total"] += len(new_rows)
data["stats"]["detail_rows"] += len(new_rows)
data["stats"]["rejected"] += len(new_rows)
data["updated"] = now_str

with open(path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"Adicionadas {len(new_rows)} linhas ao data.json")
print(f"insert_at = {insert_at}")
print(f"stats.total agora = {data['stats']['total']}")
print(f"stats.rejected agora = {data['stats']['rejected']}")
print(f"updated = {data['updated']}")
