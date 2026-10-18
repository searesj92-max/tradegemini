"""Market Tri-Strategy & Oliver Kell Fractal Cycle Scanner for Hyperliquid Mainnet.
Evaluates:
1. 2h Macro Pullback (rsi-t200b): Trend Macro Bull + RSI < 38 Pullback Recovery (Top Alpha)
2. 1h Confluence Breakout: 6-Pillar Confluence (Trend + Fast EMAs + RSI + Donchian + Vol)
3. Oliver Kell 6-Phase Fractal Cycle (Aurora Fractal):
   - Semáforo Macro (Diário / Semanal EMA 9 & EMA 21) + Lupa (4h / 1h)
   - Fases 1 a 6:
     * Fase 1: Extensão de Reversão (Capitulação / Radar)
     * Fase 2: Wedge Pop (Estouro da Cunha / Barra de Ignição)
     * Fase 3: EMA Crossback (Reteste das Médias EMA 9/21)
     * Fase 4: Base n' Break (Consolidação Apertada + Rompimento)
     * Fase 5: Extensão de Exaustão (Euforia / Realizar Parcial)
     * Fase 6: Wedge Drop (Queda da Cunha / Sinal Vermelho)
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


def classify_oliver_kell_phase(candles: list[dict]) -> dict:
    """Classifica os candles nas 6 Fases do Ciclo de Preço de Oliver Kell (EMA 9 & EMA 21)."""
    if len(candles) < 30:
        return {
            "semaphore": "NEUTRO",
            "semaphore_green": False,
            "phase": 0,
            "phase_name": "Dados Insuficientes",
            "signal": None,
            "ema9": 0.0,
            "ema21": 0.0,
        }

    closes = [float(c["c"]) for c in candles]
    opens = [float(c["o"]) for c in candles]
    highs = [float(c["h"]) for c in candles]
    lows = [float(c["l"]) for c in candles]
    vols = [float(c["v"]) for c in candles]

    ema9_s = calculate_ema(closes, 9)
    ema21_s = calculate_ema(closes, 21)
    atr = max(calculate_atr(candles, 14), closes[-1] * 0.005)

    # Align EMA arrays to end of closes
    e9_curr = ema9_s[-1]
    e9_prev = ema9_s[-2] if len(ema9_s) >= 2 else e9_curr
    e21_curr = ema21_s[-1]
    e21_prev = ema21_s[-2] if len(ema21_s) >= 2 else e21_curr

    c = closes[-1]
    o = opens[-1]
    h = highs[-1]
    l = lows[-1]
    v = vols[-1]
    vol_sma20 = sum(vols[-21:-1]) / 20.0 if len(vols) >= 21 else max(v, 1e-9)
    rvol = v / max(vol_sma20, 1e-9)

    e21_slope_up = e21_curr >= e21_prev
    semaphore_green = (c > e21_curr) and (e21_slope_up or e9_curr >= e21_curr)
    semaphore = "VERDE" if semaphore_green else "VERMELHO"

    dist_atr = (c - e21_curr) / atr
    high_dist_atr = (h - e21_curr) / atr
    low_dist_atr = (e21_curr - l) / atr

    # Count last 10 bars vs EMA 21
    below_10 = 0
    above_10 = 0
    for idx in range(1, 11):
        c_idx = closes[-1 - idx]
        e21_idx = ema21_s[-1 - idx] if len(ema21_s) > idx else e21_curr
        if c_idx < e21_idx:
            below_10 += 1
        else:
            above_10 += 1

    phase = 0
    phase_name = "Neutro"
    signal = None

    if c < e21_curr and not e21_slope_up and low_dist_atr >= 2.5 and rvol >= 1.2:
        phase = 1
        phase_name = "Fase 1: Extensão de Reversão (Capitulação/Radar)"
        signal = "RADAR_CAPITULACAO"
    elif (
        c > e21_curr
        and c > e9_curr
        and c > o
        and below_10 >= 4
        and (closes[-2] <= e21_prev or closes[-3] <= ema21_s[-3])
        and (c - o) >= 0.45 * max(h - l, 1e-9)
        and rvol >= 1.05
    ):
        phase = 2
        phase_name = "Fase 2: Wedge Pop (Estouro da Cunha / Ignição)"
        signal = "BUY_FASE2_WEDGE_POP"
    elif c > e21_curr and high_dist_atr >= 3.2 and above_10 >= 7:
        phase = 5
        phase_name = "Fase 5: Extensão de Exaustão (Realizar Parcial)"
        signal = "TAKE_PARTIAL_FASE5"
    elif (
        semaphore_green
        and above_10 >= 7
        and c > max(highs[-8:-1])
        and c > o
        and ((max(highs[-8:-1]) - min(lows[-8:-1])) / atr) <= 4.2
        and rvol >= 1.05
        and dist_atr < 2.8
    ):
        phase = 4
        phase_name = "Fase 4: Base n' Break (Rompimento de Base)"
        signal = "BUY_FASE4_BASE_BREAK"
    elif (
        semaphore_green
        and above_10 >= 6
        and (l <= e9_curr * 1.008 or lows[-2] <= e9_prev * 1.008)
        and (l >= e21_curr * 0.975)
        and c > e9_curr
        and c > o
        and (c > highs[-2] or (c - o) >= 0.45 * atr)
        and dist_atr < 2.2
    ):
        phase = 3
        phase_name = "Fase 3: EMA Crossback (Reteste das Médias)"
        signal = "BUY_FASE3_CROSSBACK"
    elif c < e21_curr and ((closes[-2] >= e21_prev and (o - c) >= 0.4 * atr) or (not e21_slope_up and c < e9_curr)):
        phase = 6
        if closes[-2] >= e21_prev or closes[-3] >= ema21_s[-3]:
            phase_name = "Fase 6: Wedge Drop (Perda da EMA 21)"
            signal = "EXIT_OR_SHORT_FASE6"
        else:
            phase_name = "Fase 6: Tendência de Baixa (Sinal Vermelho)"
            signal = "SINAL_VERMELHO"
    else:
        if semaphore_green:
            phase = 3 if dist_atr < 1.2 else 4
            phase_name = "Tendência Verde (Acima da EMA 21)"
        else:
            phase = 6
            phase_name = "Fase 6: Abaixo da EMA 21 (Aguardando Wedge Pop)"

    return {
        "semaphore": semaphore,
        "semaphore_green": semaphore_green,
        "phase": phase,
        "phase_name": phase_name,
        "signal": signal,
        "ema9": round(e9_curr, 4),
        "ema21": round(e21_curr, 4),
    }


def scan_markets():
    info = Info(constants.MAINNET_API_URL, skip_ws=True)
    meta = info.meta()
    universe = {coin["name"]: coin for coin in meta.get("universe", [])}
    
    now = int(time.time() * 1000)
    start_1h = now - (15 * 24 * 3600 * 1000) # 15 days of 1h
    start_2h = now - (35 * 24 * 3600 * 1000) # 35 days of 2h
    start_1d = now - (65 * 24 * 3600 * 1000) # 65 days of 1d for Oliver Kell Macro Map
    
    results = []
    print(f"[*] Escaneando {len(CANDIDATES)} ativos no Universo Campeão Hyperliquid (1d, 2h & 1h + Ciclo Oliver Kell)...")

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

            # 2. Fetch 2h Candles for Macro Pullback (rsi-t200b) & Oliver Kell 2h Lupa
            is_2h_pullback = False
            rsi_2h = 50.0
            atr_2h = atr_1h
            sl_price = current_price - (2.0 * atr_1h)
            tp1_price = current_price + (1.5 * (current_price - sl_price))
            setup_name = "1h Confluência"
            ok_2h = classify_oliver_kell_phase(candles_1h)

            try:
                candles_2h = info.candles_snapshot(coin, "2h", start_2h, now)
                if len(candles_2h) >= 50:
                    ok_2h = classify_oliver_kell_phase(candles_2h)
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

            # 3. Fetch 1d Candles for Oliver Kell Macro Map (Semáforo Diário)
            ok_1d = {"semaphore": "NEUTRO", "semaphore_green": False, "phase": 0, "phase_name": "N/A", "signal": None}
            try:
                candles_1d = info.candles_snapshot(coin, "1d", start_1d, now)
                if len(candles_1d) >= 30:
                    ok_1d = classify_oliver_kell_phase(candles_1d)
            except Exception:
                pass

            # Integração Fractal de Oliver Kell (Mapa 1D + Gatilho 2H)
            is_oliver_trigger = ok_1d["semaphore_green"] and (ok_2h["signal"] in ("BUY_FASE2_WEDGE_POP", "BUY_FASE3_CROSSBACK", "BUY_FASE4_BASE_BREAK"))
            if is_oliver_trigger and not is_2h_pullback:
                setup_name = f"Oliver Kell ({ok_2h['phase_name'].split(':')[0]})"
                details_1h.append(f"🔥 Gatilho Fractal Oliver Kell: Mapa 1D Verde + {ok_2h['phase_name']}")
                score_1h = max(score_1h, 5)
            elif ok_1d["semaphore_green"]:
                details_1h.append(f"🟢 Semáforo Macro 1D Verde ({ok_1d['phase_name']})")
            else:
                details_1h.append(f"🔴 Semáforo Macro 1D Vermelho ({ok_1d['phase_name']})")

            sl_pct = ((current_price - sl_price) / current_price) * 100
            tp2_price = current_price + (2.5 * (current_price - sl_price))
            tp3_price = current_price + (4.0 * (current_price - sl_price))

            final_score = 6 if is_2h_pullback else score_1h
            final_details = ["⭐ Oportunidade Campeã 2h: Preço acima de EMA 200 com RSI em Pullback Saudável"] + details_1h if is_2h_pullback else details_1h
            status = "[2H PULLBACK ALPHA]" if is_2h_pullback else ("[OLIVER FRACTAL BUY]" if is_oliver_trigger else ("[FORTE COMPRA 1H]" if score_1h >= 5 else ("[RADAR]" if score_1h >= 3 else "[FORA]")))

            sz_decimals = int(universe[coin].get("szDecimals", 2))
            factor = 10 ** sz_decimals
            size = math.floor((50.0 / current_price) * factor) / factor

            results.append({
                "coin": coin,
                "score": final_score,
                "setup": setup_name,
                "status": status,
                "is_2h_pullback": is_2h_pullback,
                "is_oliver_fractal_buy": is_oliver_trigger,
                "oliver_macro_semaphore": ok_1d["semaphore"],
                "oliver_macro_phase": ok_1d["phase_name"],
                "oliver_lupa_phase": ok_2h["phase_name"],
                "oliver_lupa_signal": ok_2h["signal"],
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

    # Sort: 2h pullbacks first, then Oliver Fractal triggers, then highest score
    results.sort(key=lambda x: (1 if x["is_2h_pullback"] else 0, 1 if x.get("is_oliver_fractal_buy") else 0, x["score"], -x["sl_pct"]), reverse=True)
    return results


if __name__ == "__main__":
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    scan = scan_markets()
    print("\n" + "="*110)
    print(f"{'RANK':<5} {'ATIVO':<7} {'SCORE':<6} {'SEMÁFORO 1D':<12} {'FASE 2H (OLIVER KELL)':<38} {'PRECO':<11} {'STATUS'}")
    print("="*110)
    for i, r in enumerate(scan[:15], 1):
        fase_curta = r.get("oliver_lupa_phase", "")[:36]
        print(f"{i:<5} {r['coin']:<7} {r['score']}/6   {r.get('oliver_macro_semaphore',''):<12} {fase_curta:<38} ${r['current_price']:<10.4f} {r['status']}")
    print("="*110)

    out_file = ROOT / "data" / "market_scan_latest.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(scan, f, indent=2, ensure_ascii=False)
    print(f"\n[+] Scan Tri-Strategy (incluindo Ciclo Fractal de Oliver Kell) salvo com sucesso em: {out_file}")
