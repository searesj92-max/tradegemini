import json, datetime

with open('dashboard/data.json', 'r') as f:
    data = json.load(f)

now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')

new_rows = [
    {
        'id': 'qm-vee-lo-btc-1h',
        'name': 'QM-VEE-LO-v2 - Pure Long Breakout Continuation BTCUSDT',
        'symbol': 'BTCUSDT',
        'timeframe': '1h',
        'source': 'greenfield quant mathematician cycle 05',
        'family': 'VEE-LO',
        'agent': 'researcher',
        'net_profit_pct': 4.44,
        'profit_factor': 1.40,
        'max_drawdown_pct': -4.66,
        'win_rate_pct': 70.83,
        'trades': 24,
        'sharpe': 1.53,
        'result_id': '01M39TNZFY8GTYGABTECBGGYVQ',
        'view_url': 'https://mcp-api.trader.dev/backtest/01M39TNZFY8GTYGABTECBGGYVQ',
        'curve': [],
        'verdict': 'Watchlist - PF 1.40, WR 70.8%, DD 4.66%, 24 trades.',
        'status': 'watchlist',
        'last_backtest': '2026-09-24',
        'pine_key': 'qm_vee_lo_v2_btc',
        'notes': 'Cycle 05 VEE-LO greenfield long-only SL 2.0xATR TP 1.5xATR. Positivo e clean.'
    },
    {
        'id': 'qm-vee-lo-eth-1h',
        'name': 'QM-VEE-LO-v2 - Pure Long Breakout Continuation ETHUSDT',
        'symbol': 'ETHUSDT',
        'timeframe': '1h',
        'source': 'greenfield quant mathematician cycle 05',
        'family': 'VEE-LO',
        'agent': 'researcher',
        'net_profit_pct': -10.48,
        'profit_factor': 0.53,
        'max_drawdown_pct': -12.34,
        'win_rate_pct': 45.83,
        'trades': 24,
        'sharpe': -2.83,
        'result_id': '01M39TP7H3H7FAMF63FZMSGZ14',
        'view_url': 'https://mcp-api.trader.dev/backtest/01M39TP7H3H7FAMF63FZMSGZ14',
        'curve': [],
        'verdict': 'Watchlist - PF 0.53, WR 45.8%, DD 12.34%, 24 trades. Negativo.',
        'status': 'watchlist',
        'last_backtest': '2026-09-24',
        'pine_key': 'qm_vee_lo_v2_eth',
        'notes': 'ETH negativo - viés de alta menos consistente em 1h com setup BTC/SOL.'
    },
    {
        'id': 'qm-vee-lo-sol-1h',
        'name': 'QM-VEE-LO-v2 - Pure Long Breakout Continuation SOLUSDT',
        'symbol': 'SOLUSDT',
        'timeframe': '1h',
        'source': 'greenfield quant mathematician cycle 05',
        'family': 'VEE-LO',
        'agent': 'researcher',
        'net_profit_pct': 20.30,
        'profit_factor': 1.96,
        'max_drawdown_pct': -4.88,
        'win_rate_pct': 73.53,
        'trades': 34,
        'sharpe': 3.38,
        'result_id': '01M39TPF5V4D3H4B5MMJWC3A6C',
        'view_url': 'https://mcp-api.trader.dev/backtest/01M39TPF5V4D3H4B5MMJWC3A6C',
        'curve': [],
        'verdict': 'Watchlist - PF 1.96, WR 73.5%, DD 4.88%, Sharpe 3.38, 34 trades. MELHOR símbolo.',
        'status': 'watchlist',
        'last_backtest': '2026-09-24',
        'pine_key': 'qm_vee_lo_v2_sol',
        'notes': 'Cycle 05 VEE-LO. 25W/9L em 34 trades. Avg win $166 vs avg loss -$236.'
    },
    {
        'id': 'qm-vee-lo-xrp-1h',
        'name': 'QM-VEE-LO-v2 - Pure Long Breakout Continuation XRPUSDT',
        'symbol': 'XRPUSDT',
        'timeframe': '1h',
        'source': 'greenfield quant mathematician cycle 05',
        'family': 'VEE-LO',
        'agent': 'researcher',
        'net_profit_pct': -0.30,
        'profit_factor': 0.99,
        'max_drawdown_pct': -12.42,
        'win_rate_pct': 54.29,
        'trades': 35,
        'sharpe': 0.12,
        'result_id': '01M39TPNZ2CE61C1Q49NJP5FGP',
        'view_url': 'https://mcp-api.trader.dev/backtest/01M39TPNZ2CE61C1Q49NJP5FGP',
        'curve': [],
        'verdict': 'Watchlist - PF 0.99, WR 54.3%, DD 12.42%, 35 trades. Quase break-even.',
        'status': 'watchlist',
        'last_backtest': '2026-09-24',
        'pine_key': 'qm_vee_lo_v2_xrp',
        'notes': 'Cycle 05 VEE-LO. 19W/16L em 35 trades. Avg trade -$0.84.'
    }
]

data['strategies'].extend(new_rows)
data['updated'] = now
data['stats']['total'] = len(data['strategies'])

with open('dashboard/data.json', 'w') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print('OK: ' + str(len(new_rows)) + ' linhas adicionadas. Total estratégias: ' + str(data['stats']['total']))

# Regenerar data.js
with open('dashboard/data.json', 'r') as f:
    jdata = json.load(f)

js = 'window.MISSION_DATA = ' + json.dumps(jdata, indent=2, ensure_ascii=False) + ';\n'

with open('dashboard/data.js', 'w') as f:
    f.write(js)

print('data.js regenerado')
