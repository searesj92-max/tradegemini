# Builder Cycle Report — 2026-09-24

**Agent**: builder
**Time**: 2026-09-24 ~18:30 BRT
**Loop target**: `data/reports/2026-09-24-1618-researcher-qm-fcs-v1.md` (WATCHLIST, Pine com bug de SL documentado)

---

## 1. Goal

Refinar o Pine **QM-FCS-v1** (Failed Continuation / Liquidity Sweep Snapback) reportado pelo researcher em 2026-09-24, corrigindo o bug de SL documentado no relatório e aplicando higiene de código. Backtest via MCP estava planeado mas **bloqueado por créditos zerados** (`balance: 0`).

## 2. Strategy or Hypothesis

**Hipótese H1 (researcher):** candles que tocam extremo recente (high/low de N barras) mas fecham de volta para dentro do range são breakouts falhados → snapback com viés de reversão. SL natural = extremo do sweep ± buffer ATR.

**Estado anterior:** WATCHLIST (parked por Gertrude). ETH 15m: PF 1.57, 117 trades, DD 3.6% (sinal robusto). BTC negativo em todos os TFs (cross-symbol fraco). Bug de SL presente na versão backtestada.

## 3. Pine Script Changes (builder refinement)

**Arquivo:** `data/pine/qm-fcs-v1-builder-refined.pine`

| Change | Before (researcher draft) | After (builder-refined) |
|---|---|---|
| SL bug (long) | `rangeL * (1 - slBuffer * atrVal / close)` — multiplicativo, buffer desprezível em preço alto | `rangeL - atrVal * slBuffer` — offset absoluto correto |
| SL bug (short) | `rangeH * (1 + slBuffer * atrVal / close)` — multiplicativo | `rangeH + atrVal * slBuffer` — offset absoluto correto |
| Reemissão de exit | `strategy.exit` dentro do if position_size (OK, mas sem comentário de engine-safety) | Mesma estrutura + comentário documentando que reemitido a cada bar é engine-safe |
| commission | 0.05% (já presente no draft) | 0.05% mantido (MCP parity) |
| process_orders_on_close | true (já presente) | true mantido |
| pyramiding | 1 (já presente) | 1 mantido |
| trailing | ausente (regra de ouro) | ausente confirmado |
| repaint | ausente (entradas no close) | ausente confirmado |
| lookahead | ausente (sem request.security) | ausente confirmado |
| Comments | mínimos | adicionados cabeçalho de ciclo + explicação da correção de SL |

**Higiene verificada:**
- ✅ `//@version=6` + `strategy(...)` declaration
- ✅ commission_value=0.05 (MCP parity)
- ✅ percent_of_equity=100, margin_long=100, margin_short=100
- ✅ process_orders_on_close=true, pyramiding=1
- ✅ SL presente (`strategy.exit(loss=...)`) e **não comentado**
- ✅ TP presente (`strategy.exit(profit=...)`)
- ✅ Sem trailing (`trail_points`/`trail_offset` ausentes)
- ✅ Sem repaint (`barstate.isconfirmed` não presente; entradas no close)
- ✅ Sem lookahead (`request.security` ausente)
- ✅ Sem arrays, sem strategy.cancel, sem martingale
- ✅ TradingView-native: OHLCV + built-ins (`ta.rsi`, `ta.ema`, `ta.atr`, `ta.highest`, `ta.lowest`, `ta.crossover`, `ta.crossunder`)

## 4. Backtest Matrix

**Não executado** — MCP com `balance: 0`, `weeklyResetAt: Invalid Date`.

| Run | Symbol | TF | SL bug | Status |
|---|---|---|---|---|
| baseline (researcher, com bug) | ETHUSDT | 15m | presente | PF 1.57, 117 trades (já reportado) |
| baseline (researcher, com bug) | BTCUSDT | 15m/1h/4h | presente | negativo (já reportado) |
| **builder-refined (sem bug)** | ETHUSDT | 15m | corrigido | **pendente — créditos=0** |
| **builder-refined (sem bug)** | BTCUSDT | 15m/1h/4h | corrigido | **pendente — créditos=0** |

**Prioridade de quando crédits voltarem:** re-backtest ETHUSDT 15m como controle (confirmar que PF 1.57 não é artefato do SL errado), depois expandir para DOGE/PEPE/SOL/AVAX/XRP em 15m e 4h para testar cross-symbol.

## 5. Results

**N/A — MCP sem créditos neste ciclo.** O Pine foi refinado e validado em higiene, mas sem crédits não há results de backtest para reportar. Números do researcher (ETH 15m PF 1.57, 117 trades, DD 3.6%) são mantenidos como referência, com a ressalva de que usavam a versão com bug de SL (buffer desprezível em ETH ~$2000 → não invalida o resultado positivo, mas deve ser revalidado).

## 6. Robustness Analysis

**Não aplicável** neste ciclo (sem backtest novo). Diagnóstico preliminar baseado no relatório do researcher:

- O bug de SL é marginal em pares de preço médio/baixo (ETH ~$2000, ATR ~$5 → buffer ≈ 0.5cents; BTC ~$20k, ATR ~$60 → buffer ≈ 0.03% do preço). A correção **não deve mudar drasticamente** os resultados positivos do ETH, mas é uma correção de precisão essencial antes de qualquer iteração séria.
- Cross-symbol fraco documentado: BTC negativo em todos os 3 TFs. Isso pode ser um problema de universalidade da hipótese ou um viés de mercado — precisa de mais símbolos para decidir.
- Pattern U de TF (bom em 15m/4h, ruim em 1h) não é explicado pela teoria atual.

## 7. Weaknesses

1. **Créditos MCP esgotados** — bloqueia backtest obrigatório. Sem crédits, não há results para Gertrude avaliar.
2. **SL corrigido mas não re-backtestado** — a confiança no PF 1.57 do ETH depende de um backtest com o bug; a correção deve ser validada antes de qualquer avanço.
3. **Cross-symbol não testado** — apenas ETH e BTC foram testados. Hipótese pode ser ETH/altcoin-specialized ou pode generalizar para outros altcoins.
4. **Pattern U de TF inexplicado** — inconsistência entre 15m/4h (positivo) e 1h (negativo) não tem explicação teórica clara.

## 8. Next Iteration

1. **Imediato:** verificar se weekly grant de 1000 crédits liberou no painel MCP (classe free tier; reset "Invalid Date" sugere problema no clock da conta).
2. **Se crédits disponíveis:** rodar re-backtest ETHUSDT 15m com Pine refinado (controle) + expandir para ≥5 pares (DOGE, PEPE, SOL, AVAX, XRP) em 15m e 4h.
3. **Se crédits indisponíveis por 1-2 semanas:** considerar rodar backtest local via `scripts/run_local_sltp_sweep.py` com disclaimer de commission gap (local usa 0% vs MCP 0.05%).
4. **Critério de melhoria (Gertrude):** ≥5 pares com PF≥1.2 e DD≤30% para promover para incubação. Se BTC continuar negativo com sample robusto → pivot para H2 (Range-Efficiency Collapse) ou aceitar H1 como "ETH/altcoin-specialized".

## 9. Verdict

**ESTACIONAR / Parked** — Pine refinado (SL bug corrigido + higiene aprovada), backtest bloqueado por falta de crédits MCP. Não rejeitado (ETH 15m com PF 1.57 e 117 trades é evidência de edge real); não aprovado (cross-symbol fraco, sem revalidação do SL corrigido). Aguardar crédits para avançar.

**Strike 1 registrado** (1 ciclo sem edge universal em BTC). Se a próxima iteração também falhar em generalização → strike 2 leva a pivot obrigatório.

**Ação requerida (humano):** verificar conta Trader Dev — se o weekly grant de 1000 crédits já liberou, reexecutar o builder cycle com backtest. Se a conta free está vedada permanentemente, considerar upgrade ou rodar sweep local com disclaimer de commission gap.

---

*Risk notice: pesquisa e educação apenas. Backtests não são performance futura. Nenhuma ordem real foi colocada neste ciclo. Incubação requer ≥20 trades / ~3 meses antes de qualquer consideração live. Aprovação humana obrigatória para execução real.*
