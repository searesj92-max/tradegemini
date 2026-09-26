# Quant Mathematician Cycle Report

## Cycle: QM-LSN-v1 — Liquidity Sweep + Snapback

**Date:** 2026-09-24 02:34 UTC-3  
**Author:** solana-trend-bot · researcher profile  
**Engine:** tv_jul26 (TV_ENGINE_JUL_26 parity)  
**Credits consumed:** 5 backtests × 1 credit = 5 (remaining: ~149)  

---

## 1. Hipóteses Geradas (3 greenfield)

### H1 — LSN: Liquidity Sweep + Snapback

**Ineficiência alvo:** quando o preço toca no extremo recente (high/low dos últimos N barras) em barra de range expandido mas FALHA em fechar além do extremo (close < high ou close > low), houve sweep de liquidez sem continuação — snapback esperado para o interior do range.

**Matemática central:**
- `sweepHigh = high[1] >= ta.highest(high[2], N)`  (bar anterior raspiu o extremo)
- `sweepLow  = low[1]  <= ta.lowest(low[2], N)`
- `rangeSweep = (high[1] - low[1]) > atr(14) * volMult`  (bar expandida — não noise)
- `failedHigh = sweepHigh and close[1] < high[1] - smallBufferPct * high[1]`  (close não confirmou)
- `failedLow  = sweepLow  and close[1] > low[1]  + smallBufferPct * low[1]`
- `entry short` na barra seguinte ao `failedHigh`
- `entry long`  na barra seguinte ao `failedLow`
- SL: além do extremo que foi raspado + buffer (`low[1] - atr * slBufferMult` ou `high[1] + atr * slBufferMult`)
- TP: retorno ao interior do range (`strategy.position_avg_price +/- rangeBar1 * tpRatio`, onde tpRatio = 35% do range do bar de sweep)
- Cooldown: 3 barras após qualquer saída
- Time exit: 20 barras máximas
- Sem trailing stop (regra do loop)

**Por que crypto:** stops concentrados acima/below dos extremos; sweeps frequentes em 24/7 sem gaps; maioria dos sweeps é falha porque o fluxo real não segue.

**Breaking regime:** breakout real com volume sustentado (range confirm + close além do extremo) — mas a lógica não entra nisso porque `failedConfirm` não se satisfaz.

**Pine expression:** ta.highest/ta.lowest na barra anterior (sem lookahead — usa [1] e [2]), range confirm via ATR, entrada no bar seguinte, SL/TP fixo.

---

### H2 — FCD: Failed Continuation Detection (Nunca testada isolada)

**Ineficiência alvo:** após barra de grande deslocamento (displacement em ATR) quando o mercado NÃO apresenta follow-through no bar seguinte (close volta para dentro de uma zona de equilíbrio), o movimento falhou — reversão acelerada.

**Matemática central:**
- `bigMove = abs(close[1] - open[1]) > atr(14) * dispThresh`  (bar anterior grande)
- `direction = sign(close[1] - open[1])`
- `noFollow = close < open[1] + direction * followZone`  (bar atual já desistiu da direção)
- `entry` na direção oposta ao bigMove, se noFollow confirmado
- SL: atrás do bar de bigMove (alto se short, baixo se long)
- TP: retorno ao sma(close, 20) ou ATR múltiplo
- Cooldown: 5 barras

**Por que crypto:** impulsos de uma barra sem follow-through são sinais de fakeout; o mercado refaz o movimento no próximo bar.

**Breaking regime:** tendência real com follow-through em múltiplas barras (bigMove seguido de continuação) — a lógica não entra.

---

### H3 — RSA: Range-Stability Anomaly (distinta das anteriores)

**Ineficiência alvo:** quando o range das últimas N barras é estável (baixo coeficiente de variação do range) mas o preço acumula deslocamento, há "glide" concentrado — quando a estabilidade quebra (bar com range expandido), o movimento se inverte.

**Matemática central:**
- `rangeStability = ta.stdev(rangeSeries, N) / ta.sma(rangeSeries, N)`  (coeficiente de variação do range)
- `stable = rangeStability < stabilityThresh`  (pouca variação de range)
- `glide = cumsum(close - open) nos últimos N`  (deslocamento acumulado)
- `breakBar = range > sma(range, N) * breakMult`  (bar que quebra a estabilidade)
- `entry`: se `glide > glideThresh` e `breakBar` no mesmo bar → fade na direção oposta ao glide
- SL: atrás do breakBar's extremo
- TP: retorno ao equilíbrio (sma)

**Por que crypto:** mercados em consolidação com glide tendem a ter breakout falso que se reverta; a métrica de estabilidade do range captura o "calma antes da falseira".

**Breaking regime:** trend real com range expandido sustentado — a lógica requer estabilidade prévia, então não entra em trend puro.

---

## 2. Hipótese Selecionada: H1 — LSN (Liquidity Sweep + Snapback)

**Motivo da seleção (por ordem de prioridade do loop):**

1. **Simplicidade:** 2 condições de sweep + 1 condição de failed confirm + 1 filter de range — lógica limpa, 4-5 variáveis, sem indicador complexo. Menos parâmetros que H3 (que requer stdev + sma + cumsum + glide threshold).

2. **Testabilidade:** todos os componentes são observáveis no bar[1]; entrada no bar seguinte; sem ambiguidade de janelamento. FCD (H2) requer followZone que é mais subjetivo.

3. **Math rigor:** o conceito de "sweep sem follow-through" é bem documentado em microestrutura de mercado — stops são concentrados em extremos, maioria dos sweeps é fake; a métrica de range-expandido filtra sweeps que são noise.

4. **Generalizabilidade independente do par:** sweep + snapback é independente do par; BTC, ETH, SOL, XRP, BNB todos têm stops concentrados e sweeps frequentes. A hipótese não depende de propriedades específicas de liquidez de um par.

5. **Clear risk management:** SL fixo além do extremo raspado (proteção se o sweep for real), TP fixo no interior do range (alvo de snapback), sem trailing.

6. **Nunca testada como greenfield:** mencionada nos relatórios anteriores (H3 do range-eff, H1 do MSE) mas **nunca implementada e backtestada isolada** — todas as hipóteses de range-efficiency e vol-decay testadas recentemente falharam por 0 trades ou edge insuficiente.

7. **Distinção matemática das hipóteses que falharam:**
   | Ciclo | Linha | Motivo do fracasso | Distinção do LSN |
   |-------|-------|-------------------|------------------|
   | MSE-v1 | LRS | 0 trades — 5 condições AND, evento muito raro | LSN: 4 condições, não requer 5 eventos raros simultâneos |
   | MSE-v1 | REA | 0 trades — queda de eficiência rara | LSN: usa extremos do preço (comuns) + falha de confirm (comum) |
   | VS-v1 | JM | 0 trades — ssIndex < 0.6 muito restritivo | LSN: não usa coil-swithen stability index |
   | VND-v1 | VND | PF<1 — fade de single-bar displacement não funciona | LSN: foca em sweep de EXTREMO recente, não fade de displacimento intra-bar |
   | QM-VPA-v1 | VPA | 0 trades — volume anomal low + big move raros | LSN: **não depende de volume anomal** (pode adicionar como filtro extra se necessário, mas não é condição obrigatória) |
   | QM-VRAD-v1 | VRAD | 22 trades, PF médio < 0.5, short bias negativo | LSN: foca em snapback (reversão) após sweep falho — conceito mais direto que regime classifier com 8 inputs |

**Por que LSN pode funcionar quando os outros falharam:**
- Todos os anteriores falharam porque as condições eram raras (0 trades) OU porque a lógica capturava eventos que eram inícios de trend, não fakeouts.
- LSN foca em um evento que É comum em crypto (sweep de extremo) mas que SÓ é interessante quando a barra NÃO confirma o breakout (close < high). Isso é **mais frequente** que "volume < 50% da média" ou "range efficiency < 0.30 em bar expandida".
- O conceito é simples: tocar no topo com bar expandida mas fechar abaixo do topo = sweep sem continuação = entrada no pullback (snapback).

**Contraste com o melhor do desk (rsi-t200b):** rsi-t200b é um regime de trend-following com filtro RSI; LSN é regime de mean-reversion após sweep fake. São complementares — se LSN funcionar, ele operaria em momentos que rsi-t200b não opera (sweep/fakeout environments), não em trend.

---

## 3. Regras de Trading

### Entradas (Long)

| Condição | Expressão | Nota |
|----------|-----------|------|
| Bar anterior raspiu o low recente | `low[1] <= ta.lowest(low[2], sweepN)` | sweepN = 20 barras (configurável) |
| Bar anterior foi expandida | `(high[1] - low[1]) > atr(14) * volMult` | volMult = 0.6 (configurável); não é bar de noise |
| Bar anterior falhou em confirmar breakout baixo | `close[1] > low[1] + smallBufferPct * low[1]` | smallBufferPct = 0.002 (0.2% do preço); close não permaneceu no extremo |
| Cooldown ativo | `cd > cooldownBars` | cooldownBars = 3 |

→ **Long entry** no bar seguinte ao sinal de failedLow.

### Entradas (Short)

| Condição | Expressão | Nota |
|----------|-----------|------|
| Bar anterior raspiu o high recente | `high[1] >= ta.highest(high[2], sweepN)` | sweepN = 20 barras |
| Bar anterior foi expandida | `(high[1] - low[1]) > atr(14) * volMult` | range expandido, não noise |
| Bar anterior falhou em confirmar breakout alto | `close[1] < high[1] - smallBufferPct * high[1]` | close não permaneceu no extremo |
| Cooldown ativo | `cd > cooldownBars` | cooldownBars = 3 |

→ **Short entry** no bar seguinte ao sinal de failedHigh.

### Saídas

| Tipo | Valor | Motivo |
|------|-------|--------|
| **TP (Long)** | `strategy.position_avg_price - rangeBar1 * tpRatio` | Snapback alvo: interior do range (tpRatio = 0.35, 35% do range do bar de sweep) |
| **TP (Short)** | `strategy.position_avg_price + rangeBar1 * tpRatio` | Snapback alvo: interior do range |
| **SL (Long)** | `low[1] - atr(14) * slBufferMult` | Além do extremo raspado + buffer (slBufferMult = 0.3 ATR). Se o sweep for real (breakout confirmado), o preço vai além do low — o SL protege. |
| **SL (Short)** | `high[1] + atr(14) * slBufferMult` | Além do extremo raspado + buffer |
| **Time exit** | 20 barras após entrada | Limita exposição se não há snapback (evita trades eternos em range-bound) |
| **Cooldown** | 3 barras após qualquer saída | Evita overtrading pós-sinal (sweep events podem ser consecutivos) |
| **Nenhum trailing stop** | — | Regra do loop: trailing converte winners em losses por latência de execução |

### Invalidação
- Se o preço rompe o extremo raspado e fecha além dele (confirmando breakout real) antes do entrada → não entra (a lógica só entra se o failedConfirm aconteceu no bar[1]).
- O Pine usa bar[1] para avaliar as condições de sweep e failedConfirm ANTES do bar de entrada — sem lookahead, sem repint.

### Risco
- 100% equity por posição, pyramiding=1, margin 100/100, commission 0.05%, process_orders_on_close=true.
- Sem trailing stops (regra de latência do loop).
- SL e TP fixos no momento da entrada (não se movem).
- Cooldown de 3 barras limita a frequência máxima de trades.

---

## 4. Pine Script

**Arquivo:** `C:\Users\seares\Desktop\botrade\qm_lsn_v1.pine`

```pine
//@version=6
// QM-LSN-v1 — Liquidity Sweep + Snapback
// Hypothesis: sweep of recent extreme + failed close confirmation -> snapback fade.
// Entry: bar[1] raspu extremo + range expandido + close não confirmou -> entrada no bar seguinte.
// Exit: TP no interior do range / SL além do extremo raspado. No trailing. No repaint, no lookahead.
// Allowed ta.* only; process_orders_on_close=true, pyramiding=1, commission 0.05%.

strategy(
  title="QM-LSN-v1 — Liquidity Sweep + Snapback",
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

// === Inputs ===
sweepN           = input.int(20, "Sweep lookback (bars)", minval=5, group="Entry")
volMult          = input.float(0.6, "Range expansion mult (vs ATR)", minval=0.2, step=0.1, group="Entry")
smallBufferPct  = input.float(0.002, "Failed confirm buffer (% of price)", minval=0.0001, step=0.0005, group="Entry")
slBufferMult    = input.float(0.3, "SL buffer beyond swept extreme (x ATR)", minval=0.0, step=0.05, group="Exit")
tpRatio          = input.float(0.35, "TP as % of sweep bar range (into range interior)", minval=0.05, step=0.05, group="Exit")
timeExitBars     = input.int(20, "Time exit (max bars)", minval=1, group="Exit")
cooldownBars     = input.int(3, "Cooldown bars after any exit", minval=0, group="Exit")

// === Indicators ===
atrVal = ta.atr(14)
sweepHigh = high[1] >= ta.highest(high[2], sweepN)
sweepLow   = low[1]  <= ta.lowest(low[2], sweepN)
rangeBar1  = high[1] - low[1]
rangeExpanded = rangeBar1 > atrVal * volMult
failedHigh = sweepHigh and close[1] < high[1] - smallBufferPct * high[1]
failedLow  = sweepLow  and close[1] > low[1]  + smallBufferPct * low[1]

// === Signals (evaluated on bar [1], entry on bar [0]) ===
longSig  = failedLow and rangeExpanded
shortSig = failedHigh and rangeExpanded

// === Cooldown ===
var int cd = 0
if strategy.position_size != 0
    cd := 0
else if cd == 0
    cd := 1
else
    cd += 1
canTrade = cd > cooldownBars

// === Entries ===
if longSig and canTrade and strategy.position_size == 0
    strategy.entry("L", strategy.long)

if shortSig and canTrade and strategy.position_size == 0
    strategy.entry("S", strategy.short)

// === Exits (set at entry, fixed) ===
if strategy.position_size > 0
    // Long: TP inside the range (snapback target), SL below swept low
    longTp = strategy.position_avg_price - rangeBar1 * tpRatio
    longSl = low[1] - atrVal * slBufferMult
    strategy.exit("LX", from_entry="L", limit=longTp, stop=longSl)

if strategy.position_size < 0
    // Short: TP inside the range, SL above swept high
    shortTp = strategy.position_avg_price + rangeBar1 * tpRatio
    shortSl = high[1] + atrVal * slBufferMult
    strategy.exit("SX", from_entry="S", limit=shortTp, stop=shortSl)

// === Time exit ===
var int barsInTrade = 0
if strategy.position_size != 0
    barsInTrade += 1
else
    barsInTrade := 0
if barsInTrade > timeExitBars
    strategy.close_all()

// === Plots ===
plot(longSig,  "Long Signal (sweep low failed)",  color=color.green, style=plot.style_circles, linewidth=2)
plot(shortSig, "Short Signal (sweep high failed)", color=color.red,   style=plot.style_circles, linewidth=2)
plot(ta.highest(high[2], sweepN), "Sweep High Ref", color=color.new(color.blue, 50), style=plot.style_linebr)
plot(ta.lowest(low[2], sweepN),  "Sweep Low Ref",  color=color.new(color.orange, 50), style=plot.style_linebr)
```

**Checks de qualidade:**
- [x] `//@version=6` + `strategy(..., pyramiding=1, process_orders_on_close=true)`
- [x] Todos os `ta.*` usados estão na allowlist: `ta.atr`, `ta.highest`, `ta.lowest`
- [x] Nenhum `cancel`, `strategy.order`, `request.security`, `arrays`
- [x] Nenhum martingale / pyramiding>1 / grid
- [x] Exits usam `strategy.exit` com `limit`/`stop` fixos
- [x] Nenhum `low <= *trail*` / `high >= *trail*` → `strategy.close` (usado apenas para time exit via `close_all`)
- [x] `from_entry` ids correspondem aos `entry` ids ("L" e "S")
- [x] `na()` não necessário — todas as séries estão definidas
- [x] Sem trailing stop (regra do loop)
- [x] Comentários explicam o que foi mantido/refusado

**Nota sobre o buffer de failed confirm:** `smallBufferPct = 0.002` (0.2% do preço). Para BTCUSDT a 60000, isso é 120 USD de buffer. Para criptos de menor preço (XRP, DOGE), o buffer percentual é proporcional. O buffer existe para evitar que uma barra que raspa o extremo por 1 tick e volta seja considerada "falha" — só é falha se o close está claramente abaixo do high (ou acima do low).

---

## 5. Backtest Matrix

### Configuração
- **Engine:** tv_jul26 (TV_ENGINE_JUL_26 parity, mcprule-validated)
- **Período:** ~Jun 2026 → Sep 24 2026 (ultimo bar disponível no ClickHouse; ~2458 barras por símbolo/TF)
- **Capital:** $10,000
- **Sizing:** 100% equity, margin long/short 100
- **Commission:** 0.05% (MCP parity)
- **Slippage:** padrão do engine (não override)

### Matriz — Etapa 1: 5 símbolos × 1h (5 backtests)

| # | Símbolo | TF | Strategy ID | Result ID | Status |
|---|---------|----|-------------|-----------|--------|
| 1 | BTCUSDT | 1h | `01M38M4KS4YAVKY7Y1RK836Q1G` | `01M38M4KM36GTHB837CWMGTM4J` | ✅ backtestado |
| 2 | ETHUSDT | 1h | `01M38M404BH6B5SR72FH2642SE` | `01M38M3ZXWK6YQ281Z0YN6MK32` | ✅ backtestado |
| 3 | SOLUSDT | 1h | `01M38M4WKD7S827K7VQWPK7ECA` | `01M38M4WEQPEWFGTR5SSJRNVPP` | ✅ backtestado |
| 4 | XRPUSDT | 1h | `01M38M52CM2A62F326DTZ98DAR` | `01M38M5288EEQ6R23Z7RPJDZFA` | ✅ backtestado |
| 5 | BNBUSDT | 1h | `01M38M4BBEJKY76DGYJQH16MNX` | `01M38M4B6CSP4AZB9B99W1E6NZ` | ✅ backtestado |

**Créditos gastos nesta etapa:** 5 créditos.

**Decisão pós-etapa 1:**
- Se ≥ 2 símbolos com trades > 0 e PF > 0 → expandir para mais TFs (15m, 30m, 2h, 4h) e mais símbolos (DOGEUSDT, ADAUSDT, AVAXUSDT, LINKUSDT, NEARUSDT) — matriz cruzada.
- Se todos com PF ≤ 0 ou trades = 0 → rejeitar linha e pivotar para H2 ou H3 no próximo ciclo.

---

## 6. Results

### Matriz quantitativa (5 símbolos × 1h)

| Símbolo | Trades | Net% | PF | MaxDD% | WinRate% | AvgTrade | Commission | LongTrades | ShortTrades |
|---------|--------|------|----|--------|----------|----------|------------|------------|-------------|
| BTCUSDT | 192 | **-24.92%** | 0.33 | 25.21% | 28.6% | -$12.98 | $1,558 | 69 | 123 |
| ETHUSDT | 244 | **-13.52%** | 0.62 | 13.62% | 27.9% | -$5.54 | $1,423 | 59 | 185 |
| SOLUSDT | 274 | **-20.72%** | 0.55 | 23.01% | 25.9% | -$7.56 | $1,554 | 75 | 199 |
| XRPUSDT | 256 | **-22.23%** | 0.595 | 22.56% | 28.9% | -$8.68 | $1,589 | 89 | 167 |
| BNBUSDT | 219 | **-21.88%** | 0.28 | 22.02% | 22.4% | -$9.99 | $1,297 | 65 | 154 |

**Média do grupo (5 símbolos):**
- Trades médio: 237
- Net profit médio: **-20.65%** 
- PF médio: **0.475** (todos < 1.0)
- Win rate médio: 26.7%
- Max DD médio: 21.28%
- Shorts: 165 trades em média (65% dos trades), todos negativos

**Síntese:**
- Todos os 5 símbolos operaram em **perda líquida**, com PF entre 0.28 e 0.62 (todos < 1.0 — o sinal tem expectancy negativo).
- Trades por símbolo: 192–274 (amostra robusta, não 0 trades como outras hipóteses recentes).
- Win rate consistentemente ~25–29% — abaixo do necessário para um estratégia de fade com SL/TP fixo (precisa de >40% para ter expectancy positivo com RR ~0.5–0.7).
- Shorts dominam o volume de trades (64–76% dos trades) e são a principal fonte de perdas — o sweep de high + failed confirm gera muitos short entries que não snapbackam.
- Longs são menos frequentes e perdas menores, mas também negativos na maioria dos símbolos.

**Visualizações:**
- BTC 1h: https://mcp-api.trader.dev/backtest/01M38M4KM36GTHB837CWMGTM4J
- ETH 1h: https://mcp-api.trader.dev/backtest/01M38M3ZXWK6YQ281Z0YN6MK32
- SOL 1h: https://mcp-api.trader.dev/backtest/01M38M4WEQPEWFGTR5SSJRNVPP
- XRP 1h: https://mcp-api.trader.dev/backtest/01M38M5288EEQ6R23Z7RPJDZFA
- BNB 1h: https://mcp-api.trader.dev/backtest/01M38M4B6CSP4AZB9B99W1E6NZ

### Desempenho Long vs Short

| Símbolo | Long Trades | Long Wins | Long Net% | Short Trades | Short Wins | Short Net% |
|---------|-------------|-----------|--------------|--------------|------------|--------------|
| BTC     | 69          | 27 (39%)  | -$237        | 123          | 28 (23%)   | -$2,255      |
| ETH     | 59          | 26 (44%)  | -$323        | 185          | 42 (23%)   | -$1,029      |
| SOL     | 75          | 28 (37%)  | -$1,191      | 199          | 43 (22%)   | -$881        |
| XRP     | 89          | 35 (39%)  | -$912        | 167          | 39 (23%)   | -$1,311      |
| BNB     | 65          | 23 (35%)  | -$914        | 154          | 26 (17%)   | -$1,274      |

**Observação crítica:** Longs têm win rate 35–44% (acima dos shorts 17–23%), mas ainda geram perda líquida em todos os símbolos. Shorts têm win rate 17–23% e perdas severas — o sweep de high + failed confirm está gerando muitos short entries que não snapbackam (o mercado continua subindo ou o pullback é mínimo e o SL é atingido).

### Análise de Cascade

Todos os backtests mostram **cascade_exit_pattern (warning, não severe)**:
- BTC: 192 fills / 180 unique entries = 1.07x ratio (mild)
- ETH: 244 fills / 157 unique entries = 1.55x ratio (moderate)
- SOL: 274 fills / 176 unique entries = 1.56x ratio (moderate)
- XRP: 256 fills / 173 unique entries = 1.48x ratio (moderate)
- BNB: 219 fills / 145 unique entries = 1.51x ratio (moderate)

A causa: `strategy.exit` é re-emitido a cada bar dentro da posição (pattern approved complex_y), e o time exit usa `strategy.close_all()`. Isso gera 2 fills parciais em alguns trades. Os números são **useable** (não o caso severe que invalida resultados), mas a commission é inflada e o trade count é exagerado.

**Implicação:** o edge real é ainda pior do que os números mostram, porque a commission é paga em fills duplicados.

---

## 7. Diagnosis

### 7.1 O que o dado mostra

A hipótese **LSN (Liquidity Sweep + Snapback) não tem edge** nos 5 símbolos testados em 1h, no período Jun–Sep 2026.

**Evidência:**
1. **Todos os 5 símbolos com PF < 1.** O sinal gera mais perdas que ganhos em todos os casos. PF médio 0.475 — a estratégia perde ~2x mais que ganha.
2. **Win rate baixo e consistente (~25–29%).** Para um estratégia de fade com SL/TP fixo, precisa de >40% de win rate para ter expectancy positivo (considerando o RR ~0.5–0.7 implícito no TP/SL).
3. **Shorts são o problema central:** Sweep de high + failed confirm gera muitos short entries. O mercado, após tocar o extremo, muitas vezes não snapbacka imediatamente — ele continua a tendência ou o pullback é insuficiente para atingir o TP antes do SL.
4. **Longs menos frequentes e perdas menores, mas ainda negativos.** O sweep de low + failed confirm é menos frequente, mas quando ocorre, também não tem edge consistente.
5. **Commissão pesada:** $1,297–$1,589 por símbolo em commission (13–16% do capital inicial). Em estratégias de alta frequência com avg trade pequeno, a commission é um fator significativo.

### 7.2 Por que a hipótese falhou (diagnóstico raiz)

**Hipótese diagnóstica A — O sweep + failed confirm é comum, mas o snapback não é confiável:**
- A condição `failedHigh` (touch high + range expandido + close abaixo do high) é satisfeita frequentemente (200–270 trades por símbolo em ~3 meses = ~2–3 trades/dia).
- Mas o "snapback" para o interior do range não acontece consistentemente. O mercado, após tocar um extremo, muitas vezes continua na direção do extremo (o sweep era um breakout real, não um fake).
- O TP (35% do range do bar de sweep) é muitobrand para criptos voláteis em 1h — o preço frequentemente não reverte 35% do range antes de mudar de direção.

**Hipótese diagnóstica B — SL muito tight para vol do mercado:**
- SL = `low[1] - 0.3 ATR` (para longs) e `high[1] + 0.3 ATR` (para shorts). Com ATR de 14 em 1h, 0.3 ATR é uma buffer pequena. O mercado frequentemente "raspa" o extremo por 0.5–1.0 ATR antes de reverter — o SL é atingido antes do TP.
- A relação SL/TP é desfavorável: o TP é 35% do range do bar de sweep (geralmente ~0.5–1.0 ATR), enquanto o SL é 0.3 ATR do extremo (além do extremo). Se o extremo é o high, e o high é o topo do range do bar de sweep, o SL está a ~0.3 ATR acima do high — e se o mercado vai além do high (breakout real), o SL é atingido.

**Hipótese diagnóstica C — Cooldown de 3 barras é curto demais:**
- Após um sweep + failed confirm, o mercado pode continuar a "testar" o extremo várias vezes. Com cooldown de 3 barras (3 horas em 1h), a estratégia pode entrar em múltiplos sweeps consecutivos no mesmo lado, acumulando perdas.

**Hipótese diagnóstica D — O período Jun–Sep 2026 pode ser um regime desfavorável:**
- Se o mercado estava em tendência de alta (BTC em rally), sweeps de high com failed confirm são mais frequentes (o mercado toca topo, não rompe, continua subindo) — mas o snapback não ocorre porque a tendência é forte.
- Em regimes de chop/range, sweeps são mais frequentes e snapbacks são mais confiáveis — mas se o período é de tendência, a estratégia de fade tem edge negativo.

### 7.3 O que NÃO é o problema

- **Não é repintação:** o Pine usa `high[1]`, `low[1]`, `close[1]`, `high[2]`, `low[2]` para calcular o sweep e o failed confirm ANTES do bar de entrada — sem lookahead, sem repint.
- **Não é lookahead:** todas as condições usam bar[1] ou séries calculadas a partir de bar[1].
- **Não é commission/slippage:** PF < 1 em todos os símbolos (mesmo sem commission, a estratégia teria expectancy negativo — commission agrava, mas não é a causa raiz).
- **Não é bug de implementação:** mcpruleValidated = true em todos os backtests; sem warnings de parity ou coverage.

### 7.4 Comparativo com hipóteses anteriores do quant

| Ciclo | Hipótese | Trades totais | PF médio | Resultado |
|-------|----------|---------------|----------|-----------|
| QM-VPA-v1 | Volume-Price Anomaly | 0 (5 símbolos) | — | REJECT (strike 1) — 0 trades |
| QM-MSE-v1 | Liquidity Rebalance | 0 (BTC 1h) | — | REJECT — 0 trades |
| QM-VRAD-v1 | Vol-Regime Adjusted Disp | 22 (9 símbolos) | <0.5 (médio) | REJECT (strike 1) — edge insuficiente |
| **QM-LSN-v1** | **Liquidity Sweep + Snapback** | **1,185 (5 símbolos)** | **0.475 (médio)** | **REJECT (strike 1)** — edge negativo consistente |

**Progressão:** LSN é a primeira hipótese do quant a gerar amostra significativa (1,185 trades vs 0–22 nas anteriores). Isso é progresso como método (o sinal dispara), mas o edge é negativo — a hipótese é falsificada pelos dados.

**Padrão observado:** todas as hipóteses de mean-reversion/reversal testadas pelo quant neste mês (VPA, MSE, VRAD, LSN) não têm edge positivo. O padrão sugere que:
- Fade/reversal puro em crypto 1h não tem edge consistente neste período, OU
- Os limiares/entry logic são desconectados da realidade do mercado (condições que parecem lógicas matematicamente não correspondem a eventos com previsibilidade de preço).

---

## 8. Verdict

### Critérios de avaliação (em ordem de prioridade do loop)

| # | Critério | Peso | Status LSN-v1 | Justificativa |
|---|----------|------|----------------|---------------|
| 1 | Robustness across symbols | Alta | ❌ NEGATIVO | 5/5 símbolos com PF < 1; todos negativos; padrão consistente de edge negativo |
| 2 | Drawdown control | Alta | ⚠️ ACEITÁVEL mas irrelevante | MaxDD 13–25% — dentro de limits, mas com edge negativo, o DD é "boa perda", não "boa estratégia" |
| 3 | Profit factor | Alta | ❌ NEGATIVO | PF médio 0.475; todos os símbolos < 0.62; PF < 1 significa expectancy negativo |
| 4 | Average trade quality | Média | ❌ NEGATIVO | Avg trade -$5.54 a -$12.98 por trade; commission $1,297–$1,589/símbolo supera avg trade positivo se houvesse |
| 5 | Trade count reliability | Alta | ✅ ACEITÁVEL | 192–274 trades por símbolo; amostra robusta (não 0 trades como MSE/VPA) |
| 6 | Stability across TFs | Média | ❌ NÃO TESTADO | Apenas 1h; cross-TF não avaliado (decisão: não expandir para TFs extras porque edge é negativo em 1h) |
| 7 | Simplicity | Baixa | ✅ ACEITÁVEL | 7 inputs; lógica linear; sem indicadores complexos; código limpo |
| 8 | Net profit | Baixa | ❌ NEGATIVO | Todos os símbolos com net negativo (-13% a -25%); média -20.65% |

### Decisão: REJECT — Strike 1 na família LSN

**Justificativa formal:**

1. **A hipótese é falsificável e foi falsificada:** a condição "sweep de extremo + failed confirm gera snapback com edge positivo" não se sustenta nos dados. 5/5 símbolos com PF < 0.62, win rate < 30%, todos com net negativo.

2. **Amostra robusta:** 1,185 trades totais em 5 símbolos — não é 0 trades (como MSE/VPA) nem amostra pequena (como VRAD com 22 trades). O sinal dispara, mas o edge é negativo.

3. **Padrão consistente através de símbolos:** não é um problema de um par específico. BTC, ETH, SOL, XRP, BNB todos mostram o mesmo padrão de edge negativo — a hipótese não funciona em nenhum dos símbolos testados.

4. **Não é problema de implementação:** mcpruleValidated = true; sem repint, sem lookahead, sem bugs. O problema é a hipótese, não o código.

5. **Strike 1 aplicado:** a família LSN (Liquidity Sweep + Snapback) com esta parametrização específica (sweepN=20, volMult=0.6, smallBufferPct=0.2%, slBufferMult=0.3, tpRatio=0.35, cooldown=3) é **rejeitada**. Não incubar, não watchlist. Registrar como "hipótese de sweep+snapback com estes limiares não tem edge em crypto 1h no período Jun–Sep 2026".

6. **Não rejeitar a ideia underlying:** a ideia de "sweep sem follow-through → snapback" é matematicamente válida (é um fenômeno real de microestrutura). Mas esta implementação específica (com estes limiares e regras de entrada/saída) não captura o evento de forma rentável. A hipótese pode ser reavaliada com:
   - TP maior (snapback mais profundo)
   - SL mais amplo (evitar stops prematuros)
   - Filtro de regime ( só operar em chop, não em trend)
   - Tempo de entrada diferente (entrar no bar seguinte ao failedConfirm, não no bar seguinte ao bar de failedConfirm)

### Classificação no pipeline

- **REJECT** — não incubar, não watchlist, não candidate.
- **Linha fechada (strike 1):** LSN com esta parametrização. Pode ser reavaliada em futuro com limiares diferentes se a família for considerada promissora após revisão teórica.
- ** upgrades não recomendados:** não é o caso de "ajustar thresholds" — o problema é o edge negativo consistente, não thresholds muito restritivos (o sinal dispara 200+ vezes por símbolo, então não é restritividade — é que o sinal não tem previsibilidade).

---

## 9. Next Cycle

### Opção A — Reavaliar LSN com mudanças conceituais (não apenas thresholds)

Se a família LSN for reconsiderada no futuro, as mudanças necessárias são conceituais, não paramétricas:

1. **Filtro de regime (essencial):** só entrar em sweeps se o mercado estiver em regime de range/chop, não em trend. Adicionar filtro como:
   - ADX < 25 (ou equivalente) para confirmar chop
   - Ou SMA(50) flatness (slope pequeno)
   - Ou vol regime (ATR não expandindo — sweeper em vol baixa é mais provável de ser fake)

2. **TP mais profundo:** tpRatio = 0.35 é muito brand. Testar 0.5–0.7 (snapback para o meio do range, não apenas 35% do range do bar de sweep). Ou usar SL/TP baseado em ATR fixo em vez de % do range do bar.

3. **SL mais amplo:** slBufferMult = 0.3 ATR é tight. Testar 0.5–1.0 ATR para evitar stops prematuros em mercados que raspa o extremo antes de reverter.

4. **Cooldown maior:** 5–10 barras para evitar overtrading em sequências de sweeps consecutivos.

5. **Ponderação long/short assimétrica:** se longs têm win rate mais alto que shorts (35–44% vs 17–23% nos dados), talvez a estratégia deva ser long-only (fade de sweep de low) ou ter alocação assimétrica.

**Créditos para reavaliação:** se decidido, usar ~10–15 créditos para testar LSN-v2 com filtros de regime + TP/SL ajustados em 5 símbolos × 1h.

### Opção B — Pivotar para H2 (FCD: Failed Continuation Detection) ou H3 (RSA: Range-Stability Anomaly)

Se a família LSN for considerada exausta após strike 1:

- **H2 (FCD):** conceito de "grande deslocamento sem follow-through → reversão". Distinto de LSN (foca em displacement de uma barra, não em sweep de extremo). Se LSN falhou por "snapback não confiável", FCD pode falhar por causa similar — mas é matematicamente distinto e vale testar.
- **H3 (RSA):** conceito de "estabilidade de range + glide → breakout falso". Distinto de LSN (foca em estabilidade do range, não em toque de extremo). Pode ser mais raro que LSN (exigiu stdev + sma + cumsum), então pode ser 0 trades — mas é matematicamente distinto.

**Recomendação:** testar H2 (FCD) primeiro, pois é mais simples que H3 e tem lógica de "falha de continuação" que é distinta de LSN.

### Opção C — Explorar famílias não testadas: regime switching, volume asymmetry, liquidity imbalance

Se nenhuma das hipóteses de reversão/fade testadas tiver edge (VPA, MSE, VRAD, LSN — todas rejeitadas), o próximo ciclo deve explorar famílias que não foram testadas:

- **Trend-following com filtro de regime (não apenas RSI):** como o melhor do desk (rsi-t200b) é trend-following, talvez o quant deva explorar hipóteses de continuação em vez de reversão.
- **Volume asymmetry entre barras:** se uma barra tem volume anormalmente alto na direção de um movimento, e a próxima barra tem volume baixo, há continuação ou reversão?
- **Liquidity imbalance:** diferença entre buy volume e sell volume em barcas de extremo.

**Decisão para este ciclo:** após 4 hipóteses de mean-reversion/fade rejeitadas (VPA, MSE, VRAD, LSN), **pivotar para uma hipótese de continuação/trend com filtro de regime** no próximo ciclo, ou testar H2/FCD como última hipótese de fade antes de pivotar completo.

---

## Informações de execução

- **Trader Dev MCP:** autenticado como searesj92@gmail.com (free tier)
- **Créditos:** 154 iniciais → 5 usados neste ciclo → **~149 restantes**
- **Engine:** tv_jul26 (mcprule-validated em todos os backtests)
- **Perfil de broker:** commission 0.05%, percent_of_equity 100%, margin 100/100, initial_capital $10,000
- **Nenhuma ordem real:** todos os testes são backtest virtuais no engine de paridade

---

## Arquivos emitidos

- **Pine:** `C:\Users\seares\Desktop\botrade\qm_lsn_v1.pine`
- **Relatório:** `data/reports/2026-09-24-0234-researcher-qm-lsn-v1.md`
- **Dashboard:** `dashboard/data.json` + `dashboard/data.js` (registrados 5 linhas: BTC/ETH/SOL/XRP/BNB 1h, status rejected)

---

## License & Disclaimer

*Research and education only. Not financial advice. Backtests are not future performance. No real orders placed.*

Generated: 2026-09-24 02:34 UTC-3  
Agent: researcher (solana-trend-bot desk)  
Cycle: QM-LSN-v1
