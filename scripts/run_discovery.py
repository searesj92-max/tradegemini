"""Batch discovery: run library strategies × symbols × TFs, write dashboard/data.json."""
from __future__ import annotations

import json
import os
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"C:\Users\seares\Desktop\botrade")
sys.path.insert(0, str(ROOT / "scripts"))

from mcp_client import McpError, TraderDevClient, load_key  # noqa: E402
from pine_library import FROM, LIBRARY, SYMBOLS, TIMEFRAMES, TO  # noqa: E402

from typing import Any  # noqa: E402


def verdict_of(row: dict) -> str:
    pf = row.get("profit_factor")
    dd = row.get("max_drawdown_pct")
    trades = row.get("trades") or 0
    wr = row.get("win_rate_pct") or 0
    net = row.get("net_profit_pct") or 0
    if pf is None or trades < 30:
        return "Watchlist"
    if pf >= 1.3 and (dd is None or dd <= 30) and net > 0:
        if trades >= 50:
            return "Candidate"
        return "Incubate"
    if pf >= 1.0 and net > 0 and trades >= 30:
        return "Watchlist"
    if pf < 0.8 or net < -20:
        return "Reject"
    return "Watchlist"


def status_of(verdict: str) -> str:
    return {
        "Reject": "rejected",
        "Watchlist": "watchlist",
        "Incubate": "incubate",
        "Candidate": "candidate",
        "Production candidate": "production",
    }.get(verdict, "draft")


def extract_kpis(payload: Any) -> dict:
    from mcp_client import TraderDevClient

    if isinstance(payload, str):
        payload = TraderDevClient._loads_lenient(payload)
    # quick_backtest shapes vary; dig common locations
    candidates = []
    if isinstance(payload, dict):
        for k in ("result", "data", "metrics", "summary"):
            if isinstance(payload.get(k), dict):
                candidates.append(payload[k])
        candidates.append(payload)
    result = {}
    for c in candidates:
        if not isinstance(c, dict):
            continue
        mapping = {
            "net_profit_pct": ["netProfitPct", "netProfitPercent", "netProfit_pct", "netPnlPct"],
            "profit_factor": ["profitFactor", "pf", "PF"],
            "max_drawdown_pct": ["maxDrawdownPct", "maxDrawdownPercent", "drawdownPct"],
            "win_rate_pct": ["winRatePct", "winRate", "winPercent"],
            "trades": ["totalTrades", "trades", "tradeCount"],
            "sharpe": ["sharpeRatio", "sharpe"],
            "result_id": ["resultId", "id", "result_id"],
            "job_id": ["jobId", "job_id"],
            "view_url": ["viewUrl", "strategyViewUrl", "browseUrl"],
        }
        for dest, keys in mapping.items():
            if dest in result and result[dest] is not None:
                continue
            for key in keys:
                if key in c and c[key] is not None:
                    result[dest] = c[key]
                    break
        # nested result.resultId
        if result.get("result_id") is None and "resultId" in c:
            result["result_id"] = c["resultId"]
    # job id often at top-level result object
    if isinstance(payload.get("result"), dict):
        r = payload["result"]
        # get_equity_curve wants result.id (NOT adhoc jobId)
        if result.get("result_id") is None:
            result["result_id"] = r.get("id") or r.get("resultId")
        if result.get("job_id") is None:
            result["job_id"] = r.get("jobId")
    if result.get("result_id") is None:
        result["result_id"] = payload.get("resultId") or payload.get("id")
    if result.get("job_id") is None:
        result["job_id"] = payload.get("jobId")
    # engine warnings
    result["warnings"] = payload.get("warnings") or (
        payload.get("result", {}) or {}
    ).get("warnings") or []
    result["engine"] = payload.get("engine") or (payload.get("result", {}) or {}).get("engine")
    return result


def downsample(points: list[dict], max_points: int = 80) -> list[dict]:
    if not points:
        return []
    if len(points) <= max_points:
        return points
    step = len(points) / float(max_points)
    out = []
    for i in range(max_points):
        out.append(points[int(i * step)])
    if out[-1] is not points[-1]:
        out[-1] = points[-1]
    return out


def get_curve(client: TraderDevClient, result_id: str | None, job_id: str | None) -> list[dict]:
    if not result_id and not job_id:
        return []
    # prefer result.id; adhoc jobId does NOT work for get_equity_curve
    candidates = [c for c in (result_id, job_id) if c]
    payload = None
    for ref in candidates:
        try:
            payload = client.call("get_equity_curve", {"jobId": ref, "maxPoints": 400})
            break
        except McpError:
            continue
    if payload is None:
        return []
    if isinstance(payload, str):
        payload = TraderDevClient._loads_lenient(payload)
        if isinstance(payload, str):
            return []
    series = []
    if isinstance(payload, list):
        series = [p for p in payload if isinstance(p, dict)]
    elif isinstance(payload, dict):
        raw = payload.get("points") or payload.get("curve") or payload.get("equity") or payload.get("data") or []
        if isinstance(payload.get("result"), dict):
            raw = raw or payload["result"].get("points") or payload["result"].get("curve") or []
        if not raw and "barIndex" in payload:
            raw = [payload]
        if isinstance(raw, dict):
            # maybe {equity:[], ...}
            keys = list(raw.keys())
            n = len(raw[keys[0]]) if keys and isinstance(raw[keys[0]], list) else 0
            for i in range(n):
                row = {}
                for k in keys:
                    if isinstance(raw[k], list) and i < len(raw[k]):
                        row[k] = raw[k][i]
                series.append(row)
        elif isinstance(raw, list):
            series = [p for p in raw if isinstance(p, dict)]
    # normalize equity only for sparkline
    out = []
    for p in series:
        eq = p.get("equity", p.get("netProfit", p.get("value")))
        if eq is None:
            continue
        out.append({"t": p.get("barTime"), "e": eq})
    return downsample(out, 80)


def main() -> int:
    key = load_key()
    client = TraderDevClient(key)
    print("connected, session", client.session_id)

    # refresh codegen rules once (required by tool docs)
    try:
        rules = client.call("get_pine_codegen_rules", {})
        print("codegen rules ok", type(rules).__name__)
    except McpError as e:
        print("codegen rules failed", e)

    # leaderboard sample for "discovered" board (public strategies)
    leaderboard: list[dict] = []
    try:
        search = client.call("search_strategies", {"sort": "profit", "limit": 24, "minTrades": 50})
        if isinstance(search, str):
            search = json.loads(search)
        for r in search.get("results", [])[:24]:
            res = r.get("result") or {}
            net = res.get("netProfitPct")
            # skip absurd multi-year 10000%+ for local board filter? keep but mark source
            row = {
                "id": r.get("id"),
                "name": r.get("name") or "untitled",
                "symbol": r.get("symbol"),
                "timeframe": str(r.get("timeframe") or ""),
                "source": "leaderboard",
                "family": "public",
                "agent": "search",
                "net_profit_pct": net,
                "profit_factor": res.get("profitFactor"),
                "max_drawdown_pct": res.get("maxDrawdownPct"),
                "win_rate_pct": res.get("winRatePct"),
                "trades": res.get("totalTrades"),
                "sharpe": res.get("sharpeRatio"),
                "result_id": res.get("resultId"),
                "view_url": res.get("viewUrl"),
                "last_backtest": datetime.fromtimestamp(
                    (res.get("createdAt") or r.get("updatedAt") or int(time.time() * 1000)) / 1000,
                    tz=timezone.utc,
                ).strftime("%Y-%m-%d"),
            }
            row["verdict"] = verdict_of(row)
            row["status"] = status_of(row["verdict"])
            leaderboard.append(row)
        print("leaderboard", len(leaderboard))
    except Exception as e:
        print("leaderboard failed", e)

    # curves for top public (best effort, few)
    for row in leaderboard[:8]:
        rid = row.get("result_id")
        if rid:
            curve = get_curve(client, rid, None)
            row["curve"] = curve

    rows: list[dict] = []
    pine_cache = {}
    errors = 0
    combos = []
    for strat_key, meta in LIBRARY.items():
        for sym in SYMBOLS:
            for tf in TIMEFRAMES:
                combos.append((strat_key, meta, sym, tf))

    print("combos", len(combos))
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
                    "notes": f"discovery {strat_key}",
                },
            )
            if isinstance(payload, str):
                try:
                    payload = json.loads(payload)
                except json.JSONDecodeError:
                    print(f"[{i}/{len(combos)}] parse fail {name}")
                    errors += 1
                    continue
            k = extract_kpis(payload)
            warnings = k.get("warnings") or []
            severe = any("cascade" in str(w).lower() for w in warnings)
            row = {
                "id": f"{strat_key}-{sym}-{tf}",
                "name": name,
                "symbol": sym,
                "timeframe": tf,
                "source": "discovery",
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
                "pine_key": strat_key,
            }
            if severe:
                row["verdict"] = "Watchlist"
                row["status"] = "draft"
                row["notes"] = "severe cascade warning — retry"
            else:
                row["verdict"] = verdict_of(row)
                row["status"] = status_of(row["verdict"])
            if row.get("result_id"):
                row["curve"] = get_curve(client, row["result_id"], k.get("job_id"))
            else:
                row["curve"] = []
            rows.append(row)
            print(
                f"[{i}/{len(combos)}] {name} net={row.get('net_profit_pct')} "
                f"pf={row.get('profit_factor')} dd={row.get('max_drawdown_pct')} "
                f"wr={row.get('win_rate_pct')} trades={row.get('trades')} -> {row['verdict']}"
            )
        except McpError as e:
            errors += 1
            print(f"[{i}/{len(combos)}] ERROR {strat_key}/{sym}/{tf}: {e}")
            time.sleep(1)
        except Exception:
            errors += 1
            print(f"[{i}/{len(combons) if False else len(combos)}] FAIL {strat_key}/{sym}/{tf}")
            traceback.print_exc()

    all_rows = rows + leaderboard
    # persist pine sources used
    pine_dir = ROOT / "data" / "pine"
    pine_dir.mkdir(parents=True, exist_ok=True)
    for k, src in pine_cache.items():
        (pine_dir / f"disc-{k}.pine").write_text(src, encoding="utf-8")

    # write report
    reports = ROOT / "data" / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d-%H%M")
    n_cand = sum(1 for r in rows if r["verdict"] in ("Candidate", "Incubate", "Watchlist") and (r.get("profit_factor") or 0) >= 1.1)
    report = [
        f"# Discovery Batch Report",
        f"",
        f"**Date**: {ts}",
        f"**Agent**: discovery-script",
        f"**Combos**: {len(rows)} local + {len(leaderboard)} leaderboard",
        f"**Errors**: {errors}",
        f"",
        f"## Top local results",
        f"",
        f"| Strategy | Sym | TF | Net% | PF | DD% | WR% | Trades | Verdict |",
        f"|---|---|---|---:|---:|---:|---:|---:|---|",
    ]
    top = sorted(
        [r for r in rows if r.get("profit_factor") is not None],
        key=lambda x: ((x.get("profit_factor") or 0), (x.get("net_profit_pct") or 0)),
        reverse=True,
    )[:25]
    for r in top:
        report.append(
            f"| {r['name']} | {r['symbol']} | {r['timeframe']} | "
            f"{fmt(r.get('net_profit_pct'))} | {fmt(r.get('profit_factor'))} | "
            f"{fmt(r.get('max_drawdown_pct'))} | {fmt(r.get('win_rate_pct'))} | "
            f"{r.get('trades')} | {r['verdict']} |"
        )
    report += [
        "",
        "## Verdict histogram (local)",
        "",
    ]
    hist: dict[str, int] = {}
    for r in rows:
        hist[r["verdict"]] = hist.get(r["verdict"], 0) + 1
    for k, v in sorted(hist.items()):
        report.append(f"- {k}: {v}")
    report += [
        "",
        "## Note",
        "",
        "Batch used Trader Dev quick_backtest (tv_jul26). No real orders.",
        "Dashboard: dashboard/data.json + dashboard/index.html.",
    ]
    (reports / f"{ts}-discovery-batch.md").write_text("\n".join(report) + "\n", encoding="utf-8")

    # write dashboard data
    data = {
        "updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "stats": {
            "total": len(all_rows),
            "local": len(rows),
            "leaderboard": len(leaderboard),
            "errors": errors,
            "candidates": sum(1 for r in all_rows if r["verdict"] == "Candidate"),
            "incubate": sum(1 for r in all_rows if r["verdict"] == "Incubate"),
            "watchlist": sum(1 for r in all_rows if r["verdict"] == "Watchlist"),
            "rejected": sum(1 for r in all_rows if r["verdict"] == "Reject"),
        },
        "strategies": all_rows,
        "agents": sorted({r.get("agent") or "unknown" for r in all_rows}),
        "families": sorted({r.get("family") or "unknown" for r in all_rows}),
    }
    out = ROOT / "dashboard" / "data.json"
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    # embed copy for file://
    embedded = json.dumps(data, ensure_ascii=False)
    html_path = ROOT / "dashboard" / "index.html"
    # data.js for offline
    (ROOT / "dashboard" / "data.js").write_text(
        "window.MISSION_DATA = " + embedded + ";\n", encoding="utf-8"
    )
    print("wrote", out, "rows", len(all_rows))
    print("stats", data["stats"])
    client.close()
    return 0 if errors < len(combos) else 1


def fmt(v):
    if v is None:
        return "-"
    if isinstance(v, float):
        return f"{v:.2f}"
    return str(v)


if __name__ == "__main__":
    sys.exit(main())
