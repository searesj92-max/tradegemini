import sys
from decimal import Decimal
from pathlib import Path
import json
import time

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from options_desk import get_derive_client_for_wallet, api_post
from derive_py.data_types import Direction, OrderType

sub_id = 116270
print(f"=== EXECUÇÃO DO TRADE SCALP BTC-PERP NA CARTEIRA 1 ({sub_id}) ===")

# 1. Fetch live ticker
t = api_post('get_ticker', {'instrument_name': 'BTC-PERP'})
ask_px = float(t.get('a') or t.get('M'))
print(f"Preço Ask BTC-PERP: ${ask_px:,.2f}")

# 2. Setup order params
amount = Decimal("0.01")
entry_px = Decimal(str(round(ask_px + 1.0, 1)))

client, sub_id, wallet = get_derive_client_for_wallet(subaccount_id=sub_id)

try:
    print(f"Enviando ordem de compra LONG: 0.01 BTC-PERP @ ${entry_px}...")
    res = client.orders.create(
        amount=amount,
        direction=Direction.buy,
        instrument_name="BTC-PERP",
        limit_price=entry_px,
        order_type=OrderType.limit,
        label="scalp_sunday_close"
    )
    print("Ordem executada com sucesso!")
    print("Order ID:", getattr(res, 'order_id', 'submitted'))

    # Setup Take Profit resting order at +$700 ($82,650)
    tp_px = Decimal(str(round(float(entry_px) + 700.0, 1)))
    time.sleep(1.0)
    print(f"Enviando ordem Take-Profit resting: 0.01 BTC-PERP @ ${tp_px} (Reduce Only)...")
    res_tp = client.orders.create(
        amount=amount,
        direction=Direction.sell,
        instrument_name="BTC-PERP",
        limit_price=tp_px,
        order_type=OrderType.limit,
        reduce_only=True,
        label="scalp_tp"
    )
    print("Take Profit registrado com sucesso!")
    print("TP Order ID:", getattr(res_tp, 'order_id', 'submitted'))

except Exception as e:
    print("Erro ao enviar ordem perp:", e)

# Check subaccount positions after
time.sleep(1.0)
sub = client.fetch_subaccount(sub_id)
print("\nPosições On-Chain na Subaccount 116270:")
for p in getattr(sub.state, 'positions', []):
    print(f"  {p.instrument_name}: amount={p.amount}")
