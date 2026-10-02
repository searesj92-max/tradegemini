#!/usr/bin/env python3
"""
Botrade Institutional High-Asymmetry Profit Harvester (80/20 Strategy + Early Risk-Free)
Watches all live positions continuously.

Dual-Stage Execution Engine:
1. Stage 1 (Risco Zero Robusto @ +35.0% ROE):
   - Raises Stop Loss to Breakeven (+0.6% cushion covering all exchange fees + real profit).
   - Guarantees trade can NEVER become a loss or fee trap once it reached +35% ROE.

2. Stage 2 (Realização Parcial 50/50 @ +45.0% ROE):
   - Executes a 50% partial market sell (locks in +$4.50+ on $20 margin).
   - Keeps remaining 50% safely above Hyperliquid's $10 minimum order requirement.
   - Locks Stop Loss of the remaining 50% runner at Breakeven (+0.6%), letting it trail freely.
   - Releases margin so the Auto Sniper can immediately take the next high-confluence trade!
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


def check_and_harvest(
    min_roe_risk_free: float = 35.0,
    min_roe_harvest: float = 45.0,
    min_pnl_usd: float = 8.00,
    executor: HyperliquidExecutor = None
) -> list[dict]:
    """Inspects all open positions.
    1. At +35% ROE -> moves SL to Breakeven (+0.6% cushion) for robust fee-free status.
    2. At +45% ROE -> executes 50% partial close and protects remaining 50% runner.
    """
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

    # Clean up state for positions that are no longer open
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

        coin_record = harvest_state.get(coin, {})

        # ----------------------------------------------------
        # STAGE 1: RISCO ZERO ROBUSTO (+35% ROE)
        # ----------------------------------------------------
        if roe >= min_roe_risk_free and not coin_record.get("risk_free"):
            print(f"\n[🛡️ RISCO ZERO ROBUSTO] {coin} atingiu +{roe:.2f}% ROE!")
            print(f"    🚀 Elevando Stop Loss para Breakeven (+0.6% anti-taxas com lucro real)...")
            be_res = executor.move_sl_to_breakeven(coin=coin, cushion_pct=0.6)
            if be_res.get("status") == "ok":
                coin_record["risk_free"] = True
                coin_record["risk_free_at"] = datetime.now(timezone.utc).isoformat()
                coin_record["risk_free_sl"] = be_res.get("new_sl")
                harvest_state[coin] = coin_record
                save_harvest_state(harvest_state)
                print(f"    ✅ Sucesso: Stop Loss de {coin} travado no breakeven protetor (${be_res.get('new_sl')})!")
            else:
                print(f"    [-] Falha ao mover SL: {be_res.get('message')}")

        # ----------------------------------------------------
        # STAGE 2: REALIZAÇÃO PARCIAL 50/50 (+45% ROE)
        # ----------------------------------------------------
        if (roe >= min_roe_harvest or pnl >= min_pnl_usd) and not coin_record.get("harvested_50"):
            print(f"\n[💰 50/50 PROFIT HARVESTER] ALVO DE +45% ATINGIDO PARA {coin}!")
            print(f"    ROE: +{roe:.2f}% | PnL: +${pnl:.4f} | Lote: {size} tokens")
            print(f"    🚀 Disparando realização automática de 50% e protegendo 50% runner...")

            res = executor.close_partial_position(coin=coin, pct=0.50, move_sl_to_be=True)
            if res.get("status") == "partial_closed":
                coin_record["harvested_50"] = True
                coin_record["harvested_at"] = datetime.now(timezone.utc).isoformat()
                coin_record["realized_pnl"] = res.get("realized_pnl")
                coin_record["roe_at_harvest"] = roe
                coin_record["remaining_size"] = res.get("remaining_size")
                harvest_state[coin] = coin_record
                save_harvest_state(harvest_state)
                results.append(res)
                print(f"    ✅ Sucesso: +${res.get('realized_pnl', 0):.2f} embolsados no bolso e margem liberada na Hyperliquid!")
            else:
                print(f"    [-] Falha na realização parcial: {res.get('message')}")

    return results


def run_harvester_loop(interval_sec: int = 5, min_roe_risk_free: float = 35.0, min_roe_harvest: float = 45.0):
    print("=" * 70)
    print("💰 BOTRADE INSTITUTIONAL PROFIT HARVESTER (50/50 STRATEGY)")
    print(f"[*] Estágio 1 (Risco Zero Robusto):    +{min_roe_risk_free:.1f}% ROE -> SL no 0x0 (+0.6%)")
    print(f"[*] Estágio 2 (Realização Parcial):     +{min_roe_harvest:.1f}% ROE -> Venda de 50%")
    print(f"[*] Runner Residual: 50% surfando com Trailing Stop sem risco")
    print(f"[*] Intervalo de Monitoramento: {interval_sec}s")
    print("=" * 70)

    executor = HyperliquidExecutor()
    while True:
        try:
            check_and_harvest(
                min_roe_risk_free=min_roe_risk_free,
                min_roe_harvest=min_roe_harvest,
                executor=executor
            )
        except Exception as e:
            print(f"[Aviso Harvester] {e}")
        time.sleep(interval_sec)


if __name__ == "__main__":
    run_harvester_loop()
