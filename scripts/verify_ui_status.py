#!/usr/bin/env python3
"""Automated verification script for Botrade Dashboard UI and Headers."""
import urllib.request
import sys

def verify():
    url = "http://localhost:8765/"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "BotradeVerification/1.0"})
        resp = urllib.request.urlopen(req, timeout=5)
    except Exception as e:
        print(f"[FAIL] Could not connect to {url}: {e}")
        sys.exit(1)

    print(f"[OK] Status Code: {resp.status}")
    
    # Verify Cache-Control headers
    cc = resp.headers.get("Cache-Control", "")
    pragma = resp.headers.get("Pragma", "")
    expires = resp.headers.get("Expires", "")
    
    print(f"[INFO] Cache-Control: {cc}")
    print(f"[INFO] Pragma: {pragma}")
    print(f"[INFO] Expires: {expires}")
    
    if "no-cache" not in cc or "no-store" not in cc:
        print("[FAIL] Anti-cache headers missing!")
        sys.exit(1)
    print("[OK] Anti-cache headers verified.")

    # Verify content
    html = resp.read().decode("utf-8")
    
    has_pine = 'data-tab="pine"' in html
    has_families = 'data-tab="families"' in html
    has_cockpit = 'data-tab="cockpit"' in html
    has_backtest_lab = 'data-tab="backtest-lab"' in html
    has_universe = 'data-tab="universe"' in html
    has_live = 'data-tab="live"' in html
    has_explorer = 'data-tab="explorer"' in html

    print(f"[CHECK] Has Pine tab: {has_pine} (expected: False)")
    print(f"[CHECK] Has Families tab: {has_families} (expected: False)")
    print(f"[CHECK] Has Cockpit: {has_cockpit} (expected: True)")
    print(f"[CHECK] Has Backtest Lab: {has_backtest_lab} (expected: True)")
    print(f"[CHECK] Has Universe: {has_universe} (expected: True)")
    print(f"[CHECK] Has Live: {has_live} (expected: True)")
    print(f"[CHECK] Has Explorer: {has_explorer} (expected: True)")

    if has_pine or has_families:
        print("[FAIL] Legacy tabs still found in HTML!")
        sys.exit(1)

    if not (has_cockpit and has_backtest_lab and has_universe and has_live and has_explorer):
        print("[FAIL] Missing one or more of the 5 core tabs!")
        sys.exit(1)

    print("\n[SUCCESS] ALL VERIFICATION CHECKS PASSED PERFECTLY!")

if __name__ == "__main__":
    verify()
