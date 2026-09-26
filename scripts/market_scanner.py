"""Market Dual-Strategy Scanner for Hyperliquid Mainnet.
Evaluates both:
1. 2h Macro Pullback (rsi-t200b): Trend Macro Bull + RSI < 38 Pullback Recovery (Top Alpha)
2. 1h Confluence Breakout: 6-Pillar Confluence (Trend + Fast EMAs + RSI + Donchian + Vol)
across the verified Top 25 high-performing assets on Hyperliquid.
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

# Verified Top 25 high-probability assets on Hyperliquid Mainnet
CANDIDATES = [
    "SOL", "NEAR", "AVAX", "SUI", "DOGE", "LINK", "ETH", "ARB", "INJ", 
    "STRK", "0G", "BNB", "LAYER", "ZORA", "MOODENG", "BERA", "KAITO", 
    "CELO", "ZEC", "VVV", "kNEIRO", "PNUT", "ANIME", "GMT", "BTC"
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
    start_1h = now - (15 * 24 * 3600 * 1000) # 15 days of 1h
    start_2h = now - (35 * 24 * 3600 * 1000) # 35 days of 2h
    
    results = []
    print(f"[*] Escaneando {len(CANDIDATES)} ativos no Universo Campeão Hyperliquid (1h & 2h)...")

    for coin in CANDIDATES:
        if coin not in universe:
            continue
        try:
            # 1. Fetch 1h Candles for Confluence
            candles_1h = info.candles_snapshot(coin, "1h", start_1h, now)
            if len(candles_1h) < 205:
                continue

            closes_1h = [float(c["c"]) for c in candles_1h]
            highs_1h = [float(c["h"]) for c in candles_1h]
            lows_1h = [float(c["l"]) for c in candles_1h]
            volumes_1h = [float(c["v"]) for c in candles_1h]
            current_price = closes_1h[-1]

            ema200_1h_series = calculate_ema(closes_1h, 200)
            ema21_1h_series = calculate_ema(closes_1h, 21)
            ema9_1h_series = calculate_ema(closes_1h, 9)

            ema200_1h = ema200_1h_series[-1] if ema200_1h_series else current_price
            ema21_1h = ema21_1h_series[-1] if ema21_1h_series else current_price
            ema9_1h = ema9_1h_series[-1] if ema9_1h_series else current_price

            rsi_1h = calculate_rsi(closes_1h, 14)
            atr_1h = calculate_atr(candles_1h, 14)
            donchian_high = max(highs_1h[-21:-1])

            # 1h Confluence Scoring
            score_1h = 0
            details_1h = []
            if current_price > ema200_1h:
                score_1h += 2
                details_1h.append("Tendência Macro 1h (Preço > EMA 200)")
            if 50.0 <= rsi_1h <= 72.0:
                score_1h += 1
                details_1h.append(f"RSI 1h Saudável ({rsi_1h:.1f})")
            dist_to_breakout = (donchian_high - current_price) / current_price * 100
            if current_price >= donchian_high or dist_to_breakout <= 1.0:
                score_1h += 1
                details_1h.append("Rompimento Donchian 20")
            if ema9_1h > ema21_1h:
                score_1h += 1
                details_1h.append("Médias Rápidas (EMA 9 > 21)")
            avg_vol_20 = sum(volumes_1h[-21:-1]) / 20 if len(volumes_1h) >= 21 else volumes_1h[-1]
            if volumes_1h[-1] > avg_vol_20 * 0.9:
                score_1h += 1
                details_1h.append("Volume Relevante")

            # 2. Fetch 2h Candles for Macro Pullback (rsi-t200b)
            is_2h_pullback = False
            rsi_2h = 50.0
            atr_2h = atr_1h
            sl_price = current_price - (2.0 * atr_1h)
            tp1_price = current_price + (1.5 * (current_price - sl_price))
            setup_name = "1h Confluência"

            try:
                candles_2h = info.candles_snapshot(coin, "2h", start_2h, now)
                if len(candles_2h) >= 205:
                    closes_2h = [float(c["c"]) for c in candles_2h]
                    ema200_2h_series = calculate_ema(closes_2h, 200)
                    ema200_2h = ema200_2h_series[-1] if ema200_2h_series else current_price
                    rsi_2h = calculate_rsi(closes_2h, 14)
                    atr_2h = calculate_atr(candles_2h, 14)

                    # 2h Pullback condition: Macro Bull + RSI in pullback zone (< 38.0)
                    if current_price > ema200_2h and rsi_2h <= 38.0:
                        is_2h_pullback = True
                        setup_name = "2h Pullback Alpha (rsi-t200b)"
                        sl_price = current_price - (2.5 * atr_2h) # Calibração campeã
                        tp1_price = current_price + (1.6 * atr_2h) # Calibração campeã
            except Exception:
                pass

            sl_pct = ((current_price - sl_price) / current_price) * 100
            tp2_price = current_price + (2.5 * (current_price - sl_price))
            tp3_price = current_price + (4.0 * (current_price - sl_price))

            final_score = 6 if is_2h_pullback else score_1h
            final_details = ["⭐ Oportunidade Campeã 2h: Preço acima de EMA 200 com RSI em Pullback Saudável"] if is_2h_pullback else details_1h
            status = "[2H PULLBACK ALPHA]" if is_2h_pullback else ("[FORTE COMPRA 1H]" if score_1h >= 5 else ("[RADAR]" if score_1h >= 3 else "[FORA]"))

            sz_decimals = int(universe[coin].get("szDecimals", 2))
            factor = 10 ** sz_decimals
            size = math.floor((50.0 / current_price) * factor) / factor

            results.append({
                "coin": coin,
                "score": final_score,
                "setup": setup_name,
                "status": status,
                "is_2h_pullback": is_2h_pullback,
                "current_price": current_price,
                "rsi_1h": round(rsi_1h, 1),
                "rsi_2h": round(rsi_2h, 1),
                "atr": round(atr_2h if is_2h_pullback else atr_1h, 4),
                "sl_price": round(sl_price, 4),
                "sl_pct": round(sl_pct, 2),
                "tp1_price": round(tp1_price, 4),
                "tp2_price": round(tp2_price, 4),
                "tp3_price": round(tp3_price, 4),
                "size": size,
                "sz_decimals": sz_decimals,
                "details": final_details
            })

            time.sleep(0.06)
        except Exception:
            continue

    # Sort: 2h pullbacks first, then highest score
    results.sort(key=lambda x: (1 if x["is_2h_pullback"] else 0, x["score"], -x["sl_pct"]), reverse=True)
    return results


if __name__ == "__main__":
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    scan = scan_markets()
    print("\n" + "="*85)
    print(f"{'RANK':<5} {'ATIVO':<8} {'SCORE':<7} {'SETUP':<28} {'PRECO':<12} {'RSI 2h/1h':<12} {'STATUS'}")
    print("="*85)
    for i, r in enumerate(scan[:12], 1):
        rsi_str = f"{r['rsi_2h']:.0f} / {r['rsi_1h']:.0f}"
        print(f"{i:<5} {r['coin']:<8} {r['score']}/6    {r['setup']:<28} ${r['current_price']:<11.4f} {rsi_str:<12} {r['status']}")
    print("="*85)

    out_file = ROOT / "data" / "market_scan_latest.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(scan, f, indent=2, ensure_ascii=False)
    print(f"\n[+] Scan Dual-Strategy salvo com sucesso em: {out_file}")
