"""Restore dashboard/data.json from the data.js backup + merge rows the
researcher cycle wrote at 14:46 (it overwrote data.json with only 8 rows).

- backup source: dashboard/data.js (window.MISSION_DATA = {...})
- new rows: current dashboard/data.json (8 rows, cycle 06)
- dedupe by id (new rows win), recompute stats, write data.json + data.js.
"""
from __future__ import annotations

import json
import re
import shutil
from datetime import datetime
from pathlib import Path

DASH = Path(r"C:\Users\seares\Desktop\botrade\dashboard")
DATA_JS = DASH / "data.js"
DATA_JSON = DASH / "data.json"


def load_js() -> dict:
    txt = DATA_JS.read_text(encoding="utf-8")
    m = re.match(r"\s*window\.MISSION_DATA\s*=\s*(.*)$", txt, re.S)
    if not m:
        raise SystemExit("data.js: formato inesperado")
    body = m.group(1).strip()
    if body.endswith(";"):
        body = body[:-1].rstrip()
    return json.loads(body)


def recompute(stats: dict, rows: list[dict]) -> dict:
    detail = [r for r in rows if not r.get("is_rollup")]
    stats = dict(stats)
    stats["total"] = len(rows)
    stats["detail_rows"] = len(detail)
    stats["rollups"] = len(rows) - len(detail)
    stats["candidates"] = sum(1 for r in rows if r.get("verdict") == "Candidate")
    stats["incubate"] = sum(1 for r in rows if r.get("verdict") == "Incubate")
    stats["watchlist"] = sum(1 for r in rows if r.get("verdict") == "Watchlist")
    stats["rejected"] = sum(1 for r in rows if r.get("verdict") == "Reject")
    curves = sum(
        1
        for r in rows
        if isinstance(r.get("curve"), list)
        and len(r["curve"]) > 1
        and isinstance(r["curve"][0], dict)
    )
    stats["live_curves"] = curves
    return stats


def main() -> int:
    backup = load_js()
    current = json.loads(DATA_JSON.read_text(encoding="utf-8"))
    print(f"backup (data.js): {len(backup.get('strategies', []))} rows, updated {backup.get('updated')}")
    print(f"atual (data.json): {len(current.get('strategies', []))} rows, updated {current.get('updated')}")

    if len(backup.get("strategies", [])) >= len(current.get("strategies", [])):
        # keep backup as base, current rows win on id collision
        rows = {r.get("id"): r for r in backup.get("strategies", []) if r.get("id")}
        for r in current.get("strategies", []):
            if r.get("id"):
                rows[r.get("id")] = r
        merged = list(rows.values())
        stats_src = backup.get("stats", {})
    else:
        # data.js is stale; keep current as base and warn
        rows = {r.get("id"): r for r in current.get("strategies", []) if r.get("id")}
        for r in backup.get("strategies", []):
            rows.setdefault(r.get("id"), r)
        merged = list(rows.values())
        stats_src = current.get("stats", {})
        print("AVISO: data.js parece mais antigo que data.json")

    out = {
        "updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "stats": recompute(stats_src, merged),
        "strategies": merged,
    }
    for k in ("engine", "window", "timeframe", "note", "symbols"):
        for src in (backup, current):
            if k in src and k not in out:
                out[k] = src[k]

    shutil.copy2(DATA_JSON, DATA_JSON.with_suffix(".json.bak-8rows"))
    DATA_JSON.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    embedded = json.dumps(out, ensure_ascii=False)
    DATA_JS.write_text("window.MISSION_DATA = " + embedded + ";\n", encoding="utf-8")
    print(f"restaurado: {len(merged)} rows | stats {out['stats']}")
    print(f"data.json + data.js gravados (backup do estado ruim: data.json.bak-8rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
