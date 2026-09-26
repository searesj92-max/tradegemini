# TxFlow DEX Integration (research)

> Status: **research / blocked on public API** — no order routing, no agent keys. Human approval always required.

## Venue (verified 2026-09-23 from docs.txflow.com)

| Item | Value |
|---|---|
| Product | **TxFlow L1** + fully on-chain **perp CLOB** DEX |
| Docs | https://docs.txflow.com |
| App (mainnet) | https://app.txflow.com — **Access Code required** (Discord) |
| App (testnet) | https://txflow-testnet.xyz — faucet 1.000 test USDC / h |
| Platform API | **“Coming Soon…”** (docs.txflow.com/api-reference) |
| npm `txflow-sdk` | **Unpublished 2026-07-16 (404)** — do not install from cache |
| TIP SDK | Channel builders (Liquidity/Settlement/MarketData/Risk) — **not** a trading bot SDK |
| Collateral | native **USDC** (Arbitrum / Polygon PoS; also Base/ETH/Solana for deposit) |
| Enable trading | one-time **gas-less** signature (EOA wallet; **never AA wallet** — funds lock risk) |
| Fees (perp VIP0) | **maker 0.015%** · **taker 0.045%** (14d volume tiers) |
| Funding | settlement **every 1 / 4 / 8h** by contract · cap ±0.05% per window |
| Order types | Limit, Market, **Post-Only**, **Reduce-Only**, TIF GTC/IOC · market slippage tol. **5%** |

## Why it could fit the desk (later)

1. USDC perps on same symbols as backtests (BTC/ETH/…).
2. Maker/taker fees comparable to desk commission assumptions (local mcprule uses 0; public forks 0.05%).
3. Testnet allows **paper/live-shape** rehearsal with zero real funds.
4. If/when Platform API ships, same MCP/HTTP pattern as Trader Dev is possible.

## Blockers (honest)

1. **No public REST/MCP trading API yet** — cannot wire Hermes order path.
2. **npm SDK gone** — no stable agent client package.
3. Mainnet needs **access code**; testnet is separate balances.
4. Wallet onboarding is **browser + signature** oriented (Privy/email or MetaMask) — agent hot-wallet flow unclear until API docs.
5. Thin alt liquidity + on-chain latency can dominate 4h swing edges.

## Hard rules (desk)

1. **Never** place real orders from a loop.
2. No seed/private keys in repo; env/secrets only.
3. Prefer **testnet** first; mainnet only after Gertrude + human confirm.
4. Every live order logs to `data/reports/` + Telegram.
5. AA wallets forbidden (docs danger hint).

## Phased plan

| Phase | Action | Status |
|---|---|---|
| 0 Read-only | markets/fees/funding into Mission Control “Venue” tab | research done |
| 1 Testnet | manual orders on txflow-testnet.xyz mirroring desk signals | **user action** (need account) |
| 2 API paper | when Platform API docs go live → read-only MCP first | blocked |
| 3 Live gated | single symbol, min size, hard SL, human confirm per order | blocked |

## Next concrete step (user)

1. Decide: **testnet** (recommended) vs mainnet access code via Discord.
2. Watch docs → `api-reference` until “Coming Soon” is replaced.
3. Do **not** ship order code until a documented API + auth model exists.

---
*Risk notice: research only. DEX perps can lose entire position. Not financial advice. Backtest ≠ fill quality on venue.*
