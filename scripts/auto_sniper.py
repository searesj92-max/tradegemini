#!/usr/bin/env python3
"""Botrade Dynamic Multi-Strategy Autonomous Sniper (Candidate & Incubate Universe).
Scans all approved Candidate and Incubate strategies from dashboard/data.json 24/7.
Evaluates modular quantitative models:
- 2h Macro Pullback (BTC, ETH, SOL, SUI, LINK)
- 4h RSI Trend Pullback (AVAX, DOGE, ADA, BCH, ETH, LINK, LTC, SOL, TRUMP)
- 4h Squeeze Momentum (ARB, TAO, XLM)
- 4h EMA Golden Cross Trend (XLM, XRP - Incubadas)
- 1h Bollinger Mean Reversion (ETH, AVAX, NEAR, ARB)
- 1h Confluence Breakout (Top 25 Universe)

Guardrails:
- Fixed $15.00-$20.00 margin per trade.
- Respects coin maxLeverage (3x for meme/micro, up to 10x for majors).
- Mandatory Stop Loss with reduce_only=True and Ratchet Trailing at +30% ROE.
- Maximum 3 concurrent open positions.
- BTC Macro Circuit Breaker.
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

STATE_FILE = ROOT / "data" / "journal" / "auto_sniper_state.json"
STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
DATA_FILE = ROOT / "dashboard" / "data.json"

# In-memory candle cache: (coin, tf) -> (timestamp, candles)
_CANDLE_CACHE: dict[tuple[str, str], tuple[float, list[dict]]] = {}
CACHE_TTL_SEC = 45.0


def get_cached_candles(executor: HyperliquidExecutor, coin: str, tf: str, days: int = 35) -> list[dict]:
    now = time.time()
    cache_key = (coin, tf)
    if cache_key in _CANDLE_CACHE:
        ts, candles = _CANDLE_CACHE[cache_key]
        if now - ts < CACHE_TTL_SEC:
            return candles

    now_ms = int(now * 1000)
    start_ms = now_ms - (days * 24 * 3600 * 1000)
    try:
        candles = executor.info.candles_snapshot(coin, tf, start_ms, now_ms)
        if candles:
            _CANDLE_CACHE[cache_key] = (now, candles)
            return candles
    except Exception:
        pass
    return []


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


def calculate_bollinger_bands(prices: list[float], period: int = 20, num_std: float = 2.0) -> tuple[float, float, float]:
    """Returns (upper, mid, lower)."""
    if len(prices) < period:
        return 0.0, 0.0, 0.0
    recent = prices[-period:]
    mid = sum(recent) / period
    variance = sum((x - mid) ** 2 for x in recent) / period
    std = math.sqrt(variance)
    return mid + (num_std * std), mid, mid - (num_std * std)


def load_approved_strategies() -> list[dict]:
    """Loads all Candidate and Incubate strategies from dashboard/data.json."""
    if not DATA_FILE.exists():
        return []
    try:
        d = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        strategies = d.get("strategies", [])
        approved = []
        seen = set()

        for s in strategies:
            verdict = s.get("verdict", "")
            if verdict in ("Candidate", "Incubate"):
                sym = s.get("symbol", "")
                if not sym or "BASKET" in sym or "rows" in sym:
                    continue
                coin = sym.replace("USDT", "").replace("USDC", "").strip()
                tf = s.get("timeframe", "2h").strip()
                fam = s.get("family", s.get("id", ""))
                key = (coin, tf, fam)
                if key in seen:
                    continue
                seen.add(key)

                pf = float(s.get("profit_factor", 1.5))
                wr = float(s.get("win_rate", 55.0)) if s.get("win_rate") else 55.0
                approved.append({
                    "id": s.get("id"),
                    "name": s.get("name", s.get("id")),
                    "coin": coin,
                    "timeframe": tf,
                    "family": fam,
                    "verdict": verdict,
                    "profit_factor": pf,
                    "win_rate": wr
                })

        # Sort: Incubated first, then highest profit factor
        approved.sort(key=lambda x: (1 if x["verdict"] == "Incubate" else 0, x["profit_factor"]), reverse=True)
        return approved
    except Exception as e:
        print(f"[Aviso] Erro ao carregar estratégias aprovadas: {e}")
        return []


def evaluate_approved_strategy(executor: HyperliquidExecutor, strat: dict) -> dict | None:
    """Evaluates an approved strategy against real-time candles."""
    coin = strat["coin"]
    tf = strat["timeframe"]
    fam = strat["family"]
    
    # Map timeframe string for Hyperliquid API
    api_tf = tf
    if tf in ("60", "1h"):
        api_tf = "1h"
    elif tf in ("15", "15m"):
        api_tf = "15m"
    elif tf == "2h":
        api_tf = "2h"
    elif tf == "4h":
        api_tf = "4h"

    candles = get_cached_candles(executor, coin, api_tf, days=45)
    if not candles or len(candles) < 205:
        return None

    closes = [float(c["c"]) for c in candles]
    highs = [float(c["h"]) for c in candles]
    lows = [float(c["l"]) for c in candles]
    current_price = closes[-1]
    atr = calculate_atr(candles, 14)
    if atr <= 0:
        return None

    is_signal = False
    details = []
    sl_multiplier = 2.0
    tp_multiplier = 2.0

    # Model 1: fam-pullback-majors (2h)
    if fam == "fam-pullback-majors" or (tf == "2h" and fam in ("pullback", "rsi-t200")):
        ema200_series = calculate_ema(closes, 200)
        ema200 = ema200_series[-1] if ema200_series else current_price
        rsi = calculate_rsi(closes, 14)
        if current_price > ema200 and rsi <= 38.0:
            is_signal = True
            sl_multiplier = 2.5
            tp_multiplier = 1.6
            details.append(f"⭐ Pullback 2h: Preço > EMA 200 e RSI 2h em sobrevenda ({rsi:.1f})")

    # Model 2: rsi-t200 (4h)
    elif fam in ("rsi-t200", "discovery") and tf == "4h":
        ema200_series = calculate_ema(closes, 200)
        ema200 = ema200_series[-1] if ema200_series else current_price
        rsi = calculate_rsi(closes, 14)
        if current_price > ema200 and rsi <= 40.0:
            is_signal = True
            sl_multiplier = 2.5
            tp_multiplier = 1.8
            details.append(f"⭐ Trend Pullback 4h: Preço > EMA 200 e RSI 4h em sobrevenda ({rsi:.1f})")

    # Model 3: squeeze (4h)
    elif fam == "squeeze" and tf == "4h":
        bb_upper, bb_mid, bb_lower = calculate_bollinger_bands(closes, 20, 2.0)
        # Keltner 1.5 ATR
        kelt_upper = bb_mid + (1.5 * atr)
        kelt_lower = bb_mid - (1.5 * atr)
        is_squeezed = bb_upper < kelt_upper or bb_lower > kelt_lower
        ema20 = bb_mid
        if is_squeezed and current_price > ema20 and closes[-1] > closes[-2]:
            is_signal = True
            sl_multiplier = 2.0
            tp_multiplier = 2.0
            details.append(f"🌪️ Volatility Squeeze 4h: Compressão BB/Keltner com expansão altista")

    # Model 4: ema9-21 (4h, Incubadas)
    elif fam == "ema9-21" and tf == "4h":
        ema9_s = calculate_ema(closes, 9)
        ema21_s = calculate_ema(closes, 21)
        ema50_s = calculate_ema(closes, 50)
        if ema9_s and ema21_s and ema50_s:
            if ema9_s[-1] > ema21_s[-1] and current_price > ema50_s[-1]:
                rsi = calculate_rsi(closes, 14)
                if 45.0 <= rsi <= 68.0:
                    is_signal = True
                    sl_multiplier = 2.0
                    tp_multiplier = 2.0
                    details.append(f"📈 Tendência 4h: EMA 9 > 21 acima da EMA 50 e RSI saudável ({rsi:.1f})")

    # Model 5: fam-bb-reversion (1h)
    elif fam == "fam-bb-reversion" and tf in ("1h", "60"):
        bb_upper, bb_mid, bb_lower = calculate_bollinger_bands(closes, 20, 2.0)
        rsi = calculate_rsi(closes, 14)
        if current_price <= bb_lower * 1.002 and rsi <= 32.0:
            is_signal = True
            sl_multiplier = 1.5
            tp_multiplier = 1.5
            details.append(f"🔄 Reversão à Média 1h: Toque na Banda Inferior com RSI ({rsi:.1f})")

    # Model 6: leaderboard / high-wr (15m)
    elif tf in ("15", "15m"):
        donch_high = max(highs[-21:-1])
        ema200_s = calculate_ema(closes, 200)
        ema200 = ema200_s[-1] if ema200_s else current_price
        if current_price >= donch_high and current_price > ema200:
            is_signal = True
            sl_multiplier = 1.8
            tp_multiplier = 2.0
            details.append(f"⚡ Donchian Breakout 15m: Rompimento de máxima de 20 períodos acima da EMA 200")

    if not is_signal:
        return None

    sl_price = current_price - (sl_multiplier * atr)
    tp1_price = current_price + (tp_multiplier * atr)
    sl_pct = ((current_price - sl_price) / current_price) * 100

    return {
        "coin": coin,
        "strategy": f"{strat['name']} ({tf})",
        "family": fam,
        "timeframe": tf,
        "verdict": strat["verdict"],
        "profit_factor": strat["profit_factor"],
        "win_rate": strat["win_rate"],
        "current_price": current_price,
        "sl_price": round(sl_price, 4 if sl_price > 1 else 6),
        "sl_pct": round(sl_pct, 2),
        "tp1_price": round(tp1_price, 4 if tp1_price > 1 else 6),
        "details": details
    }


def check_btc_macro_circuit_breaker(executor: HyperliquidExecutor) -> tuple[bool, str]:
    """Checks Bitcoin 20d Macro Trend. Pauses entries if BTC drops > 5% in 20d."""
    try:
        candles = get_cached_candles(executor, "BTC", "1d", days=30)
        if not candles or len(candles) < 21:
            return True, "Dados normais de mercado"
        closes = [float(c["c"]) for c in candles]
        cur_price = closes[-1]
        ret_20d = ((cur_price - closes[-21]) / closes[-21]) * 100

        if ret_20d <= -5.0:
            return False, f"BTC em Regime Bear ({ret_20d:+.1f}% em 20d) — Disjuntor ativado"
        return True, f"BTC em Regime Favorável ({ret_20d:+.1f}% em 20d)"
    except Exception as e:
        return True, f"Verificação normal ({e})"


def run_sniper_loop(auto_trade: bool = True, max_positions: int = 3, margin_usdc: float = 15.0, interval_sec: int = 60, dry_run: bool = False):
    print("=" * 72)
    print("🎯 BOTRADE DYNAMIC SNIPER (CANDIDATE & INCUBATE UNIVERSE)")
    print(f"[*] Modo: {'🧪 SIMULAÇÃO (DRY-RUN)' if dry_run else ('⚡ AUTOMÁTICO (DINHEIRO REAL)' if auto_trade else '📡 CO-PILOTO')}")
    print(f"[*] Margem por Entrada: ${margin_usdc:.2f} USDC (Teto seguro)")
    print(f"[*] Vagas Simultâneas: {max_positions}")
    print(f"[*] Intervalo de Varredura: {interval_sec}s")
    print("=" * 72)

    executor = HyperliquidExecutor()
    valid, msg = executor.check_credentials()
    if not valid and not dry_run:
        print(f"[-] Erro de credenciais: {msg}")
        return

    approved_strategies = load_approved_strategies()
    print(f"[*] Estratégias Aprovadas Carregadas do Catálogo: {len(approved_strategies)} estratégias ativas!")
    
    unique_coins = sorted(list(set(s["coin"] for s in approved_strategies)))
    print(f"[*] Ativos no Radar ({len(unique_coins)} moedas): {', '.join(unique_coins)}")

    while True:
        try:
            status = executor.get_account_status()
            open_positions = status.get("open_positions", status.get("positions", []))
            current_open_count = len(open_positions)
            open_coins = [p["coin"] for p in open_positions]

            allow_macro, macro_reason = check_btc_macro_circuit_breaker(executor)

            free_margin = float(status.get("withdrawable", 0.0))
            if free_margin <= 0:
                perps_val = float(status.get("perps_account_value", 0.0))
                tot_margin = float(status.get("total_margin_used", 0.0))
                free_margin = max(0.0, perps_val - tot_margin)

            min_required = max(10.0, margin_usdc)
            has_sufficient = free_margin >= min_required
            vagas = max_positions - current_open_count

            now_str = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
            print(f"\n[{now_str}] Carteira: {current_open_count}/{max_positions} abertas ({', '.join(open_coins) if open_coins else 'Nenhuma'}) | Margem Livre: ${free_margin:.2f} USDC")
            print(f"  -> Disjuntor Macro BTC: {macro_reason}")

            # Save state for dashboard
            state_payload = {
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "open_positions_count": current_open_count,
                "open_coins": open_coins,
                "max_positions": max_positions,
                "free_margin": round(free_margin, 2),
                "required_margin": round(min_required, 2),
                "has_sufficient_balance": has_sufficient,
                "macro_status": macro_reason,
                "macro_allowed": allow_macro,
                "monitored_strategies_count": len(approved_strategies),
                "monitored_coins": unique_coins,
                "status_message": "Aguardando saldo" if not has_sufficient else ("Capacidade máxima de risco atingida" if vagas <= 0 else "Varrendo mercado 24/7")
            }
            STATE_FILE.write_text(json.dumps(state_payload, indent=2, ensure_ascii=False), encoding="utf-8")

            if not allow_macro:
                print(f"  -> 🛑 DISJUNTOR MACRO ATIVO: {macro_reason}. Aguardando...")
                if dry_run: break
                time.sleep(interval_sec)
                continue

            if vagas <= 0:
                print(f"  -> 🔒 Limite de risco atingido ({current_open_count}/{max_positions}). Aguardando encerramento...")
                if dry_run: break
                time.sleep(interval_sec)
                continue

            if not has_sufficient and not dry_run:
                print(f"  -> 🔒 Saldo livre insuficiente (${free_margin:.2f} < ${min_required:.2f}). Aguardando...")
                if dry_run: break
                time.sleep(interval_sec)
                continue

            print(f"  -> Varrendo {len(approved_strategies)} estratégias aprovadas (Candidatas & Incubadas) em busca de sinais...")

            signals_detected = []
            for strat in approved_strategies:
                coin = strat["coin"]
                if coin in open_coins:
                    continue  # Already open

                sig = evaluate_approved_strategy(executor, strat)
                if sig:
                    signals_detected.append(sig)
                    print(f"    ⭐ SINAL APROVADO: {sig['coin']} via {sig['strategy']} | Preço: ${sig['current_price']} | SL: ${sig['sl_price']} (-{sig['sl_pct']}%)")
                
                time.sleep(0.04)  # Polite API spacing

            if signals_detected:
                # Prioritize: Incubate first, then highest profit factor, then lowest SL distance
                signals_detected.sort(key=lambda x: (1 if x["verdict"] == "Incubate" else 0, x["profit_factor"], -x["sl_pct"]), reverse=True)
                best = signals_detected[0]
                coin = best["coin"]
                px = best["current_price"]
                sl = best["sl_price"]
                tp = best["tp1_price"]
                strat_name = best["strategy"]

                print(f"\n[!] MELHOR ENTRADA QUANTITATIVA SELECIONADA: {coin} ({strat_name})")
                print(f"    Veredito: {best['verdict']} | PF Histórico: {best['profit_factor']:.2f} | Preço: ${px} | SL: ${sl} (-{best['sl_pct']}%) | TP1: ${tp}")

                if dry_run:
                    print("    [DRY-RUN] Simulação concluída com sucesso. Nenhuma ordem foi enviada ao livro.")
                    break

                if auto_trade:
                    print(f"    🚀 DISPARANDO EXECUÇÃO AUTOMÁTICA NA HYPERLIQUID (${margin_usdc:.2f} USDC)...")
                    
                    # Pre-flight check: minimum $10 notional
                    coin_meta = executor.universe.get(coin, {})
                    allowed_max_lev = int(coin_meta.get("maxLeverage", 10))
                    eff_lev = min(10, allowed_max_lev)

                    trade_res = executor.execute_trade(
                        coin=coin,
                        side="buy",
                        usdc_margin=margin_usdc,
                        leverage=eff_lev,
                        sl_price=sl,
                        tp_price=tp,
                        confirm=True
                    )

                    if trade_res.get("status") in ("ok", "executed"):
                        print(f"    ✅ SUCESSO! Ordem de {coin} executada e Stop Loss registrado com reduce_only na Hyperliquid!")
                        send(
                            f"🚀 *NOVA OPERAÇÃO DISPARADA PELO SNIPER!*\n\n"
                            f"• Ativo: *{coin} / USDC (LONG)*\n"
                            f"• Estratégia: *{strat_name}*\n"
                            f"• Veredito: *{best['verdict']}* (PF Histórico: *{best['profit_factor']:.2f}*)\n"
                            f"• Vagas Ocupadas: *{current_open_count + 1}/{max_positions}*\n"
                            f"• Preço de Entrada: *${px:.4f}*\n"
                            f"• Margem: *${margin_usdc:.2f} USDC @ {eff_lev}x*\n"
                            f"• Stop Loss: *${sl:.4f}* (-{best['sl_pct']}% com `reduce_only`)\n"
                            f"• Alvo 1 (TP1): *${tp:.4f}*\n"
                            f"• Detalhes: _{', '.join(best['details'])}_\n\n"
                            f"🛡️ *Ratchet Trailing Stop* ativo para proteger no 0x0 ao atingir +30% ROE."
                        )
                    else:
                        print(f"    [-] Falha na execução: {trade_res.get('error') or trade_res.get('message')}")
            else:
                print(f"  -> Nenhum sinal de confluência extrema disparado neste ciclo. Mercado calmo.")

            if dry_run:
                break

            time.sleep(interval_sec)

        except Exception as e:
            print(f"[-] Erro no loop do sniper: {e}")
            if dry_run:
                break
            time.sleep(30)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Botrade Dynamic Multi-Strategy Sniper")
    parser.add_argument("--auto", action="store_true", default=True, help="Executa ordens automaticamente (padrão: True)")
    parser.add_argument("--margin", type=float, default=15.0, help="Margem em USDC por operação (padrão: 15.0)")
    parser.add_argument("--max-positions", type=int, default=3, help="Número máximo de posições abertas simultâneas (padrão: 3)")
    parser.add_argument("--interval", type=int, default=60, help="Intervalo de varredura em segundos (padrão: 60s)")
    parser.add_argument("--dry-run", action="store_true", default=False, help="Executa 1 ciclo de teste sem emitir ordens reais")
    args = parser.parse_args()

    run_sniper_loop(
        auto_trade=args.auto,
        max_positions=args.max_positions,
        margin_usdc=args.margin,
        interval_sec=args.interval,
        dry_run=args.dry_run
    )
