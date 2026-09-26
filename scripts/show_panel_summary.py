"""Print a clear strategy % summary from dashboard/data.json (and optionally refresh)."""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"C:\Users\seares\Desktop\botrade")
DASH = ROOT / "dashboard"


def main() -> int:
    # light refresh: ensure data.js embeds latest data.json
    d = json.loads((DASH / "data.json").read_text(encoding="utf-8"))
    (DASH / "data.js").write_text(
        "window.MISSION_DATA = " + json.dumps(d, ensure_ascii=False) + ";\n",
        encoding="utf-8",
    )
    rows = d.get("strategies") or []
    det = [r for r in rows if not r.get("is_rollup")]
    print(f"PAINEL {DASH / 'index.html'}")
    print(f"updated={d.get('updated')} total={len(rows)} detail={len(det)} rollups={len(rows)-len(det)}")
    print("verdicts", dict(Counter(r.get("verdict") for r in det)))

    def g(r, k, default=0.0):
        v = r.get(k)
        return default if v is None else v

    print()
    print("=== CANDIDATES ===")
    print(
        f"{'family':14s} {'symbol':12s} {'tf':4s} "
        f"{'net%':>9} {'PF':>7} {'DD%':>7} {'WR%':>7} {'N':>5} {'W':>4} {'L':>4} src"
    )
    cands = sorted(
        [r for r in det if r.get("verdict") == "Candidate"],
        key=lambda r: -g(r, "profit_factor"),
    )
    for r in cands[:40]:
        print(
            f"{(r.get('family') or '?'):14s} {(r.get('symbol') or '?'):12s} "
            f"{(r.get('timeframe') or '?'):4s} {g(r,'net_profit_pct'):9.2f} "
            f"{g(r,'profit_factor'):7.2f} {g(r,'max_drawdown_pct'):7.2f} "
            f"{g(r,'win_rate_pct'):7.1f} {int(g(r,'trades')):5d} "
            f"{int(g(r,'wins')):4d} {int(g(r,'losses')):4d} {r.get('source','')[:14]}"
        )

    print()
    print("=== INCUBATE (top 30 by PF) ===")
    print(
        f"{'family':14s} {'symbol':12s} {'tf':4s} "
        f"{'net%':>9} {'PF':>7} {'DD%':>7} {'WR%':>7} {'N':>5} src"
    )
    inc = sorted(
        [r for r in det if r.get("verdict") == "Incubate"],
        key=lambda r: -g(r, "profit_factor"),
    )
    for r in inc[:30]:
        print(
            f"{(r.get('family') or '?'):14s} {(r.get('symbol') or '?'):12s} "
            f"{(r.get('timeframe') or '?'):4s} {g(r,'net_profit_pct'):9.2f} "
            f"{g(r,'profit_factor'):7.2f} {g(r,'max_drawdown_pct'):7.2f} "
            f"{g(r,'win_rate_pct'):7.1f} {int(g(r,'trades')):5d} {r.get('source','')[:14]}"
        )

    print()
    print("=== FAMILY SUMMARY (all detail rows) ===")
    by = defaultdict(list)
    for r in det:
        by[r.get("family") or "unknown"].append(r)
    print(
        f"{'family':14s} {'n':>4} {'C':>3} {'I':>3} {'W':>4} {'R':>4} "
        f"{'passN':>5} {'meanPF':>7} {'meanWR%':>8} {'meanNet%':>9} {'bestNet%':>9}"
    )
    fam_lines = []
    for f, rs in by.items():
        def mean(k):
            xs = [g(x, k) for x in rs]
            return sum(xs) / len(xs) if xs else 0.0
        c = sum(1 for x in rs if x.get("verdict") == "Candidate")
        i = sum(1 for x in rs if x.get("verdict") == "Incubate")
        w = sum(1 for x in rs if x.get("verdict") == "Watchlist")
        j = sum(1 for x in rs if x.get("verdict") == "Reject")
        passn = sum(
            1
            for x in rs
            if g(x, "profit_factor") >= 1.3
            and g(x, "max_drawdown_pct", 99) <= 30
            and g(x, "trades") >= 40
            and g(x, "net_profit_pct") > 0
        )
        best = max(g(x, "net_profit_pct") for x in rs) if rs else 0
        rec = (c + i, passn, c, i, w, j, mean("profit_factor"), mean("win_rate_pct"),
               mean("net_profit_pct"), best, len(rs), f)
        fam_lines.append(rec)
    fam_lines.sort(reverse=True)
    for score, passn, c, i, w, j, mpf, mwr, mnet, best, n, f in fam_lines:
        print(
            f"{f:14s} {n:4d} {c:3d} {i:3d} {w:4d} {j:4d} {passn:5d} "
            f"{mpf:7.2f} {mwr:8.1f} {mnet:9.1f} {best:9.1f}"
        )

    print()
    print("=== ROLLUPS ===")
    for r in rows:
        if not r.get("is_rollup"):
            continue
        print(
            f"{(r.get('name') or '?'):48s} pass={r.get('pairs_pass')}/{r.get('pairs_total')} "
            f"PF={r.get('profit_factor')} WR={r.get('win_rate_pct')} "
            f"v={r.get('verdict')} src={r.get('source')}"
        )

    # markdown for easy viewing
    lines = [
        "# Mission Control — resumo de estratégias (%)",
        "",
        f"Atualizado: {d.get('updated')} · rows={len(rows)} (detail={len(det)})",
        "",
        "## Candidates",
        "",
        "| Family | Símbolo | TF | Net% | PF | DD% | WR% | Trades | Origem |",
        "|---|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for r in cands:
        lines.append(
            f"| {r.get('family')} | {r.get('symbol')} | {r.get('timeframe')} | "
            f"{g(r,'net_profit_pct'):.2f} | {g(r,'profit_factor'):.2f} | "
            f"{g(r,'max_drawdown_pct'):.2f} | {g(r,'win_rate_pct'):.1f} | "
            f"{int(g(r,'trades'))} | {r.get('source')} |"
        )
    lines += [
        "",
        "## Incubate (top 30)",
        "",
        "| Family | Símbolo | TF | Net% | PF | DD% | WR% | Trades | Origem |",
        "|---|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for r in inc[:30]:
        lines.append(
            f"| {r.get('family')} | {r.get('symbol')} | {r.get('timeframe')} | "
            f"{g(r,'net_profit_pct'):.2f} | {g(r,'profit_factor'):.2f} | "
            f"{g(r,'max_drawdown_pct'):.2f} | {g(r,'win_rate_pct'):.1f} | "
            f"{int(g(r,'trades'))} | {r.get('source')} |"
        )
    lines += [
        "",
        "## Famílias",
        "",
        "| Family | N | C | I | W | R | passN | meanPF | meanWR% | meanNet% | bestNet% |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for score, passn, c, i, w, j, mpf, mwr, mnet, best, n, f in fam_lines:
        lines.append(
            f"| {f} | {n} | {c} | {i} | {w} | {j} | {passn} | "
            f"{mpf:.2f} | {mwr:.1f} | {mnet:.1f} | {best:.1f} |"
        )
    lines += ["", f"Arquivo: `{DASH / 'index.html'}` (aberto no navegador).", ""]
    out = DASH / "resumo-estrategias.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("wrote", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
