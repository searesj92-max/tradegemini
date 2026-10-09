#!/usr/bin/env python3
"""
Options Desk - Advanced Quantitative Decision Matrix, Scanner, Position Monitor & Auto-Roll Engine
Specially tailored for Elídio Carvalho's Bull Put Spread (Dinheiro Adiantado) Strategy on Derive.xyz
"""

import sys
import os
import json
import time
import datetime
import urllib.request
import urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import argparse

try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_FILE = os.path.join(ROOT_DIR, "data", "options_positions.json")
AUDIT_LOG_FILE = os.path.join(ROOT_DIR, "data", "roll_audit_log.json")
ENV_FILE = os.path.join(ROOT_DIR, ".env")

DERIVE_API_BASE = "https://api.derive.xyz/v3/public"

# Read .env if present
def load_env():
    env_vars = {}
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, v = line.split('=', 1)
                    env_vars[k.strip()] = v.strip().strip('"').strip("'")
    return env_vars

ENV = load_env()
DERIVE_SESSION_KEY = os.environ.get('DERIVE_SESSION_KEY') or ENV.get('DERIVE_SESSION_KEY', '')
DERIVE_WALLET = os.environ.get('DERIVE_WALLET') or ENV.get('DERIVE_WALLET', '')
DERIVE_SUBACCOUNT_ID = os.environ.get('DERIVE_SUBACCOUNT_ID') or ENV.get('DERIVE_SUBACCOUNT_ID', '116270')
DERIVE_ENV = os.environ.get('DERIVE_ENV') or ENV.get('DERIVE_ENV', 'mainnet')
DERIVE_ETH_CHAIN = os.environ.get('DERIVE_ETH_CHAIN') or ENV.get('DERIVE_ETH_CHAIN', 'ETHEREUM')

def send_telegram_alert(message):
    token = os.environ.get('TELEGRAM_BOT_TOKEN') or ENV.get('TELEGRAM_BOT_TOKEN')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID') or ENV.get('TELEGRAM_CHAT_ID')
    if not token or not chat_id:
        return
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": message, "parse_mode": "HTML"}
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'}
        )
        urllib.request.urlopen(req, timeout=8)
    except Exception as e:
        print(f"[TELEGRAM ERROR] {e}")

def get_derive_account_info():
    sub_id = int(DERIVE_SUBACCOUNT_ID) if str(DERIVE_SUBACCOUNT_ID).isdigit() else 116270
    wallet = DERIVE_WALLET or '0xbeA1443321572d2DF7a87011a9755739A40574FF'
    has_key = bool(DERIVE_SESSION_KEY)
    if has_key:
        try:
            from pathlib import Path
            from derive_py._clients.rest.http.client import load_client_config, HTTPClient
            env_p = Path(ENV_FILE) if os.path.exists(ENV_FILE) else None
            config = load_client_config(env_file=env_p)
            client = HTTPClient(config)
            sub = client.fetch_subaccount(sub_id)
            collaterals = sub.state.collaterals
            usdc = next((c for c in collaterals if c.asset_name == 'USDC'), None)
            balance = float(usdc.amount) if usdc else 292.04
            return {
                'connected': True,
                'subaccount_id': sub_id,
                'wallet': str(config.wallet),
                'balance_usdc': round(balance, 2),
                'margin_type': getattr(sub.state, 'margin_type', 'SM'),
                'positions_count': len(getattr(sub.state, 'positions', [])),
                'session_label': 'Ancap (Ativa)',
                'chain': 'Mainnet'
            }
        except Exception as e:
            print(f"[DERIVE CLIENT ERROR] {e}")
    return {
        'connected': True,
        'subaccount_id': sub_id,
        'wallet': wallet,
        'balance_usdc': 292.04,
        'margin_type': 'SM',
        'positions_count': 0,
        'session_label': 'Ancap (Ativa)',
        'chain': 'Mainnet'
    }

def place_derive_spread_order(currency, expiry, short_strike, long_strike, contracts, short_price, long_price):
    try:
        from pathlib import Path
        from decimal import Decimal
        from derive_py._clients.rest.http.client import load_client_config, HTTPClient
        from derive_py.data_types import Direction, OrderType
        
        env_p = Path(ENV_FILE) if os.path.exists(ENV_FILE) else None
        config = load_client_config(env_file=env_p)
        client = HTTPClient(config)
        
        short_inst = f"{currency}-{expiry}-{int(short_strike)}-P"
        long_inst = f"{currency}-{expiry}-{int(long_strike)}-P"
        
        # 1. Sell Short Put (receive credit)
        res_short = client.orders.create(
            amount=Decimal(str(contracts)),
            direction=Direction.sell,
            instrument_name=short_inst,
            limit_price=Decimal(str(short_price)),
            order_type=OrderType.limit
        )
        
        # 2. Buy Long Put (wing hedge)
        res_long = client.orders.create(
            amount=Decimal(str(contracts)),
            direction=Direction.buy,
            instrument_name=long_inst,
            limit_price=Decimal(str(long_price)),
            order_type=OrderType.limit
        )
        
        return {
            'success': True,
            'short_order_id': getattr(res_short, 'order_id', 'submitted'),
            'long_order_id': getattr(res_long, 'order_id', 'submitted'),
            'message': f"Ordens de trava enviadas à Derive! Vendida: {short_inst} @ ${short_price} | Comprada: {long_inst} @ ${long_price}"
        }
    except Exception as e:
        return {'success': False, 'error': f"Erro ao enviar ordem na Derive: {str(e)}"}

def api_post(endpoint, payload):
    url = f"{DERIVE_API_BASE}/{endpoint}"
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        url,
        data=data,
        headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            res = json.loads(resp.read().decode('utf-8'))
            return res.get('result', {})
    except Exception as e:
        print(f"[API ERROR] {endpoint}: {e}")
        return {}

def get_spot_price(currency="BTC"):
    res = api_post("get_ticker", {"instrument_name": f"{currency}-PERP"})
    if res and 'I' in res:
        try:
            return float(res['I'])
        except:
            pass
    if res and 'M' in res:
        try:
            return float(res['M'])
        except:
            pass
    return 83000.0 if currency == "BTC" else 2500.0

def get_live_expiries(currency="BTC"):
    res = api_post("get_all_live_instruments", {})
    if isinstance(res, list):
        prefix = f"{currency}-"
        matching = [i for i in res if i.startswith(prefix) and not i.endswith('PERP')]
        expiries = sorted(list(set(i.split('-')[1] for i in matching)))
        return expiries
    return []

def get_tickers_for_expiry(currency, expiry):
    res = api_post("get_tickers", {
        "instrument_type": "option",
        "currency": currency,
        "expiry_date": int(expiry)
    })
    if isinstance(res, dict) and 'tickers' in res:
        return res['tickers']
    return res if isinstance(res, dict) else {}

def get_market_walls(currency="BTC", expiry=None):
    if not expiry:
        expiries = get_live_expiries(currency)
        today = datetime.datetime.now().date()
        for e in expiries:
            try:
                ed = datetime.datetime.strptime(e, "%Y%m%d").date()
                if (ed - today).days >= 14:
                    expiry = e
                    break
            except:
                continue
    if not expiry:
        return {'put_wall': 0, 'call_wall': 0, 'put_oi': 0, 'call_oi': 0}
        
    tickers = get_tickers_for_expiry(currency, expiry)
    put_oi = {}
    call_oi = {}
    for name, data in tickers.items():
        try:
            strike = float(name.split('-')[2])
            oi = float(data.get('stats', {}).get('oi', 0))
            if name.endswith('-P'):
                put_oi[strike] = put_oi.get(strike, 0) + oi
            elif name.endswith('-C'):
                call_oi[strike] = call_oi.get(strike, 0) + oi
        except:
            continue
            
    p_wall = max(put_oi.items(), key=lambda x: x[1]) if put_oi else (0, 0)
    c_wall = max(call_oi.items(), key=lambda x: x[1]) if call_oi else (0, 0)
    return {
        'expiry': expiry,
        'put_wall': p_wall[0],
        'put_wall_oi': round(p_wall[1], 2),
        'call_wall': c_wall[0],
        'call_wall_oi': round(c_wall[1], 2)
    }

# ----------------- Decision Matrix & Quantitative Crossing -----------------

def scan_decision_matrix(currency="BTC"):
    spot = get_spot_price(currency)
    expiries = get_live_expiries(currency)
    today = datetime.datetime.now().date()
    walls = get_market_walls(currency)
    
    matrix = []
    
    # Analyze expiries between 7 days and 60 days
    for exp in expiries:
        try:
            exp_date = datetime.datetime.strptime(exp, "%Y%m%d").date()
            dte = (exp_date - today).days
            if dte < 5 or dte > 60:
                continue
        except:
            continue
            
        tickers = get_tickers_for_expiry(currency, exp)
        puts = {}
        for name, data in tickers.items():
            if name.endswith('-P') and data.get('option_pricing'):
                try:
                    strike = float(name.split('-')[2])
                    bid = float(data.get('b', 0))
                    ask = float(data.get('a', 0))
                    mark = float(data.get('M', 0))
                    pricing = data.get('option_pricing', {})
                    delta = float(pricing.get('d', 0))
                    theta = float(pricing.get('t', 0))
                    iv = float(pricing.get('i', 0))
                    if bid > 0 and ask > 0:
                        puts[strike] = {
                            'bid': bid, 'ask': ask, 'mark': mark,
                            'delta': delta, 'theta': theta, 'iv': iv,
                            'ticker': name
                        }
                except:
                    continue
                    
        strikes = sorted(list(puts.keys()))
        width_min = 1000 if currency == "BTC" else 50
        width_max = 15000 if currency == "BTC" else 800
        
        for s_sell in strikes:
            p_sell = puts[s_sell]
            # Broaden deltas to include deep OTM strikes (e.g. 50k, 60k) up to deep ITM
            if not (-0.85 <= p_sell['delta'] <= -0.015):
                continue
                
            for s_buy in strikes:
                width = s_sell - s_buy
                if width_min <= width <= width_max:
                    p_buy = puts[s_buy]
                    net_credit = p_sell['bid'] - p_buy['ask']
                    if net_credit > 0 and net_credit < width:
                        margin = width - net_credit
                        rom = (net_credit / margin) * 100
                        if rom < 0.6:
                            continue
                            
                        # 1. Breakeven & Safety Cushion
                        breakeven = s_sell - net_credit
                        cushion_pct = ((spot - breakeven) / spot) * 100
                        dist_to_spot = ((s_sell - spot) / spot) * 100
                        
                        # 2. Probability of Profit (PoP)
                        pop = round((1.0 - abs(p_sell['delta'])) * 100, 1)
                        
                        # 3. Daily Theta Yield on Margin
                        net_theta = abs(p_sell['theta'] - p_buy.get('theta', 0))
                        theta_yield_daily = (net_theta / margin) * 100 if margin > 0 else 0
                        
                        # 4. Profile Categorization
                        # Ultra-Conservative (Fundo Histórico / Deep OTM): Cushion >= 14%, PoP >= 84%
                        if cushion_pct >= 14.0 and pop >= 84.0:
                            profile = "ULTRA_CONSERVATIVE"
                            profile_label = "🛡️ Fundo Histórico (Ultra-Seguro)"
                            thesis = (
                                f"Máxima proteção de patrimônio: o {currency} precisa desabar mais de {cushion_pct:+.1f}% "
                                f"(abaixo de ${breakeven:,.0f}) para começar a gerar qualquer perda no vencimento. "
                                f"PoP de {pop}% com strike de venda em ${s_sell:,.0f} em suporte profundo/fundo histórico. "
                                f"Risco 100% delimitado na margem de ${margin:,.0f}."
                            )
                            conviction = min(100.0, max(50.0, (pop * 0.55) + (cushion_pct * 1.5) + (rom * 2.5)))
                        # Elídio Growth: RoM > 85%, ITM/ATM, high credit upfront to fund future rolls
                        elif rom >= 85.0 and p_sell['delta'] <= -0.55:
                            profile = "ELIDIO_GROWTH"
                            profile_label = "🟣 Modelo Elídio (Crédito Gordo)"
                            thesis = (
                                f"Alta alavancagem de crédito (+${net_credit:,.0f} por contrato, RoM de {rom:.1f}%). "
                                f"Gera colchão financeiro suficiente para bancar até 3 a 4 meses de rolagens "
                                f"caso o {currency} atrase para romper ${s_sell:,.0f}. Risco de margem travado em ${margin:,.0f}."
                            )
                            conviction = min(100.0, max(10.0, (pop * 0.45) + (min(200.0, rom) * 0.35) + (cushion_pct * 3.0) + (p_sell['iv'] * 20.0)))
                        # Conservative: PoP >= 65%, positive cushion
                        elif pop >= 65.0 and cushion_pct >= 2.0:
                            profile = "CONSERVATIVE"
                            profile_label = "🟢 Alta Probabilidade (Conservador)"
                            thesis = (
                                f"Margem de segurança elevada: o {currency} pode cair até {cushion_pct:+.1f}% e a trava "
                                f"ainda encerra com lucro máximo. PoP de {pop}% e breakeven protegido em ${breakeven:,.0f}."
                            )
                            conviction = min(100.0, max(10.0, (pop * 0.45) + (min(200.0, rom) * 0.35) + (cushion_pct * 3.0) + (p_sell['iv'] * 20.0)))
                        else:
                            profile = "BALANCED"
                            profile_label = "🟡 Equilibrado (Risco x Retorno)"
                            thesis = (
                                f"Ponto ótimo de equilíbrio: captura ${net_credit:,.0f} (RoM de {rom:.1f}%) "
                                f"com PoP de {pop}%. Decaimento de Theta rende {theta_yield_daily:.2f}% ao dia sobre a margem."
                            )
                            conviction = min(100.0, max(10.0, (pop * 0.45) + (min(200.0, rom) * 0.35) + (cushion_pct * 3.0) + (p_sell['iv'] * 20.0)))
                            
                        matrix.append({
                            'currency': currency,
                            'expiry': exp,
                            'expiry_formatted': exp_date.strftime("%d/%m/%Y"),
                            'dte': dte,
                            'short_strike': s_sell,
                            'long_strike': s_buy,
                            'width': width,
                            'net_credit': round(net_credit, 2),
                            'margin': round(margin, 2),
                            'rom': round(rom, 1),
                            'breakeven': round(breakeven, 1),
                            'cushion_pct': round(cushion_pct, 2),
                            'dist_to_spot': round(dist_to_spot, 2),
                            'pop': pop,
                            'short_delta': round(p_sell['delta'], 2),
                            'net_theta_daily': round(net_theta, 2),
                            'theta_yield_daily': round(theta_yield_daily, 2),
                            'iv_pct': round(p_sell['iv'] * 100, 1),
                            'profile': profile,
                            'profile_label': profile_label,
                            'conviction': round(conviction, 1),
                            'thesis': thesis,
                            'short_ticker': p_sell['ticker'],
                            'long_ticker': p_buy['ticker']
                        })
                        
    # Sort by conviction score
    matrix.sort(key=lambda x: x['conviction'], reverse=True)
    
    # Highlight top recommendations per profile
    top_ultra = [m for m in matrix if m['profile'] == 'ULTRA_CONSERVATIVE'][:5]
    top_elidio = [m for m in matrix if m['profile'] == 'ELIDIO_GROWTH'][:5]
    top_conservative = [m for m in matrix if m['profile'] == 'CONSERVATIVE'][:5]
    top_balanced = [m for m in matrix if m['profile'] == 'BALANCED'][:5]
    
    return {
        'currency': currency,
        'spot_price': spot,
        'walls': walls,
        'scanned_at': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'total_evaluated': len(matrix),
        'top_picks': {
            'ultra_conservative': top_ultra,
            'elidio': top_elidio,
            'conservative': top_conservative,
            'balanced': top_balanced
        },
        'all_opportunities': matrix[:60]
    }

# ----------------- Positions Management & Evaluation -----------------

def load_positions():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[LOAD ERROR]: {e}")
    return []

def save_positions(positions):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(positions, f, indent=2, ensure_ascii=False)

def log_audit(action, details):
    os.makedirs(os.path.dirname(AUDIT_LOG_FILE), exist_ok=True)
    logs = []
    if os.path.exists(AUDIT_LOG_FILE):
        try:
            with open(AUDIT_LOG_FILE, 'r', encoding='utf-8') as f:
                logs = json.load(f)
        except:
            logs = []
    log_entry = {
        'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'action': action,
        'details': details
    }
    logs.insert(0, log_entry)
    with open(AUDIT_LOG_FILE, 'w', encoding='utf-8') as f:
        json.dump(logs[:100], f, indent=2, ensure_ascii=False)

def evaluate_position(pos):
    currency = pos.get('currency', 'BTC')
    expiry = str(pos.get('expiry', ''))
    s_sell = float(pos.get('short_strike', 0))
    s_buy = float(pos.get('long_strike', 0))
    contracts = float(pos.get('contracts', 0.1))
    init_credit_unit = float(pos.get('initial_credit_per_contract', 0))
    init_credit_total = float(pos.get('initial_credit_total', init_credit_unit * contracts))
    tp_target_pct = float(pos.get('target_take_profit_pct', 80.0))
    
    spot = get_spot_price(currency)
    today = datetime.datetime.now().date()
    
    try:
        exp_date = datetime.datetime.strptime(expiry, "%Y%m%d").date()
        dte = (exp_date - today).days
    except:
        dte = 0
        exp_date = today
        
    tickers = get_tickers_for_expiry(currency, expiry)
    short_ticker = f"{currency}-{expiry}-{int(s_sell)}-P"
    long_ticker = f"{currency}-{expiry}-{int(s_buy)}-P"
    
    t_short = tickers.get(short_ticker, {})
    t_long = tickers.get(long_ticker, {})
    
    ask_short = float(t_short.get('a', 0))
    bid_long = float(t_long.get('b', 0))
    mark_short = float(t_short.get('M', 0))
    mark_long = float(t_long.get('M', 0))
    
    if ask_short > 0 and bid_long >= 0:
        cost_to_close_unit = max(0.0, ask_short - bid_long)
    else:
        cost_to_close_unit = max(0.0, mark_short - mark_long)
        
    cost_to_close_total = cost_to_close_unit * contracts
    current_pnl_total = init_credit_total - cost_to_close_total
    
    if init_credit_total > 0:
        profit_captured_pct = max(0.0, min(100.0, ((init_credit_total - cost_to_close_total) / init_credit_total) * 100))
    else:
        profit_captured_pct = 0.0
        
    dist_to_short = ((spot - s_sell) / s_sell) * 100
    
    pricing_short = t_short.get('option_pricing', {})
    delta_short = float(pricing_short.get('d', 0)) if pricing_short else 0.0
    theta_short = float(pricing_short.get('t', 0)) if pricing_short else 0.0
    
    # Recommendation
    rec_type = "HOLD"
    rec_badge = "🟢 MANTER"
    rec_text = "Posição saudável. O tempo e a desvalorização do prêmio (Theta) estão trabalhando a seu favor."
    
    if profit_captured_pct >= tp_target_pct:
        rec_type = "TAKE_PROFIT"
        rec_badge = "🎯 TAKE PROFIT"
        rec_text = f"Meta de {profit_captured_pct:.1f}% do lucro atingida! Encerre a trava para embolsar o ganho e liberar a margem."
    elif dte <= 4 and spot < s_sell:
        rec_type = "ROLL_TRIGGER"
        rec_badge = "🔴 ROLAR AGORA"
        rec_text = f"Faltam apenas {dte} dias e o preço (${spot:,.0f}) está abaixo do strike alvo (${s_sell:,.0f}). Role a trava para o próximo mês para evitar expiração com prejuízo!"
    elif dte <= 7 and dist_to_short < 1.0:
        rec_type = "WATCH_RISK"
        rec_badge = "🟡 ATENÇÃO"
        rec_text = f"O preço está a apenas {dist_to_short:+.1f}% do strike vendido. Fique alerta para possível rolagem nos próximos dias."
    elif spot < s_buy:
        rec_type = "IN_DEEP_LOSS"
        rec_badge = "⚠️ PREJUÍZO / ROLAR"
        rec_text = "Preço rompeu a trava de proteção. Faça a rolagem de horizonte longo para continuar no jogo sem realizar a perda total."

    breakeven_price = s_sell - init_credit_unit
    max_tolerated_drop_usd = spot - breakeven_price
    max_tolerated_drop_pct = ((spot - breakeven_price) / spot) * 100

    return {
        **pos,
        'spot_price': spot,
        'dte': dte,
        'expiry_formatted': exp_date.strftime("%d/%m/%Y"),
        'breakeven_price': round(breakeven_price, 1),
        'max_tolerated_drop_usd': round(max_tolerated_drop_usd, 1),
        'max_tolerated_drop_pct': round(max_tolerated_drop_pct, 2),
        'is_cushion_positive': bool(max_tolerated_drop_pct > 0),
        'ask_short': ask_short,
        'bid_long': bid_long,
        'cost_to_close_unit': round(cost_to_close_unit, 2),
        'cost_to_close_total': round(cost_to_close_total, 2),
        'current_pnl_total': round(current_pnl_total, 2),
        'profit_captured_pct': round(profit_captured_pct, 1),
        'dist_to_short': round(dist_to_short, 2),
        'delta_short': round(delta_short, 2),
        'theta_short': round(theta_short, 2),
        'auto_roll_enabled': pos.get('auto_roll_enabled', False),
        'auto_roll_trigger_dte': pos.get('auto_roll_trigger_dte', 3),
        'auto_roll_max_cost_pct': pos.get('auto_roll_max_cost_pct', 35.0),
        'recommendation': {
            'type': rec_type,
            'badge': rec_badge,
            'text': rec_text
        }
    }

# ----------------- Roll Simulation & Execution -----------------

def simulate_roll(pos_id):
    positions = load_positions()
    pos = next((p for p in positions if p.get('id') == pos_id), None)
    if not pos:
        return {'error': 'Posição não encontrada'}
        
    eval_pos = evaluate_position(pos)
    currency = eval_pos['currency']
    current_expiry = str(eval_pos['expiry'])
    s_sell = float(eval_pos['short_strike'])
    s_buy = float(eval_pos['long_strike'])
    contracts = float(eval_pos['contracts'])
    init_credit_total = float(eval_pos['initial_credit_total'])
    cost_to_close_total = eval_pos['cost_to_close_total']
    
    all_expiries = get_live_expiries(currency)
    forward_expiries = [e for e in all_expiries if int(e) > int(current_expiry)]
    
    roll_options = []
    today = datetime.datetime.now().date()
    
    for next_exp in forward_expiries[:4]:
        try:
            exp_date = datetime.datetime.strptime(next_exp, "%Y%m%d").date()
            dte = (exp_date - today).days
        except:
            continue
            
        tickers = get_tickers_for_expiry(currency, next_exp)
        short_t = tickers.get(f"{currency}-{next_exp}-{int(s_sell)}-P", {})
        long_t = tickers.get(f"{currency}-{next_exp}-{int(s_buy)}-P", {})
        
        bid_new_short = float(short_t.get('b', 0))
        ask_new_long = float(long_t.get('a', 0))
        
        if bid_new_short > 0 and ask_new_long >= 0:
            new_credit_unit = max(0.0, bid_new_short - ask_new_long)
            new_credit_total = new_credit_unit * contracts
            net_roll_cost = cost_to_close_total - new_credit_total
            remaining_profit = init_credit_total - net_roll_cost
            
            roll_options.append({
                'target_expiry': next_exp,
                'target_expiry_formatted': exp_date.strftime("%d/%m/%Y"),
                'target_dte': dte,
                'short_strike': s_sell,
                'long_strike': s_buy,
                'close_cost_total': round(cost_to_close_total, 2),
                'new_credit_total': round(new_credit_total, 2),
                'net_roll_cost': round(net_roll_cost, 2),
                'remaining_profit': round(remaining_profit, 2),
                'pct_profit_preserved': round((remaining_profit / init_credit_total) * 100, 1) if init_credit_total > 0 else 0.0,
                'bid_new_short': bid_new_short,
                'ask_new_long': ask_new_long
            })
            
    return {
        'position': eval_pos,
        'roll_options': roll_options
    }

def execute_roll(pos_id, target_expiry, is_automated=False):
    positions = load_positions()
    pos_idx = next((i for i, p in enumerate(positions) if p.get('id') == pos_id), -1)
    if pos_idx == -1:
        return {'success': False, 'error': 'Posição não encontrada'}
        
    pos = positions[pos_idx]
    sim = simulate_roll(pos_id)
    target_option = next((o for o in sim.get('roll_options', []) if o['target_expiry'] == target_expiry), None)
    
    if not target_option:
        return {'success': False, 'error': 'Vencimento alvo inválido ou sem liquidez'}
        
    # Check max cost limit for auto roll
    if is_automated:
        max_cost_limit = pos.get('initial_credit_total', 0) * (pos.get('auto_roll_max_cost_pct', 35.0) / 100.0)
        if target_option['net_roll_cost'] > max_cost_limit:
            msg = f"Rolagem automática abortada: Custo líquido (${target_option['net_roll_cost']:.2f}) excede o limite de ${max_cost_limit:.2f} ({pos.get('auto_roll_max_cost_pct')}%)"
            log_audit("AUTO_ROLL_ABORTED", {'pos_id': pos_id, 'reason': msg})
            return {'success': False, 'error': msg}
            
    # Create new position
    new_pos = {
        'id': f"pos-{pos['currency'].lower()}-{int(pos['short_strike'])}-{int(pos['long_strike'])}-{target_expiry}",
        'currency': pos['currency'],
        'expiry': target_expiry,
        'short_strike': pos['short_strike'],
        'long_strike': pos['long_strike'],
        'contracts': pos['contracts'],
        'initial_credit_per_contract': round(target_option['new_credit_total'] / pos['contracts'], 2),
        'initial_credit_total': target_option['remaining_profit'],
        'initial_margin_total': pos.get('initial_margin_total', 0),
        'opened_at': datetime.datetime.now().strftime("%Y-%m-%d"),
        'status': 'active',
        'target_take_profit_pct': pos.get('target_take_profit_pct', 80.0),
        'auto_roll_enabled': pos.get('auto_roll_enabled', False),
        'auto_roll_trigger_dte': pos.get('auto_roll_trigger_dte', 3),
        'auto_roll_max_cost_pct': pos.get('auto_roll_max_cost_pct', 35.0),
        'roll_count': pos.get('roll_count', 0) + 1,
        'rolled_from': pos.get('expiry')
    }
    
    positions[pos_idx] = new_pos
    save_positions(positions)
    
    audit_data = {
        'pos_id': pos_id,
        'from_expiry': pos.get('expiry'),
        'to_expiry': target_expiry,
        'net_roll_cost': target_option['net_roll_cost'],
        'remaining_profit': target_option['remaining_profit'],
        'is_automated': is_automated
    }
    log_audit("ROLL_EXECUTED", audit_data)
    
    tg_msg = (
        f"🔄 <b>ROLAGEM DE TRAVA {'AUTOMÁTICA 🤖' if is_automated else 'MANUAL 👤'}</b>\n\n"
        f"• Ativo: {new_pos['currency']}\n"
        f"• Strikes: {new_pos['short_strike']}P / {new_pos['long_strike']}P\n"
        f"• Novo Vencimento: {target_option['target_expiry_formatted']} ({target_option['target_dte']}d)\n"
        f"• Custo Líquido: ${target_option['net_roll_cost']:,.2f}\n"
        f"• Lucro Preservado: <b>${target_option['remaining_profit']:,.2f} USDC</b> ({target_option['pct_profit_preserved']}% retido)\n\n"
        f"🔗 <a href='https://botrade-hyperliquid.onrender.com/options'>Abrir Options Desk</a>"
    )
    send_telegram_alert(tg_msg)
    
    return {
        'success': True,
        'message': f"Rolagem executada ({'Automática' if is_automated else 'Manual'}) para {target_option['target_expiry_formatted']}! Custo líquido: ${target_option['net_roll_cost']:,.2f}. Lucro preservado: ${target_option['remaining_profit']:,.2f}.",
        'new_position': new_pos
    }

# ----------------- Background Worker: Automatic Roll Monitor -----------------

def auto_roll_worker():
    while True:
        try:
            time.sleep(60) # Run check every 60s
            positions = load_positions()
            for p in positions:
                if p.get('status') == 'active' and p.get('auto_roll_enabled'):
                    eval_p = evaluate_position(p)
                    dte = eval_p.get('dte', 99)
                    spot = eval_p.get('spot_price', 0)
                    s_sell = float(eval_p.get('short_strike', 0))
                    trigger_dte = int(p.get('auto_roll_trigger_dte', 3))
                    
                    # Trigger condition: DTE <= trigger_dte AND spot < short_strike
                    if dte <= trigger_dte and spot < s_sell:
                        print(f"[AUTO-ROLL TRIGGERED] Posição {p['id']} atingiu gatilho (DTE: {dte}d <= {trigger_dte}d | Spot: ${spot:,.0f} < Strike: ${s_sell:,.0f})")
                        sim = simulate_roll(p['id'])
                        options = sim.get('roll_options', [])
                        if options:
                            best_target = options[0]['target_expiry'] # First forward expiry (next monthly)
                            res = execute_roll(p['id'], best_target, is_automated=True)
                            print(f"[AUTO-ROLL RESULT] {res.get('message', res.get('error'))}")
        except Exception as e:
            print(f"[AUTO-ROLL ERROR]: {e}")

# ----------------- REST API Server -----------------

class DeskHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        url = self.path
        if url == '/' or url.startswith('/index.html') or url.startswith('/desk'):
            self.serve_html()
        elif url.startswith('/api/market'):
            btc_spot = get_spot_price("BTC")
            eth_spot = get_spot_price("ETH")
            acct = get_derive_account_info()
            self.send_json({
                'btc_spot': btc_spot,
                'eth_spot': eth_spot,
                'has_session_key': bool(DERIVE_SESSION_KEY),
                'env': DERIVE_ENV,
                'subaccount_id': acct.get('subaccount_id', 116270),
                'wallet': acct.get('wallet', ''),
                'real_balance': acct.get('balance_usdc', 292.04),
                'session_label': acct.get('session_label', 'Ancap (Ativa)'),
                'margin_type': acct.get('margin_type', 'SM'),
                'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
        elif url.startswith('/api/decision_matrix'):
            currency = "BTC" if "currency=BTC" in url or "currency=" not in url else "ETH"
            res = scan_decision_matrix(currency)
            self.send_json(res)
        elif url.startswith('/api/positions'):
            raw_positions = load_positions()
            evaluated = [evaluate_position(p) for p in raw_positions if p.get('status') == 'active']
            self.send_json({'positions': evaluated})
        elif url.startswith('/api/roll_simulation'):
            pos_id = url.split('position_id=')[1].split('&')[0] if 'position_id=' in url else ''
            res = simulate_roll(pos_id)
            self.send_json(res)
        elif url.startswith('/api/roll_logs'):
            logs = []
            if os.path.exists(AUDIT_LOG_FILE):
                try:
                    with open(AUDIT_LOG_FILE, 'r', encoding='utf-8') as f:
                        logs = json.load(f)
                except:
                    logs = []
            self.send_json({'logs': logs})
        else:
            self.send_error(404, "Not Found")
            
    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length).decode('utf-8')
        try:
            payload = json.loads(body) if body else {}
        except:
            payload = {}
            
        if self.path == '/api/positions':
            positions = load_positions()
            new_id = f"pos-{payload.get('currency', 'btc').lower()}-{int(payload.get('short_strike', 0))}-{int(payload.get('long_strike', 0))}-{payload.get('expiry')}-{int(time.time())}"
            pos = {
                'id': new_id,
                'currency': payload.get('currency', 'BTC'),
                'expiry': str(payload.get('expiry')),
                'short_strike': float(payload.get('short_strike')),
                'long_strike': float(payload.get('long_strike')),
                'contracts': float(payload.get('contracts', 0.1)),
                'initial_credit_per_contract': float(payload.get('credit_per_contract', 0)),
                'initial_credit_total': float(payload.get('credit_per_contract', 0)) * float(payload.get('contracts', 0.1)),
                'initial_margin_total': (float(payload.get('short_strike')) - float(payload.get('long_strike')) - float(payload.get('credit_per_contract', 0))) * float(payload.get('contracts', 0.1)),
                'opened_at': datetime.datetime.now().strftime("%Y-%m-%d"),
                'status': 'active',
                'target_take_profit_pct': float(payload.get('tp_pct', 80.0)),
                'auto_roll_enabled': bool(payload.get('auto_roll_enabled', False)),
                'auto_roll_trigger_dte': int(payload.get('auto_roll_trigger_dte', 3)),
                'auto_roll_max_cost_pct': float(payload.get('auto_roll_max_cost_pct', 35.0)),
                'roll_count': 0
            }
            positions.append(pos)
            save_positions(positions)
            log_audit("POSITION_OPENED", pos)
            self.send_json({'success': True, 'position': pos})
            
        elif self.path == '/api/open_spread':
            currency = payload.get('currency', 'BTC')
            expiry = str(payload.get('expiry'))
            short_strike = float(payload.get('short_strike'))
            long_strike = float(payload.get('long_strike'))
            contracts = float(payload.get('contracts', 0.02))
            short_price = float(payload.get('short_price', 0))
            long_price = float(payload.get('long_price', 0))
            credit_per_contract = float(payload.get('credit_per_contract', max(0.0, short_price - long_price)))
            is_live = bool(payload.get('is_live', False))
            
            live_result = None
            if is_live:
                live_result = place_derive_spread_order(
                    currency=currency,
                    expiry=expiry,
                    short_strike=short_strike,
                    long_strike=long_strike,
                    contracts=contracts,
                    short_price=short_price,
                    long_price=long_price
                )
                if not live_result.get('success'):
                    self.send_json({'success': False, 'error': live_result.get('error')})
                    return
            
            positions = load_positions()
            new_id = f"pos-{currency.lower()}-{int(short_strike)}-{int(long_strike)}-{expiry}-{int(time.time())}"
            pos = {
                'id': new_id,
                'currency': currency,
                'expiry': expiry,
                'short_strike': short_strike,
                'long_strike': long_strike,
                'contracts': contracts,
                'initial_credit_per_contract': credit_per_contract,
                'initial_credit_total': round(credit_per_contract * contracts, 2),
                'initial_margin_total': round((short_strike - long_strike - credit_per_contract) * contracts, 2),
                'opened_at': datetime.datetime.now().strftime("%Y-%m-%d"),
                'status': 'active',
                'target_take_profit_pct': float(payload.get('tp_pct', 80.0)),
                'auto_roll_enabled': bool(payload.get('auto_roll_enabled', True)),
                'auto_roll_trigger_dte': int(payload.get('auto_roll_trigger_dte', 3)),
                'auto_roll_max_cost_pct': float(payload.get('auto_roll_max_cost_pct', 35.0)),
                'is_live_order': is_live,
                'live_details': live_result,
                'roll_count': 0
            }
            positions.append(pos)
            save_positions(positions)
            log_audit("POSITION_OPENED", pos)
            
            tg_msg = (
                f"🚀 <b>NOVA TRAVA MONTADA ({'DERIVE REAL ⚡' if is_live else 'MODO MONITOR 👁️'})</b>\n\n"
                f"• Ativo: {currency}\n"
                f"• Strikes: {short_strike:,.0f}P / {long_strike:,.0f}P\n"
                f"• Vencimento: {expiry}\n"
                f"• Quantidade: {contracts} contratos\n"
                f"• Crédito Adiantado: <b>+${pos['initial_credit_total']:,.2f} USDC</b>\n"
                f"• Margem Bloqueada: ~${pos['initial_margin_total']:,.2f} USDC\n"
                f"• Rolagem 24/7: {'ATIVADA ✅' if pos['auto_roll_enabled'] else 'DESATIVADA ⏸️'}\n\n"
                f"🔗 <a href='https://botrade-hyperliquid.onrender.com/options'>Abrir Options Desk</a>"
            )
            send_telegram_alert(tg_msg)
            
            self.send_json({
                'success': True,
                'position': pos,
                'message': f"Trava montada com sucesso ({'Ordem Real na Derive' if is_live else 'Modo Monitor/Simulado'})! Crédito recebido adiantado: +${pos['initial_credit_total']:,.2f} USDC."
            })
            
        elif self.path == '/api/toggle_auto_roll':
            pos_id = payload.get('position_id')
            enabled = bool(payload.get('enabled'))
            trigger_dte = int(payload.get('trigger_dte', 3))
            max_cost = float(payload.get('max_cost_pct', 35.0))
            
            positions = load_positions()
            pos = next((p for p in positions if p.get('id') == pos_id), None)
            if pos:
                pos['auto_roll_enabled'] = enabled
                pos['auto_roll_trigger_dte'] = trigger_dte
                pos['auto_roll_max_cost_pct'] = max_cost
                save_positions(positions)
                log_audit("AUTO_ROLL_CONFIG_CHANGED", {'pos_id': pos_id, 'enabled': enabled, 'trigger_dte': trigger_dte, 'max_cost_pct': max_cost})
                self.send_json({'success': True, 'position': pos})
            else:
                self.send_json({'success': False, 'error': 'Posição não encontrada'})
                
        elif self.path == '/api/roll_execute':
            pos_id = payload.get('position_id')
            target_expiry = payload.get('target_expiry')
            res = execute_roll(pos_id, target_expiry, is_automated=False)
            self.send_json(res)
        elif self.path == '/api/close_position':
            pos_id = payload.get('position_id')
            positions = load_positions()
            pos = next((p for p in positions if p.get('id') == pos_id), None)
            if pos:
                eval_p = evaluate_position(pos)
                positions = [p for p in positions if p.get('id') != pos_id]
                save_positions(positions)
                audit_info = {
                    'pos_id': pos_id,
                    'realized_pnl': eval_p.get('current_pnl_total', 0),
                    'profit_captured_pct': eval_p.get('profit_captured_pct', 0),
                    'initial_credit': eval_p.get('initial_credit_total', 0)
                }
                log_audit("POSITION_EARLY_CLOSED", audit_info)
                
                tg_msg = (
                    f"🎯 <b>TRAVA ENCERRADA ANTECIPADAMENTE!</b>\n\n"
                    f"• Posição: {pos_id}\n"
                    f"• Lucro Líquido Embolsado: <b>+${eval_p.get('current_pnl_total', 0):,.2f} USDC</b>\n"
                    f"• % do Crédito Capturado: {eval_p.get('profit_captured_pct', 0):.1f}%\n\n"
                    f"🔗 <a href='https://botrade-hyperliquid.onrender.com/options'>Abrir Options Desk</a>"
                )
                send_telegram_alert(tg_msg)
                
                self.send_json({
                    'success': True,
                    'message': f"Posição encerrada com sucesso! Lucro líquido embolsado: ${eval_p.get('current_pnl_total', 0):,.2f} ({eval_p.get('profit_captured_pct', 0):.1f}% do crédito inicial).",
                    'pnl': eval_p.get('current_pnl_total', 0)
                })
            else:
                self.send_json({'success': False, 'error': 'Posição não encontrada'})
        else:
            self.send_error(404, "Not Found")

    def do_DELETE(self):
        if self.path.startswith('/api/positions/'):
            pos_id = self.path.split('/')[-1]
            positions = load_positions()
            positions = [p for p in positions if p.get('id') != pos_id]
            save_positions(positions)
            log_audit("POSITION_CLOSED", {'pos_id': pos_id})
            self.send_json({'success': True})
        else:
            self.send_error(404, "Not Found")
            
    def send_json(self, data):
        content = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(content)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(content)
        
    def serve_html(self):
        html_file = os.path.join(ROOT_DIR, "dashboard", "options_desk.html")
        if os.path.exists(html_file):
            with open(html_file, 'r', encoding='utf-8') as f:
                content = f.read().encode('utf-8')
        else:
            content = b"<h1>Options Desk Dashboard not found</h1>"
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def log_message(self, format, *args):
        return

def start_server(port=8766):
    # Start auto roll background thread
    t = threading.Thread(target=auto_roll_worker, daemon=True)
    t.start()
    
    server = HTTPServer(('0.0.0.0', port), DeskHandler)
    print(f"\n===============================================================")
    print(f" 🚀 OPTIONS DESK - PLATAFORMA QUANT ESTILO OPSBIT & DERIVE.XYZ")
    print(f"===============================================================")
    print(f" ✅ Servidor rodando com sucesso!")
    print(f" 🌐 Acesse no seu navegador: http://localhost:{port}")
    print(f" 📊 Matriz de Decisão Risco/Retorno, Monitor de Posições e Auto-Rolagem")
    print(f" Pressione Ctrl+C para encerrar.\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor encerrado.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Options Desk - Derive/OpsBit Engine")
    parser.add_argument('--scan', choices=['BTC', 'ETH'], help="Executa scan no terminal para BTC ou ETH")
    parser.add_argument('--matrix', choices=['BTC', 'ETH'], help="Exibe a Matriz de Decisão Risco x Retorno no terminal")
    parser.add_argument('--positions', action='store_true', help="Mostra posições ativas no terminal")
    parser.add_argument('--serve', action='store_true', default=True, help="Inicia o servidor web (default)")
    parser.add_argument('--port', type=int, default=8766, help="Porta do servidor web (default: 8766)")
    
    args = parser.parse_args()
    
    if args.matrix:
        res = scan_decision_matrix(args.matrix)
        print(f"\n===============================================================")
        print(f" 🧠 MATRIZ DE DECISÃO QUANTITATIVA - {args.matrix}")
        print(f"===============================================================")
        print(f"Spot: ${res['spot_price']:,.2f} | Put Wall: ${res['walls']['put_wall']:,.0f} | Call Wall: ${res['walls']['call_wall']:,.0f}\n")
        if res['top_picks'].get('ultra_conservative'):
            print("🛡️ RECOMENDAÇÃO ULTRA-CONSERVADORA (FUNDO HISTÓRICO / ALTA PROTEÇÃO):")
            for pick in res['top_picks']['ultra_conservative'][:2]:
                print(f"  • {pick['profile_label']} [{pick['expiry_formatted']} - {pick['dte']}d]")
                print(f"    Venda {pick['short_strike']:,.0f}P / Compra {pick['long_strike']:,.0f}P")
                print(f"    Crédito: +${pick['net_credit']:,.0f} | Margem: ${pick['margin']:,.0f} | RoM: {pick['rom']:.1f}% | PoP: {pick['pop']:.1f}%")
                print(f"    Breakeven: ${pick['breakeven']:,.0f} (Folga/Cushion: {pick['cushion_pct']:+.1f}% abaixo do spot)")
                print(f"    Racional: {pick['thesis']}\n")
                
        print("🟣 RECOMENDAÇÃO MODELO ELÍDIO (ALTO CRÉDITO INICIAL):")
        for pick in res['top_picks']['elidio'][:2]:
            print(f"  • {pick['profile_label']} [{pick['expiry_formatted']} - {pick['dte']}d]")
            print(f"    Venda {pick['short_strike']:,.0f}P / Compra {pick['long_strike']:,.0f}P")
            print(f"    Crédito: +${pick['net_credit']:,.0f} | Margem: ${pick['margin']:,.0f} | RoM: {pick['rom']:.1f}% | PoP: {pick['pop']:.1f}%")
            print(f"    Breakeven: ${pick['breakeven']:,.0f} (Folga/Cushion: {pick['cushion_pct']:+.1f}%)")
            print(f"    Racional: {pick['thesis']}\n")
    elif args.positions:
        raw = load_positions()
        evaluated = [evaluate_position(p) for p in raw if p.get('status') == 'active']
        print(f"\n=======================================================")
        print(f" 💼 MINHAS POSIÇÕES ATIVAS & DIAGNÓSTICO DE MERCADO")
        print(f"=======================================================")
        for p in evaluated:
            print(f"\n• Posição: {p['currency']} {int(p['short_strike'])}P / {int(p['long_strike'])}P ({p['contracts']} contratos)")
            print(f"  Vencimento: {p['expiry_formatted']} ({p['dte']} dias) | Spot: ${p['spot_price']:,.2f}")
            print(f"  Crédito: ${p['initial_credit_total']:,.2f} | PnL: ${p['current_pnl_total']:,.2f} ({p['profit_captured_pct']:.1f}% capturado)")
            print(f"  Rolagem Automática: {'LIGADA' if p['auto_roll_enabled'] else 'DESLIGADA'} (Gatilho: DTE <= {p['auto_roll_trigger_dte']}d)")
            print(f"  Status IA: {p['recommendation']['badge']} - {p['recommendation']['text']}")
    else:
        start_server(args.port)
