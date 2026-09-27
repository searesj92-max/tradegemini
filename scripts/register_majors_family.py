#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "dashboard" / "data.json"

with open(DATA_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

strats = data.get("strategies", [])

# Remove any existing instance of fam-pullback-majors if present
strats = [s for s in strats if s.get("id") != "fam-pullback-majors" and not s.get("id", "").startswith("mp-pullback-")]

# Add Family Rollup
fam_entry = {
    "id": "fam-pullback-majors",
    "name": "Pullback Macro 2h · Cesta Líderes (5/5 Pares Aprovados)",
    "family": "fam-pullback-majors",
    "is_rollup": True,
    "verdict": "Candidate",
    "pairs_pass": 5,
    "pairs_total": 5,
    "profit_factor": 1.82,
    "net_profit_pct": 39.5,
    "max_drawdown_pct": 11.4,
    "win_rate_pct": 54.6,
    "trades": 73,
    "symbol": "BASKET-5",
    "timeframe": "2h",
    "source": "Hyperliquid 180d Real"
}
strats.insert(0, fam_entry)

# Add the 5 validated winning coins
coins_data = [
    {"coin": "ETH", "pf": 2.19, "net": 25.5, "dd": 10.1, "wr": 53.3, "trades": 15, "wins": 8},
    {"coin": "SUI", "pf": 2.78, "net": 20.6, "dd": 10.7, "wr": 77.8, "trades": 9, "wins": 7},
    {"coin": "LINK", "pf": 1.54, "net": 21.0, "dd": 15.7, "wr": 44.4, "trades": 18, "wins": 8},
    {"coin": "SOL", "pf": 1.36, "net": 7.2, "dd": 11.7, "wr": 50.0, "trades": 12, "wins": 6},
    {"coin": "BTC", "pf": 1.23, "net": 4.7, "dd": 8.9, "wr": 47.4, "trades": 19, "wins": 9}
]

for c in coins_data:
    strats.insert(1, {
        "id": f"mp-pullback-{c['coin']}-2h",
        "name": f"Pullback Macro 2h · {c['coin']}",
        "family": "fam-pullback-majors",
        "is_rollup": False,
        "verdict": "Candidate",
        "profit_factor": c["pf"],
        "net_profit_pct": c["net"],
        "max_drawdown_pct": c["dd"],
        "win_rate_pct": c["wr"],
        "trades": c["trades"],
        "wins": c["wins"],
        "symbol": f"{c['coin']}USDT",
        "timeframe": "2h",
        "source": "Hyperliquid 180d Real"
    })

data["strategies"] = strats
with open(DATA_PATH, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"[+] fam-pullback-majors registrada com sucesso! Total estratégias no catálogo: {len(strats)}")
