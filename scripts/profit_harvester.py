#!/usr/bin/env python3
"""
Botrade Autonomous Profit Harvester (Auto Take-Profit & Margin Unlocker)
Watches all live positions every 5 seconds.
When any position reaches ROE >= +10.0% (or profit >= +$2.50):
1. Immediately executes a 50% partial market sell.
2. Embezzles cash into free margin balance.
3. Automatically sets the Stop Loss of the remaining 50% to Breakeven (0x0).
4. Dispatches celebratory Telegram notification.
5. Releases margin so the Auto Sniper can immediately take the next trade!
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Fix Windows console encoding
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from hyperliquid_executor import HyperliquidExecutor

HARVEST_STATE_FILE = ROOT / "data" / "journal" / "harvested_positions.json"


def load_harvest_state() -> dict:
    if HARVEST_STATE_FILE.exists():
        try:
            return json.loads(HARVEST_STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def save_harvest_state(state: dict):
    HARVEST_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    HARVEST_STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def check_and_harvest(min_roe: float = 10.0, min_pnl_usd: float = 2.50, executor: HyperliquidExecutor = None) -> list[dict]:
    """Inspects all open positions. If any meets profit threshold and hasn't been harvested yet, executes 50% partial close."""
    if executor is None:
        executor = HyperliquidExecutor()

    try:
        status = executor.get_account_status()
    except Exception as e:
        print(f"[-] Erro ao consultar conta para harvest: {e}")
        return []

    open_pos = status.get("open_positions", [])
    harvest_state = load_harvest_state()
    active_coins = {p["coin"] for p in open_pos}

    # Clean up state for positions that are no longer open (closed by TP2 or SL)
    cleaned = False
    for saved_coin in list(harvest_state.keys()):
        if saved_coin not in active_coins:
            del harvest_state[saved_coin]
            cleaned = True
    if cleaned:
        save_harvest_state(harvest_state)

    results = []
    for pos in open_pos:
        coin = pos["coin"]
        roe = float(pos.get("roe_pct", 0.0))
        pnl = float(pos.get("unrealized_pnl", 0.0))
        size = float(pos.get("size", 0.0))

        # Check if already harvested
        if coin in harvest_state:
            continue

        # Condition: ROE >= 10.0% OR PnL >= $2.50
        if roe >= min_roe or pnl >= min_pnl_usd:
            print(f"\n[💰 PROFIT HARVESTER] ALVO ATINGIDO PARA {coin}!")
            print(f"    ROE: +{roe:.2f}% | PnL: +${pnl:.4f} | Lote: {size} tokens")
            print(f"    🚀 Disparando realização automática de 50% e movendo Stop Loss para Breakeven...")

            res = executor.close_partial_position(coin=coin, pct=0.5, move_sl_to_be=True)
            if res.get("status") == "partial_closed":
                harvest_state[coin] = {
                    "harvested_at": datetime.now(timezone.utc).isoformat(),
                    "realized_pnl": res.get("realized_pnl"),
                    "roe_at_harvest": roe,
                    "remaining_size": res.get("remaining_size")
                }
                save_harvest_state(harvest_state)
                results.append(res)
                print(f"    ✅ Sucesso: +${res.get('realized_pnl', 0):.2f} embolsados e margem liberada na Hyperliquid!")
            else:
                print(f"    [-] Falha na realização parcial: {res.get('message')}")

    return results


def run_harvester_loop(interval_sec: int = 5, min_roe: float = 10.0, min_pnl_usd: float = 2.50):
    print("=" * 65)
    print("💰 BOTRADE AUTONOMOUS PROFIT HARVESTER INICIADO")
    print(f"[*] Meta de Realização Parcial: +{min_roe:.1f}% ROE ou +${min_pnl_usd:.2f} PnL")
    print(f"[*] Ação: Venda a mercado de 50% + Trava de SL no 0x0 (Breakeven)")
    print(f"[*] Intervalo de Monitoramento: {interval_sec}s")
    print("=" * 65)

    executor = HyperliquidExecutor()
    while True:
        try:
            check_and_harvest(min_roe=min_roe, min_pnl_usd=min_pnl_usd, executor=executor)
        except Exception as e:
            print(f"[Aviso Harvester] {e}")
        time.sleep(interval_sec)


if __name__ == "__main__":
    run_harvester_loop()
