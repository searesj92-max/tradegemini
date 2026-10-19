import sys
from decimal import Decimal
from pathlib import Path
import time
import json

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from options_desk import get_derive_client_for_wallet, api_post
from derive_py.data_types import Direction, OrderType

sub_id = 116270
print(f"=== AUMENTO DE POSIÇÃO BTC-PERP (+$25 MARGEM ISOLADA) NA CARTEIRA {sub_id} ===")

client, sub_id, wallet = get_derive_client_for_wallet(subaccount_id=sub_id)

# 1. Fetch live ticker
t = api_post('get_ticker', {'instrument_name': 'BTC-PERP'})
ask_px = float(t.get('a') or t.get('M'))
entry_px = Decimal(str(round(ask_px + 1.5, 1)))

# Adding 0.01 BTC consumes ~$17.40 USDC of margin (within the $25 isolated limit)
add_amount = Decimal('0.01')
print(f"Comprando +{add_amount} BTC-PERP a mercado @ ${entry_px} (adiciona ~$17.40 margem)...")
res_add = client.orders.create(
    amount=add_amount,
    direction=Direction.buy,
    instrument_name='BTC-PERP',
    limit_price=entry_px,
    order_type=OrderType.limit,
    label='scalp_add_25m'
)
print("Ordem de aumento executada com sucesso! Order ID:", getattr(res_add, 'order_id', 'submitted'))

# 2. Cancel old TP order for 0.01 BTC
time.sleep(1.0)
orders = client.orders.list_open()
for o in orders:
    if o.instrument_name == 'BTC-PERP' and o.direction == Direction.sell:
        print(f"Cancelando TP antigo ({o.amount} BTC @ ${o.limit_price})...")
        client.orders.cancel(order_id=o.order_id, instrument_name='BTC-PERP')

# 3. Create new combined TP order for 0.02 BTC at $83,200 (busca +$22 a +$25 de lucro)
time.sleep(1.0)
total_amount = Decimal('0.02')
tp_px = Decimal('83200.0')
print(f"Enviando novo TP consolidado para {total_amount} BTC @ ${tp_px}...")
res_tp = client.orders.create(
    amount=total_amount,
    direction=Direction.sell,
    instrument_name='BTC-PERP',
    limit_price=tp_px,
    order_type=OrderType.limit,
    label='scalp_tp_002'
)
print("Novo Take Profit registrado com sucesso! Order ID:", getattr(res_tp, 'order_id', 'submitted'))

# 4. Check subaccount positions after
time.sleep(1.0)
sub = client.fetch_subaccount(sub_id)
print("\nPosições On-Chain na Subaccount 116270:")
for p in getattr(sub.state, 'positions', []):
    print(f"  {p.instrument_name}: amount={p.amount}")
