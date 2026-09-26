"""Batch discovery focused on HIGH win-rate + SAFE metrics."""
from __future__ import annotations

import json
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"C:\Users\seares\Desktop\botrade")
sys.path.insert(0, str(ROOT / "scripts"))

from mcp_client import McpError, TraderDevClient, load_key  # noqa: E402
from pine_library_highwr import FROM, HIGH_WR_LIBRARY, SYMBOLS, TIMEFRAMES, TO  # noqa: E402
from run_discovery import (  # noqa: E402
    extract_kpis,
    fmt,
    get_curve,
    status_of,
)


def verdict_high_wr(row: dict) -> str:
    """Stricter safety + WR-aware verdict."""
    pf = row.get("profit_factor")
    dd = row.get("max_drawdown_pct")
    trades = row.get("trades") or 0
    wr = row.get("win_rate_pct") or 0
    net = row.get("net_profit_pct") or 0
    if pf is None or trades < 40:
        return "Watchlist"
    # reject unsafe / negative
    if pf < 1.0 or net <= 0 or (dd is not None and dd > 40):
        return "Reject"
    # safe candidate: PF, DD, WR, trades
    safe_dd = dd is None or dd <= 30
    if pf >= 1.3 and safe_dd and wr >= 50 and trades >= 50:
        return "Candidate"
    if pf >= 1.2 and safe_dd and wr >= 45 and trades >= 40:
        return "Incubate"
    if pf >= 1.1 and net > 0 and trades >= 40:
        return "Watchlist"
    if pf < 0.9 or net < -15:
        return "Reject"
    return "Watchlist"


def main() -> int:
    key = load_key()
    client = TraderDevClient(key)
    print("connected", client.session_id)

    try:
        client.call("get_pine_codegen_rules", {})
        print("codegen rules ok")
    except McpError as e:
        print("codegen rules failed", e)

    # leaderboard high-WR safe slice
    leaderboard: list[dict] = []
    try:
        search = client.call(
            "search_strategies",
            {
                "minWinRatePct": 50,
                "maxDrawdownPct": 25,
                "minProfitFactor": 1.3,
                "minTrades": 50,
                "sort": "sharpe",
                "limit": 16,
            },
        )
        if isinstance(search, str):
            search = json.loads(search)
        rows = search.get("results") or []
        for r in rows:
            res = r.get("result") or r.get("metrics") or r
            if not isinstance(res, dict):
                res = {}
            # flatten
            def g(src, *keys):
                for k in keys:
                    if src.get(k) is not None:
                        return src[k]
                return None

            # search shape may nest under result
            base = r.get("result") if isinstance(r.get("result"), dict) else r
            net = g(base, "netProfitPct", "netProfit")
            pf = g(base, "profitFactor", "pf")
            dd = g(base, "maxDrawdownPct", "drawdownPct")
            wr = g(base, "winRatePct", "winRate")
            trades = g(base, "totalTrades", "trades")
            sharpe = g(base, "sharpeRatio", "sharpe")
            # some results only expose via nested
            if pf is None and isinstance(r.get("result"), dict):
                pf = r["result"].get("profitFactor")
            row = {
                "id": r.get("id") or g(base, "resultId", "id"),
                "name": r.get("name") or "untitled",
                "symbol": r.get("symbol"),
                "timeframe": str(r.get("timeframe") or ""),
                "source": "leaderboard",
                "family": "public-hw",
                "agent": "search",
                "net_profit_pct": net,
                "profit_factor": pf,
                "max_drawdown_pct": dd,
                "win_rate_pct": wr,
                "trades": trades,
                "sharpe": sharpe,
                "result_id": g(base, "resultId", "id") or r.get("id"),
                "view_url": g(base, "viewUrl", "strategyViewUrl"),
                "last_backtest": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            }
            # skip absurd / no-SL patterns (hold-until-green, WR=100 with no PF)
            name_l = (row["name"] or "").lower()
            if "no sl" in name_l or "hold-until-green" in name_l:
                continue
            if wr is not None and wr >= 99 and pf is None:
                continue
            row["verdict"] = verdict_high_wr(row)
            row["status"] = status_of(row["verdict"])
            leaderboard.append(row)
        print("leaderboard safe", len(leaderboard))
    except Exception as e:
        print("leaderboard failed", e)

    for row in leaderboard[:6]:
        rid = row.get("result_id")
        if rid:
            row["curve"] = get_curve(client, rid, None)

    combos = []
    for strat_key, meta in HIGH_WR_LIBRARY.items():
        for sym in SYMBOLS:
            for tf in TIMEFRAMES:
                combos.append((strat_key, meta, sym, tf))

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
                    "notes": f"high-wr {strat_key}",
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
                "id": f"hw-{strat_key}-{sym}-{tf}",
                "name": name,
                "symbol": sym,
                "timeframe": tf,
                "source": "discovery-hw",
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
                "warnings": warnings,
                "last_backtest": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "pine_key": f"hw-{strat_key}",
            }
            row["verdict"] = verdict_high_wr(row)
            row["status"] = status_of(row["verdict"])
            if row.get("result_id"):
                row["curve"] = get_curve(client, row["result_id"], k.get("job_id"))
            else:
                row["curve"] = []
            rows_out.append(row)
            wr = row.get("win_rate_pct")
            print(
                f"[{i}/{len(combos)}] {name} net={fmt(row.get('net_profit_pct'))} "
                f"pf={fmt(row.get('profit_factor'))} dd={fmt(row.get('max_drawdown_pct'))} "
                f"wr={fmt(wr)} trades={row.get('trades')} -> {row['verdict']}"
            )
        except McpError as e:
            errors += 1
            print(f"[{i}/{len(combos)}] ERROR {strat_key}/{sym}/{tf}: {e}")
            time.sleep(1)
        except Exception:
            errors += 1
            print(f"[{i}/{len(combos)}] FAIL {strat_key}/{sym}/{tf}")
            traceback.print_exc()

    # persist pines
    pine_dir = ROOT / "data" / "pine"
    pine_dir.mkdir(parents=True, exist_ok=True)
    for k, src in pine_cache.items():
        (pine_dir / f"hw-{k}.pine").write_text(src, encoding="utf-8")

    all_rows = rows_out + leaderboard

    # report
    reports = ROOT / "data" / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d-%H%M")

    # aggregate by strategy key: how many pairs pass safety
    from collections import defaultdict

    by_key: dict[str, list[dict]] = defaultdict(list)
    for r in rows_out:
        key = r["id"].rsplit("-", 2)[0]  # hw-strat
        by_key[key].append(r)

    def agg_pass(rs):
        return sum(
            1
            for x in rs
            if (x.get("profit_factor") or 0) >= 1.3
            and (x.get("max_drawdown_pct") or 99) <= 30
            and (x.get("win_rate_pct") or 0) >= 50
            and (x.get("trades") or 0) >= 40
            and (x.get("net_profit_pct") or 0) > 0
        )

    report = [
        "# High-WR Safe Discovery Report",
        "",
        f"**Date**: {ts}",
        f"**Agent**: high-wr-script",
        f"**Combos**: {len(rows_out)} local + {len(leaderboard)} leaderboard",
        f"**Errors**: {errors}",
        "",
        "## Criteria (local verdict)",
        "",
        "- Candidate: PF≥1.3 · DD≤30% · **WR≥50%** · trades≥50 · net>0",
        "- Incubate: PF≥1.2 · DD≤30% · WR≥45% · trades≥40",
        "- Reject: PF<1.0 or net≤0 or DD>40%",
        "",
        "## Strategy robustness (pairs passing full safety gate)",
        "",
        "| Strategy | Pairs pass / total | Best WR | Best PF | Min DD |",
        "|---|---:|---:|---:|---:|",
    ]

    def num(v, d=0.0):
        try:
            return float(v)
        except (TypeError, ValueError):
            return d

    for key in sorted(by_key.keys()):
        rs = by_key[key]
        passed = agg_pass(rs)
        best_wr = max((num(x.get("win_rate_pct")) for x in rs), default=0)
        best_pf = max((num(x.get("profit_factor")) for x in rs), default=0)
        # among positive net rows
        pos = [x for x in rs if num(x.get("net_profit_pct")) > 0]
        min_dd = min((num(x.get("max_drawdown_pct"), 99) for x in pos), default=99)
        report.append(
            f"| {key} | {passed}/{len(rs)} | {best_wr:.1f}% | {best_pf:.2f} | {min_dd:.1f}% |"
        )

    report += [
        "",
        "## Top local rows by WR (PF≥1.2, DD≤30, trades≥40, net>0)",
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
    for r in good[:30]:
        report.append(
            f"| {r['name']} | {r['symbol']} | {r['timeframe']} | "
            f"{fmt(r.get('net_profit_pct'))} | {fmt(r.get('profit_factor'))} | "
            f"{fmt(r.get('max_drawdown_pct'))} | {fmt(r.get('win_rate_pct'))} | "
            f"{r.get('trades')} | {r['verdict']} |"
        )

    report += [
        "",
        "## Leaderboard (public, safety-filtered: no no-SL, WR<99 without PF)",
        "",
        "| Name | Sym | TF | Net% | PF | DD% | WR% | Trades | Verdict |",
        "|---|---|---|---:|---:|---:|---:|---:|---|",
    ]
    lb_sorted = sorted(
        [r for r in leaderboard if r.get("win_rate_pct") is not None],
        key=lambda x: num(x.get("win_rate_pct")),
        reverse=True,
    )
    for r in lb_sorted[:20]:
        report.append(
            f"| {r['name'][:48]} | {r['symbol']} | {r['timeframe']} | "
            f"{fmt(r.get('net_profit_pct'))} | {fmt(r.get('profit_factor'))} | "
            f"{fmt(r.get('max_drawdown_pct'))} | {fmt(r.get('win_rate_pct'))} | "
            f"{r.get('trades')} | {r['verdict']} |"
        )

    hist: dict[str, int] = {}
    for r in rows_out:
        hist[r["verdict"]] = hist.get(r["verdict"], 0) + 1
    report += ["", "## Verdict histogram (local)", ""]
    for k, v in sorted(hist.items()):
        report.append(f"- {k}: {v}")

    report += [
        "",
        "## Note",
        "",
        "Batch: high-WR design (trend filter / regime / sweep / squeeze).",
        "Engine tv_jul26. No real orders. Dashboard: dashboard/data.json + index.html.",
        "Leaderboard rows with WR≈100 and no SL were excluded as unsafe.",
    ]
    (reports / f"{ts}-high-wr-batch.md").write_text("\n".join(report) + "\n", encoding="utf-8")

    # merge into existing dashboard data (don't wipe other rows)
    data_path = ROOT / "dashboard" / "data.json"
    try:
        existing = json.loads(data_path.read_text(encoding="utf-8"))
        old_rows = existing.get("strategies") or []
    except Exception:
        old_rows = []

    new_ids = {r["id"] for r in all_rows}
    kept = [r for r in old_rows if r.get("id") not in new_ids]
    merged = kept + all_rows
    # recompute verdict counts
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

    # top safe summary for stdout
    print("\n=== TOP SAFE HIGH-WR (local) ===")
    for r in good[:15]:
        print(
            f"  WR={fmt(r.get('win_rate_pct'))}% PF={fmt(r.get('profit_factor'))} "
            f"DD={fmt(r.get('max_drawdown_pct'))}% net={fmt(r.get('net_profit_pct'))}% "
            f"trades={r.get('trades')} | {r['name']} | {r['verdict']}"
        )

    client.close()
    return 0 if errors < len(combos) else 1


if __name__ == "__main__":
    sys.exit(main())
