# AI Trading Agent Workbook (Hermes)

Single-file, agent-native workbook. Paste into Hermes Agent (any profile) and follow top to bottom. When finished, the user has a working AI hedge fund research desk connected to Trader Dev MCP.

**Audience:** an AI agent (you) helping a human set up this system on Hermes Desktop.
**Repo local:** `C:\Users\seares\Desktop\botrade`
**Time:** 5–10 min for install + first backtest.

---

## Your mission

By the end the user can:

1. Ask you to write a Pine strategy from an idea.
2. Backtest it across crypto pairs and timeframes.
3. Optimise parameters or position sizing.
4. Audit for overfitting, drawdown, fragility.
5. Run the 4 Hermes profiles (gertrude/researcher/builder/optimizer) on recurring 15–30m schedules.

You do this via **Trader Dev MCP** (`https://mcp.trader.dev/mcp?key=<PK_TOKEN>`). This repo is the skills, prompts, and loop roles that tell you how to behave as a quant desk.

## What this is NOT

- Not a live trading bot (no real orders from this workbook).
- Not a financial advisor.
- Not a guarantee (backtests ≠ future performance).

## Hard rules

**TradingView-native only.** No funding, cross-exchange arb, off-chain sentiment, on-chain analytics, options flow.
Allowed: OHLCV, volume, Pine built-ins, `request.security(lookahead_off)`, multi-symbol, date/time math, ATR/pivots/Donchian/Bollinger/Keltner.

**Honest verdicts only:** Reject / Watchlist / Incubate / Candidate / Production candidate.

**Metric priority:** robustness across symbols > drawdown > profit factor > avg trade > trade count > TF stability > simplicity > net profit LAST.

**No repainting, no lookahead, no future data. No trailing stops.**

---

## Task 1 — Confirm environment

- [ ] You know the user is on **Hermes Agent** (Desktop/CLI, Windows).
- [ ] Working dir set to `C:\Users\seares\Desktop\botrade`.

## Task 2 — Install Trader Dev MCP

Give the user (or run via Hermes MCP setup):

```text
MCP server name: trader-dev
Transport: streamable HTTP
URL: https://mcp.trader.dev/mcp?key=<PK_TOKEN>
```

- [ ] User confirms `trader-dev` appears in MCP list (restart Hermes if needed).

## Task 3 — Verify connection

Call `tools/list` on `trader-dev`. Expect: `whoami`, `get_credits`, `search_strategies`, `create_strategy`, `run_backtest`, `optimize_strategy`, `compare_backtests`, `get_equity_curve`, `get_trades`, `fork_strategy`, `promote_strategy`, `demote_strategy`, `list_active_alerts`, `test_telegram_sink`, …

Then: `whoami` (authenticated) and `get_credits` (workable balance).

- [ ] tools/list OK · [ ] whoami OK · [ ] get_credits OK

## Task 4 — First backtest (pick one flow)

**A — user pastes Pine:** hygiene check (indicator vs strategy, repaint, lookahead) → `create_strategy` → `run_backtest` 5–10 random top-100 Bybit pairs × 1h+4h → report.

**B — new idea:** demand a *mathematical hypothesis* (not "RSI<30") → Quant Mathematician skill → backtest → report.

**C — improve existing:** `search_strategies` → pick signs-of-life → `fork_strategy` → ONE change → backtest → `compare_backtests`.

- [ ] One flow completed with structured report + verdict.

## Task 5 — Specialist skills

| Skill | File | Use |
|---|---|---|
| AI Hedge Fund Manager | `skills/ai-hedge-fund/SKILL.md` | coordination |
| Quant Mathematician | `skills/quant-mathematician/SKILL.md` | greenfield |
| Mean Reversion Engineer | `skills/mean-reversion-engineer/SKILL.md` | engineered MR |
| Strategy Optimizer | `skills/strategy-optimizer/SKILL.md` | fork & improve |
| Position Optimizer | `skills/position-optimizer/SKILL.md` | sizing/Kelly, entries frozen |

Read the file, adopt the persona, do the task, drop the persona.

- [ ] User knows the 5 skills; ≥ 1 loaded for their workflow.

## Task 6 — Loop roles (killer feature)

In Hermes, loops = cron jobs (see `COMANDOS-HERMES.md` Bloco 9):

```
researcher 15m → loop/01-quant-mathematician.md
builder    15m → loop/02-builder.md
optimizer  15m → loop/06-strategy-optimizer.md
gertrude   30m → loop/00-gertrude-desk-manager.md
gertrude   60m → loop/08-risk-manager.md
```

Each fire is independent; every role file is self-contained.

- [ ] ≥ 1 loop scheduled; user understands independence.

---

## Reference — standard research report

```markdown
# Trader Dev Research Report
## 1. Goal
## 2. Strategy or Hypothesis
## 3. Pine Script Changes
## 4. Backtest Matrix (symbols / timeframes / assumptions)
## 5. Results (net, PF, DD, WR, avg trade, trades, long/short, stability)
## 6. Robustness Analysis
## 7. Weaknesses
## 8. Next Iteration
## 9. Verdict: Reject / Watchlist / Incubate / Candidate / Production candidate
```

## Reference — MCP tool inventory

Always `tools/list` first. Expected groups: auth (`whoami`, `get_credits`) · lifecycle (`search/list/get/create/update/fork/delete/promote/demote/pause/resume`) · backtest (`run_backtest`, `quick_backtest`, `optimize_strategy`, `compare_backtests`, `get_backtest_result`, `get_equity_curve`, `get_trades`) · signals (`get_recent_signals`, `list_active_alerts`, `test_telegram_sink`).

Never guess arguments.

## Troubleshooting

| Problem | Fix |
|---|---|
| No trader-dev tools | rerun MCP install; restart Hermes |
| whoami unauthenticated | login at https://trader.dev/ or API key |
| insufficient credits | `get_credits` → top up at trader.dev |
| Pine won't compile | missing `@version=5` / `strategy()` / wrong entry API |
| Zero trades | entries too strict or short history |
| search_strategies empty | broaden query or seed at trader.dev |
| "go live now" request | refuse — paper/forward only; incubation + human gate |

## Risk disclaimer (state before any deployment talk)

Research and education only. No real orders from this workbook. Backtests ≠ future. Crypto volatile; leverage can wipe you out. Paper trade + forward test ≥ 20 trades / ~3 months before any live capital. Not financial advice.

## Next steps

1. Schedule loops (`COMANDOS-HERMES.md` Bloco 9).
2. Read `SKILL.md` for master workflow.
3. Read `docs/AGENT_GUIDE.md` for deep rules.
4. Incubation prompt `prompts/07-incubation.md` after first Candidate.

Done — user has a working AI trading research desk.
