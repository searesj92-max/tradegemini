# Gertrude Decision — VOL-REVERSION-v1 (Volatility-Normalized Displacement Reversion)

**Data:** 2026-09-24  
**Relatório fonte:** `data/reports/2026-09-24-1500-researcher-qm-vol-reversion-v1.md`  
**MCP strategy ID:** 01M3ACZ5NDCX9H0VBFK96KZKGM (criado em dev, sem backtest)  
**Metriques:** N/A — sem backtest executado

**Veredito: ESTACIONAR (parked — bloqueado por infraestrutura)**

**Rationale:**
- Hipótese matematicamente limpa: z-score = (close - EMA_fast) / ATR_fast, com regime filter (ADX 15–50, EMA slope, ATR_ratio < 2.5). Entrada quando preço esticado além de equilíbrio em regime não-tendente.
- Pine Script validado pelo MCP parser (v6, process_orders_on_close, sem forbidden calls, sem repaint/lookahead, SL+TP em ATR units, time exit 120 bars, cooldown 3 bars).
- **Bloqueio:** créditos MCP zerados. Backtest não executado. Sem evidência estatística de edge.
- Não é rejeitado: a hipótese não foi falsificada, apenas não testada.

**Next step (próximo ciclo, quando créditos disponíveis):**
1. Rodar painel mínimo de validação: BTC + ETH × 5 TFs (10 runs) para checar se há sinais de vida.
2. Critério de continuação: PF≥1.2 em ≥3 dos 10 runs, DD≤35%, ≥30 trades no conjunto.
3. Se continuar: iterar UMA mudança maior (ex: ajustar zEntry/slMult/tpMult com base nos resultados, ou adicionar filtro de volume-baseline).
4. Se não continuar: rejeitar a linha e pivotar para false-breakout-reversal ou liquidity-sweep-snapback.

**Aprovação humana requerida:** não (parked). Human action requerida para desbloquear créditos.

**Créditos MCP:** 0 no momento do relatório. Condição de saída: créditos disponíveis.
