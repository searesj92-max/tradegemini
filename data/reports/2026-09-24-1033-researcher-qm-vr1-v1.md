# Quant Mathematician Cycle Report — Cycle 04

Data: 2026-09-24 10:33 UTC · Agent: researcher · Engine: tv_jul26_mc7

---

## 1. Hypotheses Generated

### H1 — Variance-Ratio Mean Reversion (VR1)
**Inefficiency:** Crypto returns exhibit short-horizon variance ratios below 1 (mean-reverting microstructure) interspersed with trending regimes (VR > 1). Fading large displacements *only* when VR confirms the MR regime should capture the reversion premium while avoiding trend chop.

**Why in crypto:** Order-book mean reversion at the microstructure level (bid-ask bounce, liquidity provision) creates a genuine VR < 1 signal at high frequency. The challenge is regime separation — trending markets have VR > 1 and should be avoided.

**Cross-symbol:** Universal microstructure property; should work on BTC, ETH, and large caps with sufficient liquidity.

**Breaking regime:** High-volatility trending environments (e.g. macro shocks, liquidations cascades) where VR>1 but displacement still triggers.

**Pine expression:** VR(2) = Var(r₂) / (2·Var(r₁)) over N-bar lookback; enter long when disp < −threshold·ATR and VR < 0.95; SL at eq − (threshold+buffer)·ATR; TP when disp returns to −tpDisp·ATR or time exit.

### H2 — Range Efficiency Collapse (unpursued this cycle)
**Inefficiency:** When a symbol's realized range over K bars collapses below its long-term typical range (range-efficiency < threshold), the next displacement tends to be larger — a "coiled spring" effect. Enter in the direction of the first break.

**Why in crypto:** Consolidation before liquidation cascades or volatility expansions; range compression is a known precursor.

**Breaking regime:** Genuine quiet regimes that stay quiet (no follow-through).

### H3 — Failed Continuation After Displacement (unpursued this cycle)
**Inefficiency:** After a large displacement bar (>2·ATR), a secondary bar in the same direction of similar magnitude is statistically less probable — the first move already exhausted the immediate liquidity. Enter against the second move.

**Why in crypto:** Liquidity absorption; the first large move consumes available liquidity on that side, making a repeat less likely.

**Breaking regime:** Strong macro trends where multiple large bars in the same direction are the norm.

### H4 — Volatility Regime Switching with Asymmetric SL (unpursued this cycle)
**Inefficiency:** Treating SL as a fixed multiple of ATR ignores that volatility is clustered. In low-vol regimes, SL should be tighter (relative to ATR) because noise is lower; in high-vol regimes, SL must be wider. A regime-adaptive SL improves the win/loss geometry.

**Why in crypto:** Volatility clustering (GARCH-like) is very strong in crypto; static ATR multiples are suboptimal.

### H5 — Distance-from-Equilibrium Exhaustion (unpursued this cycle)
**Inefficiency:** The farther price is from a slow-moving equilibrium (e.g. 200-bar SMA in price-space, not ATR-space), the higher the probability of an eventual reversion —BUT only up to a point, after which the trend is genuine. A quadratic penalty for extreme displacement captures the non-monotonicity.

**Why in crypto:** Overshoot and snapback behavior in ranging markets; the non-monotonic profile (too far = trend, not reversion) is the key insight.

---

## 2. Hypothesis Selected

**H1 — Variance-Ratio Mean Reversion (VR1).**

Selected because:
- It is a genuine statistical test (Lo & MacKinlay 1988), not an indicator soup signal.
- The VR<1 condition provides a genuine regime filter that should, in principle, separate MR from trending environments.
- It is computable from price alone (no volume, no order book), making it robust across symbols.
- The math is clean: variance ratio directly tests the random-walk null.

Risk: VR(2) at 30-bar lookback is noisy at 15m. The regime filter may be too permissive (threshold 0.95) or the wrong lookback. This is testable.

---

## 3. Trading Rules

### Equilibrium
- `eq = ta.sma(close, 50)` — slow equilibrium anchor.
- `atr = ta.atr(14)` — volatility normalizer.

### Signed displacement
- `disp = (close − eq) / atr` — normalized distance from equilibrium, signed.

### Regime filter (Variance Ratio VR(2), Lo & MacKinlay)
- r₁ = close − close[1], r₂ = close − close[2]
- `vr = Var(r₂) / (2·Var(r₁))` computed over `vrLookback = 30` bars
- MR regime active when `vr < vrThreshold = 0.95`

### Entries (both require MR regime + cooldown = 0 + flat position)
- **Long:** `disp < −1.2` (price 1.2 ATR below equilibrium, in MR regime)
- **Short:** `disp > +1.2` (price 1.2 ATR above equilibrium, in MR regime)

### Exits
- **SL (hard, set at entry):** Long SL = `eq − (1.2 + 0.5)·ATR`, Short SL = `eq + (1.2 + 0.5)·ATR`. Ratchet re-issued each bar (fixed price from entry).
- **TP (signal-based):** Close long when `disp > −0.3`, close short when `disp < +0.3` (price returns to within 0.3 ATR of equilibrium). Also close on time exit at 20 bars.
- **Cooldown:** 2 bars after any exit before re-entry allowed.

### Filters
- MR regime required (VR < 0.95)
- Cooldown enforced
- Max position age 20 bars (time exit)
- No trend filter (intentionally bare — this is the baseline)

### Risk
- 100% equity per trade (MCP parity profile: margin 100/100, pyramiding 1, commission 0.05%)
- SL = 1.7·ATR from entry (1.2 threshold + 0.5 buffer)

---

## 4. Pine Script

See `data/pine/qm_vr1_v1.pine` (same source as this cycle's backtests). Summary:

```
//@version=6
strategy("QM-VR1-V1 — Variance-Ratio MR with Regime Filter",
  overlay=true, pyramiding=1, process_orders_on_close=true,
  commission_type=strategy.commission.percent, commission_value=0.05,
  initial_capital=10000, default_qty_type=strategy.percent_of_equity,
  default_qty_value=100, margin_long=100, margin_short=100)

eq       = ta.sma(close, 50)
atr      = ta.atr(14)
disp     = (close - eq) / atr

// VR(2) regime
r1 = close - close[1]
r2 = close - close[2]
meanR1 = ta.sma(r1, 30)
varR1  = ta.sma(math.pow(r1 - meanR1, 2), 30)
meanR2 = ta.sma(r2, 30)
varR2  = ta.sma(math.pow(r2 - meanR2, 2), 30)
vr      = varR1 > 1e-9 ? varR2 / (2 * varR1) : 1.0
mrRegime = vr < 0.95

// Entry: displacement + MR regime + cooldown + flat
longSig  = disp < -1.2 and mrRegime and flat and cd == 0
shortSig = disp >  1.2 and mrRegime and flat and cd == 0

// SL ratchet (fixed price from entry)
strategy.exit("LSL", from_entry="L", stop=eq - 1.7*atr)   // on long
strategy.exit("SSL", from_entry="S", stop=eq + 1.7*atr)   // on short

// TP: displacement returns to within 0.3 ATR of eq, or 20-bar time exit
longExit  = pos > 0 and (disp > -0.3 or barsInPos >= 20)
shortExit = pos < 0 and (disp <  0.3 or barsInPos >= 20)
```

---

## 5. Backtest Matrix

| Symbol   | TF  | Strategy ID                       | Result ID                      | Bars  | Trades |
|----------|-----|-----------------------------------|--------------------------------|-------|--------|
| BTCUSDT  | 15m | 01M39FEHQM2DWFNH3W5YVESS92 (v1) | 01M39FEHG7SDBETKCBZX47BS69   | 8898  | 1307   |
| ETHUSDT  | 15m | 01M39FMHCSNKVE4MS2FSYTAS3G (v1) | 01M39FMH20H09SQS0K77FP1FBP   | 8898  | 1681   |
| BTCUSDT  | 1h  | 01M39FND0X0QR22MJP7MJY38XK (v1) | 01M39FNCT7DVT3XB1G09BTCT0T   | 2450  | 315    |

Date range: ~June 2026 – September 24, 2026 (clickhouse coverage). Commission 0.05%, slippage 0, 100% equity, margin 100/100.

---

## 6. Results

### BTCUSDT 15m
| Metric              | Value       |
|---------------------|-------------|
| Net profit          | **−75.72%** |
| Final equity        | $2,428      |
| Profit factor       | 0.27        |
| Max drawdown        | −75.72%     |
| Win rate            | 21.3%       |
| Total trades        | 1307        |
| Winning / Losing    | 279 / 1028  |
| Avg trade           | −$5.79      |
| Avg win / Avg loss  | $9.82 / −$10.03 (ratio 0.98) |
| Avg bars in trade   | 2.51        |
| Sharpe / Sortino    | −29.35 / −17.36 |
| Commission paid     | $6,841      |
| Long PF / Short PF  | long −2710, short −4863 |

### ETHUSDT 15m
| Metric              | Value       |
|---------------------|-------------|
| Net profit          | **−73.59%** |
| Final equity        | $2,641      |
| Profit factor       | 0.40        |
| Max drawdown        | −73.91%     |
| Win rate            | 20.5%       |
| Total trades        | 1681        |
| Winning / Losing    | 345 / 1336  |
| Avg trade           | −$4.38      |
| Avg win / Avg loss  | $14.08 / −$9.14 (ratio 1.54) |
| Avg bars in trade   | 2.48        |
| Sharpe / Sortino    | −22.33 / −13.95 |
| Commission paid     | $7,578      |
| Long PF / Short PF  | long −2460, short −4899 |

### BTCUSDT 1h
| Metric              | Value       |
|---------------------|-------------|
| Net profit          | **−43.81%** |
| Final equity        | $5,619      |
| Profit factor       | 0.32        |
| Max drawdown        | −43.81%     |
| Win rate            | 24.4%       |
| Total trades        | 315         |
| Winning / Losing    | 77 / 238    |
| Avg trade           | −$13.91     |
| Avg win / Avg loss  | $26.70 / −$27.04 (ratio 0.99) |
| Avg bars in trade   | 2.34        |
| Sharpe / Sortino    | −11.43 / −5.59 |
| Commission paid     | $2,287      |
| Long PF / Short PF  | long −891, short −3490 |

### Cross-asset summary
| Symbol   | TF  | Net%    | PF   | DD%    | WR%  | Trades |
|----------|-----|---------|------|--------|------|--------|
| BTCUSDT  | 15m | −75.7   | 0.27 | −75.7  | 21.3 | 1307   |
| ETHUSDT  | 15m | −73.6   | 0.40 | −73.9  | 20.5 | 1681   |
| BTCUSDT  | 1h  | −43.8   | 0.32 | −43.8  | 24.4 | 315    |

All three runs are **heavily negative**. PF ranges 0.27–0.40 (need ≥1.3 for incubation). Win rate 20–24% (below breakeven for this SL/TP geometry). Trade counts are very high (1307–1681 on 15m), indicating the entry threshold is too easily triggered — the strategy trades noise.

---

## 7. Diagnosis

### 7.1 The core problem: entry rate too high, edge per trade negative

1307 trades on 8898 bars = 1 trade every ~6.8 bars on BTC 15m. This means the "displacement > 1.2 ATR + VR < 0.95" condition is firing constantly. In a crypto market that trends a significant fraction of the time, repeatedly fading displacement at 1.2 ATR with only a 1.7 ATR SL is a losing game — the very displacements that trigger entry often continue (trend), and the SL gets hit.

### 7.2 Win/loss ratio is near 1.0 — no positive expectancy

- BTC 15m: avg win $9.82 vs avg loss $10.03 (ratio 0.98) — this is a round-trip loser before commission.
- ETH 15m: ratio 1.54 (positive!) but win rate only 20.5% — the few wins are larger than losses, but too few of them; net still −73.6%.
- BTC 1h: ratio 0.99 — same round-trip-loser geometry.

The SL/TP geometry (SL 1.7 ATR, TP at 0.3 ATR from equilibrium) creates an asymmetric target: TP is much closer than SL. This would require a win rate > 85% to be profitable (1.7/0.3 ≈ 5.7:1 reward:risk inverse, so need ~85% wins). We get 20–24%. The geometry itself is wrong for a mean-reversion strategy with a 1.7 ATR stop.

### 7.3 Commission is a major contributor but not the root cause

BTC 15m: $6,841 commission vs $7,572 gross loss → commission is ~90% of the loss. But gross profit $2,740 vs gross loss $10,313 → PF without commission would be 0.27 (essentially the same). Commission amplifies but doesn't create the loss. The underlying trades have negative expectancy.

### 7.4 VR threshold 0.95 is too permissive

At 15m, VR(2) over 30 bars repeatedly dips below 0.95 even in trending conditions (because 2-bar returns can be mean-reverting at the microstructure level even when the larger trend is up). The filter lets in too many trend-fading entries.

### 7.5 The TP logic is wrong for this geometry

Exiting when `disp > −0.3` (for longs) means we take profit when price has recovered only 0.3 ATR from the entry extreme. With entry at −1.2 ATR and SL at −1.7 ATR from eq, the TP is at 0.3 ATR from eq — which is roughly 1.5 ATR *beyond entry price* in the favorable direction. Wait — let me recompute:

- Entry long: price is at `eq − 1.2·ATR` (disp = −1.2)
- SL: `eq − 1.7·ATR` (disp = −1.7) → SL is 0.5 ATR below entry
- TP exit: when `disp > −0.3` → price at `eq − 0.3·ATR` → this is 0.9 ATR *above* entry price

So the reward:risk on a filled trade is ~0.9 ATR reward vs 0.5 ATR risk = 1.8:1. That needs ~36% win rate to break even (before commission). We get 21%. Still losing.

But note: avg bars in trade is 2.5 — most trades are being stopped out or exited very quickly. This suggests the SL is being hit frequently on the first few bars after entry (noise), and the TP is rarely reached because the displacement doesn't revert cleanly.

### 7.6 The strategy is a baseline failure — not a subtle miss

This isn't "almost working, needs a tweak." The PF of 0.27–0.40 across three runs is a definitive rejection. The mathematical idea (VR-filtered mean reversion on displacement) does not produce positive expectancy in this form on these symbols/timeframes. The entry condition is too loose, the SL too tight relative to the noise, and the regime filter insufficient.

---

## 8. Verdict

### REJECT — VR1 line, strike 1

**Rationale:**
- PF < 0.5 on all three runs (need ≥ 1.3 to even consider watchlist).
- Win rate 20–24% with an unfavorable SL/TP geometry.
- Extremely high trade count on 15m (1307–1681) — trading noise.
- Net loss −43% to −76% across symbols/timeframes — consistent negative result, not a one-off.
- Commission amplifies but does not cause the loss.
- No positive result anywhere — no candidate for incubation.

**Strike 1 of 3 on the Variance-Ratio Mean Reversion hypothesis line.** If the next cycle on a refined version of this line also fails, the line is abandoned.

### What would be needed to revisit this line
1. **Tighten the regime filter:** VR threshold lower (e.g. 0.85 or 0.80) OR use VR(3), VR(5) instead of VR(2) — multi-scale VR is more robust.
2. **Increase entry displacement threshold:** 1.5–2.0 ATR instead of 1.2 — only enter on more extreme dislocations.
3. **Fix the SL/TP geometry:** If the thesis is mean reversion, the TP should be larger relative to SL (or SL should be wider relative to the expected reversion magnitude). Currently TP is too close relative to the noise level.
4. **Add a trend filter:** Avoid long entries when the longer-term trend (e.g. 200-bar SMA slope, or higher-TF displacement) is strongly in the opposite direction.
5. **Reduce trade frequency:** Larger cooldown, higher displacement threshold, or volume confirmation.

---

## 9. Next Cycle

### Pivot consideration

The VR1 line has just produced its first strike. Per the three-strikes rule, I have two more attempts on this conceptual line before abandoning it.

**Recommendation for next cycle:** Pivot to **H3 (Failed Continuation After Displacement)** — this is a related but distinct idea. Instead of fading displacement in a MR regime, the entry condition is: a large displacement bar (>2·ATR) is followed by a second bar in the same direction that fails to extend (lower high on up moves, lower low on down moves). This is a "failure of continuation" signal, which has a different (and potentially stronger) statistical basis than VR-filtered MR.

The failed-continuation idea does not depend on the VR regime filter, which was the weakest link in VR1. It uses a purely price-action condition (displacement + failure to extend) that is more directly testable.

### Alternative: refine VR1 with stricter parameters

If we stay on the VR1 line, the minimal change set is:
- `vrThreshold` 0.95 → 0.82
- `dispThresh` 1.2 → 1.8
- `slBuffer` 0.5 → 1.0 (wider SL)
- Add a trend filter: only take longs when `eq > eq[20]` (rising equilibrium), shorts when `eq < eq[20]`

But I lean toward pivoting to H3 because the VR filter at 15m is fundamentally noisy and the displacement threshold is fighting the market microstructure.

### Decision

**Next cycle: H3 — Failed Continuation Exhaustion (FCE), greenfield.** This is a new hypothesis line, not an iteration on VR1. VR1 is parked with strike 1; if we return to it, it will be after FCE is evaluated.

---

*Report saved to `data/reports/2026-09-24-1033-researcher-qm-vr1-v1.md`.*
*Pine source: `data/pine/qm_vr1_v1.pine`.*
*Backtest links: BTC 15m, ETH 15m, BTC 1h (see matrix above).*
