"""Safe panel merge — the ONLY supported way for agents to update the panel.

Usage (never write dashboard/data.json by hand):

    python scripts/panel_upsert.py --rows rows.json
    python scripts/panel_upsert.py --report data/reports/2026-09-24-1745-researcher-foo.md

rules.json / rows.json = array of strategy row objects (or one object).
Merges by `id` (new wins on collision), keeps every other row, recomputes
stats, writes data.json + data.js atomically.

Why: agents used to rewrite data.json wholesale and wiped 731 rows down to 8.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
from datetime import datetime
from pathlib import Path

ROOT = Path(r"C:\Users\seares\Desktop\botrade")
DASH = ROOT / "dashboard"
DATA_JSON = DASH / "data.json"
DATA_JS = DASH / "data.js"


def load_current() -> dict:
    if DATA_JSON.exists():
        try:
            return json.loads(DATA_JSON.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    # fallback: data.js embedded copy
    txt = DATA_JS.read_text(encoding="utf-8")
    m = re.match(r"\s*window\.MISSION_DATA\s*=\s*(.*)$", txt, re.S)
    body = m.group(1).strip()
    if body.endswith(";"):
        body = body[:-1].rstrip()
    return json.loads(body)


def recompute(stats: dict, rows: list[dict]) -> dict:
    detail = [r for r in rows if not r.get("is_rollup")]
    out = dict(stats or {})
    out["total"] = len(rows)
    out["detail_rows"] = len(detail)
    out["rollups"] = len(rows) - len(detail)
    for key, verd in (
        ("candidates", "Candidate"),
        ("incubate", "Incubate"),
        ("watchlist", "Watchlist"),
        ("rejected", "Reject"),
    ):
        out[key] = sum(1 for r in rows if str(r.get("verdict") or "").startswith(verd))
    out["live_curves"] = sum(
        1
        for r in rows
        if isinstance(r.get("curve"), list)
        and len(r["curve"]) > 1
        and isinstance(r["curve"][0], dict)
    )
    return out


def merge(rows_in: list[dict]) -> tuple[int, int]:
    cur = load_current()
    before = len(cur.get("strategies", []))
    index = {r.get("id"): r for r in cur.get("strategies", []) if r.get("id")}
    added = 0
    for r in rows_in:
        rid = r.get("id")
        if not rid:
            sym = r.get("symbol") or "NA"
            tf = r.get("timeframe") or "na"
            key = re.sub(r"[^a-z0-9]+", "-", (r.get("name") or "x").lower()).strip("-")
            r = dict(r, id=f"{key}-{sym}-{tf}")
            rid = r["id"]
        if rid not in index:
            added += 1
        index[rid] = r
    merged = list(index.values())
    out = {
        "updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "stats": recompute(cur.get("stats", {}), merged),
        "strategies": merged,
    }
    for k in ("engine", "window", "timeframe", "note", "generated_at"):
        if k in cur:
            out[k] = cur[k]

    tmp = DATA_JSON.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    shutil.copy2(DATA_JSON, DATA_JSON.with_suffix(".json.bak"))
    os.replace(tmp, DATA_JSON)
    DATA_JS.write_text(
        "window.MISSION_DATA = " + json.dumps(out, ensure_ascii=False) + ";\n",
        encoding="utf-8",
    )
    print(f"panel_upsert: {before} -> {len(merged)} rows (+{added} novas) | stats {out['stats']}")
    return before, len(merged)


def rows_from_report(path: Path) -> list[dict]:
    txt = path.read_text(encoding="utf-8")
    # look for fenced json blocks containing a strategies array or row objects
    out: list[dict] = []
    for m in re.finditer(r"```(?:json)?\s*\n(.*?)```", txt, re.S):
        try:
            payload = json.loads(m.group(1))
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict) and isinstance(payload.get("strategies"), list):
            out.extend(payload["strategies"])
        elif isinstance(payload, dict) and payload.get("id"):
            out.append(payload)
        elif isinstance(payload, list):
            out.extend(x for x in payload if isinstance(x, dict) and (x.get("id") or x.get("name")))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", help="path to JSON file: array of rows or object with strategies[]")
    ap.add_argument("--report", help="path to a report .md (reads fenced JSON rows)")
    args = ap.parse_args()
    rows: list[dict] = []
    if args.rows:
        payload = json.loads(Path(args.rows).read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            rows = payload.get("strategies") or ([payload] if payload.get("id") else [])
        else:
            rows = [x for x in payload if isinstance(x, dict)]
    elif args.report:
        rows = rows_from_report(Path(args.report))
    else:
        ap.error("use --rows or --report")
    if not rows:
        print("nenhuma row encontrada — nada a fazer")
        return 1
    merge(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
