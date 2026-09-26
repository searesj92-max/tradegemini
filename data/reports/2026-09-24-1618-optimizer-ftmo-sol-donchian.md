# Strategy Optimizer Cycle Report

## 1. Strategy Found (name, source, why selected)

Candidate: **FTMO Guardrailed SOL Donchian Breakout (verify)**  
Source: Trader Dev public strategies, ID `01M1RZMTQJTS1K3PGW2VBR52VR` (author "Emanuel Palcuti")  
Why selected: SOLUSDT 15m, 1374 trades, PF ~12.96, max DD ~0.59%, win rate ~82%, honest-looking structure — Donchian breakout + 200 SMA trend filter + vol expansion + ATR trail (0.03) + hard SL (1.5 ATR) + FTMO daily/max-loss halt. One clear improvement surface: trailing exit tightness.

## 2. Original Performance (logic, strengths, weaknesses, metrics)

Logic (Pine v6 inspected):
- Donchian breakout (20-bar highest/lowest, shifted [1])  
- Trend filter: close > 200 SMA for longs, close < 200 SMA for shorts  
- Vol expansion: current ATR > 20-bar avg ATR  
- Position sizing: risk-based (riskPct=0.25% equity per trade) capped by max notional 50% equity  
- Exits: trail 0.03 ATR (trail_points/offset) + hard stop 1.5 ATR (loss)  
- Risk halts: daily loss halt 2% of initial capital, max account loss halt 8%, both trigger `strategy.close_all()`

Strengths:
- Transparent, no repaint/lookahead (only `ta.sma`, `ta.atr`, `ta.highest/lowest`, `strategy.entry/exit/close/close_all`, `process_orders_on_close=true`)  
- Controlled risk envelope (daily + max drawdown halts)  
- Decent trade count for a breakout system at 15m

Weaknesses / improvement hypothesis:
- Trail at 0.03 ATR on a 20-bar Donchian breakout may clip runners too early; the hard SL (1.5 ATR) still protects downside, so relaxing the trail is a low-risk one-variable experiment.

Original metrics (from search result `01M2TCXGREN87YPPW1A55Y5Y73`, same logic):
- netProfit: 65571.39 (USDT)  
- netProfitPct: 262.29%  
- profitFactor: 12.96  
- maxDrawdownPct: 0.59%  
- winRatePct: 82.02%  
- totalTrades: 1374  
- barsEvaluated: 29168  
- Window: 2025-02-25 → 2026-01-24 (approx, per fromTs/toTs)

## 3. Improvement Hypothesis

If the trailing exit is loosened from 0.03 ATR to 0.05 ATR (single change), the strategy should:
- Give more room to genuine SOL trends before exiting  
- Keep the hard SL (1.5 ATR) intact, so downside is not worsened structurally  
- Potentially raise average trade and net profit without meaningfully increasing max DD  
- Risk: slightly larger intra-trade drawdown per trade and possibly fewer trades if more get stopped out by the hard SL before trailing kicks in; must validate across pairs/TFs before any claim.

## 4. Fork Created (name, changes)

Fork blocked.  
Account tier: **free** (`user_3Jk6sKZKH1PpeBmDdC4fkwX3V4P`, `isPaid: false`).  
`fork_strategy` returned `403 fork_requires_paid_plan`.  

Attempted workaround: recreate the strategy as a new dev entry with identical Pine via `create_strategy`, then run `quick_backtest` with strategyId chain (git-style versioning) for both baseline (0.03 ATR) and modified (0.05 ATR). The recreate succeeded (new strategy ID `01M3ADK4BXZZQVXDF022WPP7J0`, name "FTMO Guardrailed SOL Donchian Breakout (baseline reproduce)", SOLUSDT 15m, 25000 capital, same broker profile).

Planned single change (NOT yet executed):  
- `atrMult`: 0.03 → 0.05 (ATR Trail Mult)  
- All other inputs unchanged: stopMult 1.5, smaLen 200, breakoutLen 20, volLen 20, riskPct 0.25, maxNotionalPct 50, dailyLossPct 2.0, maxAccountLossPct 8.0  
- Same Pine structure, same entry/exit IDs (`L`, `S`, `LX`, `SX`), same risk halts

## 5. Backtest Matrix

Planned matrix (not executed due to credits exhaustion):

| Sym | TF | Version | AtlMult | Hard SL | Note |
|-----|-----|---------|---------|---------|------|
| SOLUSDT | 15 | baseline reproduce | 0.03 | 1.5 ATR | same window as original (2025-02-25→2026-01-24) |
| SOLUSDT | 15 | modified v1 | 0.05 | 1.5 ATR | one-variable change |
| Additional (planned next) | 15/30/1h | both | both | both | multi-pair/multi-TF robustness check after SOL baseline |

Assumptions if run:
- commission 0.05%, margin 100/100, pyramiding 1, process_orders_on_close=true, initial_capital 25000, sizing percent_of_equity 100% (same as original)  
- Engine parity: tv_jul26

## 6. Results Comparison (original vs forked)

**Not available — backtest could not be executed.**

Error from `quick_backtest` (baseline reproduce attempt):

> "You have no credits remaining. Your free credits reset on Invalid Date. Upgrade to Pro to accumulate credits and never lose unused ones. …"

Because the engine did not run, no result IDs, no equity curves, no trades, no comparison. No numbers are reported here to avoid fabrication.

## 7. Robustness Check (multi-pair, multi-TF, outlier, overfit?)

Could not be performed. The original public backtest is SOL-only 15m; even if executed today, a single pair/TF is insufficient to claim robustness — the loop requires multi-pair/multi-TF. The Donchian + vol expansion + SMA filter is a reasonable structure, but without fresh backtests on other pairs (e.g. ETH, BTC, FIL, APT) and other TFs (30m, 1h), any conclusion would be speculation.

## 8. Decision: Keep / Reject / Iterate

**Stop — blocked by credits.**  
Cannot classify the change as keep/reject/iterate without a completed backtest and comparison. This cycle is terminated as a "no result" cycle, not as a rejection of the strategy or the hypothesis.

## 9. Next Cycle

Prerequisites to resume this candidate:
1. Restore Trader Dev credits (verify exchange at `/unlock-edge` for free credit doubling, or `buy_credits` / upgrade to Starter/Pro).
2. Re-run baseline reproduce backtest to confirm parity with the public result (sanity check before modifying).
3. Run modified version (atrMult 0.05) on SAME window/symbol for direct comparison.
4. If improvement holds on SOL 15m, extend to multi-pair/multi-TF (ETH, BTC, etc., 15m/30m/1h).
5. Compare via `compare_backtests`, inspect trades/equity curve, and decide keep/iterate/reject.

If credits remain unavailable next cycle, pivot to a candidate that can be recreated and backtested under available credits, or move to local backtesting and only use Trader Dev for final verification when credits return.

---

Report generated by Strategy Optimizer cycle. No real orders placed. Research/education only.
