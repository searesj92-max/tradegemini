#!/usr/bin/env python3
"""
Backtest local: H2 — Liquidez Sweep + Snapback com Filtro de Volatilidade
Fonte: dados OHLCV Binance públicos (BTC, ETH, SOL, XRP, DOGE)
Calendarizo: 2023-01-01 até hoje.
"""

import json, os, sys, datetime, time
from pathlib import Path

import numpy as np
import pandas as pd

# ---------- fetch Binance OHLCV ----------
BASE = "https://api.binance.com/api/v3/klines"
def fetch(symbol: str, interval: str, start_ms: int, end_ms: int):
    bars = []
    limit = 1000
    while start_ms < end_ms:
        url = f"{BASE}?symbol={symbol}&interval={interval}&startTime={start_ms}&endTime={end_ms}&limit={limit}"
        try:
            import urllib.request
            req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                chunk = json.loads(r.read())
            if not chunk:
                break
            bars.extend(chunk)
            start_ms = chunk[-1][0] + 1
            time.sleep(0.3)  # polite
        except Exception as e:
            print(f"fetch interrupt for {symbol}: {e}")
            break
    return bars

def bars_to_frame(bars, symbol):
    df = pd.DataFrame(bars, columns=[
        "openTime","open","high","low","close","volume",
        "closeTime","quoteVol","trades","takerBuyBase","takerBuyQuote","ignore"
    ])
    df = df[["openTime","open","high","low","close","volume"]].astype(float)
    df["openTime"] = pd.to_datetime(df["openTime"], unit="ms", utc=True)
    df = df.rename(columns={
        "openTime":"date", "open":"open", "high":"high",
        "low":"low", "close":"close", "volume":"volume"
    }).set_index("date").sort_index()
    df["symbol"] = symbol
    return df

SYMBOLS = ["BTCUSDT","ETHUSDT","SOLUSDT","XRPUSDT","DOGEUSDT"]
INTERVAL = "1h"
START = "2023-01-01"
END = datetime.datetime.now(datetime.timezone.utc)

start_ms = int(datetime.datetime(2023,1,1,tzinfo=datetime.timezone.utc).timestamp()*1000)
end_ms   = int(END.timestamp()*1000)

frames = {}
for sym in SYMBOLS:
    print(f"Fetching {sym}...", flush=True)
    bars = fetch(sym, INTERVAL, start_ms, end_ms)
    if bars:
        frames[sym] = bars_to_frame(bars, sym)
        print(f"  → {len(frames[sym])} bars")
    else:
        print(f"  → FAIL (empty)")

if not frames:
    print("ERRO: nenhum dado obtido; abortando")
    sys.exit(1)

# ---------- indicators ----------
def donchian_high(series, n):
    return series.shift(1).rolling(n).max()

def donchian_low(series, n):
    return series.shift(1).rolling(n).min()

def ema(series, span):
    return series.ewm(span=span, adjust=False).mean()

def atr(df, n=14):
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat([
        (high - low),
        (high - prev_close).abs(),
        (low - prev_close).abs()
    ], axis=1).max(axis=1)
    return tr.rolling(n).mean()

def adx(df, n=14):
    plus_dm = np.where((df["high"] - df["high"].shift(1)) > (df["low"].shift(1) - df["low"]), 
                       (df["high"] - df["high"].shift(1)), 0)
    minus_dm = np.where((df["low"].shift(1) - df["low"]) > (df["high"] - df["high"].shift(1)),
                        (df["low"].shift(1) - df["low"]), 0)
    tr = pd.concat([(df["high"]-df["low"]),
                    (df["high"]-df["close"].shift(1)).abs(),
                    (df["low"]-df["close"].shift(1)).abs()], axis=1).max(axis=1)
    atr_s = tr.rolling(n).mean()
    plus_di = 100 * pd.Series(plus_dm).rolling(n).sum() / atr_s
    minus_di = 100 * pd.Series(minus_dm).rolling(n).sum() / atr_s
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    adx_s = dx.rolling(n).mean()
    return adx_s

# ---------- strategy params ----------
SWEEP_LEN = 20       # lookback do range
CONFIRM_BARS = 3     # janela de snapback
SL_ATR_MULT = 2.0    # SL = extremo violado + ATR
TP_ATR_MULT = 1.0    # TP = ATR em direção oposta
VOL_K = 0.8          # filtro de vol: ATR > avgAtR * (1+VOL_K) → veta
ATR_LEN = 14
ADX_THRESH = 25      # ADX > thresh → veta (tendência forte)

def compute_signals(df):
    """Compute long/short sweep+snapback signals with look-ahead-free logic."""
    atr_s = atr(df, ATR_LEN)
    avg_atr = atr_s.rolling(SWEEP_LEN).mean()
    range_hi = donchian_high(df["high"], SWEEP_LEN)
    range_lo = donchian_low(df["low"], SWEEP_LEN)
    adx_s = adx(df, 14)

    df = df.copy()
    df["atr"] = atr_s
    df["avg_atr"] = avg_atr
    df["range_hi"] = range_hi
    df["range_lo"] = range_lo
    df["adx"] = adx_s

    # Pre-compute: for each candle, did a low-sweep occur recently?
    low_sweep_bars = []   # list of (idx, low_value)
    high_sweep_bars = []  # list of (idx, high_value)
    for i in range(len(df)):
        if df["low"].iloc[i] < range_lo.iloc[i]:
            low_sweep_bars.append((i, df["low"].iloc[i]))
        if df["high"].iloc[i] > range_hi.iloc[i]:
            high_sweep_bars.append((i, df["high"].iloc[i]))

    long_sig = pd.Series(False, index=df.index)
    short_sig = pd.Series(False, index=df.index)

    # Long: low sweep occurred at bar `si`, check if within next CONFIRM_BARS
    # the close recovers above range_lo[si] (snapback). Then ON the first such
    # recovery candle we fire the signal.
    for si, low_val in low_sweep_bars:
        ri = range_lo.iloc[si]
        if pd.isna(ri) or ri <= 0:
            continue
        look_end = min(si + CONFIRM_BARS + 1, len(df))
        recovery_candle = None
        for j in range(si, look_end):
            if df["close"].iloc[j] > ri:
                recovery_candle = j
                break
        if recovery_candle is not None:
            long_sig.iloc[recovery_candle] = True

    # Short: high sweep, then close falls below range_hi within CONFIRM_BARS
    for si, high_val in high_sweep_bars:
        ri = range_hi.iloc[si]
        if pd.isna(ri) or ri <= 0:
            continue
        look_end = min(si + CONFIRM_BARS + 1, len(df))
        recovery_candle = None
        for j in range(si, look_end):
            if df["close"].iloc[j] < ri:
                recovery_candle = j
                break
        if recovery_candle is not None:
            short_sig.iloc[recovery_candle] = True

    # Filters
    df["vol_ok"] = atr_s < avg_atr * (1 + VOL_K)
    df["adx_ok"] = adx_s < ADX_THRESH

    df["long_entry"] = long_sig & df["vol_ok"] & df["adx_ok"]
    df["short_entry"] = short_sig & df["vol_ok"] & df["adx_ok"]

    # SL/TP levels (computed on signal candle, based on ATR)
    df["long_sl"] = range_lo - atr_s * SL_ATR_MULT
    df["short_sl"] = range_hi + atr_s * SL_ATR_MULT
    df["long_tp"] = df["close"] + atr_s * TP_ATR_MULT
    df["short_tp"] = df["close"] - atr_s * TP_ATR_MULT

    return df

# ---------- backtest engine (mark-to-market, honest) ----------
def backtest(df, capital=10000, fee=0.001, leverage=1.0):
    df = run_strategy(df)
    cash = capital
    position = None  # dict: side, entry_price, units, open_date, peak_price, pnl
    equity = []
    entry_dates = []
    
    for i, (idx, row) in enumerate(df.iterrows()):
        if position is not None:
            # mark to market
            current_price = row["close"]
            if position["side"] == 1:  # long
                unreal = (current_price - position["entry_price"]) * position["units"] * leverage
            else:
                unreal = (position["entry_price"] - current_price) * position["units"] * leverage
            position["pnl"] = unreal
            # atualizar peak
            if current_price > position["peak_price"]:
                position["peak_price"] = current_price
            # trailing stop: se retrace > 40% do peak
            if position["side"] == 1:
                retrace = (position["peak_price"] - current_price) / (position["peak_price"] - position["entry_price"]) if position["peak_price"] > position["entry_price"] else 0
                if retrace > 0.40:
                    # fechar
                    close_pnl = unreal - row["close"] * position["units"] * fee * leverage
                    cash += unreal - row["close"] * position["units"] * fee * leverage
                    entry_dates.append(idx)
                    equity.append({"date": idx, "cash": cash, "position_pnl": 0, "total": cash})
                    position = None
                    continue
            else:
                retrace = (position["peak_price"] - current_price) / (position["entry_price"] - position["peak_price"]) if position["peak_price"] < position["entry_price"] else 0
                # invertido: short peak = mínimo; retrace se subir
                if position["peak_price"] < position["entry_price"]:
                    retrace = (current_price - position["peak_price"]) / (position["entry_price"] - position["peak_price"])
                    if retrace > 0.40:
                        close_pnl = unreal - row["close"] * position["units"] * fee * leverage
                        cash += unreal - row["close"] * position["units"] * fee * leverage
                        equity.append({"date": idx, "cash": cash, "position_pnl": 0, "total": cash})
                        position = None
                        continue
            # time exit (horizon_days)
            if (idx - position["open_date"]).days >= 30:
                cash += unreal - row["close"] * position["units"] * fee * leverage
                equity.append({"date": idx, "cash": cash, "position_pnl": 0, "total": cash})
                position = None
                continue
            equity.append({"date": idx, "cash": cash, "position_pnl": unreal, "total": cash + unreal})
        else:
            # no position — check entry
            if row["long_entry"]:
                # calcular units via % do capital
                risk_frac = 0.07
                entry_px = row["close"]
                sl_px = row["long_sl"]
                if pd.isna(sl_px) or sl_px <= 0:
                    continue
                risk_per_unit = abs(entry_px - sl_px)
                if risk_per_unit == 0:
                    continue
                units = (cash * risk_frac) / risk_per_unit / leverage
                position = {
                    "side": 1,
                    "entry_price": entry_px,
                    "units": units,
                    "open_date": idx,
                    "peak_price": entry_px,
                    "pnl": 0
                }
                equity.append({"date": idx, "cash": cash, "position_pnl": 0, "total": cash})
            elif row["short_entry"]:
                entry_px = row["close"]
                sl_px = row["short_sl"]
                if pd.isna(sl_px) or sl_px <= 0:
                    continue
                risk_per_unit = abs(entry_px - sl_px)
                if risk_per_unit == 0:
                    continue
                units = (cash * risk_frac) / risk_per_unit / leverage
                position = {
                    "side": -1,
                    "entry_price": entry_px,
                    "units": units,
                    "open_date": idx,
                    "peak_price": entry_px,
                    "pnl": 0
                }
                equity.append({"date": idx, "cash": cash, "position_pnl": 0, "total": cash})
            else:
                equity.append({"date": idx, "cash": cash, "position_pnl": 0, "total": cash})
    
    # finalizar posição aberta no final
    if position is not None:
        last = df.iloc[-1]
        current_price = last["close"]
        if position["side"] == 1:
            unreal = (current_price - position["entry_price"]) * position["units"] * leverage
            cash += unreal - current_price * position["units"] * fee * leverage
        else:
            unreal = (position["entry_price"] - current_price) * position["units"] * leverage
            cash += unreal - current_price * position["units"] * fee * leverage
        equity.append({"date": df.index[-1], "cash": cash, "position_pnl": 0, "total": cash})
    
    eq = pd.DataFrame(equity).set_index("date")
    if eq.empty:
        return None
    return eq

# ---------- metrics ----------
def metrics(eq_curve, df, trades_list):
    if eq_curve is None or len(eq_curve) < 2:
        return {"error": "sem dados"}
    net = eq_curve["total"].iloc[-1] / 10000 - 1
    peak = eq_curve["total"].cummax()
    dd = (eq_curve["total"] / peak - 1)
    max_dd = dd.min()
    # Sharpe aproximado (retornos diários/seed)
    eq_curve["ret"] = eq_curve["total"].pct_change()
    sharpe = eq_curve["ret"].mean() / eq_curve["ret"].std() * np.sqrt(252) if eq_curve["ret"].std() > 0 else 0
    profit_factor = 0
    wins = [t for t in trades_list if t["pnl"] > 0]
    losses = [t for t in trades_list if t["pnl"] <= 0]
    if wins and losses:
        gross = sum(t["pnl"] for t in wins)
        gross_loss = abs(sum(t["pnl"] for t in losses))
        profit_factor = gross / gross_loss if gross_loss > 0 else 0
    win_rate = len(wins) / len(trades_list) if trades_list else 0
    avg_trade = np.mean([t["pnl"] for t in trades_list]) if trades_list else 0
    return {
        "net_profit_pct": round(net * 100, 2),
        "max_drawdown_pct": round(max_dd * 100, 2),
        "sharpe": round(sharpe, 3),
        "profit_factor": round(profit_factor, 2),
        "win_rate_pct": round(win_rate * 100, 2),
        "avg_trade_pct": round(avg_trade * 100 / 10000, 4),
        "trades": len(trades_list),
        "wins": len(wins),
        "losses": len(losses),
    }

# ---------- track trades ----------
def backtest_with_trades(df, capital=10000, fee=0.001, leverage=1.0):
    df = compute_signals(df)
    cash = capital
    position = None
    trades = []
    eq = []
    entry_idx = 0
    for i, (idx, row) in enumerate(df.iterrows()):
        if position is not None:
            current_price = row["close"]
            if position["side"] == 1:
                unreal = (current_price - position["entry_price"]) * position["units"] * leverage
            else:
                unreal = (position["entry_price"] - current_price) * position["units"] * leverage
            position["pnl"] = unreal
            position["peak_price"] = max(position["peak_price"], current_price) if position["side"]==1 else min(position["peak_price"], current_price)
            
            # SL/TP check (baseado nos levels do candle de entrada — simplificado: usar levels calculados na entrada)
            sl_hit = False
            tp_hit = False
            if position["side"] == 1:
                if current_price <= position["sl_price"]:
                    sl_hit = True
                if current_price >= position["tp_price"]:
                    tp_hit = True
            else:
                if current_price >= position["sl_price"]:
                    sl_hit = True
                if current_price <= position["tp_price"]:
                    tp_hit = True
            
            # trailing stop (retrace 40%)
            retrace = 0
            if position["side"]==1 and position["peak_price"] > position["entry_price"]:
                retrace = (position["peak_price"] - current_price) / (position["peak_price"] - position["entry_price"])
            elif position["side"]==-1 and position["peak_price"] < position["entry_price"]:
                retrace = (current_price - position["peak_price"]) / (position["entry_price"] - position["peak_price"])
            if retrace > 0.40:
                sl_hit = True
            
            if sl_hit or tp_hit or (idx - position["open_date"]).days >= 30:
                # fechar posição
                close_fee = current_price * position["units"] * fee * leverage
                if position["side"]==1:
                    pnl_real = unreal - close_fee
                else:
                    pnl_real = unreal - close_fee
                cash += pnl_real
                trades.append({
                    "entry_date": position["open_date"],
                    "exit_date": idx,
                    "side": position["side"],
                    "entry_price": position["entry_price"],
                    "exit_price": current_price,
                    "units": position["units"],
                    "pnl": pnl_real,
                    "pnl_pct": pnl_real / capital,
                    "reason": "SL" if sl_hit else ("TP" if tp_hit else "TIME"),
                    "holding_days": (idx - position["open_date"]).days
                })
                eq.append({"date": idx, "cash": cash, "total": cash})
                position = None
                continue
            
            eq.append({"date": idx, "cash": cash, "total": cash + unreal})
        else:
            if row["long_entry"]:
                entry_px = row["close"]
                sl_price = row["long_sl"]
                tp_price = row["long_tp"]
                if pd.isna(sl_price) or pd.isna(tp_price):
                    continue
                risk_frac = 0.07
                risk_per_unit = abs(entry_px - sl_price)
                if risk_per_unit == 0:
                    continue
                units = (cash * risk_frac) / risk_per_unit / leverage
                position = {
                    "side": 1,
                    "entry_price": entry_px,
                    "units": units,
                    "open_date": idx,
                    "peak_price": entry_px,
                    "pnl": 0,
                    "sl_price": sl_price,
                    "tp_price": tp_price
                }
                eq.append({"date": idx, "cash": cash, "total": cash})
            elif row["short_entry"]:
                entry_px = row["close"]
                sl_price = row["short_sl"]
                tp_price = row["short_tp"]
                if pd.isna(sl_price) or pd.isna(tp_price):
                    continue
                risk_frac = 0.07
                risk_per_unit = abs(entry_px - sl_price)
                if risk_per_unit == 0:
                    continue
                units = (cash * risk_frac) / risk_per_unit / leverage
                position = {
                    "side": -1,
                    "entry_price": entry_px,
                    "units": units,
                    "open_date": idx,
                    "peak_price": entry_px,
                    "pnl": 0,
                    "sl_price": sl_price,
                    "tp_price": tp_price
                }
                eq.append({"date": idx, "cash": cash, "total": cash})
            else:
                eq.append({"date": idx, "cash": cash, "total": cash})
    
    if position is not None:
        last = df.iloc[-1]
        current_price = last["close"]
        close_fee = current_price * position["units"] * fee * leverage
        if position["side"]==1:
            pnl_real = (current_price - position["entry_price"]) * position["units"] * leverage - close_fee
        else:
            pnl_real = (position["entry_price"] - current_price) * position["units"] * leverage - close_fee
        cash += pnl_real
        trades.append({
            "entry_date": position["open_date"],
            "exit_date": df.index[-1],
            "side": position["side"],
            "entry_price": position["entry_price"],
            "exit_price": current_price,
            "units": position["units"],
            "pnl": pnl_real,
            "pnl_pct": pnl_real / capital,
            "reason": "TIME",
            "holding_days": (df.index[-1] - position["open_date"]).days
        })
        eq.append({"date": df.index[-1], "cash": cash, "total": cash})
    
    eq_df = pd.DataFrame(eq).set_index("date")
    return eq_df, trades

# ---------- executar ----------
print("\n=== Backtest H2: Liquidez Sweep + Snapback ===\n")
results = {}
for sym, df in frames.items():
    print(f"Backtesting {sym}...", flush=True)
    eq_curve, trades = backtest_with_trades(df)
    met = metrics(eq_curve, df, trades)
    results[sym] = {"equity": eq_curve, "trades": trades, "metrics": met}
    print(json.dumps(met, indent=2, ensure_ascii=False))
    print()

# ---------- diagnóstico de sinais ----------
print("\n=== Diagnóstico de sinais (sem filtros vs com filtros) ===\n")
diag = []
for sym, df in frames.items():
    sig_df = compute_signals(df)
    total_sweeps_low = (df["low"] < donchian_low(df["low"], SWEEP_LEN)).sum()
    total_sweeps_high = (df["high"] > donchian_high(df["high"], SWEEP_LEN)).sum()
    total_long_sig = sig_df["long_entry"].sum()
    total_short_sig = sig_df["short_entry"].sum()
    # contar snapbacks brutos
    nb = 0
    hb = 0
    for si in range(len(df)):
        rlo = donchian_low(df["low"], SWEEP_LEN).iloc[si]
        rhi = donchian_high(df["high"], SWEEP_LEN).iloc[si]
        if pd.notna(rlo) and df["low"].iloc[si] < rlo:
            look_end = min(si + CONFIRM_BARS + 1, len(df))
            if (df["close"].iloc[si:look_end] > rlo).any():
                nb += 1
        if pd.notna(rhi) and df["high"].iloc[si] > rhi:
            look_end = min(si + CONFIRM_BARS + 1, len(df))
            if (df["close"].iloc[si:look_end] < rhi).any():
                hb += 1
    diag.append({
        "symbol": sym,
        "low_sweep_events": int(total_sweeps_low),
        "high_sweep_events": int(total_sweeps_high),
        "raw_snapback_long": nb,
        "raw_snapback_short": hb,
        "long_entry_after_filters": int(total_long_sig),
        "short_entry_after_filters": int(total_short_sig),
    })
    print(f"{sym}: sweeps low={total_sweeps_low}, high={total_sweeps_high}, snapbacks low→long raw={nb}, high→short raw={hb}, entradas long={total_long_sig}, short={total_short_sig}")

print("\nDiagnóstico JSON:")
print(json.dumps(diag, indent=2, ensure_ascii=False))

# ---------- consolidar ----------
# heatmap por símbolo
summary = []
for sym, r in results.items():
    m = r["metrics"]
    summary.append({
        "symbol": sym,
        "net_profit_pct": m.get("net_profit_pct", 0),
        "max_drawdown_pct": m.get("max_drawdown_pct", 0),
        "profit_factor": m.get("profit_factor", 0),
        "win_rate_pct": m.get("win_rate_pct", 0),
        "trades": m.get("trades", 0),
        "sharpe": m.get("sharpe", 0),
    })

print("=== Resumo por símbolo ===")
print(json.dumps(summary, indent=2, ensure_ascii=False))

# ---------- salv sar métricas ----------
out = {
    "symbol": summary,
    "trades_per_symbol": {sym: len(r["trades"]) for sym, r in results.items()},
    "total_trades": sum(len(r["trades"]) for r in results.values()),
}
import tempfile, os
tmpdir = os.path.join(os.environ.get("LOCALAPPDATA", "C:/Users/seares/AppData/Local"), "Temp")
os.makedirs(tmpdir, exist_ok=True)
with open(os.path.join(tmpdir, "bt_results.json"), "w") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print(f"\nSalvo {os.path.join(tmpdir, 'bt_results.json')}")
