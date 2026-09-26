#!/usr/bin/env python3
"""
Diagnóstico rápido: H2 — sinais + filtros, apenas BTCUSDT, 1h, 2023-2025
"""
import json, os, sys, datetime, time
import numpy as np
import pandas as pd

BASE = "https://api.binance.com/api/v3/klines"
def fetch(symbol, interval, start_ms, end_ms):
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
            time.sleep(0.2)
        except Exception as e:
            print(f"fetch interrupt: {e}")
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
    # calculate 200 EMA for trend filter
    df["ema200"] = df["close"].ewm(span=200, adjust=False).mean()
    df["mid_range"] = (donchian_high(df["high"], SWEEP_LEN) + donchian_low(df["low"], SWEEP_LEN)) / 2
    return df

def donchian_high(series, n):
    return series.shift(1).rolling(n).max()

def donchian_low(series, n):
    return series.shift(1).rolling(n).min()

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
    high, low, close = df["high"], df["low"], df["close"]
    plus_dm = np.where((high - high.shift(1)) > (low.shift(1) - low),
                       (high - high.shift(1)), 0)
    minus_dm = np.where((low.shift(1) - low) > (high - high.shift(1)),
                        (low.shift(1) - low), 0)
    tr = pd.concat([(high-low),
                    (high-close.shift(1)).abs(),
                    (low-close.shift(1)).abs()], axis=1).max(axis=1)
    atr_s = tr.rolling(n).mean()
    ep = pd.Series(plus_dm).rolling(n).sum() / atr_s
    em = pd.Series(minus_dm).rolling(n).sum() / atr_s
    plus_di = 100 * ep / (1 + ep + em).replace(0, np.nan)
    minus_di = 100 * em / (1 + ep + em).replace(0, np.nan)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    return dx.rolling(n).mean()

SYMBOLS = ["BTCUSDT"]
INTERVAL = "1h"
START = "2023-01-01"
END = datetime.datetime.now(datetime.timezone.utc)
start_ms = int(datetime.datetime(2023,1,1,tzinfo=datetime.timezone.utc).timestamp()*1000)
end_ms   = int(END.timestamp()*1000)

SWEEP_LEN = 20
CONFIRM_BARS = 3
SL_ATR_MULT = 2.0
TP_ATR_MULT = 1.0
VOL_K = 0.8
ATR_LEN = 14
ADX_THRESH = 999      # desativado: não filtrar por ADX neste diagnóstico raw

frames = {}
for sym in SYMBOLS:
    print(f"Fetching {sym}...", flush=True)
    bars = fetch(sym, INTERVAL, start_ms, end_ms)
    if bars:
        frames[sym] = bars_to_frame(bars, sym)
        print(f"  → {len(frames[sym])} bars")
    else:
        print("  → FAIL")

for sym, df in frames.items():
    print(f"\n=== Diagnóstico + mini-backtest {sym} ===")
    atr_s = atr(df, ATR_LEN)
    avg_atr = atr_s.rolling(SWEEP_LEN).mean()
    range_hi = donchian_high(df["high"], SWEEP_LEN)
    range_lo = donchian_low(df["low"], SWEEP_LEN)
    adx_s = adx(df, 14)
    vol_ok = atr_s < avg_atr * (1 + VOL_K)
    adx_ok = adx_s < ADX_THRESH

    # === SINALS RAW ===
    low_sweep = df["low"] < range_lo
    high_sweep = df["high"] > range_hi

    nb_count = 0
    hb_count = 0
    long_sig_raw = pd.Series(False, index=df.index)
    short_sig_raw = pd.Series(False, index=df.index)
    for si in range(len(df)):
        rlo = range_lo.iloc[si]
        rhi = range_hi.iloc[si]
        if pd.isna(rlo) or rlo <= 0:
            pass
        else:
            if low_sweep.iloc[si]:
                look_end = min(si + CONFIRM_BARS + 1, len(df))
                if (df["close"].iloc[si:look_end] > rlo).any():
                    for j in range(si, look_end):
                        if df["close"].iloc[j] > rlo:
                            long_sig_raw.iloc[j] = True
                            nb_count += 1
                            break
            if high_sweep.iloc[si]:
                look_end = min(si + CONFIRM_BARS + 1, len(df))
                if (df["close"].iloc[si:look_end] < rhi).any():
                    for j in range(si, look_end):
                        if df["close"].iloc[j] < rhi:
                            short_sig_raw.iloc[j] = True
                            hb_count += 1
                            break

    total_low_sweep = int(low_sweep.sum())
    total_high_sweep = int(high_sweep.sum())
    raw_long_sig = int(long_sig_raw.sum())
    raw_short_sig = int(short_sig_raw.sum())

    print(f"low  sweeps : {total_low_sweep}")
    print(f"high sweeps : {total_high_sweep}")
    print(f"snapback low→long raw   : {nb_count}  (sinais brutos: {raw_long_sig})")
    print(f"snapback high→short raw : {hb_count}  (sinais brutos: {raw_short_sig})")

    vol_ok_count = int(vol_ok.sum())
    adx_ok_count = int(adx_ok.sum())
    vol_and_adx = int((vol_ok & adx_ok).sum())
    long_after_filters = int((long_sig_raw & vol_ok & adx_ok).sum())
    short_after_filters = int((short_sig_raw & vol_ok & adx_ok).sum())

    print(f"vol_ok: {vol_ok_count}/{len(df)}, adx_ok: {adx_ok_count}/{len(df)}, vol+adx: {vol_and_adx}")
    print(f"long after filters: {long_after_filters}, short: {short_after_filters}")

    long_drop_vol = int((long_sig_raw & ~vol_ok).sum())
    long_drop_adx = int((long_sig_raw & vol_ok & ~adx_ok).sum())
    short_drop_vol = int((short_sig_raw & ~vol_ok).sum())
    short_drop_adx = int((short_sig_raw & vol_ok & ~adx_ok).sum())
    print(f"long matado por vol: {long_drop_vol}, adx: {long_drop_adx}")
    print(f"short matado por vol: {short_drop_vol}, adx: {short_drop_adx}")

    print(f"ATR médio (14): {atr_s.mean():.4f}, Avg ATR ({SWEEP_LEN}): {avg_atr.mean():.4f}, Preço médio: {df['close'].mean():.2f}, range% médio: {(range_hi.mean()-range_lo.mean())/df['close'].mean()*100:.2f}%")

    # === MINI BACKTEST (sem filtros de regime, só sinal + SL/TP) ===
    print("\n--- Mini-backtest: núcleo sinal + SL/TP (sem filtros) ---")
    capital = 10000.0
    fee = 0.001
    lev = 1.0
    cash = capital
    pos = None
    trades = []
    equity_curve = []
    for i, (idx, row) in enumerate(df.iterrows()):
        if pos is not None:
            cp = row["close"]
            if pos["side"] == 1:
                unreal = (cp - pos["entry_price"]) * pos["units"] * lev
            else:
                unreal = (pos["entry_price"] - cp) * pos["units"] * lev
            pos["pnl"] = unreal
            pos["peak"] = max(pos["peak"], cp) if pos["side"]==1 else min(pos["peak"], cp)
            sl_hit = False
            tp_hit = False
            if pos["side"]==1:
                if cp <= pos["sl_price"]:
                    sl_hit = True
                if cp >= pos["tp_price"]:
                    tp_hit = True
            else:
                if cp >= pos["sl_price"]:
                    sl_hit = True
                if cp <= pos["tp_price"]:
                    tp_hit = True
            retrace = 0
            if pos["side"]==1 and pos["peak"] > pos["entry_price"]:
                retrace = (pos["peak"] - cp) / (pos["peak"] - pos["entry_price"])
            elif pos["side"]==-1 and pos["peak"] < pos["entry_price"]:
                retrace = (cp - pos["peak"]) / (pos["entry_price"] - pos["peak"])
            if retrace > 0.40:
                sl_hit = True
            if sl_hit or tp_hit or (idx - pos["open_date"]).days >= 30:
                fee_amt = cp * pos["units"] * fee * lev
                if pos["side"]==1:
                    pnl_real = unreal - fee_amt
                else:
                    pnl_real = unreal - fee_amt
                cash += pnl_real
                trades.append({
                    "entry": pos["open_date"], "exit": idx,
                    "side": pos["side"], "entry_px": pos["entry_price"],
                    "exit_px": cp, "pnl": pnl_real, "pnl_pct": pnl_real/capital,
                    "reason": "SL" if sl_hit else ("TP" if tp_hit else "TIME")
                })
                equity_curve.append({"date": idx, "cash": cash, "total": cash})
                pos = None
                continue
            equity_curve.append({"date": idx, "cash": cash, "total": cash + unreal})
        else:
            if long_sig_raw.iloc[i]:
                ep = row["close"]
                slp = range_lo.iloc[i] - atr_s.iloc[i] * SL_ATR_MULT
                tpp = ep + atr_s.iloc[i] * TP_ATR_MULT
                if pd.isna(slp) or pd.isna(tpp): continue
                risk_per_unit = abs(ep - slp)
                if risk_per_unit == 0: continue
                units = (cash * 0.07) / risk_per_unit / lev
                pos = {"side":1, "entry_price":ep, "units":units, "open_date":idx,
                       "peak":ep, "pnl":0, "sl_price":slp, "tp_price":tpp}
                equity_curve.append({"date": idx, "cash": cash, "total": cash})
            elif short_sig_raw.iloc[i]:
                ep = row["close"]
                slp = range_hi.iloc[i] + atr_s.iloc[i] * SL_ATR_MULT
                tpp = ep - atr_s.iloc[i] * TP_ATR_MULT
                if pd.isna(slp) or pd.isna(tpp): continue
                risk_per_unit = abs(ep - slp)
                if risk_per_unit == 0: continue
                units = (cash * 0.07) / risk_per_unit / lev
                pos = {"side":-1, "entry_price":ep, "units":units, "open_date":idx,
                       "peak":ep, "pnl":0, "sl_price":slp, "tp_price":tpp}
                equity_curve.append({"date": idx, "cash": cash, "total": cash})
            else:
                equity_curve.append({"date": idx, "cash": cash, "total": cash})

    if pos is not None:
        last = df.iloc[-1]
        cp = last["close"]
        fee_amt = cp * pos["units"] * fee * lev
        if pos["side"]==1:
            pnl_real = (cp - pos["entry_price"]) * pos["units"] * lev - fee_amt
        else:
            pnl_real = (pos["entry_price"] - cp) * pos["units"] * lev - fee_amt
        cash += pnl_real
        trades.append({"entry":pos["open_date"],"exit":df.index[-1],"side":pos["side"],
                       "entry_px":pos["entry_price"],"exit_px":cp,"pnl":pnl_real,
                       "pnl_pct":pnl_real/capital,"reason":"TIME"})
        equity_curve.append({"date":df.index[-1],"cash":cash,"total":cash})

    eq_df = pd.DataFrame(equity_curve).set_index("date")
    net = eq_df["total"].iloc[-1]/10000 - 1
    peak_eq = eq_df["total"].cummax()
    dd_series = eq_df["total"]/peak_eq - 1
    max_dd = dd_series.min()
    eq_df["ret"] = eq_df["total"].pct_change()
    sharpe = eq_df["ret"].mean()/eq_df["ret"].std()*np.sqrt(252) if eq_df["ret"].std()>0 else 0
    wins = [t for t in trades if t["pnl"]>0]
    losses = [t for t in trades if t["pnl"]<=0]
    pf = (sum(t["pnl"] for t in wins)/abs(sum(t["pnl"] for t in losses))) if wins and losses and sum(t["pnl"] for t in losses)!=0 else 0
    wr = len(wins)/len(trades)*100 if trades else 0
    avg_t = np.mean([t["pnl"] for t in trades]) if trades else 0

    print(f"  net_profit_pct : {net*100:.2f}%")
    print(f"  max_drawdown   : {max_dd*100:.2f}%")
    print(f"  sharpe         : {sharpe:.3f}")
    print(f"  profit_factor  : {pf:.2f}")
    print(f"  win_rate       : {wr:.1f}%")
    print(f"  trades         : {len(trades)} (wins={len(wins)}, losses={len(losses)})")
    print(f"  avg_trade      : {avg_t*100/10000:.4f}%")

    out = {
        "symbol": sym, "interval": INTERVAL, "start": START, "bars": len(df),
        "low_sweep_events": total_low_sweep, "high_sweep_events": total_high_sweep,
        "snapback_low_to_long_raw": nb_count, "snapback_high_to_short_raw": hb_count,
        "raw_long_signals": raw_long_sig, "raw_short_signals": raw_short_sig,
        "vol_ok_count": vol_ok_count, "adx_ok_count": adx_ok_count,
        "vol_and_adx_count": vol_and_adx,
        "long_entries_after_filters": long_after_filters,
        "short_entries_after_filters": short_after_filters,
        "long_killed_by_vol": long_drop_vol, "long_killed_by_adx": long_drop_adx,
        "short_killed_by_vol": short_drop_vol, "short_killed_by_adx": short_drop_adx,
        "atr_mean": round(atr_s.mean(),4), "avg_atr_mean": round(avg_atr.mean(),4),
        "price_mean": round(df["close"].mean(),2),
        "range_pct_mean": round((range_hi.mean()-range_lo.mean())/df["close"].mean()*100,2),
        # mini-backtest sem filtros
        "bt_net_pct": round(net*100,2),
        "bt_max_dd_pct": round(max_dd*100,2),
        "bt_sharpe": round(sharpe,3),
        "bt_pf": round(pf,2),
        "bt_wr_pct": round(wr,2),
        "bt_trades": len(trades),
        "bt_wins": len(wins), "bt_losses": len(losses),
    }
    tmpdir = os.path.join(os.environ.get("LOCALAPPDATA", "C:/Users/seares/AppData/Local"), "Temp")
    os.makedirs(tmpdir, exist_ok=True)
    with open(os.path.join(tmpdir, "diag_btc.json"), "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\nSalvo {os.path.join(tmpdir, 'diag_btc.json')}")
