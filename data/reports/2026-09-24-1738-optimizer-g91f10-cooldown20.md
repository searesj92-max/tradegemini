# Strategy Optimizer Cycle Report

## 1. Strategy Found

**Candidate:** `LIB-LITUSDT-G91-f10 1h-60d` (MCP id `01M1N6V3FD0M217BDSA3WV0EW0`), Bybit LITUSDT, 1h, author "Jeremy Vander Velde" (public).

**Why selected:** search_strategies on profit axis returned a homogeneous cluster of LTCUSDT EMA9-VWAP clones — not useful for attribution. Refreshed with a sharpe sort to find distinct edges. Picked `G91f10` LITUSDT 1h because:
- genuine edge (PF 3.0+, 586 trades, DD 7.3%)
- NOT the LTCUSDT breakout clone cluster dominating the profit leaderboard
- single pair with enough trades to diagnose entry/exit/cooldown, but still untested outside LIT (robustness question open)
- small coiled-up script — easy to attribute a single change

**Rejection note on alternatives considered:** SOLUSDT 15m Donchian variants had DD < 1% and PF 9–12 but a short window (many of them ~15 months or less) and that structure is much harder to attribute a single clean change without first establishing the regime; deferred.

## 2. Original Performance

**Source:** MCP public result (resultId `01M1N6TZ542DRFCC165N95AXHB`, 60d window 2026-03-05 → 2026-05-03).

| Metric | Value |
|---|---|
| Net profit (% on 10k) | 1,425.96% |
| Gross profit | 213,649.55 |
| Gross loss | 71,053.27 |
| Profit factor | 3.0069 |
| Max drawdown | 7.27% |
| Win rate | 64.33% |
| Sharpe | 24.74 |
| Sortino | 33.02 |
| Total trades | 586 |
| Winning trades | 377 |
| Losing trades | 209 |
| Bars evaluated | 1,021 |

**Logic (Pine v6, full source inspected):**
```pine
//@version=6
strategy("G91f10", overlay=true, pyramiding=1, process_orders_on_close=true,
  commission_type=strategy.commission.percent, commission_value=0.12,
  initial_capital=10000, default_qty_type=strategy.percent_of_equity,
  default_qty_value=100, margin_long=100, margin_short=100)

atr = ta.atr(14)
atrp = atr/close*100
atrm = ta.sma(atrp, 100)          // computed, NOT used anywhere

var int abierto = na
if (close > close[3] or close > close[12] or close > close[30]) and strategy.position_size == 0
    strategy.entry("L", strategy.long); abierto := bar_index
if (close < close[3] or close < close[12] or close < close[30]) and strategy.position_size == 0
    strategy.entry("S", strategy.short); abierto := bar_index

strategy.exit("LX", from_entry="L", loss=close*1.0/100/syminfo.mintick,
             trail_points=close*0.35/100/syminfo.mintick,
             trail_offset=close*0.35/100/syminfo.mintick)
strategy.exit("SX", from_entry="S", loss=close*1.0/100/syminfo.mintick,
             trail_points=close*0.35/100/syminfo.mintick,
             trail_offset=close*0.35/100/syminfo.mintick)

if strategy.position_size != 0 and not na(abierto) and bar_index - abierto >= 5
    strategy.close_all(); abierto := na
```

**Strengths:**
- Homogeneous breakout rule: long OR short if any of lags 3/12/30 pierce — simple, no multi-indicator soup
- Aggressive risk per trade (1% fixed stop, 35% ATR-trail offset) — high avg trade potential
- Built-in hard cooldown of 5 bars after any entry → prevents repeated whipsaw entries into the same micro-move
- ATR normalized and SMA'd over 100 bars computed (unused) → the infrastructure for a vol regime filter already exists in-code

**Weaknesses / diagnosis:**
- `atrm` is dead code — no regime/vol filter applied despite being calculated
- Cooldown of 5 bars is aggressive: a real 3-bar breakout can extend past 5 bars; `close_all()` at bar 5 may cut winners too early on trending days (LIT 1h)
- Entry fires on ANY of 3/12/30 — when market is sideways, lag-3 spikes trigger often → likely a chunk of the 586 trades sits in chop and the cooldown+small trailing offset is there to survive it; unclear what a longer cooldown does to that trade mix without backtest
- Only one pair + one timeframe in the public result — robustness across symbols/timeframes unproven (by design, candidate status)

## 3. Improvement Hypothesis

**One change:** extend the hard-cooldown from `bar_index - abierto >= 5` to `bar_index - abierto >= 20` (4×).

**Hypothesis:** a 5-bar forced close cuts moderate-trend winners before they fully develop; a 20-bar cooldown lets a 3/12/30-bar breakout run further when the move genuinely continues, without touching entry/slice/trailing stops. Net effect expected: fewer whipsaw resets, more avg trade when trend occurs, possibly fewer total trades, PF/WR direction TBD.

**What NOT changed (design constraint):** entry logic (OR lags 3/12/30) unchanged; SL 1% unchanged; ATR-trail 0.35 unchanged; sizing/cap/commission unchanged; `atrm` dead code NOT repurposed (would be a second change — deferred to a later cycle if cooldown is accepted).

**Attribution logic:** this is ONE parameter change to ONE control flow path (`close_all()` trigger) — results can be attributed to the cooldown, not conflated with entry or exit changes.

## 4. Fork Created

**Execution status — BLOCKED, no live fork was created.**

| Step | Attempt | Result |
|---|---|---|
| fork_strategy on `01M1N6V3FD0M217BDSA3WV0EW0` | POST `/strategies/01M1N6V3FD0M217BDSA3WV0EW0/fork` | **403 `fork_requires_paid_plan`** — forking another user's public strategy requires a paid plan; account is `free` tier |

Because a remote fork could not be created, the "fork" in this cycle is a **local Pine clone** (exact source, cooldown=20) used as the comparison arm.

**Fork source (local clone of original, change annotated):**
```pine
//@version=6
strategy("G91f10", overlay=true, pyramiding=1, process_orders_on_close=true,
  commission_type=strategy.commission.percent, commission_value=0.12,
  initial_capital=10000, default_qty_type=strategy.percent_of_equity,
  default_qty_value=100, margin_long=100, margin_short=100)

atr = ta.atr(14)
atrp = atr/close*100
atrm = ta.sma(atrp, 100)

var int abierto = na
if (close > close[3] or close > close[12] or close > close[30]) and strategy.position_size == 0
    strategy.entry("L", strategy.long); abierto := bar_index
if (close < close[3] or close < close[12] or close < close[30]) and strategy.position_size == 0
    strategy.entry("S", strategy.short); abierto := bar_index

strategy.exit("LX", from_entry="L", loss=close*1.0/100/syminfo.mintick,
             trail_points=close*0.35/100/syminfo.mintick,
             trail_offset=close*0.35/100/syminfo.mintick)
strategy.exit("SX", from_entry="S", loss=close*1.0/100/syminfo.mintick,
             trail_points=close*0.35/100/syminfo.mintick,
             trail_offset=close*0.35/100/syminfo.mintick)

// CHANGE: cooldown 5 → 20 bars
if strategy.position_size != 0 and not na(abierto) and bar_index - abierto >= 20
    strategy.close_all(); abierto := na
```
Every other line is bit-identical to the inspected original.

## 5. Backtest Matrix — NOT EXECUTED

**Attempted:** `quick_backtest` on LITUSDT, 1h, 2026-03-05 → 2026-05-03, identical commission/sizing (0.12%, percent_of_equity 100%, initialCapital 10000) for both arms (cooldown=5 baseline and cooldown=20 fork) — requested in parallel.

**Result:** blocked — **“You have no credits remaining. Your free credits reset on Invalid Date.”**

**Account state at cycle time:**
- `login` → authenticated, tier `free`, isPaid=false
- `get_credits` → balance=0, weeklyGrant=1000, weeklyResetAt="Invalid Date"
- `search_strategies` → still responded (reads, not credit-bound) — confirmed MCP reachable
- `fork_strategy` → 403 paid-plan gate (independent of credits)
- `quick_backtest` → credit gate

**Consequence:** No backtest result for fork vs original could be produced in this cycle. No comparison metrics (net/PF/DD/WR/avg/count) are available for this hypothesis. Per the loop's own stop conditions, "credits low → report and stop".

**Not fabricated:** nothing in this report claims a backtest was run. The 5-bar and 20-bar Pine are shown for reproducibility; the 20-bar outcome is unknown.

## 6. Results Comparison — NOT AVAILABLE

No fork or baseline backtest was completed in this cycle due to account limits (credit=0; fork requires paid plan for foreign strategy). No comparison table is presented.

## 7. Robustness Check — NOT DONE (no data)

Robustness checks (multi-pair LIT/SOL/BTC/ETH, multi-TF 15m/30m/1h/2h/4h, outlier/trade-concentrations, overfit look) require the fork backtest that was not executed. No evidence either way on whether the cooldown change survives outside LIT 1h.

## 8. Decision: PAUSE / RETRY NEXT CYCLE

**Cycle verdict:** incomplete — cannot keep/reject/iterate without a backtest.

**Reason:** operational blocker, not strategy verdict. The hypothesis (cooldown 5 → 20) is plausible and cleanly attributable, but no data supports or refutes it. Per the loop: "credits low · MCP down → report and stop."

**Recommended precondition to retry:**
1. Confirm credit availability: `get_credits` balance>0 (weekly grant may have reset — the `weeklyResetAt` field shows "Invalid Date" at this session, which needs clarification with the Trader Dev dashboard / account). If balance remains 0, buy credits or wait for reset.
2. Re-run the cycle:
   - If credits available AND at least one of (a) free-tier fork now permitted, or (b) strategy already forked into the user's account from a prior cycle, then `fork_strategy` → `quick_backtest` both arms → `compare_backtests`.
   - If fork still blocked but strategy is own-account, use `run_backtest` on the saved fork id (if one exists) for the baseline and re-`quick_backtest` the modified Pine for the fork arm.

**If credits never restore this week:** pivot to a candidate whose baseline result is already in the user's own account (owned strategies can be re-run with `run_backtest` — that path is credit-bearing too, but at least does not require a foreign fork). Review `list_strategies` own-account entries first.

**Under no circumstances:** do not promote this cooldown change to live without a completed backtest and a second-cycle confirmation.

## 9. Next Cycle

**Prerequisite:** credit balance > 0, and either fork permitted or an own-account strategy with existing results to compare.

**If retried on G91f10:**
1. `fork_strategy` (if now permitted) `01M1N6V3FD0M217BDSA3WV0EW0` → named fork.
2. Apply cooldown 5 → 20 (single change) via `update_strategy` or `quick_backtest` with modified Pine.
3. Backtest BOTH arms (cooldown=5 and cooldown=20) on LITUSDT 1h, 60d window, identical params → `compare_backtests`.
4. If fork wins on PF/avg-trade without DD expansion and trade distribution still sensible → test same fork on 2–3 extra pairs (SOLUSDT, BTCUSDT, ETHUSDT) × 1h and one lower TF (30m) for robustness before keep.
5. If no gain or DD/winrate degrades → reject this change, log strike, next-cycle pivot.

**If G91f10 path blocked again:** select a different candidate from the sharpe-sorted list whose baseline is already in the user's own account (owned id → can `run_backtest`), prefer one with ≥ 100 trades and DD > 3% so a change candidate is actually testable, single change, compare, decide.

**Stop condition check this cycle:** credits=0, fork blocked → reported and stopping. Next cycle should re-check credit state before doing search work that cannot be completed.

---

**Post-mortem note:** This cycle did genuine selection and Pine inspection work but hit two independent account gates (fork paid-plan gate + credit gate) before the backtest step. The improvement hypothesis and both Pine arms are recorded here reproducibly so the next cycle can execute the comparison without re-doing the inspection, once credits/plan allow.
