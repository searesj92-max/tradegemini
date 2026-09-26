# Gertrude Decision — H2-H1 Greenfield (QM-SAT-SweepSnap + QM-MeanReversion-ADR)

Date: 2026-09-26
Report source: data/reports/2026-09-26-1530-researcher-h2-h1-greenfield.md
Metrics (verified / not verified): **Not verified** — MCP credits = 0, não foi possível independentemente confirmar os números via get_backtest_result. Backtest local do researcher (Binance OHLCV público) assumido como razoável, mas sem validação MCP.

Verdict: **REJEITAR**

Rationale:
- H2 (Sweep+Snapback): PF máximo 0.73 (ETH), 0.65 (BTC). Nenhum PF ≥ 1.0 em 49 combos SL/TP testados. ADX filter matou 100% dos sinais em 1h. EMA200 não recuperou edge. WR artificial alta com PF fraco (ex: 58.7% WR, PF 0.54). 2 ciclos sem edge → strike 2/3.
- H1 (MeanReversion): PF máximo 0.87 (<1.0). 1 ciclo sem edge → strike 1/3.
- Ambos REJEITAR: critérios de incubação não atendidos (PF ≥ 1.3 em ≥ 5 pares, DD ≤ 30%, ≥ 50 trades, cross-TF stability).
- Créditos zerados impede validação independente, mas os números locais são suficientes para rejeição (não é caso borderline).

Next step: Pivot para nova hipótese. Os strikes contam: H2 ↑ strike 2, H1 ↑ strike 1.

Human required: **no** (rejeição clara, não requer aprovação para rejeitar).
