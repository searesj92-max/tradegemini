"""Batch 3: expand universe + refine surviving families + new math hypotheses.

Goal: more assets, more strategies, keep only desk-safe (no trail, SL+TP).
"""
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

from mcp_client import McpError, TraderDevClient, load_key  # noqa: E402
from run_discovery import extract_kpis, fmt, get_curve, status_of  # noqa: E402
from run_high_wr import verdict_high_wr  # noqa: E402

FROM = "2025-01-01"
TO = "2026-09-01"

# Expanded universe: core 8 + more liquid top-100-ish Bybit perps
SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT",
    "AVAXUSDT", "LINKUSDT", "ADAUSDT",
    "BNBUSDT", "NEARUSDT", "APTUSDT", "ARBUSDT",
    "OPUSDT", "INJUSDT", "ATOMUSDT", "FILUSDT",
]
# 4h primary screen; pass "1h" as argv to add 1h (credits)
TIMEFRAMES = ["4h"]

HEADER = """//@version=6
strategy("{name}",
  overlay=true,
  pyramiding=1,
  process_orders_on_close=true,
  commission_type=strategy.commission.percent,
  commission_value=0,
  initial_capital=10000,
  default_qty_type=strategy.percent_of_equity,
  default_qty_value=100,
  margin_long=100,
  margin_short=100)
"""


def exits(sl_atr: float, tp_atr: float) -> str:
    return f"""
a = ta.atr(14)
slM = input.float({sl_atr}, "SL x ATR")
tpM = input.float({tp_atr}, "TP x ATR")
if strategy.position_size > 0
    avg = strategy.position_avg_price
    strategy.exit("Lx", from_entry="L", stop=avg - slM * a, limit=avg + tpM * a)
if strategy.position_size < 0
    avg = strategy.position_avg_price
    strategy.exit("SX", from_entry="S", stop=avg + slM * a, limit=avg - tpM * a)
"""


# --- Surviving family: RSI mean-revert in EMA trend (4h) — param variants ---
def rsi_trend(rsi_len=14, buy=40, sell=60, ema_trend=200, sl=2.2, tp=1.4) -> str:
    name = f"RSI-Trend {rsi_len}/{int(buy)}/{int(sell)}/E{ema_trend}"
    return HEADER.format(name=name) + f"""
r = ta.rsi(close, {rsi_len})
t = ta.ema(close, {ema_trend})
buyLvl = {buy}.0
sellLvl = {sell}.0
longCond = close > t and ta.crossover(r, buyLvl)
shortCond = close < t and ta.crossunder(r, sellLvl)
if longCond
    strategy.entry("L", strategy.long)
if shortCond
    strategy.entry("S", strategy.short)
""" + exits(sl, tp)


# --- Vol-normalized displacement (quant, not retail) ---
def vol_displace(th_atr=1.8, lookback=20, sl=2.0, tp=1.6) -> str:
    name = f"VolDisplace {th_atr:g}/LB{lookback}"
    return HEADER.format(name=name) + f"""
a = ta.atr(14)
hi = ta.highest(high, {lookback})
lo = ta.lowest(low, {lookback})
rng = hi - lo
// bar range expanded vs average and closes in direction → displacement
avgR = ta.sma(math.max(high - low, a), {lookback})
body = math.abs(close - open)
displaceUp = body > th_atr * a and close > open and close >= hi - 0.33 * rng and close > ta.sma(close, 50)
displaceDn = body > th_atr * a and close < open and close <= lo + 0.33 * rng and close < ta.sma(close, 50)
if displaceUp and strategy.position_size == 0
    strategy.entry("L", strategy.long)
if displaceDn and strategy.position_size == 0
    strategy.entry("S", strategy.short)
""" + exits(sl, tp)


# --- Failed continuation: trend bar that fails next bar ---
def failed_cont(sl_atr=1.8, tp_atr=1.5, ema=50) -> str:
    name = f"FailedCont EMA{ema}"
    return HEADER.format(name=name) + f"""
e = ta.ema(close, {ema})
// strong trend candle then immediate opposite close-through of its open side
upFail = close[1] > open[1] and (close[1] - open[1]) > ta.atr(14) and close < open[1] and close > e
dnFail = close[1] < open[1] and (open[1] - close[1]) > ta.atr(14) and close > open[1] and close < e
if upFail and strategy.position_size == 0
    strategy.entry("L", strategy.long)
if dnFail and strategy.position_size == 0
    strategy.entry("S", strategy.short)
""" + exits(sl_atr, tp_atr)


# --- Range efficiency collapse then break (quant) ---
def range_efficiency(min_eff=0.55, max_eff=0.85, look=40, sl=2.0, tp=2.0) -> str:
    name = f"RangeEff {min_eff:g}-{max_eff:g}/L{look}"
    return HEADER.format(name=name) + f"""
c0 = close[{look}]
dist = math.abs(close - c0)
path = math.sum(math.abs(close - close[1]), {look})
eff = path > 0 ? dist / path : 0
a = ta.atr(14)
// efficiency high then a wide bar leaves the recent range → continuation
hi = ta.highest(high, {look})
lo = ta.lowest(low, {look})
effHi = eff > {min_eff} and eff < {max_eff}
longB = effHi and close > hi[1] and (close - open) > a and close > open
shortB = effHi and close < lo[1] and (open - close) > a and close < open
if longB and strategy.position_size == 0
    strategy.entry("L", strategy.long)
if shortB and strategy.position_size == 0
    strategy.entry("S", strategy.short)
""" + exits(sl, tp)


# --- Vol regime filter + Donchian breakout (desk style, fixed exits) ---
def donchian_regime(entry=20, exit_len=10, adx_max=40.0, sl=2.0, tp=2.5) -> str:
    name = f"DC-Regime {entry}/ADX<{int(adx_max)}"
    return HEADER.format(name=name) + f"""
hi = ta.highest(high, {entry})
lo = ta.lowest(low, {entry})
exitLow = ta.lowest(low, {exit_len})[1]
exitHigh = ta.highest(high, {exit_len})[1]
[diP, diM, adx] = ta.dmi(14, 14)
regime = adx < {adx_max}
longB = close > hi[1] and regime
shortB = close < lo[1] and regime
if longB and strategy.position_size == 0
    strategy.entry("L", strategy.long)
if shortB and strategy.position_size == 0
    strategy.entry("S", strategy.short)
// structural exit opposite Donchian + ATR hard stop/tp
if strategy.position_size > 0
    avg = strategy.position_avg_price
    a = ta.atr(14)
    st = math.max(avg - {sl} * a, exitLow)
    tp = avg + {tp} * a
    strategy.exit("Lx", from_entry="L", stop=st, limit=tp)
if strategy.position_size < 0
    avg = strategy.position_avg_price
    a = ta.atr(14)
    st = math.min(avg + {sl} * a, exitHigh)
    tp = avg - {tp} * a
    strategy.exit("SX", from_entry="S", stop=st, limit=tp)
"""


# --- EMA pullback in trend (refine best from batch1 ema20-50 on SOL/XRP) ---
def ema_pullback(fast=20, slow=50, sl=2.0, tp=1.8) -> str:
    name = f"EMAPB {fast}/{slow}"
    return HEADER.format(name=name) + f"""
f = ta.ema(close, {fast})
s = ta.ema(close, {slow})
t = ta.ema(close, 200)
up = f > s and close > t
dn = f < s and close < t
longB = up and low <= f and close >= f and close > close[1]
shortB = dn and high >= f and close <= f and close < close[1]
if longB and strategy.position_size == 0
    strategy.entry("L", strategy.long)
if shortB and strategy.position_size == 0
    strategy.entry("S", strategy.short)
""" + exits(sl, tp)


# --- BB pinch breakout ---
def bb_pinch(length=20, mult=2.0, width_pct=0.4, sl=1.8, tp=2.2) -> str:
    name = f"BBPinch {length}/{mult:g}"
    return HEADER.format(name=name) + f"""
len = {length}
m = {mult}
[middle, upper, lower] = ta.bb(close, len, m)
width = (upper - lower) / middle
wSma = ta.sma(width, 100)
pinched = width < wSma * {width_pct}
longB = pinched and ta.crossover(close, upper)
shortB = pinched and ta.crossunder(close, lower)
if longB and strategy.position_size == 0
    strategy.entry("L", strategy.long)
if shortB and strategy.position_size == 0
    strategy.entry("S", strategy.short)
""" + exits(sl, tp)


# --- Session-agnostic momentum z-score entry ---
def mom_z(z_entry=1.5, z_exit=0.0, look=20, sl=2.0, tp=1.5) -> str:
    name = f"MomZ {z_entry:g}/L{look}"
    return HEADER.format(name=name) + f"""
ret = close - close[1]
mu = ta.sma(ret, {look})
sd = ta.stdev(ret, {look})
z = sd > 0 ? (ret - mu) / sd : 0
longB = ta.crossover(z, {z_entry}) and close > ta.ema(close, 100)
shortB = ta.crossunder(z, -{z_entry}) and close < ta.ema(close, 100)
if longB and strategy.position_size == 0
    strategy.entry("L", strategy.long)
if shortB and strategy.position_size == 0
    strategy.entry("S", strategy.short)
""" + exits(sl, tp)


LIBRARY = {
    "rsi-t200": {"factory": lambda: rsi_trend(14, 40, 60, 200, 2.2, 1.4), "family": "regime-mr"},
    "rsi-t200b": {"factory": lambda: rsi_trend(14, 35, 65, 200, 2.5, 1.6), "family": "regime-mr"},
    "rsi-t100": {"factory": lambda: rsi_trend(14, 40, 60, 100, 2.0, 1.3), "family": "regime-mr"},
    "voldisp": {"factory": lambda: vol_displace(), "family": "quant-displace"},
    "failcont": {"factory": lambda: failed_cont(), "family": "quant-continuation"},
    "rangeeff": {"factory": lambda: range_efficiency(), "family": "quant-efficiency"},
    "dc-regime": {"factory": lambda: donchian_regime(), "family": "breakout-regime"},
    "emapb": {"factory": lambda: ema_pullback(), "family": "trend-pullback"},
    "bb-pinch": {"factory": lambda: bb_pinch(), "family": "vol-compression"},
    "mom-z": {"factory": lambda: mom_z(), "family": "quant-momentum"},
}


def main() -> int:
    # optional: filter keys via argv
    only = set(sys.argv[1:]) if len(sys.argv) > 1 else set()
    # optional: include 1h if "with1h" passed
    tfs = list(TIMEFRAMES)
    if "with1h" in only:
        only.discard("with1h")
        tfs = ["4h", "1h"]
    key = load_key()
    client = TraderDevClient(key)
    print("connected", client.session_id, "symbols", len(SYMBOLS), "tfs", tfs)
    try:
        client.call("get_pine_codegen_rules", {})
        print("codegen rules ok")
    except McpError as e:
        print("codegen rules failed", e)

    lib = {k: v for k, v in LIBRARY.items() if not only or k in only}
    combos = []
    for k, meta in lib.items():
        for sym in SYMBOLS:
            for tf in tfs:
                combos.append((k, meta, sym, tf))
    print("combos", len(combos))

    rows_out: list[dict] = []
    pine_cache: dict[str, str] = {}
    errors = 0

    for i, (strat_key, meta, sym, tf) in enumerate(combos, 1):
        try:
            if strat_key not in pine_cache:
                pine_cache[strat_key] = meta["factory"]()
            pine = pine_cache[strat_key]
            name = f"{strat_key} · {sym} · {tf}"
            payload = client.call(
                "quick_backtest",
                {
                    "pineSource": pine,
                    "symbol": sym,
                    "timeframe": tf,
                    "from": FROM,
                    "to": TO,
                    "name": name,
                    "notes": f"batch3 {strat_key}",
                },
            )
            if isinstance(payload, str):
                payload = TraderDevClient._loads_lenient(payload)
            if not isinstance(payload, dict):
                print(f"[{i}/{len(combos)}] parse fail {name}")
                errors += 1
                continue
            k = extract_kpis(payload)
            row = {
                "id": f"b3-{strat_key}-{sym}-{tf}",
                "name": name,
                "symbol": sym,
                "timeframe": tf,
                "source": "discovery-b3",
                "family": meta["family"],
                "agent": "researcher",
                "net_profit_pct": k.get("net_profit_pct"),
                "profit_factor": k.get("profit_factor"),
                "max_drawdown_pct": k.get("max_drawdown_pct"),
                "win_rate_pct": k.get("win_rate_pct"),
                "trades": k.get("trades"),
                "sharpe": k.get("sharpe"),
                "result_id": k.get("result_id"),
                "view_url": k.get("view_url"),
                "engine": k.get("engine"),
                "warnings": k.get("warnings") or [],
                "last_backtest": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "pine_key": f"b3-{strat_key}",
            }
            row["verdict"] = verdict_high_wr(row) if (row.get("win_rate_pct") or 0) >= 40 else _verdict_desk(row)
            # desk gate prefers multi-pair PF/DD; high-WR only if WR high
            row["verdict"] = _verdict_desk(row)
            row["status"] = status_of(row["verdict"])
            if row.get("result_id"):
                row["curve"] = get_curve(client, row["result_id"], k.get("job_id"))
            else:
                row["curve"] = []
            rows_out.append(row)
            print(
                f"[{i}/{len(combos)}] {name} net={fmt(row.get('net_profit_pct'))} "
                f"pf={fmt(row.get('profit_factor'))} dd={fmt(row.get('max_drawdown_pct'))} "
                f"wr={fmt(row.get('win_rate_pct'))} trades={row.get('trades')} -> {row['verdict']}"
            )
        except McpError as e:
            errors += 1
            print(f"[{i}/{len(combos)}] ERROR {strat_key}/{sym}/{tf}: {e}")
            time.sleep(1)
        except Exception:
            errors += 1
            print(f"[{i}/{len(combos)}] FAIL {strat_key}/{sym}/{tf}")
            traceback.print_exc()

    pine_dir = ROOT / "data" / "pine"
    pine_dir.mkdir(parents=True, exist_ok=True)
    for k, src in pine_cache.items():
        (pine_dir / f"b3-{k}.pine").write_text(src, encoding="utf-8")

    reports = ROOT / "data" / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d-%H%M")

    by_key: dict[str, list[dict]] = defaultdict(list)
    for r in rows_out:
        by_key[r["id"].rsplit("-", 2)[0]].append(r)

    def num(v, d=0.0):
        try:
            return float(v)
        except (TypeError, ValueError):
            return d

    def pair_pass(rs):
        return sum(
            1
            for x in rs
            if (x.get("profit_factor") or 0) >= 1.3
            and (x.get("max_drawdown_pct") or 99) <= 30
            and (x.get("trades") or 0) >= 40
            and (x.get("net_profit_pct") or 0) > 0
        )

    report = [
        "# Batch 3 — Expanded Universe Report",
        "",
        f"**Date**: {ts}",
        f"**Agent**: researcher-batch3",
        f"**Combos**: {len(rows_out)} · **Symbols**: {len(SYMBOLS)} · **Errors**: {errors}",
        "",
        "Desk gate (Candidate): PF≥1.3 · DD≤30% · trades≥40 · net>0 · multi-pair (≥5 of 16)",
        "High-WR bonus label when also WR≥50.",
        "",
        "| Strategy | pairs pass / 16 | mean PF | mean WR | best net |",
        "|---|---:|---:|---:|---:|",
    ]

    ranked = []
    for key in sorted(by_key.keys()):
        rs = by_key[key]
        p = pair_pass(rs)
        mean_pf = sum(num(x.get("profit_factor")) for x in rs) / max(len(rs), 1)
        mean_wr = sum(num(x.get("win_rate_pct")) for x in rs) / max(len(rs), 1)
        best_net = max((num(x.get("net_profit_pct")) for x in rs), default=0)
        ranked.append((p, mean_pf, mean_wr, best_net, key, rs))
        report.append(f"| {key} | {p}/{len(rs)} | {mean_pf:.2f} | {mean_wr:.1f}% | {best_net:.1f}% |")

    ranked.sort(reverse=True)
    report += ["", "## Ranked by pairs-pass", ""]
    for p, mean_pf, mean_wr, best_net, key, rs in ranked[:8]:
        top = sorted(rs, key=lambda x: num(x.get("profit_factor")), reverse=True)[:3]
        report.append(f"### {key} — {p}/16 pass")
        for t in top:
            report.append(
                f"- {t['symbol']} {t['timeframe']}: net={fmt(t.get('net_profit_pct'))}% "
                f"PF={fmt(t.get('profit_factor'))} DD={fmt(t.get('max_drawdown_pct'))}% "
                f"WR={fmt(t.get('win_rate_pct'))}% trades={t.get('trades')}"
            )
        report.append("")

    hist: dict[str, int] = {}
    for r in rows_out:
        hist[r["verdict"]] = hist.get(r["verdict"], 0) + 1
    report += ["## Verdict histogram", ""]
    for k, v in sorted(hist.items()):
        report.append(f"- {k}: {v}")
    report += ["", f"Symbols: {', '.join(SYMBOLS)}", "Engine tv_jul26. No real orders. No trailing."]

    (reports / f"{ts}-batch3-expanded.md").write_text("\n".join(report) + "\n", encoding="utf-8")

    # merge dashboard
    data_path = ROOT / "dashboard" / "data.json"
    try:
        existing = json.loads(data_path.read_text(encoding="utf-8"))
        old_rows = existing.get("strategies") or []
    except Exception:
        old_rows = []
    new_ids = {r["id"] for r in rows_out}
    kept = [r for r in old_rows if r.get("id") not in new_ids]
    merged = kept + rows_out
    stats = {
        "total": len(merged),
        "local": sum(1 for r in merged if str(r.get("source", "")).startswith("discovery")),
        "leaderboard": sum(1 for r in merged if r.get("source") == "leaderboard"),
        "errors": errors,
        "candidates": sum(1 for r in merged if r.get("verdict") == "Candidate"),
        "incubate": sum(1 for r in merged if r.get("verdict") == "Incubate"),
        "watchlist": sum(1 for r in merged if r.get("verdict") == "Watchlist"),
        "rejected": sum(1 for r in merged if r.get("verdict") == "Reject"),
    }
    data = {
        "updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "stats": stats,
        "strategies": merged,
        "agents": sorted({r.get("agent") or "unknown" for r in merged}),
        "families": sorted({r.get("family") or "unknown" for r in merged}),
    }
    data_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    (ROOT / "dashboard" / "data.js").write_text(
        "window.MISSION_DATA = " + json.dumps(data, ensure_ascii=False) + ";\n",
        encoding="utf-8",
    )
    print("wrote", data_path, "rows", len(merged), "stats", stats)

    print("\n=== TOP by pairs-pass ===")
    for p, mean_pf, mean_wr, best_net, key, rs in ranked[:10]:
        print(f"  {key}: pass {p}/16 meanPF={mean_pf:.2f} meanWR={mean_wr:.1f}% bestNet={best_net:.1f}%")

    client.close()
    return 0 if errors < len(combos) else 1


def _verdict_desk(row: dict) -> str:
    """Desk verdict: multi-pair oriented; WR bonus labels."""
    pf = row.get("profit_factor")
    dd = row.get("max_drawdown_pct")
    trades = row.get("trades") or 0
    net = row.get("net_profit_pct") or 0
    wr = row.get("win_rate_pct") or 0
    if pf is None or trades < 40:
        return "Watchlist"
    if pf < 1.0 or net <= 0 or (dd is not None and dd > 40):
        return "Reject"
    safe_dd = dd is None or dd <= 30
    if pf >= 1.3 and safe_dd and trades >= 50 and net > 0:
        if wr >= 50:
            return "Candidate"
        return "Incubate" if pf >= 1.4 or trades >= 80 else "Watchlist"
    if pf >= 1.2 and safe_dd and trades >= 40 and net > 0:
        return "Watchlist"
    if pf < 0.9 or net < -15:
        return "Reject"
    return "Watchlist"


if __name__ == "__main__":
    sys.exit(main())
