#!/usr/bin/env python3
"""
Botrade Quantitative Backtest Engine (Hyperliquid Historical Data up to 720 Days)
Features:
- Native Hyperliquid OHLCV fetch via candles_snapshot (up to 720 days).
- Automatic handling of newer tokens (starts from token listing date).
- Vectorized technical indicators: EMA 9, EMA 21, EMA 50, EMA 200, Bollinger Bands, RSI 14, ATR 14.
- Trade simulation: Dual-Engine (2h Pullback + 1h Confluence), Isolated Pullback, Confluence, or Mean Reversion.
- Realistic transaction costs: Hyperliquid Taker Fee (0.035%) + Slippage (0.05%).
- Strict SL, TP1, TP2, and Ratchet Trailing Stop (+30% ROE -> Breakeven protection).
- Output formatted directly for TradingView Lightweight Charts (candles, indicators, markers, equity curve).
- Institutional performance metrics & Gertrude Chief of Staff approval classification.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Fix Windows console encoding for UTF-8 characters
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from hyperliquid_executor import HyperliquidExecutor


def fetch_historical_candles(
    executor: HyperliquidExecutor,
    coin: str,
    timeframe: str = "1d",
    days: int = 720
) -> list[dict]:
    """Fetches up to `days` of historical candles from Hyperliquid.
    Paginates if needed for granular timeframes (1h, 2h).
    """
    now_ms = int(time.time() * 1000)
    target_start_ms = now_ms - (days * 24 * 3600 * 1000)

    try:
        # First attempt: standard snapshot
        candles = executor.info.candles_snapshot(coin, timeframe, target_start_ms, now_ms)
        if not candles:
            return []

        # If 1h or 2h and we didn't reach the target start time due to 5,000 candle limit, paginate backward once
        if timeframe in ("1h", "2h") and candles[0]["t"] > target_start_ms and len(candles) >= 4900:
            oldest_t = candles[0]["t"] - 1
            older_candles = executor.info.candles_snapshot(coin, timeframe, target_start_ms, oldest_t)
            if older_candles:
                candles = older_candles + candles

        return candles
    except Exception as e:
        print(f"[-] Erro ao obter candles para {coin}: {e}", file=sys.stderr)
        return []


def calculate_indicators(candles: list[dict]) -> dict:
    """Computes technical indicators across the candle series."""
    n = len(candles)
    if n == 0:
        return {}

    closes = [float(c["c"]) for c in candles]
    highs = [float(c["h"]) for c in candles]
    lows = [float(c["l"]) for c in candles]
    volumes = [float(c["v"]) for c in candles]
    times = [int(c["t"] / 1000) for c in candles]

    # --- EMA Helper ---
    def calc_ema(series: list[float], span: int) -> list[float]:
        res = [series[0]]
        mult = 2.0 / (span + 1.0)
        for val in series[1:]:
            res.append((val - res[-1]) * mult + res[-1])
        return res

    ema9 = calc_ema(closes, 9)
    ema21 = calc_ema(closes, 21)
    ema50 = calc_ema(closes, 50)
    ema200 = calc_ema(closes, 200)

    # --- ATR 14 Helper ---
    tr_list = []
    for i in range(n):
        if i == 0:
            tr_list.append(highs[0] - lows[0])
        else:
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i - 1]),
                abs(lows[i] - closes[i - 1])
            )
            tr_list.append(tr)

    atr14 = [tr_list[0]]
    atr_span = 14
    atr_mult = 1.0 / atr_span
    for val in tr_list[1:]:
        atr14.append((val - atr14[-1]) * atr_mult + atr14[-1])

    # --- RSI 14 Helper ---
    gains = [0.0]
    losses = [0.0]
    for i in range(1, n):
        diff = closes[i] - closes[i - 1]
        gains.append(max(0.0, diff))
        losses.append(max(0.0, -diff))

    avg_gain = sum(gains[:14]) / 14.0 if n >= 14 else 0.0
    avg_loss = sum(losses[:14]) / 14.0 if n >= 14 else 0.0
    rsi = [50.0] * min(n, 14)

    for i in range(14, n):
        avg_gain = (avg_gain * 13.0 + gains[i]) / 14.0
        avg_loss = (avg_loss * 13.0 + losses[i]) / 14.0
        if avg_loss == 0:
            rsi.append(100.0)
        else:
            rs = avg_gain / avg_loss
            rsi.append(100.0 - (100.0 / (1.0 + rs)))

    # --- Bollinger Bands (20, 2) Helper ---
    bb_upper = []
    bb_lower = []
    bb_mid = []
    bb_period = 20
    for i in range(n):
        if i < bb_period - 1:
            bb_mid.append(closes[i])
            bb_upper.append(closes[i] * 1.02)
            bb_lower.append(closes[i] * 0.98)
        else:
            window = closes[i - bb_period + 1 : i + 1]
            mean_val = sum(window) / bb_period
            variance = sum((x - mean_val) ** 2 for x in window) / bb_period
            std_dev = math.sqrt(variance)
            bb_mid.append(mean_val)
            bb_upper.append(mean_val + 2.0 * std_dev)
            bb_lower.append(mean_val - 2.0 * std_dev)

    # --- Donchian 20 High ---
    donchian_high = []
    for i in range(n):
        if i < 20:
            donchian_high.append(max(highs[:i+1]))
        else:
            donchian_high.append(max(highs[i-20:i]))

    # --- Volume SMA 20 ---
    vol_sma20 = []
    for i in range(n):
        if i < 19:
            vol_sma20.append(volumes[i])
        else:
            vol_sma20.append(sum(volumes[i - 19 : i + 1]) / 20.0)

    return {
        "times": times,
        "closes": closes,
        "highs": highs,
        "lows": lows,
        "volumes": volumes,
        "ema9": ema9,
        "ema21": ema21,
        "ema50": ema50,
        "ema200": ema200,
        "atr14": atr14,
        "rsi": rsi,
        "bb_upper": bb_upper,
        "bb_lower": bb_lower,
        "bb_mid": bb_mid,
        "donchian_high": donchian_high,
        "vol_sma20": vol_sma20,
    }


def run_simulation(
    coin: str,
    candles: list[dict],
    strategy: str = "dual",
    initial_capital: float = 100.0,
    margin_per_trade: float = 15.0,
    leverage: int = 10,
    fee_pct: float = 0.00035,      # 0.035% Hyperliquid Taker Fee
    slippage_pct: float = 0.0005,  # 0.05% Slippage
) -> dict:
    """Simulates trading over the historical candle series with partial TP and risk caps."""
    n = len(candles)
    if n < 30:
        return {"error": f"Dados insuficientes para simulação: apenas {n} candles encontrados."}

    ind = calculate_indicators(candles)
    times = ind["times"]
    closes = ind["closes"]
    highs = ind["highs"]
    lows = ind["lows"]
    volumes = ind["volumes"]
    ema9 = ind["ema9"]
    ema21 = ind["ema21"]
    ema200 = ind["ema200"]
    atr14 = ind["atr14"]
    rsi = ind["rsi"]
    bb_upper = ind["bb_upper"]
    bb_lower = ind["bb_lower"]
    bb_mid = ind["bb_mid"]
    donchian_high = ind["donchian_high"]
    vol_sma20 = ind["vol_sma20"]

    capital = initial_capital
    peak_capital = initial_capital
    max_dd_usd = 0.0
    max_dd_pct = 0.0

    trades = []
    markers = []
    equity_curve = [{"time": times[0], "value": round(capital, 2), "drawdown_pct": 0.0}]

    in_position = False
    pos_entry_price = 0.0
    pos_entry_time = 0
    pos_entry_index = 0
    pos_remaining_tokens = 0.0
    pos_original_tokens = 0.0
    pos_sl = 0.0
    pos_tp1 = 0.0
    pos_tp2 = 0.0
    pos_strategy = ""
    ratchet_activated = False
    tp1_realized = False
    realized_pnl_trade = 0.0

    total_fees_paid = 0.0

    start_bar = min(30, n // 4)

    for i in range(start_bar, n):
        cur_t = times[i]
        c_open = float(candles[i]["o"])
        c_high = highs[i]
        c_low = lows[i]
        c_close = closes[i]
        c_atr = atr14[i]

        # -------------------------------------------------------------
        # 1. MANAGE ACTIVE POSITION
        # -------------------------------------------------------------
        if in_position:
            current_max_roe = ((c_high - pos_entry_price) / pos_entry_price) * leverage * 100.0

            # Ratchet Trailing Stop: +30% ROE locks SL to Breakeven
            if current_max_roe >= 30.0 and not ratchet_activated:
                pos_sl = max(pos_sl, pos_entry_price * (1.0 + (fee_pct * 2 + slippage_pct * 2)))
                ratchet_activated = True

            # Check Partial Take Profit 1 (50% exit at 1.5R)
            if c_high >= pos_tp1 and not tp1_realized:
                exit_price = pos_tp1 * (1.0 - slippage_pct)
                half_tokens = pos_original_tokens * 0.5
                gross_pnl_tp1 = (exit_price - pos_entry_price) * half_tokens
                exit_fee_tp1 = (exit_price * half_tokens) * fee_pct
                net_pnl_tp1 = gross_pnl_tp1 - exit_fee_tp1

                realized_pnl_trade += net_pnl_tp1
                total_fees_paid += exit_fee_tp1
                capital += net_pnl_tp1
                pos_remaining_tokens -= half_tokens
                tp1_realized = True

                # Lock SL of the remaining half to Breakeven
                pos_sl = max(pos_sl, pos_entry_price * (1.0 + (fee_pct * 2 + slippage_pct * 2)))
                ratchet_activated = True

                markers.append({
                    "time": cur_t,
                    "position": "aboveBar",
                    "color": "#10b981",
                    "shape": "arrowDown",
                    "text": f"TP1 (50%): +{((exit_price - pos_entry_price)/pos_entry_price)*leverage*100:.1f}%"
                })

            # Check Take Profit 2 (Full Target on remaining tokens)
            if c_high >= pos_tp2:
                exit_price = pos_tp2 * (1.0 - slippage_pct)
                gross_pnl_tp2 = (exit_price - pos_entry_price) * pos_remaining_tokens
                exit_fee_tp2 = (exit_price * pos_remaining_tokens) * fee_pct
                net_pnl_tp2 = gross_pnl_tp2 - exit_fee_tp2

                realized_pnl_trade += net_pnl_tp2
                total_fees_paid += exit_fee_tp2
                capital += net_pnl_tp2

                final_roe_pct = (realized_pnl_trade / margin_per_trade) * 100.0

                trades.append({
                    "id": len(trades) + 1,
                    "type": "LONG",
                    "strategy": pos_strategy,
                    "entry_time": pos_entry_time,
                    "entry_date": datetime.fromtimestamp(pos_entry_time, timezone.utc).strftime("%d/%m/%Y %H:%M"),
                    "entry_price": round(pos_entry_price, 4),
                    "exit_time": cur_t,
                    "exit_date": datetime.fromtimestamp(cur_t, timezone.utc).strftime("%d/%m/%Y %H:%M"),
                    "exit_price": round(exit_price, 4),
                    "exit_reason": "TAKE_PROFIT_2",
                    "exit_reason_label": "🎯 Alvo TP2",
                    "pnl_usd": round(realized_pnl_trade, 2),
                    "roe_pct": round(final_roe_pct, 2),
                    "hold_bars": i - pos_entry_index,
                    "ratchet_protected": ratchet_activated,
                })

                markers.append({
                    "time": cur_t,
                    "position": "aboveBar",
                    "color": "#10b981",
                    "shape": "arrowDown",
                    "text": f"🎯 TP2: {final_roe_pct:+.1f}%"
                })

                in_position = False
                ratchet_activated = False
                tp1_realized = False
                realized_pnl_trade = 0.0

            # Check Stop Loss hit
            elif c_low <= pos_sl:
                exit_price = pos_sl * (1.0 - slippage_pct)
                gross_pnl_sl = (exit_price - pos_entry_price) * pos_remaining_tokens
                exit_fee_sl = (exit_price * pos_remaining_tokens) * fee_pct
                net_pnl_sl = gross_pnl_sl - exit_fee_sl

                realized_pnl_trade += net_pnl_sl
                total_fees_paid += exit_fee_sl
                capital += net_pnl_sl

                final_roe_pct = (realized_pnl_trade / margin_per_trade) * 100.0

                is_be = (ratchet_activated or tp1_realized) and realized_pnl_trade >= 0
                trades.append({
                    "id": len(trades) + 1,
                    "type": "LONG",
                    "strategy": pos_strategy,
                    "entry_time": pos_entry_time,
                    "entry_date": datetime.fromtimestamp(pos_entry_time, timezone.utc).strftime("%d/%m/%Y %H:%M"),
                    "entry_price": round(pos_entry_price, 4),
                    "exit_time": cur_t,
                    "exit_date": datetime.fromtimestamp(cur_t, timezone.utc).strftime("%d/%m/%Y %H:%M"),
                    "exit_price": round(exit_price, 4),
                    "exit_reason": "RAT_BE" if is_be else "STOP_LOSS",
                    "exit_reason_label": "🛡️ 0x0 Protegido" if is_be else "🛑 Stop Loss",
                    "pnl_usd": round(realized_pnl_trade, 2),
                    "roe_pct": round(final_roe_pct, 2),
                    "hold_bars": i - pos_entry_index,
                    "ratchet_protected": ratchet_activated,
                })

                markers.append({
                    "time": cur_t,
                    "position": "aboveBar",
                    "color": "#10b981" if is_be else "#ef4444",
                    "shape": "arrowDown",
                    "text": f"{'0x0' if is_be else 'SL'}: {final_roe_pct:+.1f}%"
                })

                in_position = False
                ratchet_activated = False
                tp1_realized = False
                realized_pnl_trade = 0.0

            # Max duration safety exit (35 bars)
            elif (i - pos_entry_index) >= 35:
                exit_price = c_close * (1.0 - slippage_pct)
                gross_pnl_time = (exit_price - pos_entry_price) * pos_remaining_tokens
                exit_fee_time = (exit_price * pos_remaining_tokens) * fee_pct
                net_pnl_time = gross_pnl_time - exit_fee_time

                realized_pnl_trade += net_pnl_time
                total_fees_paid += exit_fee_time
                capital += net_pnl_time

                final_roe_pct = (realized_pnl_trade / margin_per_trade) * 100.0

                trades.append({
                    "id": len(trades) + 1,
                    "type": "LONG",
                    "strategy": pos_strategy,
                    "entry_time": pos_entry_time,
                    "entry_date": datetime.fromtimestamp(pos_entry_time, timezone.utc).strftime("%d/%m/%Y %H:%M"),
                    "entry_price": round(pos_entry_price, 4),
                    "exit_time": cur_t,
                    "exit_date": datetime.fromtimestamp(cur_t, timezone.utc).strftime("%d/%m/%Y %H:%M"),
                    "exit_price": round(exit_price, 4),
                    "exit_reason": "TIME_EXIT",
                    "exit_reason_label": "⏱️ Time Exit",
                    "pnl_usd": round(realized_pnl_trade, 2),
                    "roe_pct": round(final_roe_pct, 2),
                    "hold_bars": i - pos_entry_index,
                    "ratchet_protected": ratchet_activated,
                })

                markers.append({
                    "time": cur_t,
                    "position": "aboveBar",
                    "color": "#f59e0b",
                    "shape": "arrowDown",
                    "text": f"TIME: {final_roe_pct:+.1f}%"
                })

                in_position = False
                ratchet_activated = False
                tp1_realized = False
                realized_pnl_trade = 0.0

        # -------------------------------------------------------------
        # 2. SCAN FOR NEW ENTRY SIGNALS (IF NOT IN POSITION)
        # -------------------------------------------------------------
        if not in_position:
            trigger_entry = False
            strat_name = ""
            entry_sl = 0.0
            entry_tp1 = 0.0
            entry_tp2 = 0.0

            # Condition 1: Pullback Macro (Trend Continuation near EMA 200 / Oversold RSI)
            is_uptrend = c_close > ema200[i]
            prev_rsi_low = min(rsi[max(0, i - 4) : i])
            rsi_oversold_pullback = prev_rsi_low <= 38.0 and rsi[i] > rsi[i - 1]
            bullish_turn = c_close > ema9[i] and c_close > c_open

            if strategy in ("dual", "pullback") and is_uptrend and rsi_oversold_pullback and bullish_turn:
                trigger_entry = True
                strat_name = "Pullback Macro"
                raw_sl = c_close - (1.6 * c_atr)
                max_sl = c_close * 0.965  # Max -3.5% SL distance (-35% ROE at 10x)
                entry_sl = max(raw_sl, max_sl)
                risk_dist = c_close - entry_sl
                entry_tp1 = c_close + (2.0 * risk_dist)
                entry_tp2 = c_close + (3.8 * risk_dist)

            # Condition 2: Confluence Breakout (Strict Score 5/6 evaluation)
            score_1h = 0
            if c_close > ema200[i]: score_1h += 2
            if 50.0 <= rsi[i] <= 68.0: score_1h += 1
            if c_close > donchian_high[i]: score_1h += 1  # Genuine breakout above 20-period high
            if ema9[i] > ema21[i] and ema9[i-1] <= ema21[i-1]: score_1h += 1  # Fresh cross
            if volumes[i] >= (1.2 * vol_sma20[i]) if vol_sma20[i] > 0 else True: score_1h += 1

            if not trigger_entry and strategy in ("dual", "confluence") and score_1h >= 5:
                trigger_entry = True
                strat_name = "Confluência Breakout"
                raw_sl = c_close - (1.5 * c_atr)
                max_sl = c_close * 0.965
                entry_sl = max(raw_sl, max_sl)
                risk_dist = c_close - entry_sl
                entry_tp1 = c_close + (2.0 * risk_dist)
                entry_tp2 = c_close + (3.5 * risk_dist)

            # Condition 3: Mean Reversion (Bollinger Bands lower bounce)
            if not trigger_entry and strategy == "mean_reversion":
                touched_lower = lows[i - 1] <= bb_lower[i - 1] or c_low <= bb_lower[i]
                bounce_green = c_close > c_open and rsi[i] < 40.0 and c_close > ema9[i]
                if touched_lower and bounce_green:
                    trigger_entry = True
                    strat_name = "Mean Reversion"
                    raw_sl = c_close - (1.4 * c_atr)
                    max_sl = c_close * 0.97
                    entry_sl = max(raw_sl, max_sl)
                    entry_tp1 = bb_mid[i]
                    entry_tp2 = bb_upper[i]

            # Execute Entry if triggered
            if trigger_entry and entry_sl < c_close:
                in_position = True
                pos_entry_price = c_close * (1.0 + slippage_pct)
                pos_entry_time = cur_t
                pos_entry_index = i
                pos_strategy = strat_name
                pos_sl = entry_sl
                pos_tp1 = entry_tp1
                pos_tp2 = entry_tp2
                ratchet_activated = False
                tp1_realized = False
                realized_pnl_trade = 0.0

                pos_notional = margin_per_trade * leverage
                pos_original_tokens = pos_notional / pos_entry_price
                pos_remaining_tokens = pos_original_tokens
                entry_fee = pos_notional * fee_pct
                total_fees_paid += entry_fee
                capital -= entry_fee

                markers.append({
                    "time": cur_t,
                    "position": "belowBar",
                    "color": "#10b981",
                    "shape": "arrowUp",
                    "text": f"BUY ${pos_entry_price:.2f}"
                })

        # Track Equity Curve and Drawdown
        peak_capital = max(peak_capital, capital)
        dd_usd = peak_capital - capital
        dd_pct = (dd_usd / peak_capital) * 100.0 if peak_capital > 0 else 0.0
        max_dd_usd = max(max_dd_usd, dd_usd)
        max_dd_pct = max(max_dd_pct, dd_pct)

        equity_curve.append({
            "time": cur_t,
            "value": round(capital, 2),
            "drawdown_pct": round(dd_pct, 2)
        })

    # Close any remaining position at end of backtest
    if in_position:
        final_price = closes[-1] * (1.0 - slippage_pct)
        gross_pnl = (final_price - pos_entry_price) * pos_remaining_tokens
        exit_notional = final_price * pos_remaining_tokens
        exit_fee = exit_notional * fee_pct
        total_fees_paid += exit_fee
        net_pnl = gross_pnl - exit_fee
        realized_pnl_trade += net_pnl
        capital += net_pnl
        roe_pct = (realized_pnl_trade / margin_per_trade) * 100.0

        trades.append({
            "id": len(trades) + 1,
            "type": "LONG",
            "strategy": pos_strategy,
            "entry_time": pos_entry_time,
            "entry_date": datetime.fromtimestamp(pos_entry_time, timezone.utc).strftime("%d/%m/%Y %H:%M"),
            "entry_price": round(pos_entry_price, 4),
            "exit_time": times[-1],
            "exit_date": datetime.fromtimestamp(times[-1], timezone.utc).strftime("%d/%m/%Y %H:%M"),
            "exit_price": round(final_price, 4),
            "exit_reason": "BACKTEST_END",
            "exit_reason_label": "🏁 Fim do Teste",
            "pnl_usd": round(net_pnl, 2),
            "roe_pct": round(roe_pct, 2),
            "hold_bars": len(candles) - pos_entry_index,
            "ratchet_protected": ratchet_activated,
        })

    # Compute Summary Statistics
    total_trades = len(trades)
    winning_trades = [t for t in trades if t["pnl_usd"] > 0]
    losing_trades = [t for t in trades if t["pnl_usd"] <= 0]

    win_count = len(winning_trades)
    loss_count = len(losing_trades)
    win_rate = (win_count / total_trades * 100.0) if total_trades > 0 else 0.0

    gross_profit = sum(t["pnl_usd"] for t in winning_trades)
    gross_loss = abs(sum(t["pnl_usd"] for t in losing_trades))
    net_profit = capital - initial_capital
    net_profit_pct = (net_profit / initial_capital) * 100.0

    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (99.0 if gross_profit > 0 else 0.0)

    avg_win = (gross_profit / win_count) if win_count > 0 else 0.0
    avg_loss = (gross_loss / loss_count) if loss_count > 0 else 0.0
    payoff_ratio = (avg_win / avg_loss) if avg_loss > 0 else 0.0

    # Max consecutive streaks
    cur_win_streak = 0
    max_win_streak = 0
    cur_loss_streak = 0
    max_loss_streak = 0
    for t in trades:
        if t["pnl_usd"] > 0:
            cur_win_streak += 1
            cur_loss_streak = 0
            max_win_streak = max(max_win_streak, cur_win_streak)
        else:
            cur_loss_streak += 1
            cur_win_streak = 0
            max_loss_streak = max(max_loss_streak, cur_loss_streak)

    # Simplified Sharpe Ratio approximation
    pnls = [t["pnl_usd"] for t in trades]
    if len(pnls) >= 5:
        mean_pnl = sum(pnls) / len(pnls)
        std_pnl = math.sqrt(sum((x - mean_pnl) ** 2 for x in pnls) / len(pnls))
        sharpe = (mean_pnl / std_pnl * math.sqrt(365)) if std_pnl > 0 else 0.0
    else:
        sharpe = 0.0

    # Gertrude Approval Gate Classification (from AGENTS.md)
    if profit_factor >= 1.30 and max_dd_pct <= 30.0 and total_trades >= 15 and win_rate >= 45.0:
        gertrude_verdict = "APROVADO PARA INCUBAÇÃO"
        gertrude_status = "approved"
        gertrude_badge = "🟢 APROVADO (Pronto para o Sniper)"
    elif profit_factor >= 1.05 and max_dd_pct <= 40.0 and total_trades >= 8:
        gertrude_verdict = "ESTACIONADO (Promissor mas Inconclusivo)"
        gertrude_status = "parked"
        gertrude_badge = "🟡 ESTACIONADO (Observação)"
    else:
        gertrude_verdict = "REJEITADO (Risco Elevado ou Baixa Assimetria)"
        gertrude_status = "rejected"
        gertrude_badge = "🔴 REJEITADO (Não Ativar)"

    # Format Lightweight Charts friendly Candlesticks
    chart_candles = []
    for c in candles:
        chart_candles.append({
            "time": int(c["t"] / 1000),
            "open": float(c["o"]),
            "high": float(c["h"]),
            "low": float(c["l"]),
            "close": float(c["c"]),
            "volume": float(c["v"])
        })

    # Format Indicator Series for Lightweight Charts
    chart_ema9 = [{"time": times[idx], "value": round(ema9[idx], 4)} for idx in range(n)]
    chart_ema21 = [{"time": times[idx], "value": round(ema21[idx], 4)} for idx in range(n)]
    chart_ema200 = [{"time": times[idx], "value": round(ema200[idx], 4)} for idx in range(n)]
    chart_bbupper = [{"time": times[idx], "value": round(bb_upper[idx], 4)} for idx in range(n)]
    chart_bblower = [{"time": times[idx], "value": round(bb_lower[idx], 4)} for idx in range(n)]
    chart_rsi = [{"time": times[idx], "value": round(rsi[idx], 2)} for idx in range(n)]

    days_actual = round((times[-1] - times[0]) / 86400.0, 1) if n > 0 else 0

    return {
        "status": "ok",
        "symbol": coin,
        "strategy": strategy,
        "strategy_label": {
            "dual": "Dual-Engine (Pullback + Confluência)",
            "pullback": "Pullback Macro em Tendência",
            "confluence": "Confluência Breakout",
            "mean_reversion": "Mean Reversion (Bandas de Bollinger)"
        }.get(strategy, strategy),
        "days_actual": days_actual,
        "start_date": datetime.fromtimestamp(times[0], timezone.utc).strftime("%d/%m/%Y"),
        "end_date": datetime.fromtimestamp(times[-1], timezone.utc).strftime("%d/%m/%Y"),
        "candles_count": n,
        "summary": {
            "initial_capital": round(initial_capital, 2),
            "final_capital": round(capital, 2),
            "net_profit_usd": round(net_profit, 2),
            "net_profit_pct": round(net_profit_pct, 2),
            "profit_factor": round(profit_factor, 2),
            "win_rate_pct": round(win_rate, 1),
            "total_trades": total_trades,
            "winning_trades": win_count,
            "losing_trades": loss_count,
            "max_drawdown_pct": round(max_dd_pct, 2),
            "max_drawdown_usd": round(max_dd_usd, 2),
            "avg_win_usd": round(avg_win, 2),
            "avg_loss_usd": round(avg_loss, 2),
            "payoff_ratio": round(payoff_ratio, 2),
            "sharpe_ratio": round(sharpe, 2),
            "max_win_streak": max_win_streak,
            "max_loss_streak": max_loss_streak,
            "total_fees_paid_usd": round(total_fees_paid, 2),
            "gertrude_verdict": gertrude_verdict,
            "gertrude_status": gertrude_status,
            "gertrude_badge": gertrude_badge
        },
        "candles": chart_candles,
        "indicators": {
            "ema9": chart_ema9,
            "ema21": chart_ema21,
            "ema200": chart_ema200,
            "bb_upper": chart_bbupper,
            "bb_lower": chart_bblower,
            "rsi": chart_rsi
        },
        "markers": markers,
        "equity_curve": equity_curve,
        "trades": trades
    }


def run_backtest_pipeline(
    symbol: str = "SOL",
    days: int = 720,
    timeframe: str = "1d",
    strategy: str = "dual",
    initial_capital: float = 100.0,
    margin_per_trade: float = 15.0,
    leverage: int = 10
) -> dict:
    """End-to-end execution of a backtest pipeline for any Hyperliquid asset."""
    executor = HyperliquidExecutor()
    candles = fetch_historical_candles(executor, symbol, timeframe, days)
    if not candles:
        return {
            "status": "error",
            "message": f"Não foi possível obter candles para {symbol} no timeframe {timeframe}."
        }

    res = run_simulation(
        coin=symbol,
        candles=candles,
        strategy=strategy,
        initial_capital=initial_capital,
        margin_per_trade=margin_per_trade,
        leverage=leverage
    )
    return res


def main():
    parser = argparse.ArgumentParser(description="Botrade Hyperliquid 720d Backtest Engine")
    parser.add_argument("--symbol", type=str, default="SOL", help="Crypto symbol (e.g. SOL, BTC, KAITO)")
    parser.add_argument("--days", type=int, default=720, help="Lookback period in days (e.g. 720)")
    parser.add_argument("--timeframe", type=str, default="1d", choices=["1h", "2h", "4h", "1d"], help="Candle timeframe")
    parser.add_argument("--strategy", type=str, default="dual", choices=["dual", "pullback", "confluence", "mean_reversion"])
    parser.add_argument("--margin", type=float, default=15.0, help="Margin in USDC per trade")
    parser.add_argument("--leverage", type=int, default=10, help="Leverage multiplier")
    args = parser.parse_args()

    print(f"[*] Executando Backtest Quantitativo: {args.symbol} ({args.timeframe}) por {args.days} dias...")
    res = run_backtest_pipeline(
        symbol=args.symbol,
        days=args.days,
        timeframe=args.timeframe,
        strategy=args.strategy,
        margin_per_trade=args.margin,
        leverage=args.leverage
    )

    if res.get("status") == "error":
        print(f"[-] Erro: {res.get('message')}")
        sys.exit(1)

    s = res["summary"]
    print("\n" + "=" * 60)
    print(f"📊 RESULTADO DO BACKTEST: {res['symbol']} ({res['strategy_label']})")
    print(f"📅 Período Real: {res['start_date']} até {res['end_date']} ({res['days_actual']} dias)")
    print(f"🕯️ Total de Velas: {res['candles_count']} | Trades Executados: {s['total_trades']}")
    print("=" * 60)
    print(f"💰 Lucro Líquido: ${s['net_profit_usd']:.2f} ({s['net_profit_pct']:+.1f}%)")
    print(f"🎯 Fator de Lucro (PF): {s['profit_factor']:.2f}x")
    print(f"🏆 Taxa de Acerto (Win Rate): {s['win_rate_pct']:.1f}% ({s['winning_trades']} vitórias / {s['losing_trades']} derrotas)")
    print(f"📉 Max Drawdown: -{s['max_drawdown_pct']:.1f}% (-${s['max_drawdown_usd']:.2f})")
    print(f"⚖️ Payoff Ratio: {s['payoff_ratio']:.2f}x (Ganho Médio ${s['avg_win_usd']:.2f} / Perda Média ${s['avg_loss_usd']:.2f})")
    print(f"🛡️ Taxas Reais Pagas: ${s['total_fees_paid_usd']:.2f}")
    print(f"🏛️ Veredito de Gertrude: {s['gertrude_badge']}")
    print("=" * 60)


if __name__ == "__main__":
    main()
