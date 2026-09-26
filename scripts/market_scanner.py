"""Market Confluence Scanner for Hyperliquid Mainnet.
Evaluates the 6 quantitative pillars across top perpetual pairs on Hyperliquid.
"""
from __future__ import annotations

import json
import math
import os
import sys
import time
from pathlib import Path

from hyperliquid.info import Info
from hyperliquid.utils import constants

ROOT = Path(r"C:\Users\seares\Desktop\botrade")
sys.path.insert(0, str(ROOT))

CANDIDATES = [
    "BTC", "ETH", "SOL", "HYPE", "INJ", "AVAX", "SUI", "DOGE", "XRP", 
    "NEAR", "LINK", "APT", "TIA", "RENDER", "ARB", "OP", "PEPE", "WIF", 
    "AAVE", "ENA", "PENDLE", "FET", "SEI", "DOT", "ADA"
]


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


def scan_markets():
    info = Info(constants.MAINNET_API_URL, skip_ws=True)
    meta = info.meta()
    universe = {coin["name"]: coin for coin in meta.get("universe", [])}
    
    now = int(time.time() * 1000)
    start_1h = now - 24 * 3600 * 1000 * 15 # 15 days of 1h candles = 360 candles
    
    results = []
    print(f"[*] Escaneando {len(CANDIDATES)} ativos na Hyperliquid Mainnet (Tempo Gráfico 1h)...")

    for coin in CANDIDATES:
        if coin not in universe:
            continue
        try:
            candles = info.candles_snapshot(coin, "1h", start_1h, now)
            if len(candles) < 205:
                continue

            closes = [float(c["c"]) for c in candles]
            highs = [float(c["h"]) for c in candles]
            lows = [float(c["l"]) for c in candles]
            volumes = [float(c["v"]) for c in candles]
            current_price = closes[-1]

            # Indicators
            ema200_series = calculate_ema(closes, 200)
            ema21_series = calculate_ema(closes, 21)
            ema9_series = calculate_ema(closes, 9)

            ema200 = ema200_series[-1] if ema200_series else current_price
            ema21 = ema21_series[-1] if ema21_series else current_price
            ema9 = ema9_series[-1] if ema9_series else current_price

            rsi = calculate_rsi(closes, 14)
            atr = calculate_atr(candles, 14)

            # Donchian 20 High
            donchian_high = max(highs[-21:-1])

            # 6 Pillars Scoring
            score = 0
            details = []

            # 1. Macro Trend (EMA 200) - Weight 2
            if current_price > ema200:
                score += 2
                details.append("Tendência Macro Altista (Preço > EMA 200)")
            else:
                details.append("Preço abaixo da EMA 200 (Alerta de Fraqueza)")

            # 2. Momentum RSI 14 - Weight 1
            if 50.0 <= rsi <= 72.0:
                score += 1
                details.append(f"RSI 14 Saudável ({rsi:.1f} - Expansão Sem Sobrecompra)")
            elif rsi > 72.0:
                details.append(f"RSI 14 Esticado ({rsi:.1f} - Zona de Sobrecompra)")
            else:
                details.append(f"RSI 14 Frio ({rsi:.1f} - Abaixo de 50)")

            # 3. Donchian 20 Breakout - Weight 1
            dist_to_breakout = (donchian_high - current_price) / current_price * 100
            if current_price >= donchian_high or dist_to_breakout <= 1.0:
                score += 1
                details.append(f"Rompimento Donchian 20 (Distância do Topo: {dist_to_breakout:+.2f}%)")
            else:
                details.append(f"Abaixo do Topo Donchian 20 ({dist_to_breakout:+.2f}%)")

            # 4. Short-term EMAs (9 > 21) - Weight 1
            if ema9 > ema21:
                score += 1
                details.append("Médias Rápidas Alinhadas (EMA 9 > EMA 21)")
            else:
                details.append("Médias Rápidas Cruzadas para Baixo (EMA 9 < EMA 21)")

            # 5. Volume Expansion - Weight 1
            avg_vol_20 = sum(volumes[-21:-1]) / 20 if len(volumes) >= 21 else volumes[-1]
            if volumes[-1] > avg_vol_20 * 0.9:
                score += 1
                details.append("Volume Acima da Média de 20 períodos")
            else:
                details.append("Volume Abaixo da Média")

            # Risk Calculations (2.0x ATR for Stop Loss)
            sl_price = current_price - (2.0 * atr)
            sl_pct = ((current_price - sl_price) / current_price) * 100
            tp1_price = current_price + (1.5 * (current_price - sl_price))
            tp2_price = current_price + (2.5 * (current_price - sl_price))
            tp3_price = current_price + (4.0 * (current_price - sl_price))

            # Notional sizing for $5.00 margin @ 10x
            notional_usd = 50.0
            sz_decimals = int(universe[coin].get("szDecimals", 2))
            factor = 10 ** sz_decimals
            size = math.floor((notional_usd / current_price) * factor) / factor

            results.append({
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
                "size": size,
                "sz_decimals": sz_decimals,
                "details": details
            })

            time.sleep(0.08) # Respect rate limits
        except Exception as e:
            continue

    # Sort by score descending
    results.sort(key=lambda x: (x["score"], -x["sl_pct"]), reverse=True)
    return results


if __name__ == "__main__":
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    scan = scan_markets()
    print("\n" + "="*75)
    print(f"{'RANK':<5} {'ATIVO':<8} {'SCORE':<7} {'PRECO':<12} {'RSI 14':<8} {'STOP LOSS %':<12} {'CLASSIFICACAO'}")
    print("="*75)
    for i, r in enumerate(scan[:10], 1):
        status = "[FORTE COMPRA]" if r["score"] >= 5 else ("[RADAR]" if r["score"] >= 3 else "[FORA]")
        print(f"{i:<5} {r['coin']:<8} {r['score']}/6    ${r['current_price']:<11.4f} {r['rsi']:<8} -{r['sl_pct']:<10.2f}% {status}")
    print("="*75)

    # Save to json for quick consumption
    out_file = ROOT / "data" / "market_scan_latest.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(scan, f, indent=2, ensure_ascii=False)
    print(f"\n[+] Scan completo salvo em: {out_file}")
