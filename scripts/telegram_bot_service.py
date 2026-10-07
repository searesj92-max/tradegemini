#!/usr/bin/env python3
"""
Botrade Interactive DeFi Treasury & Yield Sentinel Bot (Telegram)
Provides real-time institutional monitoring and profit tracking for DeFi positions:
- /lucro: Dedicated profit dashboard (real accrued yield, price distance, yesterday's benchmark)
- /defi or /pools: Radar of the active concentrated liquidity range (min, max, floor/ceiling distances)
- /relatorio: Consolidated 24h daily summary report
- /saldo or /status: Consolidated treasury capital, live equity and asset composition
- /planilha: Live spreadsheet link for Google Sheets (=IMPORTDATA) & instant CSV download
- Strictly presents real accrued yield and previous day's baseline. Zero future daily estimates.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

# Fix Windows console encoding
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

# Load .env
env_file = ROOT / ".env"
if env_file.exists():
    for line in env_file.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
DEFAULT_CHAT = os.environ.get("TELEGRAM_SIGNALS_CHAT_ID", os.environ.get("TELEGRAM_CHAT_ID", "")).strip()

from defi_pools_monitor import (
    fetch_live_market_data,
    evaluate_positions,
    generate_consolidated_report,
    calculate_profit_metrics,
    fetch_usd_brl,
    POSITIONS
)
from defi_treasury_tracker import format_defi_message


def tg_api_call(method: str, data: dict = None) -> dict:
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip() or TOKEN
    if not bot_token:
        return {"ok": False, "error": "TELEGRAM_BOT_TOKEN não configurado"}

    url = f"https://api.telegram.org/bot{bot_token}/{method}"
    payload = json.dumps(data, ensure_ascii=False).encode("utf-8") if data else None
    headers = {"Content-Type": "application/json; charset=utf-8", "User-Agent": "BotradeDesk/2.0"}

    req = urllib.request.Request(url, data=payload, headers=headers, method="POST" if payload else "GET")
    try:
        with urllib.request.urlopen(req, timeout=35) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"ok": False, "error": str(e)}


def send_message(chat_id: str | int, text: str, reply_markup: dict = None) -> dict:
    data = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    if reply_markup:
        data["reply_markup"] = reply_markup
    res = tg_api_call("sendMessage", data)
    if not res.get("ok") and ("parse" in str(res.get("error", "")).lower() or "400" in str(res.get("error", ""))):
        # Fallback to plain text if Markdown parsing fails
        data.pop("parse_mode", None)
        res = tg_api_call("sendMessage", data)
    return res


def send_document(chat_id: str | int, file_path: Path | str, caption: str = None) -> dict:
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip() or TOKEN
    if not bot_token:
        return {"ok": False, "error": "Token não configurado"}

    url = f"https://api.telegram.org/bot{bot_token}/sendDocument"
    p = Path(file_path)
    if not p.exists():
        return {"ok": False, "error": f"Arquivo {file_path} não encontrado"}

    file_bytes = p.read_bytes()
    filename = p.name
    boundary = "----WebKitFormBoundary" + os.urandom(16).hex()

    body = bytearray()
    body.extend(f"--{boundary}\r\n".encode("utf-8"))
    body.extend(f'Content-Disposition: form-data; name="chat_id"\r\n\r\n{chat_id}\r\n'.encode("utf-8"))
    if caption:
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(f'Content-Disposition: form-data; name="caption"\r\n\r\n{caption}\r\n'.encode("utf-8"))
    body.extend(f"--{boundary}\r\n".encode("utf-8"))
    body.extend(f'Content-Disposition: form-data; name="document"; filename="{filename}"\r\n'.encode("utf-8"))
    body.extend(b"Content-Type: text/csv; charset=utf-8\r\n\r\n")
    body.extend(file_bytes)
    body.extend(f"\r\n--{boundary}--\r\n".encode("utf-8"))

    req = urllib.request.Request(
        url,
        data=bytes(body),
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "User-Agent": "BotradeDesk/2.0"
        },
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=35) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"[-] Erro ao enviar documento Telegram: {e}")
        return {"ok": False, "error": str(e)}


def edit_message(chat_id: str | int, message_id: int, text: str, reply_markup: dict = None) -> dict:
    data = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    if reply_markup:
        data["reply_markup"] = reply_markup
    res = tg_api_call("editMessageText", data)
    if not res.get("ok") and ("parse" in str(res.get("error", "")).lower() or "400" in str(res.get("error", ""))):
        data.pop("parse_mode", None)
        res = tg_api_call("editMessageText", data)
    return res


def answer_callback(callback_query_id: str, text: str = None) -> dict:
    data = {"callback_query_id": callback_query_id}
    if text:
        data["text"] = text
    return tg_api_call("answerCallbackQuery", data)


def format_defi_profit_dashboard() -> tuple[str, dict]:
    """Generates pure dedicated profit & valuation dashboard without speculative future estimates."""
    now = datetime.now(timezone.utc)
    market = fetch_live_market_data()
    evaluated, _, profits = evaluate_positions(market)

    item = evaluated[0] if evaluated else {}
    pos = item.get("pos", {})
    prof = item.get("profit", {})
    px = item.get("current_price", 2697.0)
    usd_brl = fetch_usd_brl()

    cur_eq = prof.get("current_equity_usd", pos.get("capital_usd", 11568.85))
    init_eq = prof.get("initial_equity_usd", 11568.85)
    diff_usd = prof.get("equity_diff_usd", 0.0)
    diff_pct = prof.get("equity_diff_pct", 0.0)
    diff_sign = "+" if diff_usd >= 0 else "-"

    acc_aero = prof.get("accrued_aero", 0.0)
    acc_usd = prof.get("accrued_usd", 0.0)
    acc_fees = prof.get("accrued_fees_usd", 0.0)
    hours = prof.get("hours_active", 0.0)

    prev_usd = prof.get("prev_day_usd", 21.09)
    prev_aero = prof.get("prev_day_aero", 23.8)
    prev_brl = prof.get("prev_day_brl", prev_usd * usd_brl)

    dist_ceil = item.get("dist_ceiling", 0.0)
    dist_floor = item.get("dist_floor", 0.0)
    out_count = item.get("out_of_range_count", 0)

    p_min = pos.get("range_min", 2596.73)
    p_max = pos.get("range_max", 2798.98)

    if px >= p_min:
        floor_dist_str = f"+{dist_floor:.2f}% (margem de ~${px - p_min:.2f})"
    else:
        floor_dist_str = f"🔴 Rompido abaixo por -{abs(dist_floor):.2f}% (-${p_min - px:.2f})"

    if px <= p_max:
        ceiling_dist_str = f"+{dist_ceil:.2f}% (margem de ~${p_max - px:.2f})"
    else:
        ceiling_dist_str = f"🔴 Rompido acima por +{abs(dist_ceil):.2f}% (+${px - p_max:.2f})"

    lines = [
        "💰 *PAINEL DE RENDIMENTOS — TESOURARIA DEFI*",
        f"⏱️ _{now.strftime('%d/%m/%Y %H:%M UTC')}_",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "💼 *PATRIMÔNIO SOB CUSTÓDIA:*",
        f"• *Saldo Atual:* *`${cur_eq:,.2f} USD`* (**~R$ {cur_eq*usd_brl:,.2f}**)",
        f"• *Composição sob Custódia:* `{pos.get('weth_amount', 4.3322):.4f} WETH` + `{pos.get('usdc_amount', 0.0):,.2f} USDC`",
        f"• *Aporte Inicial:* `${init_eq:,.2f} USD` (Depósito #7732601)",
        f"• *Variação de Capital:* *`{diff_sign}${abs(diff_usd):.2f} USD ({diff_sign}{abs(diff_pct):.2f}%)`*",
        f"• *Cotação Dólar Base:* `R$ {usd_brl:.4f}` (Tempo Real)",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n",
        "🎯 *RADAR DA FAIXA & SEGURANÇA:*",
        f"• *Par:* *{pos.get('name', 'WETH / USDC (Slipstream 50)')}*",
        f"• *Preço Atual:* *`${px:,.2f} USDC`*",
        f"• *Faixa Ativa:* *`${p_min:,.2f}` ↔ `${p_max:,.2f}`*",
        f"• *Distância do Teto:* `{ceiling_dist_str}`",
        f"• *Distância do Piso:* `{floor_dist_str}`",
        f"• *Status:* {item.get('status_text', '🟢 100% IN RANGE')}",
        f"• *Saídas de Faixa:* *`{out_count} vezes`*",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n",
        "💰 *RENDIMENTOS REALIZADOS (SEM ESTIMATIVAS):*",
        f"• *AERO Minerado:* *`~{acc_aero:.2f} AERO`* (~${acc_aero*0.80:.2f} USD)",
        f"• *Taxas de Swap:* *`+${acc_fees:.2f} USD`*",
        f"• *Total Acumulado:* *`+${acc_usd:.2f} USD`* (**~R$ {acc_usd*usd_brl:.2f}**) em `{hours:.1f}h`",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"📊 *Referência do Dia Anterior:* *`~{prev_aero:.1f} AERO`* (*`+${prev_usd:.2f} USD`* / **~R$ {prev_brl:.2f}**)",
        "  └ _(Rendimento real do fechamento anterior para base comparativa)_",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "🛡️ _Monitoramento 24/7 ativo na nuvem (Render.com)._"
    ]

    markup = {
        "inline_keyboard": [
            [{"text": "🔄 Atualizar", "callback_data": "defi_profit"}, {"text": "📊 Planilha ao Vivo", "callback_data": "defi_sheet"}],
            [{"text": "📡 Radar da Faixa", "callback_data": "defi_treasury"}, {"text": "📑 Fechamento 24h", "callback_data": "daily_report"}]
        ]
    }
    return "\n".join(lines), markup


def format_defi_status_summary() -> tuple[str, dict]:
    """Generates clean high-level treasury capital allocation status."""
    now_utc = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")
    market = fetch_live_market_data()
    evaluated, _, profits = evaluate_positions(market)

    item = evaluated[0] if evaluated else {}
    pos = item.get("pos", {})
    prof = item.get("profit", {})
    px = item.get("current_price", 2697.0)
    usd_brl = fetch_usd_brl()

    cur_eq = prof.get("current_equity_usd", pos.get("capital_usd", 11568.85))
    init_eq = prof.get("initial_equity_usd", 11568.85)
    diff_usd = prof.get("equity_diff_usd", 0.0)
    diff_pct = prof.get("equity_diff_pct", 0.0)
    diff_sign = "+" if diff_usd >= 0 else "-"

    acc_usd = prof.get("accrued_usd", 0.0)
    prev_usd = prof.get("prev_day_usd", 21.09)
    out_count = item.get("out_of_range_count", 0)

    p_min = pos.get("range_min", 2596.73)
    p_max = pos.get("range_max", 2798.98)
    range_state_str = "🔴 Rompido abaixo" if px < p_min else ("🔴 Rompido acima" if px > p_max else "100% dentro do range")
    status_foot = "🔴 *Posição fora da faixa (100% em WETH). Emissões e taxas pausadas.*" if (px < p_min or px > p_max) else "🟢 *Cofre consolidado único, 100% ativo e gerando taxas no Gauge.*"

    lines = [
        "💼 *SALDO CONSOLIDADO — TESOURARIA DEFI*",
        f"⏱️ _{now_utc}_",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"💰 *PATRIMÔNIO TOTAL:* *`${cur_eq:,.2f} USD`* (**~R$ {cur_eq*usd_brl:,.2f}**)",
        f"• *Aporte Inicial:* `${init_eq:,.2f} USD`",
        f"• *Variação de Capital:* *`{diff_sign}${abs(diff_usd):.2f} USD ({diff_sign}{abs(diff_pct):.2f}%)`*",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n",
        "📍 *POSIÇÃO PRINCIPAL EM CUSTÓDIA:*",
        "• *Par:* *WETH / USDC (Slipstream 50)*",
        "  ├ *Identificação:* `Deposit #7732601` (Staked no Gauge Aerodrome)",
        f"  ├ *Composição:* `{pos.get('weth_amount', 4.3322):.4f} WETH` + `{pos.get('usdc_amount', 0.0):,.2f} USDC`",
        f"  ├ *Faixa Ativa:* `${p_min:,.2f}` ↔ `${p_max:,.2f}`",
        f"  ├ *Preço Atual:* `${px:,.2f} USDC`",
        f"  └ *Saídas de Faixa:* `{out_count} vezes` ({range_state_str})",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n",
        "💰 *RENDIMENTOS REALIZADOS:*",
        f"• *Acumulado neste Ciclo:* *`+${acc_usd:.2f} USD`* (~R$ {acc_usd*usd_brl:.2f})",
        f"• *Referência Fechamento Anterior:* *`+${prev_usd:.2f} USD`* (~R$ {prev_usd*usd_brl:.2f})",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
        status_foot
    ]

    markup = {
        "inline_keyboard": [
            [{"text": "💰 Ver Rendimentos (/lucro)", "callback_data": "defi_profit"}, {"text": "📊 Planilha ao Vivo", "callback_data": "defi_sheet"}],
            [{"text": "📡 Radar da Faixa (/defi)", "callback_data": "defi_treasury"}, {"text": "📑 Fechamento 24h (/relatorio)", "callback_data": "daily_report"}]
        ]
    }
    return "\n".join(lines), markup


def format_daily_report_message() -> tuple[str, dict]:
    """Generates 24-hour daily closing summary for DeFi treasury with verified real baseline."""
    now_utc = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")
    market = fetch_live_market_data()
    evaluated, _, profits = evaluate_positions(market)

    item = evaluated[0] if evaluated else {}
    pos = item.get("pos", {})
    prof = item.get("profit", {})
    px = item.get("current_price", 2697.0)
    usd_brl = fetch_usd_brl()

    cur_eq = prof.get("current_equity_usd", pos.get("capital_usd", 11568.85))
    init_eq = prof.get("initial_equity_usd", 11568.85)
    diff_usd = prof.get("equity_diff_usd", 0.0)
    diff_pct = prof.get("equity_diff_pct", 0.0)
    diff_sign = "+" if diff_usd >= 0 else "-"

    acc_aero = prof.get("accrued_aero", 0.0)
    acc_usd = prof.get("accrued_usd", 0.0)
    acc_fees = prof.get("accrued_fees_usd", 0.0)
    hours = prof.get("hours_active", 0.0)

    prev_usd = prof.get("prev_day_usd", 21.09)
    prev_aero = prof.get("prev_day_aero", 23.8)
    prev_brl = prof.get("prev_day_brl", prev_usd * usd_brl)

    dist_ceil = item.get("dist_ceiling", 0.0)
    dist_floor = item.get("dist_floor", 0.0)
    out_count = item.get("out_of_range_count", 0)

    p_min = pos.get("range_min", 2596.73)
    p_max = pos.get("range_max", 2798.98)
    if px >= p_min:
        floor_dist_str = f"+{dist_floor:.2f}% (margem de ~${px - p_min:.2f})"
    else:
        floor_dist_str = f"🔴 Rompido abaixo por -{abs(dist_floor):.2f}% (-${p_min - px:.2f})"

    if px <= p_max:
        ceiling_dist_str = f"+{dist_ceil:.2f}% (margem de ~${p_max - px:.2f})"
    else:
        ceiling_dist_str = f"🔴 Rompido acima por +{abs(dist_ceil):.2f}% (+${px - p_max:.2f})"

    lines = [
        "📑 *RELATÓRIO DE FECHAMENTO — TESOURARIA DEFI*",
        f"⏱️ _Período Apurado: {now_utc}_",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "💼 *PATRIMÔNIO SOB CUSTÓDIA:*",
        f"• *Saldo Atual:* *`${cur_eq:,.2f} USD`* (**~R$ {cur_eq*usd_brl:,.2f}**)",
        f"• *Composição sob Custódia:* `{pos.get('weth_amount', 4.3322):.4f} WETH` + `{pos.get('usdc_amount', 0.0):,.2f} USDC`",
        f"• *Aporte Inicial:* `${init_eq:,.2f} USD`",
        f"• *Variação de Capital:* *`{diff_sign}${abs(diff_usd):.2f} USD ({diff_sign}{abs(diff_pct):.2f}%)`*",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n",
        "💰 *RENDIMENTO REAL DO DIA ANTERIOR (BASE COMPARATIVA):*",
        f"• *Em Dólar:* *`+${prev_usd:.2f} USD`*",
        f"• *Em Reais:* 🟢 *`+R$ {prev_brl:,.2f}`*",
        f"• *Em AERO:* *`~{prev_aero:.1f} AERO`* (Fechamento 24h Real)",
        "  └ _(Valor verificado do dia anterior para base comparativa empírica)_\n",
        "💰 *RENDIMENTO REAL ACUMULADO NESTE CICLO:*",
        f"• *Total Acumulado:* *`+${acc_usd:.2f} USD`* (**~R$ {acc_usd*usd_brl:.2f}**) em `{hours:.1f}h`",
        f"• *Composição:* `~{acc_aero:.2f} AERO` + `+${acc_fees:.2f} Taxas de Swap`",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n",
        "🎯 *RADAR DA FAIXA & STATUS:*",
        f"• *Par:* *{pos.get('name', 'WETH / USDC (Slipstream 50)')}*",
        f"• *Preço Atual:* *`${px:,.2f} USDC`*",
        f"• *Faixa Ativa:* `${p_min:,.2f}` ↔ `${p_max:,.2f}`*",
        f"• *Distância do Teto:* `{ceiling_dist_str}`",
        f"• *Distância do Piso:* `{floor_dist_str}`",
        f"• *Saídas da Faixa:* *`{out_count} vezes`*",
        f"• *Status:* {item.get('status_text', '🟢 100% IN RANGE')}",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "🛡️ _Relatório oficial consolidado do Sentinela 24/7 na nuvem (Render.com)._"
    ]

    markup = {
        "inline_keyboard": [
            [{"text": "💰 Ver Rendimento Real", "callback_data": "defi_profit"}, {"text": "📊 Planilha ao Vivo", "callback_data": "defi_sheet"}],
            [{"text": "📡 Radar da Faixa", "callback_data": "defi_treasury"}, {"text": "💼 Alocação Patrimonial", "callback_data": "refresh_status"}]
        ]
    }
    return "\n".join(lines), markup


def format_virtual_rebalance_status() -> tuple[str, dict]:
    """Informs that VIRTUAL position was disassembled and capital consolidated into WETH/USDC."""
    lines = [
        "ℹ️ *POSIÇÃO VIRTUAL / WETH CONCLUÍDA & DESMONTADA*",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "Todo o capital das posições secundárias anteriores foi resgatado e **consolidado integralmente** no cofre principal:",
        "\n• *Cofre Principal:* **WETH / USDC (Slipstream 50)**",
        "• *Identificação:* `Deposit #7732601`",
        "• *Rede:* Base Network (Aerodrome Finance)",
        "• *Faixa Concentrada:* `$2,596.73` ↔ `$2,798.98 USDC`",
        "• *Benefício:* Zero risco de rebalanceamento forçado no fundo e mineração direta de AERO no Gauge.",
        "\n━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "👉 Digite `/lucro` para ver os rendimentos ou `/defi` para ver o radar da faixa."
    ]
    markup = {
        "inline_keyboard": [
            [{"text": "💰 Ver Rendimentos (/lucro)", "callback_data": "defi_profit"}],
            [{"text": "📡 Ver Radar da Faixa (/defi)", "callback_data": "defi_treasury"}]
        ]
    }
    return "\n".join(lines), markup


def handle_planilha_command(chat_id: int | str):
    """Generates on-demand spreadsheet and provides Google Sheets live link + Excel files."""
    try:
        from defi_sheet_recorder import record_snapshot
        m = fetch_live_market_data()
        e, _, p = evaluate_positions(m)
        record_snapshot(e, p, m)
    except Exception as e:
        print(f"[-] Erro ao atualizar snapshot para /planilha: {e}")

    sheet_url = "https://botrade-hyperliquid.onrender.com/api/defi/live.csv"
    web_dashboard_url = "https://botrade-hyperliquid.onrender.com/planilha"
    history_url = "https://botrade-hyperliquid.onrender.com/api/defi/history.csv"

    msg = (
        "📊 *PLANILHA AO VIVO DE RENDIMENTOS & PNL (SEM ESTIMATIVAS)*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "Sua planilha atualiza **dinamicamente a todo momento que você abre** com:\n"
        "• *Saldo Atual:* Patrimônio total atualizado em USD e BRL\n"
        "• *Aporte Inicial:* $11,568.85 USD (Depósito #7732601)\n"
        "• *Valorização ou Desvalorização:* PnL exato em $ e %\n"
        "• *Rendimentos Reais Acumulados:* AERO minerado + taxas de swap reais\n"
        "• *Referência do Dia Anterior:* Rendimento real de ontem (~23.8 AERO / +$21.09 USD)\n"
        "• *Faixa de Liquidez:* Piso ($2,596.73), Teto ($2,798.98) e distâncias\n"
        "• *Saídas do Range:* Contador persistente de quantas vezes saiu da faixa\n\n"
        "🟢 *OPÇÃO 1: GOOGLE PLANILHAS (AO VIVO NO NAVEGADOR/CELULAR)*\n"
        "1. Abra uma nova planilha no Google Sheets (`sheets.new`)\n"
        "2. Na célula **A1**, cole a fórmula abaixo:\n\n"
        f"`=IMPORTDATA(\"{sheet_url}\")`\n\n"
        "_Pronto! Toda vez que você abrir a planilha, o Google Sheets busca os dados mais recentes do servidor!_\n\n"
        "📁 *OPÇÃO 2: ARQUIVOS CSV EM ANEXO*\n"
        "Enviando abaixo os arquivos para abrir direto no Excel ou Bloco de Notas:"
    )

    markup = {
        "inline_keyboard": [
            [{"text": "🌐 Abrir Painel Web (/planilha)", "url": web_dashboard_url}],
            [{"text": "📥 Baixar CSV ao Vivo", "url": sheet_url}],
            [{"text": "💰 Ver Rendimento Real", "callback_data": "defi_profit"}]
        ]
    }
    send_message(chat_id, msg, markup)

    # Send document files directly
    latest_file = ROOT / "data" / "defi_latest.csv"
    history_file = ROOT / "data" / "defi_history.csv"

    if latest_file.exists():
        send_document(chat_id, latest_file, caption="📊 Resumo Consolidado WETH/USDC (defi_latest.csv)")
    if history_file.exists():
        send_document(chat_id, history_file, caption="📈 Histórico Granular de Rendimentos & PnL (defi_history.csv)")


def handle_command(chat_id: int | str, text: str, message_id: int = None):
    cmd_parts = text.strip().split()
    cmd = cmd_parts[0].lower()

    # 1. MENU / AJUDA
    if cmd in ("/start", "/help", "/ajuda", "ajuda", "help", "menu"):
        msg = (
            "🏛️ *SENTINELA & TESOURARIA DEFI BOTRADE*\n\n"
            "Monitoramento 24/7 da pool WETH / USDC (Deposit #7732601) e Arbitragem Flash Loan:\n\n"
            "• `/arbitragem` ou `/arb` - ⚡ Radar de Spreads ao Vivo (Aerodrome, Uniswap v3, PancakeSwap)\n"
            "• `/planilha` ou `planilha` - 📊 Planilha ao vivo (Google Sheets automático e arquivos CSV)\n"
            "• `/lucro` ou `lucro` - 💰 Rendimento real acumulado e base de ontem (sem estimativas)\n"
            "• `/defi` ou `/pools` - 🎯 Radar da faixa ($2,596 ↔ $2,798), distâncias de piso/teto e saídas\n"
            "• `/saldo` ou `/status` - 💼 Saldo atualizado, composição e valorização/desvalorização\n"
            "• `/relatorio` ou `relatorio` - 📑 Resumo executivo de fechamento 24h\n\n"
            "_Toque diretamente nos botões interativos abaixo:_"
        )
        markup = {
            "inline_keyboard": [
                [{"text": "⚡ Radar Arbitragem (/arb)", "callback_data": "refresh_arbitrage"}, {"text": "📊 Planilha ao Vivo", "callback_data": "defi_sheet"}],
                [{"text": "💰 Rendimento Real (/lucro)", "callback_data": "defi_profit"}, {"text": "📡 Radar da Faixa (/defi)", "callback_data": "defi_treasury"}],
                [{"text": "💼 Saldo Atualizado (/saldo)", "callback_data": "refresh_status"}, {"text": "📑 Relatório 24h", "callback_data": "daily_report"}]
            ]
        }
        send_message(chat_id, msg, markup)
        return

    # 2. PLANILHA AO VIVO (GOOGLE SHEETS & EXCEL)
    if cmd in ("/planilha", "/excel", "/csv", "/sheets", "/sheet", "planilha", "excel", "csv", "sheets", "sheet") or "planilha" in text.lower():
        handle_planilha_command(chat_id)
        return

    # 3. LUCRO DEDICADO (REAL ACUMULADO + BASE ANTERIOR)
    if cmd in ("/lucro", "/lucros", "/rendimento", "/rendimentos", "/ganhos", "lucro", "lucros", "rendimento", "rendimentos", "ganhos", "quanto rendeu", "lucro de hoje") or "lucro" in text.lower() or "rendeu" in text.lower():
        text_out, markup = format_defi_profit_dashboard()
        send_message(chat_id, text_out, markup)
        return

    # 4. DEFI TREASURY / POOLS RADAR
    if cmd in ("/defi", "/tesouraria", "/pools", "/pool", "defi", "tesouraria", "pools", "pool") or "pool" in text.lower() or "faixa" in text.lower():
        text_out, markup = format_defi_message()
        send_message(chat_id, text_out, markup)
        return

    # 5. SALDO & STATUS DE ALOCAÇÃO
    if cmd in ("/saldo", "/status", "/posicoes", "/posições", "saldo", "status", "posicoes", "posições"):
        text_out, markup = format_defi_status_summary()
        send_message(chat_id, text_out, markup)
        return

    # 6. DIAGNÓSTICO VIRTUAL (DESMONTADA)
    if cmd in ("/virtual", "/krystal", "/rebalance", "virtual", "krystal", "rebalance", "rebalanceamento"):
        text_out, markup = format_virtual_rebalance_status()
        send_message(chat_id, text_out, markup)
        return

    # 7. RELATÓRIO 24H
    if cmd in ("/relatorio", "/report", "/resumo", "relatorio", "resumo"):
        text_out, markup = format_daily_report_message()
        send_message(chat_id, text_out, markup)
        return

    # 8. RADAR DE ARBITRAGEM DEFI ON-CHAIN
    if cmd in ("/arbitragem", "/arb", "arbitragem", "arb") or "arbitragem" in text.lower():
        from defi_arbitrage_engine import scan_all_markets, format_radar_report, record_opportunities
        send_message(chat_id, "⚡ *Consultando pools da Base em tempo real (Aerodrome, Uniswap, PancakeSwap)...*")
        opps = scan_all_markets()
        record_opportunities(opps)
        rep = format_radar_report(opps)
        markup = {
            "inline_keyboard": [
                [{"text": "🌐 Abrir Cockpit em Tela", "url": "https://botrade-hyperliquid.onrender.com/arbitragem"}, {"text": "🔄 Atualizar Spreads", "callback_data": "refresh_arbitrage"}],
                [{"text": "📊 Planilha ao Vivo", "callback_data": "defi_sheet"}, {"text": "💰 Rendimento da Pool", "callback_data": "defi_profit"}]
            ]
        }
        send_message(chat_id, rep, markup)
        return

    send_message(
        chat_id,
        f"❓ *Comando não reconhecido:* `{text}`\n\nDigite `/arbitragem` para ver spreads ao vivo, `/lucro` para o rendimento da pool, `/defi` para o radar da faixa ou `/ajuda` para o menu."
    )


def handle_callback_query(cq: dict):
    cq_id = cq.get("id")
    from_user = cq.get("from", {})
    chat_id = from_user.get("id")
    msg = cq.get("message", {})
    msg_id = msg.get("message_id")
    data = cq.get("data", "")

    if data == "refresh_arbitrage":
        answer_callback(cq_id, "Buscando spreads na Base...")
        from defi_arbitrage_engine import scan_all_markets, format_radar_report, record_opportunities
        opps = scan_all_markets()
        record_opportunities(opps)
        rep = format_radar_report(opps)
        markup = {
            "inline_keyboard": [
                [{"text": "🌐 Abrir Cockpit em Tela", "url": "https://botrade-hyperliquid.onrender.com/arbitragem"}, {"text": "🔄 Atualizar Spreads", "callback_data": "refresh_arbitrage"}],
                [{"text": "📊 Planilha ao Vivo", "callback_data": "defi_sheet"}, {"text": "💰 Rendimento da Pool", "callback_data": "defi_profit"}]
            ]
        }
        if msg_id:
            edit_message(chat_id, msg_id, rep, markup)
        else:
            send_message(chat_id, rep, markup)
        return

    if data in ("defi_profit", "profit_summary"):
        answer_callback(cq_id, "Calculando rendimento real...")
        text_out, markup = format_defi_profit_dashboard()
        if msg_id:
            edit_message(chat_id, msg_id, text_out, markup)
        else:
            send_message(chat_id, text_out, markup)
        return

    if data == "defi_treasury":
        answer_callback(cq_id, "Consultando radar da faixa...")
        text_out, markup = format_defi_message()
        if msg_id:
            edit_message(chat_id, msg_id, text_out, markup)
        else:
            send_message(chat_id, text_out, markup)
        return

    if data == "refresh_status":
        answer_callback(cq_id, "Atualizando saldo consolidado...")
        text_out, markup = format_defi_status_summary()
        if msg_id:
            edit_message(chat_id, msg_id, text_out, markup)
        else:
            send_message(chat_id, text_out, markup)
        return

    if data == "daily_report":
        answer_callback(cq_id, "Gerando fechamento 24h...")
        text_out, markup = format_daily_report_message()
        if msg_id:
            edit_message(chat_id, msg_id, text_out, markup)
        else:
            send_message(chat_id, text_out, markup)
        return

    if data == "defi_sheet":
        answer_callback(cq_id, "Gerando planilha ao vivo...")
        handle_planilha_command(chat_id)
        return

    answer_callback(cq_id)


def register_bot_commands():
    commands = [
        {"command": "planilha", "description": "📊 Planilha ao vivo (atualiza a todo momento)"},
        {"command": "arbitragem", "description": "⚡ Radar de arbitragem on-chain (spreads ao vivo)"},
        {"command": "lucro", "description": "💰 Rendimento real acumulado e base de ontem"},
        {"command": "defi", "description": "🎯 Radar da faixa ($2,596 a $2,798) e saídas"},
        {"command": "saldo", "description": "💼 Saldo consolidado e valorização patrimonial"},
        {"command": "relatorio", "description": "📑 Relatório de fechamento 24h"},
        {"command": "ajuda", "description": "❓ Menu interativo de comandos"}
    ]
    res = tg_api_call("setMyCommands", {"commands": commands})
    if res.get("ok"):
        print("[*] Comandos registrados com sucesso no menu '/' do Telegram!")
    else:
        print(f"[-] Aviso ao registrar comandos: {res.get('error')}")


def run_telegram_bot_daemon(poll_timeout: int = 25):
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip() or TOKEN
    if not bot_token:
        print("[Telegram Bot] AVISO: TELEGRAM_BOT_TOKEN não definido. Bot aguardando credenciais.")
        return

    register_bot_commands()
    print("[*] Iniciando Botrade Interactive Telegram Bot (Polling DeFi Ativo)...")
    last_update_id = 0

    while True:
        try:
            params = {"offset": last_update_id + 1, "timeout": poll_timeout, "allowed_updates": ["message", "callback_query"]}
            res = tg_api_call("getUpdates", params)

            if not res.get("ok"):
                time.sleep(3)
                continue

            updates = res.get("result", [])
            for upd in updates:
                last_update_id = max(last_update_id, upd.get("update_id", 0))

                if "message" in upd:
                    msg = upd["message"]
                    chat = msg.get("chat", {})
                    chat_id = chat.get("id")
                    text = msg.get("text", "")
                    if text and chat_id:
                        handle_command(chat_id, text, msg.get("message_id"))

                elif "callback_query" in upd:
                    handle_callback_query(upd["callback_query"])

        except Exception as e:
            print(f"[Telegram Bot Error]: {e}")
            time.sleep(4)


if __name__ == "__main__":
    if "--test-profit" in sys.argv:
        t, _ = format_defi_profit_dashboard()
        print(t)
    elif "--register" in sys.argv:
        register_bot_commands()
    else:
        run_telegram_bot_daemon()
