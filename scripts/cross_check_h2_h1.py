#!/usr/bin/env python3
"""
Cross-symbol + alternativa: H2 em ETH/SOL + H1 (reversão de média) em BTC
- H2: mesmos sinais de sweep+snapback + EMA200 filter, SL/TP variados
- H1: reversão de média com distância normalizada por ATR
"""
import json, os, sys, datetime, time
import numpy as np
import pandas as pd
from collections import Counter

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

def run_h2(df, sl_mult=1.5, tp_mult=2.0, use_ema=True):
    SWEEP_LEN=20; CONFIRM_BARS=3; ATR_LEN=14; RISK=0.07; FEE=0.001; LEV=1.0; HORIZON=30; RETRACE=0.40
    atr_s = atr(df, ATR_LEN)
    avg_atr = atr_s.rolling(SWEEP_LEN).mean()
    range_hi = donchian_high(df["high"], SWEEP_LEN)
    range_lo = donchian_low(df["low"], SWEEP_LEN)
    ema200 = df["ema200"]
    nb=0; hb=0
    long_sig = pd.Series(False, index=df.index)
    short_sig = pd.Series(False, index=df.index)
    for si in range(len(df)):
        rlo = range_lo.iloc[si]; rhi = range_hi.iloc[si]
        if pd.isna(rlo) or pd.isna(rhi) or rlo<=0 or rhi<=0: continue
        if df["low"].iloc[si] < rlo:
            look_end = min(si+CONFIRM_BARS+1, len(df))
            if (df["close"].iloc[si:look_end] > rlo).any():
                for j in range(si, look_end):
                    if df["close"].iloc[j] > rlo:
                        long_sig.iloc[j] = True; nb+=1; break
        if df["high"].iloc[si] > rhi:
            look_end = min(si+CONFIRM_BARS+1, len(df))
            if (df["close"].iloc[si:look_end] < rhi).any():
                for j in range(si, look_end):
                    if df["close"].iloc[j] < rhi:
                        short_sig.iloc[j] = True; hb+=1; break
    if use_ema:
        long_sig = long_sig & (df["close"] > ema200)
        short_sig = short_sig & (df["close"] < ema200)

    cash=10000.0; pos=None; trades=[]
    for i,(idx,row) in enumerate(df.iterrows()):
        if pos:
            cp=row["close"]
            if pos["side"]==1: unreal=(cp-pos["entry_price"])*pos["units"]*LEV
            else: unreal=(pos["entry_price"]-cp)*pos["units"]*LEV
            pos["pnl"]=unreal
            pos["peak"]=max(pos["peak"],cp) if pos["side"]==1 else min(pos["peak"],cp)
            sl_hit=tp_hit=False
            if pos["side"]==1:
                if cp<=pos["sl"]: sl_hit=True
                if cp>=pos["tp"]: tp_hit=True
            else:
                if cp>=pos["sl"]: sl_hit=True
                if cp<=pos["tp"]: tp_hit=True
            retrace=0
            if pos["side"]==1 and pos["peak"]>pos["entry_price"]:
                retrace=(pos["peak"]-cp)/(pos["peak"]-pos["entry_price"])
            elif pos["side"]==-1 and pos["peak"]<pos["entry_price"]:
                retrace=(cp-pos["peak"])/(pos["entry_price"]-pos["peak"])
            if retrace>RETRACE: sl_hit=True
            if (idx-pos["open"])/pd.Timedelta(days=1) >= HORIZON: time_exit=True
            else: time_exit=False
            if sl_hit or tp_hit or time_exit:
                fee=cp*pos["units"]*FEE*LEV
                cash+=unreal-fee
                trades.append({"pnl":unreal-fee, "reason":"SL" if sl_hit else ("TP" if tp_hit else "TIME")})
                pos=None
                continue
        else:
            if long_sig.iloc[i]:
                ep=row["close"]; slp=range_lo.iloc[i]-atr_s.iloc[i]*sl_mult; tpp=ep+atr_s.iloc[i]*tp_mult
                if pd.isna(slp) or pd.isna(tpp) or slp<=0: continue
                rpu=abs(ep-slp)
                if rpu==0: continue
                units=(cash*RISK)/rpu/LEV
                pos={"side":1,"entry_price":ep,"units":units,"open":idx,"peak":ep,"sl":slp,"tp":tpp}
            elif short_sig.iloc[i]:
                ep=row["close"]; slp=range_hi.iloc[i]+atr_s.iloc[i]*sl_mult; tpp=ep-atr_s.iloc[i]*tp_mult
                if pd.isna(slp) or pd.isna(tpp) or slp<=0: continue
                rpu=abs(ep-slp)
                if rpu==0: continue
                units=(cash*RISK)/rpu/LEV
                pos={"side":-1,"entry_price":ep,"units":units,"open":idx,"peak":ep,"sl":slp,"tp":tpp}
    if pos:
        cp=df.iloc[-1]["close"]; fee=cp*pos["units"]*FEE*LEV
        if pos["side"]==1: unreal=(cp-pos["entry_price"])*pos["units"]*LEV
        else: unreal=(pos["entry_price"]-cp)*pos["units"]*LEV
        cash+=unreal-fee
        trades.append({"pnl":unreal-fee,"reason":"TIME"})
    net=cash/10000-1
    wins=[t for t in trades if t["pnl"]>0]; losses=[t for t in trades if t["pnl"]<=0]
    gs=sum(t["pnl"] for t in wins); ls=abs(sum(t["pnl"] for t in losses))
    pf=gs/ls if ls>0 else 0
    wr=len(wins)/len(trades)*100 if trades else 0
    return {"net":net*100,"pf":pf,"wr":wr,"trades":len(trades),"wins":len(wins),"losses":len(losses),
            "longs":len([t for t in trades if t.get("side",0)==1]),"shorts":len([t for t in trades if t.get("side",0)==-1]),
            "snap_low":nb,"snap_high":hb}

def run_h1(df, dist_mult=2.0, sl_mult=1.5, tp_mult=1.0):
    """H1: reversão de média com distância normalizada por ATR"""
    ATR_LEN=14; RISK=0.07; FEE=0.001; LEV=1.0; HORIZON=30; RETRACE=0.40
    atr_s = atr(df, ATR_LEN)
    ema20 = df["close"].ewm(span=20, adjust=False).mean()
    # distância da média em ATR
    dist_atr = (df["close"] - ema20).abs() / atr_s
    # candle de reversão: close cruza EMA para dentro (após estar fora)
    long_entry = (df["close"] < ema20) & (df["close"].shift(1) >= ema20.shift(1)) & (dist_atr > dist_mult)
    short_entry = (df["close"] > ema20) & (df["close"].shift(1) <= ema20.shift(1)) & (dist_atr > dist_mult)
    cash=10000.0; pos=None; trades=[]
    for i,(idx,row) in enumerate(df.iterrows()):
        if pos:
            cp=row["close"]
            if pos["side"]==1: unreal=(cp-pos["entry_price"])*pos["units"]*LEV
            else: unreal=(pos["entry_price"]-cp)*pos["units"]*LEV
            pos["pnl"]=unreal
            pos["peak"]=max(pos["peak"],cp) if pos["side"]==1 else min(pos["peak"],cp)
            sl_hit=tp_hit=False
            if pos["side"]==1:
                if cp<=pos["sl"]: sl_hit=True
                if cp>=pos["tp"]: tp_hit=True
            else:
                if cp>=pos["sl"]: sl_hit=True
                if cp<=pos["tp"]: tp_hit=True
            retrace=0
            if pos["side"]==1 and pos["peak"]>pos["entry_price"]:
                retrace=(pos["peak"]-cp)/(pos["peak"]-pos["entry_price"])
            elif pos["side"]==-1 and pos["peak"]<pos["entry_price"]:
                retrace=(cp-pos["peak"])/(pos["entry_price"]-pos["peak"])
            if retrace>RETRACE: sl_hit=True
            if (idx-pos["open"])/pd.Timedelta(days=1) >= HORIZON: time_exit=True
            else: time_exit=False
            if sl_hit or tp_hit or time_exit:
                fee=cp*pos["units"]*FEE*LEV
                cash+=unreal-fee
                trades.append({"pnl":unreal-fee,"reason":"SL" if sl_hit else ("TP" if tp_hit else "TIME")})
                pos=None
                continue
        else:
            if long_entry.iloc[i]:
                ep=row["close"]; slp=row["close"]-atr_s.iloc[i]*sl_mult; tpp=row["close"]+atr_s.iloc[i]*tp_mult
                rpu=atr_s.iloc[i]*sl_mult
                if rpu==0: continue
                units=(cash*RISK)/rpu/LEV
                pos={"side":1,"entry_price":ep,"units":units,"open":idx,"peak":ep,"sl":slp,"tp":tpp}
            elif short_entry.iloc[i]:
                ep=row["close"]; slp=row["close"]+atr_s.iloc[i]*sl_mult; tpp=row["close"]-atr_s.iloc[i]*tp_mult
                rpu=atr_s.iloc[i]*sl_mult
                if rpu==0: continue
                units=(cash*RISK)/rpu/LEV
                pos={"side":-1,"entry_price":ep,"units":units,"open":idx,"peak":ep,"sl":slp,"tp":tpp}
    if pos:
        cp=df.iloc[-1]["close"]; fee=cp*pos["units"]*FEE*LEV
        if pos["side"]==1: unreal=(cp-pos["entry_price"])*pos["units"]*LEV
        else: unreal=(pos["entry_price"]-cp)*pos["units"]*LEV
        cash+=unreal-fee
        trades.append({"pnl":unreal-fee,"reason":"TIME"})
    net=cash/10000-1
    wins=[t for t in trades if t["pnl"]>0]; losses=[t for t in trades if t["pnl"]<=0]
    gs=sum(t["pnl"] for t in wins); ls=abs(sum(t["pnl"] for t in losses))
    pf=gs/ls if ls>0 else 0
    wr=len(wins)/len(trades)*100 if trades else 0
    return {"net":net*100,"pf":pf,"wr":wr,"trades":len(trades),"wins":len(wins),"losses":len(losses),
            "dist_mult":dist_mult,"sl_mult":sl_mult,"tp_mult":tp_mult}

START="2023-01-01"; END=datetime.datetime.now(datetime.timezone.utc)
start_ms = int(datetime.datetime(2023,1,1,tzinfo=datetime.timezone.utc).timestamp()*1000)
end_ms   = int(END.timestamp()*1000)

results = {}
for sym in ["BTCUSDT","ETHUSDT","SOLUSDT"]:
    print(f"\n=== Fetch {sym} ===", flush=True)
    bars = fetch(sym, "1h", start_ms, end_ms)
    if not bars:
        print(f"  FAIL {sym}"); continue
    df = bars_to_frame(bars, sym)
    print(f"  → {len(df)} bars")
    results[sym] = {"df": df}

print("\n" + "="*60)
print("H2 CROSS-SYMBOL: sweep+snapback + EMA200 filter")
print("="*60)
for sym, r in results.items():
    df = r["df"]
    for slm, tpm in [(1.5,2.0),(2.0,2.0),(2.5,2.0),(3.0,1.0),(3.0,0.5)]:
        res = run_h2(df, slm, tpm, use_ema=True)
        print(f"  {sym} SL={slm}x ATR TP={tpm}x ATR: net={res['net']:.2f}% pf={res['pf']:.2f} wr={res['wr']:.1f}% trades={res['trades']} (L={res['longs']} S={res['shorts']})  snapL={res['snap_low']} snapH={res['snap_high']}")
    print()

print("="*60)
print("H1: reversão de média com distância normalizada por ATR")
print("="*60)
if "BTCUSDT" in results:
    df = results["BTCUSDT"]["df"]
    for dm in [1.5, 2.0, 2.5, 3.0]:
        for slm in [1.5, 2.0, 2.5]:
            for tpm in [1.0, 1.5, 2.0]:
                res = run_h1(df, dm, slm, tpm)
                if res["trades"] >= 100:
                    print(f"  BTC SL={slm}x TP={tpm}x dist={dm}x: net={res['net']:.2f}% pf={res['pf']:.2f} wr={res['wr']:.1f}% trades={res['trades']}")
    print()

# resumo H2 por símbolo (melhor combinação)
print("="*60)
print("RESUMO H2 — melhor combinação por símbolo")
print("="*60)
summary_h2 = []
for sym, r in results.items():
    df = r["df"]
    best = None
    for slm in [1.5,2.0,2.5,3.0]:
        for tpm in [0.5,1.0,1.5,2.0,2.5,3.0]:
            res = run_h2(df, slm, tpm, use_ema=True)
            if best is None or res["net"] > best["net"]:
                best = res
                best["sl"]=slm; best["tp"]=tpm
    if best:
        summary_h2.append({"symbol":sym,"best_net":round(best["net"],2),"best_pf":round(best["pf"],2),
                           "best_wr":round(best["wr"],1),"trades":best["trades"],
                           "sl":best["sl"],"tp":best["tp"],
                           "longs":best["longs"],"shorts":best["shorts"]})
        print(f"  {sym}: melhor SL={best['sl']}x TP={best['tp']}x → net={best['net']:.2f}% pf={best['pf']:.2f} wr={best['wr']:.1f}% trades={best['trades']} (L={best['longs']} S={best['shorts']})")

print()
print("="*60)
print("CONCLUSÃO H2: edge cross-symbol?")
h2_ok = [s for s in summary_h2 if s["best_pf"] >= 1.1]
if h2_ok:
    print(f"  H2 tem PF>=1.1 em: {[s['symbol'] for s in h2_ok]}")
else:
    print("  H2 NÃO tem PF>=1.1 em NENHUM símbolo testado → linha sem edge")

# salvar
tmpdir = os.path.join(os.environ.get("LOCALAPPDATA","C:/Users/seares/AppData/Local"),"Temp")
os.makedirs(tmpdir, exist_ok=True)
with open(os.path.join(tmpdir,"cross_symbol_h2.json"),"w") as f:
    json.dump({"h2_summary":summary_h2}, f, ensure_ascii=False, indent=2)
print(f"\nSalvo {os.path.join(tmpdir,'cross_symbol_h2.json')}")
