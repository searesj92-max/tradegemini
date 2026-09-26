"""Merge local top40 rows into Mission Control dashboard (by id)."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"C:\Users\seares\Desktop\botrade")
sys.path.insert(0, str(ROOT / "scripts"))


def main() -> int:
    local_path = ROOT / "data" / "local" / "top40_local.json"
    if not local_path.exists():
        print("missing", local_path)
        return 1
    local = json.loads(local_path.read_text(encoding="utf-8"))
    local_rows = local.get("rows") or []
    for r in local_rows:
        # keep curves light
        if r.get("curve") and len(r["curve"]) > 40:
            r["curve"] = r["curve"][::2][:40]
        r.setdefault("source", "local-ohlcv")
        r.setdefault("agent", "local-engine")

    # family rollup local
    by = {}
    for r in local_rows:
        by.setdefault(r["family"], []).append(r)
    rollups = []
    for fam, rs in by.items():
        def ok(x):
            return (
                (x.get("profit_factor") or 0) >= 1.3
                and (x.get("max_drawdown_pct") or 99) <= 30
                and (x.get("trades") or 0) >= 40
                and (x.get("net_profit_pct") or 0) > 0
            )
        p = sum(1 for x in rs if ok(x))
        mpf = sum(x.get("profit_factor") or 0 for x in rs) / len(rs)
        mwr = sum(x.get("win_rate_pct") or 0 for x in rs) / len(rs)
        # cap absurd PF 999 for display mean? keep raw but note
        rollups.append({
            "id": f"locfam-{fam}",
            "name": f"[LOCAL40] {fam}",
            "symbol": f"{len(rs)} rows",
            "timeframe": "4h",
            "source": "local-rollup",
            "family": f"local-{fam}",
            "agent": "local-engine",
            "net_profit_pct": round(max(x.get("net_profit_pct") or 0 for x in rs), 2),
            "profit_factor": round(mpf, 3),
            "max_drawdown_pct": round(max(x.get("max_drawdown_pct") or 0 for x in rs), 2),
            "win_rate_pct": round(mwr, 2),
            "trades": sum(x.get("trades") or 0 for x in rs),
            "wins": sum(x.get("wins") or 0 for x in rs),
            "losses": sum(x.get("losses") or 0 for x in rs),
            "win_pct": round(mwr, 2),
            "loss_pct": round(100 - mwr, 2),
            "pairs_pass": p,
            "pairs_total": len(rs),
            "is_rollup": True,
            "last_backtest": "2026-09-23",
            "verdict": (
                "Candidate" if p >= 5 and mpf >= 1.3
                else ("Incubate" if p >= 3 else ("Watchlist" if p >= 1 or mpf >= 1.1 else "Reject"))
            ),
            "status": "candidate" if p >= 5 else "watchlist",
            "notes": f"top40 local · pass {p}/40 · meanPF {mpf:.2f} · meanWR {mwr:.1f}%",
            "pine_key": None,
            "curve": [],
            "sharpe": None,
            "avg_trade": None,
            "long_trades": None,
            "short_trades": None,
            "result_id": None,
            "view_url": None,
        })

    dpath = ROOT / "dashboard" / "data.json"
    d = json.loads(dpath.read_text(encoding="utf-8"))
    old = d.get("strategies") or []
    # drop previous local-ohlcv / local-rollup to avoid dupes on re-run
    old = [
        r for r in old
        if r.get("source") not in ("local-ohlcv", "local-rollup")
        and not str(r.get("id") or "").startswith("loc-")
        and not str(r.get("id") or "").startswith("locfam-")
    ]
    new_ids = {r["id"] for r in local_rows} | {r["id"] for r in rollups}
    merged = [r for r in old if r.get("id") not in new_ids] + rollups + local_rows

    rank = {"Candidate": 0, "Incubate": 1, "Watchlist": 2, "Reject": 3}
    merged.sort(key=lambda r: (0 if r.get("is_rollup") else 1, rank.get(r.get("verdict"), 9), -(r.get("profit_factor") or 0)))

    stats = {
        "total": len(merged),
        "detail_rows": sum(1 for r in merged if not r.get("is_rollup")),
        "rollups": sum(1 for r in merged if r.get("is_rollup")),
        "live_curves": sum(1 for r in merged if r.get("curve")),
        "local_ohlcv": sum(1 for r in merged if r.get("source") == "local-ohlcv"),
        "leaderboard": sum(1 for r in merged if r.get("source") == "leaderboard"),
        "candidates": sum(1 for r in merged if r.get("verdict") == "Candidate"),
        "incubate": sum(1 for r in merged if r.get("verdict") == "Incubate"),
        "watchlist": sum(1 for r in merged if r.get("verdict") == "Watchlist"),
        "rejected": sum(1 for r in merged if r.get("verdict") == "Reject"),
        "errors": 0,
        "credits_used_local": 0,
    }
    d["updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    d["generated_at"] = datetime.now(timezone.utc).isoformat()
    d["stats"] = stats
    d["strategies"] = merged
    d["agents"] = sorted({r.get("agent") or "unknown" for r in merged})
    d["families"] = sorted({r.get("family") or "unknown" for r in merged})
    d["local"] = {
        "source": "binance+bybit free klines",
        "combos": len(local_rows),
        "report": "data/reports/2026-09-23-1944-local-top40.md",
        "universe": local.get("universe"),
    }
    dpath.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    (ROOT / "dashboard" / "data.js").write_text(
        "window.MISSION_DATA = " + json.dumps(d, ensure_ascii=False) + ";\n",
        encoding="utf-8",
    )
    print("merged", len(merged), "stats", stats)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
