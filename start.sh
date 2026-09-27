#!/bin/bash
echo "[*] =============================================="
echo "[*] INICIANDO BOTRADE NA NUVEM (RENDER.COM)"
echo "[*] =============================================="

# Garante que os diretórios necessários existem
mkdir -p dashboard data/journal data/reports data/approvals data/parked data/rejected

# Inicia o Monitor de Trailing Stop e Sincronização em background
python -u scripts/run_live_monitor.py &

# Inicia o Sniper Autônomo em background (com auto trade $20.00 e max 3 posições)
python -u scripts/auto_sniper.py --auto --margin 20.0 --max-positions 3 --interval 60 &

# O processo principal em primeiro plano é o Cockpit Web Server (escuta na porta $PORT do Render)
echo "[*] Subindo Cockpit Web Server no processo principal..."
exec python -u scripts/dashboard_server.py
