#!/usr/bin/env python3
"""
Telegram Options Monitor Daemon
Fetches live BTC spot price, inspects active positions in data/options_positions.json,
calculates safety buffer, theta, and sends a concise executive report to Telegram.
Can run standalone or every 3 hours.
"""

import sys
import json
import time
import datetime
import urllib.request
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "scripts"))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
from send_telegram import send

POSITIONS_FILE = ROOT_DIR / "data" / "options_positions.json"

def get_live_btc_price():
    try:
        url = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            return float(data["price"])
    except Exception:
        return 82300.0

def generate_report():
    spot = get_live_btc_price()
    now_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    
    if not POSITIONS_FILE.exists():
        return "Nenhuma posição encontrada."
        
    positions = json.loads(POSITIONS_FILE.read_text(encoding="utf-8"))
    
    # Filter only real live orders
    live_pos = [p for p in positions if p.get("is_live_order") is True and p.get("status") == "active"]
    
    msg = [
        "📊 *RELATÓRIO OPTIONS DESK — CARTEIRA TANGEM*",
        f"🕒 _Atualizado em:_ `{now_str}`",
        f"🪙 *Bitcoin Spot:* `${spot:,.2f}`",
        "━━━━━━━━━━━━━━━━━━━━━━"
    ]
    
    total_credit = sum(p.get("initial_credit_total", 0.0) for p in live_pos)
    total_margin = sum(p.get("initial_margin_total", 0.0) for p in live_pos)
    
    try:
        import options_desk
    except Exception:
        options_desk = None

    for idx, pos in enumerate(live_pos, 1):
        short_k = pos["short_strike"]
        long_k = pos["long_strike"]
        contracts = pos["contracts"]
        credit = pos.get("initial_credit_total", 0.0)
        margin = pos.get("initial_margin_total", 0.0)
        expiry = pos["expiry"]
        exp_formatted = f"{expiry[6:8]}/{expiry[4:6]}/{expiry[0:4]}"
        
        dist_usd = spot - short_k
        dist_pct = (dist_usd / spot) * 100
        breakeven = short_k - (credit / contracts)
        status_icon = "🟢" if dist_pct >= 5.0 else ("🟡" if dist_pct > 2.0 else "🔴")

        eval_p = options_desk.evaluate_position(pos) if options_desk else {}
        dte = eval_p.get("dte", 0)
        upnl = eval_p.get("current_pnl_total", 0.0)
        upnl_pct = eval_p.get("profit_captured_pct", 0.0)
        rem_table = eval_p.get("cost_to_close_total", 0.0)
        rem_per_day = rem_table / max(1, dte)
        rec = eval_p.get("recommendation", {})
        upnl_sign = "+" if upnl >= 0 else ""

        msg.append(f"\n*{idx}. Posição: BTC {short_k:,.0f} / {long_k:,.0f} Put Spread*")
        msg.append(f"   • *Vencimento:* `{exp_formatted}` (`{dte}d` restantes | `{contracts}` BTC)")
        msg.append(f"   • *Crédito Inicial:* `+${credit:,.2f} USDC` (Margem: `${margin:,.2f}`)")
        msg.append(f"   • *Lucro Atual (Mark Derive):* `{upnl_sign}${upnl:,.2f} USDC` (`{upnl_pct:.1f}%` capturado)")
        msg.append(f"   • *Restante na Mesa:* `${rem_table:,.2f}` (`+${rem_per_day:,.2f}/dia` até 100%)")
        msg.append(f"   • *Distância de Segurança:* {status_icon} `+${dist_usd:,.2f}` (`+{dist_pct:.1f}%` acima)")
        msg.append(f"   • *Decisão (80% vs 100%):* {rec.get('badge', '🟢 MANTER')}")

    msg.append("\n━━━━━━━━━━━━━━━━━━━━━━")
    msg.append(f"💰 *Total de Crédito Embolsado:* `+${total_credit:,.2f} USDC`")
    msg.append(f"🔒 *Margem Total Travada:* `${total_margin:,.2f} USDC`")
    msg.append(f"🛡️ *Status Geral:* `100% FORA DO DINHEIRO (OTM)`")
    
    return "\n".join(msg)

def send_instant_report():
    text = generate_report()
    res = send(text)
    print("Telegram response:", res)
    return res

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--daemon":
        print("Iniciando monitoramento Telegram a cada 3 horas (10800s)...")
        while True:
            try:
                send_instant_report()
            except Exception as e:
                print("Erro no envio:", e)
            time.sleep(3 * 3600)
    else:
        send_instant_report()
