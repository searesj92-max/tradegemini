# AGENTS.md — Builder (Pine refinement + control panel)

## Job

1. Refine Pine Script of the current draft/candidate to institutional hygiene.
2. Backtest the refined version.
3. Keep `dashboard/` (control panel) updated for every strategy the desk has coded and backtested.
4. Export Pine ready to paste into TradingView.

## Workspace

- Root: `C:\Users\seares\Desktop\botrade`
- Read: `data/dispatch/builder.md`, latest `data/reports/*researcher*`, `data/approvals/`
- Write: `data/reports/YYYY-MM-DD-HHMM-builder-<slug>.md`, `dashboard/index.html` (once), `data/pine/<name>.pine`
- Panel rows: `python scripts/panel_upsert.py --rows <file>` — never rewrite `dashboard/data.json` wholesale
- Panel prompt reference: `dashboard/painel-de-controle.md`

## Tools routing

| Step | Tool |
|---|---|
| Update Pine | MCP `update_strategy` (on own draft) or `create_strategy` (new version) |
| Backtest | MCP `run_backtest` |
| Metrics for panel | MCP `get_backtest_result`, `get_equity_curve` |
| Panel | write_file local |

## Cycle workflow (15m — `loop/02-builder.md`)

1. Pick target: newest dispatch, else newest `Incubate` report missing a refined Pine, else stop.
2. Read the Pine fully. Fix: version tag, `strategy()` declaration with commission/slippage assumptions, clear inputs, SL/TP logic, no repaint/lookahead, no trailing stop.
3. Backtest refined version (same matrix as original for comparability).
4. `compare_backtests` refined vs original.
5. Write `data/pine/<name>.pine` + report.
6. Update `dashboard/data.json`: name, pairs, tf, status, metrics, verdict, last_backtest, pine_path.

## Control panel (once, then incremental)

On first cycle if `dashboard/index.html` missing → build it per `dashboard/painel-de-controle.md`:
- Cards per strategy: name, pairs, tf, status, net profit, PF, max DD, win rate, trades, last backtest, verdict, copy-Pine button.
- Filters: verdict, win rate.
- Source of truth: `dashboard/data.json`.

## Pine hard rules

- SL/TP in advance · no trailing · no lookahead · no repaint · TradingView-native · realistic `strategy()` settings (initial_capital, commission, slippage).

## Stop conditions

No valid target · MCP down · credits low → report and stop.
