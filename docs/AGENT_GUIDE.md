# Agent Guide — regras profundas para o desk

This repo is designed to be read by AI agents (Hermes profiles).

## Onboarding checklist for any agent

1. Read `SKILL.md`.
2. Confirm Trader Dev MCP is connected (`tools/list`).
3. Inspect available MCP tools and schemas.
4. Do not guess missing tool arguments.
5. Ask for missing information only when required.

## Strategy lifecycle rules

- Start with `search_strategies` where the role allows it (optimizer yes, researcher no — greenfield only).
- Pick strategies with potential.
- Fork before editing.
- Change one main idea at a time.
- Compare every fork against the original (`compare_backtests`).

## Verdict labels (only these)

`Reject` · `Watchlist` · `Incubate` · `Candidate` · `Production candidate`

## Metric priority

1. Robustness across symbols
2. Drawdown control
3. Profit factor
4. Average trade quality
5. Trade count reliability
6. Stability across nearby timeframes
7. Simplicity
8. Net profit

## Multi-agent communication

- Agents do NOT chat with each other via tokens.
- Write structured files: `data/reports/`, `data/dispatch/`, `data/approvals/`.
- Gertrude is the only profile with the Telegram gateway for approvals.
- Each fire of a loop is independent — every role file is self-contained.

## Stop conditions (every loop)

- Trader Dev MCP unreachable → report and stop.
- Credits below threshold → report and stop.
- No productive work possible this cycle → report and stop (don't fake it).

## Hard prohibitions

- No real orders from any loop.
- No trailing stops in strategy code (video rule — latency puts you in loss).
- No off-chain data (funding, sentiment, on-chain) unless redesigned as price-action equivalent.
- No promoting to production without human gate.
