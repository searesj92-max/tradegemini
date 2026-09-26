"""MCP verify: rsi-t200b best SL/TP 1.8/1.5 on 8 batch3 passers — ~8 credits.

Baseline comparison comes from batch3 report (SL 2.5 / TP 1.6, tv_jul26).
Window: 2025-01-01 → 2026-09-01 · TF 4h · no trailing.
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"C:\Users\seares\Desktop\botrade")
sys.path.insert(0, str(ROOT / "scripts"))

from mcp_client import McpError, TraderDevClient, load_key  # noqa: E402
from run_discovery import extract_kpis, get_curve, status_of  # noqa: E402
from run_batch3 import HEADER, _verdict_desk, rsi_trend  # noqa: E402

FROM = "2025-01-01"
TO = "2026-09-01"
PAIRS = ["ETHUSDT", "AVAXUSDT", "ARBUSDT", "OPUSDT", "ATOMUSDT", "INJUSDT", "XRPUSDT", "SOLUSDT"]
TF = "4h"
SL_TP = (1.8, 1.5)
BASELINE_SL_TP = (2.5, 1.6)


def pine_best() -> str:
    return rsi_trend(14, 35, 65, 200, SL_TP[0], SL_TP[1]).replace(
        "RSI-Trend 14/35/65/E200",
        f"RSI-Trend 14/35/65/E200 SL{SL_TP[0]} TP{SL_TP[1]}",
    )


def pair_pass(k: dict) -> bool:
    pf = k.get("profit_factor")
    dd = k.get("max_drawdown_pct")
    n = k.get("trades") or 0
    net = k.get("net_profit_pct") or 0
    return pf is not None and pf >= 1.3 and (dd is None or dd <= 30) and n >= 40 and net > 0


def main() -> int:
    key = load_key()
    client = TraderDevClient(key)
    credits_before = None
    try:
        credits_before = client.call("get_credits", {})
    except Exception as e:
        print("get_credits before failed:", e)
    print("credits_before", credits_before)

    pine = pine_best()
    pine_path = ROOT / "data" / "pine" / f"b3-rsi-t200b-sl{SL_TP[0]}-tp{SL_TP[1]}.pine"
    pine_path.write_text(pine, encoding="utf-8")

    rows = []
    errors = 0
    for i, sym in enumerate(PAIRS, 1):
        name = f"rsi-t200b {SL_TP[0]}/{SL_TP[1]} · {sym} · {TF}"
        try:
            payload = client.call(
                "quick_backtest",
                {
                    "pineSource": pine,
                    "symbol": sym,
                    "timeframe": TF,
                    "from": FROM,
                    "to": TO,
                    "name": name,
                    "notes": "mcp-verify-sltp rsi-t200b",
                },
            )
            if isinstance(payload, str):
                payload = TraderDevClient._loads_lenient(payload)
            if not isinstance(payload, dict):
                print(f"[{i}/{len(PAIRS)}] parse fail {name}")
                errors += 1
                continue
            k = extract_kpis(payload)
            row = {
                "id": f"verify-rsi-t200b-{SL_TP[0]}-{SL_TP[1]}-{sym}-{TF}",
                "name": name,
                "symbol": sym,
                "timeframe": TF,
                "source": "mcp-verify-sltp",
                "family": "regime-mr",
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
                "warnings": k.get("warnings") or [],
                "last_backtest": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "pine_key": f"verify-rsi-t200b-sl{SL_TP[0]}",
                "sl": SL_TP[0],
                "tp": SL_TP[1],
                "baseline_sl": BASELINE_SL_TP[0],
                "baseline_tp": BASELINE_SL_TP[1],
            }
            row["verdict"] = _verdict_desk(row)
            row["status"] = status_of(row["verdict"])
            row["soft_pass"] = (
                (row["profit_factor"] or 0) >= 1.3
                and (row["max_drawdown_pct"] or 99) <= 30
                and (row["trades"] or 0) >= 20
                and (row["net_profit_pct"] or 0) > 0
            )
            row["strict_pass"] = pair_pass(row)
            if row.get("result_id"):
                row["curve"] = get_curve(client, row["result_id"], k.get("job_id"))
            else:
                row["curve"] = []
            rows.append(row)
            print(
                f"[{i}/{len(PAIRS)}] {sym} net={row.get('net_profit_pct')} "
                f"pf={row.get('profit_factor')} dd={row.get('max_drawdown_pct')} "
                f"wr={row.get('win_rate_pct')} n={row.get('trades')} "
                f"soft={row['soft_pass']} strict={row['strict_pass']} -> {row['verdict']}"
            )
            time.sleep(0.4)
        except McpError as e:
            errors += 1
            print(f"[{i}/{len(PAIRS)}] ERROR {sym}: {e}")
            time.sleep(1)
        except Exception as e:
            errors += 1
            print(f"[{i}/{len(PAIRS)}] FAIL {sym}: {e}")

    credits_after = None
    try:
        credits_after = client.call("get_credits", {})
    except Exception as e:
        print("get_credits after failed:", e)
    print("credits_after", credits_after)
    client.close()

    nstrict = sum(1 for r in rows if r.get("strict_pass"))
    nsoft = sum(1 for r in rows if r.get("soft_pass"))
    mpf = sum(r["profit_factor"] for r in rows if r.get("profit_factor") is not None) / len(rows) if rows else 0
    mdd = max((r["max_drawdown_pct"] or 0) for r in rows) if rows else 0
    mwr = sum(r["win_rate_pct"] for r in rows if r.get("win_rate_pct") is not None) / len(rows) if rows else 0

    ts = datetime.now().strftime("%Y-%m-%d-%H%M")
    out = {
        "updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "strategy": "rsi-t200b",
        "change": "SL/TP 1.8/1.5 (from local sweep best) verified on tv_jul26",
        "pairs": PAIRS,
        "timeframe": TF,
        "sl_tp": list(SL_TP),
        "baseline_sl_tp": list(BASELINE_SL_TP),
        "window": {"from": FROM, "to": TO},
        "strict_pass": nstrict,
        "soft_pass": nsoft,
        "total": len(rows),
        "mean_pf": round(mpf, 3) if rows else 0,
        "max_dd": round(mdd, 2) if rows else 0,
        "mean_wr": round(mwr, 2) if rows else 0,
        "errors": errors,
        "credits_before": credits_before,
        "credits_after": credits_after,
        "rows": rows,
        "verdict": "MCP_CONFIRMED" if nsoft >= 6 else ("MCP_PARTIAL" if nsoft >= 4 else "MCP_FAIL"),
        "engine": "tv_jul26",
        "zero_real_orders": True,
    }
    jpath = ROOT / "data" / "local" / "rsi-t200b-mcp-verify.json"
    jpath.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print("wrote", jpath)

    lines = [
        "# MCP verify: rsi-t200b SL 1.8 / TP 1.5 (tv_jul26)",
        "",
        f"**Date**: {ts} · **TF**: {TF} · **Window**: {FROM} → {TO}",
        f"**Pairs**: {' '.join(PAIRS)} · **errors**: {errors}",
        f"**Verdict**: {out['verdict']} · soft {nsoft}/{len(rows)} · strict {nstrict}/{len(rows)}",
        f"**meanPF**: {mpf:.3f} · **maxDD%**: {mdd:.1f} · **meanWR%**: {mwr:.1f}",
        f"**Credits**: {credits_before} → {credits_after}",
        "",
        "| Pair | Net% | PF | DD% | WR% | Trades | Soft | Strict | Verdict |",
        "|---|---:|---:|---:|---:|---:|---|---|---|",
    ]
    for r in sorted(rows, key=lambda x: -(x.get("profit_factor") or 0)):
        lines.append(
            f"| {r['symbol']} | {r.get('net_profit_pct')} | {r.get('profit_factor')} | "
            f"{r.get('max_drawdown_pct')} | {r.get('win_rate_pct')} | {r.get('trades')} | "
            f"{'Y' if r.get('soft_pass') else 'N'} | {'Y' if r.get('strict_pass') else 'N'} | {r['verdict']} |"
        )
    lines += [
        "",
        "## Notes",
        "",
        "- Same entries as batch3 baseline (RSI 14/35/65 · EMA200); only SL/TP changed 2.5/1.6 → 1.8/1.5.",
        "- No trailing, commission 0 (mcprule), engine tv_jul26.",
        "- Soft gate: PF≥1.3 · DD≤30 · N≥20 · net>0. Strict adds N≥40.",
        "- No real orders. Human approval required before any live step.",
        "",
        "**Next**: Gertrude re-score vs parked baseline; cross-TF 2h still weak locally (3/8).",
    ]
    rep = ROOT / "data" / "reports" / f"{ts}-optimizer-rsi-t200b-mcp-verify.md"
    rep.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("wrote", rep)
    print(f"verdict={out['verdict']} soft={nsoft} strict={nstrict}")
    return 0 if rows else 1


if __name__ == "__main__":
    raise SystemExit(main())
