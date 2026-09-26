# MCP verify: rsi-t200b SL 1.8 / TP 1.5 (tv_jul26)

**Date**: 2026-09-24-1254 · **TF**: 4h · **Window**: 2025-01-01 → 2026-09-01
**Pairs**: ETHUSDT AVAXUSDT ARBUSDT OPUSDT ATOMUSDT INJUSDT XRPUSDT SOLUSDT · **errors**: 0
**Verdict**: MCP_CONFIRMED · soft 8/8 · strict 6/8
**meanPF**: 2.010 · **maxDD%**: 29.2 · **meanWR%**: 36.7
**Credits**: {'balance': 45, 'weeklyGrant': 1000, 'weeklyResetAt': 'Invalid Date', 'subscription': {'tier': 'free', 'status': 'none', 'currentPeriodEnd': None}, 'message': 'You have 45 credits.'} → {'balance': 37, 'weeklyGrant': 1000, 'weeklyResetAt': 'Invalid Date', 'subscription': {'tier': 'free', 'status': 'none', 'currentPeriodEnd': None}, 'message': 'You have 37 credits.'}

| Pair | Net% | PF | DD% | WR% | Trades | Soft | Strict | Verdict |
|---|---:|---:|---:|---:|---:|---|---|---|
| ETHUSDT | 36.5770663 | 3.08752345 | 9.55747627 | 44.73684211 | 38 | Y | N | Watchlist |
| ARBUSDT | 80.91400798 | 2.5239554 | 8.0306276 | 36.98630137 | 73 | Y | Y | Incubate |
| OPUSDT | 74.15951361 | 2.08849528 | 14.03728998 | 38.80597015 | 67 | Y | Y | Incubate |
| SOLUSDT | 23.90314068 | 1.94418093 | 7.96594379 | 42.85714286 | 35 | Y | N | Watchlist |
| AVAXUSDT | 24.51341779 | 1.74896587 | 12.3276225 | 34.04255319 | 47 | Y | Y | Watchlist |
| ATOMUSDT | 31.44104281 | 1.6690626 | 13.40960332 | 32.25806452 | 62 | Y | Y | Incubate |
| INJUSDT | 31.24352679 | 1.5735722 | 29.23637782 | 30.76923077 | 65 | Y | Y | Incubate |
| XRPUSDT | 14.52255271 | 1.44289632 | 8.92325543 | 33.33333333 | 42 | Y | Y | Watchlist |

## Notes

- Same entries as batch3 baseline (RSI 14/35/65 · EMA200); only SL/TP changed 2.5/1.6 → 1.8/1.5.
- No trailing, commission 0 (mcprule), engine tv_jul26.
- Soft gate: PF≥1.3 · DD≤30 · N≥20 · net>0. Strict adds N≥40.
- No real orders. Human approval required before any live step.

**Next**: Gertrude re-score vs parked baseline; cross-TF 2h still weak locally (3/8).
