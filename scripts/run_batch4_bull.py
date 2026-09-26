"""Batch 4: bull-regime strategies for current BTC high — lower risk focus.

Gate: PF>=1.3 DD<=30 trades>=40 net>0; track long/short if available.
Save dashboard merge.
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

FROM = "2025-01-01"
TO = "2026-09-01"
SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT",
    "BNBUSDT", "AVAXUSDT", "LINKUSDT", "ADAUSDT",
    "OPUSDT", "ARBUSDT", "FILUSDT", "NEARUSDT",
]
TIMEFRAMES = ["4h"]  # screen; survivors get 1h later

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


def long_only_exits(sl_atr: float, tp_atr: float) -> str:
    return f"""
a = ta.atr(14)
slM = input.float({sl_atr}, "SL x ATR")
tpM = input.float({tp_atr}, "TP x ATR")
if strategy.position_size > 0
    avg = strategy.position_avg_price
    strategy.exit("Lx", from_entry="L", stop=avg - slM * a, limit=avg + tpM * a)
"""


# Bull pullback: buy dips in confirmed uptrend (low risk on rally)
def bull_pullback(ema_t=200, ema_f=20, rsi_buy=45, sl=1.8, tp=1.6) -> str:
    name = f"BullPB E{ema_t}/F{ema_f}/R{int(rsi_buy)}"
    return HEADER.format(name=name) + f"""
t = ta.ema(close, {ema_t})
f = ta.ema(close, {ema_f})
r = ta.rsi(close, 14)
up = t > t[20] and close > t and f > ta.ema(close, 50)
longB = up and low <= f and close >= f and r <= {rsi_buy} and close > close[1]
if longB and strategy.position_size == 0
    strategy.entry("L", strategy.long)
""" + long_only_exits(sl, tp)


# Higher-high breakout with trend confirmation, long only
def hh_breakout(n=20, ema_t=50, sl=2.0, tp=2.5) -> str:
    name = f"HH-Break n{n}/E{ema_t}"
    return HEADER.format(name=name) + f"""
hi = ta.highest(high, {n})
t = ta.ema(close, {ema_t})
longB = close > hi[1] and close > t and ta.crossover(close, hi[1])
if longB and strategy.position_size == 0
    strategy.entry("L", strategy.long)
""" + long_only_exits(sl, tp)


# RSI trend filter long-only (best family, bull side only)
def rsi_t_long(buy=40, ema_t=200, sl=2.2, tp=1.8) -> str:
    name = f"RSI-T-Long R{int(buy)}/E{ema_t}"
    return HEADER.format(name=name) + f"""
r = ta.rsi(close, 14)
t = ta.ema(close, {ema_t})
up = t > t[10] and close > t
longB = up and ta.crossover(r, {buy}.0)
if longB and strategy.position_size == 0
    strategy.entry("L", strategy.long)
""" + long_only_exits(sl, tp)


# Squeeze expansion long-only in bull
def squeeze_long(length=20, mult=1.5, look=50, sl=1.8, tp=2.2) -> str:
    name = f"SQ-Long BB{length}/{mult:g}"
    return HEADER.format(name=name) + f"""
[middle, upper, lower] = ta.bb(close, {length}, {mult})
width = (upper - lower) / middle
wMin = ta.lowest(width, {look})
compressed = width <= wMin * 1.15
t = ta.ema(close, 100)
expandUp = compressed and close > upper and close > t and close > open
if expandUp and strategy.position_size == 0
    strategy.entry("L", strategy.long)
""" + long_only_exits(sl, tp)


# EMA9/21 golden pullback long-only in uptrend
def ema_gold_pull(fast=9, slow=21, sl=1.6, tp=1.5) -> str:
    name = f"GoldPB {fast}/{slow}"
    return HEADER.format(name=name) + f"""
f = ta.ema(close, {fast})
s = ta.ema(close, {slow})
t = ta.ema(close, 200)
up = f > s and close > t
longB = up and low <= f and close >= f and ta.rsi(close, 14) < 55
if longB and strategy.position_size == 0
    strategy.entry("L", strategy.long)
""" + long_only_exits(sl, tp)


# Donchian long breakout + ADX filter (bull continuation)
def dc_long(entry=20, sl=2.2, tp=3.0) -> str:
    name = f"DC-Long n{entry}"
    return HEADER.format(name=name) + f"""
hi = ta.highest(high, {entry})
t = ta.ema(close, 100)
[diP, diM, adx] = ta.dmi(14, 14)
longB = close > hi[1] and close > t and diP > diM and adx > 18
if longB and strategy.position_size == 0
    strategy.entry("L", strategy.long)
""" + long_only_exits(sl, tp)


# Momentum pullback: z-score dip in uptrend long
def mom_dip(z=-1.2, look=20, sl=1.8, tp=1.5) -> str:
    name = f"MomDip z{z:g}"
    return HEADER.format(name=name) + f"""
ret = close - close[1]
mu = ta.sma(ret, {look})
sd = ta.stdev(ret, {look})
zz = sd > 0 ? (ret - mu) / sd : 0
t = ta.ema(close, 200)
up = t > t[20] and close > t
longB = up and ta.crossunder(zz, {z})
if longB and strategy.position_size == 0
    strategy.entry("L", strategy.long)
""" + long_only_exits(sl, tp)


LIBRARY = {
    "bull-pb": {"factory": lambda: bull_pullback(), "family": "bull-pullback"},
    "hh-brk": {"factory": lambda: hh_breakout(), "family": "bull-breakout"},
    "rsi-t-l": {"factory": lambda: rsi_t_long(), "family": "bull-rsi-trend"},
    "sq-long": {"factory": lambda: squeeze_long(), "family": "bull-squeeze"},
    "gold-pb": {"factory": lambda: ema_gold_pull(), "family": "bull-pullback"},
    "dc-long": {"factory": lambda: dc_long(), "family": "bull-breakout"},
    "mom-dip": {"factory": lambda: mom_dip(), "family": "bull-momentum"},
}


def verdict_bull(row: dict) -> str:
    pf = row.get("profit_factor")
    dd = row.get("max_drawdown_pct")
    trades = row.get("trades") or 0
    net = row.get("net_profit_pct") or 0
    wr = row.get("win_rate_pct") or 0
    if pf is None or trades < 40:
        return "Watchlist"
    if pf < 1.0 or net <= 0 or (dd is not None and dd > 40):
        return "Reject"
    safe = dd is None or dd <= 30
    if pf >= 1.3 and safe and trades >= 50 and net > 0:
        return "Candidate" if wr >= 50 else ("Incubate" if pf >= 1.4 or trades >= 80 else "Watchlist")
    if pf >= 1.2 and safe and trades >= 40 and net > 0:
        return "Watchlist"
    if pf < 0.9 or net < -15:
        return "Reject"
    return "Watchlist"


def main() -> int:
    key = load_key()
    client = TraderDevClient(key)
    print("connected", client.session_id, "bull batch", len(SYMBOLS), "symbols")
    try:
        client.call("get_pine_codegen_rules", {})
    except McpError as e:
        print("codegen", e)

    combos = [(k, m, s, tf) for k, m in LIBRARY.items() for s in SYMBOLS for tf in TIMEFRAMES]
    print("combos", len(combos))
    rows_out = []
    pine_cache = {}
    errors = 0

    for i, (sk, meta, sym, tf) in enumerate(combos, 1):
        try:
            if sk not in pine_cache:
                pine_cache[sk] = meta["factory"]()
            name = f"{sk} · {sym} · {tf}"
            payload = client.call(
                "quick_backtest",
                {
                    "pineSource": pine_cache[sk],
                    "symbol": sym,
                    "timeframe": tf,
                    "from": FROM,
                    "to": TO,
                    "name": name,
                    "notes": f"bull {sk}",
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
                "id": f"b4-{sk}-{sym}-{tf}",
                "name": name,
                "symbol": sym,
                "timeframe": tf,
                "source": "discovery-bull",
                "family": meta["family"],
                "agent": "researcher",
                "net_profit_pct": k.get("net_profit_pct"),
                "profit_factor": k.get("profit_factor"),
                "max_drawdown_pct": k.get("max_drawdown_pct"),
                "win_rate_pct": k.get("win_rate_pct"),
                "trades": k.get("trades"),
                "sharpe": k.get("sharpe"),
                "avg_trade": k.get("avg_trade"),
                "long_trades": k.get("long_trades"),
                "short_trades": k.get("short_trades"),
                "result_id": k.get("result_id"),
                "view_url": k.get("view_url"),
                "engine": k.get("engine"),
                "warnings": k.get("warnings") or [],
                "last_backtest": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "pine_key": f"b4-{sk}",
            }
            row["verdict"] = verdict_bull(row)
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
            print(f"[{i}/{len(combos)}] ERROR {sk}/{sym}: {e}")
            time.sleep(1)
        except Exception:
            errors += 1
            print(f"FAIL {sk}/{sym}")
            traceback.print_exc()

    pine_dir = ROOT / "data" / "pine"
    pine_dir.mkdir(parents=True, exist_ok=True)
    for k, src in pine_cache.items():
        (pine_dir / f"b4-{k}.pine").write_text(src, encoding="utf-8")

    reports = ROOT / "data" / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d-%H%M")

    by_key = defaultdict(list)
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
        "# Batch 4 — Bull Regime (Low Risk) Report",
        "",
        f"**Date**: {ts} · **Errors**: {errors} · **Symbols**: {len(SYMBOLS)} long-only designs",
        "",
        "| Strategy | pass/12 | meanPF | meanWR | bestNet |",
        "|---|---:|---:|---:|---:|",
    ]
    ranked = []
    for key in sorted(by_key):
        rs = by_key[key]
        p = pair_pass(rs)
        mpf = sum(num(x.get("profit_factor")) for x in rs) / max(len(rs), 1)
        mwr = sum(num(x.get("win_rate_pct")) for x in rs) / max(len(rs), 1)
        bn = max((num(x.get("net_profit_pct")) for x in rs), default=0)
        ranked.append((p, mpf, mwr, bn, key, rs))
        report.append(f"| {key} | {p}/{len(rs)} | {mpf:.2f} | {mwr:.1f}% | {bn:.1f}% |")

    ranked.sort(reverse=True)
    report += ["", "## Top by pairs-pass", ""]
    for p, mpf, mwr, bn, key, rs in ranked[:6]:
        report.append(f"### {key} — {p}/12")
        for t in sorted(rs, key=lambda x: num(x.get("profit_factor")), reverse=True)[:4]:
            report.append(
                f"- {t['symbol']}: net={fmt(t.get('net_profit_pct'))}% PF={fmt(t.get('profit_factor'))} "
                f"DD={fmt(t.get('max_drawdown_pct'))}% WR={fmt(t.get('win_rate_pct'))}% trades={t.get('trades')} {t['verdict']}"
            )
        report.append("")

    hist = {}
    for r in rows_out:
        hist[r["verdict"]] = hist.get(r["verdict"], 0) + 1
    report += ["## Verdicts", ""]
    for k, v in sorted(hist.items()):
        report.append(f"- {k}: {v}")
    (reports / f"{ts}-batch4-bull.md").write_text("\n".join(report) + "\n", encoding="utf-8")

    data_path = ROOT / "dashboard" / "data.json"
    try:
        existing = json.loads(data_path.read_text(encoding="utf-8"))
        old_rows = existing.get("strategies") or []
    except Exception:
        old_rows = []
    new_ids = {r["id"] for r in rows_out}
    merged = [r for r in old_rows if r.get("id") not in new_ids] + rows_out
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

    print("\n=== BULL TOP ===")
    for p, mpf, mwr, bn, key, rs in ranked[:8]:
        print(f"  {key}: {p}/12 PF={mpf:.2f} WR={mwr:.1f}% best={bn:.1f}%")

    client.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
