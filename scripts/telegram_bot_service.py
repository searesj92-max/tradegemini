#!/usr/bin/env python3
"""
Botrade Interactive Bidirectional Telegram Bot
Allows full institutional remote control of Hyperliquid trading operations:
- /status: Live balance, margin, active positions, ROE, macro regime, and sniper state.
- /lucro <COIN> or button: Harvests 50% profit, moves SL to BE (+0.2%), frees margin.
- /fechar <COIN> or button: Closes 100% of position at market and cancels trigger orders.
- /funding: Real-time Hyperliquid funding radar & short-squeeze candidates.
- /top: Mass universe 720d leaderboard and Gertrude champions.
- /pausar & /retomar: Controls the autonomous sniper engine.
- Interactive Inline Keyboards for 1-tap mobile execution.
"""

from __future__ import annotations

import argparse
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

from hyperliquid_executor import HyperliquidExecutor
from funding_radar import fetch_funding_radar
from universe_scanner import scan_universe, LEADERBOARD_FILE
from defi_treasury_tracker import format_defi_message


def tg_api_call(method: str, data: dict = None) -> dict:
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip() or TOKEN
    if not bot_token:
        return {"ok": False, "error": "TELEGRAM_BOT_TOKEN não configurado"}

    url = f"https://api.telegram.org/bot{bot_token}/{method}"
    payload = json.dumps(data, ensure_ascii=False).encode("utf-8") if data else None
    headers = {"Content-Type": "application/json; charset=utf-8", "User-Agent": "BotradeDesk/1.0"}
    
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


def get_macro_status_summary() -> str:
    from dashboard_server import get_cached_btc_macro_regime
    try:
        regime = get_cached_btc_macro_regime()
        label = regime.get("status_label", "🟢 NORMAL")
        reg_name = regime.get("regime_name", "Range Neutro")
        return f"{label} ({reg_name})"
    except Exception:
        return "🟢 Regime Operacional Normal"


def get_sniper_state() -> tuple[bool, str]:
    state_file = ROOT / "data" / "journal" / "auto_sniper_state.json"
    if state_file.exists():
        try:
            d = json.loads(state_file.read_text(encoding="utf-8"))
            paused = bool(d.get("paused", False))
            return paused, "⏸️ PAUSADO" if paused else "🟢 ATIVO (Monitorando Entradas)"
        except Exception:
            pass
    return False, "🟢 ATIVO (Monitorando Entradas)"


def set_sniper_state(paused: bool) -> bool:
    state_file = ROOT / "data" / "journal" / "auto_sniper_state.json"
    state_file.parent.mkdir(parents=True, exist_ok=True)
    cur = {}
    if state_file.exists():
        try:
            cur = json.loads(state_file.read_text(encoding="utf-8"))
        except Exception:
            pass
    cur["paused"] = paused
    cur["updated_at"] = datetime.now(timezone.utc).isoformat()
    state_file.write_text(json.dumps(cur, indent=2), encoding="utf-8")
    return True


def format_status_payload() -> tuple[str, dict]:
    executor = HyperliquidExecutor()
    st = executor.get_account_status()
    paused, sniper_label = get_sniper_state()
    macro_label = get_macro_status_summary()

    spot_val = float(st.get("spot_usdc_balance", 0.0))
    perps_val = float(st.get("perps_account_value", 0.0))
    equity = spot_val + perps_val
    used_margin = float(st.get("total_margin_used", 0.0))
    free_margin = float(st.get("free_margin", max(0.0, equity - used_margin)))
    margin_util = (used_margin / equity * 100) if equity > 0 else 0.0

    open_pos = st.get("open_positions", [])

    lines = [
        "🏛️ *BOTRADE QUANTITATIVE DESK — HYPERLIQUID*",
        "━━━━━━━━━━━━━━━━━━━━━━",
        f"💰 *Patrimônio Total:* `${equity:.2f} USDC`",
        f"  • Spot USDC: `${spot_val:.2f}`",
        f"  • Perps Garantia: `${perps_val:.2f}`",
        f"📊 *Margem em Uso:* `${used_margin:.2f}` ({margin_util:.1f}%)",
        f"💵 *Margem Livre Disponível:* `${free_margin:.2f} USDC`",
        f"🎯 *Auto-Sniper:* `{sniper_label}`",
        f"🌐 *Macro BTC:* `{macro_label}`",
        "━━━━━━━━━━━━━━━━━━━━━━",
        f"📍 *POSIÇÕES ABERTAS:* *{len(open_pos)}*"
    ]

    inline_kb = []

    if open_pos:
        for p in open_pos:
            c = p["coin"]
            side = p["side"]
            sz = p["size"]
            entry = float(p.get("entry_px", 0.0))
            roe = float(p.get("roe_pct", 0.0))
            pnl = float(p.get("unrealized_pnl", 0.0))
            mark = float(p.get("mark_px", 0.0))
            if mark <= 0:
                mark = entry + (pnl / sz if sz else 0)
            sl = p.get("sl_price")
            pnl_emoji = "🟢" if pnl >= 0 else "🔴"
            sign = "+" if pnl >= 0 else ""
            lev = float(p.get("leverage", 10))

            lines.append(f"\n• *{c}/USDC* ({side} {lev:.0f}x)")
            lines.append(f"  Lote: `{sz} {c}` | Entrada: `${entry:.4f}`")
            lines.append(f"  Preço Atual: `${mark:.4f}`")
            lines.append(f"  PnL: {pnl_emoji} *{sign}${pnl:.2f}* ({sign}{roe:.2f}% ROE)")
            if sl:
                lines.append(f"  🛡️ Stop Loss Ativo: `${sl:.4f}`")

            # Position-specific action buttons
            inline_kb.append([
                {"text": f"💰 Colher 50% ({c})", "callback_data": f"harvest:{c}"},
                {"text": f"🛑 Fechar 100% ({c})", "callback_data": f"close:{c}"}
            ])
    else:
        lines.append("\n_Nenhuma posição aberta no momento. O Sniper está rastreando oportunidades._")

    # Desk control buttons
    toggle_sniper_btn = {"text": "▶️ Retomar Sniper", "callback_data": "resume_sniper"} if paused else {"text": "⏸️ Pausar Sniper", "callback_data": "pause_sniper"}
    
    inline_kb.append([toggle_sniper_btn, {"text": "🔄 Atualizar", "callback_data": "refresh_status"}])
    inline_kb.append([
        {"text": "💰 Ver Lucro Realizado", "callback_data": "profit_summary"},
        {"text": "⚡ Radar Funding", "callback_data": "funding_radar"}
    ])

    return "\n".join(lines), {"inline_keyboard": inline_kb}


def format_profit_summary_message() -> tuple[str, dict]:
    executor = HyperliquidExecutor()
    st = executor.get_account_status()
    open_pos = st.get("open_positions", [])

    unrealized_total = sum(float(p.get("unrealized_pnl", 0.0)) for p in open_pos)

    tot_closed_pnl = 0.0
    tot_fees = 0.0
    wins = 0
    losses = 0
    recent_winners = []

    try:
        fills = executor.info.user_fills(executor.main_address)
        for f in fills:
            cpnl = float(f.get("closedPnl", 0.0))
            fee = float(f.get("fee", 0.0))
            tot_closed_pnl += cpnl
            tot_fees += fee
            if cpnl != 0:
                if cpnl > 0:
                    wins += 1
                else:
                    losses += 1
                if cpnl > 0 and len(recent_winners) < 6:
                    coin = f.get("coin")
                    recent_winners.append(f"• *{coin}*: `+${cpnl:.2f} USDC` (Taxa: `${fee:.3f}`)")
    except Exception:
        pass

    net_closed = tot_closed_pnl - tot_fees
    total_net = net_closed + unrealized_total
    total_trades = wins + losses
    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0.0

    pnl_emoji = "🟢" if total_net >= 0 else "🔴"
    sign = "+" if total_net >= 0 else ""

    lines = [
        "🏆 *CONSOLIDAÇÃO DE LUCRO — BOTRADE HYPERLIQUID*",
        f"Data: {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M UTC')}",
        "━━━━━━━━━━━━━━━━━━━━━━",
        f"💵 *LUCRO TOTAL LÍQUIDO:* {pnl_emoji} *{sign}${total_net:.2f} USDC*",
        "━━━━━━━━━━━━━━━━━━━━━━",
        f"✅ *Lucro Fechado (No Bolso):* `+${net_closed:.2f} USDC`",
        f"📈 *Lucro em Aberto (Posições Ativas):* `+${unrealized_total:.2f} USDC`",
        f"💸 *Taxas Totais Descontadas:* `${tot_fees:.2f} USDC`",
        f"🎯 *Taxa de Acerto Real:* *{win_rate:.1f}%* ({wins}V / {losses}D em {total_trades} parciais)",
        "━━━━━━━━━━━━━━━━━━━━━━",
        "📍 *Últimos Encerramentos com Lucro:*"
    ]
    if recent_winners:
        lines.extend(recent_winners)
    else:
        lines.append("  _Nenhum trade encerrado ainda._")

    if open_pos:
        lines.append("\n🔥 *Posições em Andamento Gerando Lucro:*")
        for p in open_pos:
            c = p["coin"]
            pnl = float(p.get("unrealized_pnl", 0.0))
            roe = float(p.get("roe_pct", 0.0))
            e_sign = "+" if pnl >= 0 else ""
            lines.append(f"  • *{c}*: {e_sign}${pnl:.2f} USDC ({e_sign}{roe:.1f}% ROE)")

    markup = {
        "inline_keyboard": [
            [{"text": "📊 Ver Saldo & Posições", "callback_data": "refresh_status"}],
            [{"text": "🔄 Atualizar Lucro", "callback_data": "profit_summary"}]
        ]
    }
    return "\n".join(lines), markup


def format_funding_radar_message() -> tuple[str, dict]:
    data = fetch_funding_radar(min_volume_usd=100000.0)
    top_sq = data.get("top_negative_squeeze", [])[:6]
    top_over = data.get("top_positive_overheated", [])[:4]

    lines = [
        "⚡ *RADAR DE FUNDING RATE & SQUEEZE (HYPERLIQUID)*",
        "Taxas pagas a cada 1 hora diretamente na exchange.",
        "━━━━━━━━━━━━━━━━━━━━━━",
        "🔥 *ALTO POTENCIAL DE SHORT SQUEEZE*",
        "_Shorts pagam juros pesados para Longs (Alta assimetria):_"
    ]

    for x in top_sq:
        c = x["coin"]
        apr = x["apr_pct"]
        daily = x["daily_pct"]
        oi_k = x["oi_usd"] / 1000.0
        lines.append(f"• *{c}*: `{apr:+.1f}% APR` ({daily:+.2f}%/dia) | OI: `${oi_k:.0f}k`")

    lines.append("\n⚠️ *MERCADOS SOBRECARREGADOS EM LONG*")
    lines.append("_Longs pagando custos altos por hora (Risco de correção):_")
    for x in top_over:
        c = x["coin"]
        apr = x["apr_pct"]
        daily = x["daily_pct"]
        lines.append(f"• *{c}*: `{apr:+.1f}% APR` ({daily:+.2f}%/dia)")

    reply_markup = {
        "inline_keyboard": [
            [{"text": "📊 Ver Status", "callback_data": "refresh_status"}, {"text": "🏆 Top Alphas", "callback_data": "top_alpha"}]
        ]
    }
    return "\n".join(lines), reply_markup


def format_top_alpha_message() -> tuple[str, dict]:
    cached = None
    if LEADERBOARD_FILE.exists():
        try:
            cached = json.loads(LEADERBOARD_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass

    if not cached or "leaderboard" not in cached:
        cached = scan_universe(limit=10, days=180, timeframe="4h")

    leaders = cached.get("leaderboard", [])[:6]
    days = cached.get("days", 180)
    tf = cached.get("timeframe", "4h")

    lines = [
        f"🏆 *LEADERBOARD DE ALPHA — VARREDURA 720d/180d*",
        f"Critérios de Governança Gertrude | Base: {days} dias ({tf})",
        "━━━━━━━━━━━━━━━━━━━━━━"
    ]

    for r in leaders:
        pnl_sign = "+" if r["net_profit_usd"] >= 0 else ""
        lines.append(
            f"*{r['rank']}. {r['coin']}* — {r['gertrude_badge']}\n"
            f"   Trades: `{r['total_trades']}` | Win: `{r['win_rate_pct']:.1f}%`\n"
            f"   Fator Lucro: `{r['profit_factor']:.2f}x` | Lucro Líq: `{pnl_sign}${r['net_profit_usd']:.2f}`\n"
            f"   Max Drawdown: `-{r['max_drawdown_pct']:.1f}%`"
        )

    reply_markup = {
        "inline_keyboard": [
            [{"text": "📊 Ver Status", "callback_data": "refresh_status"}, {"text": "⚡ Radar Funding", "callback_data": "funding_radar"}]
        ]
    }
    return "\n".join(lines), reply_markup


def format_daily_report_message() -> tuple[str, dict]:
    executor = HyperliquidExecutor()
    status = executor.get_account_status()
    perps_val = float(status.get("perps_account_value", 0.0))
    spot_val = float(status.get("spot_usdc_balance", 0.0))
    total_equity = perps_val + spot_val
    open_pos = status.get("open_positions", [])

    # Fetch recent fills to calculate closed trades & realized PnL in last 24h
    now_ts = time.time()
    day_ago_ms = int((now_ts - 86400) * 1000)
    realized_pnl_24h = 0.0
    closed_trades_count = 0
    wins_24h = 0

    try:
        fills = executor.info.user_fills(executor.main_address)
        recent_fills = [f for f in fills if int(f.get("time", 0)) >= day_ago_ms]
        for f in recent_fills:
            cpnl = float(f.get("closedPnl", 0.0))
            if cpnl != 0:
                realized_pnl_24h += cpnl
                closed_trades_count += 1
                if cpnl > 0:
                    wins_24h += 1
    except Exception:
        pass

    wr_24h = (wins_24h / closed_trades_count * 100.0) if closed_trades_count > 0 else 0.0
    pnl_emoji = "🟢" if realized_pnl_24h >= 0 else "🔴"
    sign = "+" if realized_pnl_24h >= 0 else ""

    lines = [
        "📑 *RELATÓRIO DIÁRIO DE FECHAMENTO — BOTRADE*",
        f"Data: {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M UTC')}",
        "━━━━━━━━━━━━━━━━━━━━━━",
        f"💰 *Patrimônio Total:* `${total_equity:.2f} USDC`",
        f"  • Spot USDC: `${spot_val:.2f}`",
        f"  • Perps Margin: `${perps_val:.2f}`",
        "━━━━━━━━━━━━━━━━━━━━━━",
        f"📊 *Desempenho Real (Últimas 24h):*",
        f"  • PnL Realizado: {pnl_emoji} *{sign}${realized_pnl_24h:.2f} USDC*",
        f"  • Trades Fechados: *{closed_trades_count}* ({wins_24h}W / {max(0, closed_trades_count - wins_24h)}L)",
        f"  • Taxa de Acerto: *{wr_24h:.1f}%*",
        "━━━━━━━━━━━━━━━━━━━━━━",
        f"📍 *Posições Ativas no Momento:* *{len(open_pos)}*"
    ]

    for p in open_pos:
        c = p["coin"]
        side = p["side"]
        pnl = p["unrealized_pnl"]
        roe = p["roe_pct"]
        e_sign = "+" if pnl >= 0 else ""
        lines.append(f"  • {c} ({side}): {e_sign}${pnl:.2f} ({e_sign}{roe:.1f}% ROE)")

    lines.append("\n_Todas as estratégias operam com gestão de risco institucional e alocação controlada._")

    markup = {
        "inline_keyboard": [
            [{"text": "📊 Ver Status Completo", "callback_data": "refresh_status"}],
            [{"text": "⚡ Radar Funding", "callback_data": "funding_radar"}, {"text": "🏆 Top Alphas", "callback_data": "top_alpha"}]
        ]
    }
    return "\n".join(lines), markup


def handle_command(chat_id: int | str, text: str, message_id: int = None):
    cmd_parts = text.strip().split()
    cmd = cmd_parts[0].lower()
    arg = cmd_parts[1].upper() if len(cmd_parts) > 1 else ""

    if cmd in ("/start", "/help", "/ajuda", "ajuda", "help", "menu"):
        msg = (
            "🏛️ *BEM-VINDO AO CONTROLE OPERACIONAL BOTRADE*\n\n"
            "Comande a mesa de operações quantitativas na Hyperliquid e a Tesouraria DeFi diretamente pelo Telegram:\n\n"
            "• `/defi` ou `/tesouraria` - 🏦 Raio-X completo das Pools DeFi na Base (WETH/USDC + VIRTUAL/WETH)\n"
            "• `/lucro` ou `lucro` - 💰 Mostra o lucro total, trades fechados e taxas\n"
            "• `/saldo` ou `saldo` - 💵 Saldo total, garantias e margem livre\n"
            "• `/posicoes` ou `posicoes` - 📍 Posições abertas em tempo real e ROE%\n"
            "• `/relatorio` ou `relatorio` - 📑 Resumo executivo de fechamento das últimas 24h\n"
            "• `/colher <MOEDA>` - Realiza 50% de lucro e trava Stop no 0x0\n"
            "• `/fechar <MOEDA>` - Encerra 100% da posição a mercado\n"
            "• `/fechar_todas` - 🚨 Emergência: encerra todas as posições imediatamente\n"
            "• `/funding` - Radar de Funding Rates e Short Squeezes\n"
            "• `/pausar` - Pausa o Auto-Sniper (congela novas ordens)\n"
            "• `/retomar` - Reativa o rastreio e disparos do Sniper\n\n"
            "_Dica: Você pode usar os botões interativos abaixo com 1 toque:_"
        )
        markup = {
            "inline_keyboard": [
                [{"text": "🏦 Tesouraria DeFi (Base)", "callback_data": "defi_treasury"}],
                [{"text": "💰 Ver Lucro Realizado", "callback_data": "profit_summary"}, {"text": "📊 Ver Saldo & Posições", "callback_data": "refresh_status"}],
                [{"text": "⚡ Radar de Funding", "callback_data": "funding_radar"}, {"text": "🏆 Top 5 Alphas", "callback_data": "top_alpha"}],
                [{"text": "📑 Relatório 24h", "callback_data": "daily_report"}]
            ]
        }
        send_message(chat_id, msg, markup)
        return

    # 0. DEFI TREASURY / POOLS (BASE L2)
    if cmd in ("/defi", "/tesouraria", "/pools", "/pool", "/base", "defi", "tesouraria", "pools", "pool", "base") or "tesouraria" in text.lower() or "defi" in text.lower() or "yield" in text.lower():
        text_out, markup = format_defi_message()
        send_message(chat_id, text_out, markup)
        return

    # 1. LUCRO / PNL
    if cmd in ("/lucro", "/lucros", "/pnl", "/ganhos", "lucro", "lucros", "pnl", "ganhos") and not arg:
        text_out, markup = format_profit_summary_message()
        send_message(chat_id, text_out, markup)
        return

    # 2. SALDO / EQUITY
    if cmd in ("/saldo", "/balance", "saldo", "balance"):
        text_out, markup = format_status_payload()
        send_message(chat_id, text_out, markup)
        return

    # 3. POSIÇÕES ABERTAS / STATUS
    if cmd in ("/posicoes", "/posições", "posicoes", "posições", "/status", "status", "/operacoes", "operacoes"):
        text_out, markup = format_status_payload()
        send_message(chat_id, text_out, markup)
        return

    # 4. RELATÓRIO 24H
    if cmd in ("/relatorio", "/report", "/resumo", "/fechamento", "relatorio", "resumo"):
        text_out, markup = format_daily_report_message()
        send_message(chat_id, text_out, markup)
        return

    # 5. RADAR DE FUNDING
    if cmd in ("/funding", "/radar", "funding", "radar"):
        text_out, markup = format_funding_radar_message()
        send_message(chat_id, text_out, markup)
        return

    # 6. TOP ALPHAS
    if cmd in ("/top", "/leaderboard", "/alpha", "top"):
        text_out, markup = format_top_alpha_message()
        send_message(chat_id, text_out, markup)
        return

    # 7. PAUSAR / RETOMAR
    if cmd in ("/pausar", "/pause", "pausar"):
        set_sniper_state(True)
        send_message(chat_id, "⏸️ *AUTO-SNIPER PAUSADO COM SUCESSO!*\nNenhuma nova ordem será aberta até reativação.", {
            "inline_keyboard": [[{"text": "▶️ Retomar Sniper", "callback_data": "resume_sniper"}, {"text": "📊 Ver Status", "callback_data": "refresh_status"}]]
        })
        return

    if cmd in ("/retomar", "/resume", "retomar"):
        set_sniper_state(False)
        send_message(chat_id, "▶️ *AUTO-SNIPER RETOMADO COM SUCESSO!*\nMonitoramento dinâmico liberado para disparos.", {
            "inline_keyboard": [[{"text": "⏸️ Pausar Sniper", "callback_data": "pause_sniper"}, {"text": "📊 Ver Status", "callback_data": "refresh_status"}]]
        })
        return

    # 8. COLHEITA PARCIAL / HARVEST
    if cmd in ("/colher", "/harvest", "/parcial", "colher") or (cmd in ("/lucro", "lucro") and arg):
        coin = arg or "BTC"
        executor = HyperliquidExecutor()
        res = executor.close_partial_position(coin=coin, pct=0.5, move_sl_to_be=True)
        status_txt = "✅ *Sucesso*" if res.get("status") in ("closed", "ok", "partial_closed") else f"⚠️ *{res.get('status')}*"
        msg = f"{status_txt}: {res.get('message', 'Comando executado.')}"
        send_message(chat_id, msg, {"inline_keyboard": [[{"text": "📊 Ver Status Atualizado", "callback_data": "refresh_status"}]]})
        return

    # 9. ENCERRAMENTO TOTAL
    if cmd in ("/fechar", "/close", "fechar"):
        coin = arg or "BTC"
        executor = HyperliquidExecutor()
        res = executor.close_full_position(coin=coin)
        status_txt = "✅ *Sucesso*" if res.get("status") in ("closed", "ok") else f"⚠️ *{res.get('status')}*"
        msg = f"{status_txt}: {res.get('message', 'Comando executado.')}"
        send_message(chat_id, msg, {"inline_keyboard": [[{"text": "📊 Ver Status Atualizado", "callback_data": "refresh_status"}]]})
        return

    # 10. BOTÃO DE PÂNICO (FECHAR TODAS)
    if cmd in ("/fechar_todas", "/panic", "/close_all", "/liquidar_todas", "fechar_todas"):
        executor = HyperliquidExecutor()
        status = executor.get_account_status()
        open_pos = status.get("open_positions", [])
        if not open_pos:
            send_message(chat_id, "ℹ️ Não há posições abertas na carteira para encerrar.")
            return

        send_message(chat_id, f"🚨 *ENCERRAMENTO DE EMERGÊNCIA DISPARADO!*\nEncerrando a mercado {len(open_pos)} posições ativas...")
        closed_results = []
        for p in open_pos:
            c = p["coin"]
            res = executor.close_full_position(coin=c)
            closed_results.append(f"• *{c}:* {res.get('message', 'Encerrada')}")

        summary_msg = (
            "✅ *TODAS AS POSIÇÕES FORAM ENCERRADAS!*\n\n" +
            "\n".join(closed_results) +
            "\n\n🛡️ Ordens de Stop Loss e Take Profit canceladas. Margem liberada."
        )
        send_message(chat_id, summary_msg, {"inline_keyboard": [[{"text": "📊 Ver Status Atualizado", "callback_data": "refresh_status"}]]})
        return

    send_message(chat_id, f"❓ *Comando não reconhecido:* `{text}`\nDigite `/help` ou `ajuda` para visualizar o menu de comandos.")


def handle_callback_query(cq: dict):
    cq_id = cq["id"]
    data = cq.get("data", "")
    message = cq.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    msg_id = message.get("message_id")

    if not chat_id:
        answer_callback(cq_id)
        return

    if data == "defi_treasury":
        answer_callback(cq_id, "Consultando Tesouraria DeFi...")
        text_out, markup = format_defi_message()
        if msg_id:
            edit_message(chat_id, msg_id, text_out, markup)
        else:
            send_message(chat_id, text_out, markup)
        return

    if data == "profit_summary":
        answer_callback(cq_id, "Calculando lucros acumulados...")
        text_out, markup = format_profit_summary_message()
        if msg_id:
            edit_message(chat_id, msg_id, text_out, markup)
        else:
            send_message(chat_id, text_out, markup)
        return

    if data == "refresh_status":
        answer_callback(cq_id, "Atualizando dados...")
        text_out, markup = format_status_payload()
        if msg_id:
            edit_message(chat_id, msg_id, text_out, markup)
        else:
            send_message(chat_id, text_out, markup)
        return

    if data == "funding_radar":
        answer_callback(cq_id, "Consultando taxas de funding...")
        text_out, markup = format_funding_radar_message()
        if msg_id:
            edit_message(chat_id, msg_id, text_out, markup)
        else:
            send_message(chat_id, text_out, markup)
        return

    if data == "top_alpha":
        answer_callback(cq_id, "Consultando Leaderboard...")
        text_out, markup = format_top_alpha_message()
        if msg_id:
            edit_message(chat_id, msg_id, text_out, markup)
        else:
            send_message(chat_id, text_out, markup)
        return

    if data == "pause_sniper":
        set_sniper_state(True)
        answer_callback(cq_id, "Sniper pausado!")
        text_out, markup = format_status_payload()
        if msg_id:
            edit_message(chat_id, msg_id, text_out, markup)
        return

    if data == "resume_sniper":
        set_sniper_state(False)
        answer_callback(cq_id, "Sniper retomado!")
        text_out, markup = format_status_payload()
        if msg_id:
            edit_message(chat_id, msg_id, text_out, markup)
        return

    if data.startswith("harvest:"):
        coin = data.split(":", 1)[1]
        answer_callback(cq_id, f"Realizando 50% de {coin}...")
        executor = HyperliquidExecutor()
        res = executor.close_partial_position(coin=coin, pct=0.5, move_sl_to_be=True)
        text_out, markup = format_status_payload()
        if msg_id:
            edit_message(chat_id, msg_id, text_out, markup)
        send_message(chat_id, f"💰 *Execução Parcial:* {res.get('message')}")
        return

    if data.startswith("close:"):
        coin = data.split(":", 1)[1]
        answer_callback(cq_id, f"Encerrando {coin} a mercado...")
        executor = HyperliquidExecutor()
        res = executor.close_full_position(coin=coin)
        text_out, markup = format_status_payload()
        if msg_id:
            edit_message(chat_id, msg_id, text_out, markup)
        send_message(chat_id, f"🛑 *Execução Total:* {res.get('message')}")
        return

    if data == "daily_report":
        answer_callback(cq_id, "Gerando relatório 24h...")
        text_out, markup = format_daily_report_message()
        if msg_id:
            edit_message(chat_id, msg_id, text_out, markup)
        else:
            send_message(chat_id, text_out, markup)
        return

    answer_callback(cq_id)


def register_bot_commands():
    commands = [
        {"command": "defi", "description": "🏦 Tesouraria DeFi & Pools na Base"},
        {"command": "tesouraria", "description": "🏦 Raio-X completo das Pools DeFi"},
        {"command": "saldo", "description": "💵 Saldo e margem Hyperliquid"},
        {"command": "posicoes", "description": "📍 Posições abertas ao vivo"},
        {"command": "lucro", "description": "💰 Lucro realizado e trades"},
        {"command": "relatorio", "description": "📑 Relatório diário 24h"},
        {"command": "funding", "description": "⚡ Radar de funding rates"},
        {"command": "help", "description": "❓ Menu e botões de comando"}
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
    print(f"[*] Iniciando Botrade Interactive Telegram Bot (Polling Ativo)...")
    last_update_id = 0
    last_daily_report_day = ""

    while True:
        try:
            # Check for 00:00 UTC daily closing report
            now_dt = datetime.now(timezone.utc)
            today_str = now_dt.strftime("%Y-%m-%d")
            if now_dt.hour == 0 and now_dt.minute <= 5 and last_daily_report_day != today_str:
                target_chat = os.environ.get("TELEGRAM_SIGNALS_CHAT_ID", os.environ.get("TELEGRAM_CHAT_ID", "")).strip() or DEFAULT_CHAT
                if target_chat:
                    try:
                        rep_text, rep_markup = format_daily_report_message()
                        send_message(target_chat, rep_text, rep_markup)
                        print(f"[*] Relatório diário de fechamento (00:00 UTC) enviado com sucesso para {target_chat}")
                    except Exception as rep_err:
                        print(f"[-] Erro ao enviar relatório diário automático: {rep_err}")
                last_daily_report_day = today_str

            params = f"?timeout={poll_timeout}"
            if last_update_id > 0:
                params += f"&offset={last_update_id + 1}"

            url = f"https://api.telegram.org/bot{bot_token}/getUpdates{params}"
            req = urllib.request.Request(url, headers={"User-Agent": "BotradeDesk/1.0"})
            with urllib.request.urlopen(req, timeout=poll_timeout + 10) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            if data.get("ok"):
                updates = data.get("result", [])
                for u in updates:
                    last_update_id = max(last_update_id, u["update_id"])
                    
                    if "message" in u and "text" in u["message"]:
                        msg = u["message"]
                        chat_id = msg["chat"]["id"]
                        text = msg["text"]
                        print(f"[Telegram Bot] Mensagem recebida de {chat_id}: {text}")
                        handle_command(chat_id, text, msg.get("message_id"))

                    elif "callback_query" in u:
                        cq = u["callback_query"]
                        print(f"[Telegram Bot] Botão clicado: {cq.get('data')}")
                        handle_callback_query(cq)

            time.sleep(0.5)
        except Exception as e:
            # Prevent rapid error loop on network glitch
            time.sleep(3)


def main():
    parser = argparse.ArgumentParser(description="Botrade Bidirectional Telegram Bot")
    parser.add_argument("--once", action="store_true", help="Process pending updates once and exit")
    args = parser.parse_args()

    if args.once:
        print("[*] Executando verificação única de updates...")
        res = tg_api_call("getUpdates", {"limit": 10})
        print(f"Updates pendentes: {len(res.get('result', []))}")
    else:
        run_telegram_bot_daemon()


if __name__ == "__main__":
    main()
