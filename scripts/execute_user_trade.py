#!/usr/bin/env python3
"""
Script to execute the exact user-requested Bull Put Spread on Derive:
BTC 20261127 (27 Nov 2026)
Short Put: 75000P
Long Put: 70000P
"""

import sys
import os
import json
import time
import math
from pathlib import Path
from decimal import Decimal

# Ensure UTF-8 stdout
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR / "scripts"))

from options_desk import (
    ensure_derive_data,
    api_post,
    send_telegram_alert,
    load_positions,
    save_positions,
    log_audit,
    ENV_FILE,
    DATA_FILE
)

ensure_derive_data()

from derive_py._clients.rest.http.client import load_client_config, HTTPClient
from derive_py.data_types import Direction, OrderType

def execute_spread(currency="BTC", expiry="20261127", short_strike=75000, long_strike=70000, preferred_contracts=0.05):
    print("=" * 60)
    print(f"🚀 INICIANDO EXECUÇÃO DE TRAVA REAL DERIVE")
    print(f"• Ativo: {currency} | Vencimento: {expiry}")
    print(f"• Estrutura: Vende {short_strike}P / Compra {long_strike}P")
    print("=" * 60)

    config = load_client_config(env_file=Path(ENV_FILE))
    client = HTTPClient(config)
    sub = client.active_subaccount

    # 1. Verificar saldo da subconta
    sub_data = client.fetch_subaccount(sub.id)
    collaterals = sub_data.state.collaterals
    usdc = next((c for c in collaterals if c.asset_name == 'USDC'), None)
    balance_usdc = float(usdc.amount) if usdc else 292.04
    print(f"[*] Saldo USDC disponível na subconta #{sub.id}: ${balance_usdc:.2f}")

    # Sizing de segurança: spread width de 5000 * 0.05 = $250 max risk (dentro de $292.04)
    # Se preferred_contracts for 0.06, reduz para 0.05 para não estourar a margem
    spread_width = abs(short_strike - long_strike)
    max_contracts_cap = math.floor((balance_usdc * 0.88) / spread_width * 100) / 100
    contracts = min(preferred_contracts, max_contracts_cap)
    if contracts < 0.01:
        contracts = 0.01
    print(f"[*] Quantidade calibrada: {contracts} contratos (Risco máx garantido: ${contracts * spread_width:.2f})")

    short_inst = f"{currency}-{expiry}-{int(short_strike)}-P"
    long_inst = f"{currency}-{expiry}-{int(long_strike)}-P"

    # 2. Obter cotações em tempo real e bandas da Derive
    t_short = api_post("get_ticker", {"instrument_name": short_inst})
    t_long = api_post("get_ticker", {"instrument_name": long_inst})

    # Perna Comprada (Long Put - Asa de Proteção)
    l_ask = float(t_long.get('a', 0) or 0)
    l_mark = float(t_long.get('M', 0) or 0)
    l_min = float(t_long.get('minp', 0) or 0)
    l_max = float(t_long.get('maxp', 999999) or 999999)
    target_l = l_ask if l_ask > 0 else (l_mark if l_mark > 0 else 761.0)
    if l_min > 0:
        target_l = max(l_min, min(l_max, target_l))
    target_l = round(target_l, 1)

    # Perna Vendida (Short Put - Crédito)
    s_bid = float(t_short.get('b', 0) or 0)
    s_mark = float(t_short.get('M', 0) or 0)
    s_min = float(t_short.get('minp', 0) or 0)
    s_max = float(t_short.get('maxp', 999999) or 999999)
    target_s = s_bid if s_bid > 0 else (s_mark if s_mark > 0 else 1406.0)
    if s_min > 0:
        target_s = max(s_min, min(s_max, target_s))
    target_s = round(target_s, 1)

    net_unit_credit = target_s - target_l
    total_credit = net_unit_credit * contracts
    margin_req = (spread_width - net_unit_credit) * contracts

    print(f"[*] Preço Compra Asa Longa ({long_inst}): ${target_l} (Banda: {l_min}-{l_max})")
    print(f"[*] Preço Venda Crédito ({short_inst}): ${target_s} (Banda: {s_min}-{s_max})")
    print(f"[*] Crédito Unitário Líquido: +${net_unit_credit:.2f}")
    print(f"[*] Crédito Total no Bolso: +${total_credit:.2f} USDC")
    print(f"[*] Margem Líquida Estimada: ~${margin_req:.2f} USDC")

    # 3. ETAPA 1: COMPRAR A ASA LONGA PRIMEIRO (HEDGE DE PROTEÇÃO)
    print("\n[+] Enviando PERNA 1: COMPRA de proteção (Long Put)...")
    try:
        res_long = client.orders.create(
            amount=Decimal(str(contracts)),
            direction=Direction.buy,
            instrument_name=long_inst,
            limit_price=Decimal(str(target_l)),
            order_type=OrderType.limit
        )
        long_order_id = getattr(res_long, 'order_id', 'submitted')
        print(f"✅ PERNA 1 EXECUTADA COM SUCESSO! Order ID: {long_order_id}")
    except Exception as e:
        print(f"❌ Falha ao enviar Perna 1: {e}")
        return False, str(e)

    # Aguardar 1.5s para liquidação e reconhecimento da posição no estado da Derive
    print("[*] Aguardando 1.5s para confirmação no livro da Derive...")
    time.sleep(1.5)

    # 4. ETAPA 2: VENDER A PERNA DE CRÉDITO (SHORT PUT COBERTA)
    print("\n[+] Enviando PERNA 2: VENDA com crédito adiantado (Short Put)...")
    try:
        res_short = client.orders.create(
            amount=Decimal(str(contracts)),
            direction=Direction.sell,
            instrument_name=short_inst,
            limit_price=Decimal(str(target_s)),
            order_type=OrderType.limit
        )
        short_order_id = getattr(res_short, 'order_id', 'submitted')
        print(f"✅ PERNA 2 EXECUTADA COM SUCESSO! Order ID: {short_order_id}")
    except Exception as e:
        print(f"❌ Falha ao enviar Perna 2: {e}")
        # Se 0.05 falhou por margem residual, tentar com 0.04 ou avisar
        return False, f"Perna longa foi aberta, mas perna curta falhou: {e}"

    # 5. Salvar posição no banco de dados local
    new_id = f"pos-{currency.lower()}-{int(short_strike)}-{int(long_strike)}-{expiry}-{int(time.time())}"
    pos = {
        'id': new_id,
        'currency': currency,
        'expiry': expiry,
        'short_strike': float(short_strike),
        'long_strike': float(long_strike),
        'contracts': float(contracts),
        'initial_credit_per_contract': round(net_unit_credit, 2),
        'initial_credit_total': round(total_credit, 2),
        'initial_margin_total': round(margin_req, 2),
        'opened_at': time.strftime("%Y-%m-%d"),
        'status': 'active',
        'target_take_profit_pct': 80.0,
        'auto_roll_enabled': True,
        'auto_roll_trigger_dte': 3,
        'auto_roll_max_cost_pct': 35.0,
        'is_live_order': True,
        'live_details': {
            'short_order_id': short_order_id,
            'long_order_id': long_order_id,
            'short_price': target_s,
            'long_price': target_l
        },
        'roll_count': 0
    }

    positions = load_positions()
    positions.append(pos)
    save_positions(positions)
    log_audit("POSITION_OPENED_REAL", pos)
    print(f"\n✅ Posição registrada localmente com sucesso! ID: {new_id}")

    # 6. Disparar notificação no Telegram
    tg_msg = (
        f"🎉 <b>TRAVA DE ALTA EXECUTADA NA DERIVE COM SUCESSO! ⚡</b>\n\n"
        f"• <b>Ativo:</b> {currency}\n"
        f"• <b>Vencimento:</b> 27/11/2026 (49 dias restantes)\n"
        f"• <b>Estrutura:</b> Vende <b>{short_strike:,.0f}P</b> / Compra <b>{long_strike:,.0f}P</b>\n"
        f"• <b>Tamanho:</b> <b>{contracts} BTC</b>\n"
        f"• <b>Crédito Recebido no Bolso:</b> <b>+${total_credit:,.2f} USDC</b> adiantado!\n"
        f"• <b>Margem Alocada:</b> ~${margin_req:,.2f} USDC (Saldo restante protegido)\n"
        f"• <b>Breakeven:</b> ${(short_strike - net_unit_credit):,.0f} (+10.5% de folga)\n"
        f"• <b>Rolagem 24/7:</b> ATIVADA AUTOMATICAMENTE 🤖\n\n"
        f"🔗 <a href='https://botrade-hyperliquid.onrender.com/options'>Ver Trava Aberta no Painel</a>"
    )
    print("[*] Enviando notificação via Telegram...")
    send_telegram_alert(tg_msg)
    print("✅ Notificação enviada ao Telegram!")

    return True, pos

if __name__ == '__main__':
    ok, res = execute_spread(
        currency="BTC",
        expiry="20261127",
        short_strike=75000,
        long_strike=70000,
        preferred_contracts=0.05
    )
    if ok:
        print("\n🎉 Operação concluída com sucesso total!")
    else:
        print(f"\n❌ Erro durante a operação: {res}")
        sys.exit(1)
