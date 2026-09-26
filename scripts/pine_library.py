"""mcprule-compliant Pine strategies for batch discovery (botrade)."""

# Broker header MUST: commission=0? Video said commission 0.05% but mcprule says commission=0.
# Trader Dev get_pine_codegen_rules: commission=0, percent_of_equity=100, margin 100/100.
# quick_backtest description says commission 0.05% in parity — use mcprule commission=0 and let API parity apply.


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


def ema_cross(fast: int = 20, slow: int = 50, sl_pct: float = 2.0, tp_pct: float = 4.0) -> str:
    name = f"EMA {fast}/{slow} Cross"
    return HEADER.format(name=name) + f"""
fastLen = input.int({fast}, "Fast EMA")
slowLen = input.int({slow}, "Slow EMA")
slPct = input.float({sl_pct}, "SL %")
tpPct = input.float({tp_pct}, "TP %")

fastEma = ta.ema(close, fastLen)
slowEma = ta.ema(close, slowLen)
longCond = ta.crossover(fastEma, slowEma)
shortCond = ta.crossunder(fastEma, slowEma)

if longCond
    strategy.entry("L", strategy.long)
if shortCond
    strategy.entry("S", strategy.short)

if strategy.position_size > 0
    avg = strategy.position_avg_price
    strategy.exit("Lx", from_entry="L", stop=avg * (1 - slPct / 100), limit=avg * (1 + tpPct / 100))
if strategy.position_size < 0
    avg = strategy.position_avg_price
    strategy.exit("Sx", from_entry="S", stop=avg * (1 + slPct / 100), limit=avg * (1 - tpPct / 100))
"""


def rsi_reversion(length: int = 14, buy: float = 30, sell: float = 70, sl_pct: float = 2.0, tp_pct: float = 3.0) -> str:
    name = f"RSI Reversion {length}/{int(buy)}/{int(sell)}"
    return HEADER.format(name=name) + f"""
rsiLen = input.int({length}, "RSI")
buyLvl = input.float({buy}, "Buy below")
sellLvl = input.float({sell}, "Sell above")
slPct = input.float({sl_pct}, "SL %")
tpPct = input.float({tp_pct}, "TP %")

rsi = ta.rsi(close, rsiLen)
if rsi < buyLvl
    strategy.entry("L", strategy.long)
if rsi > sellLvl
    strategy.entry("S", strategy.short)
if strategy.position_size > 0
    avg = strategy.position_avg_price
    strategy.exit("Lx", from_entry="L", stop=avg * (1 - slPct / 100), limit=avg * (1 + tpPct / 100))
if strategy.position_size < 0
    avg = strategy.position_avg_price
    strategy.exit("Sx", from_entry="S", stop=avg * (1 + slPct / 100), limit=avg * (1 - tpPct / 100))
"""


def donchian_breakout(length: int = 20, sl_atr: float = 1.5, tp_atr: float = 3.0) -> str:
    name = f"Donchian Breakout {length}"
    return HEADER.format(name=name) + f"""
len = input.int({length}, "Channel length")
atrLen = input.int(14, "ATR")
slM = input.float({sl_atr}, "SL x ATR")
tpM = input.float({tp_atr}, "TP x ATR")

upper = ta.highest(high, len)
lower = ta.lowest(low, len)
a = ta.atr(atrLen)
longCond = close >= upper[1]
shortCond = close <= lower[1]
if longCond
    strategy.entry("L", strategy.long)
if shortCond
    strategy.entry("S", strategy.short)
if strategy.position_size > 0
    strategy.exit("Lx", from_entry="L", stop=close - slM * a, limit=close + tpM * a)
if strategy.position_size < 0
    strategy.exit("Sx", from_entry="S", stop=close + slM * a, limit=close - tpM * a)
"""


def bollinger_pullback(length: int = 20, mult: float = 2.0, sl_pct: float = 1.5, tp_pct: float = 2.5) -> str:
    name = f"BB Pullback {length}/{mult:g}"
    return HEADER.format(name=name) + f"""
len = input.int({length}, "Length")
mult = input.float({mult}, "Std dev")
slPct = input.float({sl_pct}, "SL %")
tpPct = input.float({tp_pct}, "TP %")

[middle, upper, lower] = ta.bb(close, len, mult)
longCond = low <= lower and close > lower
shortCond = high >= upper and close < upper
if longCond
    strategy.entry("L", strategy.long)
if shortCond
    strategy.entry("S", strategy.short)
if strategy.position_size > 0
    avg = strategy.position_avg_price
    strategy.exit("Lx", from_entry="L", stop=avg * (1 - slPct / 100), limit=avg * (1 + tpPct / 100))
if strategy.position_size < 0
    avg = strategy.position_avg_price
    strategy.exit("Sx", from_entry="S", stop=avg * (1 + slPct / 100), limit=avg * (1 - tpPct / 100))
"""


def macd_trend(fast: int = 12, slow: int = 26, signal: int = 9, sl_pct: float = 2.0, tp_pct: float = 3.0) -> str:
    name = f"MACD Trend {fast}/{slow}/{signal}"
    return HEADER.format(name=name) + f"""
fast = input.int({fast})
slow = input.int({slow})
sig = input.int({signal})
slPct = input.float({sl_pct}, "SL %")
tpPct = input.float({tp_pct}, "TP %")

[macd, signalLine, hist] = ta.macd(close, fast, slow, sig)
longCond = ta.crossover(macd, signalLine) and hist > hist[1]
shortCond = ta.crossunder(macd, signalLine) and hist < hist[1]
if longCond
    strategy.entry("L", strategy.long)
if shortCond
    strategy.entry("S", strategy.short)
if strategy.position_size > 0
    avg = strategy.position_avg_price
    strategy.exit("Lx", from_entry="L", stop=avg * (1 - slPct / 100), limit=avg * (1 + tpPct / 100))
if strategy.position_size < 0
    avg = strategy.position_avg_price
    strategy.exit("Sx", from_entry="S", stop=avg * (1 + slPct / 100), limit=avg * (1 - tpPct / 100))
"""


def fbr_v1() -> str:
    # from data/pine/FBR-01.pine — already validated by researcher (rejected on BTC)
    return open(
        r"C:\Users\seares\Desktop\botrade\data\pine\FBR-01.pine",
        encoding="utf-8",
    ).read()


LIBRARY = {
    "ema20-50": {"factory": lambda: ema_cross(20, 50), "family": "trend"},
    "ema9-21": {"factory": lambda: ema_cross(9, 21, 1.5, 3.0), "family": "trend"},
    "rsi14-30-70": {"factory": lambda: rsi_reversion(), "family": "mean-reversion"},
    "rsi14-25-75": {"factory": lambda: rsi_reversion(14, 25, 75, 1.5, 2.5), "family": "mean-reversion"},
    "donchian20": {"factory": lambda: donchian_breakout(20), "family": "breakout"},
    "donchian55": {"factory": lambda: donchian_breakout(55, 2.0, 4.0), "family": "breakout"},
    "bb20-2": {"factory": lambda: bollinger_pullback(), "family": "mean-reversion"},
    "macd": {"factory": lambda: macd_trend(), "family": "trend"},
    "fbr-v1": {"factory": fbr_v1, "family": "sweep"},
}

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT", "AVAXUSDT", "LINKUSDT", "ADAUSDT"]
TIMEFRAMES = ["1h", "4h"]
FROM = "2025-01-01"
TO = "2026-09-01"
