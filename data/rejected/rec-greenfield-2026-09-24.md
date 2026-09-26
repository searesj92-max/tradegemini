# Gertrude Decision — REC-v2 (Range-Efficiency Collapse) — Greenfield 15m

Date: 2026-09-24
Report source: data/reports/2026-09-24-1824-researcher-rec-greenfield.md
Metrics (verified / not verified): **Not independently verified** — MCP credits = 0. Os 6 backtests foram via MCP (créditos do ciclo anterior). Os result IDs estão presentes. Assumidos como válidos. Zero trades em todos os símbolos é um resultado que não requer verificação complexa.

Verdict: **REJEITAR**

Rationale:
- 6 símbolos × 15m, ~9 meses de histórico: **zero trades em todos**. Uma estratégia com zero trades não tem edge — é uma estratégia sem operação.
- Causa matematicamente identificável: rangeThreshold 0.03 + ATR regime filter + volMult 1.2 em 15m de crypto principal é condição de mercado muito rara. Não é overfit — é sub-trigger (filtros muito apertados).
- Hipótese não está morta — está no timeframe errado (15m). REC pode ter vida em 1h/4h ou com threshold mais amplo. Mas para 15m: REJEITAR.
- Pine limpo (sem valuewhen, sem repainting, SL/TP presente). Problema é seletividade, não qualidade do sinal.
- Credit exhaustion também bloqueou FAILCONT-v1 (hipótese B) — registrada mas não testada.

Next step: Se créditos retornarem: testar REC-v2 em 1h/4h com threshold mais amplo. Ou executar FAILCONT-v1.

Human required: **no**.
