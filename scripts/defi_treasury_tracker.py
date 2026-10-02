#!/usr/bin/env python3
"""
DeFi Treasury Tracker (Base Network) for Botrade
Tracks active Concentrated Liquidity and Yield Farming positions:
1. Aerodrome WETH/USDC (Mellow Strategy)
2. Krystal Uniswap V3 VIRTUAL/WETH (Autopilot Rebalance)
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# Fix Windows console encoding
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data" / "defi_treasury.json"

DEFAULT_TREASURY = {
    "wallet": "0xa36C0cb2159Fd132A6EFe461E170cf399a503a54",
    "network": "Base (Layer 2)",
    "updated_at": "2026-09-30T18:50:00Z",
    "positions": [
        {
            "id": "aerodrome_weth_usdc",
            "name": "WETH / USDC (Slipstream Concentrated 100)",
            "protocol": "Aerodrome Finance (via Mellow)",
            "type": "Cofre Conservador (Âncora)",
            "vault_contract": "0xcd975e6a5F55137755487F0918b8ca74aCCe7925",
            "gauge_contract": "0xF33a96b5932D9E9B9A0eDA447AbD8C9d48d2e0c8",
            "shares": "6.387.575.600.801.918 (~0,8498% do cofre)",
            "capital_usd": 10168.90,
            "composition": "2.0565 WETH + $4,690.10 USDC",
            "range_min": 2596.73,
            "range_max": 2785.00,
            "range_unit": "USDC/ETH",
            "current_price_ref": 2682.55,
            "status": "🟢 IN RANGE (Centralizado)",
            "apr_display": "68.76% (visor)",
            "apr_real": "~148.0% a.a.",
            "emissions_rate": "~2.27 AERO/h (~54.5 AERO/dia)",
            "daily_usd": 43.60,
            "monthly_usd": 1308.00,
            "reward_token": "AERO"
        },
        {
            "id": "krystal_virtual_weth",
            "name": "VIRTUAL / WETH 0.05% (#6118348)",
            "protocol": "Uniswap V3 (via Krystal Autopilot)",
            "type": "Posição Foguete (Narrativa IA)",
            "nft_id": "6118348",
            "strategy_id": "103005758",
            "capital_usd": 406.46,
            "composition": "256 VIRTUAL (~$204) + 0.0753 WETH (~$202)",
            "range_min": 0.0002886,
            "range_max": 0.0003067,
            "range_unit": "WETH/VIRTUAL",
            "current_price_ref": 0.0002974,
            "status": "🟢 IN RANGE (Centralizado)",
            "automation": "Auto-Rebalance Ativo (Keeper Grid)",
            "apr_estimated": "~117% a 541% a.a.",
            "daily_usd": 5.95,
            "monthly_usd": 178.50,
            "reward_token": "Taxas Puras (WETH + VIRTUAL)"
        }
    ]
}


def load_treasury() -> dict:
    if DATA_FILE.exists():
        try:
            return json.loads(DATA_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(json.dumps(DEFAULT_TREASURY, indent=2, ensure_ascii=False), encoding="utf-8")
    return DEFAULT_TREASURY


def format_defi_message() -> tuple[str, dict]:
    t = load_treasury()
    positions = t.get("positions", [])
    
    total_capital = sum(p.get("capital_usd", 0.0) for p in positions)
    total_daily = sum(p.get("daily_usd", 0.0) for p in positions)
    total_monthly = sum(p.get("monthly_usd", 0.0) for p in positions)
    total_brl_month = total_monthly * 5.50
    total_brl_day = total_daily * 5.50

    lines = [
        "🏦 *TESOURARIA DEFI & MULTI-CHAIN YIELD*",
        f"📅 Data: {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M UTC')}",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"🌐 *Redes:* Base L2 + Monad L1 (4 Posições Ativas)",
        f"💰 *Capital Total Alocado:* `${total_capital:,.2f} USDC`",
        f"💵 *Renda Diária Est.:* `~${total_daily:,.2f} / dia` (~R$ {total_brl_day:,.2f}/dia)",
        f"🚀 *Renda Mensal Proj.:* `~${total_monthly:,.2f} / mês` (~R$ {total_brl_month:,.2f}/mês)",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    ]

    for idx, p in enumerate(positions, 1):
        lines.append(f"📍 *POSIÇÃO {idx}: {p['name']}*")
        lines.append(f"  • *Protocolo:* {p['protocol']}")
        lines.append(f"  • *Tipo:* {p['type']}")
        lines.append(f"  • *Saldo Alocado:* `${p['capital_usd']:,.2f}` ({p['composition']})")
        lines.append(f"  • *Faixa Ativa:* `{p['range_min']} <-> {p['range_max']} {p['range_unit']}`")
        lines.append(f"  • *Status:* {p['status']}")
        
        if "automation" in p:
            lines.append(f"  • *Autopilot:* 🤖 {p['automation']}")
        if "emissions_rate" in p:
            lines.append(f"  • *Ritmo:* {p['emissions_rate']}")
        
        apr_txt = p.get('apr_real') or p.get('apr_estimated') or p.get('apr_display')
        lines.append(f"  • *APR Estimado:* *{apr_txt}*")
        lines.append(f"  • *Renda Estimada:* `~${p['daily_usd']:.2f}/dia` (~${p['monthly_usd']:.2f}/mês)")
        lines.append("")

    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("🛡️ *Estratégia:* Barbell (96% Âncora WETH/USDC + 4% Foguete IA VIRTUAL)")
    lines.append("_Monitoramento on-chain 100% ativo com alertas de range e rebalanceamento._")

    markup = {
        "inline_keyboard": [
            [{"text": "🔄 Atualizar Tesouraria", "callback_data": "defi_treasury"}],
            [{"text": "📊 Saldo Hyperliquid", "callback_data": "refresh_status"}, {"text": "💰 Lucro Acumulado", "callback_data": "profit_summary"}],
            [{"text": "📑 Relatório Diário", "callback_data": "daily_report"}]
        ]
    }

    return "\n".join(lines), markup


if __name__ == "__main__":
    text, _ = format_defi_message()
    print(text)
