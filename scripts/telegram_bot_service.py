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
            "🎯 *OPTIONS DESK — BOTRADE BOT (PUT SPREADS)*\n\n"
            "Monitoramento 24/7 e Controle Total das suas operações com opções Put Spreads na Derive (Carteira Tangem):\n\n"
            "• `/travas` ou `/posicoes` - 💼 Relatório detalhado das suas travas ativas e PnL\n"
            "• `/perps` ou `/radar` - ⚡ *RADAR PERPÉTUOS DERIVE* (ADA, SOL, LINK, DOGE... Alavancado 10x)\n"
            "• `/entrar_perp <moeda>` - 🚀 Executar trade alavancado com Stop Loss e Take Profit automáticos\n"
            "• `/fechar` - 🛑 *ENCERRAMENTO DE EMERGÊNCIA* (Recompra e liquida trava na Derive imediatamente)\n"
            "• `/rolar` - 🔄 *ROLAGEM DE DEFESA* (Rola trava para próximo vencimento se mercado cair)\n"
            "• `/relatorio` ou `/status` - 📊 Resumo executivo de margem, crédito e distâncias\n"
            "• `/lucro` - 💰 Total de crédito embolsado e alvos de Take Profit\n"
            "• `/opcoes` - 🛡️ Radar de novas oportunidades com maior folga\n"
            "• `/iv` - 🌡️ Termômetro de Volatilidade do Bitcoin\n\n"
            "_Toque nos botões interativos abaixo para operar ou consultar:_"
        )
        markup = {
            "inline_keyboard": [
                [{"text": "⚡ Radar Perpétuos (/perps)", "callback_data": "refresh_perps"}, {"text": "💼 Minhas Travas (/travas)", "callback_data": "options_positions"}],
                [{"text": "🎯 Radar Opções (/opcoes)", "callback_data": "options_radar"}, {"text": "🔄 Rolar Trava", "callback_data": "menu_roll"}],
                [{"text": "📊 Relatório Geral", "callback_data": "daily_report"}, {"text": "🌡️ Termômetro IV", "callback_data": "options_iv"}],
                [{"text": "🛑 Fechar Trava", "callback_data": "menu_close"}, {"text": "🌐 Abrir Derive", "url": "https://app.derive.xyz"}]
            ]
        }
        send_message(chat_id, msg, markup)
        return

    # 2. RELATÓRIO DE TRAVAS / SALDO / STATUS / LUCRO (REDIRECIONADO EXCLUSIVAMENTE PARA OPTIONS)
    if cmd in ("/lucro", "/lucros", "/rendimento", "/rendimentos", "/ganhos", "lucro", "lucros", "rendimento", "rendimentos", "ganhos",
               "/saldo", "/status", "/posicoes", "/posições", "saldo", "status", "posicoes", "posições",
               "/relatorio", "/report", "/resumo", "relatorio", "resumo"):
        try:
            from telegram_options_monitor import generate_report
            rep = generate_report()
            markup = {
                "inline_keyboard": [
                    [{"text": "🔄 Atualizar Posições", "callback_data": "options_positions"}, {"text": "🎯 Radar Derive", "callback_data": "options_radar"}],
                    [{"text": "🌡️ Termômetro IV", "callback_data": "options_iv"}, {"text": "🌐 Abrir Derive", "url": "https://app.derive.xyz"}]
                ]
            }
            send_message(chat_id, rep, markup)
        except Exception as e:
            send_message(chat_id, f"❌ Erro ao gerar relatório de opções: {e}")
        return

    # 3. AVISO SOBRE POOLS DESMONTADAS
    if cmd in ("/defi", "/tesouraria", "/pools", "/pool", "defi", "tesouraria", "pools", "pool", "/planilha", "planilha"):
        msg = (
            "ℹ️ *POOLS DE LIQUIDEZ DESMONTADAS*\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "O capital das pools DeFi foi 100% resgatado e migrado com sucesso para a sua custódia segura na **Tangem** e para as operações de **Opções Put Spreads na Derive**.\n\n"
            "👉 Digite `/travas` ou `/relatorio` para acompanhar as suas operações ativas de Puts no Bitcoin!"
        )
        markup = {
            "inline_keyboard": [
                [{"text": "💼 Ver Minhas Travas (/travas)", "callback_data": "options_positions"}],
                [{"text": "📊 Relatório Consolidado", "callback_data": "daily_report"}]
            ]
        }
        send_message(chat_id, msg, markup)
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

    # 9. RADAR DE OPÇÕES DERIVE (TRAVAS DE SEGURANÇA ELÍDIO CARVALHO)
    if cmd in ("/opcoes", "/opções", "/options", "/trava", "opcoes", "opções", "options"):
        try:
            import options_desk
            matrix = options_desk.scan_decision_matrix("BTC")
            top = matrix.get('top_picks', {}).get('ultra_conservative', [])[:3]
            spot = matrix.get('spot_price', 0)
            
            lines = [
                "🎯 *OPTIONS DESK — RADAR DE MÁXIMA SEGURANÇA (DERIVE)*",
                "━━━━━━━━━━━━━━━━━━━━━━━━━━",
                f"• *Spot BTC:* `${spot:,.0f}`",
                f"• *Estratégia:* Trava de Alta com Puts (Elídio Carvalho)",
                "\n*TOP 3 TRAVAS COM MAIOR FOLGA DE QUEDA:*\n"
            ]
            for i, o in enumerate(top, 1):
                lines.append(
                    f"*{i}. {o['short_strike']:,.0f}P / {o['long_strike']:,.0f}P* ({o['expiry_formatted']} • {o['dte']}d)\n"
                    f"  🛡️ *Folga de Queda:* `+{o['cushion_pct']:.1f}%` (PoP: {o['pop']:.0f}%)\n"
                    f"  💰 *Crédito:* `+${o['net_credit']:,.1f} USDC` (ROM: {o['rom']:.1f}%)\n"
                    f"  🛑 *Breakeven:* `${o['breakeven']:,.0f}` (BTC precisa cair {o['cushion_pct']:.1f}%)\n"
                )
            lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━")
            lines.append("👉 Toque no botão abaixo para abrir a mesa e montar no painel:")
            
            markup = {
                "inline_keyboard": [
                    [{"text": "🌐 Abrir Mesa de Opções", "url": "https://botrade-hyperliquid.onrender.com/options"}],
                    [{"text": "💼 Ver Minhas Travas", "callback_data": "options_positions"}],
                    [{"text": "🌡️ Termômetro de Volatilidade", "callback_data": "options_iv"}]
                ]
            }
            send_message(chat_id, "\n".join(lines), markup)
        except Exception as e:
            send_message(chat_id, f"❌ *Erro ao consultar Options Desk:* {e}")
        return

    # 10. MINHAS TRAVAS / POSIÇÕES DE OPÇÕES ABERTAS
    if cmd in ("/travas", "/posicoes_opcoes", "/minhas_travas", "travas"):
        try:
            import options_desk
            raw_pos = options_desk.load_positions()
            active = [options_desk.evaluate_position(p) for p in raw_pos if p.get('status') == 'active']
            if not active:
                send_message(
                    chat_id,
                    "💼 *OPTIONS DESK — NENHUMA TRAVA ABERTA NO MOMENTO*\n\n"
                    "Você não possui travas ativas na custódia.\n"
                    "Digite `/opcoes` para ver as melhores oportunidades do momento!",
                    {"inline_keyboard": [[{"text": "🎯 Ver Oportunidades (/opcoes)", "callback_data": "options_radar"}]]}
                )
                return

            lines = [
                "💼 *OPTIONS DESK — SUAS TRAVAS ATIVAS*",
                "━━━━━━━━━━━━━━━━━━━━━━━━━━"
            ]
            for p in active:
                rec = p.get('recommendation', {})
                prog = p.get('profit_captured_pct', 0)
                lines.append(
                    f"• *{p.get('currency', 'BTC')} {p.get('short_strike', 0):,.0f}P / {p.get('long_strike', 0):,.0f}P* ({p.get('contracts', 0)} contratos)\n"
                    f"  📅 *Vencimento:* {p.get('expiry_formatted')} ({p.get('dte')}d restantes)\n"
                    f"  💰 *Crédito Inicial:* `+${p.get('initial_credit_total', 0):.2f} USDC`\n"
                    f"  📈 *Lucro Líquido Atual:* `+${p.get('current_pnl_total', 0):.2f}` (*{prog:.1f}%* do crédito)\n"
                    f"  🛡️ *Tolerância de Queda:* `-{p.get('max_tolerated_drop_pct', 0):.1f}%` (até ${p.get('breakeven_price', 0):,.0f})\n"
                    f"  🤖 *Status:* {rec.get('badge', 'EM ANDAMENTO')}\n"
                )
            lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━")
            lines.append("👉 _Toque no botão vermelho abaixo para fechar qualquer trava antecipadamente na Derive com 1 clique:_")
            kb = [
                [{"text": "🌐 Abrir no Painel Web", "url": "https://botrade-hyperliquid.onrender.com/options"}],
            ]
            for p in active:
                pos_id = p.get('id')
                s_k = p.get('short_strike', 0)
                l_k = p.get('long_strike', 0)
                kb.append([
                    {"text": f"🛑 Fechar Trava {s_k:,.0f}P", "callback_data": f"req_close_{pos_id}"},
                    {"text": f"🔄 Rolar {s_k:,.0f}P", "callback_data": f"sim_roll_{pos_id}"}
                ])
            kb.append([{"text": "🔄 Atualizar Posições", "callback_data": "options_positions"}])
            markup = {"inline_keyboard": kb}
            send_message(chat_id, "\n".join(lines), markup)
        except Exception as e:
            send_message(chat_id, f"❌ *Erro ao listar travas:* {e}")
        return

    # 10.1 FECHAR TRAVA MANUALMENTE (EMERGÊNCIA / ANTECIPAÇÃO)
    if cmd in ("/fechar", "/fechar_trava", "/encerrar", "/panico", "fechar", "encerrar", "panico"):
        try:
            import options_desk
            raw_pos = options_desk.load_positions()
            active = [p for p in raw_pos if p.get('status') == 'active']
            if not active:
                send_message(chat_id, "ℹ️ *Você não possui travas ativas na Derive para fechar no momento.*")
                return

            lines = [
                "🛑 *MESA DE EMERGÊNCIA — ENCERRAMENTO ANTECIPADO (DERIVE)*",
                "━━━━━━━━━━━━━━━━━━━━━━━━━━",
                "Selecione abaixo a trava que deseja **recomprar a mercado e encerrar imediatamente** on-chain na Derive:\n"
            ]
            kb = []
            for p in active:
                pos_id = p.get('id')
                s_k = p.get('short_strike', 0)
                l_k = p.get('long_strike', 0)
                cur = p.get('currency', 'BTC')
                lines.append(f"• *{cur} {s_k:,.0f}P / {l_k:,.0f}P* (`{pos_id}`)")
                kb.append([{"text": f"🛑 Confirmar Fechamento {s_k:,.0f}P/{l_k:,.0f}P", "callback_data": f"req_close_{pos_id}"}])

            kb.append([{"text": "❌ Cancelar", "callback_data": "options_positions"}])
            send_message(chat_id, "\n".join(lines), {"inline_keyboard": kb})
        except Exception as e:
            send_message(chat_id, f"❌ Erro ao processar comando de fechamento: {e}")
        return

    # 10.2 ROLAR TRAVA DEFENSIVA
    if cmd in ("/rolar", "/rolagem", "rolar", "rolagem"):
        try:
            import options_desk
            raw_pos = options_desk.load_positions()
            active = [p for p in raw_pos if p.get('status') == 'active']
            if not active:
                send_message(chat_id, "ℹ️ *Você não possui travas ativas na Derive para rolar no momento.*")
                return

            lines = [
                "🔄 *MESA DEFENSIVA — ROLAGEM DE TRAVA (DERIVE)*",
                "━━━━━━━━━━━━━━━━━━━━━━━━━━",
                "Selecione a trava que deseja simular e rolar para defender contra quedas:\n"
            ]
            kb = []
            for p in active:
                pos_id = p.get('id')
                s_k = p.get('short_strike', 0)
                l_k = p.get('long_strike', 0)
                lines.append(f"• *BTC {s_k:,.0f}P / {l_k:,.0f}P* (`{pos_id}`)")
                kb.append([{"text": f"🔄 Simular Rolagem {s_k:,.0f}P", "callback_data": f"sim_roll_{pos_id}"}])

            kb.append([{"text": "❌ Cancelar", "callback_data": "options_positions"}])
            send_message(chat_id, "\n".join(lines), {"inline_keyboard": kb})
        except Exception as e:
            send_message(chat_id, f"❌ Erro ao processar rolagem: {e}")
        return

    # 10.3 MODO DESENVOLVEDOR — CRIAR / MODIFICAR CÓDIGO VIA ANTIGRAVITY CLI
    if cmd in ("/dev", "/codar", "/code", "/codigo"):
        instrucao = " ".join(cmd_parts[1:]).strip()
        if not instrucao:
            send_message(
                chat_id,
                "ℹ️ *MODO DESENVOLVEDOR (ANTIGRAVITY CODE ENGINE)*\n\n"
                "Para pedir ao Antigravity para criar ou alterar código, digite:\n"
                "`/dev <sua instrução>`\n\n"
                "*Exemplos:*\n"
                "• `/dev Adicione um log no arquivo options_desk.py`\n"
                "• `/dev Crie um script para calcular o retorno anualizado das travas`\n"
                "• `/dev Verifique os últimos 10 logs de erro do sistema`"
            )
            return

        send_message(chat_id, f"🛠️ *Antigravity iniciando tarefa no projeto...*\n_\"{instrucao}\"_\n\n⏳ Analisando arquivos e aplicando alterações...")
        try:
            import subprocess
            proc = subprocess.run(
                ["/usr/local/bin/agy", "-p", instrucao, "--dangerously-skip-permissions"],
                cwd="/home/ubuntu/botrade",
                capture_output=True,
                text=True,
                timeout=120
            )
            out = proc.stdout.strip() or proc.stderr.strip() or "Tarefa executada com sucesso pelo Antigravity."
            if len(out) > 3800:
                out = out[:3800] + "\n\n... (saída longa truncada)"
            send_message(chat_id, f"🤖 *Resultado do Antigravity (VPS):*\n\n{out}")
        except subprocess.TimeoutExpired:
            send_message(chat_id, "⚠️ A tarefa no código levou mais de 2 minutos e foi pausada.")
        except Exception as e:
            send_message(chat_id, f"❌ Erro na execução do Antigravity: {e}")
        return

    # 11. TERMÔMETRO DE VOLATILIDADE (IV RANK)
    if cmd in ("/volatilidade", "/iv", "volatilidade", "iv"):
        try:
            import options_desk
            iv = options_desk.get_iv_regime("BTC")
            spot = options_desk.get_spot_price("BTC")
            lines = [
                "🌡️ *TERMÔMETRO QUANT DE VOLATILIDADE (BTC)*",
                "━━━━━━━━━━━━━━━━━━━━━━━━━━",
                f"• *Spot BTC:* `${spot:,.0f}`",
                f"• *IV Implícita (ATM):* `{iv['atm_iv_pct']}%`",
                f"• *IV Rank Percentil:* `{iv['iv_rank']}%`",
                f"• *Put Skew:* `{iv['put_skew_pct']:+.1f}%`",
                f"• *Diagnóstico:* {iv['badge']}",
                f"\n💡 *Orientação da Mesa:*\n{iv['advice']}\n",
                "━━━━━━━━━━━━━━━━━━━━━━━━━━"
            ]
            markup = {
                "inline_keyboard": [
                    [{"text": "🎯 Ver Travas Adequadas (/opcoes)", "callback_data": "options_radar"}],
                    [{"text": "🌐 Abrir Options Desk", "url": "https://botrade-hyperliquid.onrender.com/options"}]
                ]
            }
            send_message(chat_id, "\n".join(lines), markup)
        except Exception as e:
            send_message(chat_id, f"❌ *Erro ao consultar IV:* {e}")
        return

    # 11.2 RADAR DE PERPÉTUOS DERIVE (SNIPER 5Y SPECIALIST — SUB #116270)
    if cmd in ("/perps", "/perp", "/sniper", "/radar", "perps", "perp", "sniper", "radar"):
        try:
            import derive_perp_sniper
            status = derive_perp_sniper.get_full_perp_sniper_status(force_scan=True)
            acct = status.get("account_isolation", {})
            radar = status.get("radar", [])
            cash = acct.get("total_cash_usdc", 265.18)
            free = acct.get("free_margin_total_usdc", 265.18)
            open_perps = acct.get("perp_positions", [])

            lines = [
                "⚡ *DERIVE PERP SNIPER — RADAR AO VIVO (SUB #116270)*",
                "━━━━━━━━━━━━━━━━━━━━━━━━━━",
                f"• *Saldo na Subconta:* `${cash:,.2f} USDC` (Margem Livre: `${free:,.2f}`)",
                f"• *Alavancagem Padrão:* `10x Isolada` (Stop Loss Dinâmico ATR)",
                f"• *Slots em Uso:* `{len(open_perps)}/2` posições ativas\n"
            ]

            if open_perps:
                lines.append("*POSIÇÕES ATIVAS SENDO ACOMPANHADAS:*")
                for p in open_perps:
                    pnl_sign = "+" if p.get("unrealized_pnl_usd", 0) >= 0 else ""
                    lines.append(
                        f"• *{p['instrument_name']} ({p['side']})* | Entrada: `${p['entry_price']}`\n"
                        f"  PnL Atual: `{pnl_sign}${p.get('unrealized_pnl_usd', 0):.2f}` (`{p.get('roe_pct', 0):+.1f}% ROE`)\n"
                        f"  🛑 SL: `${p.get('sl_price', '—')}` | 🎯 TP: `${p.get('tp_price', '—')}`"
                    )
                lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

            lines.append("*RADAR DE ATIVOS DERIVE (PRONTIDÃO PARA ENTRAR):*")
            kb = []
            for r in radar[:6]:
                score = r.get("readiness_score", 0)
                coin = r.get("coin")
                side = r.get("projected_side", "—")
                icon = "🔥" if score >= 90 else ("🟡" if score >= 70 else "⚪")
                sl = r.get("projected_sl", 0)
                tp = r.get("projected_tp", 0)
                lines.append(
                    f"{icon} *{coin}-PERP* ({r.get('timeframe')}) • Score: `{score:.0f}/100`\n"
                    f"  • Preço: `${r.get('mark_price')}` | Projeção: *{side}*\n"
                    f"  • 🛑 SL: `${sl:.4f}` | 🎯 TP: `${tp:.4f}`\n"
                    f"  • Gatilho: _{r.get('signal_reason', 'Aguardando confluência')}_\n"
                )
                if score >= 70:
                    kb.append([{"text": f"🚀 Entrar em {coin}-PERP ({side})", "callback_data": f"req_perp_{coin}"}])

            lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━")
            lines.append("👉 Toque no botão acima para autorizar a entrada ou digite:\n`/entrar_perp <moeda>` (Ex: `/entrar_perp ADA`)")

            kb.append([{"text": "🔄 Atualizar Radar", "callback_data": "refresh_perps"}])
            send_message(chat_id, "\n".join(lines), {"inline_keyboard": kb})
        except Exception as e:
            send_message(chat_id, f"❌ Erro ao consultar radar de perpétuos: {e}")
        return

    # 11.3 EXECUTAR ENTRADA PERP MANUALMENTE
    if cmd in ("/entrar_perp", "/operar_perp", "/comprar_perp", "/vender_perp"):
        if len(cmd_parts) < 2:
            send_message(chat_id, "ℹ️ *Uso do Comando:*\n`/entrar_perp <MOEDA>`\n\n*Exemplos:*\n• `/entrar_perp ADA`\n• `/entrar_perp LINK`\n• `/entrar_perp SOL`")
            return
        coin_target = cmd_parts[1].upper().replace("-PERP", "")
        send_message(chat_id, f"⚡ *Preparando entrada em {coin_target}-PERP na Derive...*")
        try:
            import derive_perp_sniper
            ev = derive_perp_sniper.evaluate_coin_specialist(coin_target)
            side = ev.get("projected_side", "LONG") if ev else "LONG"
            res = derive_perp_sniper.execute_derive_perp_entry(coin_target, side, manual=True)
            if res.get("success"):
                send_message(chat_id, f"✅ *Ordem enviada com sucesso para {coin_target}-PERP!*\n\n{res.get('message', '')}")
            else:
                send_message(chat_id, f"⚠️ *Não foi possível executar:* {res.get('error')}")
        except Exception as e:
            send_message(chat_id, f"❌ Erro na execução: {e}")
        return

    # 12. PERGUNTA LIVRE / CHAT COM A IA (ANTIGRAVITY / GEMINI) OU VÍDEO DO YOUTUBE
    try:
        from google import genai
        from google.genai import types
        import re
        from ai_context import get_live_project_context

        ai_key = os.environ.get("GEMINI_API_KEY", "").strip()
        if not ai_key:
            env_file = ROOT / ".env"
            if env_file.exists():
                for line in env_file.read_text(encoding="utf-8").splitlines():
                    if line.startswith("GEMINI_API_KEY="):
                        ai_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                        break
        client = genai.Client(api_key=ai_key)

        def generate_with_fallback(contents):
            for model_name in ["gemini-3.8-flash", "gemini-3.5-flash-lite"]:
                try:
                    r = client.models.generate_content(model=model_name, contents=contents)
                    if r and r.text:
                        return r.text.strip(), model_name
                except Exception as err:
                    print(f"[-] Aviso: modelo {model_name} indisponivel ({err}). Tentando fallback...")
            raise RuntimeError("Nenhum modelo Gemini respondeu no momento.")

        # Detecta se há link do YouTube na mensagem
        yt_match = re.search(r'(https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)[a-zA-Z0-9_\-]+[^\s]*)', text)
        if yt_match:
            yt_url = yt_match.group(1).strip()
            user_instruction = text.replace(yt_url, "").strip() or "Faça um resumo executivo completo e estruturado deste vídeo, destacando a tese, estratégias operacionais, indicadores ou lições práticas de mercado."
            send_message(chat_id, "🎬 *Link do YouTube detectado!*\n_Assistindo e processando o vídeo com a inteligência multimodal do Gemini... Isso pode levar alguns segundos._")

            yt_part = types.Part.from_uri(file_uri=yt_url, mime_type="video/*")
            prompt_video = (
                "Você é o analista quantitativo do projeto Botrade. O usuário enviou o vídeo acima para análise detalhada.\n"
                f"INSTRUÇÃO DO USUÁRIO: {user_instruction}\n\n"
                "Estruture sua resposta em markdown claro e agradável:\n"
                "1. 📌 Resumo da Tese / Ideia Central\n"
                "2. 📊 Estratégias, Setups ou Indicadores citados\n"
                "3. ⚠️ Riscos e Pontos de Atenção\n"
                "4. 💡 Conclusão & Aplicação Prática para a nossa mesa de trading"
            )

            ai_reply, used_model = generate_with_fallback([yt_part, prompt_video])
            # Envia em blocos se exceder o limite do Telegram (4096 caracteres)
            if len(ai_reply) > 4000:
                chunks = [ai_reply[i:i+3900] for i in range(0, len(ai_reply), 3900)]
                for idx, c in enumerate(chunks, 1):
                    send_message(chat_id, f"🎬 *Análise do Vídeo (Parte {idx}/{len(chunks)} • {used_model}):*\n\n{c}")
            else:
                send_message(chat_id, f"🎬 *Análise do Vídeo do YouTube ({used_model}):*\n\n{ai_reply}")
            return

        # Chat normal com contexto do projeto
        send_message(chat_id, "🤖 _Consultando Antigravity / Gemini com dados ao vivo da mesa..._")
        sys_ctx = get_live_project_context()
        full_prompt = f"{sys_ctx}\n\nPERGUNTA DO USUÁRIO NO TELEGRAM:\n{text}"

        ai_reply, used_model = generate_with_fallback(full_prompt)
        send_message(chat_id, f"🤖 *Antigravity / Gemini ({used_model}):*\n\n{ai_reply}")
        return
    except Exception as e:
        send_message(
            chat_id,
            f"❌ *Erro ao processar mensagem com a IA:* {e}\n\nSe enviou um link, verifique se o vídeo é público."
        )


def handle_callback_query(cq: dict):
    cq_id = cq.get("id")
    from_user = cq.get("from", {})
    chat_id = from_user.get("id")
    msg = cq.get("message", {})
    msg_id = msg.get("message_id")
    data = cq.get("data", "")

    if data == "options_radar":
        answer_callback(cq_id, "Buscando travas na Derive...")
        handle_command(chat_id, "/opcoes")
        return

    if data == "options_positions":
        answer_callback(cq_id, "Carregando travas ativas...")
        handle_command(chat_id, "/travas")
        return

    if data == "options_iv":
        answer_callback(cq_id, "Calculando volatilidade...")
        handle_command(chat_id, "/iv")
        return

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

    if data in ("daily_report", "defi_profit", "profit_summary", "refresh_status"):
        answer_callback(cq_id, "Gerando relatório de opções...")
        from telegram_options_monitor import generate_report
        rep = generate_report()
        markup = {
            "inline_keyboard": [
                [{"text": "💼 Minhas Travas (/travas)", "callback_data": "options_positions"}, {"text": "🎯 Radar Derive", "callback_data": "options_radar"}],
                [{"text": "🌡️ Termômetro IV", "callback_data": "options_iv"}, {"text": "🌐 Abrir Derive", "url": "https://app.derive.xyz"}]
            ]
        }
        if msg_id:
            edit_message(chat_id, msg_id, rep, markup)
        else:
            send_message(chat_id, rep, markup)
        return

    if data in ("defi_treasury", "defi_sheet"):
        answer_callback(cq_id, "Pools desmontadas")
        msg = (
            "ℹ️ *POOLS DE LIQUIDEZ DESMONTADAS*\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "O capital das pools DeFi foi 100% resgatado e migrado para a custódia segura na **Tangem** e para as operações de **Opções Put Spreads na Derive**.\n\n"
            "👉 Use os botões abaixo para ver suas travas ativas no Bitcoin:"
        )
        markup = {
            "inline_keyboard": [
                [{"text": "💼 Ver Minhas Travas (/travas)", "callback_data": "options_positions"}],
                [{"text": "📊 Relatório Consolidado", "callback_data": "daily_report"}]
            ]
        }
        if msg_id:
            edit_message(chat_id, msg_id, msg, markup)
        else:
            send_message(chat_id, msg, markup)
        return

    if data == "menu_close":
        answer_callback(cq_id, "Abrindo mesa de emergência...")
        handle_command(chat_id, "/fechar")
        return

    if data == "menu_roll":
        answer_callback(cq_id, "Abrindo mesa defensiva...")
        handle_command(chat_id, "/rolar")
        return

    # Pedido de confirmação de fechamento
    if data.startswith("req_close_"):
        target_id = data.replace("req_close_", "")
        answer_callback(cq_id, "Preparando confirmação...")
        try:
            import options_desk
            raw_pos = options_desk.load_positions()
            pos = next((x for x in raw_pos if x.get("id") == target_id), None)
            if not pos:
                send_message(chat_id, "❌ Trava não encontrada.")
                return

            short_k = pos.get("short_strike", 0)
            long_k = pos.get("long_strike", 0)
            cur = pos.get("currency", "BTC")
            contracts = pos.get("contracts", 0)
            sub_id = pos.get("live_details", {}).get("subaccount_id") or pos.get("subaccount_id", 116804)

            prompt_msg = (
                "⚠️ *CONFIRMAÇÃO DE FECHAMENTO ANTECIPADO (DERIVE)* ⚠️\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"Você está prestes a liquidar a mercado a seguinte trava:\n\n"
                f"• *Par:* `{cur} {short_k:,.0f}P / {long_k:,.0f}P`\n"
                f"• *Vencimento:* `{pos.get('expiry')}`\n"
                f"• *Contratos:* `{contracts}` {cur}\n"
                f"• *Subconta Derive:* `#{sub_id}`\n\n"
                "Ao confirmar, o robô enviará ordens taker imediatas para **recomprar a perna vendida** e eliminar todo o risco on-chain, liberando a margem da sua custódia Tangem.\n\n"
                "*DESEJA EXECUTAR O FECHAMENTO AGORA?*"
            )
            markup = {
                "inline_keyboard": [
                    [{"text": "🚨 SIM, LIQUIDAR NA DERIVE AGORA", "callback_data": f"do_close_{target_id}"}],
                    [{"text": "❌ Cancelar e Manter Ativa", "callback_data": "options_positions"}]
                ]
            }
            if msg_id:
                edit_message(chat_id, msg_id, prompt_msg, markup)
            else:
                send_message(chat_id, prompt_msg, markup)
        except Exception as e:
            send_message(chat_id, f"❌ Erro ao preparar confirmação: {e}")
        return

    # Execução on-chain de fechamento
    if data.startswith("do_close_"):
        target_id = data.replace("do_close_", "")
        answer_callback(cq_id, "Enviando ordens para a Derive...")
        send_message(chat_id, "⏳ *Executando fechamento on-chain na Derive... Aguarde confirmação imediata.*")
        try:
            import options_desk
            raw_pos = options_desk.load_positions()
            pos = next((x for x in raw_pos if x.get("id") == target_id), None)
            if not pos:
                send_message(chat_id, "❌ Trava não encontrada.")
                return

            pos_wallet = pos.get("live_details", {}).get("wallet") or pos.get("wallet")
            pos_sub = pos.get("live_details", {}).get("subaccount_id") or pos.get("subaccount_id")
            res = options_desk.close_derive_spread_order(
                currency=pos.get("currency", "BTC"),
                expiry=str(pos.get("expiry")),
                short_strike=float(pos.get("short_strike")),
                long_strike=float(pos.get("long_strike")),
                contracts=float(pos.get("contracts")),
                wallet_address=pos_wallet,
                subaccount_id=pos_sub
            )
            if res.get("success"):
                pos["status"] = "closed"
                pos["closed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                pos["close_details"] = res
                cost = float(res.get("cost_to_close_total", 0.0))
                realized_pnl = float(pos.get("initial_credit_total", 0.0)) - cost
                pos["realized_pnl_usd"] = round(realized_pnl, 2)
                options_desk.save_positions(raw_pos)
                options_desk.log_audit("MANUAL_TELEGRAM_EMERGENCY_CLOSE", {"pos_id": target_id, "res": res, "realized_pnl": realized_pnl})

                success_msg = (
                    "✅ *TRAVA ENCERRADA COM SUCESSO NA DERIVE!* 🏁\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"• *Par:* BTC {pos.get('short_strike'):,.0f}P / {pos.get('long_strike'):,.0f}P\n"
                    f"• *Subconta:* #{pos_sub}\n"
                    f"• *Crédito Recebido Inicialmente:* `+${pos.get('initial_credit_total', 0):.2f} USDC`\n"
                    f"• *Custo de Recompra:* `${cost:.2f} USDC`\n"
                    f"• *Resultado Líquido Realizado:* *`{'+' if realized_pnl >= 0 else ''}${realized_pnl:.2f} USDC`*\n"
                    f"• *Margem:* 🟢 *100% Desbloqueada e Salva!*\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━"
                )
                markup = {"inline_keyboard": [[{"text": "💼 Ver Minhas Travas", "callback_data": "options_positions"}]]}
                send_message(chat_id, success_msg, markup)
            else:
                send_message(chat_id, f"❌ *Falha no fechamento on-chain da Derive:* {res.get('error')}")
        except Exception as e:
            send_message(chat_id, f"❌ Erro crítico ao fechar trava: {e}")
        return

    # Simulação de rolagem
    if data.startswith("sim_roll_"):
        target_id = data.replace("sim_roll_", "")
        answer_callback(cq_id, "Calculando opções de rolagem...")
        try:
            import options_desk
            sim = options_desk.simulate_roll(target_id)
            if not sim.get("success"):
                send_message(chat_id, f"❌ Não foi possível simular rolagem: {sim.get('error')}")
                return

            opts = sim.get("roll_options", [])
            lines = [
                f"🛡️ *SIMULAÇÃO DE ROLAGEM DEFENSIVA:*",
                f"• *Trava Atual:* BTC {sim.get('current_short_strike'):,.0f}P ({sim.get('current_dte')}d restantes)",
                f"• *Custo para Fechar Atual:* `${sim.get('close_cost_total'):.2f} USDC`",
                "━━━━━━━━━━━━━━━━━━━━━━━━━━",
                "*OPÇÕES DE ROLAGEM COM CRÉDITO OU DEFESA:*\n"
            ]
            kb = []
            for i, o in enumerate(opts[:3], 1):
                tgt_exp = o['target_expiry']
                tgt_short = o.get('short_strike', sim.get('current_short_strike'))
                net_cost = o['net_roll_cost']
                cost_str = f"Crédito: +${abs(net_cost):.2f}" if net_cost <= 0 else f"Custo: -${net_cost:.2f}"
                lines.append(
                    f"*{i}. Vcto: {tgt_exp} ({o['new_dte']}d)* — Strike: ${tgt_short:,.0f}P\n"
                    f"   • *Balanço:* `{cost_str}` | *Folga:* `+{o.get('new_cushion_pct', 0):.1f}%`\n"
                )
                kb.append([{"text": f"🛡️ Rolar para {tgt_exp} (${tgt_short:,.0f}P)", "callback_data": f"do_roll_{target_id}_{tgt_exp}_{int(tgt_short)}"}])

            kb.append([{"text": "❌ Cancelar", "callback_data": "options_positions"}])
            send_message(chat_id, "\n".join(lines), {"inline_keyboard": kb})
        except Exception as e:
            send_message(chat_id, f"❌ Erro ao simular rolagem: {e}")
        return

    # Execução de rolagem
    if data.startswith("do_roll_"):
        parts = data.split("_")
        target_id = parts[2]
        target_exp = parts[3]
        target_short = float(parts[4]) if len(parts) > 4 else None
        answer_callback(cq_id, "Executando rolagem...")
        send_message(chat_id, "⏳ *Executando rolagem defensiva na Derive... Aguarde.*")
        try:
            import options_desk
            res = options_desk.execute_roll(target_id, target_exp, target_short_strike=target_short, is_automated=False)
            if res.get("success"):
                send_message(chat_id, f"✅ *ROLAGEM EXECUTADA COM SUCESSO!*\n\n{res.get('message', '')}")
            else:
                send_message(chat_id, f"❌ *Falha na rolagem:* {res.get('error')}")
        except Exception as e:
            send_message(chat_id, f"❌ Erro ao executar rolagem: {e}")
        return

    if data == "refresh_perps":
        answer_callback(cq_id, "Atualizando radar...")
        handle_command(chat_id, "/perps")
        return

    if data.startswith("req_perp_"):
        coin = data.replace("req_perp_", "").upper()
        answer_callback(cq_id, f"Preparando {coin}...")
        try:
            import derive_perp_sniper
            ev = derive_perp_sniper.evaluate_coin_specialist(coin)
            side = ev.get("projected_side", "LONG") if ev else "LONG"
            px = ev.get("mark_price", 0) if ev else 0
            sl = ev.get("projected_sl", 0) if ev else 0
            tp = ev.get("projected_tp", 0) if ev else 0
            msg = (
                f"🚀 *CONFIRMAÇÃO DE ENTRADA ALAVANCADA*\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"• Contrato: *{coin}-PERP ({side})*\n"
                f"• Subconta: `#116270` ($265 USDC livres)\n"
                f"• Preço Atual: `${px}`\n"
                f"• 🛑 Stop Loss Automático: `${sl:.4f}`\n"
                f"• 🎯 Take Profit Alvo: `${tp:.4f}`\n"
                f"• Alavancagem: *10x Isolada*\n\n"
                f"Deseja enviar a ordem a mercado agora e ativar o monitoramento de saída no lucro ou stop?"
            )
            kb = [
                [{"text": f"✅ Confirmar Entrada em {coin}", "callback_data": f"exec_perp_{coin}"}],
                [{"text": "❌ Cancelar", "callback_data": "refresh_perps"}]
            ]
            send_message(chat_id, msg, {"inline_keyboard": kb})
        except Exception as e:
            send_message(chat_id, f"❌ Erro ao preparar entrada: {e}")
        return

    if data.startswith("exec_perp_"):
        coin = data.replace("exec_perp_", "").upper()
        answer_callback(cq_id, f"Enviando ordem {coin}...")
        send_message(chat_id, f"⏳ *Executando ordem a mercado para {coin}-PERP na Derive...*")
        try:
            import derive_perp_sniper
            ev = derive_perp_sniper.evaluate_coin_specialist(coin)
            side = ev.get("projected_side", "LONG") if ev else "LONG"
            res = derive_perp_sniper.execute_derive_perp_entry(coin, side, manual=True)
            if res.get("success"):
                send_message(chat_id, f"✅ *ORDEM EXECUTADA COM SUCESSO!* 🚀\n\n{res.get('message', '')}")
            else:
                send_message(chat_id, f"⚠️ *Não foi possível executar:* {res.get('error')}")
        except Exception as e:
            send_message(chat_id, f"❌ Erro na execução de {coin}: {e}")
        return

    answer_callback(cq_id)


def register_bot_commands():
    commands = [
        {"command": "perps", "description": "⚡ Radar Perpétuos Derive (ADA, SOL, LINK... 10x)"},
        {"command": "entrar_perp", "description": "🚀 Executar entrada alavancada com SL/TP"},
        {"command": "travas", "description": "💼 Suas travas ativas, PnL e botão de fechar"},
        {"command": "dev", "description": "🛠️ Criar ou alterar código via Antigravity Engine"},
        {"command": "fechar", "description": "🛑 Fechar trava imediatamente na Derive (Emergência)"},
        {"command": "rolar", "description": "🔄 Rolar trava para defender de quedas"},
        {"command": "opcoes", "description": "🎯 Radar de novas oportunidades com maior folga"},
        {"command": "relatorio", "description": "📊 Relatório executivo de margem e segurança"},
        {"command": "lucro", "description": "💰 Crédito embolsado e alvos de Take Profit"},
        {"command": "iv", "description": "🌡️ Termômetro de Volatilidade do Bitcoin"},
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
