"""Run living strategy families on top-40 universe LOCALLY (0 API credits)."""
from __future__ import annotations

import json
import sys
import time
import traceback
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"C:\Users\seares\Desktop\botrade")
sys.path.insert(0, str(ROOT / "scripts"))

from local_engine import STRATEGIES, backtest, desk_gate, load_ohlcv  # noqa: E402
from top_universe import merge_top40  # noqa: E402


def main() -> int:
    top = merge_top40(40)
    print(f"universe n={len(top)} strategies={len(STRATEGIES)} combos={len(top)*len(STRATEGIES)}")
    rows = []
    errors = 0
    t0 = time.time()
    n = len(top) * len(STRATEGIES)
    k = 0
    for asset in top:
        provider = asset.get("kline_provider") or "binance"
        symbol = asset.get("binance_symbol") or asset.get("bybit_symbol")
        if not symbol:
            continue
        try:
            bars = load_ohlcv(provider, symbol, "4h", refresh=False)
        except Exception as e:
            print(f"download fail {provider}/{symbol}: {e}")
            errors += 1
            continue
        if not bars:
            print(f"empty {provider}/{symbol}")
            errors += 1
            continue
        for strat in STRATEGIES:
            k += 1
            try:
                r = backtest(strat, f"{asset['base']}USDT", bars, "4h")
                v = desk_gate(r)
                row = {
                    "id": f"loc-{strat}-{asset['base']}-4h",
                    "name": f"{strat} · {asset['base']}USDT · 4h",
                    "symbol": f"{asset['base']}USDT",
                    "base": asset["base"],
                    "timeframe": "4h",
                    "source": "local-ohlcv",
                    "family": strat,
                    "agent": "local-engine",
                    "kline_provider": provider,
                    "kline_symbol": symbol,
                    "net_profit_pct": round(r.net_profit_pct, 4),
                    "profit_factor": round(r.profit_factor, 4),
                    "max_drawdown_pct": round(r.max_drawdown_pct, 4),
                    "win_rate_pct": round(r.win_rate_pct, 4),
                    "trades": r.trades,
                    "wins": r.wins,
                    "losses": r.losses,
                    "win_pct": round(r.win_rate_pct, 4),
                    "loss_pct": round(100 - r.win_rate_pct, 4) if r.trades else None,
                    "avg_trade": round(r.avg_trade_pct, 5),
                    "long_trades": r.long_trades,
                    "short_trades": r.short_trades,
                    "expectancy_pct": round(r.net_profit_pct / r.trades, 4) if r.trades else None,
                    "verdict": v,
                    "status": {
                        "Candidate": "candidate",
                        "Incubate": "incubate",
                        "Watchlist": "watchlist",
                        "Reject": "rejected",
                    }[v],
                    "last_backtest": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                    "engine": "local-python",
                    "commission_bps": 5,
                    "result_id": None,
                    "view_url": None,
                    "pine_key": {
                        "rsi-t200b": "b3-rsi-t200b",
                        "rsi-t200": "b3-rsi-t200",
                        "rsi-t100": "b3-rsi-t100",
                        "rsi-t-l": "b4-rsi-t-l",
                        "squeeze": "hw-squeeze",
                        "gold-pb": "b4-gold-pb",
                        "mom-dip": "b4-mom-dip",
                        "ema20-50": "disc-ema20-50",
                        "ema9-21": "disc-ema9-21",
                        "bull-pb": "b4-bull-pb",
                        "hh-brk": "b4-hh-brk",
                        "dc-long": "b4-dc-long",
                    }.get(strat),
                    "curve": [{"t": i, "e": e} for i, e in enumerate(r.equity[:: max(1, len(r.equity) // 40)])],
                }
                rows.append(row)
                print(
                    f"[{k}/{n}] {row['name']} net={row['net_profit_pct']:.2f}% "
                    f"pf={row['profit_factor']:.2f} dd={row['max_drawdown_pct']:.2f} "
                    f"wr={row['win_rate_pct']:.1f}% tr={row['trades']} -> {v}"
                )
            except Exception:
                errors += 1
                print(f"FAIL {strat}/{asset['base']}")
                traceback.print_exc()
    dt = time.time() - t0
    print(f"done rows={len(rows)} errors={errors} sec={dt:.1f}")

    # family robustness
    by = defaultdict(list)
    for r in rows:
        by[r["family"]].append(r)

    def npass(rs):
        return sum(
            1
            for x in rs
            if (x["profit_factor"] or 0) >= 1.3
            and (x["max_drawdown_pct"] or 99) <= 30
            and (x["trades"] or 0) >= 40
            and (x["net_profit_pct"] or 0) > 0
        )

    print("\n=== LOCAL TOP40 FAMILY (pairs pass / 40) ===")
    fam_rows = []
    for fam, rs in sorted(by.items(), key=lambda kv: -npass(kv[1])):
        p = npass(rs)
        mpf = sum(x["profit_factor"] or 0 for x in rs) / len(rs)
        mwr = sum(x["win_rate_pct"] or 0 for x in rs) / len(rs)
        bn = max(x["net_profit_pct"] or 0 for x in rs)
        print(f"  {fam:12s} {p:2d}/40  meanPF={mpf:.2f} meanWR={mwr:.1f}% bestNet={bn:.1f}%")
        fam_rows.append({"family": fam, "pairs_pass": p, "pairs_total": len(rs),
                         "mean_pf": round(mpf, 3), "mean_wr": round(mwr, 2),
                         "best_net": round(bn, 2)})

    hist = defaultdict(int)
    for r in rows:
        hist[r["verdict"]] += 1
    print("verdicts", dict(hist))

    out = {
        "updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "local-ohlcv-binance-bybit",
        "window": {"from": "2025-01-01", "to": "2026-09-01"},
        "universe": [a["base"] for a in top],
        "stats": {
            "total": len(rows),
            "errors": errors,
            "candidates": hist.get("Candidate", 0),
            "incubate": hist.get("Incubate", 0),
            "watchlist": hist.get("Watchlist", 0),
            "rejected": hist.get("Reject", 0),
        },
        "families": fam_rows,
        "rows": rows,
    }
    path = ROOT / "data" / "local" / "top40_local.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print("wrote", path)

    # report markdown
    ts = datetime.now().strftime("%Y-%m-%d-%H%M")
    lines = [
        "# Local Top-40 Backtest Report (0 API credits)",
        "",
        f"**Date**: {ts} · **Engine**: local Python · **Window**: 2025-01-01 → 2026-09-01 · **TF**: 4h",
        f"**Universe**: top 40 Bybit/Binance USDT perps by 24h volume · **combos**: {len(rows)} · **errors**: {errors}",
        f"**Commission**: 5 bps/side local (Trader Dev mcprule uses 0 — local is stricter)",
        "",
        "## Family robustness (pairs pass gate / 40)",
        "",
        "| Strategy | pass/40 | meanPF | meanWR | bestNet |",
        "|---|---:|---:|---:|---:|",
    ]
    for fr in fam_rows:
        lines.append(
            f"| {fr['family']} | {fr['pairs_pass']}/40 | {fr['mean_pf']} | {fr['mean_wr']}% | {fr['best_net']}% |"
        )
    lines += ["", "## Top detail rows (gate pass, sorted PF)", "",
              "| Strategy | Sym | Net% | PF | DD% | WR% | W | L | Trades | Verdict |",
              "|---|---|---:|---:|---:|---:|---:|---:|---:|---|"]
    top_rows = sorted(
        [r for r in rows if (r["profit_factor"] or 0) >= 1.3 and (r["trades"] or 0) >= 40 and (r["net_profit_pct"] or 0) > 0],
        key=lambda r: -(r["profit_factor"] or 0),
    )[:40]
    for r in top_rows:
        lines.append(
            f"| {r['family']} | {r['symbol']} | {r['net_profit_pct']:.2f} | {r['profit_factor']:.2f} | "
            f"{r['max_drawdown_pct']:.2f} | {r['win_rate_pct']:.1f} | {r['wins']} | {r['losses']} | "
            f"{r['trades']} | {r['verdict']} |"
        )
    lines += ["", "## Verdicts", ""]
    for k2, v in sorted(hist.items()):
        lines.append(f"- {k2}: {v}")
    lines += [
        "",
        "## Note",
        "",
        "Local engine approximates Pine `process_orders_on_close` + ATR SL/TP.",
        "Survivors should be re-checked on Trader Dev (`quick_backtest`) before Gertrude acts.",
        "Data: Binance/Bybit public klines (free). No real orders.",
    ]
    rep = ROOT / "data" / "reports" / f"{ts}-local-top40.md"
    rep.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("wrote", rep)
    return 0


if __name__ == "__main__":
    sys.exit(main())
