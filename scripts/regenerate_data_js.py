#!/usr/bin/env python3
"""Regenerate dashboard/data.js from dashboard/data.json."""

import json
import datetime
from pathlib import Path

ROOT = Path(r"C:\Users\seares\Desktop\botrade")
data_json = ROOT / "dashboard" / "data.json"
data_js = ROOT / "dashboard" / "data.js"

with open(data_json, "r", encoding="utf-8") as f:
    data = json.load(f)

embedded = json.dumps(data, ensure_ascii=False)
data_js.write_text("window.MISSION_DATA = " + embedded + ";\n", encoding="utf-8")

print(f"Regenerated {data_js}")
print(f"JSON size: {len(embedded)} chars")
print(f"Strategy count: {len(data['strategies'])}")
print(f"Updated: {data.get('updated', 'unknown')}")
