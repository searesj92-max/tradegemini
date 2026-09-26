"""Local SL/TP grid for rsi-t200b on batch3 passers — 0 API credits.

Dispatch: data/dispatch/optimizer-rsi-t200b-sl-tp-2026-09-23.md
Pairs: ETH AVAX ARB OP ATOM INJ XRP SOL (batch3 8/16 passers)
Baseline: SL 2.5 / TP 1.6 ATR (local + batch3 defaults).
"""
from __future__ import annotations

import json
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"C:\Users\seares\Desktop\botrade")
sys.path.insert(0, str(ROOT / "scripts"))

from local_engine import backtest, desk_gate, load_ohlcv  # noqa: E402

PAIRS = ["ETH", "AVAX", "ARB", "OP", "ATOM", "INJ", "XRP", "SOL"]
BASELINE = (2.5, 1.6)
# grid: change ONE dimension carefully — SL/TP only, entries intact
GRID = [
    (2.5, 1.6),  # baseline
    (2.5, 1.2),
    (2.5, 1.0),
    (2.0, 1.6),
    (2.0, 1.3),
    (2.0, 1.0),
    (1.8, 1.5),
    (1.8, 1.2),
    (1.5, 1.5),
    (1.5, 1.2),
    (3.0, 1.6),
    (3.0, 2.0),
]


def _provider_symbol(base: str) -> tuple[str, str]:
    # prefer binance cache pattern from top40; download via load_ohlcv
    return "binance", f"{base}USDT"


def _pair_pass(r) -> bool:
    return (
        (r.profit_factor or 0) >= 1.3
        and (r.max_drawdown_pct or 99) <= 30
        and (r.trades or 0) >= 40
        and (r.net_profit_pct or 0) > 0
    )


def _soft_pass(r) -> bool:
    """Local engine often has fewer trades than tv_jul26 — soft gate for ranking."""
    return (
        (r.profit_factor or 0) >= 1.3
        and (r.max_drawdown_pct or 99) <= 30
        and (r.trades or 0) >= 20
        and (r.net_profit_pct or 0) > 0
    )


def main() -> int:
    # load universe map for provider hints if present
    uni = {}
    upath = ROOT / "data" / "universe" / "top40.json"
    if upath.exists():
        try:
            top = json.loads(upath.read_text(encoding="utf-8"))
            if isinstance(top, dict):
                top = top.get("assets") or top.get("universe") or top.get("rows") or []
            for a in top:
                if isinstance(a, dict) and a.get("base"):
                    uni[a["base"]] = a
        except Exception:
            pass

    results = {}  # (sl, tp) -> list of per-pair dicts
    bars_cache = {}
    errors = 0
    for base in PAIRS:
        asset = uni.get(base, {})
        provider = asset.get("kline_provider") or "binance"
        symbol = asset.get("binance_symbol") or asset.get("bybit_symbol") or f"{base}USDT"
        if base in ("HYPE", "LIT") or (base not in {a for a in uni} and provider == "bybit"):
            provider, symbol = _provider_symbol(base) if base not in uni else (provider, symbol)
        # force binance first, bybit fallback for OP ATOM INJ if needed
        bars = None
        for p, s in ((provider, symbol), ("binance", f"{base}USDT"), ("bybit", f"{base}USDT")):
            try:
                bars = load_ohlcv(p, s, "4h", refresh=False)
                if bars:
                    provider, symbol = p, s
                    break
            except Exception as e:
                print(f"  fail {p}/{s}: {e}")
                errors += 1
        if not bars:
            print(f"SKIP {base} no ohlcv")
            continue
        bars_cache[base] = (provider, symbol, bars)
        print(f"loaded {base} provider={provider} bars={len(bars)}")

    for sl, tp in GRID:
        key = (sl, tp)
        rows = []
        for base, (provider, symbol, bars) in bars_cache.items():
            try:
                r = backtest("rsi-t200b", f"{base}USDT", bars, "4h", sl_tp=(sl, tp))
                rows.append({
                    "base": base,
                    "net": round(r.net_profit_pct, 4),
                    "pf": round(min(r.profit_factor, 999), 4),
                    "dd": round(r.max_drawdown_pct, 4),
                    "wr": round(r.win_rate_pct, 4),
                    "trades": r.trades,
                    "wins": r.wins,
                    "losses": r.losses,
                    "pass": _pair_pass(r),
                    "soft_pass": _soft_pass(r),
                    "gate": desk_gate(r),
                })
            except Exception:
                errors += 1
                print(f"FAIL {base} sl={sl} tp={tp}")
        results[key] = rows
        npass = sum(1 for x in rows if x["pass"])
        nsoft = sum(1 for x in rows if x["soft_pass"])
        mpf = sum(x["pf"] for x in rows) / len(rows) if rows else 0
        mdd = max((x["dd"] for x in rows), default=0)
        mwr = sum(x["wr"] for x in rows) / len(rows) if rows else 0
        mtr = sum(x["trades"] for x in rows) / len(rows) if rows else 0
        print(
            f"SL={sl} TP={tp}: pass={npass}/{len(rows)} soft={nsoft}/{len(rows)} "
            f"meanPF={mpf:.3f} maxDD={mdd:.1f}% meanWR={mwr:.1f}% meanN={mtr:.1f}"
        )

    # rank: strict pass, then soft pass, then mean PF of soft passers, then mean DD
    def score(item):
        sl, tp = item[0]
        rows = item[1]
        npass = sum(1 for x in rows if x["pass"])
        nsoft = sum(1 for x in rows if x["soft_pass"])
        softers = [x for x in rows if x["soft_pass"]]
        mpf = sum(x["pf"] for x in softers) / len(softers) if softers else (
            sum(x["pf"] for x in rows) / len(rows) if rows else 0
        )
        mdd = sum(x["dd"] for x in rows) / len(rows) if rows else 99
        mean_trades = sum(x["trades"] for x in rows) / len(rows) if rows else 0
        return (npass, nsoft, mpf, -mdd, mean_trades)

    ranked = sorted(results.items(), key=score, reverse=True)
    best = ranked[0]
    base_rows = results[BASELINE]
    base_npass = sum(1 for x in base_rows if x["pass"])
    base_nsoft = sum(1 for x in base_rows if x["soft_pass"])
    best_npass = sum(1 for x in best[1] if x["pass"])
    best_nsoft = sum(1 for x in best[1] if x["soft_pass"])

    print("\n=== RANK (best first) ===")
    for (sl, tp), rows in ranked:
        npass = sum(1 for x in rows if x["pass"])
        nsoft = sum(1 for x in rows if x["soft_pass"])
        mark = " *BEST*" if (sl, tp) == best[0] else (" *BASE*" if (sl, tp) == BASELINE else "")
        print(f"  SL={sl} TP={tp} pass={npass}/{len(rows)} soft={nsoft}/{len(rows)}{mark}")

    def soft_mpf(rows):
        soft = [x for x in rows if x["soft_pass"]]
        if not soft:
            return 0.0
        return sum(x["pf"] for x in soft) / len(soft)

    def mean_dd(rows):
        return sum(x["dd"] for x in rows) / len(rows) if rows else 99

    # IMPROVED if more soft/strict passers, or same soft passers with higher mean PF and no worse mean DD
    ok_improve = (
        (best_npass > base_npass)
        or (best_nsoft > base_nsoft)
        or (
            best_nsoft == base_nsoft
            and soft_mpf(best[1]) > soft_mpf(base_rows)
            and mean_dd(best[1]) <= mean_dd(base_rows) + 1.0
        )
    )
    if base_npass == 0 and best_npass == 0 and best_nsoft == base_nsoft and soft_mpf(best[1]) <= soft_mpf(base_rows):
        ok_improve = False
    # local trade-count ceiling: note when strict gate blocked solely by N<40
    trade_limited = all(x["trades"] < 40 for x in best[1])

    # write results
    ts = datetime.now().strftime("%Y-%m-%d-%H%M")
    out = {
        "updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "strategy": "rsi-t200b",
        "change": "SL/TP only",
        "pairs": PAIRS,
        "baseline_sl_tp": list(BASELINE),
        "best_sl_tp": list(best[0]),
        "baseline_soft_pass": base_nsoft,
        "best_soft_pass": best_nsoft,
        "trade_limited_strict_gate": trade_limited,
        "errors": errors,
        "grid": [
            {
                "sl": sl, "tp": tp,
                "pass": sum(1 for x in rows if x["pass"]),
                "soft_pass": sum(1 for x in rows if x["soft_pass"]),
                "total": len(rows),
                "mean_pf": round(sum(x["pf"] for x in rows) / len(rows), 3) if rows else 0,
                "soft_mpf": round(soft_mpf(rows), 3),
                "max_dd": round(max((x["dd"] for x in rows), default=0), 2),
                "mean_wr": round(sum(x["wr"] for x in rows) / len(rows), 2) if rows else 0,
                "mean_n": round(sum(x["trades"] for x in rows) / len(rows), 1) if rows else 0,
                "rows": rows,
            }
            for (sl, tp), rows in ranked
        ],
        "verdict": "IMPROVED" if ok_improve else "NO_IMPROVEMENT",
        "source": "local-ohlcv",
        "commission_bps": 5,
        "window": {"from": "2025-01-01", "to": "2026-09-01"},
    }
    jpath = ROOT / "data" / "local" / "rsi-t200b-sltp-sweep.json"
    jpath.parent.mkdir(parents=True, exist_ok=True)
    jpath.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print("wrote", jpath)

    # markdown report
    lines = [
        "# Optimizer local: rsi-t200b SL/TP sweep (0 credits)",
        "",
        f"**Date**: {ts} · **Engine**: local Python · **TF**: 4h · **Pairs**: {' '.join(PAIRS)}",
        f"**Baseline**: SL {BASELINE[0]} / TP {BASELINE[1]} ATR · **Best**: SL {best[0][0]} / TP {best[0][1]}",
        f"**Verdict**: {out['verdict']} · **errors**: {errors} · "
        f"soft-pass (N≥20): baseline {base_nsoft}/8 → best {best_nsoft}/8",
        "",
        "## Grid ranking",
        "",
        "| SL | TP | pass/8 | soft/8 | meanPF | softPF | maxDD% | meanWR% | meanN | note |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for (sl, tp), rows in ranked:
        npass = sum(1 for x in rows if x["pass"])
        nsoft = sum(1 for x in rows if x["soft_pass"])
        mpf = sum(x["pf"] for x in rows) / len(rows) if rows else 0
        mdd = max((x["dd"] for x in rows), default=0)
        mwr = sum(x["wr"] for x in rows) / len(rows) if rows else 0
        mn = sum(x["trades"] for x in rows) / len(rows) if rows else 0
        note = ""
        if (sl, tp) == BASELINE:
            note = "baseline"
        if (sl, tp) == best[0]:
            note = ("BEST; " if note else "") + "winner"
        lines.append(
            f"| {sl} | {tp} | {npass}/{len(rows)} | {nsoft}/{len(rows)} | {mpf:.3f} | "
            f"{soft_mpf(rows):.3f} | {mdd:.1f} | {mwr:.1f} | {mn:.1f} | {note} |"
        )
    lines += [
        "",
        f"## Best cell detail — SL {best[0][0]} / TP {best[0][1]}",
        "",
        "| Pair | Net% | PF | DD% | WR% | Trades | Soft | Strict |",
        "|---|---:|---:|---:|---:|---:|---|---|",
    ]
    for x in sorted(best[1], key=lambda y: -y["pf"]):
        lines.append(
            f"| {x['base']} | {x['net']} | {x['pf']} | {x['dd']} | {x['wr']} | {x['trades']} | "
            f"{'Y' if x.get('soft_pass') else 'N'} | {'Y' if x['pass'] else 'N'} |"
        )
    lines += ["", "## Baseline detail — SL 2.5 / TP 1.6", "",
              "| Pair | Net% | PF | DD% | WR% | Trades | Soft | Strict |",
              "|---|---:|---:|---:|---:|---:|---|---|"]
    for x in sorted(base_rows, key=lambda y: -y["pf"]):
        lines.append(
            f"| {x['base']} | {x['net']} | {x['pf']} | {x['dd']} | {x['wr']} | {x['trades']} | "
            f"{'Y' if x.get('soft_pass') else 'N'} | {'Y' if x['pass'] else 'N'} |"
        )
    lines += [
        "",
        "## Notes",
        "",
        "- Entries/signals unchanged; only SL/TP ATR multipliers (dispatch rule).",
        "- No trailing, no martingale, local commission 5bps/side.",
        f"- Strict desk gate uses trades≥40 — local rsi-t200b emits ~19–38 trades/8 pairs "
        f"(trade-limited: {trade_limited}). Soft pass = PF≥1.3 · DD≤30 · N≥20 · net>0.",
        "- Local engine ≠ tv_jul26 — re-check survivors on Trader Dev before Gertrude promotes.",
        "- Zero API credits used.",
        "",
        "**Next**: if IMPROVED, Gertrude re-evaluates for incubation + cross-TF; else ESTACIONAR.",
        "Cross-TF 1h/2h still required for any incubation claim.",
    ]
    rep = ROOT / "data" / "reports" / f"{ts}-optimizer-rsi-t200b-sltp-local.md"
    rep.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("wrote", rep)
    print(f"verdict={out['verdict']} best={best[0]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
