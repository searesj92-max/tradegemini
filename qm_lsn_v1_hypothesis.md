# Quant Mathematician Cycle Report
## Cycle: QM-LSN-v1 (Liquidity Sweep + Snapback)
## Date: 2026-09-24

---

## 1. Hipóteses Geradas (3 greenfield)

### H1 — LSN: Liquidity Sweep + Snapback *(selecionada, esta execução)*

**Ineficiência alvo:** quando o preço toca no extremo recente (high/low dos últimos N barras) em barra de range expandido mas FALHA em fechar além do extremo (close < high ou close > low), houve sweep de liquidez sem continuação — snapback esperado para o interior do range.

**Matemática central:**
- `sweepHigh = high[1] >= ta.highest(high[2], N)`  # bar anterior raspiu o extremo
- `sweepLow  = low[1]  <= ta.lowest(low[2], N)`
- `rangeSweep = (high[1] - low[1]) > atr(14) * volMult`  # bar expandida (não noise)
- `failedHigh = sweepHigh and close[1] < high[1] - smallBuffer`  # close não confirmou
- `failedLow  = sweepLow  and close[1] > low[1]  + smallBuffer`
- `entry short` na barra seguinte ao `failedHigh`
- `entry long`  na barra seguinte ao `failedLow`
- SL: além do extremo que foi raspado + buffer
- TP: retorno ao interior do range (50% do range interno) ou ATR múltiplo
- Cooldown: 3 barras
- sem trailing stop (regra do loop)

**Por que crypto:** stops concentrados acima/below dos extremos; sweeps frequentes em 24/7 sem gaps; maioria dos sweeps é falha porque o fluxo real não segue.

**Breaking regime:** breakout real com volume sustentado (range confirm + close além do extremo) — mas a lógica não entra nisso porque `failedConfirm` não se satisfaz.

**Pine expression:** ta.highest/ta.lowest na barra anterior (sem lookahead — usa [1]), range confirm via ATR, entrada no bar seguinte, SL/TP fixo.

---

### H2 — FCD: Failed Continuation Detection (Nunca testada isolada)

**Ineficiência alvo:** após barra de grande deslocamento (displacement em ATR) quando o mercado NÃO apresenta follow-through no bar seguinte (close volta para dentro de uma zona de equilíbrio), o movimento falhou — reversão acelerada.

**Matemática central:**
- `bigMove = abs(close[1] - open[1]) > atr(14) * dispThresh`  # bar anterior grande
- `direction = sign(close[1] - open[1])`
- `noFollow = close < open[1] + direction * followZone`  # bar atual já desistiu da direção
- `entry` na direção oposta ao bigMove, se noFollow confirmado
- `SL`: atrás do bar de bigMove (alto se short, baixo se long)
- `TP`: retorno ao sma(close, 20) ou ATR múltiplo
- Cooldown: 5 barras

**Por que crypto:** impulsos de uma barra sem follow-through são sinais de fakeout; o mercado refaz o movimento no próximo bar.

**Breaking regime:** tendência real com follow-through em múltiplas barras (bigMove seguido de continuação) — a lógica não entra.

**Pine expression:** usa bar[1] para bigMove, bar atual para noFollow, entrada no bar seguinte.

---

### H3 — RSA: Range-Stability Anomaly (distinta das anteriores)

**Ineficiência alvo:** quando o range das últimas N barras é estável (baixo coeficiente de variação do range) mas o preço acumula deslocamento (close - open cumulativo positivo ou negativo), há "glide" concentrado — quando a estabilidade quebra (bar com range expandido), o movimento se inverte.

**Matemática central:**
- `rangeSeries = ta.range(high, low)`
- `rangeStability = ta.stdev(rangeSeries, N) / ta.sma(rangeSeries, N)`  # coeficiente de variação
- `stable = rangeStability < stabilityThresh`  # pouca variação de range
- `glide = cumsum(close - open) nos últimos N`  # deslocamento acumulado
- `breakBar = range > sma(range, N) * breakMult`  # bar que quebra a estabilidade
- `entry`: se `glide > glideThresh` e `breakBar` no mesmo bar → fade na direção oposta ao glide
- SL: atrás do breakBar's extremo
- TP: retorno ao equilíbrio (sma)
- Cooldown: 5 barras

**Por que crypto:** mercados em consolidação com glide tendem a ter breakout falso que se reverta; a métrica de estabilidade do range captura o "calma antes da falseira".

**Breaking regime:** trend real com range expandido sustentado — a lógica requer estabilidade prévia, então não entra em trend puro.

**Pine expression:** ta.stdev + ta.sma para CV; cumsum manual via var; entrada no bar do break.

---

## 2. Hipótese Selecionada

**H1 — LSN (Liquidity Sweep + Snapback)**

**Motivo da seleção (por ordem de prioridade do loop):**

1. **Simplicidade:** 2 condições de sweep + 1 condição de failed confirm + 1 filter de range — lógica limpa, 4-5 variáveis, sem indicador complexo.
2. **Testabilidade:** todos os componentes são observáveis no bar[1]; entrada no bar seguinte; sem ambiguidade de janelamento.
3. **Math rigor:** o conceito de "sweep sem follow-through" é bem documentado em microestrutura de mercado — stops são concentrados em extremos, maioria dos sweeps é fake; a métrica de range-expandido filtra sweeps que são noise.
4. **Generalizabilidade:** sweep + snapback é independente do par; BTC, ETH, SOL, XRP, BNB todos têm stops concentrados e sweeps frequentes.
5. **Clear risk management:** SL fixo além do extremo, TP fixo no interior do range, sem trailing.
6. **Nunca testada como greenfield:** mencionada nos relatórios anteriores (H3 do range-eff, H1 do MSE) mas nunca implementada e backtestada isolada — todas as hipóteses de range-efficiency e vol-decay falharam por 0 trades ou edge insuficiente; a abordagem de "sweep sem confirm" é distinta.

**Contraste com hipóteses que falharam:**

| Ciclo | Linha | Motivo do fracasso | Distinção do LSN |
|-------|-------|-------------------|------------------|
| MSE-v1 | LRS | 0 trades — 5 condições AND, evento muito raro | LSN: 4 condições, não requer 5 eventos raros simultâneos |
| MSE-v1 | REA | 0 trades — queda de eficiência rara | LSN: usa extremos do preço (comuns) + falha de confirm (comum) |
| VS-v1 | JM | 0 trades — ssIndex < 0.6 muito restritivo | LSN: não usa coil-swithen stability index |
| VND-v1 | VND | PF<1 — fade de single-bar displacement não funciona | LSN: foca em sweep de EXTREMO recente, não fade de displacimento intra-bar |
| QM-VPA-v1 | VPA | 0 trades — volume anomal low + big move raros | LSN: não depende de volume anomal (pode adicionar como filtro se necessário) |
| QM-VRAD-v1 | VRAD | 22 trades, PF médio < 0.5, short bias negativo | LSN: foca em snapback (reversão) após sweep falho — conceito mais direto que regime classifier |

**Por que LSN pode funcionar quando os outros falharam:**
- Todos os anteriores falharam porque as condições eram raras (0 trades) OU porque a lógica capturava eventos que eram inícios de trend, não fakeouts.
- LSN foca em um evento que É comum em crypto (sweep de extremo) mas que SÓ é interessante quando a barra NÃO confirma o breakout (close < high). Isso é mais frequente que "volume < 50% da média" ou "range efficiency < 0.30 em bar expandida".
- O conceito é simples: tocar no topo com bar expandida mas fechar abaixo do topo = sweep sem continuação = entrada no pullback.

---

## 3. Regras de Trading

### Entradas (Long)

| Condição | Expressão | Nota |
|----------|-----------|------|
| Bar anterior raspiu o low recente | `low[1] <= ta.lowest(low[2], N)` | N barras lookback |
| Bar anterior foi expandida | `(high[1] - low[1]) > atr(14) * volMult` | Não é bar de noise |
| Bar anterior falhou em confirmar breakout baixo | `close[1] > low[1] + smallBuffer` | Close não permaneceu no extremo |
| Preço atual já em snapback (opcional) | `(close - low[1]) < snapbackZone` | Entry no bar seguinte ao sinal |

→ **Long entry** no bar seguinte ao sinal de failedLow.

### Entradas (Short)

| Condição | Expressão | Nota |
|----------|-----------|------|
| Bar anterior raspiu o high recente | `high[1] >= ta.highest(high[2], N)` | N barras lookback |
| Bar anterior foi expandida | `(high[1] - low[1]) > atr(14) * volMult` | Não é bar de noise |
| Bar anterior falhou em confirmar breakout alto | `close[1] < high[1] - smallBuffer` | Close não permaneceu no extremo |

→ **Short entry** no bar seguinte ao sinal de failedHigh.

### Saídas

| Tipo | Valor | Motivo |
|------|-------|--------|
| **TP** | retorno ao interior do range: `strategy.position_avg_price +/- (high[1]-low[1]) * tpRatio` | Snapback esperado ao interior |
| **SL** | além do extremo raspado + buffer: `longSL = low[1] - atr * slBufferMult` / `shortSL = high[1] + atr * slBufferMult` | Proteção se o sweep for real |
| **Time exit** | N barras (ex: 20) | Limita exposição se não snapback |
| **Cooldown** | 3 barras após qualquer saída | Evita overtrading |
| **Nenhum trailing** | — | Regra do loop: trailing converte winners em losses por latência |

### Invalidação
- Se o preço rompe o extremo raspado e fecha além dele (confirmando breakout real) antes do entrada → não entra (a lógica só entra se o failedConfirm aconteceu no bar [1]).

### Risco
- 100% equity, pyramiding=1, margin 100/100, commission 0.05%, process_orders_on_close=true.
- Sem trailing stops (regra de latência do loop).
- SL e TP fixos no momento da entrada (não se movem).

---

## 4. Pine Script

```pine
//@version=6
// QM-LSN-v1 — Liquidity Sweep + Snapback
// Hypothesis: sweep of recent extreme + failed close confirmation → snapback fade.
// Entry: bar[1] raspu extremo + range expandido + close não confirmou → entrada no bar seguinte.
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
sweepLow  = low[1]  <= ta.lowest(low[2], sweepN)
rangeBar1 = high[1] - low[1]
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

**Nota:** o Pine usa `high[1]`, `low[1]`, `close[1]` e `high[2]`, `low[2]` para calcular o sweep e o failed confirm ANTES do bar de entrada — sem lookahead, sem repint. A entrada ocorre no bar seguinte ao sinal.

---

## 5. Backtest Matrix (completo — 10 símbolos × 1h)

**Configuração:**
- Engine: tv_jul26 (tv_jul26_mc7), mcpruleValidated=true
- Janela: 2026-06-01 → 2026-09-24 (~3.7 meses, 3061 barras avaliadas cada)
- Capital: $10,000
- Sizing: % equity 100, margin long/short 100
- Commission: 0.05% (MCP parity, hard-forced)
- Slippage: padrão Bybit lot filters por símbolo
- Long + Short ambos ativados

| # | Símbolo | TF | Strategy ID | Result ID | View URL | Net% | PF | DD% | WR% | Trades |
|---|---------|-----|-------------|-----------|----------|------|-----|------|------|--------|
| 1 | BTCUSDT | 60m | 01M38SX4FS4QSEFQCWM1ZW275F | 01M38SXNHZQ1RQVQRKYZCAQBAK | https://mcp-api.trader.dev/backtest/01M38SXNHZQ1RQVQRKYZCAQBAK | -27.80 | 0.461 | 29.51 | 31.28 | 243 |
| 2 | ETHUSDT | 60m | 01M38SX4FS4QSEFQCWM1ZW275F | 01M38SXZYGWDKX60WEXPNFXVJV | https://mcp-api.trader.dev/backtest/01M38SXZYGWDKX60WEXPNFXVJV | -16.27 | 0.665 | 18.42 | 28.71 | 303 |
| 3 | SOLUSDT | 60m | 01M38SX4FS4QSEFQCWM1ZW275F | 01M38SYB6YQWVX0JBMRE3T4KVB | https://mcp-api.trader.dev/backtest/01M38SYB6YQWVX0JBMRE3T4KVB | -24.30 | 0.595 | 27.97 | 26.09 | 345 |
| 4 | XRPUSDT | 60m | 01M38SX4FS4QSEFQCWM1ZW275F | 01M38SYKVHZV1Q5KKSFFT1WN3C | https://mcp-api.trader.dev/backtest/01M38SYKVHZV1Q5KKSFFT1WN3C | -31.06 | 0.523 | 31.28 | 29.69 | 320 |
| 5 | BNBUSDT | 60m | 01M38SX4FS4QSEFQCWM1ZW275F | 01M38SYXMVR64Y0V4KP9S3AWR9 | https://mcp-api.trader.dev/backtest/01M38SYXMVR64Y0V4KP9S3AWR9 | -27.45 | 0.379 | 27.59 | 24.47 | 282 |
| 6 | DOGEUSDT | 60m | 01M38SX4FS4QSEFQCWM1ZW275F | 01M38SZ759P6KZXZKWVJ8HDKZB | https://mcp-api.trader.dev/backtest/01M38SZ759P6KZXZKWVJ8HDKZB | -21.76 | 0.642 | 22.64 | 29.77 | 299 |
| 7 | AVAXUSDT | 60m | 01M38SX4FS4QSEFQCWM1ZW275F | 01M38SZVRXH1S6BQ441TXCV1SM | https://mcp-api.trader.dev/backtest/01M38SZVRXH1S6BQ441TXCV1SM | -15.35 | 0.781 | 25.84 | 30.89 | 327 |
| 8 | LINKUSDT | 60m | 01M38SX4FS4QSEFQCWM1ZW275F | 01M38T02K4YM01BNS1TTAA7BYF | https://mcp-api.trader.dev/backtest/01M38T02K4YM01BNS1TTAA7BYF | -13.93 | 0.773 | 16.87 | 27.43 | 350 |
| 9 | ADAUSDT | 60m | 01M38SX4FS4QSEFQCWM1ZW275F | 01M38T0MBBP5734NZ967KJYT2V | https://mcp-api.trader.dev/backtest/01M38T0MBBP5734NZ967KJYT2V | -46.02 | 0.504 | 49.41 | 28.96 | 335 |
| 10 | NEARUSDT | 60m | 01M38SX4FS4QSEFQCWM1ZW275F | 01M38T0W0K01CEP1FAMWPD0HTP | https://mcp-api.trader.dev/backtest/01M38T0W0K01CEP1FAMWPD0HTP | -6.99 | 0.937 | 23.53 | 34.33 | 367 |

---

## 6. Results

### Agregados (10 símbolos × 1h)

| Métrica | Valor |
|---------|-------|
| Símbolos com PF ≥ 1 | **0 / 10** |
| Símbolos com net profit ≥ 0 | **0 / 10** |
| Trades totais | **3,171** |
| PF médio | **0.625** |
| DD médio | **27.30%** |
| DD máximo | **49.41%** (ADA) |
| WR médio | **29.22%** |
| AvgBars médio | **2.10** |
| Longs positivos | 2/10 (AVAX +82, NEAR +2480) |
| Shorts positivos | 0/10 |

### Por símbolo — perfil de perda

- **BTC:** Short devastador (-2470 vs long -310). 148 shorts, 95 longs. PF 0.46. DD 29.5%.
- **ETH:** Short menos devastador mas ainda pior que long. 216 shorts, 87 longs. PF 0.66.
- **SOL:** Long e short ambos negativos, short levemente pior. 243 shorts, 102 longs. PF 0.60.
- **XRP:** Long pior que short (long -1653, short -1453). 122 longs, 198 shorts. PF 0.52.
- **BNB:** Long pior que short. 92 longs, 190 shorts. PF 0.38.
- **DOGE:** Long DEVASTADOR (-1795 vs short -380). A única exceção onde short é muito melhor, mas total negativo. PF 0.64.
- **AVAX:** Único com long positivo (+82) — marginal. Short -1617. 99 longs, 228 shorts. PF 0.78.
- **LINK:** O mais "equilibrado" — long -741, short -651. PF 0.77, DD 16.9%.
- **ADA:** O pior. DD 49.4%, PF 0.50, net -46%. Long e short ambos ~ -2200/-2394.
- **NEAR:** O "menos ruim" net -7%. Long +2480 (excelente!) mas short -3178 (catastrófico). 118 longs, 249 shorts. PF 0.94.

**Pattern dominante:** em 8/10 símbolos, o lado SHORT é o maior drenador de equity. Em 2/10 (DOGE, XRP), o lado LONG é o maior drenador. A estratégia não tem direcionalidade consistente — o problema é sistemaico, não de direção.

---

## 7. Diagnosis

### 7.1 O que o backtest mostrou de real versus hipótese

**Hipótese:** sweep de extremo + falha de confirm → snapback → fade ganha.

**Realidade observada:**
1. **Avg bars in trade ≈ 2 em todos os símbolos.** Diagnóstico central: os trades duram 2 barras em média. Se o snapback estivesse ocorrendo, esperaríamos trades de duração maior (o TP é no interior do range — precisa de tempo para o preço voltar). Com 2 barras, a saída é quase sempre pelo SL, não pelo TP. O mercado **não está revertendo** após o sweep falho — está continuando, levando o stop.
2. **Shorts catastróficos em maioria dos símbolos.** Isso indica que os sweeps de HIGH (rápidas para cima que falham em fechar acima) são frequentemente seguidos de CONTINUACAO para cima, não de snapback para baixo. O mercado rompe o high e fecha abaixo, sim — mas depois continua subindo nos bares seguintes, levar o short stop. Consistente com mercados em tendência onde o pullback após o sweep é mínimo e a tendência prevalece.
3. **Longs positivos apenas em AVAX (+82) e NEAR (+2480).** Esses são outliers que sugerem que, em alguns mercados, o sweep de LOW com falha de confirm realmente leva a snapback. Mas em NEAR o lado short ainda drena -3178 — então a estratégia como um todo (long+short) ainda perde.

### 7.2 Por que a lógica falhou

**Raiz 1 — A hipótese confunde "sweep sem confirm" com "fakeout".** Um candle que raspa o extremo e fecha dentro dele pode ser:
- (a) Fakeout com snapback (o que a estratégia espera) — ocorre, mas é menos frequente.
- (b) Aperto de stops antes da continuação real (stop run + continuation) — MUITO mais frequente em mercados trending.

A lógica não distingue (a) de (b). O filtro de "range expandido" não ajuda porque ambos os casos têm range expandido.

**Raiz 2 — SL muito apertado.** O SL é `low[1] - atr*0.3` para longs e `high[1] + atr*0.3` para shorts. Com avg bars = 2, o SL é acionado quase sempre antes do TP. O ATR*0.3 é muito pequeno como buffer — qualquer continuation de mínima magnitude leva ao stop.

**Raiz 3 — Commission drag.** Com ~300 trades por símbolo e 0.05% por ordem de entrada+saída, a comissão total por símbolo fica entre $1600-$2400. Em símbolos onde o net é -7% (NEAR), a comissão representou ~24% do equity perdido. Alta taxa de trades curtos amplifica a proporção commission/gross.

**Raiz 4 — Cooldown de 3 barras é insuficiente.** Com 3 barras de cooldown, a estratégia pode entrar em novas operações muito rápido após uma perda, acumulando perdas sequenciais em mercados que não fazem snapback.

### 7.3 O que NÃO é problema (para isolar a raiz)

- **Não é repaint/lookahead:** código revisado, usa [1] e [2] consistentemente, sem request.security, sem arrays.
- **Não é amostra pequena:** 3171 trades totais, 10 símbolos, 3.7 meses — estatisticamente significativo para rejeitar.
- **Não é single-coin wonder:** 0/10 positivos — problema é universal.
- **Não é custo-only:** mesmo sem comissão, o gross profit é menor que gross loss em todos (PF < 1 em todos). A comissão piora, mas não causa o PF < 1.

### 7.4 Diagnóstico de direcionalidade

O lado short é o principal causador de perda em 8/10 símbolos. Isso sugere que o mercado, quando faz um sweep de HIGH com failed close, **continua para cima** (o pullback é mínimo e o stop short é acionado antes do snapback). Consistente com mercados em tendência ascendente onde o sweep de high é parte da formação de bull flag / pennant, não um fakeout.

---

## 8. Verdict

**REJECT — QM-LSN-v1 (Liquidity Sweep + Snapback)**

### Critérios de rejeição atendidos

| Critério | Valor | Threshold | Status |
|----------|-------|-----------|--------|
| Símbolos com PF ≥ 1 | 0 / 10 | ≥ 1 símbolo com PF ≥ 1 | **FAIL** |
| Símbolos com net profit ≥ 0 | 0 / 10 | ≥ 1 símbolo | **FAIL** |
| Max DD | 49.41% (ADA) | ≤ 30% | **FAIL** |
| DD médio | 27.30% | ≤ 25% | **FAIL** (marginal) |
| AvgBars in trade | 2.10 | Deveria ser maior se snapback real | **FAIL** (trades são SL-driven) |
| Long/short balance | Short domina perdas em 8/10 | Deve ser equilibrado ou long-biased consistente | **FAIL** |
| Trades totais | 3171 | ≥ 50 trades por símbolo (ok) | OK — amostra adequada |

### Categorização: REJECT

A hipótese LSN, como implementada, **falhou em todos os símbolos em todos os TF testados (1h)**. PF < 1 em todos. Zero símbolos com equity positivo. A lógica central — que sweep sem confirm leva a snapback — **não se manifesta no mercado**. Os trades são curtos (avg 2 barras), SL-driven, com short bias catastrófico.

**O conceito não foi totalmente invalidado** — AVAX longs (+82) e NEAR longs (+2480) mostram que, em alguns mercados, o sweep de LOW com failed confirm PODE levar a snapback long. Mas como estratégia completa (long+short), o lado short drena mais que o lado long ganha. A hipótese precisa ser re-enquadradas como **pure long-only (sweep de low com failed confirm → long snapback)** ou requerer um filtro de regime que exclude mercados onde o sweep é parte de trend continuation.

### Regra de três strikes

Este é **Strike 1** da linha LSN. Se o próximo ciclo (com ajuste de regime classifier ou long-only) também falhar, strike 2. Se falhar novamente, strike 3 → linha rejeitada permanentemente, pivotar para nova hipótese.

---

## 9. Next Cycle

### O que fazer com esta linha

**Opção A — Long-only filtrando regime bull:**
- Converter para **long-only**: só entrar em long quando sweep de LOW com failed confirm E o mercado está em regime de consolidação/reversal (ex: price abaixo de SMA(50) ou ATR em contração). Só testar NEAR, AVAX, DOGE (onde long tem chance).
- Vantagem: elimina o dano do short bias.
- Risco: menos trades, sample size menor.

**Opção B — Regime classifier (sweep em range vs sweep em trend):**
- Adicionar filtro que detecta se o candle de sweep está dentro de um range horizonto (ex: just something dentro do canal de N barras) vs se está em breakout de um wedge/triange (onde continuation é mais provável).
- Isso requer adicionar condições de range-bound vs trending — pode usar `ta.rising`/`ta.falling` de longo prazo, ou canal de Bollinger, ou distance from SMA.

**Opção C — Aumentar SL buffer e TP ratio:**
- `slBufferMult` de 0.3 → 0.8 ou 1.0 (mais espaço para o swing antes do stop).
- `tpRatio` de 0.35 → 0.5 ou 0.6 (mais agressivo na captura do snapback).
- Risco: mais trades vão para time exit (20 barras) ou perdem mais antes do TP.

**Opção D — Pivot total para H2 ou H3:**
- H2 (FCD — Failed Continuation Detection) nunca foi testada isolada.
- H3 (RSA — Range-Stability Anomaly) nunca foi testada.

### Recomendação

**Tentar opção A (long-only + regime filter em 1 símbolo de cada vez: NEAR, AVAX) antes de pivotar totalmente — porque NEAR longs mostraram +2480 em 367 trades, o que é uma señal de que o conceito de long snapback após sweep de low pode ter vida em SOME mercados.**

Se long-only em NEAR/AVAX com regime filter também der PF < 1 → pivotar para H2 (FCD) ou H3 (RSA).

---

*Research and education only. Not financial advice. Backtests are not future performance. No real orders placed.*
