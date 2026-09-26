#!/usr/bin/env python3
"""
Backtest H2 v2: Liquidez Sweep + Snapback com EMA200 Filter
BTCUSDT 1h 2023-2025
- detecção de falso breakout de range (sweep) + snapback reverso
- filtro EMA200 (long só abaixo da EMA, short só acima) — sem ADX (matou tudo)
- SL: nível violado - 1.5*ATR   TP: entry + 2.0*ATR (ou reversão do range)
- sizing: 7% do capital por risco unitário
- mark-to-market, equity curve, trades list
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
    # precompute EMA200
    df["ema200"] = df["close"].ewm(span=200, adjust=False).mean()
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

SYMBOLS = ["BTCUSDT"]
INTERVAL = "1h"
START = "2023-01-01"
END = datetime.datetime.now(datetime.timezone.utc)
start_ms = int(datetime.datetime(2023,1,1,tzinfo=datetime.timezone.utc).timestamp()*1000)
end_ms   = int(END.timestamp()*1000)

SWEEP_LEN = 20
CONFIRM_BARS = 3
SL_ATR_MULT = 1.5
TP_ATR_MULT = 2.0
ATR_LEN = 14
RISK_FRAC = 0.07
FEE = 0.001
LEVERAGE = 1.0
HORIZON_DAYS = 30
TRAILING_RETRACE = 0.40
# sweep params para diagnóstico
SL_SWEEP = [1.0, 1.25, 1.5, 2.0, 2.5, 3.0]
TP_SWEEP = [0.5, 0.75, 1.0, 1.5, 2.0, 2.5, 3.0]

frames = {}
for sym in SYMBOLS:
    print(f"Fetching {sym}...", flush=True)
    bars = fetch(sym, INTERVAL, start_ms, end_ms)
    if bars:
        frames[sym] = bars_to_frame(bars, sym)
        print(f"  → {len(frames[sym])} bars")
    else:
        print(f"  → FAIL")

for sym, df in frames.items():
    print(f"\n=== Backtest H2 v2 — {sym} 1h {START}→hoje ===")
    atr_s = atr(df, ATR_LEN)
    avg_atr = atr_s.rolling(SWEEP_LEN).mean()
    range_hi = donchian_high(df["high"], SWEEP_LEN)
    range_lo = donchian_low(df["low"], SWEEP_LEN)
    ema200 = df["ema200"]

    # signal detection (look-ahead free)
    nb_count = 0
    hb_count = 0
    long_sig = pd.Series(False, index=df.index)
    short_sig = pd.Series(False, index=df.index)
    for si in range(len(df)):
        rlo = range_lo.iloc[si]
        rhi = range_hi.iloc[si]
        if pd.isna(rlo) or pd.isna(rhi) or rlo <= 0 or rhi <= 0:
            continue
        low_broke = df["low"].iloc[si] < rlo
        high_broke = df["high"].iloc[si] > rhi
        if low_broke:
            look_end = min(si + CONFIRM_BARS + 1, len(df))
            if (df["close"].iloc[si:look_end] > rlo).any():
                for j in range(si, look_end):
                    if df["close"].iloc[j] > rlo:
                        long_sig.iloc[j] = True
                        nb_count += 1
                        break
        if high_broke:
            look_end = min(si + CONFIRM_BARS + 1, len(df))
            if (df["close"].iloc[si:look_end] < rhi).any():
                for j in range(si, look_end):
                    if df["close"].iloc[j] < rhi:
                        short_sig.iloc[j] = True
                        hb_count += 1
                        break

    # filters
    use_ema_filter = True
    if use_ema_filter:
        long_sig = long_sig & (df["close"] > ema200)
        short_sig = short_sig & (df["close"] < ema200)

    n_long = int(long_sig.sum())
    n_short = int(short_sig.sum())
    print(f"sweep low events: {(df['low'] < range_lo).sum()}, high events: {(df['high'] > range_hi).sum()}")
    print(f"snapback low→long raw: {nb_count}, high→short raw: {hb_count}")
    print(f"long signals: {n_long}, short signals: {n_short}")

    # backtest engine
    capital = 10000.0
    cash = capital
    pos = None
    trades = []
    eq_curve = []
    for i, (idx, row) in enumerate(df.iterrows()):
        if pos is not None:
            cp = row["close"]
            if pos["side"] == 1:
                unreal = (cp - pos["entry_price"]) * pos["units"] * LEVERAGE
            else:
                unreal = (pos["entry_price"] - cp) * pos["units"] * LEVERAGE
            pos["pnl"] = unreal
            # peak tracking
            pos["peak"] = max(pos["peak"], cp) if pos["side"]==1 else min(pos["peak"], cp)
            # SL / TP check
            sl_hit = tp_hit = False
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
            # trailing stop (retrace from peak)
            retrace = 0
            if pos["side"]==1 and pos["peak"] > pos["entry_price"]:
                retrace = (pos["peak"] - cp) / (pos["peak"] - pos["entry_price"])
            elif pos["side"]==-1 and pos["peak"] < pos["entry_price"]:
                retrace = (cp - pos["peak"]) / (pos["entry_price"] - pos["peak"])
            if retrace > TRAILING_RETRACE:
                sl_hit = True
            # time exit
            time_exit = (idx - pos["open_date"]).days >= HORIZON_DAYS
            if sl_hit or tp_hit or time_exit:
                fee_amt = cp * pos["units"] * FEE * LEVERAGE
                pnl_real = unreal - fee_amt
                cash += pnl_real
                reason = "SL" if sl_hit else ("TP" if tp_hit else "TIME")
                trades.append({
                    "entry": pos["open_date"], "exit": idx,
                    "side": pos["side"], "entry_px": pos["entry_price"],
                    "exit_px": cp, "pnl": pnl_real, "pnl_pct": pnl_real/capital,
                    "reason": reason,
                    "sl": pos["sl_price"], "tp": pos["tp_price"]
                })
                eq_curve.append({"date": idx, "cash": cash, "total": cash})
                pos = None
                continue
            eq_curve.append({"date": idx, "cash": cash, "total": cash + unreal})
        else:
            if long_sig.iloc[i]:
                ep = row["close"]
                slp = range_lo.iloc[i] - atr_s.iloc[i] * SL_ATR_MULT
                tpp = ep + atr_s.iloc[i] * TP_ATR_MULT
                if pd.isna(slp) or pd.isna(tpp) or slp <= 0:
                    continue
                risk_per_unit = abs(ep - slp)
                if risk_per_unit == 0:
                    continue
                units = (cash * RISK_FRAC) / risk_per_unit / LEVERAGE
                pos = {"side":1, "entry_price":ep, "units":units, "open_date":idx,
                       "peak":ep, "pnl":0, "sl_price":slp, "tp_price":tpp}
                eq_curve.append({"date": idx, "cash": cash, "total": cash})
            elif short_sig.iloc[i]:
                ep = row["close"]
                slp = range_hi.iloc[i] + atr_s.iloc[i] * SL_ATR_MULT
                tpp = ep - atr_s.iloc[i] * TP_ATR_MULT
                if pd.isna(slp) or pd.isna(tpp) or slp <= 0:
                    continue
                risk_per_unit = abs(ep - slp)
                if risk_per_unit == 0:
                    continue
                units = (cash * RISK_FRAC) / risk_per_unit / LEVERAGE
                pos = {"side":-1, "entry_price":ep, "units":units, "open_date":idx,
                       "peak":ep, "pnl":0, "sl_price":slp, "tp_price":tpp}
                eq_curve.append({"date": idx, "cash": cash, "total": cash})
            else:
                eq_curve.append({"date": idx, "cash": cash, "total": cash})

    # close final position
    if pos is not None:
        cp = df.iloc[-1]["close"]
        fee_amt = cp * pos["units"] * FEE * LEVERAGE
        if pos["side"]==1:
            pnl_real = (cp - pos["entry_price"]) * pos["units"] * LEVERAGE - fee_amt
        else:
            pnl_real = (pos["entry_price"] - cp) * pos["units"] * LEVERAGE - fee_amt
        cash += pnl_real
        trades.append({"entry":pos["open_date"],"exit":df.index[-1],"side":pos["side"],
                       "entry_px":pos["entry_price"],"exit_px":cp,"pnl":pnl_real,
                       "pnl_pct":pnl_real/capital,"reason":"TIME"})
        eq_curve.append({"date":df.index[-1],"cash":cash,"total":cash})

    eq_df = pd.DataFrame(eq_curve).set_index("date")
    if len(eq_df) < 2:
        print("ERRO: curva vazia")
        continue

    net = eq_df["total"].iloc[-1]/10000 - 1
    peak_eq = eq_df["total"].cummax()
    dd_series = eq_df["total"]/peak_eq - 1
    max_dd = dd_series.min()
    eq_df["ret"] = eq_df["total"].pct_change()
    sharpe = eq_df["ret"].mean()/eq_df["ret"].std()*np.sqrt(252) if eq_df["ret"].std()>0 else 0
    wins = [t for t in trades if t["pnl"]>0]
    losses = [t for t in trades if t["pnl"]<=0]
    gains_sum = sum(t["pnl"] for t in wins)
    losses_sum = abs(sum(t["pnl"] for t in losses))
    pf = gains_sum/losses_sum if losses_sum > 0 else 0
    wr = len(wins)/len(trades)*100 if trades else 0
    avg_t = np.mean([t["pnl"] for t in trades]) if trades else 0

    print(f"\nResultados:")
    print(f"  net_profit_pct : {net*100:.2f}%")
    print(f"  max_drawdown   : {max_dd*100:.2f}%")
    print(f"  sharpe         : {sharpe:.3f}")
    print(f"  profit_factor  : {pf:.2f}")
    print(f"  win_rate       : {wr:.1f}%  ({len(wins)} wins / {len(losses)} losses)")
    print(f"  trades         : {len(trades)}")
    print(f"  avg_trade_pct  : {avg_t*100/10000:.4f}%  ({avg_t:.2f} USD)")
    print(f"  final_capital  : {cash:.2f} USD")

    # distribuição de razão de saída
    from collections import Counter
    reasons = Counter(t["reason"] for t in trades)
    print(f"  saídas por motivo: {dict(reasons)}")

    # PnL por trade (top 10)
    trades_sorted = sorted(trades, key=lambda t: t["pnl"], reverse=True)
    print(f"\nTop 10 trades (por PnL):")
    for t in trades_sorted[:10]:
        print(f"  {t['side']:+d} {t['entry'].date()}→{t['exit'].date()}  entry={t['entry_px']:.2f} exit={t['exit_px']:.2f}  PnL={t['pnl']:.2f} USD ({t['pnl_pct']*100:.3f}%)  {t['reason']}")

    print(f"\nPiores 5 trades:")
    for t in trades_sorted[-5:]:
        print(f"  {t['side']:+d} {t['entry'].date()}→{t['exit'].date()}  entry={t['entry_px']:.2f} exit={t['exit_px']:.2f}  PnL={t['pnl']:.2f} USD ({t['pnl_pct']*100:.3f}%)  {t['reason']}")

    # long/short separado
    long_trades = [t for t in trades if t["side"]==1]
    short_trades = [t for t in trades if t["side"]==-1]
    if long_trades:
        l_wins = [t for t in long_trades if t["pnl"]>0]
        l_losses = [t for t in long_trades if t["pnl"]<=0]
        l_pf = sum(t["pnl"] for t in l_wins)/abs(sum(t["pnl"] for t in l_losses)) if l_losses and sum(t["pnl"] for t in l_losses)!=0 else 0
        l_wr = len(l_wins)/len(long_trades)*100 if long_trades else 0
        print(f"\nLONG separado: trades={len(long_trades)} pf={l_pf:.2f} wr={l_wr:.1f}%")
    if short_trades:
        s_wins = [t for t in short_trades if t["pnl"]>0]
        s_losses = [t for t in short_trades if t["pnl"]<=0]
        s_pf = sum(t["pnl"] for t in s_wins)/abs(sum(t["pnl"] for t in s_losses)) if s_losses and sum(t["pnl"] for t in s_losses)!=0 else 0
        s_wr = len(s_wins)/len(short_trades)*100 if short_trades else 0
        print(f"SHORT separado: trades={len(short_trades)} pf={s_pf:.2f} wr={s_wr:.1f}%")

    out = {
        "symbol": sym,
        "interval": INTERVAL,
        "start": START,
        "end": END.isoformat(),
        "bars": len(df),
        "sweep_low_events": int((df["low"] < range_lo).sum()),
        "sweep_high_events": int((df["high"] > range_hi).sum()),
        "snapback_low_to_long": nb_count,
        "snapback_high_to_short": hb_count,
        "long_signals": n_long,
        "short_signals": n_short,
        "bt_net_pct": round(net*100,2),
        "bt_max_dd_pct": round(max_dd*100,2),
        "bt_sharpe": round(sharpe,3),
        "bt_pf": round(pf,2),
        "bt_wr_pct": round(wr,2),
        "bt_trades": len(trades),
        "bt_wins": len(wins),
        "bt_losses": len(losses),
        "bt_avg_trade_pct": round(avg_t*100/10000,4),
        "bt_final_capital": round(cash,2),
        "bt_long_trades": len(long_trades) if long_trades else 0,
        "bt_short_trades": len(short_trades) if short_trades else 0,
        "bt_long_pf": round(l_pf,2) if long_trades else 0,
        "bt_short_pf": round(s_pf,2) if short_trades else 0,
    }

    tmpdir = os.path.join(os.environ.get("LOCALAPPDATA", "C:/Users/seares/AppData/Local"), "Temp")
    os.makedirs(tmpdir, exist_ok=True)
    with open(os.path.join(tmpdir, "bt_h2_v2_btc.json"), "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\nSalvo {os.path.join(tmpdir, 'bt_h2_v2_btc.json')}")

    # === SWEEP PARAMS: avaliar multiple SL/TP combos ===
    print("\n\n=== SWEEP: Avaliando combinações SL/TP ===")
    results_sweep = []
    for sl_mult in SL_SWEEP:
        for tp_mult in TP_SWEEP:
            if tp_mult <= 0 or sl_mult <= 0:
                continue
            # re-executar backtest com estes parâmetros
            cash_s = capital
            pos_s = None
            trades_s = []
            for i, (idx, row) in enumerate(df.iterrows()):
                if pos_s is not None:
                    cp = row["close"]
                    if pos_s["side"] == 1:
                        unreal = (cp - pos_s["entry_price"]) * pos_s["units"] * LEVERAGE
                    else:
                        unreal = (pos_s["entry_price"] - cp) * pos_s["units"] * LEVERAGE
                    pos_s["pnl"] = unreal
                    pos_s["peak"] = max(pos_s["peak"], cp) if pos_s["side"]==1 else min(pos_s["peak"], cp)
                    sl_hit = tp_hit = False
                    if pos_s["side"]==1:
                        if cp <= pos_s["sl_price"]:
                            sl_hit = True
                        if cp >= pos_s["tp_price"]:
                            tp_hit = True
                    else:
                        if cp >= pos_s["sl_price"]:
                            sl_hit = True
                        if cp <= pos_s["tp_price"]:
                            tp_hit = True
                    retrace = 0
                    if pos_s["side"]==1 and pos_s["peak"] > pos_s["entry_price"]:
                        retrace = (pos_s["peak"] - cp) / (pos_s["peak"] - pos_s["entry_price"])
                    elif pos_s["side"]==-1 and pos_s["peak"] < pos_s["entry_price"]:
                        retrace = (cp - pos_s["peak"]) / (pos_s["entry_price"] - pos_s["peak"])
                    if retrace > TRAILING_RETRACE:
                        sl_hit = True
                    time_exit = (idx - pos_s["open_date"]).days >= HORIZON_DAYS
                    if sl_hit or tp_hit or time_exit:
                        fee_amt = cp * pos_s["units"] * FEE * LEVERAGE
                        cash_s += unreal - fee_amt
                        trades_s.append({"reason": "SL" if sl_hit else ("TP" if tp_hit else "TIME"),
                                          "pnl": unreal - fee_amt})
                        pos_s = None
                        continue
                else:
                    if long_sig.iloc[i]:
                        ep = row["close"]
                        slp = range_lo.iloc[i] - atr_s.iloc[i] * sl_mult
                        tpp = ep + atr_s.iloc[i] * tp_mult
                        if pd.isna(slp) or pd.isna(tpp) or slp <= 0:
                            continue
                        risk_per_unit = abs(ep - slp)
                        if risk_per_unit == 0:
                            continue
                        units = (cash_s * RISK_FRAC) / risk_per_unit / LEVERAGE
                        pos_s = {"side":1, "entry_price":ep, "units":units, "open_date":idx,
                                 "peak":ep, "sl_price":slp, "tp_price":tpp}
                    elif short_sig.iloc[i]:
                        ep = row["close"]
                        slp = range_hi.iloc[i] + atr_s.iloc[i] * sl_mult
                        tpp = ep - atr_s.iloc[i] * tp_mult
                        if pd.isna(slp) or pd.isna(tpp) or slp <= 0:
                            continue
                        risk_per_unit = abs(ep - slp)
                        if risk_per_unit == 0:
                            continue
                        units = (cash_s * RISK_FRAC) / risk_per_unit / LEVERAGE
                        pos_s = {"side":-1, "entry_price":ep, "units":units, "open_date":idx,
                                 "peak":ep, "sl_price":slp, "tp_price":tpp}
            # finalizar posição
            if pos_s is not None:
                cp = df.iloc[-1]["close"]
                fee_amt = cp * pos_s["units"] * FEE * LEVERAGE
                if pos_s["side"]==1:
                    unreal = (cp - pos_s["entry_price"]) * pos_s["units"] * LEVERAGE
                else:
                    unreal = (pos_s["entry_price"] - cp) * pos_s["units"] * LEVERAGE
                cash_s += unreal - fee_amt
                trades_s.append({"reason":"TIME", "pnl": unreal - fee_amt})
            net_s = cash_s/10000 - 1
            wins_s = [t for t in trades_s if t["pnl"]>0]
            losses_s = [t for t in trades_s if t["pnl"]<=0]
            gains_sum_s = sum(t["pnl"] for t in wins_s)
            losses_sum_s = abs(sum(t["pnl"] for t in losses_s))
            pf_s = gains_sum_s/losses_sum_s if losses_sum_s > 0 else 0
            wr_s = len(wins_s)/len(trades_s)*100 if trades_s else 0
            results_sweep.append({
                "sl_mult": sl_mult, "tp_mult": tp_mult,
                "net_pct": round(net_s*100,2),
                "pf": round(pf_s,2),
                "wr_pct": round(wr_s,1),
                "trades": len(trades_s),
                "wins": len(wins_s), "losses": len(losses_s),
            })
    # ordenar por net_pct descendente
    results_sweep.sort(key=lambda x: x["net_pct"], reverse=True)
    print(f"\nTop 10 combinações SL/TP:")
    for r in results_sweep[:10]:
        print(f"  SL={r['sl_mult']}x ATR, TP={r['tp_mult']}x ATR: net={r['net_pct']:.2f}%  pf={r['pf']:.2f}  wr={r['wr_pct']:.1f}%  trades={r['trades']}  wins={r['wins']} losses={r['losses']}")
    print(f"\nPiores 5 combinações:")
    for r in results_sweep[-5:]:
        print(f"  SL={r['sl_mult']}x ATR, TP={r['tp_mult']}x ATR: net={r['net_pct']:.2f}%  pf={r['pf']:.2f}  wr={r['wr_pct']:.1f}%  trades={r['trades']}  wins={r['wins']} losses={r['losses']}")
    print(f"\nA melhor combinação (por net): SL={results_sweep[0]['sl_mult']}x, TP={results_sweep[0]['tp_mult']}x  net={results_sweep[0]['net_pct']:.2f}%  pf={results_sweep[0]['pf']:.2f}  wr={results_sweep[0]['wr_pct']:.1f}%  trades={results_sweep[0]['trades']}")

    # se a melhor combinação tiver PF < 1.0, a linha não tem edge
    best = results_sweep[0]
    if best["pf"] < 1.0:
        print(f"\n*** CONCLUSÃO: Melhor SL/TP ainda tem PF={best['pf']:.2f} < 1.0 → sem edge neste símbolo/TF ***")
    else:
        print(f"\n*** ATENÇÃO: PF={best['pf']:.2f} >= 1.0 com SL={best['sl_mult']}x, TP={best['tp_mult']}x — requer validação em mais símbolos ***")

    # salvar resultados do sweep
    with open(os.path.join(tmpdir, "bt_h2_v2_sweep.json"), "w") as f:
        json.dump(results_sweep, f, ensure_ascii=False, indent=2)
    print(f"\nSalvo {os.path.join(tmpdir, 'bt_h2_v2_sweep.json')}")
