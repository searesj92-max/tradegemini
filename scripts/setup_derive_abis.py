#!/usr/bin/env python3
"""
Setup helper to ensure derive_py has the required Ethereum ABIs on cloud deployment.
"""
import os
import urllib.request
import json

def setup_abis():
    try:
        import derive_py
        pkg_dir = os.path.dirname(derive_py.__file__)
        target_dir = os.path.join(pkg_dir, "data", "abis", "ethereum")
        os.makedirs(target_dir, exist_ok=True)
        
        manifest_file = os.path.join(target_dir, "contracts.json")
        if os.path.exists(manifest_file):
            print("[ABIs] Ethereum ABIs already present.")
            return

        print("[ABIs] Downloading missing Ethereum ABIs from GitHub...")
        raw_base = "https://raw.githubusercontent.com/derivexyz/derive-py/main/"
        req = urllib.request.Request(
            "https://api.github.com/repos/derivexyz/derive-py/git/trees/main?recursive=1",
            headers={"User-Agent": "Mozilla/5.0"}
        )
        tree = json.loads(urllib.request.urlopen(req, timeout=15).read().decode("utf-8"))
        eth_files = [item["path"] for item in tree.get("tree", []) if item["path"].startswith("derive_py/data/abis/ethereum/")]

        for fpath in eth_files:
            fname = os.path.basename(fpath)
            dest = os.path.join(target_dir, fname)
            url = raw_base + fpath
            content = urllib.request.urlopen(url, timeout=15).read()
            with open(dest, "wb") as f:
                f.write(content)
        print(f"[ABIs] {len(eth_files)} ABI files installed successfully.")
    except Exception as e:
        print(f"[ABIs Warning] Failed to download ABIs: {e}")

if __name__ == "__main__":
    setup_abis()
