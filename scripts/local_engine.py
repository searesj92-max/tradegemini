"""Local OHLCV download + indicator + strategy backtest engine (free, no credits)."""
from __future__ import annotations

import json
import math
import ssl
import time
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

ROOT = Path(r"C:\Users\seares\Desktop\botrade")
DATA_DIR = ROOT / "data" / "ohlcv"
DATA_DIR.mkdir(parents=True, exist_ok=True)
CTX = ssl.create_default_context()

# window aligned with Trader Dev batches
FROM_MS = 1735689600000  # 2025-01-01 00:00:00 UTC
TO_MS = 1788249600000    # 2026-09-01 00:00:00 UTC


def _get(url: str, timeout: float = 30.0):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 botrade-local"})
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
        return json.loads(r.read().decode())


def download_binance_klines(symbol: str, interval: str = "4h") -> list[list]:
    """Return raw kline arrays [[openTime, o,h,l,c,v, ...], ...]."""
    out: list[list] = []
    start = FROM_MS
    while start < TO_MS:
        url = (
            f"https://api.binance.com/api/v3/klines"
            f"?symbol={symbol}&interval={interval}&startTime={start}&endTime={TO_MS}&limit=1000"
        )
        batch = _get(url)
        if not batch:
            break
        out.extend(batch)
        last = int(batch[-1][0])
        nxt = last + 1
        if nxt <= start:
            break
        start = nxt
        if len(batch) < 1000:
            break
        time.sleep(0.12)
    return out


def download_bybit_klines(symbol: str, interval: str = "240") -> list[list]:
    """Bybit v5 klines -> same shape as binance-ish: [ts,o,h,l,c,vol, ...]."""
    out: list[list] = []
    cursor = ""
    while True:
        url = (
            f"https://api.bybit.com/v5/market/kline?category=linear"
            f"&symbol={symbol}&interval={interval}&start={FROM_MS}&end={TO_MS}&limit=1000"
        )
        if cursor:
            url += f"&cursor={cursor}"
        data = _get(url)
        lst = (data.get("result") or {}).get("list") or []
        if not lst:
            break
        # bybit returns newest first: [start, open, high, low, close, volume, turnover]
        for row in lst:
            out.append([
                int(row[0]), float(row[1]), float(row[2]), float(row[3]),
                float(row[4]), float(row[5]),
            ])
        cursor = (data.get("result") or {}).get("nextPageCursor") or ""
        if not cursor:
            break
        time.sleep(0.12)
    out.sort(key=lambda r: int(r[0]))
    return out


def load_ohlcv(provider: str, symbol: str, interval: str = "4h", refresh: bool = False) -> list[dict]:
    """Cache and return bars: {t,o,h,l,c,v}."""
    safe = f"{provider}_{symbol}_{interval}.json"
    path = DATA_DIR / safe
    if path.exists() and not refresh:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if raw:
            return raw
    if provider == "binance":
        iv = interval
        raw_k = download_binance_klines(symbol, iv)
        bars = [
            {"t": int(k[0]), "o": float(k[1]), "h": float(k[2]), "l": float(k[3]), "c": float(k[4]), "v": float(k[5])}
            for k in raw_k
        ]
    else:
        iv = {"15m": "15", "1h": "60", "2h": "120", "4h": "240", "1d": "D"}.get(interval, interval)
        raw_k = download_bybit_klines(symbol, iv)
        bars = [
            {"t": int(k[0]), "o": float(k[1]), "h": float(k[2]), "l": float(k[3]), "c": float(k[4]), "v": float(k[5])}
            for k in raw_k
        ]
    path.write_text(json.dumps(bars), encoding="utf-8")
    return bars


# ---------- indicators (Pine-compatible enough) ----------

def ema(vals: list[float], n: int) -> list[float | None]:
    if n <= 0 or not vals:
        return []
    k = 2.0 / (n + 1.0)
    out: list[float | None] = [None] * len(vals)
    # seed with SMA of first n
    if len(vals) < n:
        return out
    s = sum(vals[:n])
    out[n - 1] = s / n
    prev = out[n - 1]
    for i in range(n, len(vals)):
        prev = vals[i] * k + prev * (1 - k)
        out[i] = prev
    return out


def rsi(vals: list[float], n: int = 14) -> list[float | None]:
    out: list[float | None] = [None] * len(vals)
    if len(vals) <= n:
        return out
    gains = 0.0
    losses = 0.0
    for i in range(1, n + 1):
        d = vals[i] - vals[i - 1]
        if d >= 0:
            gains += d
        else:
            losses -= d
    ag = gains / n
    al = losses / n
    out[n] = 100.0 if al == 0 else 100.0 - 100.0 / (1.0 + ag / al)
    for i in range(n + 1, len(vals)):
        d = vals[i] - vals[i - 1]
        g = d if d > 0 else 0.0
        l = -d if d < 0 else 0.0
        ag = (ag * (n - 1) + g) / n
        al = (al * (n - 1) + l) / n
        out[i] = 100.0 if al == 0 else 100.0 - 100.0 / (1.0 + ag / al)
    return out


def atr(bars: list[dict], n: int = 14) -> list[float | None]:
    out: list[float | None] = [None] * len(bars)
    if len(bars) <= n:
        return out
    trs = [0.0] * len(bars)
    for i, b in enumerate(bars):
        if i == 0:
            trs[i] = b["h"] - b["l"]
        else:
            pc = bars[i - 1]["c"]
            trs[i] = max(b["h"] - b["l"], abs(b["h"] - pc), abs(b["l"] - pc))
    # Wilder smoothing
    s = sum(trs[1 : n + 1])
    out[n] = s / n
    for i in range(n + 1, len(bars)):
        out[i] = (out[i - 1] * (n - 1) + trs[i]) / n
    return out


def sma(vals: list[float], n: int) -> list[float | None]:
    out: list[float | None] = [None] * len(vals)
    if len(vals) < n:
        return out
    s = sum(vals[:n])
    out[n - 1] = s / n
    for i in range(n, len(vals)):
        s += vals[i] - vals[i - n]
        out[i] = s / n
    return out


def stdev(vals: list[float], n: int) -> list[float | None]:
    out: list[float | None] = [None] * len(vals)
    for i in range(n - 1, len(vals)):
        window = vals[i - n + 1 : i + 1]
        m = sum(window) / n
        var = sum((x - m) ** 2 for x in window) / n  # Pine ta.stdev is population? actually sample n-1 in TV — use n
        # TradingView ta.stdev uses population (n)
        out[i] = math.sqrt(var)
    return out


def highest(bars: list[dict], n: int, key: str = "h") -> list[float | None]:
    out: list[float | None] = [None] * len(bars)
    for i in range(len(bars)):
        if i < n - 1:
            continue
        out[i] = max(bars[j][key] for j in range(i - n + 1, i + 1))
    return out


def lowest(bars: list[dict], n: int, key: str = "l") -> list[float | None]:
    out: list[float | None] = [None] * len(bars)
    for i in range(len(bars)):
        if i < n - 1:
            continue
        out[i] = min(bars[j][key] for j in range(i - n + 1, i + 1))
    return out


def crossover(a: list[float | None], b: list[float | None] | float, i: int) -> bool:
    if i < 1:
        return False
    if isinstance(b, list):
        if a[i] is None or a[i - 1] is None or b[i] is None or b[i - 1] is None:
            return False
        return a[i - 1] <= b[i - 1] and a[i] > b[i]
    if a[i] is None or a[i - 1] is None:
        return False
    return a[i - 1] <= b and a[i] > b


def crossunder(a: list[float | None], b: list[float | None] | float, i: int) -> bool:
    if i < 1:
        return False
    if isinstance(b, list):
        if a[i] is None or a[i - 1] is None or b[i] is None or b[i - 1] is None:
            return False
        return a[i - 1] >= b[i - 1] and a[i] < b[i]
    if a[i] is None or a[i - 1] is None:
        return False
    return a[i - 1] >= b and a[i] < b


def adx(bars: list[dict], n: int = 14) -> list[float | None]:
    out: list[float | None] = [None] * len(bars)
    if len(bars) <= 2 * n:
        return out
    tr_list = [0.0] * len(bars)
    plus_dm = [0.0] * len(bars)
    minus_dm = [0.0] * len(bars)
    for i in range(1, len(bars)):
        h = bars[i]["h"]
        l = bars[i]["l"]
        ph = bars[i - 1]["h"]
        pl = bars[i - 1]["l"]
        pc = bars[i - 1]["c"]
        tr_list[i] = max(h - l, abs(h - pc), abs(l - pc))
        up_move = h - ph
        down_move = pl - l
        plus_dm[i] = up_move if (up_move > down_move and up_move > 0) else 0.0
        minus_dm[i] = down_move if (down_move > up_move and down_move > 0) else 0.0

    tr_smooth = sum(tr_list[1 : n + 1])
    pdm_smooth = sum(plus_dm[1 : n + 1])
    mdm_smooth = sum(minus_dm[1 : n + 1])

    dx_list = [0.0] * len(bars)
    for i in range(n + 1, len(bars)):
        tr_smooth = tr_smooth - (tr_smooth / n) + tr_list[i]
        pdm_smooth = pdm_smooth - (pdm_smooth / n) + plus_dm[i]
        mdm_smooth = mdm_smooth - (mdm_smooth / n) + minus_dm[i]
        pdi = 100.0 * (pdm_smooth / tr_smooth) if tr_smooth > 0 else 0.0
        mdi = 100.0 * (mdm_smooth / tr_smooth) if tr_smooth > 0 else 0.0
        diff = abs(pdi - mdi)
        total = pdi + mdi
        dx_list[i] = 100.0 * (diff / total) if total > 0 else 0.0

    if len(bars) > 2 * n:
        adx_smooth = sum(dx_list[n + 1 : 2 * n + 1]) / n
        out[2 * n] = adx_smooth
        for i in range(2 * n + 1, len(bars)):
            adx_smooth = (adx_smooth * (n - 1) + dx_list[i]) / n
            out[i] = adx_smooth
    return out


def supertrend(bars: list[dict], period: int = 10, multiplier: float = 3.0) -> tuple[list[float | None], list[int]]:
    n = len(bars)
    trend = [1] * n
    st_line: list[float | None] = [None] * n
    a = atr(bars, period)
    if n <= period:
        return st_line, trend

    upper_band = [0.0] * n
    lower_band = [0.0] * n
    for i in range(period, n):
        hl2 = (bars[i]["h"] + bars[i]["l"]) / 2.0
        atr_val = a[i] or 0.0
        basic_upper = hl2 + multiplier * atr_val
        basic_lower = hl2 - multiplier * atr_val

        prev_c = bars[i - 1]["c"]
        prev_upper = upper_band[i - 1]
        prev_lower = lower_band[i - 1]

        upper_band[i] = basic_upper if (basic_upper < prev_upper or prev_c > prev_upper) else prev_upper
        lower_band[i] = basic_lower if (basic_lower > prev_lower or prev_c < prev_lower) else prev_lower

        prev_trend = trend[i - 1]
        curr_c = bars[i]["c"]
        if prev_trend == 1:
            trend[i] = -1 if curr_c < lower_band[i] else 1
        else:
            trend[i] = 1 if curr_c > upper_band[i] else -1

        st_line[i] = lower_band[i] if trend[i] == 1 else upper_band[i]

    return st_line, trend


def keltner_channel(bars: list[dict], n: int = 20, mult: float = 1.5) -> tuple[list[float | None], list[float | None], list[float | None]]:
    c = [b["c"] for b in bars]
    mid = ema(c, n)
    a = atr(bars, n)
    upper: list[float | None] = [None] * len(bars)
    lower: list[float | None] = [None] * len(bars)
    for i in range(len(bars)):
        if mid[i] is not None and a[i] is not None:
            upper[i] = mid[i] + mult * a[i]
            lower[i] = mid[i] - mult * a[i]
    return mid, upper, lower


def bollinger_bands(c: list[float], n: int = 20, mult: float = 2.0) -> tuple[list[float | None], list[float | None], list[float | None]]:
    mid = sma(c, n)
    sd = stdev(c, n)
    upper: list[float | None] = [None] * len(c)
    lower: list[float | None] = [None] * len(c)
    for i in range(len(c)):
        if mid[i] is not None and sd[i] is not None:
            upper[i] = mid[i] + mult * sd[i]
            lower[i] = mid[i] - mult * sd[i]
    return mid, upper, lower


@dataclass
class Trade:
    side: str  # long/short
    entry_i: int
    entry_price: float
    exit_i: int | None = None
    exit_price: float | None = None
    reason: str = ""
    pnl_pct: float = 0.0


@dataclass
class Result:
    strategy: str
    symbol: str
    timeframe: str
    net_profit_pct: float = 0.0
    profit_factor: float = 0.0
    max_drawdown_pct: float = 0.0
    win_rate_pct: float = 0.0
    trades: int = 0
    wins: int = 0
    losses: int = 0
    avg_trade_pct: float = 0.0
    long_trades: int = 0
    short_trades: int = 0
    equity: list[float] = field(default_factory=list)
    trades_detail: list[dict] = field(default_factory=list)
    source: str = "local"


def _signal_fn(name: str, bars: list[dict]) -> Callable[[int], str | None]:
    """Return side 'long'/'short'/None for flat-state entries on bar i (close)."""
    c = [b["c"] for b in bars]
    h = [b["h"] for b in bars]
    lo = [b["l"] for b in bars]
    o = [b["o"] for b in bars]
    r = rsi(c, 14)
    a = atr(bars, 14)

    if name in ("rsi-t200b", "rsi-t200", "rsi-t100"):
        # params
        buy, sell, ema_n, _sl, _tp = {
            "rsi-t200b": (35.0, 65.0, 200, 2.5, 1.6),
            "rsi-t200": (40.0, 60.0, 200, 2.2, 1.4),
            "rsi-t100": (40.0, 60.0, 100, 2.0, 1.3),
        }[name]
        t = ema(c, ema_n)

        def sig(i: int, r=r, t=t, buy=buy, sell=sell) -> str | None:
            if r[i] is None or t[i] is None:
                return None
            if c[i] > t[i] and crossover(r, buy, i):
                return "long"
            if c[i] < t[i] and crossunder(r, sell, i):
                return "short"
            return None

        return sig

    if name == "rsi-t-l":
        t = ema(c, 200)

        def sig(i: int, r=r, t=t) -> str | None:
            if i < 10 or r[i] is None or t[i] is None or t[i - 10] is None:
                return None
            up = t[i] > t[i - 10] and c[i] > t[i]
            if up and crossover(r, 40.0, i):
                return "long"
            return None

        return sig

    if name == "squeeze":
        # BB 20 / 1.5
        n, mult, lb = 20, 1.5, 50
        mid = sma(c, n)
        sd = stdev(c, n)
        upper = [None] * len(c)
        lower = [None] * len(c)
        width = [None] * len(c)
        for i in range(len(c)):
            if mid[i] is None or sd[i] is None:
                continue
            upper[i] = mid[i] + mult * sd[i]
            lower[i] = mid[i] - mult * sd[i]
            if mid[i]:
                width[i] = (upper[i] - lower[i]) / mid[i]
        wmin = [None] * len(c)
        for i in range(len(c)):
            if i < lb - 1 or width[i] is None:
                continue
            wmin[i] = min(width[j] for j in range(i - lb + 1, i + 1) if width[j] is not None)

        def sig(i: int, upper=upper, lower=lower, width=width, wmin=wmin) -> str | None:
            if None in (upper[i], lower[i], width[i], wmin[i]):
                return None
            compressed = width[i] <= wmin[i] * 1.15
            if compressed and c[i] > upper[i] and c[i] > o[i]:
                return "long"
            if compressed and c[i] < lower[i] and c[i] < o[i]:
                return "short"
            return None

        return sig

    if name == "gold-pb":
        f = ema(c, 9)
        s = ema(c, 21)
        t = ema(c, 200)

        def sig(i: int, f=f, s=s, t=t, r=r) -> str | None:
            if None in (f[i], s[i], t[i], r[i]):
                return None
            up = f[i] > s[i] and c[i] > t[i]
            if up and lo[i] <= f[i] and c[i] >= f[i] and r[i] < 55:
                return "long"
            return None

        return sig

    if name == "mom-dip":
        ret = [0.0] + [c[i] - c[i - 1] for i in range(1, len(c))]
        mu = sma(ret, 20)
        sd = stdev(ret, 20)
        t = ema(c, 200)
        zz: list[float | None] = [None] * len(c)
        for i in range(len(c)):
            if mu[i] is None or sd[i] is None:
                continue
            zz[i] = 0.0 if sd[i] == 0 else (ret[i] - mu[i]) / sd[i]

        def sig(i: int, zz=zz, t=t) -> str | None:
            if i < 20 or zz[i] is None or zz[i - 1] is None or t[i] is None or t[i - 20] is None:
                return None
            up = t[i] > t[i - 20] and c[i] > t[i]
            if up and crossunder(zz, -1.2, i):
                return "long"
            return None

        return sig

    if name == "ema20-50":
        f = ema(c, 20)
        s = ema(c, 50)

        def sig(i: int, f=f, s=s) -> str | None:
            if crossover(f, s, i):
                return "long"
            if crossunder(f, s, i):
                return "short"
            return None

        return sig

    if name == "ema9-21":
        f = ema(c, 9)
        s = ema(c, 21)

        def sig(i: int, f=f, s=s) -> str | None:
            if crossover(f, s, i):
                return "long"
            if crossunder(f, s, i):
                return "short"
            return None

        return sig

    if name == "bull-pb":
        t = ema(c, 200)
        f = ema(c, 20)
        e50 = ema(c, 50)
        r = rsi(c, 14)

        def sig(i: int, t=t, f=f, e50=e50, r=r) -> str | None:
            if i < 20 or None in (t[i], t[i - 20], f[i], e50[i], r[i]):
                return None
            up = t[i] > t[i - 20] and c[i] > t[i] and f[i] > e50[i]
            if up and lo[i] <= f[i] and c[i] >= f[i] and r[i] <= 45 and c[i] > c[i - 1]:
                return "long"
            return None

        return sig

    if name == "hh-brk":
        hi = highest(bars, 20, "h")
        t = ema(c, 50)

        def sig(i: int, hi=hi, t=t) -> str | None:
            if i < 1 or hi[i - 1] is None or t[i] is None:
                return None
            if c[i] > hi[i - 1] and c[i] > t[i] and crossover(c, [x for x in [None] * i + [None]], i):
                pass
            # ta.crossover(close, hi[1]) — series of prior highest
            if c[i] > hi[i - 1] and c[i] > t[i] and (i >= 1 and c[i - 1] <= hi[i - 1]):
                # approximate: prev close not above prev highest, now is
                if c[i - 1] <= (hi[i - 2] if i >= 2 and hi[i - 2] is not None else hi[i - 1]):
                    return "long"
            return None

        return sig

    if name == "dc-long":
        hi = highest(bars, 20, "h")
        t = ema(c, 100)
        # simplified DMI
        def sig(i: int, hi=hi, t=t) -> str | None:
            if i < 15 or hi[i - 1] is None or t[i] is None:
                return None
            if c[i] > hi[i - 1] and c[i] > t[i]:
                return "long"
            return None

        return sig

    if name == "confluence-6p":
        e200 = ema(c, 200)
        e21 = ema(c, 21)
        e9 = ema(c, 9)
        dh = highest(bars, 20, "h")
        v = [b["v"] for b in bars]
        v_ma = sma(v, 20)

        def sig(i: int, e200=e200, e21=e21, e9=e9, r=r, dh=dh, v=v, v_ma=v_ma) -> str | None:
            if i < 200 or None in (e200[i], e21[i], e9[i], r[i], dh[i - 1]):
                return None
            macro_bull = c[i] > e200[i]
            fast_bull = e9[i] > e21[i]
            rsi_ok = 50.0 <= r[i] <= 72.0
            vol_ok = (v[i] >= (v_ma[i] or 0) * 0.85) if v_ma[i] else True
            donchian_break = (c[i] >= dh[i - 1] * 0.99)
            triggered = crossover(e9, e21, i) or crossover(r, 50.0, i) or (c[i] >= dh[i - 1] and c[i - 1] < dh[i - 1])
            if macro_bull and fast_bull and rsi_ok and vol_ok and donchian_break and triggered:
                return "long"
            return None

        return sig

    if name == "supertrend-adx":
        _st_line, trend = supertrend(bars, 10, 3.0)
        adx_val = adx(bars, 14)
        e200 = ema(c, 200)

        def sig(i: int, trend=trend, adx_val=adx_val, e200=e200) -> str | None:
            if i < 30 or None in (adx_val[i], e200[i]):
                return None
            strong_trend = (adx_val[i] or 0) >= 22.0
            if strong_trend and trend[i] == 1 and trend[i - 1] == -1 and c[i] > e200[i]:
                return "long"
            if strong_trend and trend[i] == -1 and trend[i - 1] == 1 and c[i] < e200[i]:
                return "short"
            return None

        return sig

    if name == "keltner-bb-squeeze":
        _k_mid, k_up, k_low = keltner_channel(bars, 20, 1.5)
        _b_mid, b_up, b_low = bollinger_bands(c, 20, 2.0)
        squeeze = [
            (b_up[j] is not None and k_up[j] is not None and b_up[j] < k_up[j] and b_low[j] > k_low[j])
            for j in range(len(bars))
        ]

        def sig(i: int, b_up=b_up, b_low=b_low, squeeze=squeeze) -> str | None:
            if i < 25 or None in (b_up[i], b_low[i]):
                return None
            was_squeezed = any(squeeze[i - k] for k in range(1, 6))
            if was_squeezed:
                if c[i] > b_up[i] and c[i] > o[i]:
                    return "long"
                if c[i] < b_low[i] and c[i] < o[i]:
                    return "short"
            return None

        return sig

    if name == "dip-pullback-v2":
        e200 = ema(c, 200)
        e50 = ema(c, 50)
        fast_r = rsi(c, 7)

        def sig(i: int, e200=e200, e50=e50, fast_r=fast_r) -> str | None:
            if i < 200 or None in (e200[i], e50[i], fast_r[i]):
                return None
            uptrend = c[i] > e200[i] and e50[i] > e200[i]
            dip_bounce = crossover(fast_r, 32.0, i)
            bull_candle = c[i] > o[i]
            if uptrend and dip_bounce and bull_candle:
                return "long"
            return None

        return sig

    if name == "waddah-attar-explosion":
        e20 = ema(c, 20)
        e40 = ema(c, 40)
        _bb_mid, bb_up, bb_low = bollinger_bands(c, 20, 2.0)
        atr_100 = atr(bars, 100)
        e200 = ema(c, 200)

        macd_diff = [
            (e20[j] - e40[j]) if (e20[j] is not None and e40[j] is not None) else None
            for j in range(len(bars))
        ]
        expl_line = [
            (bb_up[j] - bb_low[j]) if (bb_up[j] is not None and bb_low[j] is not None) else None
            for j in range(len(bars))
        ]
        dead_zone = [
            (atr_100[j] * 3.7) if atr_100[j] is not None else None
            for j in range(len(bars))
        ]

        def sig(i: int, macd_diff=macd_diff, expl_line=expl_line, dead_zone=dead_zone, e200=e200) -> str | None:
            if i < 105 or None in (macd_diff[i], expl_line[i], dead_zone[i], e200[i]):
                return None
            m = macd_diff[i]
            prev_m = macd_diff[i - 1] or 0.0
            e = expl_line[i]
            d = dead_zone[i]
            if m > 0 and m > e and m > d and m > prev_m and c[i] > e200[i]:
                if prev_m <= (expl_line[i - 1] or 0.0) or prev_m <= (dead_zone[i - 1] or 0.0):
                    return "long"
            if m < 0 and abs(m) > e and abs(m) > d and abs(m) > abs(prev_m) and c[i] < e200[i]:
                if abs(prev_m) <= (expl_line[i - 1] or 0.0) or abs(prev_m) <= (dead_zone[i - 1] or 0.0):
                    return "short"
            return None

        return sig

    if name == "chandelier-exit":
        hh22 = highest(bars, 22, "h")
        ll22 = lowest(bars, 22, "l")
        a22 = atr(bars, 22)
        e200 = ema(c, 200)

        def sig(i: int, hh22=hh22, ll22=ll22, a22=a22, e200=e200) -> str | None:
            if i < 30 or None in (hh22[i - 1], ll22[i - 1], a22[i], e200[i]):
                return None
            long_stop = hh22[i - 1] - 3.0 * a22[i]
            short_stop = ll22[i - 1] + 3.0 * a22[i]

            prev_long_stop = (hh22[i - 2] if i >= 2 and hh22[i - 2] is not None else hh22[i - 1]) - 3.0 * (a22[i - 1] or a22[i])
            prev_short_stop = (ll22[i - 2] if i >= 2 and ll22[i - 2] is not None else ll22[i - 1]) + 3.0 * (a22[i - 1] or a22[i])

            if c[i] > long_stop and c[i - 1] <= prev_long_stop and c[i] > e200[i] and c[i] > o[i]:
                return "long"
            if c[i] < short_stop and c[i - 1] >= prev_short_stop and c[i] < e200[i] and c[i] < o[i]:
                return "short"
            return None

        return sig

    if name == "stoch-rsi-t200":
        e200 = ema(c, 200)
        r = rsi(c, 14)

        stoch_k = [None] * len(c)
        for i in range(14, len(c)):
            window = [r[j] for j in range(i - 13, i + 1) if r[j] is not None]
            if len(window) == 14:
                min_r = min(window)
                max_r = max(window)
                diff = max_r - min_r
                stoch_k[i] = ((r[i] - min_r) / diff * 100.0) if diff > 0 else 50.0

        smooth_k: list[float | None] = [None] * len(c)
        for i in range(len(c)):
            w = [stoch_k[j] for j in range(max(0, i - 2), i + 1) if stoch_k[j] is not None]
            if len(w) == 3:
                smooth_k[i] = sum(w) / 3.0

        smooth_d: list[float | None] = [None] * len(c)
        for i in range(len(c)):
            w = [smooth_k[j] for j in range(max(0, i - 2), i + 1) if smooth_k[j] is not None]
            if len(w) == 3:
                smooth_d[i] = sum(w) / 3.0

        def sig(i: int, smooth_k=smooth_k, smooth_d=smooth_d, e200=e200) -> str | None:
            if i < 200 or None in (smooth_k[i], smooth_k[i - 1], smooth_d[i], smooth_d[i - 1], e200[i]):
                return None
            if c[i] > e200[i] and smooth_k[i - 1] <= 25.0 and crossover(smooth_k, smooth_d, i) and c[i] > o[i]:
                return "long"
            if c[i] < e200[i] and smooth_k[i - 1] >= 75.0 and crossunder(smooth_k, smooth_d, i) and c[i] < o[i]:
                return "short"
            return None

        return sig

    raise KeyError(f"unknown strategy {name}")


def _sl_tp(name: str) -> tuple[float, float]:
    return {
        "rsi-t200b": (2.5, 1.6),
        "rsi-t200": (2.2, 1.4),
        "rsi-t100": (2.0, 1.3),
        "rsi-t-l": (2.2, 1.8),
        "squeeze": (1.5, 2.5),
        "gold-pb": (1.6, 1.5),
        "mom-dip": (1.8, 1.5),
        "ema20-50": (2.0, 4.0),
        "ema9-21": (2.0, 4.0),
        "bull-pb": (1.8, 1.6),
        "hh-brk": (2.0, 2.5),
        "dc-long": (2.2, 3.0),
        "confluence-6p": (2.0, 3.0),
        "supertrend-adx": (2.0, 3.5),
        "keltner-bb-squeeze": (1.8, 2.8),
        "dip-pullback-v2": (1.6, 2.0),
        "waddah-attar-explosion": (2.0, 3.0),
        "chandelier-exit": (2.0, 3.5),
        "stoch-rsi-t200": (2.0, 2.5),
    }[name]


def _exit_only_long(name: str) -> bool:
    return name in ("rsi-t-l", "gold-pb", "mom-dip", "bull-pb", "hh-brk", "dc-long", "confluence-6p", "dip-pullback-v2")


def backtest(strategy: str, symbol: str, bars: list[dict], timeframe: str = "4h",
             commission: float = 0.0005, initial: float = 10000.0,
             sl_tp: tuple[float, float] | None = None) -> Result:
    """commission = per side fraction (0.0005 = 5bps). sl_tp overrides _sl_tp(strategy)."""
    res = Result(strategy=strategy, symbol=symbol, timeframe=timeframe, source="local")
    if len(bars) < 250:
        return res
    sig = _signal_fn(strategy, bars)
    sl_m, tp_m = sl_tp if sl_tp is not None else _sl_tp(strategy)
    a = atr(bars, 14)
    long_only = _exit_only_long(strategy)

    equity = initial
    peak = initial
    max_dd = 0.0
    trades: list[Trade] = []
    pos: Trade | None = None
    eq_curve: list[float] = []

    def close_pos(i: int, price: float, reason: str) -> None:
        nonlocal pos, equity, peak, max_dd
        assert pos is not None
        # commission on exit
        notional = equity  # simplified: full equity re-entry model (percent_of_equity)
        if pos.side == "long":
            gross = (price / pos.entry_price - 1.0)
        else:
            gross = (1.0 - price / pos.entry_price)
        fee = commission * 2  # entry+exit approx charged on exit for simplicity
        pnl = gross - fee
        equity = equity * (1.0 + pnl)
        pos.exit_i = i
        pos.exit_price = price
        pos.reason = reason
        pos.pnl_pct = pnl * 100.0
        trades.append(pos)
        pos = None
        peak = max(peak, equity)
        dd = (peak - equity) / peak * 100.0
        max_dd = max(max_dd, dd)

    for i in range(1, len(bars)):
        b = bars[i]
        # manage open exits first (SL/TP) — conservative: SL if both hit
        if pos is not None and i > pos.entry_i:
            avg = pos.entry_price
            if a[i] is None:
                a_use = a[pos.entry_i] or 0.0
            else:
                a_use = a[i]
            if pos.side == "long":
                stop = avg - sl_m * a_use
                limit = avg + tp_m * a_use
                # gap: open through stop
                if b["o"] <= stop:
                    close_pos(i, min(b["o"], stop) if b["o"] <= stop else stop, "sl")
                elif b["l"] <= stop:
                    close_pos(i, stop, "sl")
                elif b["h"] >= limit:
                    close_pos(i, limit, "tp")
            else:
                stop = avg + sl_m * a_use
                limit = avg - tp_m * a_use
                if b["o"] >= stop:
                    close_pos(i, max(b["o"], stop), "sl")
                elif b["h"] >= stop:
                    close_pos(i, stop, "sl")
                elif b["l"] <= limit:
                    close_pos(i, limit, "tp")

        # entry signal on close (process_orders_on_close)
        if pos is None and a[i] is not None:
            side = sig(i)
            if side and not (long_only and side == "short"):
                # fee entry
                equity = equity * (1.0 - commission)
                pos = Trade(side=side, entry_i=i, entry_price=b["c"])
                peak = max(peak, equity)

        eq_curve.append(equity)

    # force close at end
    if pos is not None:
        close_pos(len(bars) - 1, bars[-1]["c"], "eod")

    # metrics
    res.equity = eq_curve
    res.trades = len(trades)
    res.wins = sum(1 for t in trades if t.pnl_pct > 0)
    res.losses = res.trades - res.wins
    res.win_rate_pct = (res.wins / res.trades * 100.0) if res.trades else 0.0
    res.long_trades = sum(1 for t in trades if t.side == "long")
    res.short_trades = sum(1 for t in trades if t.side == "short")
    res.net_profit_pct = (equity / initial - 1.0) * 100.0
    res.max_drawdown_pct = max_dd
    gp = sum(t.pnl_pct for t in trades if t.pnl_pct > 0)
    gl = abs(sum(t.pnl_pct for t in trades if t.pnl_pct < 0))
    res.profit_factor = (gp / gl) if gl > 0 else (999.0 if gp > 0 else 0.0)
    res.avg_trade_pct = (sum(t.pnl_pct for t in trades) / res.trades) if res.trades else 0.0
    res.trades_detail = [
        {
            "side": t.side,
            "entry_t": bars[t.entry_i]["t"],
            "entry_price": t.entry_price,
            "exit_t": bars[t.exit_i]["t"] if t.exit_i is not None else None,
            "exit_price": t.exit_price,
            "pnl_pct": round(t.pnl_pct, 4),
            "reason": t.reason,
        }
        for t in trades
    ]
    return res


STRATEGIES = [
    "rsi-t200b", "rsi-t200", "rsi-t100", "rsi-t-l",
    "squeeze", "gold-pb", "mom-dip", "ema20-50", "ema9-21",
    "bull-pb", "hh-brk", "dc-long",
    "confluence-6p", "supertrend-adx", "keltner-bb-squeeze", "dip-pullback-v2",
    "waddah-attar-explosion", "chandelier-exit", "stoch-rsi-t200",
]


def desk_gate(r: Result) -> str:
    if r.trades < 40 or r.profit_factor <= 0 or r.net_profit_pct <= 0:
        if r.trades == 0:
            return "Watchlist"
        if r.profit_factor < 1.0 or r.net_profit_pct <= 0 or r.max_drawdown_pct > 40:
            return "Reject"
        return "Watchlist"
    if r.profit_factor < 1.0 or r.net_profit_pct <= 0 or r.max_drawdown_pct > 40:
        return "Reject"
    safe = r.max_drawdown_pct <= 30
    if r.profit_factor >= 1.3 and safe and r.trades >= 50 and r.net_profit_pct > 0:
        return "Candidate" if r.win_rate_pct >= 50 else ("Incubate" if r.profit_factor >= 1.4 or r.trades >= 80 else "Watchlist")
    if r.profit_factor >= 1.2 and safe and r.trades >= 40 and r.net_profit_pct > 0:
        return "Watchlist"
    if r.profit_factor < 0.9 or r.net_profit_pct < -15:
        return "Reject"
    return "Watchlist"
