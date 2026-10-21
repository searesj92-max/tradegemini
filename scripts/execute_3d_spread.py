import sys
from pathlib import Path
import json
import time

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from options_desk import (
    place_derive_spread_order,
    get_derive_account_info,
    load_positions,
    save_positions
)

sub_id = 116804
print(f"=== EXECUÇÃO DA TRAVA 3 DIAS (23/OUT/2026 80K/78K) NA SUBACCOUNT {sub_id} ===")

# 1. Check account before
acct_before = get_derive_account_info(subaccount_id=sub_id)
print(f"Saldo Antes: ${acct_before.get('balance_usdc'):,.2f} | Margem Livre: ${acct_before.get('free_margin'):,.2f}")

# 2. Place order on-chain
res = place_derive_spread_order(
    currency="BTC",
    expiry="20261023",
    short_strike=80000,
    long_strike=78000,
    contracts=0.70,
    short_price=300.0,
    long_price=115.0,
    subaccount_id=sub_id
)

print("\nResultado da Ordem na Derive:")
print(json.dumps(res, indent=2))

if res.get("success"):
    # 3. Register position in options_positions.json
    positions = load_positions()
    real_credit_per_contract = res.get("credit_per_contract", 185.0)
    real_contracts = res.get("contracts", 0.70)
    
    new_pos = {
        "id": f"pos-btc-80000-78000-20261023-{int(time.time())}",
        "currency": "BTC",
        "expiry": "20261023",
        "short_strike": 80000.0,
        "long_strike": 78000.0,
        "contracts": real_contracts,
        "initial_credit_per_contract": real_credit_per_contract,
        "initial_credit_total": round(real_contracts * real_credit_per_contract, 2),
        "initial_margin_total": round(real_contracts * (2000.0 - real_credit_per_contract), 2),
        "opened_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "status": "active",
        "target_take_profit_pct": 100.0,
        "auto_take_profit_enabled": False,
        "auto_close_on_tp": False,
        "auto_roll_enabled": True,
        "auto_roll_autonomous": False,
        "auto_roll_trigger_dte": 1,
        "auto_roll_max_cost_pct": 35.0,
        "is_live_order": True,
        "live_details": {
            "wallet": acct_before.get("wallet"),
            "subaccount_id": sub_id,
            "short_order_id": str(res.get("short_order_id", "submitted")),
            "long_order_id": str(res.get("long_order_id", "submitted")),
            "instrument": "BTC $80,000/$78,000 Put Spread Oct 23 (3D)",
            "total_received": round(real_contracts * real_credit_per_contract, 2),
            "breakeven": round(80000.0 - real_credit_per_contract, 2),
            "max_profit": round(real_contracts * real_credit_per_contract, 2),
            "max_loss": round(real_contracts * (2000.0 - real_credit_per_contract), 2)
        },
        "roll_count": 0
    }
    positions.append(new_pos)
    save_positions(positions)
    print("\n[SUCESSO] Nova trava de 3 dias registrada com sucesso no painel de controle e monitoramento!")

# 4. Check account after
acct_after = get_derive_account_info(subaccount_id=sub_id)
print(f"\nSaldo Depois: ${acct_after.get('balance_usdc'):,.2f} | Margem Livre Restante: ${acct_after.get('free_margin'):,.2f}")
