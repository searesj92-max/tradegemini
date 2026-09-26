# Optimizer local: rsi-t200b SL/TP sweep (0 credits)

**Date**: 2026-09-23-1949 · **Engine**: local Python · **TF**: 4h · **Pairs**: ETH AVAX ARB OP ATOM INJ XRP SOL
**Baseline**: SL 2.5 / TP 1.6 ATR · **Best**: SL 1.5 / TP 1.2
**Verdict**: NO_IMPROVEMENT · **errors**: 0

## Grid ranking

| SL | TP | pass/8 | meanPF | maxDD% | meanWR% | note |
|---:|---:|---:|---:|---:|---:|---|
| 1.5 | 1.2 | 0/8 | 2.114 | 13.8 | 72.0 | winner |
| 1.8 | 1.2 | 0/8 | 2.787 | 16.3 | 79.0 |  |
| 2.0 | 1.0 | 0/8 | 2.467 | 21.1 | 80.7 |  |
| 2.5 | 1.2 | 0/8 | 2.868 | 19.4 | 82.7 |  |
| 2.5 | 1.0 | 0/8 | 2.845 | 21.4 | 83.4 |  |
| 1.8 | 1.5 | 0/8 | 2.787 | 22.2 | 74.4 |  |
| 1.5 | 1.5 | 0/8 | 2.170 | 24.1 | 67.0 |  |
| 2.0 | 1.3 | 0/8 | 2.544 | 21.2 | 77.5 |  |
| 2.5 | 1.6 | 0/8 | 2.652 | 23.6 | 78.3 | baseline |
| 3.0 | 1.6 | 0/8 | 2.669 | 20.4 | 81.1 |  |
| 3.0 | 2.0 | 0/8 | 2.810 | 20.4 | 77.6 |  |
| 2.0 | 1.6 | 0/8 | 2.439 | 24.4 | 73.7 |  |

## Best cell detail — SL 1.5 / TP 1.2

| Pair | Net% | PF | DD% | WR% | Trades | Pass |
|---|---:|---:|---:|---:|---:|---|
| ETH | 34.4239 | 3.572 | 5.3929 | 82.6087 | 23 | N |
| ATOM | 29.7242 | 2.1388 | 10.5253 | 68.9655 | 29 | N |
| XRP | 20.9368 | 2.0395 | 4.6537 | 73.913 | 23 | N |
| SOL | 19.6716 | 2.0205 | 10.8625 | 70.0 | 20 | N |
| INJ | 36.03 | 1.9872 | 10.0412 | 70.3704 | 27 | N |
| ARB | 41.8387 | 1.8868 | 8.254 | 71.0526 | 38 | N |
| AVAX | 16.9203 | 1.7571 | 10.6492 | 71.4286 | 21 | N |
| OP | 19.025 | 1.5109 | 13.7617 | 67.8571 | 28 | N |

## Baseline detail — SL 2.5 / TP 1.6

| Pair | Net% | PF | DD% | WR% | Trades | Pass |
|---|---:|---:|---:|---:|---:|---|
| AVAX | 62.5343 | 4.681 | 8.8849 | 89.4737 | 19 | N |
| ARB | 127.9782 | 4.1526 | 9.0419 | 87.0968 | 31 | N |
| XRP | 40.0242 | 2.6902 | 11.6369 | 81.8182 | 22 | N |
| INJ | 67.2974 | 2.4549 | 15.6872 | 79.1667 | 24 | N |
| ETH | 35.0985 | 2.4092 | 16.9346 | 78.2609 | 23 | N |
| SOL | 25.4237 | 1.9385 | 18.6641 | 73.6842 | 19 | N |
| ATOM | 18.7455 | 1.5274 | 23.6153 | 68.0 | 25 | N |
| OP | 17.3746 | 1.3643 | 15.5812 | 69.2308 | 26 | N |

## Notes

- Entries/signals unchanged; only SL/TP ATR multipliers (dispatch rule).
- No trailing, no martingale, local commission 5bps/side.
- Local engine ≠ tv_jul26 — re-check survivors on Trader Dev before Gertrude promotes.
- Zero API credits used.

**Next**: if IMPROVED, Gertrude re-evaluates for incubation + cross-TF; else ESTACIONAR.
