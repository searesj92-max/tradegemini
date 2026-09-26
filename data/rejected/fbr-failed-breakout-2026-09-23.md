# Gertrude Decision — FBR (Failed Breakout Reversal, QM-FBR-v1/v2)

Date: 2026-09-23
Report source: data/reports/2026-09-23-1655-researcher-fbr-reject.md

Metrics:
- v1 BTC 1h: Net -87.9% · PF 0.63 · DD 88% · WR 23.4% · Trades 947
- v2 BTC 1h (+ADX): Net -61.9% · PF 0.64 · DD 62.2% · WR 19.4% · Trades 468
- Multi-symbol v2 (ETH/SOL/XRP 1h): todos negativos (PF 0.84–0.87, DD 38–54%)

Verdict: **REJEITAR**

Rationale:
- PF < 1 em todas as configurações; DD > 30% em todos; WR ~20–23%.
- v2 melhorou trade count e DD em relação à v1, mas não melhorou PF ou WR — o filtro de regime removeu sinais, mas os trades restantes também não têm edge.
- Three strikes em uma única iteração (v1, v2, multi-símbolo) → linha abandonada.
- Conclusão do autor: "sweep em range frequentemente continua, não reverte" — hipótese H2 falhou.
- Linha H2 está morta; não retomar sem mudança de conceito.

Next step: linha abandonada. Próxima hipótese pelo researcher (H3/H4 ou novo conceito).

Human required: no.
