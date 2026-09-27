#!/usr/bin/env python3
import sys

sys.stdout.reconfigure(encoding="utf-8")

with open('dashboard/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print("--- TABS (BUTTONS) ---")
for i, l in enumerate(lines):
    if 'class="nav-tab' in l or 'data-tab=' in l:
        print(f"L{i+1}: {l.strip()}")

print("\n--- TAB-VIEWS (DIVS) ---")
for i, l in enumerate(lines):
    if 'id="tab-' in l:
        print(f"L{i+1}: {l.strip()}")
