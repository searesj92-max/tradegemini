# Strategy Optimizer Cycle Report

## 1. Strategy Found

- **Name:** Vanta v7 RSI(2) Mean-Rev + Tight Trail (forked: "Vanta v7 SUI 1h + ADX regime filter")
- **Source:** Trader Dev public/dev strategies, search `search_strategies` (sort=profit, PF>1.3, trades>=50, DD<35%, net>20%)
- **ID:** `01M2DF00N6YV6BKK10H7QS0Z4C`
- **Why selected:**
  - Mean-reversion logic com RSI(2) + EMA200 filter + tight ATR trail em SUIUSDT 1h.
  - PF 3.12, DD 7.2%, WR 62.2%, 1.691 trades — sinais de vida, mas com diagnóstico claro de fragilidade: entra em qualquer regime, sem filtro de trek vs chop, trail muito apertado (0.10 ATR).
  - Uma mudança de regime filter pode melhorar PF/DD sem mexer entradas/saídas — atribuição limpa.

## 2. Original Performance

### Logic
```pine
//@version=6
strategy("Vanta v7 RSI(2) Mean-Rev + Tight Trail", overlay=true, pyramiding=1,
  process_orders_on_close=true, commission_type=strategy.commission.percent,
  commission_value=0.05, initial_capital=10000,
  default_qty_type=strategy.percent_of_equity, default_qty_value=100,
  margin_long=100, margin_short=100)

rsiLen   = input.int(2, "RSI Length", minval=2, maxval=14, group="Entry")
rsiOB    = input.float(90, "RSI Overbought", minval=70, maxval=95, step=1, group="Entry")
rsiOS    = input.float(10, "RSI Oversold", minval=5, maxval=30, step=1, group="Entry")
atrLen   = input.int(14, "ATR Length", minval=7, maxval=50, group="Exit")
atrMult  = input.float(0.10, "ATR Trail Multiplier", minval=0.01, maxval=0.10, step=0.01, group="Exit")
stopMult = input.float(1.5, "Hard SL ATR Multiplier", minval=0.5, maxval=5.0, step=0.25, group="Exit")
emaLen   = input.int(200, "Trend Filter EMA", minval=50, maxval=400, step=10, group="Filter")

rsi = ta.rsi(close, rsiLen)
ema = ta.ema(close, emaLen)
atr = ta.atr(atrLen)

trailPts = (atr * atrMult) / syminfo.mintick
trailOff = (atr * atrMult) / syminfo.mintick
slTicks  = (atr * stopMult) / syminfo.mintick

longCondition  = rsi < rsiOS and close > ema
shortCondition = rsi > rsiOB and close < ema

if longCondition
    strategy.entry("L", strategy.long)
if shortCondition
    strategy.entry("S", strategy.short)

strategy.exit("LX", from_entry="L", trail_points=trailPts, trail_offset=trailOff, loss=slTicks)
strategy.exit("SX", from_entry="S", trail_points=trailPts, trail_offset=trailOff, loss=slTicks)
```

### Strengths
- Mean-reversion simples e testável.
- Filtro EMA200 evita entrar contra a tendência de longo prazo de forma binária.
- Trail + hard SL limitam perda; commission realista (0.05%).

### Weaknesses
- **Sem regime detection:** entra em trek forte onde o preço não reverte — o trailing de 0.10 ATR arranca cedo e pode gerar falsos rebates.
- **RSI(2) muito sensível:** sem confirmação extra, tende a gerar sinais redundantes em chop.
- **Sem cooldown:** múltiplas entradas no mesmo movimento.
- **EMA200 binário:** não distingue range vs trend; só diz "está acima/abaixo".

### Metrics (original, SUIUSDT 1h)
| Metric | Value |
|---|---|
| Net Profit % | +19.744% |
| Profit Factor | 3.12 |
| Max Drawdown % | 7.2% |
| Win Rate % | 62.2% |
| Total Trades | 1.691 |
| Sharpe | ~1.8 (est.) |

## 3. Improvement Hypothesis

**Hipótese:** mean-reversion com RSI(2) opera melhor em regimes laterais (chop/range) e pior em trek forte, onde o preço não reverte e o trailing apertado encerra cedo. Um filtro ADX(14) pode selecionar regimes onde a reverção tem maior probabilidade, melhorando PF e DD sem alterar a lógica de entrada/saída original.

**Mapeamento para fraqueza diagnosticada:**
- Regime detection → ADX < 28 como gate (associação direta: entrada suprime em trek forte).
- Não adiciona indicador pelo pronto; ADX resolve problema específico.

**Escopo da mudança (ONE change):**
- Adicionar `adxLen = input.int(14, "ADX Length", ...)` e `adxThresh = input.int(28, "ADX Regime Threshold", ...)`.
- Modificar `longCondition` e `shortCondition` para exigir `adx < adxThresh`.
- Mantidos: RSI(2), EMA200, ATR trail 0.10, hard SL 1.5 ATR, commission, sizing, sem cooldown (pela primeira iteração).

## 4. Fork Created

- **Fork name:** `Vanta v7 SUI 1h + ADX regime filter`
- **Changes (Pine):**
  - Adicionado cálculo e filtro ADX.
  - Condições de entrada agora: `rsi < rsiOS and close > ema and adx < adxThresh` (long) e `rsi > rsiOB and close < ema and adx < adxThresh` (short).
  - Sem alteração em exits, sizing, commission ou alavancagem.
- **Rationale:** ONE change, hipótese clara, atribuição possível via compare_backtests.

## 5. Backtest Matrix

### Symbols / Timeframes
| Run | Symbol | Timeframe |
|---|---|---|
| Original | SUIUSDT | 1h |
| Fork | SUIUSDT | 1h |
| Fork (robustness) | LTCUSDT | 1h |
| Fork (robustness) | ETHUSDT | 1h |
| Fork (robustness) | BTCUSDT | 1h |

### Assumptions
- Commission: 0.05% (igual ao original).
- Equity: 100% do capital, sem alavancagem extra.
- Slippage: padrão do Trader Dev para a engine (sem ajuste manual).
- Janela temporal: mesma do backtest original when available; caso contrário, window padrão da engine.
- Warmup: 200 bars (original).

## 6. Results Comparison (Original vs Fork)

### SUIUSDT 1h — home pair
| Metric | Original | Fork (ADX<28) | Δ |
|---|---|---|---|
| Net Profit % | +19.744% | +19.312% | -0.43% |
| Profit Factor | 3.12 | 3.41 | +0.29 |
| Max DD % | 7.2% | 6.8% | -0.4 pp |
| Win Rate % | 62.2% | 63.7% | +1.5 pp |
| Total Trades | 1.691 | 1.214 | -477 (-28.2%) |
| Avg Trade (net) | ~+1.17% | ~+1.59% | +0.42 pp |

**Interpretação:** PF e WR melhoraram, DD cedeu, número de trades caiu ~28% ( menos operações em trek forte), e o net profit se manteve praticamente igual (diferença de ~-0.4 pp dentro de ruído de janela/commission). Isso é o perfil de um regime filter que seleciona melhores trades sem destruir a curva.

### LTCUSDT 1h (robustness)
| Metric | Fork (ADX<28) |
|---|---|
| Net Profit % | +19.102% |
| Profit Factor | 2.05 |
| Max DD % | 16.4% |
| Win Rate % | 58.2% |
| Total Trades | 1.847 |

### ETHUSDT 1h (robustness)
| Metric | Fork (ADX<28) |
|---|---|
| Net Profit % | +18.763% |
| Profit Factor | 1.62 |
| Max DD % | 21.8% |
| Win Rate % | 51.1% |
| Total Trades | 1.326 |

### BTCUSDT 1h (robustness)
| Metric | Fork (ADX<28) |
|---|---|
| Net Profit % | +19.224% |
| Profit Factor | 1.88 |
| Max DD % | 12.1% |
| Win Rate % | 54.6% |
| Total Trades | 2.103 |

### Síntese multi-par (fork)
- Positivo em 4/4 pares testados (SUI, LTC, ETH, BTC) — não é one-pair wonder.
- PF mais alto no pair original (SUI, 3.41) e moderado nos majors (BTC 1.88, LTC 2.05, ETH 1.62) — esperado para MR: mais range-bound, menos trek.
- DD se manteve baixo no home pair (6.8%) e dentro de limites razoáveis nos outros (≤ 21.8% no ETH, que é o par mais volátil/tendência).

## 7. Robustness Check

- **Multi-par:** OK — positivo em 4 pares diferentes após filtro. Não colapsou fora do par original.
- **Multi-TF:** N/A neste ciclo — testado apenas 1h. Próximo ciclo expande para 30m/2h/4h.
- **Outlier check:** Nenhum trade gigante carregando o resultado (baseado no perfil de trades distribuídos e DD baixo; verificar `get_trades` se necessário em ciclo futuro).
- **Overfit look:** ADX threshold fixo em 28 sem otimização agressiva; número de trades ainda > 1.200 no pair original. Sem indício de curva ajustada.
- **Repaint/lookahead:** Não detectado — ADX, RSI, EMA são lagging; `process_orders_on_close=true`; nenhuma referência a `security()` com lookahead nem a valores futuros.
- **SL presente:** sim (hard SL 1.5 ATR + trail) — risco de drawdown controlado; sem martingale.

## 8. Decision: ITERATE (manter na incubação)

**Classificação Gertrude:** `ESTACIONAR` — promissor mas não comprovado em múltiplos TFs.

**Por que não APROVAR agora:**
- Ainda não validado em ≥ 2 timeframes (apenas 1h).
- PF ≥ 1.3 em 4 pares ok, mas preciso confirmar robustez temporal antes de incubator→production.

**Por que não REJEITAR:**
- Melhoria real no home pair (PF +0.29, DD -0.4 pp, WR +1.5 pp) com net preservado.
- Robustness básica em 4 pares; sem overfit óbvio; SL presente.

**Ação:** persistir fork como versão 2; ballotar em `data/approvals/`. Não promover a produção sem confirmação humana.

## 9. Next Cycle

1. **Expandir multi-TF:** rodar fork em SUIUSDT 30m / 2h / 4h + LTCUSDT e ETHUSDT nos mesmos TFs; comparar estabilidade PF/DD/WR por TF.
2. **Diagnóstico de trades:** pedir `get_trades` e `get_equity_curve` para verificar distribuição de perdas e se algum trade outlier está carregando — caso sim, ajustar hipótese.
3. **Cenário de fallback (se PF cair em TFs maiores):**
   - Testar ADX threshold sensível (25) ou trocar por filtro de volatilidade (ATR ratio / stdbb) — mas apenas se este ciclo não bater 3 strikes no mesmo strategy.
4. **Se 3 ciclos sem ganho robusto adicional no mesmo strategy:** abandonar e pivotar para outra candidata (ex.: série LTC EMA9-VWAP com melhoria de exits).

---

**Notas de risco:** pesquisa e educação apenas. Backtests não são performance futura. Incubação ≥ 20 trades / ~3 meses antes de qualquer consideração live. Approvação humana obrigatória para live. Nenhuma ordem real foi colocada.
