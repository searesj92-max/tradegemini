# Optimizer local: rsi-t200b SL/TP sweep (0 credits)

**Date**: 2026-09-23-1951 · **Engine**: local Python · **TF**: 4h · **Pairs**: ETH AVAX ARB OP ATOM INJ XRP SOL
**Baseline**: SL 2.5 / TP 1.6 ATR · **Best**: SL 1.8 / TP 1.5
**Verdict**: IMPROVED · **errors**: 0 · soft-pass (N≥20): baseline 6/8 → best 8/8

## Grid ranking

| SL | TP | pass/8 | soft/8 | meanPF | softPF | maxDD% | meanWR% | meanN | note |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1.8 | 1.5 | 0/8 | 8/8 | 2.787 | 2.787 | 22.2 | 74.4 | 25.1 | winner |
| 1.5 | 1.5 | 0/8 | 8/8 | 2.170 | 2.170 | 24.1 | 67.0 | 26.1 |  |
| 1.5 | 1.2 | 0/8 | 8/8 | 2.114 | 2.114 | 13.8 | 72.0 | 26.1 |  |
| 1.8 | 1.2 | 0/8 | 7/8 | 2.787 | 3.002 | 16.3 | 79.0 | 25.2 |  |
| 2.0 | 1.6 | 0/8 | 7/8 | 2.439 | 2.445 | 24.4 | 73.7 | 24.5 |  |
| 2.0 | 1.0 | 0/8 | 6/8 | 2.467 | 2.895 | 21.1 | 80.7 | 25.2 |  |
| 2.0 | 1.3 | 0/8 | 6/8 | 2.544 | 2.871 | 21.2 | 77.5 | 24.9 |  |
| 2.5 | 1.6 | 0/8 | 6/8 | 2.652 | 2.433 | 23.6 | 78.3 | 23.6 | baseline |
| 3.0 | 1.6 | 0/8 | 6/8 | 2.669 | 2.220 | 20.4 | 81.1 | 23.1 |  |
| 3.0 | 2.0 | 0/8 | 6/8 | 2.810 | 2.208 | 20.4 | 77.6 | 23.0 |  |
| 2.5 | 1.0 | 0/8 | 5/8 | 2.845 | 3.589 | 21.4 | 83.4 | 24.6 |  |
| 2.5 | 1.2 | 0/8 | 5/8 | 2.868 | 3.413 | 19.4 | 82.7 | 24.1 |  |

## Best cell detail — SL 1.8 / TP 1.5

| Pair | Net% | PF | DD% | WR% | Trades | Soft | Strict |
|---|---:|---:|---:|---:|---:|---|---|
| XRP | 53.6669 | 4.9576 | 4.9513 | 86.3636 | 22 | Y | N |
| ETH | 48.2119 | 4.0315 | 6.8577 | 82.6087 | 23 | Y | N |
| ARB | 107.1866 | 3.2567 | 6.6502 | 77.7778 | 36 | Y | N |
| AVAX | 39.8057 | 2.8138 | 12.6511 | 80.0 | 20 | Y | N |
| SOL | 25.4934 | 2.0492 | 16.7997 | 70.0 | 20 | Y | N |
| INJ | 35.0592 | 1.7887 | 16.8677 | 68.0 | 25 | Y | N |
| ATOM | 25.3205 | 1.7664 | 22.2248 | 62.963 | 27 | Y | N |
| OP | 29.6524 | 1.6324 | 15.6869 | 67.8571 | 28 | Y | N |

## Baseline detail — SL 2.5 / TP 1.6

| Pair | Net% | PF | DD% | WR% | Trades | Soft | Strict |
|---|---:|---:|---:|---:|---:|---|---|
| AVAX | 62.5343 | 4.681 | 8.8849 | 89.4737 | 19 | N | N |
| ARB | 127.9782 | 4.1526 | 9.0419 | 87.0968 | 31 | Y | N |
| XRP | 40.0242 | 2.6902 | 11.6369 | 81.8182 | 22 | Y | N |
| INJ | 67.2974 | 2.4549 | 15.6872 | 79.1667 | 24 | Y | N |
| ETH | 35.0985 | 2.4092 | 16.9346 | 78.2609 | 23 | Y | N |
| SOL | 25.4237 | 1.9385 | 18.6641 | 73.6842 | 19 | N | N |
| ATOM | 18.7455 | 1.5274 | 23.6153 | 68.0 | 25 | Y | N |
| OP | 17.3746 | 1.3643 | 15.5812 | 69.2308 | 26 | Y | N |

## Notes

- Entries/signals unchanged; only SL/TP ATR multipliers (dispatch rule).
- No trailing, no martingale, local commission 5bps/side.
- Strict desk gate uses trades≥40 — local rsi-t200b emits ~19–38 trades/8 pairs (trade-limited: True). Soft pass = PF≥1.3 · DD≤30 · N≥20 · net>0.
- Local engine ≠ tv_jul26 — re-check survivors on Trader Dev before Gertrude promotes.
- Zero API credits used.

**Next**: if IMPROVED, Gertrude re-evaluates for incubation + cross-TF; else ESTACIONAR.
Cross-TF 1h/2h still required for any incubation claim.
