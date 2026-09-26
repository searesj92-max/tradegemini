# Gertrude Decision — rsi-t200b SL/TP builder refinement

Date: 2026-09-24
Report source: data/reports/2026-09-24-1530-builder-rsi-t200b-sltp.md
Metrics (verified / not verified): N/A — Pine refinado e validado em higiene, mas backtest bloqueado (MCP credits = 0)
Verdict: ESTACIONAR
Rationale: Pine `rsi-t200b-builder-refined.pine` pronto (commission 0.05% MCP parity, SL/TP parametrizável, sem trailing, sem repaint/lookahead). Refinação de higiene aprovada. Porém o sweep de SL/TP nos 8 pares solicitado pelo dispatch anterior não pode executar sem créditos. A estratégia baseline (rsi-t200b) já tem result MCP confirmado em ciclo anterior (meanPF 2.01, maxDD 29.2%, 6/8 strict pass) — verNota: este relatório de builder é apenas a preparação, não os resultados.
Next step: Quando crédits retornarem, executar sweep SL/TP (mínimo 3 combinações) nos 8 pares do batch 3. Critério de melhoria: PF subir sem DD > 30% e trades ≥ 40 por par.
Human required: no (pode aguardar; ação humana opcional: verificar se weekly grant de 1000 credits já liberou no painel Trader Dev)
