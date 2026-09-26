#!/usr/bin/env python3
"""Extrai todos os blocos fenced do relatório e mostra detalhes."""
from __future__ import annotations
import json, re, sys
from pathlib import Path

ROOT = Path(r"C:\Users\seares\Desktop\botrade")
report = ROOT / "data/reports/2026-09-26-1530-researcher-h2-h1-greenfield.md"
txt = report.read_text(encoding="utf-8")

for i, m in enumerate(re.finditer(r"```(?:json)?\s*\n(.*?)```", txt, re.S)):
    block = m.group(1)
    print(f"--- Bloco {i} ---", file=sys.stderr)
    print(f"Payload type: {'dict' if block.startswith('{') else 'list' if block.startswith('[') else 'other'}", file=sys.stderr)
    print(f"Length: {len(block)} chars", file=sys.stderr)
    # Try to parse
    try:
        parsed = json.loads(block)
        print(f"Parsed OK: {type(parsed).__name__}", file=sys.stderr)
        if isinstance(parsed, dict):
            print(f"  keys: {list(parsed.keys())}", file=sys.stderr)
        elif isinstance(parsed, list):
            print(f"  list len: {len(parsed)}", file=sys.stderr)
            if parsed:
                print(f"  first item keys: {list(parsed[0].keys()) if isinstance(parsed[0], dict) else 'N/A'}", file=sys.stderr)
                for item in parsed:
                    if isinstance(item, dict) and item.get('id'):
                        print(f"  row: {item['id']}", file=sys.stderr)
    except json.JSONDecodeError as e:
        print(f"JSON error: {e}", file=sys.stderr)
    print(file=sys.stderr)

print("FIM", file=sys.stderr)
