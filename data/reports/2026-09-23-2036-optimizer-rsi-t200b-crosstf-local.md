# Optimizer local: rsi-t200b cross-TF 1h/2h (0 credits)

**Date**: 2026-09-23-2036 · **Engine**: local Python · **Pairs**: ETH AVAX ARB OP ATOM INJ XRP SOL
**Best SL/TP**: 1.8 / 1.5 ATR · **Baseline**: 2.5 / 1.6
**Window**: 2025-01-01 → 2026-09-01 · **errors**: 0
**Verdict**: MIXED · stable TFs (soft≥5/8): 4h

## Soft-pass by TF (N≥20 gate)

| TF | best 1.8/1.5 | baseline 2.5/1.6 |
|---|---:|---:|
| 1h | 0/8 | 0/8 |
| 2h | 3/8 | 4/8 |
| 4h | 8/8 | 6/8 |

## Cell matrix

| SL | TP | TF | soft/8 | strict/8 | meanPF | maxDD% | meanWR% | meanN | meanNet% |
|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 2.5 | 1.6 | 1h | 0/8 | 0/8 | 0.921 | 48.33 | 60.74 | 85.9 | -15.68 |
| 2.5 | 1.6 | 2h | 4/8 | 4/8 | 1.459 | 37.8 | 68.09 | 47.0 | 19.02 |
| 2.5 | 1.6 | 4h | 6/8 | 0/8 | 2.652 | 23.62 | 78.34 | 23.6 | 49.31 |
| 1.8 | 1.5 | 1h | 0/8 | 0/8 | 0.948 | 35.36 | 55.78 | 95.8 | -12.27 |
| 1.8 | 1.5 | 2h | 3/8 | 3/8 | 1.352 | 35.62 | 60.88 | 51.9 | 11.41 |
| 1.8 | 1.5 | 4h | 8/8 | 0/8 | 2.787 | 22.22 | 74.45 | 25.1 | 45.55 |

## Best cell detail — SL 1.8 / TP 1.5 by TF

### 1h

| Pair | Net% | PF | DD% | WR% | Trades | Soft |
|---|---:|---:|---:|---:|---:|---|
| SOL | 10.5405 | 1.2072 | 22.3227 | 60.3774 | 106 | N |
| XRP | 5.3462 | 1.1523 | 22.6671 | 62.069 | 87 | N |
| ATOM | -7.4037 | 0.9867 | 16.9922 | 57.0 | 100 | N |
| OP | -8.9363 | 0.9858 | 19.388 | 55.3191 | 94 | N |
| AVAX | -16.8947 | 0.8642 | 24.0652 | 54.6512 | 86 | N |
| ARB | -23.7714 | 0.8362 | 32.7077 | 54.2553 | 94 | N |
| ETH | -21.6785 | 0.778 | 26.0972 | 53.0612 | 98 | N |
| INJ | -35.363 | 0.7703 | 35.363 | 49.505 | 101 | N |

### 2h

| Pair | Net% | PF | DD% | WR% | Trades | Soft |
|---|---:|---:|---:|---:|---:|---|
| SOL | 74.5242 | 2.7735 | 5.9969 | 76.9231 | 52 | Y |
| AVAX | 30.5972 | 1.6709 | 13.5383 | 64.4444 | 45 | Y |
| ETH | 29.596 | 1.6563 | 13.706 | 68.9655 | 58 | Y |
| ARB | 4.9398 | 1.1263 | 27.0635 | 57.1429 | 56 | N |
| OP | -12.3493 | 0.9275 | 35.6247 | 55.5556 | 54 | N |
| INJ | -14.4218 | 0.92 | 26.7316 | 54.386 | 57 | N |
| ATOM | -10.4477 | 0.885 | 17.2207 | 55.102 | 49 | N |
| XRP | -11.1406 | 0.8591 | 23.4017 | 54.5455 | 44 | N |

### 4h

| Pair | Net% | PF | DD% | WR% | Trades | Soft |
|---|---:|---:|---:|---:|---:|---|
| XRP | 53.6669 | 4.9576 | 4.9513 | 86.3636 | 22 | Y |
| ETH | 48.2119 | 4.0315 | 6.8577 | 82.6087 | 23 | Y |
| ARB | 107.1866 | 3.2567 | 6.6502 | 77.7778 | 36 | Y |
| AVAX | 39.8057 | 2.8138 | 12.6511 | 80.0 | 20 | Y |
| SOL | 25.4934 | 2.0492 | 16.7997 | 70.0 | 20 | Y |
| INJ | 35.0592 | 1.7887 | 16.8677 | 68.0 | 25 | Y |
| ATOM | 25.3205 | 1.7664 | 22.2248 | 62.963 | 27 | Y |
| OP | 29.6524 | 1.6324 | 15.6869 | 67.8571 | 28 | Y |

## Notes

- Entries/signals unchanged; only timeframe resample + SL/TP from prior sweep.
- No trailing, no martingale, local commission 5bps/side.
- Soft gate: PF≥1.3 · DD≤30 · N≥20 · net>0. Strict adds N≥40.
- Local engine ≠ tv_jul26 — MCP verify still pending if Gertrude promotes.
- Zero API credits used.

**Next**: Gertrude re-eval for incubation if STABLE on ≥2 TFs; else keep ESTACIONAR.
