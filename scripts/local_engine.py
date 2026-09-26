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
        iv = {"1h": "60", "2h": "120", "4h": "240", "1d": "D"}.get(interval, interval)
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
    }[name]


def _exit_only_long(name: str) -> bool:
    return name in ("rsi-t-l", "gold-pb", "mom-dip", "bull-pb", "hh-brk", "dc-long")


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
