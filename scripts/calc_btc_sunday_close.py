import urllib.request
import json
import datetime
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# 1. Spot BTC
req = urllib.request.Request('https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT', headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req) as resp:
    spot = float(json.loads(resp.read().decode())['price'])

# 2. Daily candles
req_d = urllib.request.Request('https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1d&limit=250', headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req_d) as resp:
    candles_d = json.loads(resp.read().decode())
closes_d = [float(c[4]) for c in candles_d]

def calc_ema(series, period):
    k = 2.0 / (period + 1.0)
    ema = series[0]
    res = [ema]
    for p in series[1:]:
        ema = (p * k) + (ema * (1 - k))
        res.append(ema)
    return res

ema9_d = calc_ema(closes_d, 9)[-1]
ema21_d = calc_ema(closes_d, 21)[-1]
sma20_d = sum(closes_d[-20:]) / 20.0
sma50_d = sum(closes_d[-50:]) / 50.0

# 3. Weekly candles (BMSB: 20-week SMA + 21-week EMA)
req_w = urllib.request.Request('https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1w&limit=100', headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req_w) as resp:
    candles_w = json.loads(resp.read().decode())
closes_w = [float(c[4]) for c in candles_w]
sma20_w = sum(closes_w[-20:]) / 20.0
ema21_w = calc_ema(closes_w, 21)[-1]

# 4. Volume Map / Volume Profile
req_vol = urllib.request.Request('https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1h&limit=168', headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req_vol) as resp:
    candles_1h = json.loads(resp.read().decode())

# Calculate POC (Point of Control) for the week
price_buckets = {}
for c in candles_1h:
    p_typ = (float(c[2]) + float(c[3]) + float(c[4])) / 3.0
    bucket = round(p_typ / 250.0) * 250.0
    vol = float(c[5])
    price_buckets[bucket] = price_buckets.get(bucket, 0.0) + vol

poc_price = max(price_buckets.keys(), key=lambda k: price_buckets[k])

print("=" * 65)
print(" AUDITORIA DE FECHAMENTO SEMANAL DO BITCOIN (DOMINGO)")
print("=" * 65)
print(f"Preço Spot BTC Agora: ${spot:,.2f}")
print(f"\n--- NÍVEIS CHAVE DO SEMANAL (FECHAMENTO DE DOMINGO ÀS 21:00 BRT) ---")
print(f"• 21-Week EMA (BMSB Topo):     ${ema21_w:,.2f}")
print(f"• 20-Week SMA (BMSB Base):     ${sma20_w:,.2f}")
print(f"• Faixa do Bull Market Band:   ${min(sma20_w, ema21_w):,.2f} - ${max(sma20_w, ema21_w):,.2f}")
print(f"• Status contra o BMSB:        {'ACIMA (BULLISH 🐂)' if spot > max(sma20_w, ema21_w) else 'DENTRO OU ABAIXO (ALERTA ⚠️)'}")
print(f"• Abertura da Semana:          ${float(candles_w[-1][1]):,.2f}")

print(f"\n--- MÉDIAS MÓVEIS DIÁRIAS (OLIVER KELL / TREND) ---")
print(f"• EMA 9 Diária:                ${ema9_d:,.2f}")
print(f"• EMA 21 Diária:               ${ema21_d:,.2f}")
print(f"• SMA 20 Diária:               ${sma20_d:,.2f}")
print(f"• SMA 50 Diária:               ${sma50_d:,.2f}")

print(f"\n--- MAPA DE VOLUME (VOLUME PROFILE - 7 DIAS) ---")
print(f"• POC (Point of Control - Maior Volume): ${poc_price:,.2f}")
print("=" * 65)
