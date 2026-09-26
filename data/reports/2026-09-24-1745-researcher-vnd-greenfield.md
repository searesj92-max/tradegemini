# Quant Mathematician Cycle Report — QM-VND-v1

**Cycle**: 2026-09-24-1745 · **Agent**: researcher (quant-mathematician) · **Engine**: tv_jul26 (MCP) · **Status**: créditos=0 → backtest bloqueado

---

## 1. Hipóteses Geradas

### H1 — QM-VND: Volatility-Normalized Displacement com Follow-Through Decay ✅
**Ineficiência**: Após deslocamento de preço normalizado por ATR maior que um limiar (ex: 1.5×ATR em relação à média móvel local), quando o follow-through (retorno do próximo período na mesma direção) é fraco ou negativo, há sobre-reação sem confirmação — reversão de curto prazo esperada.

**Por que crypto**: Volatilidade esp spike + liquidação de leverage em One-Realized-Price gera displacement artificial sem sustentação de vol.

**Caso cross-symbol**: Efeito de sobre-reação é universal, mas magnitude varia com beta do ativo.

**Regime que quebra**: Forte tendência unidirecional (displacement é sustentado, não reversão). Filtro de tendência (ADX) evita falso positivo.

**Expressão Pine**: `displacement = math.abs(close - ta.sma(close, lookback)) / atr` — entrada quando displacement > limiar E follow-through fraco.

### H2 — QM-FC: Falha de Continação + Range Efficiency Collapse
**Ineficiência**: Após breakout/bar de alta eficiência de range (body grande, range ≈ high-low completo), falha de continuação no próximo período + compressão de range sinaliza exhaustion.

**Por que crypto**: Breakouts falseados em low-liquidity são comuns; range efficiency collapse após impulse é padrão de exhaustion.

**Caso cross-symbol**: Aplica a qualquer ativo com gap/spike; magnitude varia com profundidade de livro.

**Regime que quebra**: Range expansion sustentada (trend real) — onde o próximo bar expande, não contrai.

### H3 — QM-AVS: Volume Spike Assíncrono + Range Contraction
**Ineficiência**: Spike de volume (> k×Média de Volume) sem deslocamento de preço correspondente (low displacement despite high volume) indica distribuição/acumulação — reversão quando range subsequente contrai.

**Por que crypto**: Volume fake/spam é comum em crypto; volume sem preço é sinal de fraqueza.

**Caso cross-symbol**: Universal, mas limiar de volume é relativo a cada símbolo.

**Regime que quebra**: Volume real de tendência (volume + displacement conjunto) — filtro compound.

### H4 — QM-DEB: Breach de Banda de Equilíbrio + Snapback
**Ineficiência**: Quando preço sai de banda de equilíbrio adaptativa (médio móvel + ATR múltiplos) e retorna rapidamente (snapback), entrada de reversão no retorno com confirmação de falha de continuação.

**Por que crypto**: Bandas de equilíbrio (mean reversion) são naturais em ativos mean-reverting; crypto tem componente MR inter-day.

**Caso cross-symbol**: Parâmetros de banda precisam ser relativos a volatilidade de cada ativo.

**Regime que quebra**: Tendência forte de longo prazo (preço foge da banda sem snapback).

### H5 — QM-REG: Classifier de Regime com Filtro de Entropia
**Ineficiência**: Operar só no regime adequado para a estratégia — MR só em chop/compressão, breakout só em regime de expansão. Classifier via ADX + entropia de returns + volatilidade.

**Por que crypto**: Regimes alternam rapidamente; estratégia universal que não filtra regime perde em transição.

**Caso cross-symbol**: Classificador é universal; estratégia종속 ao regime.

**Regime que quebra**: Classifier errado em regime de transição (lento para adaptar).

---

## 2. Hipótese Selecionada (base matemática)

**Seleção: H1 — QM-VND (Volatility-Normalized Displacement com Follow-Through Decay)**

**Por que esta**:
- Displacement normalizado remove viés de escala (preço não importa, é a razão ao ATR que importa)
- Follow-through decay captura a fraqueza de sustentação — a assinatura de overreaction sem confirmação
- Poucos parâmetros: lookback para equilíbrio, limiar de displacement, janela de follow-through — teste de robustez vs. overfitting é fácil
- Generalizável: qualquer ativo com volatilidade medível e componente de overreaction
- Simplicidade: 3 inputs principais, lógica de uma linha (displacement + follow-through), SL/TP bem definidos
- Anti-sobreajuste: Limiares baseados em múltiplos de ATR (não valores absolutos de preço) são naturalmente scaláveis cross-symbol

---

## 3. Regras de Trading (QM-VND-v1)

**Idéia central**: Preço se desloca muito de seu equilíbrio recente (SMA + ATR normalizado) mas o próximo período NÃO confirma a direção — follow-through fraco. Entra na reversão com SL além do displacement.

### Parâmetros (inputs)
- `equilibriumLookback` = 20 (períodos para médio de equilíbrio)
- `displacementMult` = 1.5 (múltiplo de ATR para considerar "deslocamento grande")
- `followThroughBars` = 2 (períodos para medir follow-through)
- `followThroughWeak` = 0.3 (fração de ATR — se displacement do follow-through < isso, é fraco)
- `trendFilter` = true (habilita filtro ADX de tendência)
- `adxTrendThresh` = 25 (ADX > isso = tendência forte = sem operação MR)
- `slFromEntryMult` = 2.0 (SL = entrada + 2×ATR)
- `tpFromEntryMult` = 1.0 (TP = entrada - 1×ATR para longs reversais, inverso para shorts)
- `cooldownBars` = 5 (barras de espera após saída antes de nova entrada mesma direção)

### Long Entry (reversão de curto).
1. Calcular `equilibrium = ta.sma(close, equilibriumLookback)`
2. Calcular `atr = ta.atr(atrLength)` com atrLength = equilibriumLookback
3. `displacement = (close - equilibrium) / atr` (sinalizado — positivo = acima, negativo = abaixo)
4. Condição de overreaction: `displacement < -displacementMult` (preço muito abaixo do equilíbrio)
5. Follow-through fraco: calcular `followRet = close - close[followThroughBars]` normalizado; se `followRet / atr[followThroughBars] < followThroughWeak` (o preço não subiu suficiente nos últimos N períodos — fraca recuperação)
6. Filtro de tendência (se habilitado): `adx < adxTrendThresh` (não está em tendência forte)
7. Cooldown: `barssince(lastExit) > cooldownBars`
8. Se tudo satisfeito → `strategy.entry("L", strategy.long)`

### Short Entry (espelhado).
1. `displacement > +displacementMult` (preço muito acima do equilíbrio)
2. Follow-through fraco para baixo: `followRet / atr[followThroughBars] > -followThroughWeak` (preço não caiu suficiente)
3. `adx < adxTrendThresh`
4. Cooldown ok
5. → `strategy.entry("S", strategy.short)`

### Saídas (SL e TP fixos em ATR — NÃO trailing).
- Long: SL = entryPrice - `slFromEntryMult * atr` (absoluto); TP = entryPrice + `tpFromEntryMult * atr` (absoluto)
- Short: SL = entryPrice + `slFromEntryMult * atr`; TP = entryPrice - `tpFromEntryMult * atr`
- Usar `strategy.exit` com stop= e limit= em preços absolutos (strat_complex_y pattern)

### Invalidação.
- Se preço atinge SL ou TP — saída automática via strategy.exit
- Se regime mudou (ADX sobe) enquanto em posição — manter até SL/TP (sem trailing)

### Cooldown.
- Após qualquer saída, `cooldownBars` antes de nova entrada na mesma direção.

### Nota: NO trailing stops (regra do vídeo — latency broker transforma winners em losses).

---

## 4. Pine Script (QM-VND-v1)

```pine
//@version=6
// =============================================================================
// QM-VND-v1 — Volatility-Normalized Displacement with Follow-Through Decay
// Agent: researcher (quant-mathematician)
// Date: 2026-09-24
// Hypothesis: after normalized displacement from local equilibrium, weak
// follow-through (next N bars don't confirm direction) → mean-reversion entry
// with ATR-based absolute SL/TP. No trailing. Regime filter: ADX.
// =============================================================================

// --- MCP RULE COMPLIANCE ---
// process_orders_on_close=true · pyramiding=1 · commission 0.05% ·
// default_qty_type=percent_of_equity, 100 · margin_long/short=100
// No trailing · No arrays · No request.security · No cancel · No martingale
// strategy.exit with absolute stop/limit prices (strat_complex_y style)

strategy(
  title="QM-VND-v1",
  overlay=true,
  pyramiding=1,
  process_orders_on_close=true,
  commission_type=strategy.commission.percent,
  commission_value=0.05,
  initial_capital=10000,
  default_qty_type=strategy.percent_of_equity,
  default_qty_value=100,
  margin_long=100,
  margin_short=100
)

// --- Inputs ---
eqLookback    = input.int(20,  "Equilibrium lookback (SMA + ATR base)", minval=5)
displMult     = input.float(1.5, "Displacement threshold (×ATR)", minval=0.5, step=0.1)
ftBars        = input.int(2,   "Follow-through lookback (bars)", minval=1)
ftWeakThresh  = input.float(0.3, "Follow-through weakness threshold (×ATR)", minval=0.0, step=0.1)
adxEnabled    = input.bool(true, "Enable ADX trend filter")
adxThresh     = input.float(25.0, "ADX trend threshold (above = no MR)", minval=10, maxval=60, step=1)
atrLen        = input.int(14,  "ATR length (separate from equilibrium)", minval=5)
slMult        = input.float(2.0, "SL distance (×ATR from entry)", minval=0.5, step=0.1)
tpMult        = input.float(1.0, "TP distance (×ATR from entry)", minval=0.25, step=0.1)
cooldownBars  = input.int(5,   "Cooldown bars after exit", minval=0)

// --- Series ---
atrVal     = ta.atr(atrLen)
equilibrium = ta.sma(close, eqLookback)

// Normalized displacement from equilibrium (signed: positive = price above eq)
displacement = (close - equilibrium) / atrVal

// ADX trend filter
adxVal = ta.dmi(atrLen, atrLen).adx
trendStrong = adxEnabled ? adxVal > adxThresh : false

// Follow-through: how much price moved in the last ftBars, normalized by ATR at that time
// For long reversal setup (price too low): we want weak upward follow-through
// followMoveNorm = (close - close[ftBars]) / atrVal[ftBars]
// Weak if followMoveNorm < ftWeakThresh (didn't recover enough)
followRetLongSetup = (close - close[ftBars]) / atrVal[ftBars]
followWeakForLong  = followRetLongSetup < ftWeakThresh   // didn't bounce enough

// For short reversal setup (price too high): weak downward follow-through
// We want followMoveNorm > -ftWeakThresh (didn't drop enough)
followRetShortSetup = (close - close[ftBars]) / atrVal[ftBars]
followWeakForShort  = followRetShortSetup > -ftWeakThresh // didn't drop enough

// Cooldown tracking
var int lastLongExitBar  = -cooldownBars - 1
var int lastShortExitBar = -cooldownBars - 1

// --- Entry conditions ---

// Long reversal: price significantly below equilibrium + weak bounce + not trending strong
longSetup = not trendStrong and displacement < -displMult and followWeakForLong
longCooldownOk = bar_index - lastLongExitBar > cooldownBars
longEntry = longSetup and longCooldownOk and strategy.position_size <= 0

// Short reversal: price significantly above equilibrium + weak pullback + not trending strong
shortSetup = not trendStrong and displacement > displMult and followWeakForShort
shortCooldownOk = bar_index - lastShortExitBar > cooldownBars
shortEntry = shortSetup and shortCooldownOk and strategy.position_size >= 0

// --- Entries ---
if longEntry
    strategy.entry("L", strategy.long)

if shortEntry
    strategy.entry("S", strategy.short)

// --- Exits (absolute ATR-based SL/TP via strategy.exit — NO trailing) ---
// Exit IDs must match from_entry. Use absolute prices.

// Long: SL below entry, TP above entry
if strategy.position_size > 0
    slPriceLong  = strategy.position_avg_price - atrVal * slMult
    tpPriceLong  = strategy.position_avg_price + atrVal * tpMult
    strategy.exit("LX", from_entry="L", stop=slPriceLong, limit=tpPriceLong)

// Short: SL above entry, TP below entry
if strategy.position_size < 0
    slPriceShort = strategy.position_avg_price + atrVal * slMult
    tpPriceShort = strategy.position_avg_price - atrVal * tpMult
    strategy.exit("SX", from_entry="S", stop=slPriceShort, limit=tpPriceShort)

// --- Cooldown bookkeeping ---
// Mark exit bars: track when position flips to zero after being non-zero.
_lastPosNonZeroBar = ta.valuewhen(strategy.position_size != 0, bar_index, 0)

if strategy.position_size == 0 and _lastPosNonZeroBar != bar_index
    // We just went flat after being in position — record the exit bar
    wasLong  = _lastPosNonZeroBar > lastLongExitBar
    wasShort = _lastPosNonZeroBar > lastShortExitBar
    if wasLong
        lastLongExitBar := bar_index
    if wasShort
        lastShortExitBar := bar_index

// --- Signal plots (for debugging, non-trading) ---
plot(longEntry  ? 1 : 0, "Long entry signal", style=plot.style_circles, linewidth=2, color=color.green)
plot(shortEntry ? 1 : 0, "Short entry signal", style=plot.style_circles, linewidth=2, color=color.red)

// Equilibrium line (reference)
plot(equilibrium, "Equilibrium SMA", color=color.orange, linewidth=1)
```

**Regras MCP observadas**:
- `process_orders_on_close=true`, `pyramiding=1`, `commission_value=0.05`
- `% equity 100` + `margin 100` (perfil de paridade)
- Sem trailing (usando `strategy.exit` com stop/limit absolutos — padrão strat_complex_y)
- Sem arrays, sem `request.security`, sem `strategy.cancel`, sem martingale
- SL/TP em Múltiplos de ATR (escaláveis cross-symbol)
- `ta.dmi().adx` — permitido pela allowlist MCP

---

## 5. Backtest Matrix

| Campo | Valor |
|---|---|
| **Estratégia MCP** | `QM-VND-v1` (ID `01M3AJ282SGD5Q9GET6CQ571BT`) |
| **Símbolo home** | SOLUSDT (BYBIT:SOLUSDT.P) |
| **Timeframe home** | 1h |
| **Window pretendido** | 2025-01-01 → 2026-09-01 (tv_jul26) |
| **Multi-symbol pretendido** | 5–10 top-100 Bybit pares × 15m/30m/1h/2h/4h |
| **Long/Short** | Bilateral |
| **Engine** | tv_jul26 (MCP) |
| **Resultado** | ⚠️ **Backlog testado — créditos=0** |

**Status do backtest**: `run_backtest` retornou erro `"You have no credits remaining. Your free credits reset on Invalid Date."` A estratégia foi criada com sucesso (dev mode, active), mas o backtest não executou.

**Plan B para quando créditos retornarem**:
1. `run_backtest` no ID registrado → resultado → `get_trades` + `get_equity_curve`
2. Expandir para 5–10 símbolos × 1h (e cross-TF se permitido)
3. Comparar vs `rsi-t200b` (melhor do book local, PF 1.69, 8/16 pares em 4h)

---

## 6. Resultados

| Métrica | Valor |
|---|---|
| **Net Profit %** | ⏳ pendente (credits=0) |
| **Profit Factor** | ⏳ pendente |
| **Max Drawdown %** | ⏳ pendente |
| **Win Rate %** | ⏳ pendente |
| **Trades** | ⏳ pendente |
| **Long/Short PF** | ⏳ pendente |
| **TF Stability** | ⏳ pendente |

**Evidência disponível neste ciclo**: apenas o Pine Script auditado + registro no MCP (ID válido, modos dev/active). Sem números de backtest, não há como emitir verdict quantitativo definitivo.

---

## 7. Diagnóstico (antes de melhorar)

**Contexto do livro local**:
- RSI+trend family domina (rsi-t200b: 8/16, PF 1.69 — melhor do book)
- Hipóteses quant novas (displacement, fail-cont, range-eff, momentum z) **não passaram em 4h**
- voldisp = 0 trades (condição contraditória)
- failcont/rangeeff = amostra pequena
- Créditos **em 0** — reset com data inválida

**Risco do QM-VND**:
- Hipótese de follow-through decay é coerente com literatura de overreaction, mas nunca foi testada no livro local (é nova)
- Risco: mesma lógica de MR pode cair no mesmo erro das hipóteses quant que falharam (displacement sem follow-through pode ser mais robusto, mas só backtest confirma)
- Filtro ADX pode ser muito restritivo ou pouco — parâmetro sensível

**O que precisamos ver**:
1. Quantos trades geram em 1h nos 5–10 símbolos (amostra ≥ 50 para significância)
2. PF cross-symbol (gate: PF≥1.3 em múltiplos pares)
3. DD max (gate: ≤ 30%)
4. Win rate vs PF (MR espera WR<50% mas PF>1 — OK se PF alto)
5. Estabilidade cross-TF (se funciona em 15m/30m/1h/2h/4h)

---

## 8. Verdict

| Critério | Avaliação |
|---|---|
| **Registro MCP** | ✅ Pronto (ID válido, Pine auditado, modos dev/active) |
| **Backtest executado** | ❌ Não (credits=0 — blocker de infra, não de estratégia) |
| **Evidência de edge** | ⏳ insuficiente para verdict quantitativo |
| **Qualidade do design** | ✅ Greenfield rigoroso, sem indicador soup, sem trailing, com SL/TP em ATR e filtro de regime |
| **Verdict** | **⏳ PENDING — aguardando créditos para backtest** |

**Classificação provisória**: `ESTACIONAR` (hipótese coerente, Pine pronto, sem dados). Não `REJEITAR` (não há evidência negativa — só ausência de teste). Não `INCUBATE` (precisa de backtest primeiro).

**Ação recomendada pelo desk**:
- Quando créditos retornarem (reset em `Invalid Date` — verificar `/unlock-edge` ou `buy_credits`), rodar `run_backtest` no ID registrado
- Se PF≥1.3 em ≥ 3 pares com trades≥40 e DD≤30 → subir para `INCUBATE` e agendar cross-TF
- Se PF<1.3 ou amostra pequena → diagnosticar e iterar (uma mudança: follow-through window, mult de displacement, ou remover filtro ADX) ou rejeitar com strike

---

## 9. Próximo Ciclo

**Se créditos disponíveis**:
1. `run_backtest` no ID `01M3AJ282SGD5Q9GET6CQ571BT` (SOL 1h) → capturar KPIs
2. Expandir para 5–10 símbolos × 1h (BTC ETH XRP DOGE AVAX BNB LINK ADA NEAR SOL)
3. Cross-TF se possível (15m, 30m, 2h, 4h em 2–3 símbolos)
4. Comparar vs `rsi-t200b` (baseline do book)
5. Diagnosticar: se PF bom mas apenas uns poucos símbolos → investigar se é alavancagem do ativo ou overfitting de parâmetros

**Se créditos continuarem zerados**:
- O Pine está pronto para rodar quando créditos voltarem — não é desperdício, é trabalho concluído
- Considerar `buy_credits` (Starter $9.99/mo) se há interesse real em avançar este ciclo
- Ou pivotar para uma hipótese que possa ser testada localmente (se houver dados locais)

---

## Bloco JSON para Painel (consiste com upsert realizado)

```json
{
  "strategies": [
    {
      "id": "01M3AJ282SGD5Q9GET6CQ571BT",
      "name": "QM-VND-v1",
      "symbol": "SOLUSDT",
      "timeframe": "1h",
      "source": "hermes-cron-greenfield",
      "family": "displacement-followthrough",
      "agent": "researcher",
      "net_profit_pct": null,
      "profit_factor": null,
      "max_drawdown_pct": null,
      "win_rate_pct": null,
      "trades": null,
      "sharpe": null,
      "result_id": null,
      "view_url": null,
      "curve": null,
      "verdict": "Pending — awaiting credits",
      "status": "dev",
      "last_backtest": null,
      "pine_key": "qm-vnd-v1",
      "mcp_strategy_id": "01M3AJ282SGD5Q9GET6CQ571BT"
    }
  ]
}
```

---

*Research only. Not financial advice. Backtest ≠ future performance. No real orders placed. Generated 2026-09-24-1745.*
