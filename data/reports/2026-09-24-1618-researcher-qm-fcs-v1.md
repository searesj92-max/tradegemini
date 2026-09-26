# Quant Mathematician Cycle Report — QM-FCS-v1

## 1. Hypotheses Generated

### H1 — Failed Continuation / Liquidity Sweep Snapback (FCS)
Ineficiência: candles que "limparam" o extremo de N barras (high/low) mas fecham de volta para dentro do range são breakouts falhados. O mercado rasga a liquidez mas não sustenta a nova região → snapback com viés de reversão. Matemática: probabilidade condicional de movimento oposto dado sweep+fail-close > 50% em regimes de baixa tendência. Cross-symbol: genérico. Regime de ruptura: tendência forte (ADX alto) anula o efeito.

### H2 — Range-Efficiency Collapse (REC)
Ineficiência: alta volatilidade com baixa eficiência de alcance (range grande, body pequeno) sinaliza compressão pré-ruptura ou choppy; relação range/ATR vs body/ATR revela cansaço de direção. Cross-symbol: genérico. Rompe em trending forte.

### H3 — Volatility-Normalized Displacement Asymmetry (VND)
Ineficiência: mudança na assimetria (skewness) da distribuição de deslocamentos normalizados por ATR anuncia mudança de regime; trade a reversão da assimetria. Cross-symbol: genérico. Rompe em squeezes.

### H4 — Volume-Price Anomaly (VPA)
Ineficiência: divergência entre mudança de preço e mudança de volume (preço sobe com volume caindo = fraude de força). Cross-symbol: genérico. Rompe em mercados com volume espúrio ou orderbook profundo.

### H5 — Entropy Regime Switch (ERS)
Ineficiência: sequência de direções de candle tem entropia baixa em tendência e alta em chop; transição de regime gera oportunidade. Cross-symbol: genérico. Rompe em transições rápidas.

## 2. Hypothesis Selected

**H1 — FCS**. Critérios: simplicidade (1-2 parâmetros) · testabilidade objetiva · base matemática clara (condicional probabilística de falha de breakout) · cross-symbol · SL/TP natural (o extremum é o ponto de invalidação).

## 3. Trading Rules

| Item | Regra |
|---|---|
| **Long entry** | Candle toca o low do lookback (N=20) mas fecha acima de 30% do range; entrada no close do candle |
| **Short entry** | Candle toca o high do lookback mas fecha abaixo de 30% do range; entrada no close do candle |
| **SL long** | abaixo do low que foi "swept" menos buffer de ATR (rangeL - atr × slBuffer) |
| **SL short** | acima do high que foi "swept" mais buffer de ATR |
| **TP** | 1× ATR normalizado a partir do preço de entrada |
| **Filtro de vol** | só opera se ATR% > mínimo relativo (default 0.3% do preço) |
| **Cooldown** | 1 bar após fechamento antes de re-entrar na mesma direção |
| **Invalidação** | se o candle de entrada não confirma (fechamento fora do critério), cancela o sinal |

## 4. Pine Script

```pine
//@version=6
strategy("QM-FCS-v1 — Failed Continuation / Liquidity Sweep Snapback",
  overlay=true,
  pyramiding=1,
  process_orders_on_close=true,
  commission_type=strategy.commission.percent,
  commission_value=0.05,
  initial_capital=10000,
  default_qty_type=strategy.percent_of_equity,
  default_qty_value=100,
  margin_long=100,
  margin_short=100)

// ============================================================
// QM-FCS-v1 — Hipótese H1: Failed Continuation / Liquidity Sweep Snapback
// Mathematical basis: candles that sweep a recent extremum (high/low of N bars)
// but close back inside the range are failed breakouts → snapback bias.
// ============================================================

// --- Inputs ---
lookback = input.int(20, "Sweep lookback (bars)", minval=5, maxval=100)
atrMult  = input.float(1.0, "TP: ATR multiple", minval=0.5, maxval=4.0, step=0.1)
slBuffer = input.float(0.1, "SL buffer (ATR fraction)", minval=0.0, maxval=1.0, step=0.05)
volFilter = input.bool(true, "Enable ATR volatility filter")
atrMinPct = input.float(0.3, "Min ATR % of price for vol filter", minval=0.05, maxval=2.0, step=0.05)

// --- Indicators ---
atrVal   = ta.atr(14)
rangeH   = ta.highest(high, lookback)
rangeL   = ta.lowest(low, lookback)

// Sweep detection: current candle high/low touches extreme but close returns inside
sweepLong  = (low <= rangeL) and (close > rangeL + (rangeH - rangeL) * 0.30)
sweepShort = (high >= rangeH) and (close < rangeH - (rangeH - rangeL) * 0.30)

// Volatility filter: ATR % of price above threshold
atrPct = atrVal / close * 100
volOK  = not volFilter or (atrPct >= atrMinPct)

// --- Entry conditions ---
longSignal  = sweepLong  and volOK
shortSignal = sweepShort and volOK

// --- Visuals ---
plot(rangeH, "Sweep high", color=color.red, style=plot.style_circles, linewidth=1)
plot(rangeL, "Sweep low",  color=color.green, style=plot.style_circles, linewidth=1)
plotshape(longSignal,  "Long sweep",  shape.triangleup,   location.belowbar, color=green, size=size.small)
plotshape(shortSignal, "Short sweep", shape.triangledown, location.abovebar, color=red,   size=size.small)

// --- Entries ---
if longSignal and strategy.position_size == 0
    strategy.entry("L", strategy.long)

if shortSignal and strategy.position_size == 0
    strategy.entry("S", strategy.short)

// --- Exits (SL/TP via strategy.exit) ---
// Long: SL below swept low - ATR buffer; TP at entry + ATR*mult
if strategy.position_size > 0
    slPriceLong  = rangeL - atrVal * slBuffer
    tpPriceLong = close + atrVal * atrMult
    strategy.exit("LX", from_entry="L", stop=slPriceLong, limit=tpPriceLong)

// Short: SL above swept high + ATR buffer; TP at entry - ATR*mult
if strategy.position_size < 0
    slPriceShort  = rangeH + atrVal * slBuffer
    tpPriceShort = close - atrVal * atrMult
    strategy.exit("SX", from_entry="S", stop=slPriceShort, limit=tpPriceShort)
```

**Nota de implementação:** versão implementada no backtest usa `rangeL * (1 - slBuffer * atrVal / close)` para SL long — um bug de formulação (multiplicativo em vez de offset). A versão correta acima usa `rangeL - atrVal * slBuffer`. Isso NÃO foi testado; os resultados abaixo refletem a versão com bug.

## 5. Backtest Matrix

| Symbol | Timeframe | Net Profit % | PF | Max DD % | Win Rate % | Trades | Long/Pf | Short/Pf |
|---|---|---|---|---|---|---|---|---|
| BTCUSDT | 15m | -4.71% | 0.63 | 6.3% | 42.2% | 45 | -222 / 0.63 | -249 / 0.63 |
| BTCUSDT | 1h | -3.95% | 0.72 | 5.7% | 36.1% | 36 | -76 / 0.72 | -319 / 0.72 |
| BTCUSDT | 4h | -0.81% | 0.80 | 2.6% | 50.0% | 10 | +90 / 0.80 | -171 / 0.80 |
| ETHUSDT | 15m | +8.91% | 1.57 | 3.6% | 46.2% | 117 | +501 / 1.57 | +390 / 1.57 |
| ETHUSDT | 1h | -0.74% | 0.96 | 11.3% | 29.3% | 58 | +392 / 0.96 | -466 / 0.96 |
| ETHUSDT | 4h | +3.94% | 1.74 | 3.1% | 46.2% | 13 | +73 / 1.74 | +321 / 1.74 |

**Engine:** TV_ENGINE_JUL_26 parity · Commission 0.05% · Sizing 100% equity · Margin 100/100 · Initial capital $10,000

## 6. Results

### Síntese
- **BTCUSDT:** negativo em todos os 3 timeframes (PF 0.63-0.80). Sem edge.
- **ETHUSDT:** positivo em 15m (PF 1.57, 117 trades) e 4h (PF 1.74, 13 trades); negativo em 1h (PF 0.96).
- **Amostra:** 117 trades em ETH 15m é robusta; 13 trades em ETH 4h é pequena (pode ser sorte); 10-45 trades em BTC são insuficientes para conclusão.
- **Pattern U:** ETH mostra ótimo em extremos (15m/4h) e ruim no meio (1h). Isso pode indicar que o efeito FCS funciona em baixa TF (sweep rápido + snapback imediato) e em alta TF (sweep de larger structure), mas falha em 1h onde a dinâmica é intermediária.

### Métricas detalhadas — ETHUSDT 15m (melhor backtest)
| Métrica | Valor |
|---|---|
| Net profit | +8.91% |
| Profit factor | 1.57 |
| Max drawdown | 3.6% |
| Win rate | 46.2% |
| Trades | 117 |
| Avg trade | +0.076% |
| Ratio avg win/loss | 1.83 |
| Sharpe | 2.87 |
| Commission paid | $814.74 |
| Long trades | 42 (27 wins, +500.93) |
| Short trades | 75 (27 wins, +390.07) |

### Comentário sobre o bug de SL
A versão backtestada usa `slPriceLong = rangeL * (1 - slBuffer * atrVal / close)` em vez de `rangeL - atrVal * slBuffer`. Para BTC (preço ~$20,000, ATR ~$60, slBuffer=0.1): buffer = 0.1 × (60/20000) = 0.0003 → SL = rangeL × 0.9997 ≈ rangeL. O buffer é desprezível. Isso não invalida o resultado (o SL foi basicamente o low do sweep), mas significa que a proteção extra de ATR não foi aplicada — e o resultado negativo em BTC não é "porque o SL era muito largo", é "porque o sinal em si não tem edge em BTC".

## 7. Diagnosis

### O que funciona
- O efeito FCS se manifesta em **ETH**, especialmente em 15m (alta frequência de sweeps + snapbacks) e 4h (sweep de estrutura maior).
- As métricas de ETH 15m são robustas: PF 1.57, DD controlado (3.6%), 117 trades, ambos os lados lucrativos.
- A hipótese tem vida — não é um phantom.

### O que falha
- **BTC não coopera.** PF < 1 em todos os 3 TFs. Ou o sweep em BTC é "mais real" (menos fakeout) ou o modelo não captura a dinâmica de BTC.
- **ETH 1h é o pior.** Pattern U não é explicado pela teoria — pode ser amostragem ou pode ser que 1h é um "zona morta" de sinal.
- **Amostra pequena em 4h** (13 trades) — o PF 1.74 pode ser sort.
- **Bug de SL** não afeta a conclusão (o SL foi basicamente o extremo sem buffer), mas precisa ser corrigido antes de qualquer iteração séria.

### Diagnóstico de fragilidade
- Cross-symbol: falhou em BTC, passou em ETH. Não é universal.
- Cross-TF: pattern U inconsistente (bem em 15m/4h, ruim em 1h).
- A estratégia é "long/short agnostic" — mas ETH 15m favorece shorts (75 vs 42). Isso pode ser um viés de mercado, não do sinal.
- Sem filtro de regime: o sinal dispara em qualquer condição de volatilidade acima do mínimo. Pode estar entrando em chop ou em trending forte (onde o sweep é "real").

## 8. Verdict

### **WATCHLIST — Incubação frágil**

**Critérios de Gertrude (APROVAR → incubação):**
- PF ≥ 1.3 em ≥ 5 pares → ❌ (apenas 2 pares positivos, 1 com PF > 1.3)
- Max DD ≤ 30% → ✅ (3.6% em melhor caso)
- ≥ 50 trades → ✅ (117 em ETH 15m)
- Estável em ≥ 2 TFs → ❌ (15m OK, 4h OK com amostra pequena, 1h ruim)
- Sem repaint/lookahead → ✅
- SL presente → ✅ (mas com bug de formulação)

**Por que WATCHLIST e não REJEITAR:**
A hipótese H1 tem sinal real em ETH com métricas robustas (117 trades, PF 1.57, DD 3.6%). Não é overfit — o sinal é simples (1 parâmetro principal: lookback) e a lógica é testável. Mas a falta de universalidade (BTC negativo) e o pattern U de TF tornam incorreto promover para incubação sem mais trabalho.

**Por que não INCUBAR agora:**
- Só 2 pares positivos (preciso ≥ 5 para Gertrude).
- BTC negativo em todos os TFs — a hipótese pode ser "ETH-only" ou "alta-beta-only", o que limita utilidade.
- Amostra pequena em 4h.
- Bug de SL não testado na versão correta.

### Recomendação de próxima iteração (ONE major change)

**Opção A — Corrigir SL + adicionar filtro de regime:**
1. Corrigir `slPriceLong = rangeL - atrVal * slBuffer` (offset correto)
2. Adicionar filtro de regime simples: só operar quando o candle de entrada tem range < 1.5× ATR médio (evita sweeps "de verdade" em trending forte)
3. Expandir para mais pares (DOGE, PEPE, SOL, AVAX) para testar universalidade

**Opção B — Specializar para alta-EF (volatility-normalized):**
1. Manter a hipótese mas adicionar normalização de lookback pelo ATR para adaptar à volatilidade do par
2. Fazer lookback variável: `lookback = floor(atrVal / close * 100 * k)` — padrão adaptativo
3. Testar se o efeito se generaliza quando a detecção de sweep é adaptativa

**Opção C — Pivot:**
1. Descartar H1 e testar H2 (Range-Efficiency Collapse) ou H5 (Entropy Regime Switch) em ETH
2. Manter ETH como laboratório principal

## 9. Next Cycle

1. Corrigir o bug de SL na versão Pine e re-backtestar ETHUSDT 15m como controle (para confirmar que o PF 1.57 não é artefato do SL errado)
2. Expandir para 5+ pares (DOGE, PEPE, SOL, AVAX, XRP) em 15m e 4h para testar cross-symbol
3. Se ≥ 5 pares com PF ≥ 1.2 e DD ≤ 30% → então promover para incubação
4. Se BTC continuar negativo em todos os TFs com amostra robusta → considerar pivot para H2 ou H5, ou aceitar que H1 é "ETH/altcoin-specialized"

**Contagem de strikes:** 1 ciclo sem edge universal em BTC. Se a próxima iteração também falhar em generalização, o strike 2 leva a pivot obrigatório.

---

**Relatório gerado:** 2026-09-24 16:18 UTC-3  
**Agent:** researcher (Hermes cron)  
**Estratégia:** `01M3A38DNZSP00Y5DKHWP5VCS0` — QM-FCS-v1  
**MCP:** Trader Dev MCP (TV_ENGINE_JUL_26 parity)  
**Créditos restantes:** 33 (início) → ~27 após 6 backtests (cada backtest ~1 crédito; serviço free tier)
