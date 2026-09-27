#!/usr/bin/env python3
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

with open('dashboard/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Check all $(...) calls in script
script_matches = re.findall(r'<script\b[^>]*>([\s\S]*?)</script>', html, re.IGNORECASE)
app_script = script_matches[-1] if script_matches else ""

# Find all document.getElementById or $("...")
id_calls = re.findall(r'\$\(["\']([^"\']+)["\']\)', app_script)
id_calls += re.findall(r'document\.getElementById\(["\']([^"\']+)["\']\)', app_script)

unique_ids = sorted(set(id_calls))
missing_ids = []
for el_id in unique_ids:
    if f'id="{el_id}"' not in html and f"id='{el_id}'" not in html:
        missing_ids.append(el_id)

print(f"Total Unique IDs referenced in JS: {len(unique_ids)}")
print(f"Missing IDs count: {len(missing_ids)}")
if missing_ids:
    print("Missing IDs:", missing_ids)
else:
    print("ALL ELEMENT IDS EXIST IN HTML!")
