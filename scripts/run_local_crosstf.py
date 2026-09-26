"""Cross-TF check: rsi-t200b on 1h/2h with best SL/TP — 0 API credits.

Follow-up to data/local/rsi-t200b-sltp-sweep.json (best SL 1.8 / TP 1.5).
Pairs: ETH AVAX ARB OP ATOM INJ XRP SOL (batch3 8/16 passers).
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(r"C:\Users\seares\Desktop\botrade")
sys.path.insert(0, str(ROOT / "scripts"))

from local_engine import backtest, desk_gate, load_ohlcv  # noqa: E402

PAIRS = ["ETH", "AVAX", "ARB", "OP", "ATOM", "INJ", "XRP", "SOL"]
TFS = ["1h", "2h", "4h"]
BASELINE = (2.5, 1.6)
BEST = (1.8, 1.5)
CELLS = [BASELINE, BEST]


def soft_pass(r) -> bool:
    return (
        (r.profit_factor or 0) >= 1.3
        and (r.max_drawdown_pct or 99) <= 30
        and (r.trades or 0) >= 20
        and (r.net_profit_pct or 0) > 0
    )


def strict_pass(r) -> bool:
    return (
        (r.profit_factor or 0) >= 1.3
        and (r.max_drawdown_pct or 99) <= 30
        and (r.trades or 0) >= 40
        and (r.net_profit_pct or 0) > 0
    )


def load_bars(base: str, tf: str):
    for p, s in (("binance", f"{base}USDT"), ("bybit", f"{base}USDT")):
        try:
            bars = load_ohlcv(p, s, tf, refresh=False)
            if bars:
                return p, s, bars
        except Exception as e:
            print(f"  fail {p}/{s} {tf}: {e}")
    return None, None, None


def main() -> int:
    errors = 0
    data = {}  # (sl, tp, tf) -> rows
    for sl, tp in CELLS:
        for tf in TFS:
            rows = []
            for base in PAIRS:
                provider, symbol, bars = load_bars(base, tf)
                if not bars:
                    print(f"SKIP {base} {tf}")
                    errors += 1
                    continue
                try:
                    r = backtest("rsi-t200b", f"{base}USDT", bars, tf, sl_tp=(sl, tp))
                    rows.append({
                        "base": base,
                        "provider": provider,
                        "net": round(r.net_profit_pct, 4),
                        "pf": round(min(r.profit_factor, 999), 4),
                        "dd": round(r.max_drawdown_pct, 4),
                        "wr": round(r.win_rate_pct, 4),
                        "trades": r.trades,
                        "soft_pass": soft_pass(r),
                        "strict_pass": strict_pass(r),
                        "gate": desk_gate(r),
                    })
                except Exception:
                    errors += 1
                    print(f"FAIL {base} {tf} sl={sl} tp={tp}")
            data[(sl, tp, tf)] = rows
            nsoft = sum(1 for x in rows if x["soft_pass"])
            nstrict = sum(1 for x in rows if x["strict_pass"])
            mpf = sum(x["pf"] for x in rows) / len(rows) if rows else 0
            mdd = max((x["dd"] for x in rows), default=0)
            mwr = sum(x["wr"] for x in rows) / len(rows) if rows else 0
            mn = sum(x["trades"] for x in rows) / len(rows) if rows else 0
            print(
                f"SL={sl} TP={tp} {tf}: soft={nsoft}/{len(rows)} strict={nstrict}/{len(rows)} "
                f"meanPF={mpf:.3f} maxDD={mdd:.1f}% meanWR={mwr:.1f}% meanN={mn:.1f}"
            )

    def cell_summary(rows):
        return {
            "soft_pass": sum(1 for x in rows if x["soft_pass"]),
            "strict_pass": sum(1 for x in rows if x["strict_pass"]),
            "total": len(rows),
            "mean_pf": round(sum(x["pf"] for x in rows) / len(rows), 3) if rows else 0,
            "max_dd": round(max((x["dd"] for x in rows), default=0), 2),
            "mean_wr": round(sum(x["wr"] for x in rows) / len(rows), 2) if rows else 0,
            "mean_n": round(sum(x["trades"] for x in rows) / len(rows), 1) if rows else 0,
            "mean_net": round(sum(x["net"] for x in rows) / len(rows), 2) if rows else 0,
        }

    # stability: best SL/TP soft-pass across TFs
    best_soft_by_tf = {
        tf: cell_summary(data[(BEST[0], BEST[1], tf)])["soft_pass"] for tf in TFS
    }
    base_soft_by_tf = {
        tf: cell_summary(data[(BASELINE[0], BASELINE[1], tf)])["soft_pass"] for tf in TFS
    }
    stable_tfs = [tf for tf in TFS if best_soft_by_tf[tf] >= 5]
    verdict = "STABLE" if len(stable_tfs) >= 2 else ("MIXED" if any(best_soft_by_tf[t] >= 5 for t in TFS) else "UNSTABLE")

    ts = datetime.now().strftime("%Y-%m-%d-%H%M")
    out = {
        "updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "strategy": "rsi-t200b",
        "change": "cross-TF (1h/2h/4h) · best SL/TP 1.8/1.5 vs baseline 2.5/1.6",
        "pairs": PAIRS,
        "timeframes": TFS,
        "baseline_sl_tp": list(BASELINE),
        "best_sl_tp": list(BEST),
        "soft_pass_by_tf_best": best_soft_by_tf,
        "soft_pass_by_tf_baseline": base_soft_by_tf,
        "stable_tfs": stable_tfs,
        "verdict": verdict,
        "errors": errors,
        "cells": [
            {"sl": sl, "tp": tp, "tf": tf, **cell_summary(data[(sl, tp, tf)]), "rows": data[(sl, tp, tf)]}
            for sl, tp in CELLS
            for tf in TFS
        ],
        "source": "local-ohlcv",
        "commission_bps": 5,
        "window": {"from": "2025-01-01", "to": "2026-09-01"},
        "zero_credits": True,
    }
    jpath = ROOT / "data" / "local" / "rsi-t200b-crosstf.json"
    jpath.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print("wrote", jpath)

    lines = [
        "# Optimizer local: rsi-t200b cross-TF 1h/2h (0 credits)",
        "",
        f"**Date**: {ts} · **Engine**: local Python · **Pairs**: {' '.join(PAIRS)}",
        f"**Best SL/TP**: {BEST[0]} / {BEST[1]} ATR · **Baseline**: {BASELINE[0]} / {BASELINE[1]}",
        f"**Window**: 2025-01-01 → 2026-09-01 · **errors**: {errors}",
        f"**Verdict**: {verdict} · stable TFs (soft≥5/8): {', '.join(stable_tfs) or '—'}",
        "",
        "## Soft-pass by TF (N≥20 gate)",
        "",
        "| TF | best 1.8/1.5 | baseline 2.5/1.6 |",
        "|---|---:|---:|",
    ]
    for tf in TFS:
        lines.append(f"| {tf} | {best_soft_by_tf[tf]}/8 | {base_soft_by_tf[tf]}/8 |")

    lines += [
        "",
        "## Cell matrix",
        "",
        "| SL | TP | TF | soft/8 | strict/8 | meanPF | maxDD% | meanWR% | meanN | meanNet% |",
        "|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for sl, tp in CELLS:
        for tf in TFS:
            s = cell_summary(data[(sl, tp, tf)])
            note_tf = tf
            lines.append(
                f"| {sl} | {tp} | {note_tf} | {s['soft_pass']}/{s['total']} | {s['strict_pass']}/{s['total']} | "
                f"{s['mean_pf']} | {s['max_dd']} | {s['mean_wr']} | {s['mean_n']} | {s['mean_net']} |"
            )

    lines += [
        "",
        f"## Best cell detail — SL {BEST[0]} / TP {BEST[1]} by TF",
        "",
    ]
    for tf in TFS:
        lines += [f"### {tf}", "", "| Pair | Net% | PF | DD% | WR% | Trades | Soft |", "|---|---:|---:|---:|---:|---:|---|"]
        for x in sorted(data[(BEST[0], BEST[1], tf)], key=lambda y: -y["pf"]):
            lines.append(
                f"| {x['base']} | {x['net']} | {x['pf']} | {x['dd']} | {x['wr']} | {x['trades']} | "
                f"{'Y' if x['soft_pass'] else 'N'} |"
            )
        lines.append("")

    lines += [
        "## Notes",
        "",
        "- Entries/signals unchanged; only timeframe resample + SL/TP from prior sweep.",
        "- No trailing, no martingale, local commission 5bps/side.",
        "- Soft gate: PF≥1.3 · DD≤30 · N≥20 · net>0. Strict adds N≥40.",
        "- Local engine ≠ tv_jul26 — MCP verify still pending if Gertrude promotes.",
        "- Zero API credits used.",
        "",
        "**Next**: Gertrude re-eval for incubation if STABLE on ≥2 TFs; else keep ESTACIONAR.",
    ]
    rep = ROOT / "data" / "reports" / f"{ts}-optimizer-rsi-t200b-crosstf-local.md"
    rep.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("wrote", rep)
    print(f"verdict={verdict} stable={stable_tfs} best_soft_by_tf={best_soft_by_tf}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
