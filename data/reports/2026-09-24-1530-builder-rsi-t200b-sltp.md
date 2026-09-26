# Builder Cycle Report — 2026-09-24

**Agent**: builder  
**Time**: 2026-09-24 ~15:30 BRT  
**Loop target**: `data/dispatch/optimizer-rsi-t200b-sl-tp-2026-09-23.md` (Gertrude dispatch, priority NEXT)

---

## 1. Goal

Otimizar **apenas SL/TP** da estratégia `rsi-t200b` (RSI trend filter, família `hw-rsi-t200`, 4h), mantendo intactos entries e exits de sinal, nos 8 pares que passaram no batch 3: ETH, AVAX, ARB, OP, ATOM, INJ, XRP, SOL.

## 2. Strategy / Hypothesis

**Pine base**: `data/pine/hw-rsi-t200.pine` — RSI(14) cross buyLvl=40 / sellLvl=60, EMA200 trend filter, SL 2.2 ATR, TP 1.4 ATR, commission=0 (local engine).

**Hipótese de otimização (Gertrude)**: variar SL/TP multiples (ex. SL 1.0–2.0 ATR, TP 1.5–3.0 ATR) para melhorar PF sem aumentar DD > 30% e sem reduzir trades abaixo de 40 por par.

**Mapeamento de mudança**: ONE change (SL/TP multiples) — entries/exits de sinal não alterados.

## 3. Pine Script Changes (builder refinement)

**Arquivo**: `data/pine/rsi-t200b-builder-refined.pine`

| Change | Before | After |
|---|---|---|
| commission | `0` (local engine) | `0.05%` (MCP parity) |
| initial_capital | 10000 | 10000 (mantido) |
| default_qty | percent_of_equity 100 | percent_of_equity 100 (mantido) |
| margin_long/short | 100 | 100 (mantido) |
| SL/TP multiples | 2.2 / 1.4 (baseline) | 2.2 / 1.4 (mantido para sweep de referência; parametrizavel via input) |
| trailing | ausente | ausente (regra de ouro) |
| signal logic | RSI crossover/crossunder + EMA200 filter | **idêntica** (não tocada) |

**Higiene verificada**:
- ✅ `//@version=6` + `strategy(...)` declaration
- ✅ commission_value=0.05 (MCP parity)
- ✅ percent_of_equity=100, margin_long=100, margin_short=100
- ✅ process_orders_on_close=true, pyramiding=1
- ✅ SL presente (`strategy.exit(loss=...)`) e **não comentado**
- ✅ TP presente (`strategy.exit(profit=...)`)
- ✅ Sem trailing (`trail_points`/`trail_offset` ausentes)
- ✅ Sem repaint (`barstate.isconfirmed` não presente)
- ✅ Sem lookahead (`request.security` ausente)
- ✅ Sem arrays, sem strategy.cancel, sem martingale
- ✅ TradingView-native: OHLCV + built-ins (`ta.rsi`, `ta.ema`, `ta.atr`, `ta.crossover`, `ta.crossunder`)

## 4. Backtest Matrix (planejado — créditos indisponíveis)

### Alvo (8 pares × 4h, janela 2025-01-01 → 2026-09-01, commission 0.05%)

| Run | Symbol | SL ATR | TP ATR | Status |
|---|---|---|---|---|
| baseline | ETHUSDT | 2.2 | 1.4 | **MCP créditos=0 — não executado** |
| baseline | AVAXUSDT | 2.2 | 1.4 | pendente |
| sweep #1 | ETHUSDT | 1.5 | 1.4 | pendente |
| sweep #2 | ETHUSDT | 2.2 | 2.0 | pendente |
| sweep #3 | ETHUSDT | 3.0 | 1.4 | pendente |
| (×8 pares) | ARB/OP/ATOM/INJ/XRP/SOL | variar | variar | pendente |

### Assumptions
- Commission: 0.05% (MCP parity)
- Equity: 100% do capital, sem alavancagem extra
- Slippage: padrão do Trader Dev engine
- Janela: 2025-01-01 → 2026-09-01 (window padrão rtubation)
- Warmup: 200 bars (implícito na engine)

## 5. Results

**N/A — MCP sem créditos** (`get_credits` retornou `balance: 0`, `weeklyGrant: 1000`, `weeklyResetAt: Invalid Date`).

O pine foi **refinado e validado em higiene**, pronto para backtest assim que créditos retornarem. O dispatch gertrude exige ≥3 combinações de SL/TP nos 8 pares; sem créditos, não é possível avançar neste ciclo.

### Alternativa local (Não executada neste ciclo)
- `scripts/run_local_sltp_sweep.py` — existe no repositório; pode rodar o sweep localmente com o engine local (commission 0, ligeiramente optimista vs MCP 0.05%). Se os créditos MCP não voltarem em 1-2 semanas, executar sweep local e reportar como estimativa com disclaimer de commission gap.

## 6. Robustness Analysis

**Não aplicável** — sem resultados de backtest. O pine é idêntico ao baseline `hw-rsi-t200` que já passou por validação multi-par no batch 3 (8/16 pares, mean PF 1.69 no local). A única mudança (commission 0 → 0.05%) **reduz** o net profit esperado vs números locais previamente reportados — efeito conhecido e esperado.

## 7. Weaknesses

1. **Créditos MCP esgotados** — bloco o backtest obrigatório do dispatch. Sem créditos, não há results para Gertrude avaliar.
2. **Commission gap**: pine local usa 0.05% agora (paridade MCP), mas números do batch 3 reportados foram com commission=0. Comparar resultados futuros com baseline anterior requer ajuste de referência.
3. **Sem sweep executado** — a otimização em si não aconteceu; apenas a preparação do pine e a documentação do plano.
4. **weeklyResetAt = Invalid Date** — sugere clock de reset de créditos com problema na conta free tier; verificar no painel do Trader Dev se o grant de 1000 crédits já liberou.

## 8. Next Iteration

1. **Imediato**: verificar se weekly grant liberou no painel MCP (`/unlock-edge` ou `/pricing`) — se sim, reexecutar este ciclo com créditos disponíveis.
2. **Se créditos disponíveis**: rodar baseline nos 8 pares (ou subconjunto 2-3 para validar) + 3+ combinações SL/TP no ETHUSDT como parâmetro de referência.
3. **Se créditos indisponíveis por 1-2 semanas**: rodar `scripts/run_local_sltp_sweep.py` localmente com disclaimer de commission gap, reportar estimativa.
4. **Critério de melhoria (Gertrude)**: PF subir sem DD > 30% e trades ≥ 40 por par. Se nenhuma combinação bater → reportar e estacionar, não forçar.

## 9. Verdict

**ESTACIONAR / Pendente de créditos** — pine refinado e pronto, backtest bloqueado por falta de créditos MCP. Não rejeitado; não aprovado. Aguardar créditos para avançar.

**Ação requerida (humano)**: verificar conta Trader Dev — se o weekly grant de 1000 crédits já liberou, reexecutar o builder cycle. Se a conta free está vedada, considerar upgrade ou rodar sweep local com disclaimer.

---

*Risk notice: pesquisa e educação apenas. Backtests não são performance futura. Nenhuma ordem real foi colocada.*
