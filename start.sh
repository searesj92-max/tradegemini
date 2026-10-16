#!/bin/bash
echo "[*] =============================================="
echo "[*] INICIANDO BOTRADE NA NUVEM (RENDER.COM)"
echo "[*] MODO OPTIONS DESK 24/7 (DERIVE.XYZ) ATIVO"
echo "[*] MODO DERIVE PERP SNIPER V5 (5-YEAR VALIDATED) ATIVO"
echo "[*] MODO SENTINELA DEFI ATIVO (4 POOLS 24/7)"
echo "[*] =============================================="

# Garante que os diretórios necessários existem
mkdir -p dashboard data/journal data/reports data/approvals data/parked data/rejected data/options

# Configura as ABIs da Derive se necessário
python -u scripts/setup_derive_abis.py

# Inicia o Options Desk Server & Background Auto-Roll Worker (escuta local na 8766)
echo "[*] Subindo Options Desk 24/7 (Auto-Roll Daemon)..."
python -u scripts/options_desk.py --port 8766 &

# Inicia o Monitor de Opções / Put Spreads 24/7 para o Telegram (a cada 3 horas)
echo "[*] Subindo Monitor de Opções / Put Spreads 24/7 para Telegram..."
python -u scripts/telegram_options_monitor.py --daemon &

# Inicia o Monitor e Telegram Bot Interativo em background
python -u scripts/run_live_monitor.py &

# O processo principal em primeiro plano é o Cockpit Web Server (escuta na porta $PORT do Render)
echo "[*] Subindo Cockpit Web Server no processo principal..."
exec python -u scripts/dashboard_server.py
