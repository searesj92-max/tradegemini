#!/usr/bin/env python3
"""
Backtest Engine: Weekly Sniper Options (7-10 Days DTE) with Dynamic Rollover
Simulates 3-Year (2023-2026) and 6-Year (2020-2026) BTC Daily Candles.
Evaluates:
  - 7 to 10 day expiry cycles
  - Take Profit at 75%
  - Real Defensive Rollovers when Spot breaches or threatens Short Strike (Down & Out / Forward Roll)
  - Max consecutive rolls (up to 3 rolls)
  - Compounding vs Fixed sizing ($1,850 and $10,000 portfolio base)
"""

import math
import time
import json
import datetime
import urllib.request
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent

def fetch_historical_btc_candles():
    end_time = int(time.time() * 1000)
    all_candles = []
    print("[1/4] Coletando candles históricos do Bitcoin da Binance...")
    for page in range(3):
        url = f'https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1d&limit=1000&endTime={end_time}'
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                if not data:
                    break
                all_candles = data + all_candles
                end_time = data[0][0] - 1
                time.sleep(0.15)
        except Exception as e:
            print(f"[FETCH ERROR] {e}")
            break
            
    unique_candles = {c[0]: c for c in all_candles}
    sorted_raw = [unique_candles[k] for k in sorted(unique_candles.keys())]
    
    candles = []
    for r in sorted_raw:
        candles.append({
            'timestamp': int(r[0]),
            'date': datetime.datetime.fromtimestamp(r[0] / 1000).strftime('%Y-%m-%d'),
            'year': datetime.datetime.fromtimestamp(r[0] / 1000).year,
            'open': float(r[1]),
            'high': float(r[2]),
            'low': float(r[3]),
            'close': float(r[4])
        })
    print(f"[DATA READY] {len(candles)} candles diários carregados ({candles[0]['date']} a {candles[-1]['date']}).")
    return candles

def normal_cdf(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

def bs_put_price(s, k, t, r, sigma):
    if t <= 0:
        return max(0.0, k - s)
    if sigma <= 0.01:
        sigma = 0.01
    d1 = (math.log(s / k) + (r + 0.5 * sigma ** 2) * t) / (sigma * math.sqrt(t))
    d2 = d1 - sigma * math.sqrt(t)
    return k * math.exp(-r * t) * normal_cdf(-d2) - s * normal_cdf(-d1)

def run_weekly_sniper_backtest(candles, years=3, initial_capital=1850.0, otm_pct=0.06, target_dte=8):
    today = datetime.datetime.now()
    target_start = today - datetime.timedelta(days=int(years * 365.25))
    target_ts = int(target_start.timestamp() * 1000)
    
    sub_candles = [c for c in candles if c['timestamp'] >= target_ts]
    if len(sub_candles) < 50:
        return None
        
    r = 0.04
    # 20-day realized volatility
    vols = [0.55] * len(sub_candles)
    for i in range(20, len(sub_candles)):
        rets = [math.log(sub_candles[j]['close'] / sub_candles[j-1]['close']) for j in range(i-19, i+1)]
        mean_r = sum(rets) / len(rets)
        var = sum((x - mean_r) ** 2 for x in rets) / (len(rets) - 1)
        vols[i] = math.sqrt(var) * math.sqrt(365)
        
    capital = initial_capital
    peak_capital = initial_capital
    max_dd_pct = 0.0
    
    current_trade = None
    trade_logs = []
    
    stats = {
        'total_cycles': 0,
        'normal_wins_tp': 0,
        'normal_wins_expired': 0,
        'rolled_cycles': 0,
        'roll_saved_wins': 0,
        'roll_failed_stops': 0,
        'total_rolls_count': 0,
        'total_profit': 0.0,
        'win_rate': 0.0,
        'max_dd': 0.0
    }
    
    i = 20
    while i < len(sub_candles):
        c = sub_candles[i]
        spot = c['close']
        iv = max(0.35, vols[i] * 1.15)
        
        # 1. Manage active trade
        if current_trade:
            dte_rem = current_trade['target_dte'] - (i - current_trade['entry_idx'])
            t_annual = max(0.001, dte_rem / 365.0)
            
            p_s = bs_put_price(spot, current_trade['short_strike'], t_annual, r, iv)
            p_l = bs_put_price(spot, current_trade['long_strike'], t_annual, r, iv)
            close_cost = max(0.0, p_s - p_l) * current_trade['contracts']
            
            # Cumulative PnL of this trade chain (including roll costs/credits)
            unrealized_pnl = current_trade['accum_credit'] - close_cost
            captured_pct = (unrealized_pnl / current_trade['initial_credit']) * 100 if current_trade['initial_credit'] > 0 else 0
            
            # CONDITION A: Take Profit at 75%
            if captured_pct >= 75.0:
                pnl = current_trade['accum_credit'] - close_cost
                capital += pnl
                stats['total_cycles'] += 1
                if current_trade['roll_count'] > 0:
                    stats['roll_saved_wins'] += 1
                else:
                    stats['normal_wins_tp'] += 1
                trade_logs.append({
                    'date': c['date'],
                    'type': 'TP_75%',
                    'rolls': current_trade['roll_count'],
                    'pnl': round(pnl, 2),
                    'spot': spot,
                    'capital': round(capital, 2)
                })
                current_trade = None
                
            # CONDITION B: Price Threat / Breach -> DEFENSIVE ROLLOVER!
            # If Spot drops within 1% of short strike or below short strike
            elif (spot <= current_trade['short_strike'] * 1.01) and (current_trade['roll_count'] < 3) and (i + 8 < len(sub_candles)):
                # Execute Roll:
                # 1. Pay close_cost to buy back current spread
                cost_to_close = close_cost
                current_trade['accum_credit'] -= cost_to_close
                current_trade['roll_count'] += 1
                stats['total_rolls_count'] += 1
                
                # 2. Open new roll spread: Roll out in time (+8 days) and down in strike (new spot * 0.95)
                new_short = round((spot * (1.0 - otm_pct)) / 500) * 500
                new_width = current_trade['width']
                new_long = new_short - new_width
                new_dte = target_dte
                t_new = new_dte / 365.0
                
                p_s_new = bs_put_price(spot, new_short, t_new, r, iv)
                p_l_new = bs_put_price(spot, new_long, t_new, r, iv)
                new_credit_unit = max(40.0, p_s_new - p_l_new)
                new_credit_total = new_credit_unit * current_trade['contracts']
                
                current_trade['accum_credit'] += new_credit_total
                current_trade['entry_idx'] = i
                current_trade['target_dte'] = new_dte
                current_trade['short_strike'] = new_short
                current_trade['long_strike'] = new_long
                
                if current_trade['roll_count'] == 1:
                    stats['rolled_cycles'] += 1
                    
            # CONDITION C: Max rolls reached or DTE reached zero
            elif dte_rem <= 0:
                stats['total_cycles'] += 1
                if spot >= current_trade['short_strike']:
                    # Finished above short strike: full credit kept!
                    pnl = current_trade['accum_credit']
                    if current_trade['roll_count'] > 0:
                        stats['roll_saved_wins'] += 1
                    else:
                        stats['normal_wins_expired'] += 1
                elif spot <= current_trade['long_strike']:
                    # Below long strike: max loss of the spread
                    loss_total = current_trade['width'] * current_trade['contracts']
                    pnl = current_trade['accum_credit'] - loss_total
                    if current_trade['roll_count'] > 0:
                        stats['roll_failed_stops'] += 1
                    else:
                        stats['roll_failed_stops'] += 1
                else:
                    # In between strikes
                    loss_total = (current_trade['short_strike'] - spot) * current_trade['contracts']
                    pnl = current_trade['accum_credit'] - loss_total
                    if pnl >= 0:
                        stats['roll_saved_wins'] += 1
                    else:
                        stats['roll_failed_stops'] += 1
                        
                capital += pnl
                trade_logs.append({
                    'date': c['date'],
                    'type': 'EXPIRED',
                    'rolls': current_trade['roll_count'],
                    'pnl': round(pnl, 2),
                    'spot': spot,
                    'capital': round(capital, 2)
                })
                current_trade = None
                
        # Drawdown tracking
        if capital > peak_capital:
            peak_capital = capital
        dd = (peak_capital - capital) / peak_capital * 100 if peak_capital > 0 else 0
        if dd > max_dd_pct:
            max_dd_pct = dd
            
        # Open new trade if none active
        if not current_trade and (i + target_dte) < len(sub_candles):
            t_ann = target_dte / 365.0
            short_k = round((spot * (1.0 - otm_pct)) / 500) * 500
            spread_w = 4000.0 if spot > 60000 else 2500.0
            long_k = short_k - spread_w
            
            p_s0 = bs_put_price(spot, short_k, t_ann, r, iv)
            p_l0 = bs_put_price(spot, long_k, t_ann, r, iv)
            credit_u = max(40.0, p_s0 - p_l0)
            margin_u = spread_w - credit_u
            
            # Sizing: use 65% to 75% of capital (conservative margin buffer)
            alloc_margin = capital * 0.70
            contracts = round(math.floor((alloc_margin / margin_u) * 100) / 100, 2)
            if contracts < 0.05:
                contracts = 0.05
                
            init_credit = credit_u * contracts
            current_trade = {
                'entry_idx': i,
                'target_dte': target_dte,
                'short_strike': short_k,
                'long_strike': long_k,
                'width': spread_w,
                'contracts': contracts,
                'initial_credit': init_credit,
                'accum_credit': init_credit,
                'roll_count': 0
            }
            
        i += 1
        
def run_weekly_sniper_backtest(candles, years=3, initial_capital=1850.0, otm_pct=0.06, target_dte=8, mode='fixed_tranche', fixed_alloc=1200.0):
    today = datetime.datetime.now()
    target_start = today - datetime.timedelta(days=int(years * 365.25))
    target_ts = int(target_start.timestamp() * 1000)
    
    sub_candles = [c for c in candles if c['timestamp'] >= target_ts]
    if len(sub_candles) < 50:
        return None
        
    r = 0.04
    vols = [0.55] * len(sub_candles)
    for i in range(20, len(sub_candles)):
        rets = [math.log(sub_candles[j]['close'] / sub_candles[j-1]['close']) for j in range(i-19, i+1)]
        mean_r = sum(rets) / len(rets)
        var = sum((x - mean_r) ** 2 for x in rets) / (len(rets) - 1)
        vols[i] = math.sqrt(var) * math.sqrt(365)
        
    capital = initial_capital
    extracted_profit = 0.0
    peak_capital = initial_capital
    max_dd_pct = 0.0
    
    current_trade = None
    trade_logs = []
    
    stats = {
        'total_cycles': 0,
        'normal_wins_tp': 0,
        'normal_wins_expired': 0,
        'rolled_cycles': 0,
        'roll_saved_wins': 0,
        'roll_failed_stops': 0,
        'total_rolls_count': 0,
        'total_profit': 0.0,
        'win_rate': 0.0,
        'max_dd': 0.0,
        'mode': mode
    }
    
    i = 20
    while i < len(sub_candles):
        c = sub_candles[i]
        spot = c['close']
        iv = max(0.35, vols[i] * 1.15)
        
        # 1. Manage active trade
        if current_trade:
            dte_rem = current_trade['target_dte'] - (i - current_trade['entry_idx'])
            t_annual = max(0.001, dte_rem / 365.0)
            
            p_s = bs_put_price(spot, current_trade['short_strike'], t_annual, r, iv)
            p_l = bs_put_price(spot, current_trade['long_strike'], t_annual, r, iv)
            close_cost = max(0.0, p_s - p_l) * current_trade['contracts']
            
            unrealized_pnl = current_trade['accum_credit'] - close_cost
            captured_pct = (unrealized_pnl / current_trade['initial_credit']) * 100 if current_trade['initial_credit'] > 0 else 0
            
            # CONDITION A: Take Profit at 75%
            if captured_pct >= 75.0:
                pnl = current_trade['accum_credit'] - close_cost
                capital += pnl
                stats['total_cycles'] += 1
                if current_trade['roll_count'] > 0:
                    stats['roll_saved_wins'] += 1
                else:
                    stats['normal_wins_tp'] += 1
                    
                if mode == 'fixed_tranche' and capital > initial_capital:
                    extracted_profit += (capital - initial_capital)
                    capital = initial_capital
                    
                trade_logs.append({
                    'date': c['date'],
                    'type': 'TP_75%',
                    'rolls': current_trade['roll_count'],
                    'pnl': round(pnl, 2),
                    'spot': spot,
                    'capital': round(capital + extracted_profit, 2)
                })
                current_trade = None
                
            # CONDITION B: Price Threat / Breach -> DEFENSIVE ROLLOVER!
            elif (spot <= current_trade['short_strike'] * 1.01) and (current_trade['roll_count'] < 3) and (i + 8 < len(sub_candles)):
                cost_to_close = close_cost
                current_trade['accum_credit'] -= cost_to_close
                current_trade['roll_count'] += 1
                stats['total_rolls_count'] += 1
                
                # Roll out in time (+8 days) and down in strike
                new_short = round((spot * (1.0 - otm_pct)) / 500) * 500
                new_width = current_trade['width']
                new_long = new_short - new_width
                new_dte = target_dte
                t_new = new_dte / 365.0
                
                p_s_new = bs_put_price(spot, new_short, t_new, r, iv)
                p_l_new = bs_put_price(spot, new_long, t_new, r, iv)
                new_credit_unit = max(40.0, p_s_new - p_l_new)
                new_credit_total = new_credit_unit * current_trade['contracts']
                
                current_trade['accum_credit'] += new_credit_total
                current_trade['entry_idx'] = i
                current_trade['target_dte'] = new_dte
                current_trade['short_strike'] = new_short
                current_trade['long_strike'] = new_long
                
                if current_trade['roll_count'] == 1:
                    stats['rolled_cycles'] += 1
                    
            # CONDITION C: Max rolls reached or DTE reached zero
            elif dte_rem <= 0:
                stats['total_cycles'] += 1
                if spot >= current_trade['short_strike']:
                    pnl = current_trade['accum_credit']
                    if current_trade['roll_count'] > 0:
                        stats['roll_saved_wins'] += 1
                    else:
                        stats['normal_wins_expired'] += 1
                elif spot <= current_trade['long_strike']:
                    loss_total = current_trade['width'] * current_trade['contracts']
                    pnl = current_trade['accum_credit'] - loss_total
                    stats['roll_failed_stops'] += 1
                else:
                    loss_total = (current_trade['short_strike'] - spot) * current_trade['contracts']
                    pnl = current_trade['accum_credit'] - loss_total
                    if pnl >= 0:
                        stats['roll_saved_wins'] += 1
                    else:
                        stats['roll_failed_stops'] += 1
                        
                capital += pnl
                if mode == 'fixed_tranche' and capital > initial_capital:
                    extracted_profit += (capital - initial_capital)
                    capital = initial_capital
                    
                trade_logs.append({
                    'date': c['date'],
                    'type': 'EXPIRED',
                    'rolls': current_trade['roll_count'],
                    'pnl': round(pnl, 2),
                    'spot': spot,
                    'capital': round(capital + extracted_profit, 2)
                })
                current_trade = None
                
        # Drawdown tracking on total account net worth
        total_net_worth = capital + extracted_profit if mode == 'fixed_tranche' else capital
        if total_net_worth > peak_capital:
            peak_capital = total_net_worth
        dd = (peak_capital - total_net_worth) / peak_capital * 100 if peak_capital > 0 else 0
        if dd > max_dd_pct:
            max_dd_pct = dd
            
        # Open new trade if none active
        if not current_trade and (i + target_dte) < len(sub_candles):
            t_ann = target_dte / 365.0
            short_k = round((spot * (1.0 - otm_pct)) / 500) * 500
            spread_w = 4000.0 if spot > 60000 else 2500.0
            long_k = short_k - spread_w
            
            p_s0 = bs_put_price(spot, short_k, t_ann, r, iv)
            p_l0 = bs_put_price(spot, long_k, t_ann, r, iv)
            credit_u = max(40.0, p_s0 - p_l0)
            margin_u = spread_w - credit_u
            
            # Allocation sizing
            if mode == 'fixed_tranche':
                alloc_margin = fixed_alloc
            else:
                # Controlled compounding: max 25% of total capital per trade
                alloc_margin = min(capital * 0.25, 5000.0)
                
            contracts = round(math.floor((alloc_margin / margin_u) * 100) / 100, 2)
            if contracts < 0.05:
                contracts = 0.05
                
            init_credit = credit_u * contracts
            current_trade = {
                'entry_idx': i,
                'target_dte': target_dte,
                'short_strike': short_k,
                'long_strike': long_k,
                'width': spread_w,
                'contracts': contracts,
                'initial_credit': init_credit,
                'accum_credit': init_credit,
                'roll_count': 0
            }
            
        i += 1
        
    wins_total = stats['normal_wins_tp'] + stats['normal_wins_expired'] + stats['roll_saved_wins']
    total_ops = stats['total_cycles']
    win_rate = (wins_total / total_ops * 100) if total_ops > 0 else 0
    final_equity = capital + extracted_profit if mode == 'fixed_tranche' else capital
    stats['total_profit'] = final_equity - initial_capital
    stats['win_rate'] = win_rate
    stats['max_dd'] = max_dd_pct
    stats['final_capital'] = final_equity
    stats['extracted_profit'] = extracted_profit
    
    return stats, trade_logs, sub_candles

def main():
    candles = fetch_historical_btc_candles()
    
    print("\n" + "="*85)
    print("BACKTEST QUANTITATIVO: SNIPER SEMANAL (7-10 DIAS) COM ROLAGEM DEFENSIVA")
    print("="*85)
    
    # 1. Teste no capital do usuário ($1.850 total, mão fixa de $1.200 por ciclo)
    stats_user, _, candles3 = run_weekly_sniper_backtest(
        candles, years=3, initial_capital=1850.0, otm_pct=0.06, target_dte=8, mode='fixed_tranche', fixed_alloc=1200.0
    )
    
    print(f"\n[CENÁRIO 1: CARTEIRA ATUAL DO USUÁRIO ($1,850 COM MÃO FIXA DE $1,200)]")
    print(f"Período: 3 Anos ({candles3[0]['date']} a {candles3[-1]['date']}) | BTC: ${candles3[0]['close']:,.2f} -> ${candles3[-1]['close']:,.2f}")
    print(f"Total de Ciclos Operados: {stats_user['total_cycles']} semanas")
    print(f"Vitórias Diretas (Sem Calor): {stats_user['normal_wins_tp'] + stats_user['normal_wins_expired']} trades")
    print(f"Ciclos que Acionaram Rolagem Defensiva: {stats_user['rolled_cycles']} vezes")
    print(f"  -> Rolagens que SALVARAM o Trade no Lucro: {stats_user['roll_saved_wins']} ({stats_user['roll_saved_wins']/(stats_user['rolled_cycles'] or 1)*100:.1f}%)")
    print(f"  -> Rolagens que Estoparam: {stats_user['roll_failed_stops']}")
    print(f"Taxa de Acerto Total (Win Rate): {stats_user['win_rate']:.1f}%")
    print(f"Lucro Líquido Acumulado: +${stats_user['total_profit']:,.2f} (+{stats_user['total_profit']/1850.0*100:.1f}%)")
    print(f"Renda Média Mensal Gerada: +${stats_user['total_profit']/36:.2f} / mês")
    print(f"Saldo Final Total: ${stats_user['final_capital']:,.2f}")
    print(f"Maior Drawdown Patrimonial: {stats_user['max_dd']:.1f}%")
    
    # 2. Teste em 6 anos com o Crash de 2022
    stats_6y, _, candles6 = run_weekly_sniper_backtest(
        candles, years=6, initial_capital=1850.0, otm_pct=0.06, target_dte=8, mode='fixed_tranche', fixed_alloc=1200.0
    )
    print("\n" + "-"*85)
    print(f"[CENÁRIO 2: STRESS TEST DE 6 ANOS (2020-2026 | SOBREVIVÊNCIA AO CRASH DE 2022)]")
    print(f"Total de Ciclos: {stats_6y['total_cycles']} semanas")
    print(f"Rolagens que Salvaram: {stats_6y['roll_saved_wins']} de {stats_6y['rolled_cycles']} ({stats_6y['roll_saved_wins']/(stats_6y['rolled_cycles'] or 1)*100:.1f}%)")
    print(f"Taxa de Acerto: {stats_6y['win_rate']:.1f}%")
    print(f"Lucro Líquido Acumulado: +${stats_6y['total_profit']:,.2f} (+{stats_6y['total_profit']/1850.0*100:.1f}%)")
    print(f"Maior Drawdown nos 6 Anos: {stats_6y['max_dd']:.1f}%")
    print("="*85 + "\n")

if __name__ == "__main__":
    main()
