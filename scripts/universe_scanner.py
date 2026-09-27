#!/usr/bin/env python3
"""
Botrade Mass Universe 720d Alpha Scanner
Sweeps through the most liquid perpetual assets on Hyperliquid,
simulates quantitative strategies across historical data,
and generates an institutional Leaderboard ranking the Top Champion Coins for the Sniper.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Fix Windows console encoding
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from hyperliquid_executor import HyperliquidExecutor
from backtest_engine import run_backtest_pipeline

LEADERBOARD_FILE = ROOT / "data" / "reports" / "universe_leaderboard.json"


def scan_universe(
    limit: int = 25,
    days: int = 180,
    timeframe: str = "4h",
    strategy: str = "dual"
) -> dict:
    """Scans the top liquid universe coins, runs quantitative backtests, and ranks champions."""
    executor = HyperliquidExecutor()
    ctxs = executor.info.meta_and_asset_ctxs()

    universe = ctxs[0]["universe"]
    metas = ctxs[1]

    # Rank by 24h volume to pick the most liquid coins first
    coin_pool = []
    for i, u in enumerate(universe):
        name = u["name"]
        m = metas[i] if i < len(metas) else {}
        vol = float(m.get("dayNtlVlm", 0.0))
        coin_pool.append({
            "name": name,
            "volume_24h": vol,
            "max_leverage": u.get("maxLeverage", 10),
            "price": float(m.get("markPx", 0.0))
        })

    coin_pool.sort(key=lambda x: x["volume_24h"], reverse=True)
    selected_coins = coin_pool[:limit]

    print(f"[*] Varrendo {len(selected_coins)} ativos mais líquidos por {days} dias ({timeframe})...")

    results = []
    for idx, c in enumerate(selected_coins):
        sym = c["name"]
        try:
            bt_res = run_backtest_pipeline(
                symbol=sym,
                days=days,
                timeframe=timeframe,
                strategy=strategy,
                margin_per_trade=15.0,
                leverage=10
            )

            if bt_res.get("status") == "ok":
                s = bt_res["summary"]
                results.append({
                    "rank": 0,
                    "coin": sym,
                    "price": c["price"],
                    "volume_24h": c["volume_24h"],
                    "days_actual": bt_res.get("days_actual", days),
                    "candles_count": bt_res.get("candles_count", 0),
                    "total_trades": s["total_trades"],
                    "win_rate_pct": s["win_rate_pct"],
                    "profit_factor": s["profit_factor"],
                    "net_profit_usd": s["net_profit_usd"],
                    "net_profit_pct": s["net_profit_pct"],
                    "max_drawdown_pct": s["max_drawdown_pct"],
                    "payoff_ratio": s["payoff_ratio"],
                    "gertrude_verdict": s["gertrude_verdict"],
                    "gertrude_status": s["gertrude_status"],
                    "gertrude_badge": s["gertrude_badge"]
                })
        except Exception as e:
            print(f"[-] Erro em {sym}: {e}", file=sys.stderr)

        time.sleep(0.05)

    # Sort results: Approved first, then highest Profit Factor, then highest Net Profit
    def sort_key(item):
        status_weight = 2 if item["gertrude_status"] == "approved" else (1 if item["gertrude_status"] == "parked" else 0)
        return (status_weight, item["profit_factor"], item["net_profit_usd"])

    results.sort(key=sort_key, reverse=True)
    for i, r in enumerate(results):
        r["rank"] = i + 1

    payload = {
        "status": "ok",
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "total_scanned": len(results),
        "days": days,
        "timeframe": timeframe,
        "strategy": strategy,
        "champions": [r for r in results if r["gertrude_status"] == "approved"][:5],
        "leaderboard": results
    }

    # Save to disk
    LEADERBOARD_FILE.parent.mkdir(parents=True, exist_ok=True)
    LEADERBOARD_FILE.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    return payload


def main():
    parser = argparse.ArgumentParser(description="Botrade Mass Universe Scanner")
    parser.add_argument("--limit", type=int, default=15, help="Number of liquid coins to scan")
    parser.add_argument("--days", type=int, default=180, help="Lookback days")
    parser.add_argument("--timeframe", type=str, default="4h", choices=["1h", "2h", "4h", "1d"])
    parser.add_argument("--strategy", type=str, default="dual")
    args = parser.parse_args()

    res = scan_universe(limit=args.limit, days=args.days, timeframe=args.timeframe, strategy=args.strategy)

    print("\n" + "=" * 75)
    print(f"🏆 LEADERBOARD DE ALPHA: TOP {len(res['leaderboard'])} ATIVOS DA HYPERLIQUID ({args.days}d {args.timeframe})")
    print("=" * 75)
    print(f"{'#':<3} {'Moeda':<9} {'Trades':<8} {'Win Rate':<10} {'Fator Lucro':<14} {'Lucro Líq':<12} {'Max DD':<10} {'Veredito'}")
    print("-" * 75)
    for r in res["leaderboard"][:15]:
        pnl_str = f"{'+' if r['net_profit_usd']>=0 else ''}${r['net_profit_usd']:.2f}"
        print(f"{r['rank']:<3} {r['coin']:<9} {r['total_trades']:<8} {r['win_rate_pct']:>5.1f}%     {r['profit_factor']:>6.2f}x       {pnl_str:<12} -{r['max_drawdown_pct']:.1f}%    {r['gertrude_badge']}")
    print("=" * 75)


if __name__ == "__main__":
    main()
