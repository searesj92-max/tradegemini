# Gertrude Decision — QM-VWAPDISP-v1 (VWAP displacement from-equilibrium fade)

Date: 2026-09-24
Report source: data/reports/2026-09-24-1745-researcher-qm-vwapdisp-v1.md
Metrics (verified / not verified): N/A — v4 exploratório (sem regime guard) gerou hipótese, mas v5/v6 (com regime guard) não foram rodados por crédits. v1 com regime guard gerou zero trades.
Verdict: ESTACIONAR
Rationale: Hipótese VWAP-displacement fade é matematicamente clara (z-score em relação ao VWAP, regime guard via |med−VWAP|). v1 com regime guard → zero trades (thresholds muito restritivos ou regime bloqueando tudo). v4 exploratório (sem regime guard) ainda não foi backtestado neste relatório — o relatório documenta a preparação dos Pine scripts v1-v6, mas os backtests v4 não têm resultados reportados. Crédits esgotados impedem avançar para v5/v6.
Next step: Quando crédits disponíveis: rodar v4 (exploratório, sem regime guard) em BTC/ETH/SOL em 15m/1h para ver se gera trades com PF > 1. Se sim, adicionar regime guard de v5 (vwap_slope_strict) e comparar. Se v4 também zero trades, ajustar thresholds antes de adicionar regime.
Human required: no
