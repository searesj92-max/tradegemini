# Gertrude Decision — VND-FTD (QM-VND-FTD v1/v1b)

**Date:** 2026-09-24

**Strategy code:** QM-VND-FTD (H1 — Volatility-Normalized Displacement + Follow-Through Decay)
**Agent:** researcher

**Backtests:**
- BTC 1h v1: Net -16.9% · PF 0.50 · DD 17.8% · WR 28.4% · 116 trades
- ETH 1h v1: Net -9.3% · PF 0.78 · DD 15.1% · WR 29.9% · 157 trades
- SOL 1h v1: Net -20.8% · PF 0.56 · DD 24.7% · WR 23.4% · 158 trades
- BTC 1h v1b: Net -18.9% · PF 0.39 · DD 19.2% · WR 31.3% · 112 trades
- ETH 1h v1b: Net +1.9% · PF 1.07 · DD 6.9% · WR 37.1% · 124 trades
- SOL 1h v1b: Net -19.3% · PF 0.54 · DD 23.0% · WR 22.3% · 157 trades

**Verdict: REJEITAR**

**Rationale:**
- 5 de 6 backtests com PF < 1; única exceção ETH v1b PF 1.07 marginal, não replicável.
- Three strikes claros: v1 BTC negativo, v1b BTC negativo, SOL negativo em ambas as versões.
- WR baixo (23–37%) indica stops sendo batidos — big moves frequentemente continuam, não exaurem.
- Não há edge universal cross-symbol em 1h para H1.
- Hipótese H1 abandonada com três strikes — pivotar para H2/H3 em próxima rodada.

**Próximo passo:** novo conceito de greenfield no próximo dispatch do researcher.

**Human required:** no (rejeição automática por falta de edge replicável).
