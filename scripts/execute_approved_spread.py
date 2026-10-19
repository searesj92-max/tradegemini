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
    save_positions,
    DATA_FILE
)

sub_id = 116804
print(f"=== EXECUÇÃO DA TRAVA 1 (30/OUT/2026 68K/62K) NA SUBACCOUNT {sub_id} ===")

# 1. Check account before
acct_before = get_derive_account_info(subaccount_id=sub_id)
print(f"Saldo Antes: ${acct_before.get('balance_usdc'):,.2f} | Margem Livre: ${acct_before.get('free_margin'):,.2f}")

# 2. Place order on-chain
res = place_derive_spread_order(
    currency="BTC",
    expiry="20261030",
    short_strike=68000,
    long_strike=62000,
    contracts=0.10,
    short_price=106.0,
    long_price=78.0,
    subaccount_id=sub_id
)

print("\nResultado da Ordem na Derive:")
print(json.dumps(res, indent=2))

if res.get("success"):
    # 3. Register position in options_positions.json
    positions = load_positions()
    new_pos = {
        "id": f"pos-btc-68000-62000-20261030-{int(time.time())}",
        "currency": "BTC",
        "expiry": "20261030",
        "short_strike": 68000.0,
        "long_strike": 62000.0,
        "contracts": res.get("contracts", 0.10),
        "initial_credit_per_contract": 28.0,
        "initial_credit_total": round(res.get("contracts", 0.10) * 28.0, 2),
        "initial_margin_total": round(res.get("contracts", 0.10) * 6000.0, 2),
        "opened_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "status": "active",
        "target_take_profit_pct": 80.0,
        "auto_take_profit_enabled": True,
        "auto_close_on_tp": True,
        "auto_roll_enabled": True,
        "auto_roll_autonomous": True,
        "auto_roll_trigger_dte": 3,
        "auto_roll_max_cost_pct": 35.0,
        "is_live_order": True,
        "live_details": {
            "wallet": acct_before.get("wallet"),
            "subaccount_id": sub_id,
            "short_order_id": str(res.get("short_order_id", "submitted")),
            "long_order_id": str(res.get("long_order_id", "submitted")),
            "instrument": "BTC $68,000/$62,000 Put Spread Oct 30",
            "total_received": round(res.get("contracts", 0.10) * 28.0, 2),
            "breakeven": 67972.0,
            "max_profit": round(res.get("contracts", 0.10) * 28.0, 2),
            "max_loss": round(res.get("contracts", 0.10) * (6000.0 - 28.0), 2)
        },
        "roll_count": 0
    }
    positions.append(new_pos)
    save_positions(positions)
    print("\n[SUCESSO] Nova trava registrada com sucesso no painel de controle e monitoramento!")

# 4. Check account after
acct_after = get_derive_account_info(subaccount_id=sub_id)
print(f"\nSaldo Depois: ${acct_after.get('balance_usdc'):,.2f} | Margem Livre Restante: ${acct_after.get('free_margin'):,.2f}")
