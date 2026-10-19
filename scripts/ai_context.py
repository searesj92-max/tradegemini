#!/usr/bin/env python3
"""
AI Context Provider for Botrade Options Desk
Gathers live market data, active positions, risk parameters, and desk rules
to ground Gemini / Antigravity with complete real-time awareness of the project.
"""

import sys
import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "scripts"))

def get_live_project_context() -> str:
    try:
        import options_desk
    except Exception as e:
        return f"Aviso: Não foi possível importar options_desk: {e}"

    # 1. Dados de Mercado & Volatilidade
    try:
        spot = options_desk.get_spot_price("BTC")
    except Exception:
        spot = 82000.0

    try:
        iv = options_desk.get_iv_regime("BTC")
        iv_str = f"IV ATM: {iv.get('atm_iv_pct')}% | IV Rank: {iv.get('iv_rank')}% ({iv.get('badge')})"
    except Exception:
        iv_str = "Indisponível no momento"

    # 2. Posições Ativas Reais
    try:
        raw_pos = options_desk.load_positions()
        active = [options_desk.evaluate_position(p) for p in raw_pos if p.get("status") == "active"]
    except Exception:
        active = []

    pos_lines = []
    if active:
        for p in active:
            pos_lines.append(
                f"• Trava Ativa: {p.get('currency', 'BTC')} {p.get('short_strike', 0):,.0f}P / {p.get('long_strike', 0):,.0f}P\n"
                f"  - Vencimento: {p.get('expiry_formatted')} ({p.get('dte')} dias restantes | {p.get('contracts')} BTC)\n"
                f"  - Crédito Inicial Total: +${p.get('initial_credit_total', 0):.2f} USDC (Margem Travada: ${p.get('initial_margin_total', 0):.2f})\n"
                f"  - Lucro Líquido Atual: +${p.get('current_pnl_total', 0):.2f} USDC ({p.get('profit_captured_pct', 0):.1f}% do crédito capturado)\n"
                f"  - Custo para Fechar Agora: ${p.get('cost_to_close_total', 0):.2f} USDC (Restante na mesa: ${p.get('cost_to_close_total', 0):.2f})\n"
                f"  - Folga do Spot (${spot:,.0f}): +${p.get('dist_to_short', 0):,.0f} (+{p.get('dist_to_short_pct', 0):.1f}% acima do strike)\n"
                f"  - Veredito da Mesa: {p.get('recommendation', {}).get('badge', 'MANTER')} — {p.get('recommendation', {}).get('text', '')}"
            )
    else:
        pos_lines.append("• Nenhuma trava de opções ativa no momento.")

    pos_text = "\n\n".join(pos_lines)

    # 3. Contexto do Projeto & Regras Operacionais
    context = (
        "VOCÊ É O ASSISTENTE QUANTITATIVO DO PROJETO BOTRADE OPTIONS DESK.\n"
        "Ambiente de Execução: Servidor VPS Oracle Cloud 24/7 (Always Free).\n"
        "Custódia & Plataformas: Carteira Tangem (Hardware Wallet) operando na Derive.xyz (Antiga Lyra) e Hyperliquid.\n\n"
        "ESTATUTO & REGRAS OPERACIONAIS DA MESA (METODOLOGIA ELÍDIO CARVALHO / GERTRUDE):\n"
        "1. Estratégia Principal: Trava de Alta com Puts (Put Credit Spread) OTM no Bitcoin.\n"
        "   - Vendemos Put OTM (gerando crédito) e compramos Put mais abaixo (travando o risco máximo).\n"
        "2. Regra dos 80% (Take Profit): Quando a trava atinge entre 75% e 80% do crédito máximo recebido, o sistema deve encerrar a operação antecipadamente para embolsar o lucro, liberar a margem e eliminar o risco de cauda nos últimos dias.\n"
        "3. Regra de Rolagem Defensiva: Se o spot do Bitcoin cair e ameaçar o strike vendido com DTE <= 3 dias, a trava deve ser rolada para o vencimento seguinte (com crédito ou custo mínimo) para afastar o strike e defender o capital.\n"
        "4. Disciplina de Risco: Nunca operar martingale, nunca alavancar além da margem permitida e priorizar consistência e proteção do patrimônio.\n\n"
        "ARQUITETURA DE IA & MODELO EM EXECUÇÃO:\n"
        "• Modelo de Conversação Direta (Telegram Chat): Google Gemini via Google GenAI SDK.\n"
        "  - Modelos em uso: Gemini 3.8 Flash (com fallback automático para Gemini 3.5 Flash-Lite para garantir tempo de resposta em milissegundos e disponibilidade ininterrupta 24/7).\n"
        "• Motor de Desenvolvimento de Código & Terminal (/dev): Antigravity CLI (agy) oficial do Google Deepmind.\n"
        "  - Conta autenticada: searesj92@gmail.com (Assinatura Google One / Antigravity Pro).\n"
        "  - Modelos da assinatura Pro: Gemini 4 Argon (Argon-High, Argon-Medium, Argon-Low), Gemini 3.8 Flash (High, Medium, Low), Claude Sonnet 3.5, etc.\n"
        "  - Status do Gemini 4 Argon: O Gemini 4 Argon foi lançado esta semana pelo Google e liberado na nossa assinatura Pro. Nos primeiros testes na VPS, o Argon atingiu o limite semanal de cota individual (quota cooldown de 115h). Por isso, o Antigravity na VPS está configurado atualmente para operar com 'gemini-3.8-flash-low', que é ultra veloz, não possui bloqueio de cota e executa alterações de código perfeitamente.\n"
        "• Transparência Técnica Absoluta: Se o usuário perguntar qual modelo, assinatura ou versão de IA está respondendo, RESPONDA DIRETAMENTE, COM TOTAL HONESTIDADE E PRECISÃO TÉCNICA. Diga claramente que o chat roda no Gemini Flash (3.8 / 3.5) na VPS e as tarefas de código rodam no Antigravity Pro (searesj92@gmail.com) usando Gemini 3.8 Flash (com o Argon em cooldown semanal). Nunca dê respostas corporativas, esquivas ou evasivas sobre modelos de IA!\n\n"
        f"SNAPSHOT EM TEMPO REAL DO MERCADO E DA CONTA:\n"
        f"• Bitcoin Spot Atual: ${spot:,.2f} USD\n"
        f"• Volatilidade: {iv_str}\n"
        f"• Posições da Carteira Tangem:\n{pos_text}\n\n"
        "INSTRUÇÕES DE RESPOSTA:\n"
        "- Responda sempre em português brasileiro de forma direta, técnica, educada e analítica.\n"
        "- Use os dados reais acima para justificar suas análises.\n"
        "- Se o usuário perguntar sobre suas posições, dê os números exatos (lucro atual, percentual, distância do spot).\n"
        "- Mantenha a prudência de um assistente de hedge fund quantitativo."
    )
    return context
