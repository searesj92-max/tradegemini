"""Build top-N trading universe from free public APIs (no credits)."""
from __future__ import annotations

import json
import ssl
import urllib.request
from pathlib import Path

ROOT = Path(r"C:\Users\seares\Desktop\botrade")
OUT = ROOT / "data" / "universe"
OUT.mkdir(parents=True, exist_ok=True)

STABLE = {
    "USDCUSDT", "USDTUSDT", "BUSDUSDT", "TUSDUSDT", "DAIUSDT", "FDUSDUSDT",
    "USD1USDT", "RLUSDUSDT", "USDEUSDT", "PYUSDUSDT", "EURUSDT", "AEURUSDT",
    "USDPUSDT", "GUSDUSDT", "SUSDUSDT", "USTCUSDT", "USDJUSDT", "USDDUSDT",
    "FDUSD", "USDC", "USDT",
}
# pure stable/staked noise often in volume lists
SKIP_PREFIX = ("C", "E")  # not reliable; keep explicit list only

CTX = ssl.create_default_context()


def _get(url: str, timeout: float = 25.0):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 botrade-research"})
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
        return json.loads(r.read().decode())


def top_binance(n: int = 60) -> list[dict]:
    t = _get("https://api.binance.com/api/v3/ticker/24hr")
    rows = []
    for x in t:
        sym = x.get("symbol") or ""
        if not sym.endswith("USDT"):
            continue
        if sym in STABLE:
            continue
        # skip leveraged tokens if any
        if sym.endswith("UPUSDT") or sym.endswith("DOWNUSDT") or "BULL" in sym or "BEAR" in sym:
            continue
        qv = float(x.get("quoteVolume") or 0)
        if qv <= 0:
            continue
        rows.append({
            "exchange": "binance",
            "symbol": sym,
            "base": sym[:-4],
            "quote_volume_24h": qv,
            "last_price": float(x.get("lastPrice") or 0),
        })
    rows.sort(key=lambda r: r["quote_volume_24h"], reverse=True)
    return rows[:n]


def top_bybit(n: int = 60) -> list[dict]:
    b = _get("https://api.bybit.com/v5/market/tickers?category=linear")
    res = b.get("result", {}).get("list", [])
    rows = []
    for x in res:
        sym = x.get("symbol") or ""
        if not sym.endswith("USDT"):
            continue
        if sym in STABLE:
            continue
        turn = float(x.get("turnover24h") or 0)
        if turn <= 0:
            continue
        rows.append({
            "exchange": "bybit",
            "symbol": sym,
            "base": sym[:-4],
            "quote_volume_24h": turn,
            "last_price": float(x.get("lastPrice") or 0),
        })
    rows.sort(key=lambda r: r["quote_volume_24h"], reverse=True)
    return rows[:n]


def normalize_base(base: str) -> str:
    # 1000PEPE -> PEPE for Binance symbol mapping
    if base.startswith("1000") and len(base) > 4:
        return base[4:]
    if base.startswith("1000000"):
        return base[7:]
    return base


def binance_symbol(base: str) -> str:
    return f"{base}USDT"


def merge_top40(n: int = 40) -> list[dict]:
    by = top_bybit(80)
    bn = top_binance(80)
    bn_map = {r["base"]: r for r in bn}
    # prefer Bybit perp universe (desk trades perps) then fill with Binance
    seen = set()
    out: list[dict] = []
    for r in by:
        b = normalize_base(r["base"])
        if b in seen:
            continue
        # map to binance kline symbol if exists
        bs = binance_symbol(b)
        has_binance = bs in {x["symbol"] for x in bn} or any(
            x["symbol"] == bs for x in bn
        )
        # also try original base
        if bs not in {x["symbol"] for x in bn}:
            # check normalized in binance list by symbol
            if not any(x["symbol"] == bs for x in bn):
                # still allow bybit-only later via bybit klines fallback
                has_binance = False
        out.append({
            "base": b,
            "bybit_symbol": r["symbol"],
            "binance_symbol": bs if any(x["symbol"] == bs for x in bn) else None,
            "bybit_turnover": r["quote_volume_24h"],
            "source_rank": "bybit",
            "kline_provider": "binance" if any(x["symbol"] == bs for x in bn) else "bybit",
        })
        seen.add(b)
        if len(out) >= n:
            break
    if len(out) < n:
        for r in bn:
            b = r["base"]
            if b in seen:
                continue
            out.append({
                "base": b,
                "bybit_symbol": None,
                "binance_symbol": r["symbol"],
                "bybit_turnover": None,
                "binance_quote_volume": r["quote_volume_24h"],
                "source_rank": "binance",
                "kline_provider": "binance",
            })
            seen.add(b)
            if len(out) >= n:
                break
    for i, r in enumerate(out, 1):
        r["rank"] = i
    return out[:n]


def main() -> int:
    top = merge_top40(40)
    path = OUT / "top40.json"
    path.write_text(json.dumps(top, indent=2), encoding="utf-8")
    print(f"wrote {path} n={len(top)}")
    for r in top:
        print(f"  {r['rank']:02d} {r['base']:12s} bybit={r.get('bybit_symbol')} binance={r.get('binance_symbol')} via={r.get('kline_provider')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
