"""Export detailed analysis data (equity+timestamps, trades, monthly, drawdown zones, sharpe)
for the Mission Control analysis overlay — 0 API credits.

Writes dashboard/analysis.js consumed by index.html (window.ANALYSIS_DATA).
Re-runs the same local backtests as top40_local.json so numbers match the cards.
"""
from __future__ import annotations

import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"C:\Users\seares\Desktop\botrade")
sys.path.insert(0, str(ROOT / "scripts"))

from local_engine import backtest, load_ohlcv  # noqa: E402

EQUITY_POINTS = 400
INITIAL = 10000.0


def downsample(points: list[list], target: int) -> list[list]:
    if len(points) <= target:
        return points
    step = len(points) / target
    out = [points[int(i * step)] for i in range(target)]
    if out[-1] != points[-1]:
        out.append(points[-1])
    return out


def monthly_returns(points: list[list]) -> dict[str, float]:
    by_month: dict[str, float] = {}
    for t, e in points:
        key = datetime.fromtimestamp(t / 1000, tz=timezone.utc).strftime("%Y-%m")
        by_month[key] = e
    months = sorted(by_month)
    out: dict[str, float] = {}
    prev = INITIAL
    for m in months:
        e = by_month[m]
        if prev > 0:
            out[m] = round((e / prev - 1.0) * 100.0, 3)
        prev = e
    return out


def sharpe(points: list[list], bars_per_year: float = 2190.0) -> float | None:
    # 4h bars: 6/day * 365 = 2190
    rets = []
    for i in range(1, len(points)):
        e0, e1 = points[i - 1][1], points[i][1]
        if e0 > 0:
            rets.append(e1 / e0 - 1.0)
    if len(rets) < 10:
        return None
    n = len(rets)
    mean = sum(rets) / n
    var = sum((r - mean) ** 2 for r in rets) / max(1, n - 1)
    sd = math.sqrt(var)
    if sd == 0:
        return None
    return round(mean / sd * math.sqrt(bars_per_year), 3)


def drawdown_zones(points: list[list], top_n: int = 5) -> list[dict]:
    zones = []
    peak = points[0][1]
    peak_t = points[0][0]
    trough_e = peak
    trough_t = peak_t
    in_dd = False
    dd_start = peak_t
    for t, e in points:
        if e >= peak:
            if in_dd:
                depth = (peak - trough_e) / peak * 100.0
                if depth > 0.01:
                    zones.append({"s": dd_start, "e": t, "t": trough_t, "d": round(depth, 2)})
                in_dd = False
            peak = e
            peak_t = t
            trough_e = e
            trough_t = t
        else:
            if not in_dd:
                in_dd = True
                dd_start = peak_t
            if e < trough_e:
                trough_e = e
                trough_t = t
    if in_dd:
        depth = (peak - trough_e) / peak * 100.0
        if depth > 0.01:
            zones.append({"s": dd_start, "e": points[-1][0], "t": trough_t, "d": round(depth, 2)})
    zones.sort(key=lambda z: -z["d"])
    zones = zones[:top_n]
    for i, z in enumerate(zones, 1):
        z["i"] = i
    zones.sort(key=lambda z: z["s"])
    return zones


def main() -> int:
    top_path = ROOT / "data" / "local" / "top40_local.json"
    top = json.loads(top_path.read_text(encoding="utf-8"))
    rows_meta = {r["id"]: r for r in top["rows"]}

    bars_cache: dict[tuple[str, str], list[dict]] = {}
    out_rows: dict[str, dict] = {}
    errors = 0
    n = len(top["rows"])
    for k, meta in enumerate(top["rows"], 1):
        strat = meta["family"]
        base = meta.get("base") or meta["symbol"].replace("USDT", "")
        provider = meta.get("kline_provider") or "binance"
        symbol = meta.get("kline_symbol") or meta["symbol"]
        key = (provider, symbol)
        if key not in bars_cache:
            try:
                bars_cache[key] = load_ohlcv(provider, symbol, "4h", refresh=False)
            except Exception as e:
                print(f"load fail {provider}/{symbol}: {e}")
                errors += 1
                continue
        bars = bars_cache[key]
        if not bars or len(bars) < 250:
            continue
        try:
            r = backtest(strat, f"{base}USDT", bars, "4h")
        except Exception:
            errors += 1
            print(f"FAIL {strat}/{base}")
            continue
        # equity points with real timestamps: eq_curve[j] <-> bars[j+1]
        eq_pts = [[bars[0]["t"], INITIAL]]
        for j, e in enumerate(r.equity):
            eq_pts.append([bars[j + 1]["t"], round(e, 2)])
        eq_ds = downsample(eq_pts, EQUITY_POINTS)
        trades = [
            [
                t["entry_t"],
                t["exit_t"] or t["entry_t"],
                1 if t["side"] == "long" else 0,
                round(t["entry_price"], 6),
                round(t["exit_price"], 6) if t["exit_price"] else None,
                t["pnl_pct"],
                t["reason"],
            ]
            for t in r.trades_detail
        ]
        out_rows[meta["id"]] = {
            "eq": eq_ds,
            "monthly": monthly_returns(eq_pts),
            "sharpe": sharpe(eq_pts),
            "zones": drawdown_zones(eq_pts),
            "trades": trades,
            "engine": "local-python",
        }
        if k % 60 == 0:
            print(f"[{k}/{n}] ...")
    print(f"exported {len(out_rows)} rows, errors={errors}")

    payload = {
        "updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "window": {"from": "2025-01-01", "to": "2026-09-01"},
        "timeframe": "4h",
        "initial": INITIAL,
        "note": "engine local python · 5bps commission · 0 créditos",
        "rows": out_rows,
    }
    js = "window.ANALYSIS_DATA = " + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n"
    (ROOT / "dashboard" / "analysis.js").write_text(js, encoding="utf-8")
    size = (ROOT / "dashboard" / "analysis.js").stat().st_size / (1024 * 1024)
    print(f"wrote dashboard/analysis.js ({size:.2f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
