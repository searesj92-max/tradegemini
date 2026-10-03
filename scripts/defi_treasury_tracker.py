#!/usr/bin/env python3
"""
DeFi Treasury Tracker (Multi-Chain: Base & Monad) for Botrade
Tracks active Concentrated Liquidity and Yield Farming positions:
1. Aerodrome WETH/USDC (Mellow Strategy)
2. Aerodrome USDC/GOOGLc (Gauge Staking)
3. Krystal Uniswap V3 VIRTUAL/WETH (Autopilot Rebalance)
4. Uniswap v4 MON/USDC (Monad)
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Fix Windows console encoding
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

DATA_FILE = ROOT / "data" / "defi_treasury.json"


def load_treasury() -> dict:
    if DATA_FILE.exists():
        try:
            return json.loads(DATA_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def format_defi_message() -> tuple[str, dict]:
    markup = {
        "inline_keyboard": [
            [{"text": "💰 Ver Lucros de Hoje & Total", "callback_data": "defi_profit"}],
            [{"text": "🔄 Atualizar Radar das 4 Pools", "callback_data": "defi_treasury"}],
            [{"text": "💼 Alocação Patrimonial", "callback_data": "refresh_status"}, {"text": "📑 Relatório 24h", "callback_data": "daily_report"}]
        ]
    }

    try:
        from defi_pools_monitor import fetch_live_market_data, evaluate_positions, generate_consolidated_report
        market = fetch_live_market_data()
        evaluated, _, profits = evaluate_positions(market)
        report_text = generate_consolidated_report(evaluated, profits)
        return report_text, markup
    except Exception as e:
        print(f"[-] Erro ao gerar relatório ao vivo: {e}")

    # Fallback to local json if network fails
    t = load_treasury()
    positions = t.get("positions", [])
    total_capital = sum(p.get("capital_usd", 0.0) for p in positions)
    total_daily = sum(p.get("daily_usd", 0.0) for p in positions)

    lines = [
        "🏦 *TESOURARIA DEFI & MULTI-CHAIN YIELD (OFFLINE BACKUP)*",
        f"📅 Data: {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M UTC')}",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"🌐 *Redes:* Base L2 + Monad L1 (4 Posições Ativas)",
        f"💰 *Capital Total Alocado:* `${total_capital:,.2f} USDC`",
        f"💵 *Renda Diária Est.:* `~${total_daily:,.2f} / dia` (~R$ {total_daily * 5.50:,.2f}/dia)",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    ]
    for idx, p in enumerate(positions, 1):
        lines.append(f"📍 *POSIÇÃO {idx}: {p['name']}* ({p.get('chain', 'DeFi')})")
        lines.append(f"  • *Saldo:* `${p.get('capital_usd', 0):,.2f}`")
        lines.append(f"  • *Faixa:* `{p.get('range_min')} <-> {p.get('range_max')}`")
        lines.append(f"  • *Renda:* `~${p.get('daily_usd', 0):.2f}/dia`")
        lines.append("")

    return "\n".join(lines), markup


if __name__ == "__main__":
    text, _ = format_defi_message()
    print(text)
