"""Fork public high-WR entries → desk-compliant exits (no trail) + multi-par backtest."""
from __future__ import annotations

import json
import re
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
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT", "AVAXUSDT", "LINKUSDT", "ADAUSDT"]
TIMEFRAMES = ["4h", "1h"]

HEADER = """//@version=6
strategy("{name}",
  slippage=2,
  overlay=true,
  pyramiding=1,
  process_orders_on_close=true,
  commission_type=strategy.commission.percent,
  commission_value=0.05,
  initial_capital=10000,
  default_qty_type=strategy.percent_of_equity,
  default_qty_value=100,
  margin_long=100,
  margin_short=100)
"""

# Desk-compliant exit block: fixed SL/TP in ATR, no trailing
EXIT = """
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


def g91_notrail(sl_atr: float = 2.0, tp_atr: float = 1.2) -> str:
    """G91 momentum multi-close breakout, fixed ATR exits, no date window, no trail."""
    return HEADER.format(name="G91 no-trail ATR exits") + f"""
atr = ta.atr(14)
slM = input.float({sl_atr})
tpM = input.float({tp_atr})
mom = (close > close[3] or close > close[12] or close > close[30]) and strategy.position_size == 0
momS = (close < close[3] or close < close[12] or close < close[30]) and strategy.position_size == 0
if mom
    strategy.entry("L", strategy.long)
if momS
    strategy.entry("S", strategy.short)
a = atr
if strategy.position_size > 0
    avg = strategy.position_avg_price
    strategy.exit("Lx", from_entry="L", stop=avg - slM * a, limit=avg + tpM * a)
if strategy.position_size < 0
    avg = strategy.position_avg_price
    strategy.exit("SX", from_entry="S", stop=avg + slM * a, limit=avg - tpM * a)
"""


def g91_tight_tp(sl_atr: float = 2.5, tp_atr: float = 0.8) -> str:
    """Same entries, asymmetric R:R for higher WR (small TP, wide SL)."""
    return HEADER.format(name="G91 tight TP high-WR") + f"""
atr = ta.atr(14)
slM = input.float({sl_atr})
tpM = input.float({tp_atr})
mom = (close > close[3] or close > close[12] or close > close[30]) and strategy.position_size == 0
momS = (close < close[3] or close < close[12] or close < close[30]) and strategy.position_size == 0
if mom
    strategy.entry("L", strategy.long)
if momS
    strategy.entry("S", strategy.short)
a = atr
if strategy.position_size > 0
    avg = strategy.position_avg_price
    strategy.exit("Lx", from_entry="L", stop=avg - slM * a, limit=avg + tpM * a)
if strategy.position_size < 0
    avg = strategy.position_avg_price
    strategy.exit("SX", from_entry="S", stop=avg + slM * a, limit=avg - tpM * a)
"""


def vanta_notrail(sl_atr: float = 1.5, tp_atr: float = 1.0) -> str:
    """Vanta RSI(2) mean-revert + EMA200, fixed SL/TP, no trail, commission 0.05."""
    return HEADER.format(name="Vanta RSI2 no-trail") + f"""
rsiLen = input.int(2)
rsiOB = input.float(90.0)
rsiOS = input.float(10.0)
emaLen = input.int(200)
atrLen = input.int(14)
slM = input.float({sl_atr})
tpM = input.float({tp_atr})
r = ta.rsi(close, rsiLen)
ema = ta.ema(close, emaLen)
a = ta.atr(atrLen)
longCondition = r < rsiOS and close > ema
shortCondition = r > rsiOB and close < ema
if longCondition
    strategy.entry("L", strategy.long)
if shortCondition
    strategy.entry("S", strategy.short)
if strategy.position_size > 0
    avg = strategy.position_avg_price
    strategy.exit("Lx", from_entry="L", stop=avg - slM * a, limit=avg + tpM * a)
if strategy.position_size < 0
    avg = strategy.position_avg_price
    strategy.exit("SX", from_entry="S", stop=avg + slM * a, limit=avg - tpM * a)
"""


def vanta_tight_tp(sl_atr: float = 2.2, tp_atr: float = 0.7) -> str:
    """Vanta asymmetric exits for high WR."""
    return HEADER.format(name="Vanta RSI2 tight TP") + f"""
rsiLen = input.int(2)
rsiOB = input.float(90.0)
rsiOS = input.float(10.0)
emaLen = input.int(200)
slM = input.float({sl_atr})
tpM = input.float({tp_atr})
r = ta.rsi(close, rsiLen)
ema = ta.ema(close, emaLen)
a = ta.atr(14)
longCondition = r < rsiOS and close > ema
shortCondition = r > rsiOB and close < ema
if longCondition
    strategy.entry("L", strategy.long)
if shortCondition
    strategy.entry("S", strategy.short)
if strategy.position_size > 0
    avg = strategy.position_avg_price
    strategy.exit("Lx", from_entry="L", stop=avg - slM * a, limit=avg + tpM * a)
if strategy.position_size < 0
    avg = strategy.position_avg_price
    strategy.exit("SX", from_entry="S", stop=avg + slM * a, limit=avg - tpM * a)
"""


def ltc_ema9_vwap_notrail(sl_atr: float = 2.0, tp_atr: float = 1.5) -> str:
    """LTC EMA9/VWAP cross + SMA150 + RSI filter, fixed exits."""
    return HEADER.format(name="EMA9-VWAP no-trail") + f"""
atrLength = input.int(7)
smaLen = input.int(150)
rsiLen = input.int(19)
rsiLongMax = input.int(60)
rsiShortMin = input.int(40)
slM = input.float({sl_atr})
tpM = input.float({tp_atr})
ema9 = ta.ema(close, 9)
vwap = ta.vwap(close)
sma = ta.sma(close, smaLen)
a = ta.atr(atrLength)
rsi = ta.rsi(close, rsiLen)
longCross = ta.crossover(ema9, vwap)
shortCross = ta.crossunder(ema9, vwap)
longCondition = longCross and close > sma and rsi < rsiLongMax
shortCondition = shortCross and close < sma and rsi > rsiShortMin
if longCondition
    strategy.entry("L", strategy.long)
if shortCondition
    strategy.entry("S", strategy.short)
if strategy.position_size > 0
    avg = strategy.position_avg_price
    strategy.exit("Lx", from_entry="L", stop=avg - slM * a, limit=avg + tpM * a)
if strategy.position_size < 0
    avg = strategy.position_avg_price
    strategy.exit("SX", from_entry="S", stop=avg + slM * a, limit=avg - tpM * a)
"""


def ema4_vwap_notrail(sl_atr: float = 1.8, tp_atr: float = 1.2) -> str:
    """EMA4/VWAP cross, fixed ATR exits (public BTC had NO hard SL — desk requires SL)."""
    return HEADER.format(name="EMA4-VWAP no-trail") + f"""
slM = input.float({sl_atr})
tpM = input.float({tp_atr})
ema = ta.ema(close, 4)
vwap = ta.vwap(close)
a = ta.atr(14)
longCondition = ta.crossover(ema, vwap)
shortCondition = ta.crossunder(ema, vwap)
if longCondition
    strategy.close("S")
    strategy.entry("L", strategy.long)
if shortCondition
    strategy.close("L")
    strategy.entry("S", strategy.short)
if strategy.position_size > 0
    avg = strategy.position_avg_price
    strategy.exit("Lx", from_entry="L", stop=avg - slM * a, limit=avg + tpM * a)
if strategy.position_size < 0
    avg = strategy.position_avg_price
    strategy.exit("SX", from_entry="S", stop=avg + slM * a, limit=avg - tpM * a)
"""


LIB = {
    "g91-nt": {"factory": lambda: g91_notrail(), "family": "public-fork"},
    "g91-tight": {"factory": lambda: g91_tight_tp(), "family": "public-fork"},
    "vanta-nt": {"factory": lambda: vanta_notrail(), "family": "public-fork"},
    "vanta-tight": {"factory": lambda: vanta_tight_tp(), "family": "public-fork"},
    "ltc-nt": {"factory": lambda: ltc_ema9_vwap_notrail(), "family": "public-fork"},
    "ema4-nt": {"factory": lambda: ema4_vwap_notrail(), "family": "public-fork"},
}


def main() -> int:
    key = load_key()
    client = TraderDevClient(key)
    print("connected", client.session_id)
    try:
        client.call("get_pine_codegen_rules", {})
        print("codegen rules ok")
    except McpError as e:
        print("codegen rules failed", e)

    combos = []
    for k, meta in LIB.items():
        for sym in SYMBOLS:
            for tf in TIMEFRAMES:
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
                    "notes": f"notrail {strat_key}",
                },
            )
            if isinstance(payload, str):
                payload = TraderDevClient._loads_lenient(payload)
            if not isinstance(payload, dict):
                print(f"[{i}/{len(combos)}] parse fail {name}")
                errors += 1
                continue
            k = extract_kpis(payload)
            warnings = k.get("warnings") or []
            row = {
                "id": f"nt-{strat_key}-{sym}-{tf}",
                "name": name,
                "symbol": sym,
                "timeframe": tf,
                "source": "discovery-notrail",
                "family": meta["family"],
                "agent": "optimizer",
                "net_profit_pct": k.get("net_profit_pct"),
                "profit_factor": k.get("profit_factor"),
                "max_drawdown_pct": k.get("max_drawdown_pct"),
                "win_rate_pct": k.get("win_rate_pct"),
                "trades": k.get("trades"),
                "sharpe": k.get("sharpe"),
                "result_id": k.get("result_id"),
                "view_url": k.get("view_url"),
                "engine": k.get("engine"),
                "warnings": warnings,
                "last_backtest": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "pine_key": f"nt-{strat_key}",
            }
            row["verdict"] = verdict_high_wr(row)
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
        (pine_dir / f"nt-{k}.pine").write_text(src, encoding="utf-8")

    # report
    reports = ROOT / "data" / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d-%H%M")

    by_key: dict[str, list[dict]] = defaultdict(list)
    for r in rows_out:
        key = r["id"].rsplit("-", 2)[0]
        by_key[key].append(r)

    def num(v, d=0.0):
        try:
            return float(v)
        except (TypeError, ValueError):
            return d

    def agg_pass(rs, wr_min=50):
        return sum(
            1
            for x in rs
            if (x.get("profit_factor") or 0) >= 1.3
            and (x.get("max_drawdown_pct") or 99) <= 30
            and (x.get("win_rate_pct") or 0) >= wr_min
            and (x.get("trades") or 0) >= 40
            and (x.get("net_profit_pct") or 0) > 0
        )

    report = [
        "# No-Trail Public Fork Multi-Par Report",
        "",
        f"**Date**: {ts}",
        "**Agent**: optimizer-notrail",
        f"**Combos**: {len(rows_out)}",
        f"**Errors**: {errors}",
        "",
        "## Changes vs public leaderboard",
        "",
        "- Removed all trailing stops (desk rule)",
        "- Hard SL + TP fixed in ATR",
        "- Removed G91 hard-coded date window",
        "- commission 0.05% kept",
        "",
        "## Robustness (WR>=50 gate / WR>=45 gate)",
        "",
        "| Strategy | pass WR50 | pass WR45 | Best WR | Best PF | Min DD |",
        "|---|---:|---:|---:|---:|---:|",
    ]

    for key in sorted(by_key.keys()):
        rs = by_key[key]
        best_wr = max((num(x.get("win_rate_pct")) for x in rs), default=0)
        best_pf = max((num(x.get("profit_factor")) for x in rs), default=0)
        pos = [x for x in rs if num(x.get("net_profit_pct")) > 0]
        min_dd = min((num(x.get("max_drawdown_pct"), 99) for x in pos), default=99)
        report.append(
            f"| {key} | {agg_pass(rs, 50)}/{len(rs)} | {agg_pass(rs, 45)}/{len(rs)} | "
            f"{best_wr:.1f}% | {best_pf:.2f} | {min_dd:.1f}% |"
        )

    report += [
        "",
        "## Top rows (PF>=1.2 DD<=30 trades>=40 net>0)",
        "",
        "| Strategy | Sym | TF | Net% | PF | DD% | WR% | Trades | Verdict |",
        "|---|---|---|---:|---:|---:|---:|---:|---|",
    ]
    good = [
        r
        for r in rows_out
        if (r.get("profit_factor") or 0) >= 1.2
        and (r.get("max_drawdown_pct") or 99) <= 30
        and (r.get("trades") or 0) >= 40
        and (r.get("net_profit_pct") or 0) > 0
    ]
    good.sort(key=lambda x: (num(x.get("win_rate_pct")), num(x.get("profit_factor"))), reverse=True)
    for r in good[:40]:
        report.append(
            f"| {r['name']} | {r['symbol']} | {r['timeframe']} | "
            f"{fmt(r.get('net_profit_pct'))} | {fmt(r.get('profit_factor'))} | "
            f"{fmt(r.get('max_drawdown_pct'))} | {fmt(r.get('win_rate_pct'))} | "
            f"{r.get('trades')} | {r['verdict']} |"
        )

    hist: dict[str, int] = {}
    for r in rows_out:
        hist[r["verdict"]] = hist.get(r["verdict"], 0) + 1
    report += ["", "## Verdict histogram", ""]
    for k, v in sorted(hist.items()):
        report.append(f"- {k}: {v}")
    report += [
        "",
        "## Note",
        "",
        "Public leaderboard WR 60-85% relied on trailing. This batch tests whether edge survives without trail.",
        "Engine tv_jul26. No real orders.",
    ]
    (reports / f"{ts}-notrail-fork.md").write_text("\n".join(report) + "\n", encoding="utf-8")

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

    print("\n=== TOP SAFE HIGH-WR (no-trail) ===")
    for r in good[:20]:
        print(
            f"  WR={fmt(r.get('win_rate_pct'))}% PF={fmt(r.get('profit_factor'))} "
            f"DD={fmt(r.get('max_drawdown_pct'))}% net={fmt(r.get('net_profit_pct'))}% "
            f"trades={r.get('trades')} | {r['name']} | {r['verdict']}"
        )

    client.close()
    return 0 if errors < len(combos) else 1


if __name__ == "__main__":
    sys.exit(main())
