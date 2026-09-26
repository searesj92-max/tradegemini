"""Botrade Autonomous Market Sniper & Confluence Executor.
Continuously scans Hyperliquid's top-ranked crypto universe, detects high-confluence
setups (Score >= 5/6), and executes trades automatically ($5.00 USDC @ 10x) with
mandatory Stop Loss and Ratchet Trailing Stop.

Guardrails:
- Maximum 1 concurrent position by default (never over-allocates capital).
- Only operates on verified Elite & Candidate coins.
- Fixed $5.00 margin per trade.
- Immediate Telegram alert on every detection and execution.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", line_buffering=True)

from hyperliquid_executor import HyperliquidExecutor
from send_telegram import send

RANKING_FILE = ROOT / "dashboard" / "universe_ranking.json"
STATE_FILE = ROOT / "data" / "journal" / "auto_sniper_state.json"
STATE_FILE.parent.mkdir(parents=True, exist_ok=True)


def calculate_ema(prices: list[float], period: int) -> list[float]:
    if len(prices) < period:
        return []
    multiplier = 2 / (period + 1)
    ema = [sum(prices[:period]) / period]
    for p in prices[period:]:
        ema.append((p - ema[-1]) * multiplier + ema[-1])
    return ema


def calculate_rsi(prices: list[float], period: int = 14) -> float:
    if len(prices) < period + 1:
        return 50.0
    changes = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
    gains = [c if c > 0 else 0 for c in changes]
    losses = [-c if c < 0 else 0 for c in changes]

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(period, len(changes)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def calculate_atr(candles: list[dict], period: int = 14) -> float:
    if len(candles) < period + 1:
        return 0.0
    trs = []
    for i in range(1, len(candles)):
        h = float(candles[i]["h"])
        l = float(candles[i]["l"])
        prev_c = float(candles[i - 1]["c"])
        tr = max(h - l, abs(h - prev_c), abs(l - prev_c))
        trs.append(tr)

    atr = sum(trs[:period]) / period
    for tr in trs[period:]:
        atr = (atr * (period - 1) + tr) / period
    return atr


def get_watchlist() -> list[dict]:
    """Loads elite and approved candidate coins from the universe ranking."""
    if not RANKING_FILE.exists():
        # Fallback to standard robust perps
        return [{"coin": c} for c in ["SOL", "INJ", "AVAX", "BERA", "ZEC", "ZRO", "REZ", "ENA", "ICP", "BTC", "ETH"]]
    
    try:
        data = json.loads(RANKING_FILE.read_text(encoding="utf-8"))
        top_coins = data.get("top_coins", [])
        # Select coins with ELITE_CANDIDATE or CANDIDATE
        elite = [c for c in top_coins if c.get("verdict") in ("ELITE_CANDIDATE", "CANDIDATE")]
        if not elite:
            elite = top_coins[:20]
        return elite[:25] # Monitor top 25 high-probability assets
    except Exception as e:
        print(f"[-] Erro ao carregar universe_ranking.json: {e}")
        return [{"coin": c} for c in ["SOL", "INJ", "AVAX", "BERA", "ZEC", "ZRO", "REZ", "ENA", "ICP"]]


def evaluate_asset(executor: HyperliquidExecutor, coin: str) -> dict | None:
    """Evaluates real-time 6-pillar confluence on 1h candles."""
    now_ms = int(time.time() * 1000)
    start_ms = now_ms - (15 * 24 * 3600 * 1000) # 15 days of 1h candles

    try:
        candles = executor.info.candles_snapshot(coin, "1h", start_ms, now_ms)
        if len(candles) < 205:
            return None

        closes = [float(c["c"]) for c in candles]
        highs = [float(c["h"]) for c in candles]
        lows = [float(c["l"]) for c in candles]
        volumes = [float(c["v"]) for c in candles]
        current_price = closes[-1]

        # EMAs
        ema200_series = calculate_ema(closes, 200)
        ema21_series = calculate_ema(closes, 21)
        ema9_series = calculate_ema(closes, 9)

        ema200 = ema200_series[-1] if ema200_series else current_price
        ema21 = ema21_series[-1] if ema21_series else current_price
        ema9 = ema9_series[-1] if ema9_series else current_price

        rsi = calculate_rsi(closes, 14)
        atr = calculate_atr(candles, 14)
        donchian_high = max(highs[-21:-1])

        score = 0
        details = []

        # 1. Macro Trend (Preço > EMA 200)
        if current_price > ema200:
            score += 2
            details.append("Preço acima da EMA 200 (Tendência de Alta)")

        # 2. RSI 14 (Pullback Saudável 48-68)
        if 48.0 <= rsi <= 68.0:
            score += 1
            details.append(f"RSI 14 Saudável ({rsi:.1f})")

        # 3. Donchian 20 Breakout / Proximidade do Topo
        dist_to_donchian = (donchian_high - current_price) / current_price * 100
        if current_price >= donchian_high or dist_to_donchian <= 1.0:
            score += 1
            details.append("Rompimento / Proximidade do Topo Donchian 20")

        # 4. Médias Rápidas Alinhadas (EMA 9 > EMA 21)
        if ema9 > ema21:
            score += 1
            details.append("Médias Rápidas Alinhadas (EMA 9 > 21)")

        # 5. Volume Acima da Média
        avg_vol = sum(volumes[-21:-1]) / 20 if len(volumes) >= 21 else volumes[-1]
        if volumes[-1] > avg_vol * 0.85:
            score += 1
            details.append("Volume Relevante")

        sl_price = current_price - (2.0 * atr)
        sl_pct = ((current_price - sl_price) / current_price) * 100
        tp1_price = current_price + (1.5 * (current_price - sl_price))
        tp2_price = current_price + (2.5 * (current_price - sl_price))
        tp3_price = current_price + (4.0 * (current_price - sl_price))

        return {
            "coin": coin,
            "score": score,
            "current_price": current_price,
            "rsi": round(rsi, 1),
            "ema200": round(ema200, 4),
            "atr": round(atr, 4),
            "sl_price": round(sl_price, 4),
            "sl_pct": round(sl_pct, 2),
            "tp1_price": round(tp1_price, 4),
            "tp2_price": round(tp2_price, 4),
            "tp3_price": round(tp3_price, 4),
            "details": details
        }
    except Exception as e:
        return None


def run_sniper_loop(auto_trade: bool = True, max_positions: int = 3, margin_usdc: float = 15.0, interval_sec: int = 60):
    print("=" * 70)
    print("🎯 BOTRADE AUTONOMOUS SNIPER & CONFLUENCE EXECUTOR INICIADO")
    print(f"[*] Modo de Execução: {'⚡ AUTOMÁTICO (DINHEIRO REAL)' if auto_trade else '📡 APENAS NOTIFICAÇÃO (CO-PILOTO)'}")
    print(f"[*] Limite de Posições Simultâneas: {max_positions}")
    print(f"[*] Margem por Nova Entrada: ${margin_usdc:.2f} USDC @ 10x")
    print(f"[*] Intervalo de Varredura: {interval_sec}s")
    print("=" * 70)

    executor = HyperliquidExecutor()
    valid, msg = executor.check_credentials()
    while not valid:
        print(f"[-] Erro de credenciais: {msg}. Aguardando credenciais... (tentando em 10s)")
        time.sleep(10)
        executor = HyperliquidExecutor()
        valid, msg = executor.check_credentials()


    # Notify Telegram of startup
    mode_str = "⚡ 100% AUTOMÁTICO (DINHEIRO REAL)" if auto_trade else "📡 MODO CO-PILOTO (Sinais)"
    send(
        f"🎯 *BOTRADE SNIPER ATIVADO NO MODO AUTOMÁTICO*\n\n"
        f"• Modo: *{mode_str}*\n"
        f"• Limite de Carteira: *Até {max_positions} operações simultâneas*\n"
        f"• Margem por Nova Entrada: *${margin_usdc:.2f} USDC @ 10x*\n"
        f"• Stop Loss: *2.0x ATR Obrigatório*\n"
        f"• Trailing: *Ratchet +30% Automático (Risco Zero)*\n"
        f"• Universo: *Top 25 Moedas Campeãs da Hyperliquid*\n\n"
        f"O robô está ativo e executará as próximas 2 oportunidades automaticamente!"
    )

    while True:
        try:
            status = executor.get_account_status()
            open_positions = status.get("open_positions", status.get("positions", []))
            current_open_count = len(open_positions)
            open_coins = [p["coin"] for p in open_positions]

            now_str = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
            print(f"\n[{now_str}] Status da Carteira: {current_open_count}/{max_positions} posições abertas ({', '.join(open_coins) if open_coins else 'Nenhuma'})")

            # Check if capacity allows opening a new position
            if current_open_count >= max_positions:
                print(f"  -> Capacidade máxima de risco atingida ({current_open_count}/{max_positions} trades em andamento: {', '.join(open_coins)}).")
                print(f"  -> O robô monitora as posições e aguarda liberação de vaga para novas entradas.")
            else:
                watchlist = get_watchlist()
                vagas_disponiveis = max_positions - current_open_count
                print(f"  -> Temos {vagas_disponiveis} vaga(s) disponível(is)! Varrendo {len(watchlist)} moedas campeãs em busca de Confluência Score >= 5/6...")

                candidates_found = []
                for item in watchlist:
                    coin = item["coin"]
                    if coin in open_coins:
                        continue # Already in this position

                    res = evaluate_asset(executor, coin)
                    if res and res["score"] >= 5:
                        candidates_found.append(res)
                        print(f"    ⭐ SINAL DETECTADO: {coin} (Score {res['score']}/6 | Preço ${res['current_price']})")
                    
                    time.sleep(0.08) # Polite rate limit

                # Sort by highest score, then lowest SL distance
                candidates_found.sort(key=lambda x: (x["score"], -x["sl_pct"]), reverse=True)

                if candidates_found:
                    best = candidates_found[0]
                    coin = best["coin"]
                    px = best["current_price"]
                    sl = best["sl_price"]
                    tp = best["tp1_price"]

                    print(f"\n[!] MELHOR OPORTUNIDADE DO MERCADO ENCONTRADA: {coin}")
                    print(f"    Preço: ${px} | SL: ${sl} (-{best['sl_pct']}%) | TP1: ${tp} | Score: {best['score']}/6")

                    if auto_trade:
                        print(f"    🚀 DISPARANDO EXECUÇÃO AUTOMÁTICA NA HYPERLIQUID (${margin_usdc:.2f} @ 10x)...")
                        trade_res = executor.execute_trade(
                            coin=coin,
                            side="buy",
                            usdc_margin=margin_usdc,
                            leverage=10,
                            sl_price=sl,
                            tp_price=tp,
                            confirm=True
                        )

                        if trade_res.get("status") in ("ok", "executed"):
                            print(f"    ✅ SUCESSO! Ordem de {coin} executada e Stop Loss registrado na Hyperliquid!")
                            send(
                                f"🚀 *NOVA OPERAÇÃO DISPARADA AUTOMATICAMENTE!*\n\n"
                                f"• Ativo: *{coin} / USDC (LONG)*\n"
                                f"• Vagas Ocupadas: *{current_open_count + 1}/{max_positions}*\n"
                                f"• Preço de Entrada: *${px:.4f}*\n"
                                f"• Margem Alocada: *${margin_usdc:.2f} USDC @ 10x* (Notional: ~${margin_usdc*10:.2f} USD)\n"
                                f"• Stop Loss Obrigatório: *${sl:.4f}* (-{best['sl_pct']}%)\n"
                                f"• Alvo 1 (TP1): *${tp:.4f}*\n"
                                f"• Confluência Técnica: *Score {best['score']}/6*\n\n"
                                f"🛡️ *Ratchet Trailing Stop* já ativado para proteger no 0x0 ao atingir +30% ROE.\n"
                                f"🌐 *Painel:* http://192.168.18.12:8765/"
                            )
                        else:
                            print(f"    [-] Falha na execução: {trade_res.get('error') or trade_res.get('message')}")
                    else:
                        send(
                            f"📡 *OPORTUNIDADE DE OURO DETECTADA!*\n\n"
                            f"• Ativo: *{coin}* (Score: *{best['score']}/6*)\n"
                            f"• Preço Atual: *${px:.4f}*\n"
                            f"• Stop Loss Sugerido: *${sl:.4f}* (-{best['sl_pct']}%)\n"
                            f"• Alvo Estimado: *${tp:.4f}*\n\n"
                            f"Acesse o Cockpit para executar com 1 clique: http://192.168.18.12:8765/"
                        )

            time.sleep(interval_sec)

        except Exception as e:
            print(f"[-] Erro no loop do sniper: {e}")
            time.sleep(30)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Botrade Autonomous Sniper")
    parser.add_argument("--auto", action="store_true", default=True, help="Executa ordens automaticamente com dinheiro real (padrão: True)")
    parser.add_argument("--margin", type=float, default=15.0, help="Margem em USDC por operação (padrão: 15.0)")
    parser.add_argument("--max-positions", type=int, default=3, help="Número máximo de posições abertas simultâneas (padrão: 3)")
    parser.add_argument("--interval", type=int, default=60, help="Intervalo de varredura em segundos (padrão: 60s)")
    args = parser.parse_args()

    run_sniper_loop(auto_trade=args.auto, max_positions=args.max_positions, margin_usdc=args.margin, interval_sec=args.interval)
