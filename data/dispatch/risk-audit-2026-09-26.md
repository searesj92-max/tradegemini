# Dispatch — Risk Audit (Gertrude)

**Date**: 2026-09-26
**Role**: risk (Gertrude herself)
**Goal**: Auditar as estratégias em parked/rejected e reportar ao usuário sobre os bloqueios infráestrutura, sem consumir créditos MCP.

**Configuração**:
- Créditos MCP: 0 (bloqueado para qualquer backtest)
- Fork de estratégias de terceiros: bloqueado (403, plano pago necessário)
- Estratégias próprias do searesj92: potencialmente forkáveis (sem plano pago) — verificar com list_strategies

**Definition of done**:
1. Ler os 5 relatórios de decisão escritos neste ciclo (3 rejected, 2 parked).
2. Verificar no MCP se há alguma estratégia própria do searesj92 com sinais de vida (list_strategies) — sem consumir créditos.
3. Reportar ao usuário via resposta final: resumo executivo das classificações + status dos bloqueios.

**Constraints**:
- ZERO créditos MCP → qualquer ação que consuma créditos (backtest, quick_backtest, compare_backtests) é proibida.
- ZERO ordens reais.
- Sem modificar estratégias ou criar novas sem autorização.

**Prioridade**: comunicar o usuário que:
- 3 estratégias rejeitadas (H2-H1, LSN, REC) — sem vida, strikes acumulando
- 2 estratégias em parked (FCS-v1 com sinal real em ETH mas amostra insuficiente; AEGIS e FTMO bloqueados por infra)
- MCP credits = 0, reset em "Invalid Date" — backtests bloqueados
- Fork bloqueado (403) para contas free
- Para desbloquear: buy_credits OU /unlock-edge (exchange verification) OU upgrade de plano
