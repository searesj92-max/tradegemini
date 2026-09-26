# AGENTS.md — Optimizer (fork + sweep + compare)

## Job

Search for strategies with potential, fork them, improve ONE variable (or run MCP parameter sweep), backtest multi-pair/multi-TF, compare vs original, keep only genuine improvements.

## Workspace

- Root: `C:\Users\seares\Desktop\botrade`
- Read: `data/dispatch/optimizer.md`, `data/approvals/` (candidates to improve)
- Write: `data/reports/YYYY-MM-DD-HHMM-optimizer-<slug>.md`, update panel via `python scripts/panel_upsert.py --rows <file>` (never rewrite `dashboard/data.json` wholesale)

## Tools routing

| Step | Tool |
|---|---|
| Find candidates | MCP `search_strategies` |
| Inspect | MCP `get_strategy` |
| Preserve baseline | MCP `fork_strategy` |
| Apply change | MCP `update_strategy` or `optimize_strategy` (sweep) |
| Verify | MCP `run_backtest` / `quick_backtest` |
| Diff | MCP `compare_backtests` |
| Diagnose | MCP `get_equity_curve`, `get_trades` |

## Candidate selection

Good: positive PF but poor DD · good WR weak avg trade · good entries bad exits · strong on 1 pair untested elsewhere · too many chop trades · good longs bad shorts · simple edge needing better risk.

Avoid: < 50 trades · 1 pair only · unrealistic curves · repaint/lookahead · 10+ tightly-tuned inputs · one giant trade carries it · collapses outside original market.

## Cycle workflow (15m — `loop/06-strategy-optimizer.md`)

1. `search_strategies` → pick ONE candidate.
2. `get_strategy` → understand fully → improvement hypothesis.
3. `fork_strategy` → clear fork name.
4. Apply **ONE** major change (or one `optimize_strategy` sweep on a small grid).
5. `run_backtest` across random top-100 Bybit pairs × 15m/30m/1h/2h/4h.
6. `compare_backtests` fork vs original.
7. Decision: keep / reject / iterate. Persist via `update_strategy`.
8. Report in the standard optimizer format.

## Improvement areas (must map to a diagnosed weakness)

Regime detection · vol filtering · trend/chop classification · entry timing · exit logic · SL placement (ATR vs fixed) · TP structure · cooldown · session filter · false-breakout detection · MR confirmation · momentum exhaustion · trend-avoidance for MR.

## Priority of metrics

Robustness > DD > PF > avg trade > count > TF stability > simplicity > net profit.

## Three-strikes rule

3 cycles iterating one strategy with no gain → abandon, pivot next cycle.

## Stop conditions

No candidates · credits low · MCP down → report and stop.
