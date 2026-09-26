"""Rebuild dashboard/data.json + data.js from reports + live rows.

Recovers lost full board after schema overwrite; enriches win/loss split.
"""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"C:\Users\seares\Desktop\botrade")
REPORTS = ROOT / "data" / "reports"
DASH = ROOT / "dashboard"


def fnum(v, default=None):
    if v is None:
        return default
    s = str(v).strip().replace("%", "").replace(",", "")
    if s in ("", "—", "-", "n/a", "N/A"):
        return default
    try:
        return float(s)
    except ValueError:
        return default


def enrich(row: dict) -> dict:
    trades = row.get("trades")
    wr = row.get("win_rate_pct")
    if trades and wr is not None and fnum(trades) is not None and fnum(wr) is not None:
        t = int(round(float(trades)))
        w = int(round(t * float(wr) / 100.0))
        w = max(0, min(t, w))
        row["wins"] = w
        row["losses"] = t - w
        row["win_pct"] = round(float(wr), 2)
        row["loss_pct"] = round(100.0 - float(wr), 2) if t else None
    else:
        row.setdefault("wins", None)
        row.setdefault("losses", None)
        if wr is not None:
            row["win_pct"] = fnum(wr)
            row["loss_pct"] = round(100.0 - float(wr), 2)
    # expectancy-ish
    net = fnum(row.get("net_profit_pct"))
    if net is not None and trades:
        row["expectancy_pct"] = round(net / float(trades), 4)
    if not row.get("id"):
        sym = row.get("symbol") or "NA"
        tf = row.get("timeframe") or "na"
        key = re.sub(r"[^a-z0-9]+", "-", (row.get("name") or "x").lower()).strip("-")
        row["id"] = f"{key}-{sym}-{tf}"
    if not row.get("status"):
        v = row.get("verdict") or "Watchlist"
        row["status"] = {
            "Candidate": "candidate",
            "Incubate": "incubate",
            "Watchlist": "watchlist",
            "Reject": "rejected",
        }.get(v, "watchlist")
    return row


def parse_md_table_rows(text: str) -> list[dict]:
    """Parse discovery-style tables: | name | sym | tf | net | pf | dd | wr | trades | verdict |"""
    out = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 8:
            continue
        if set("".join(cells)) <= set("-: "):
            continue
        # skip header-ish
        low = cells[0].lower()
        if low in ("strategy", "name", "---") or low.startswith("strategy"):
            continue
        # try numeric positions from the right: verdict, trades, wr, dd, pf, net
        try:
            # standard 9-col
            if len(cells) >= 9 and fnum(cells[4]) is not None and fnum(cells[7]) is not None:
                name, sym, tf = cells[0], cells[1], cells[2]
                net, pf, dd, wr, trades = fnum(cells[3]), fnum(cells[4]), fnum(cells[5]), fnum(cells[6]), int(fnum(cells[7], 0) or 0)
                verdict = cells[8]
            elif len(cells) >= 8 and fnum(cells[3]) is not None:
                # | Strategy | pass | meanPF | meanWR | bestNet | (5 col family)
                if len(cells) == 5 and fnum(cells[1]) is not None and "pass" in text[max(0, text.find(line) - 200):text.find(line)].lower():
                    continue
                name, sym, tf = cells[0], "", ""
                net, pf, dd, wr, trades = fnum(cells[1]), fnum(cells[2]), fnum(cells[3]), fnum(cells[4]) if len(cells) > 4 else None, int(fnum(cells[5], 0) or 0) if len(cells) > 5 else 0
                verdict = cells[6] if len(cells) > 6 else "Watchlist"
            else:
                continue
        except (ValueError, IndexError):
            continue
        # name often "strat · SYM · TF"
        parts = [p.strip() for p in name.split("·")]
        if len(parts) >= 3:
            name, sym, tf = parts[0], parts[1], parts[2]
        if not sym or sym in ("Sym", "Symbol"):
            continue
        if tf in ("TF", "Timeframe"):
            continue
        if not isinstance(net, (int, float)):
            continue
        out.append(
            {
                "name": name.strip(),
                "symbol": sym,
                "timeframe": str(tf),
                "net_profit_pct": net,
                "profit_factor": pf,
                "max_drawdown_pct": dd,
                "win_rate_pct": wr,
                "trades": trades,
                "verdict": verdict if verdict in ("Candidate", "Incubate", "Watchlist", "Reject") else "Watchlist",
            }
        )
    return out


def parse_bullet_rows(text: str) -> list[dict]:
    """Parse '### b3-rsi-t200b' + '- SYM TF: net=x% PF=y ...' sections."""
    out: list[dict] = []
    current = None
    for line in text.splitlines():
        m = re.match(r"^###\s+(\S+)", line.strip())
        if m:
            current = m.group(1)
            continue
        m = re.match(
            r"^-\s+([A-Z0-9]+)\s+(\w+):\s+net=([-\d.]+)%\s+PF=([-\d.]+)\s+DD=([-\d.]+)%\s+WR=([-\d.]+)%\s+trades=(\d+)",
            line.strip(),
        )
        if m and current:
            out.append(
                {
                    "name": current,
                    "symbol": m.group(1),
                    "timeframe": m.group(2),
                    "net_profit_pct": fnum(m.group(3)),
                    "profit_factor": fnum(m.group(4)),
                    "max_drawdown_pct": fnum(m.group(5)),
                    "win_rate_pct": fnum(m.group(6)),
                    "trades": int(m.group(7)),
                    "verdict": "Watchlist",
                }
            )
        # batch4 style without % on net sometimes: net=0% already covered
    return out


def source_family(name: str) -> tuple[str, str]:
    n = name.lower()
    if n.startswith("b3-") or "rsi-t200" in n or n in ("rsi-t100", "squeeze", "bb-pinch"):
        return "batch3", "researcher"
    if n.startswith("b4-") or n.startswith("rsi-t-l") or n in ("hh-brk", "bull-pb", "gold-pb", "dc-long", "mom-dip", "sq-long"):
        return "batch4", "researcher"
    if n.startswith("hw-") or n.startswith("disc-"):
        return "high-wr" if n.startswith("hw-") else "discovery", "researcher"
    if n.startswith("nt-"):
        return "notrail", "optimizer"
    if n.startswith("lib-") or "g91" in n or "desk 62" in n or "ftmo" in n or "donchian trail" in n or "claude strategy" in n or "kontrolle" in n or "paper retest" in n:
        return "leaderboard", "search"
    return "local", "researcher"


def load_report_rows() -> list[dict]:
    rows: list[dict] = []
    for path in sorted(REPORTS.glob("*.md")):
        text = path.read_text(encoding="utf-8", errors="replace")
        name = path.name
        batch = None
        if "discovery" in name:
            batch = "discovery"
        elif "high-wr" in name and "synthesis" not in name:
            batch = "high-wr"
        elif "notrail" in name:
            batch = "notrail"
        elif "batch3" in name:
            batch = "batch3"
        elif "batch4" in name:
            batch = "batch4"
        elif "leaderboard" in name:
            batch = "leaderboard"
        if not batch:
            # still try table parse for top rows
            batch = "report"
        for r in parse_md_table_rows(text):
            fam, agent = source_family(r["name"])
            if batch == "discovery":
                fam, agent = "discovery", "researcher"
            elif batch == "high-wr":
                if fam == "leaderboard":
                    pass
                else:
                    fam, agent = "high-wr", "researcher"
            elif batch == "notrail":
                fam, agent = "notrail", "optimizer"
            elif batch == "batch3":
                fam, agent = "batch3", "researcher"
            elif batch == "batch4":
                fam, agent = "batch4", "researcher"
            r["family"] = fam
            r["agent"] = agent
            r["source"] = "leaderboard" if fam == "leaderboard" else f"report-{batch}"
            r["last_backtest"] = "2026-09-23"
            r["pine_key"] = None
            r["curve"] = []
            rows.append(r)
        if batch in ("batch3", "batch4", "high-wr", "notrail", "discovery"):
            for r in parse_bullet_rows(text):
                fam, agent = source_family(r["name"])
                if batch == "batch3":
                    fam, agent = "batch3", "researcher"
                elif batch == "batch4":
                    fam, agent = "batch4", "researcher"
                r["family"] = fam
                r["agent"] = agent
                r["source"] = f"report-{batch}"
                r["last_backtest"] = "2026-09-23"
                r["pine_key"] = None
                r["curve"] = []
                rows.append(r)
    return rows


def family_rollups(current: list[dict], report_rows: list[dict]) -> list[dict]:
    """Family-level cards: pass rate from report tables where available."""
    by_fam: dict[str, list[dict]] = defaultdict(list)
    for r in current + report_rows:
        fam = r.get("family") or "unknown"
        if r.get("trades") is None and r.get("profit_factor") is None:
            continue
        by_fam[fam].append(r)
    rollups = []
    for fam, rs in by_fam.items():
        if len(rs) < 3:
            continue
        # recompute pairs pass with desk gate
        def ok(x):
            pf = fnum(x.get("profit_factor"), 0) or 0
            dd = fnum(x.get("max_drawdown_pct"), 99) or 99
            tr = fnum(x.get("trades"), 0) or 0
            net = fnum(x.get("net_profit_pct"), 0) or 0
            return pf >= 1.3 and dd <= 30 and tr >= 40 and net > 0

        p = sum(1 for x in rs if ok(x))
        mpf = sum(fnum(x.get("profit_factor"), 0) or 0 for x in rs) / len(rs)
        mwr = sum(fnum(x.get("win_rate_pct"), 0) or 0 for x in rs) / len(rs)
        mdd = max((fnum(x.get("max_drawdown_pct"), 0) or 0) for x in rs)
        bn = max((fnum(x.get("net_profit_pct"), 0) or 0) for x in rs)
        tot_tr = sum(int(fnum(x.get("trades"), 0) or 0) for x in rs)
        wins = sum(int(x.get("wins") or 0) for x in rs if x.get("wins") is not None)
        losses = sum(int(x.get("losses") or 0) for x in rs if x.get("losses") is not None)
        rollups.append(
            {
                "id": f"fam-{fam}",
                "name": f"[FAMILY] {fam}",
                "symbol": f"{len(rs)} rows",
                "timeframe": "—",
                "source": "rollup",
                "family": fam,
                "agent": "desk",
                "net_profit_pct": round(bn, 2),
                "profit_factor": round(mpf, 3),
                "max_drawdown_pct": round(mdd, 2),
                "win_rate_pct": round(mwr, 2),
                "trades": tot_tr,
                "wins": wins if wins else None,
                "losses": losses if losses else None,
                "win_pct": round(mwr, 2),
                "loss_pct": round(100 - mwr, 2),
                "pairs_pass": p,
                "pairs_total": len(rs),
                "is_rollup": True,
                "sharpe": None,
                "avg_trade": None,
                "long_trades": None,
                "short_trades": None,
                "result_id": None,
                "view_url": None,
                "curve": [],
                "last_backtest": "2026-09-23",
                "verdict": (
                    "Candidate"
                    if p >= 5 and mpf >= 1.3
                    else ("Incubate" if p >= 4 and mpf >= 1.2 else ("Watchlist" if p >= 1 or mpf >= 1.1 else "Reject"))
                ),
                "status": "candidate" if p >= 5 and mpf >= 1.3 else "watchlist",
                "pine_key": None,
                "notes": f"pass {p}/{len(rs)} · meanPF {mpf:.2f} · meanWR {mwr:.1f}%",
            }
        )
    return rollups


def normalize_legacy(rows: list[dict]) -> list[dict]:
    out = []
    for r in rows:
        if r.get("id") and str(r.get("id")).startswith("b4-"):
            out.append(r)
            continue
        # legacy parked schema
        metrics = r.get("metrics") or {}
        name = r.get("name") or "legacy"
        # flatten
        flat = {
            "id": r.get("id") or f"legacy-{re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')}",
            "name": name,
            "symbol": metrics.get("symbol") or r.get("symbol") or "—",
            "timeframe": r.get("timeframe") or metrics.get("timeframe") or "—",
            "source": r.get("source") or "legacy-decision",
            "family": r.get("family") or "decision",
            "agent": r.get("agent") or "gertrude",
            "net_profit_pct": metrics.get("net") if metrics.get("net") is not None else r.get("net_profit_pct"),
            "profit_factor": metrics.get("PF") if metrics.get("PF") is not None else r.get("profit_factor"),
            "max_drawdown_pct": metrics.get("DD") if metrics.get("DD") is not None else (
                metrics.get("maxDD") if isinstance(metrics.get("maxDD"), (int, float)) else r.get("max_drawdown_pct")
            ),
            "win_rate_pct": metrics.get("WR") if metrics.get("WR") is not None else r.get("win_rate_pct"),
            "trades": metrics.get("trades") if metrics.get("trades") is not None else r.get("trades"),
            "sharpe": r.get("sharpe"),
            "avg_trade": r.get("avg_trade"),
            "long_trades": r.get("long_trades"),
            "short_trades": r.get("short_trades"),
            "result_id": r.get("result_id"),
            "view_url": r.get("view_url"),
            "curve": r.get("curve") or [],
            "last_backtest": r.get("last_backtest") or r.get("reportDate") or "2026-09-23",
            "verdict": r.get("verdict") or "Watchlist",
            "status": r.get("status") or "watchlist",
            "pine_key": r.get("pine_key"),
            "notes": r.get("notes"),
            "pairs_pass": metrics.get("pairsPass") or metrics.get("pairsWithSignal"),
            "pairs_total": metrics.get("totalPairs") or metrics.get("pairs"),
            "is_rollup": bool(metrics.get("pairsPass") or metrics.get("totalPairs")),
        }
        # map verdict language
        v = str(flat["verdict"]).lower()
        if v in ("estacionar", "parked"):
            flat["verdict"] = "Incubate" if flat.get("profit_factor") and float(flat["profit_factor"] or 0) >= 1.3 else "Watchlist"
        elif v in ("rejeitar", "rejected"):
            flat["verdict"] = "Reject"
        elif v in ("aprovar", "candidate"):
            flat["verdict"] = "Candidate"
        if flat["verdict"] not in ("Candidate", "Incubate", "Watchlist", "Reject"):
            st = str(r.get("status") or "")
            flat["verdict"] = {"candidate": "Candidate", "incubate": "Incubate", "rejected": "Reject", "parked": "Watchlist"}.get(st, "Watchlist")
        flat["status"] = {
            "Candidate": "candidate",
            "Incubate": "incubate",
            "Watchlist": "watchlist",
            "Reject": "rejected",
        }[flat["verdict"]]
        # keep extra metrics blob for panel detail
        if metrics:
            flat["extra"] = metrics
        out.append(flat)
    return out


def main() -> int:
    data_path = DASH / "data.json"
    current = json.loads(data_path.read_text(encoding="utf-8"))
    raw_strategies = current.get("strategies") or []
    if isinstance(raw_strategies, dict):
        current_rows = []
        for k, v in raw_strategies.items():
            if isinstance(v, dict):
                row = dict(v)
                row.setdefault("name", k)
                row.setdefault("id", re.sub(r"[^a-z0-9]+", "-", k.lower()).strip("-"))
                current_rows.append(row)
    else:
        current_rows = [r for r in raw_strategies if isinstance(r, dict)]
    live = [r for r in current_rows if r.get("id") and str(r.get("id")).startswith("b4-")]
    legacy = [r for r in current_rows if r not in live]

    report_rows = load_report_rows()
    # dedupe report rows by id
    seen = set()
    deduped = []
    for r in report_rows:
        r = enrich(r)
        if r["id"] in seen:
            # prefer higher trades / non-empty
            continue
        seen.add(r["id"])
        deduped.append(r)

    live_n = [enrich(dict(r)) for r in live]
    legacy_n = normalize_legacy(legacy)
    for r in legacy_n:
        enrich(r)

    # merge: live b4 by id > report by id > legacy by id
    by_id: dict[str, dict] = {}
    for r in deduped:
        by_id[r["id"]] = r
    for r in legacy_n:
        by_id[r["id"]] = r
    for r in live_n:
        # live wins (has curve)
        by_id[r["id"]] = r

    # family rollups from report+live
    pool = list(by_id.values())
    rollups = family_rollups(live_n + [r for r in pool if not r.get("is_rollup")], [])
    # dedupe rollup ids
    for ru in rollups:
        by_id[ru["id"]] = ru

    merged = list(by_id.values())
    # stable sort: rollups first? no — cards mixed; sort by verdict quality then pf
    rank = {"Candidate": 0, "Incubate": 1, "Watchlist": 2, "Reject": 3}
    merged.sort(key=lambda r: (0 if r.get("is_rollup") else 1, rank.get(r.get("verdict"), 9), -(r.get("profit_factor") or 0)))

    stats = {
        "total": len(merged),
        "detail_rows": sum(1 for r in merged if not r.get("is_rollup")),
        "rollups": sum(1 for r in merged if r.get("is_rollup")),
        "live_curves": sum(1 for r in merged if r.get("curve")),
        "local": sum(1 for r in merged if str(r.get("source", "")).startswith(("discovery", "report", "b4", "high", "batch")) or r.get("source") in ("discovery-bull", "legacy-decision")),
        "leaderboard": sum(1 for r in merged if r.get("source") == "leaderboard"),
        "candidates": sum(1 for r in merged if r.get("verdict") == "Candidate"),
        "incubate": sum(1 for r in merged if r.get("verdict") == "Incubate"),
        "watchlist": sum(1 for r in merged if r.get("verdict") == "Watchlist"),
        "rejected": sum(1 for r in merged if r.get("verdict") == "Reject"),
        "errors": current.get("stats", {}).get("errors", 0),
    }

    data = {
        "updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "window": {"from": "2025-01-01", "to": "2026-09-01", "engine": "tv_jul26"},
        "stats": stats,
        "strategies": merged,
        "agents": sorted({r.get("agent") or "unknown" for r in merged}),
        "families": sorted({r.get("family") or "unknown" for r in merged}),
        "credits_note": "get_credits antes de novos lotes",
        "txflow": {
            "status": "research",
            "sdk": "txflow-sdk (npm) + MCP server",
            "docs": "docs.txflow.com",
            "venue": "perp DEX L1 · CLOB on-chain",
            "gate": "human approval required — no auto orders",
        },
    }
    data_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    (DASH / "data.js").write_text(
        "window.MISSION_DATA = " + json.dumps(data, ensure_ascii=False) + ";\n",
        encoding="utf-8",
    )
    print("rows", len(merged), "stats", json.dumps(stats))
    # top families
    fams = [r for r in merged if r.get("is_rollup")]
    fams.sort(key=lambda r: (-(r.get("pairs_pass") or 0), -(r.get("profit_factor") or 0)))
    for f in fams[:8]:
        print(" fam", f["family"], f.get("pairs_pass"), "/", f.get("pairs_total"), "PF", f.get("profit_factor"), f.get("verdict"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
