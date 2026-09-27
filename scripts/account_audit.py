#!/usr/bin/env python3
"""Audit full Hyperliquid financial performance: deposits, balance, realized PnL, fees."""
import sys
from pathlib import Path
from datetime import datetime, timezone

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from hyperliquid_executor import HyperliquidExecutor

def main():
    e = HyperliquidExecutor()
    status = e.get_account_status()
    fills = e.info.user_fills(e.main_address)
    ledger = e.info.user_non_funding_ledger_updates(e.main_address, 0)
    
    try:
        funding = e.info.user_funding_history(e.main_address, 0)
    except Exception:
        funding = []

    print("=" * 65)
    print("      RELATÓRIO FINANCEIRO COMPLETO — HYPERLIQUID MAINNET")
    print("=" * 65)

    print("\n📥 1. HISTÓRICO DE DEPÓSITOS ENVIADOS")
    total_deposited = 0.0
    for l in ledger:
        d = l.get("delta", {})
        amt = float(d.get("amount", 0.0))
        total_deposited += amt
        dt = datetime.fromtimestamp(l["time"] / 1000, timezone.utc).strftime("%d/%m/%Y %H:%M:%S UTC")
        print(f"  • Data: {dt} | Valor: ${amt:6.2f} USDC | Tipo: {d.get('type')}")
    print(f"  -------------------------------------------------------------")
    print(f"  💰 TOTAL DEPOSITADO NA CONTA: ${total_deposited:.2f} USDC")

    print("\n🏦 2. PATRIMÔNIO ATUAL NA CARTEIRA")
    perps_eq = float(status.get("perps_account_value", 0.0))
    spot_usdc = float(status.get("spot_usdc_balance", 0.0))
    total_equity = perps_eq + spot_usdc
    print(f"  • Saldo em Caixa Livre (Spot USDC): ${spot_usdc:.2f}")
    print(f"  • Margem Alocada em Contratos (Perps): ${perps_eq:.2f}")
    print(f"  -------------------------------------------------------------")
    print(f"  💵 PATRIMÔNIO LÍQUIDO ATUAL: ${total_equity:.2f} USDC")

    diff = total_equity - total_deposited
    pct = (diff / total_deposited * 100) if total_deposited > 0 else 0.0
    print("\n📊 3. BALANÇO GERAL (DEPÓSITOS vs PATRIMÔNIO ATUAL)")
    if diff >= 0:
        print(f"  🟢 VOCÊ ESTÁ NO LUCRO LÍQUIDO DE: +${diff:.4f} USD (+{pct:.2f}%)")
    else:
        print(f"  🔴 PREJUÍZO LÍQUIDO DE: -${abs(diff):.4f} USD ({pct:.2f}%)")

    print("\n🔍 4. DETALHAMENTO DE OPERAÇÕES E CUSTOS")
    total_closed_pnl = sum(float(f.get("closedPnl", 0.0)) for f in fills)
    total_fees = sum(float(f.get("fee", 0.0)) for f in fills)
    total_funding = sum(float(f["delta"].get("usdc", 0.0)) for f in funding) if funding else 0.0

    print(f"  • Lucro Bruto Realizado dos Trades: ${total_closed_pnl:+.4f} USD")
    print(f"  • Taxas Pagas à Corretora (Fees):   -${total_fees:.4f} USD")
    print(f"  • Taxas de Financiamento (Funding): ${total_funding:+.4f} USD")
    net_trading = total_closed_pnl - total_fees + total_funding
    print(f"  • Resultado Líquido das Operações:  ${net_trading:+.4f} USD")

    print("\n📋 5. HISTÓRICO DE CADA OPERAÇÃO REALIZADA")
    by_coin = {}
    for f in fills:
        c = f["coin"]
        by_coin.setdefault(c, []).append(f)

    for coin, coin_fills in by_coin.items():
        coin_pnl = sum(float(x.get("closedPnl", 0.0)) for x in coin_fills)
        coin_fee = sum(float(x.get("fee", 0.0)) for x in coin_fills)
        coin_net = coin_pnl - coin_fee
        print(f"  • {coin:5s}: PnL Bruto ${coin_pnl:+.4f} | Taxas -${coin_fee:.4f} | Líquido: ${coin_net:+.4f} USD")

    print("=" * 65)

if __name__ == "__main__":
    main()
