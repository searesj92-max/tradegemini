#!/usr/bin/env python3
"""
High-Speed Options Monitor & Rollover Guard (30s Polling)
Vigilância em tempo real com alertas rápidos no Telegram e gatilho de rolagem -4k.
"""

import sys
import time
import json
import datetime
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "scripts"))

from send_telegram import send
import options_desk

POSITIONS_FILE = ROOT_DIR / "data" / "options_positions.json"

POLL_INTERVAL_SEC = 30  # Monitoramento de alta precisão a cada 30 segundos
ALERT_COOLDOWN_SEC = 300  # Evita flood no Telegram (mínimo 5 min entre alertas de mesmo nível)

_last_alert_level = None
_last_alert_time = 0

def check_guard():
    global _last_alert_level, _last_alert_time
    
    if not POSITIONS_FILE.exists():
        return
        
    try:
        positions = json.loads(POSITIONS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return
        
    active_pos = [p for p in positions if p.get("status") == "active" and p.get("is_live_order") is True]
    if not active_pos:
        return
        
    spot = options_desk.get_spot_price("BTC")
    if not spot or spot < 1000:
        return

    now = time.time()
    now_str = datetime.datetime.now().strftime("%H:%M:%S")

    for pos in active_pos:
        short_k = float(pos["short_strike"])
        long_k = float(pos["long_strike"])
        contracts = float(pos["contracts"])
        expiry = pos.get("expiry", "")
        exp_formatted = f"{expiry[6:8]}/{expiry[4:6]}" if len(expiry) >= 8 else expiry
        
        dist_usd = spot - short_k
        dist_pct = (dist_usd / spot) * 100

        # Classificação dos Níveis de Risco
        level = "SEGURO"
        icon = "🟢"
        if dist_usd <= 0:
            level = "CRITICO_ROLAGEM"
            icon = "🔴"
        elif dist_usd <= 500:
            level = "ALERTA_IMINENTE"
            icon = "🟠"
        elif dist_usd <= 1000:
            level = "ATENCAO"
            icon = "🟡"

        # Log silencioso a cada 30s no console
        print(f"[{now_str}] Spot: ${spot:,.1f} | Strike: ${short_k:,.0f} | Folga: {icon} ${dist_usd:+,.1f} ({dist_pct:+.2f}%) | Nível: {level}")

        # Se houver mudança de nível ou expirar cooldown
        if level != "SEGURO":
            should_alert = (level != _last_alert_level) or (now - _last_alert_time > ALERT_COOLDOWN_SEC)
            if should_alert:
                _last_alert_level = level
                _last_alert_time = now

                if level == "CRITICO_ROLAGEM":
                    msg = (
                        f"🚨 *ALERTA CRÍTICO: PREÇO TOCOU O STRIKE!*\n\n"
                        f"• *Bitcoin Spot:* `${spot:,.2f}`\n"
                        f"• *Strike Vendido:* `${short_k:,.0f}P`\n"
                        f"• *Vencimento:* `{exp_formatted}`\n"
                        f"• *Folga:* `-$ {abs(dist_usd):,.2f}` (`{dist_pct:.2f}%`)\n\n"
                        f"🛡️ *AÇÃO IMEDIATA RECOMENDADA:* Rolagem Defensiva baixando o strike em pelo menos -$4.000 (para $75.000P ou $76.000P).\n"
                        f"Execute `/rolar` no bot para acionar a rotação automática!"
                    )
                elif level == "ALERTA_IMINENTE":
                    msg = (
                        f"🟠 *AVISO DE VIGILÂNCIA: FOLGA INFERIOR A $500*\n\n"
                        f"• *Bitcoin Spot:* `${spot:,.2f}`\n"
                        f"• *Strike Vendido:* `${short_k:,.0f}P`\n"
                        f"• *Distância Atual:* `+${dist_usd:,.2f}` (+{dist_pct:.2f}%)\n\n"
                        f"A mesa está em prontidão. Se o spot cruzar ${short_k:,.0f}, o protocolo de rolagem para -$4k será liberado."
                    )
                else: # ATENCAO
                    msg = (
                        f"🟡 *RADAR OPTIONS DESK: BTC SE APROXIMOU DE $1.000 DO STRIKE*\n\n"
                        f"• *Spot:* `${spot:,.2f}` | Strike: `${short_k:,.0f}P`\n"
                        f"• *Folga de Segurança:* `+${dist_usd:,.2f}` (+{dist_pct:.2f}%)\n"
                        f"Monitoramento acelerado ativo (checagem a cada 30 segundos)."
                    )
                send(msg)

def run_loop():
    print(f"Iniciando High-Speed Watchdog (intervalo: {POLL_INTERVAL_SEC}s)...")
    while True:
        try:
            check_guard()
        except Exception as e:
            print(f"[WATCHDOG ERROR] {e}")
        time.sleep(POLL_INTERVAL_SEC)

if __name__ == "__main__":
    run_loop()
