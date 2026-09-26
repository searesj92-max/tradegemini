"""High-WR safe strategy library for botrade discovery batch 2."""

HEADER = """//@version=6
strategy("{name}",
  overlay=true,
  pyramiding=1,
  process_orders_on_close=true,
  commission_type=strategy.commission.percent,
  commission_value=0,
  initial_capital=10000,
  default_qty_type=strategy.percent_of_equity,
  default_qty_value=100,
  margin_long=100,
  margin_short=100)
"""


def trend_pullback(fast: int = 20, slow: int = 50, trend: int = 200, sl_atr: float = 2.0, tp_atr: float = 1.4) -> str:
    """Pullback into fast EMA while higher trend holds — higher WR via tight TP."""
    name = f"Trend Pullback {fast}/{slow}/EMA{trend}"
    return HEADER.format(name=name) + f"""
fastLen = input.int({fast})
slowLen = input.int({slow})
trendLen = input.int({trend})
rsiLen = input.int(14)
atrLen = input.int(14)
slM = input.float({sl_atr}, "SL x ATR")
tpM = input.float({tp_atr}, "TP x ATR")

f = ta.ema(close, fastLen)
s = ta.ema(close, slowLen)
t = ta.ema(close, trendLen)
r = ta.rsi(close, rsiLen)
a = ta.atr(atrLen)

upTrend = t > t[10] and close > t and f > s
dnTrend = t < t[10] and close < t and f < s

// touch fast EMA in trend direction (pullback), close confirms
longCond = upTrend and low <= f and close >= f and r < 55
shortCond = dnTrend and high >= f and close <= f and r > 45

if longCond
    strategy.entry("L", strategy.long)
if shortCond
    strategy.entry("S", strategy.short)

if strategy.position_size > 0
    avg = strategy.position_avg_price
    strategy.exit("Lx", from_entry="L", stop=avg - slM * a, limit=avg + tpM * a)
if strategy.position_size < 0
    avg = strategy.position_avg_price
    strategy.exit("Sx", from_entry="S", stop=avg + slM * a, limit=avg - tpM * a)
"""


def bb_regime_fade(length: int = 20, mult: float = 2.0, adx_max: float = 22.0, sl_atr: float = 1.8, tp_atr: float = 1.1) -> str:
    """Fade band edges only in non-trending regime (ADX filter). Tight TP toward mean = high WR."""
    name = f"BB Regime Fade {length}/{mult:g}/ADX<{int(adx_max)}"
    return HEADER.format(name=name) + f"""
len = input.int({length})
mult = input.float({mult})
adxLen = input.int(14)
adxMax = input.float({adx_max})
atrLen = input.int(14)
slM = input.float({sl_atr})
tpM = input.float({tp_atr})

[middle, upper, lower] = ta.bb(close, len, mult)
diPlus = ta.rma(ta.change(high), adxLen)
diMinus = ta.rma(ta.change(low), adxLen)
trs = ta.rma(ta.tr, adxLen)
plus = 100 * diPlus / trs
minus = 100 * diMinus / trs
adx = 100 * ta.rma(math.abs(plus - minus) / (plus + minus), adxLen)
a = ta.atr(atrLen)

rangeOk = adx < adxMax
// close back inside band after pierce — higher WR than catching the knife
longCond = rangeOk and low <= lower and close > lower
shortCond = rangeOk and high >= upper and close < upper

if longCond
    strategy.entry("L", strategy.long)
if shortCond
    strategy.entry("S", strategy.short)

if strategy.position_size > 0
    avg = strategy.position_avg_price
    // TP toward middle band approx via tight ATR target; SL beyond band
    strategy.exit("Lx", from_entry="L", stop=avg - slM * a, limit=avg + tpM * a)
if strategy.position_size < 0
    avg = strategy.position_avg_price
    strategy.exit("Sx", from_entry="S", stop=avg + slM * a, limit=avg - tpM * a)
"""


def rsi_trend_filtered(length: int = 14, buy: float = 35, sell: float = 65, ema_trend: int = 100, sl_atr: float = 2.0, tp_atr: float = 1.3) -> str:
    """RSI mean-reversion only in direction of higher EMA trend."""
    name = f"RSI Trend Filter {length}/{int(buy)}/{int(sell)}/EMA{ema_trend}"
    return HEADER.format(name=name) + f"""
rsiLen = input.int({length})
buyLvl = input.float({buy})
sellLvl = input.float({sell})
trendLen = input.int({ema_trend})
atrLen = input.int(14)
slM = input.float({sl_atr})
tpM = input.float({tp_atr})

r = ta.rsi(close, rsiLen)
t = ta.ema(close, trendLen)
a = ta.atr(atrLen)

// enter when RSI recovers from extreme in trend direction (not at extreme itself)
longCond = close > t and ta.crossover(r, buyLvl)
shortCond = close < t and ta.crossunder(r, sellLvl)

if longCond
    strategy.entry("L", strategy.long)
if shortCond
    strategy.entry("S", strategy.short)

if strategy.position_size > 0
    avg = strategy.position_avg_price
    strategy.exit("Lx", from_entry="L", stop=avg - slM * a, limit=avg + tpM * a)
if strategy.position_size < 0
    avg = strategy.position_avg_price
    strategy.exit("Sx", from_entry="S", stop=avg + slM * a, limit=avg - tpM * a)
"""


def squeeze_breakout(length: int = 20, mult: float = 1.5, lookback: int = 50, sl_atr: float = 1.5, tp_atr: float = 2.5) -> str:
    """Vol compression then expansion break — fewer, higher-quality trades."""
    name = f"Squeeze Breakout BB{length}/{mult:g}/W{lookback}"
    return HEADER.format(name=name) + f"""
len = input.int({length})
mult = input.float({mult})
lb = input.int({lookback})
atrLen = input.int(14)
slM = input.float({sl_atr})
tpM = input.float({tp_atr})

[middle, upper, lower] = ta.bb(close, len, mult)
width = (upper - lower) / middle
wMin = ta.lowest(width, lb)
a = ta.atr(atrLen)

// compression: width near recent min, then expansion candle
compressed = width <= wMin * 1.15
expandUp = compressed and close > upper and close > open
expandDn = compressed and close < lower and close < open

if expandUp
    strategy.entry("L", strategy.long)
if expandDn
    strategy.entry("S", strategy.short)

if strategy.position_size > 0
    avg = strategy.position_avg_price
    strategy.exit("Lx", from_entry="L", stop=avg - slM * a, limit=avg + tpM * a)
if strategy.position_size < 0
    avg = strategy.position_avg_price
    strategy.exit("Sx", from_entry="S", stop=avg + slM * a, limit=avg - tpM * a)
"""


def ema9_vwap_proxy(fast: int = 9, trend: int = 200, sl_atr: float = 1.5, tp_atr: float = 1.8) -> str:
    """Fast EMA pullback vs slow trend (VWAP-like mean proxy on crypto 24/7)."""
    name = f"EMA{fast} Pullback vs EMA{trend}"
    return HEADER.format(name=name) + f"""
fastLen = input.int({fast})
trendLen = input.int({trend})
atrLen = input.int(14)
slM = input.float({sl_atr})
tpM = input.float({tp_atr})

f = ta.ema(close, fastLen)
t = ta.ema(close, trendLen)
a = ta.atr(atrLen)

// reclaim fast EMA in direction of trend
longCond = ta.crossover(f, t) or (close > t and ta.crossover(close, f) and close[1] <= f[1])
shortCond = ta.crossunder(f, t) or (close < t and ta.crossunder(close, f) and close[1] >= f[1])

if longCond
    strategy.entry("L", strategy.long)
if shortCond
    strategy.entry("S", strategy.short)

if strategy.position_size > 0
    avg = strategy.position_avg_price
    strategy.exit("Lx", from_entry="L", stop=avg - slM * a, limit=avg + tpM * a)
if strategy.position_size < 0
    avg = strategy.position_avg_price
    strategy.exit("Sx", from_entry="S", stop=avg + slM * a, limit=avg - tpM * a)
"""


def failed_sweep(length: int = 20, sl_atr: float = 1.5, tp_atr: float = 2.0) -> str:
    """Liquidity sweep + reclaim of range — classic stop-hunt reverse."""
    name = f"Failed Sweep {length}"
    return HEADER.format(name=name) + f"""
len = input.int({length})
atrLen = input.int(14)
slM = input.float({sl_atr})
tpM = input.float({tp_atr})

hi = ta.highest(high, len)
lo = ta.lowest(low, len)
a = ta.atr(atrLen)

// sweep below range then close back inside
sweepLow = low < lo[1] and close > lo[1]
sweepHigh = high > hi[1] and close < hi[1]

if sweepLow
    strategy.entry("L", strategy.long)
if sweepHigh
    strategy.entry("S", strategy.short)

if strategy.position_size > 0
    avg = strategy.position_avg_price
    strategy.exit("Lx", from_entry="L", stop=avg - slM * a, limit=avg + tpM * a)
if strategy.position_size < 0
    avg = strategy.position_avg_price
    strategy.exit("Sx", from_entry="S", stop=avg + slM * a, limit=avg - tpM * a)
"""


HIGH_WR_LIBRARY = {
    "tp-ema200": {"factory": lambda: trend_pullback(20, 50, 200), "family": "trend-pullback"},
    "tp-ema100": {"factory": lambda: trend_pullback(20, 50, 100, 1.8, 1.2), "family": "trend-pullback"},
    "tp-fast": {"factory": lambda: trend_pullback(9, 21, 100, 1.6, 1.1), "family": "trend-pullback"},
    "bb-fade-adx": {"factory": lambda: bb_regime_fade(), "family": "regime-mr"},
    "bb-fade-4h": {"factory": lambda: bb_regime_fade(20, 2.0, 25.0, 2.0, 1.2), "family": "regime-mr"},
    "rsi-t100": {"factory": lambda: rsi_trend_filtered(), "family": "regime-mr"},
    "rsi-t200": {"factory": lambda: rsi_trend_filtered(14, 40, 60, 200, 2.2, 1.4), "family": "regime-mr"},
    "squeeze": {"factory": lambda: squeeze_breakout(20, 1.5, 50, 1.5, 2.5), "family": "vol-squeeze"},
    "ema9-t200": {"factory": lambda: ema9_vwap_proxy(), "family": "trend-pullback"},
    "sweep20": {"factory": lambda: failed_sweep(20), "family": "sweep"},
    "sweep55": {"factory": lambda: failed_sweep(55, 2.0, 2.5), "family": "sweep"},
}

# Safer matrix: 4h primary (fewer false signals), 1h secondary for TF stability check
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT", "AVAXUSDT", "LINKUSDT", "ADAUSDT"]
TIMEFRAMES = ["4h", "1h"]
FROM = "2025-01-01"
TO = "2026-09-01"
