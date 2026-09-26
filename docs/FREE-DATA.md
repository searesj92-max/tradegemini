# Free / local data & backtest stack (credit-safe)

> Goal: never burn Trader Dev credits on bulk screening. Use free APIs + local engine; reserve MCP for verification.

## Current status

| Layer | Source | Cost | Use |
|---|---|---|---|
| Universe (top 40) | Binance `ticker/24hr` + Bybit `v5/market/tickers` | **free** | rank by 24h USDT volume |
| OHLCV 4h/1h | Binance `klines` + Bybit `kline` (public) | **free** | local backtest |
| Local engine | `scripts/local_engine.py` (Python) | **free** | screen thousands of combos |
| Pine parity check | Trader Dev MCP `quick_backtest` | **~1 credit/row** | survivors only |
| Curve / trades detail | Trader Dev `get_equity_curve` / `get_trades` | cheap/free reads | finalists |

## Scripts

```powershell
$py = "$env:LOCALAPPDATA\hermes\hermes-agent\venv\Scripts\python.exe"

# 1) refresh top-40 universe (free)
& $py C:\Users\seares\Desktop\botrade\scripts\top_universe.py

# 2) local screen — 0 credits (downloads OHLCV once, caches in data/ohlcv/)
& $py C:\Users\seares\Desktop\botrade\scripts\run_local_top40.py

# 3) push local rows into Mission Control
& $py C:\Users\seares\Desktop\botrade\scripts\merge_local_dashboard.py

# 4) ONLY survivors → Trader Dev (spend credits carefully)
#    e.g. validate top 5 families × 5 pairs = 25 credits
```

## Hybrid workflow (recommended)

```
[free] top N symbols + local OHLCV
        │
        ▼
[free] local engine × families × symbols  ──► kill rejects
        │
        ▼
[MCP credits] quick_backtest on top ~20–40 rows only
        │
        ▼
[free] rebuild_dashboard / merge_local ──► Mission Control
        │
        ▼
Gertrude gate
```

## Local engine caveats

- Approximates Pine `process_orders_on_close` + ATR SL/TP (same-bar SL priority = conservative).
- Local commission **5 bps/side** (stricter than mcprule commission=0 on Trader Dev).
- Not a substitute for tv_jul26 for final claims — **always re-check survivors on MCP**.
- bull-pb still ~0 trades locally (same entry issue as MCP batch4).

## Other free platforms (research only)

| Platform | Notes |
|---|---|
| **Binance/Bybit public klines** | already used; no key for history |
| **CCXT** | multi-exchange; install if we need more venues |
| **TradingView free** | manual Pine charts; no bulk API |
| **VectorBT / backtrader** | optional richer Python libs (not installed) |
| **Databento / Tardis** | paid tick data — skip for now |
| Trader Dev free tier | weekly grant; **protect for verification** |

## Credit policy

1. `get_credits` before any MCP batch.
2. If balance < 50 → local only until weekly reset or top-up.
3. Never re-run full 160/480 MCP matrices; local screen first.
4. Target: **≤ 50 credits/week** on verification.

## Top-40 universe file

`data/universe/top40.json` — rank by 24h turnover (Bybit linear preferred, Binance fill).
Includes tokenized stocks/metals on Bybit when volume ranks (SOXL, TSLA, XAU, XAG…).

---
*Risk notice: local backtests are research approximations. Not financial advice.*
