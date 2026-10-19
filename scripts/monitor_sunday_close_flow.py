import urllib.request
import json
import datetime
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Query recent 1m candles around 21:00 BRT (00:00 UTC)
url_1m = 'https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1m&limit=15'
req = urllib.request.Request(url_1m, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req) as resp:
    klines_1m = json.loads(resp.read().decode())

print("=" * 70)
print(f" MONITOR DE FLUXO DE VOLUME PÓS-FECHAMENTO (21:00 BRT / 00:00 UTC)")
print("=" * 70)

total_vol_recent = 0
total_buy_vol_recent = 0

for k in klines_1m:
    open_time = datetime.datetime.fromtimestamp(k[0]/1000, tz=datetime.timezone.utc)
    # Convert to BRT (UTC - 3)
    brt_time = open_time - datetime.timedelta(hours=3)
    o = float(k[1])
    h = float(k[2])
    l = float(k[3])
    c = float(k[4])
    vol = float(k[5])
    taker_buy_vol = float(k[9])
    taker_sell_vol = vol - taker_buy_vol
    buy_pct = (taker_buy_vol / vol * 100) if vol > 0 else 50.0
    delta = taker_buy_vol - taker_sell_vol
    
    total_vol_recent += vol
    total_buy_vol_recent += taker_buy_vol
    
    bar_dir = "🟢 ALTA" if c >= o else "🔴 BAIXA"
    print(f"[{brt_time.strftime('%H:%M')}] {bar_dir} | O: ${o:,.1f} | C: ${c:,.1f} | Vol: {vol:,.1f} BTC | Comprador: {buy_pct:.1f}% | Delta: {delta:+,.1f} BTC")

overall_buy_pct = (total_buy_vol_recent / total_vol_recent * 100) if total_vol_recent > 0 else 50.0
print("-" * 70)
print(f"Volume Total Últimos 15 min: {total_vol_recent:,.1f} BTC")
print(f"Pressão Compradora Agregada: {overall_buy_pct:.1f}% {'🟢 COMPRADORES NO CONTROLE' if overall_buy_pct > 52 else '🔴 VENDEDORES NO CONTROLE' if overall_buy_pct < 48 else '⚪ EQUILIBRADO'}")

# Also check 24h ticker for orderbook spread / 24h stats
url_ticker = 'https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT'
with urllib.request.urlopen(urllib.request.Request(url_ticker, headers={'User-Agent': 'Mozilla/5.0'})) as resp:
    tick = json.loads(resp.read().decode())
    print(f"Preço Spot Atual: ${float(tick['lastPrice']):,.2f}")
    print(f"Máxima 24h: ${float(tick['highPrice']):,.2f} | Mínima 24h: ${float(tick['lowPrice']):,.2f}")
print("=" * 70)
