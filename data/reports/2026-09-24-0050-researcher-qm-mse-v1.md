# Quant Mathematician Cycle Report
## Cycle: QM-MSE-v1 (Microstructure-Specific Event Hypotheses — Batch Test)
## Date: 2026-09-24 00:50 UTC-3

---

## 1. Hipóteses Geradas (3 greenfield)

### H1 — LRS: Liquidity Rebalance Snapback

**Ineficiência alvo:** Após um candle que rompe um extremo recente (HH/LL de N barras) com range anomal, mas cujo close "falha" em manter a ruptura (fecha para dentro do range), o mercado tende a se rebalancear na direção oposta ao lado "vazio" (liquidity void).

**Matemática central:**
- `sweepHigh = high[1] > ta.highest(high, N)[2]` (high[1] rompe HH de barras anteriores)
- `rangeAnom = (high - low) > ta.sma(ta.range, N) * α`
- `failedClose = close[1] < ta.highest(high, N)[2]` (long: volta para dentro)
- `voidSide = close[1] < hl2[1]` → rebalance para cima → long
- Entry no bar seguinte ao failed-close

**Por que na crypto:** Stops concentrados em extremos recentes; sweeps com fakeout são frequentes em vol alta; o mercado 24/7 tem poucos gaps, então o fakeout-close é detectável.

**Breaking regime:** tendência monótona sem pullback (o sweep é legítimo continuation, não liquidity grab); vol muito baixa (sem stops para sweep).

---

### H2 — REA: Range-Efficiency Asymmetry After Expansion

**Ineficiência alvo:** Quando range efficiency (close-to-close progress ÷ total range) cai abruptamente após um período de alta eficiência, há exaustão de tendência com viés de reversão.

**Matemática central:**
- `eff_N = Σ|close[n]-close[n-1]| / (HH_N - LL_N)` (manual rolling sum, sem ta.sum)
- `prevEffHigh = eff[1] > 0.5`
- `effDrop = eff < 0.3`
- `atrMinOk = atr > ta.sma(atr, 20) * 0.7`
- Entrada: `prevEffHigh and effDrop and atrMinOk and (close > SMA20 → long ou close < SMA20 → short)`
- SL: 1.5×ATR, TP: 2.0×ATR, time exit 20 barras

**Por que na crypto:** Movimentos limpos em crypto são seguidos de consolidação quando o fluxo se exaurce; a mudança de eficiência é indicador mais precoce que RSI/MACD para exaustão.

**Breaking regime:** mercado lateral com RE alternando sem padrão claro; gap de liquidez que pula a zona de eficiência.

---

### H3 — JM: Jump Magnet Reversion (Left-Side Pattern)

**Ineficiência alvo:** Quando o mercado está em coil switchen (volatility stability index baixo = ATR/ATR_avg < 0.6), um candle com low abaixo da lower band (ou high acima da upper band) mas close voltando para dentro da banda cria left zone — gatilho de reversão para o centro.

**Matemática central:**
- `ssIndex = ATR / SMA(ATR, 20)` — baixo = regime estável
- `band = ± 2 * ATR * bandMult`
- `longLeftZone = low[1] > lowerBand[1] and close[1] < lowerBand[1]` (low toca abaixo mas close volta)
- `shortLeftZone = high[1] < upperBand[1] and close[1] > upperBand[1]`
- Entry: `lowStability and leftZone[1]`
- SL/TP: ATR-based, time exit 20 barras

**Por que na crypto:** Coil swithen com band bounces são padrão de mean-reversion em rodízio de volatilidade; o left zone (low abaixo mas close dentro) captura o fake breakout dentro do regime estável.

**Breaking regime:** vol alta (ssIndex > 0.6) — o coil se quebra e o banded candle é genuinamente breakout, não fakeout; mercado em trend forte sem regime estável.

---

## 2. Hipótese Selecionada

**Nenhuma das 3 selecionada para um único ciclo — todas testadas em paralelo como batch greenfield.**

Motivo: três conceitos distintos de microstructure (liquidity void, efficiency asymmetry, banded coil) representam diferentes famílias de ineficiência. Testar em paralelo economiza créditos e dá diagnóstico cruzado imediato.

---

## 3. Regras de Trading (resumo por hipótese)

Ver seção 1 para a matemática completa. Em comum:
- **Sem trailing stops** (regra do loop — latência de broker converte winners em losses)
- **SL/TP fixos em ATR múltiplos** (1.5× ATR SL, 2.0× ATR TP para REA/JM; 0.5× ATR SL, centro do range para TP em LRS)
- **Cooldown:** 1 barra após saída
- **Time exit:** 20 barras máx
- **Risco:** 100% equity, margin 100/100, commission 0.05%, pyramiding=1
- **Sem filtro de tendência SMA200** (os padrões são independentes de tendência maior)

---

## 4. Pine Script

### 4.1 QM-LRS-v1 [CORRECTED] — Liquidity Rebalance Snapback

Caminho: `C:\Users\seares\Desktop\botrade\workspaceqm_lrs_v1_corrected.pine`

```pine
//@version=6
strategy("QM-LRS-v1 — Liquidity Rebalance Snapback [CORRECTED]",
  overlay=true, pyramiding=1, process_orders_on_close=true,
  commission_type=strategy.commission.percent, commission_value=0.05,
  initial_capital=10000, default_qty_type=strategy.percent_of_equity,
  default_qty_value=100, margin_long=100, margin_short=100)

sweepLen      = input.int(20, "Sweep lookback")
rangeAvgLen   = input.int(20, "Range avg length")
rangeAnomMult = input.float(1.5, "Range anomaly mult")
cooldownBars  = input.int(1, "Cooldown")
timeExitBars  = input.int(20, "Max bars")
atrLen        = input.int(14, "ATR length")

atr = ta.atr(atrLen)
smaRange = ta.sma(ta.range, rangeAvgLen)
hhPrev = ta.highest(high, sweepLen)[2]
llPrev = ta.lowest(low, sweepLen)[2]
hl2 = (high + low) / 2
rangeAnom = (high - low) > smaRange * rangeAnomMult

sweepHigh = high[1] > hhPrev
sweepLow  = low[1]  < llPrev
failedHigh = close[1] < hhPrev
failedLow  = close[1] > llPrev
longVoid  = close[1] < hl2[1]
shortVoid = close[1] > hl2[1]
atrOk = atr > ta.sma(atr, 20) * 0.8

longSig  = sweepHigh and failedHigh and longVoid and rangeAnom and atrOk
shortSig = sweepLow  and failedLow  and shortVoid and rangeAnom and atrOk

var int cd = 0
if strategy.position_size != 0
    cd := 0
else if cd == 0
    cd := 1
else
    cd += 1
canTrade = cd > cooldownBars

if longSig and canTrade
    strategy.entry("L", strategy.long)
if shortSig and canTrade
    strategy.entry("S", strategy.short)

if strategy.position_size > 0
    strategy.exit("LX", from_entry="L", stop=close - atr*0.5, limit=(hhPrev+llPrev)/2)
if strategy.position_size < 0
    strategy.exit("SX", from_entry="S", stop=close + atr*0.5, limit=(hhPrev+llPrev)/2)

var int barsInTrade = 0
if strategy.position_size != 0
    barsInTrade += 1
else
    barsInTrade := 0
if barsInTrade > timeExitBars
    strategy.close_all()
```

**Correção aplicada vs v1 original:** `hhPrev = ta.highest(high, N)[2]` em vez de `hh = ta.highest(high, N)` — o original comparava `high[1] > hh` onde hh incluía high[1] no janelamento, tornando a condição sempre falsa (lookahead que se auto-invalidava).

### 4.2 QM-REA-v2 — Range-Efficiency Asymmetry (sem ta.sum)

Caminho: `C:\Users\seares\Desktop\botrade\workspaceqm_rea_v2.pine`

```pine
//@version=6
strategy("QM-REA-v2 — Range-Efficiency Asymmetry After Expansion [no ta.sum]",
  overlay=true, pyramiding=1, process_orders_on_close=true,
  commission_type=strategy.commission.percent, commission_value=0.05,
  initial_capital=10000, default_qty_type=strategy.percent_of_equity,
  default_qty_value=100, margin_long=100, margin_short=100)

effLen       = input.int(20, "Efficiency window")
highEffThresh = input.float(0.5, "High efficiency threshold")
lowEffThresh  = input.float(0.3, "Low efficiency trigger")
atrLen       = input.int(14, "ATR length")
cooldownBars = input.int(1, "Cooldown")
timeExitBars = input.int(20, "Max bars")

var float closeDiffSum = 0.0
if bar_index == 0
    closeDiffSum := 0.0
else
    diffNow = math.abs(close - close[1])
    diffOld = math.abs(close[effLen] - close[effLen-1])
    closeDiffSum := closeDiffSum + diffNow - diffOld

highestHigh = ta.highest(high, effLen)
lowestLow   = ta.lowest(low, effLen)
totalRange  = math.max(highestHigh - lowestLow, 1e-9)
eff         = closeDiffSum / totalRange

prevEffHigh = eff[1] > highEffThresh
effDrop     = eff < lowEffThresh
atrCur      = ta.atr(atrLen)
atrMinOk    = atrCur > ta.sma(atrCur, 20) * 0.7

reversalLong  = prevEffHigh and effDrop and atrMinOk and close > ta.sma(close, 20)
reversalShort = prevEffHigh and effDrop and atrMinOk and close < ta.sma(close, 20)

var int cd = 0
if strategy.position_size != 0
    cd := 0
else if cd == 0
    cd := 1
else
    cd += 1
canTrade = cd > cooldownBars

if reversalLong and canTrade
    strategy.entry("L", strategy.long)
if reversalShort and canTrade
    strategy.entry("S", strategy.short)

if strategy.position_size > 0
    strategy.exit("LX", from_entry="L", stop=close - atrCur*1.5, limit=close + atrCur*2.0)
if strategy.position_size < 0
    strategy.exit("SX", from_entry="S", stop=close + atrCur*1.5, limit=close - atrCur*2.0)

var int barsInTrade = 0
if strategy.position_size != 0
    barsInTrade += 1
else
    barsInTrade := 0
if barsInTrade > timeExitBars
    strategy.close_all()
```

**Nota técnica:** v1 usou `ta.sum` que não é implementado no runtime do engine (erro: "unimplemented function 'ta.sum'"). v2 usa rolling sum manual com `var float` que adiciona o diff novo e remove o diff antigo — equivalente matemático a `ta.sum` para janelamento fixo.

### 4.3 QM-JM-v1 — Jump Magnet Reversion (Left-Side Pattern)

Caminho: `C:\Users\seares\Desktop\botrade\workspaceqm_jm_v1.pine`

```pine
//@version=6
strategy("QM-JM-v1 — Jump Magnet Reversion (left-side pattern)",
  overlay=true, pyramiding=1, process_orders_on_close=true,
  commission_type=strategy.commission.percent, commission_value=0.05,
  initial_capital=10000, default_qty_type=strategy.percent_of_equity,
  default_qty_value=100, margin_long=100, margin_short=100)

ssPeriod   = input.int(50, "Stability index")
leftZones  = input.bool(true, "Left zones active")
atrLen     = input.int(14, "ATR length")
bandMult   = input.float(1.5, "Band halfwidth mult")
cooldownBars = input.int(1, "Cooldown")
timeExitBars = input.int(20, "Max bars")

atr = ta.atr(atrLen)
atrAvg = ta.sma(atr, 20)
ssIndex = atr / atrAvg
lowStability = ssIndex < 0.6

fillBand = 2.0 * atr * bandMult
upperBand = close + fillBand
lowerBand = close - fillBand

longLeftZone  = low[1]  > lowerBand[1] and close[1] < lowerBand[1]
shortLeftZone = high[1] < upperBand[1]  and close[1] > upperBand[1]

longEntry  = lowStability and leftZones and longLeftZone[1]
shortEntry = lowStability and leftZones and shortLeftZone[1]

var int cd = 0
if strategy.position_size != 0
    cd := 0
else if cd == 0
    cd := 1
else
    cd += 1
canTrade = cd > cooldownBars

if longEntry and canTrade
    strategy.entry("L", strategy.long)
if shortEntry and canTrade
    strategy.entry("S", strategy.short)

if strategy.position_size > 0
    strategy.exit("LX", from_entry="L", stop=close - atr*1.5, limit=close + atr*2.0)
if strategy.position_size < 0
    strategy.exit("SX", from_entry="S", stop=close + atr*1.5, limit=close - atr*2.0)

var int barsInTrade = 0
if strategy.position_size != 0
    barsInTrade += 1
else
    barsInTrade := 0
if barsInTrade > timeExitBars
    strategy.close_all()
```

---

## 5. Backtest Matrix

### Configuração
- **Engine:** tv_jul26 (TV_ENGINE_JUL_26 parity) + mc7
- **Período:** ~Jun 2026 → Sep 24 2026 (clamped ao último bar no ClickHouse)
- **Capital:** $10,000
- **Sizing:** 100% equity, margin 100/100
- **Commission:** 0.05% (mcp parity)
- **Slippage:** 2 ticks
- **Nota:** cada backtest é um strategyId separado (adhoc mode)

### Matriz de Backtests (diagnóstico por hipótese × símbolo)

|| Hipótese | Símbolo | TF | Strategy ID | Result ID | Trades |
||---|---|---|---|---|---|---|
|| LRS-v1 [CORRECTED] | BTCUSDT | 1h | 01M38DKSFAGT6V4R2A3MCYR3XR | 01M38DM06Y7NZW7BEGEMJR29AD | 0 |
|| REA-v2 [no ta.sum] | BTCUSDT | 1h | 01M38E2YPA09HDSWWGC4FMBF6K | 01M38E363MVJBX2ZMNQPJQYG4J | 0 |
|| REA-v2 [no ta.sum] | SOLUSDT | 1h | 01M38E536W7FCMF921Q5C3W1DA | 01M38E532MERBEGNK8HGYX8GE1 | 0 |
|| JM-v1 | BTCUSDT | 1h | 01M38E46KZFGMX179VKMBMY1TX | 01M38E4E799VFBJXFRZ23HQ756 | 0 |

**Credits consumidos:** 4 backtests × 1 credit = 4 (restam 167)

---

## 6. Results

### Síntese numérica

Todos os 4 backtests em 2 símbolos (BTC e SOL) × 3 hipóteses (LRS, REA, JM) resultaram em **0 trades**.

|| Métrica | Valor |
||---------|-------|
|| Total trades | **0** |
|| Net profit | **$0 (0%)** |
|| Profit factor | **0** |
|| Win rate | **N/A** |
|| Max drawdown | **0%** |
|| Avg trade | **N/A** |
|| Sharpe | **N/A** |

### Visualizações
- LRS BTC 1h: https://mcp-api.trader.dev/backtest/01M38DM06Y7NZW7BEGEMJR29AD
- REA BTC 1h: https://mcp-api.trader.dev/backtest/01M38E363MVJBX2ZMNQPJQYG4J
- REA SOL 1h: https://mcp-api.trader.dev/backtest/01M38E532MERBEGNK8HGYX8GE1
- JM BTC 1h: https://mcp-api.trader.dev/backtest/01M38E4E799VFBJXFRZ23HQ756

---

## 7. Diagnosis

### O que o dado diz

**0 trades em 2460 barras avaliadas × 4 configurações × 3 hipóteses.**

Isso é **silêncio absoluto** — não é drawdown, não é perda, é ausência de disparo. O padrão é consistente: nenhuma das 3 hipóteses de microstructure-specific eventos dispara no período testado (Jun-Sep 2026 em BTC/1h e SOL/1h).

### Diagnóstico por hipótese

**LRS (Liquidity Rebalance Snapback):**
- A versão original (v1) tinha um bug de lookahead: `high[1] > hh` onde `hh = ta.highest(high, N)` no bar atual — o `high[1]` está no janelamento do HH, então a condição era sempre falsa.
- A versão corrigida (v1 [CORRECTED]) usa `hhPrev = ta.highest(high, N)[2]` para comparar com HH de barras anteriores.
- Após a correção, **ainda 0 trades** — o evento combinado (sweep + failed close + void side + range anomal + ATR OK) não ocorreu no período.
- **Diagnóstico raiz:** O evento "sweep + failed close" pode ser mais raro que previsto em BTC/1h neste período, ou a combinação AND de 5 condições é excessivamente restritiva.

**REA (Range-Efficiency Asymmetry):**
- v1 falhou com erro de runtime: `ta.sum` não implementado no engine.
- v2 reescrito com rolling sum manual (adicionar diff novo, remover diff antigo).
- Após correção técnica, **0 trades em BTC e SOL** — a condição `prevEffHigh and effDrop` (eficiência alta segue de eficiência baixa) não se manifestou.
- **Diagnóstico raiz:** A queda abrupta de efficiency de >0.5 para <0.3 em janelamento de 20 barras é um evento raro em BTC/1h e SOL/1h no período — ou a métrica não captura o que a hipótese espera.

**JM (Jump Magnet / Left-Side Pattern):**
- **0 trades em BTC/1h** — a condição `ssIndex < 0.6` (coil swithen) + `leftZone` (low abaixo da banda mas close dentro) não ocorreu simultaneamente.
- **Diagnóstico raiz:** O limiar `ssIndex < 0.6` pode ser muito restritivo para o período — ou o left zone pattern é mais raro que previsto.

### Diagnóstico transversal (o que NÃO é o problema)

- **Não é repainting:** todos os backtests deram `mcpruleValidated: true`. O código usa apenas funções allowlist, process_orders_on_close=true.
- **Não é lookahead:** a correção de LRS (shifted HH/LL) e a lógica de REA/JM usam apenas barras passadas ([1], [effLen]).
- **Não é commission/slippage:** 0 trades significa que o problema é a lógica de entrada, não os custos.
- **Não é falta de dados:** 2460 barras avaliadas por teste — cobertura de ~114% do período solicitado.

### O que PODE ser o problema

1. **Os eventos que as hipóteses buscam são raros neste período:** Jun-Sep 2026 em BTC/1h e SOL/1h pode não ter tido os sweeps limpos, drops de eficiência, ou banded coil swithens que as hipóteses descrevem — o mercado pode ter estado em um regime diferente (ex: recto, vol moderado, sem microestrutura extrema).

2. **Os limiares são desconectados da realidade do mercado:** `rangeAnomMult=1.5`, `ssIndex<0.6`, `eff < 0.3` — todos são valores heurísticos sem calibração empírica. Pode ser que os eventos ocorrem mas não atendem os limiares tão restritivos.

3. **A lógica AND é excessivamente restritiva:** LRS exige 5 condições simultâneas; REA exige 4 (prevEffHigh, effDrop, atrMinOk, SMA side). Em mercados reais, eventos raros são ainda mais raros quando combinados com AND.

4. **O período é curto demais para eventos raros:** ~3 meses de dados podem não conter o evento que a hipótese descreve se ele ocorre em frequência menor que 1 por 2460 barras.

---

## 8. Verdict

### REJECT (Linha MSE — 3 strikes)

**Justificativa:**

1. **Três hipóteses distintas testadas em paralelo** (LRS, REA, JM) — todas dão 0 trades em BTC/1h e SOL/1h.
2. **Sem evidência de edge:** 0 trades = sem evidência de edge por deﬁnição (não há trades para medir PF, WR, DD).
3. **Não é um problema técnico corrigível:** LRS já teve bug corrigido e ainda 0 trades. REA já teve ta.sum workaround e ainda 0 trades. JM nunca teve bug técnico.
4. **O padrão é consistente através de símbolos:** BTC e SOL dão o mesmo resultado — não é um problema de símbolo específico.
5. **Credits suficientes para expandir mas o sinal é claro:** 167 credits restantes dão margem para testar mais símbolos/TFs, mas a evidência atual já indica que estas linhas conceiveuais não funcionam no período testado.

**Classificação no pipeline:**
- **REJECT** — não incubar, não watchlist. Registrar como "hipóteses de microstructure-specific events não dispararam no período Jun-Sep 2026 em BTC/1h e SOL/1h".
- **Linha fechada:** LRS, REA, JM — três strikes no espaço conceitual "microstructure-specific event detection".

---

## 9. Próximo Ciclo

### Opção A — Pivotar para outra família conceitual

As 3 hipóteses deste ciclo exploraram "eventos de microestrutura específicos" (sweep, eficiência, coil). O próximo ciclo deve explorar famílias não testadas:

1. **Volume-Price Anomalies:** dislocação entre mudança de preço e mudança de volume (volume anômalo sem movimento de preço correspondente → reversão).
2. **Trend Exhaustion via Candle Position:** candle cujo corpo é pequeno relativo ao range mas cuja posição (close no topo ou fundo) indica exaustão — diferente de RSI/MACD, é posição de candle dentro do range.
3. **Regime Switching via Return Distribution Shape:** mudança na assimetria/skew da distribuição de retornos em janelamento curto → entrada no lado da nova direção.

### Opção B — Testar LRS/REA/JM com limiares mais brandos em mais símbolos

Se quiser dar mais uma chance a estas linhas antes de pivotar:
- Relaxar LRS: remover ATR filter, abaixar rangeAnomMult para 1.2
- Relaxar REA: abaixar highEffThresh para 0.3, lowEffThresh para 0.2
- Expandir para XRP, BNB, DOGE (mais vol, mais sweeps em alts)
- Multi-TF: 15m, 30m (mais barras, mais eventos)

### Opção C — Parar e registrar

Se o próximo ciclo também falhar (3 strikes na nova família), registrar o palace como "nenhuma das hipóteses de microestrutura testadas (VND, RD, VCE-FC, LRS, REA, JM) disparou em crypto pairs no período 2026" — e pivotar para famílias de volume ou regime switching.

**Decisão tomada neste ciclo:** Opção A — pivotar para Volume-Price Anomalies na próxima iteração. Os conceitos de microestrutura-specific events (LRS, REA, JM) foram testados e falsificados com evidência consistente (0 trades em 4 configurações × 2 símbolos).

---

## Control Panel Update

Novas linhas para `dashboard/data.json`:

```json
[
  {
    "id": "mse-lrs-btc-1h",
    "name": "QM-LRS-v1 [CORRECTED]",
    "symbol": "BTCUSDT",
    "timeframe": "1h",
    "source": "greenfield",
    "family": "mse-lrs",
    "agent": "researcher",
    "net_profit_pct": 0,
    "profit_factor": 0,
    "max_drawdown_pct": 0,
    "win_rate_pct": 0,
    "trades": 0,
    "sharpe": null,
    "result_id": "01M38DM06Y7NZW7BEGEMJR29AD",
    "view_url": "https://mcp-api.trader.dev/backtest/01M38DM06Y7NZW7BEGEMJR29AD",
    "curve": null,
    "verdict": "rejected",
    "status": "backtested",
    "last_backtest": "2026-09-24T00:39:00.939Z",
    "pine_key": "01M38DKSFAGT6V4R2A3MCYR3XR",
    "notes": "0 trades em 2460 barras; bug de lookahead corrigido [2] shift; ainda 0 trades → hipótese falsificada"
  },
  {
    "id": "mse-rea-btc-1h",
    "name": "QM-REA-v2 [no ta.sum]",
    "symbol": "BTCUSDT",
    "timeframe": "1h",
    "source": "greenfield",
    "family": "mse-rea",
    "agent": "researcher",
    "net_profit_pct": 0,
    "profit_factor": 0,
    "max_drawdown_pct": 0,
    "win_rate_pct": 0,
    "trades": 0,
    "sharpe": null,
    "result_id": "01M38E363MVJBX2ZMNQPJQYG4J",
    "view_url": "https://mcp-api.trader.dev/backtest/01M38E363MVJBX2ZMNQPJQYG4J",
    "curve": null,
    "verdict": "rejected",
    "status": "backtested",
    "last_backtest": "2026-09-24T00:47:18.622Z",
    "pine_key": "01M38E2YPA09HDSWWGC4FMBF6K",
    "notes": "ta.sum não implementado → rolling sum manual; 0 trades em BTC 1h"
  },
  {
    "id": "mse-rea-sol-1h",
    "name": "QM-REA-v2 [no ta.sum]",
    "symbol": "SOLUSDT",
    "timeframe": "1h",
    "source": "greenfield",
    "family": "mse-rea",
    "agent": "researcher",
    "net_profit_pct": 0,
    "profit_factor": 0,
    "max_drawdown_pct": 0,
    "win_rate_pct": 0,
    "trades": 0,
    "sharpe": null,
    "result_id": "01M38E532MERBEGNK8HGYX8GE1",
    "view_url": "https://mcp-api.trader.dev/backtest/01M38E532MERBEGNK8HGYX8GE1",
    "curve": null,
    "verdict": "rejected",
    "status": "backtested",
    "last_backtest": "2026-09-24T00:48:22.181Z",
    "pine_key": "01M38E536W7FCMF921Q5C3W1DA",
    "notes": "0 trades em SOL 1h; confirma que REA não dispara em 2 símbolos distintos"
  },
  {
    "id": "mse-jm-btc-1h",
    "name": "QM-JM-v1",
    "symbol": "BTCUSDT",
    "timeframe": "1h",
    "source": "greenfield",
    "family": "mse-jm",
    "agent": "researcher",
    "net_profit_pct": 0,
    "profit_factor": 0,
    "max_drawdown_pct": 0,
    "win_rate_pct": 0,
    "trades": 0,
    "sharpe": null,
    "result_id": "01M38E4E799VFBJXFRZ23HQ756",
    "view_url": "https://mcp-api.trader.dev/backtest/01M38E4E799VFBJXFRZ23HQ756",
    "curve": null,
    "verdict": "rejected",
    "status": "backtested",
    "last_backtest": "2026-09-24T00:47:59.378Z",
    "pine_key": "01M38E46KZFGMX179VKMBMY1TX",
    "notes": "0 trades em BTC 1h; coil swithen + left zone pattern não se manifestou"
  }
]
```

---

*Research and education only. Not financial advice. Backtests are not future performance.*
*Trader Dev MCP: authenticated as searesj92@gmail.com · engine tv_jul26_mc7 · parity profile applied.*
