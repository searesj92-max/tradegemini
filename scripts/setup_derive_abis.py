#!/usr/bin/env python3
"""
Setup helper to ensure derive_py has the required Ethereum ABIs on cloud deployment.
Copies directly from the repository's bundled derive_data directory.
"""
import os
import shutil
from pathlib import Path

def setup_abis():
    try:
        import derive_py
        pkg_dir = Path(derive_py.__file__).parent
        target_dir = pkg_dir / "data"
        target_dir.mkdir(parents=True, exist_ok=True)
        
        manifest_file = target_dir / "abis" / "ethereum" / "contracts.json"
        
        repo_root = Path(__file__).resolve().parent.parent
        src_data = repo_root / "derive_data"
        
        if src_data.exists():
            print(f"[ABIs] Copying bundled derive_data from {src_data} to {target_dir}...")
            shutil.copytree(src_data, target_dir, dirs_exist_ok=True)
            print("[ABIs] Bundled ABIs installed successfully.")
        else:
            print("[ABIs Warning] Local derive_data folder not found!")
            
        if manifest_file.exists():
            print(f"[ABIs] Verified: {manifest_file} is present and ready.")
        else:
            print(f"[ABIs Warning] contracts.json is still missing at {manifest_file}")
            
    except Exception as e:
        print(f"[ABIs Error] Failed to setup ABIs: {e}")

if __name__ == "__main__":
    setup_abis()
