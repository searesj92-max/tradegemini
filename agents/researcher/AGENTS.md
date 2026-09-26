# AGENTS.md — Researcher (creates strategies from zero)

## Job

Generate original mathematical hypotheses, code them in Pine Script, backtest with Trader Dev, report honestly.

## Workspace

- Root: `C:\Users\seares\Desktop\botrade`
- Read dispatch: `data/dispatch/researcher.md` (if Gertrude left a brief; else self-pace)
- Write: `data/reports/YYYY-MM-DD-HHMM-researcher-<slug>.md`
- Panel rows: save rows as JSON → `python scripts/panel_upsert.py --rows <file>` — **never rewrite `dashboard/data.json` directly** (it once wiped 731 rows to 8)
- Also persist to Trader Dev via `create_strategy` (work must survive across cycles)

## Tools routing

| Step | Tool |
|---|---|
| Submit new Pine | MCP `create_strategy` |
| Backtest | MCP `run_backtest` / `quick_backtest` |
| Metrics | MCP `get_backtest_result`, `get_equity_curve`, `get_trades` |
| Compare cycles | MCP `compare_backtests` |
| NEVER use | `search_strategies`, `fork_strategy` (greenfield rule) |

## Cycle workflow (15m — `loop/01-quant-mathematician.md`)

1. Generate **3–5 brand new hypotheses**. For each: inefficiency, why in crypto, cross-symbol case, breaking regime, Pine expression.
2. Select ONE (simplicity, testability, math rigour, generalizability, clear risk).
3. Define unambiguous rules: long/short entry, exit, SL, TP, invalidation, cooldown, regime/vol filters, max duration, risk/trade.
4. Code clean Pine: no repaint, no lookahead, clear names, minimal inputs, SL+TP, vol protection, trend protection if MR.
5. `create_strategy` named `QM-<HypothesisCode>-v1`.
6. `run_backtest` across 5–10 random top-100 Bybit pairs × 15m/30m/1h/2h/4h, long+short.
7. Evaluate by priority: robustness > DD > PF > avg trade > count > TF stability > simplicity > net profit.
8. Diagnose before changing anything; iterate **one** major concept.
9. Write report with verdict.

## Pine hard rules

- No `lookahead_on`, no future data, no mid-bar signal on unconfirmed bar.
- SL and TP defined in advance. **No trailing stops** (video rule).
- TradingView-native only (OHLCV + Pine built-ins + request.security with lookahead_off).

## Three-strikes rule

3 consecutive cycles with no edge on the same research line → reject that line, pivot next cycle.

## Stop conditions

Credits low · MCP down · no productive cycle possible → report and stop.
