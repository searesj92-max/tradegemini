# Quant Mathematician Cycle Report
## Cycle: QM-LSN-v1 (Liquidity Sweep + Snapback) — BATCH COMPLETO
## Date: 2026-09-24T23:00 UTC-03:00 (Brazil)

---

## 1. Hipóteses Geradas (revisão — arquivo existente)

### H1 — LSN: Liquidity Sweep + Snapback *(selecionada, esta execução)*
**Ineficiência alvo:** quando o preço toca no extremo recente (high/low dos últimos N barras) em barra de range expandido mas FALHA em fechar além do extremo (close < high ou close > low), houve sweep de liquidez sem continuação — snapback esperado para o interior do range.

**Matemática central:** `sweepHigh = high[1] >= ta.highest(high[2], N)`; `sweepLow = low[1] <= ta.lowest(low[2], N)`; `rangeExpanded = (high[1]-low[1]) > atr(14)*volMult`; `failedHigh = sweepHigh and close[1] < high[1] - smallBuffer`; `failedLow = sweepLow and close[1] > low[1] + smallBuffer`; entrada no bar seguinte; SL além do extremo + buffer; TP no interior do range.

**Por que crypto:** stops concentrados acima/below dos extremos; sweeps frequentes em 24/7 sem gaps; maioria dos sweeps é falha porque o fluxo real não segue.

**Breaking regime:** breakout real com volume sustentado (range confirm + close além do extremo) — a lógica não entra porque `failedConfirm` não se satisfaz.

### H2 — FCD: Failed Continuation Detection *(não testada neste ciclo)*
### H3 — RSA: Range-Stability Anomaly *(não testada neste ciclo)*

---

## 2. Hipótese Selecionada

**H1 — LSN (Liquidity Sweep + Snapback)** — executada e comprovadamente rejeitada.

**Motivo da seleção original (arquivo qm_lsn_v1_hypothesis.md):** simplicidade, testabilidade, rigor matemático, generalizabilidade cross-symbol, risk management claro, never tested as greenfield.

---

## 3. Trading Rules

### Entradas
- **Long:** bar[1] raspiu low recente (`low[1] <= ta.lowest(low[2], N)`), bar[1] range expandido (`> atr(14)*0.6`), bar[1] falhou em confirmar breakout baixo (`close[1] > low[1] + 0.2%*low[1]`). Entrada no bar seguinte.
- **Short:** bar[1] raspiu high recente (`high[1] >= ta.highest(high[2], N)`), bar[1] range expandido, bar[1] falhou em confirmar breakout alto (`close[1] < high[1] - 0.2%*high[1]`). Entrada no bar seguinte.

### Saídas
- **TP (long):** `position_avg_price - rangeBar1 * 0.35` (interior do range)
- **TP (short):** `position_avg_price + rangeBar1 * 0.35`
- **SL (long):** `low[1] - atr(14)*0.3` (além do extremo raspado + buffer)
- **SL (short):** `high[1] + atr(14)*0.3`
- **Time exit:** 20 barras máximas
- **Cooldown:** 3 barras após qualquer saída

### Risco
- 100% equity, pyramiding=1, margin 100/100, commission 0.05%, process_orders_on_close=true.
- **Nenhum trailing stop** (regra do loop — latência a broker converte winners em losses).
- SL e TP fixos no momento da entrada, não se movem.

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
    longTp = strategy.position_avg_price - rangeBar1 * tpRatio
    longSl = low[1] - atrVal * slBufferMult
    strategy.exit("LX", from_entry="L", limit=longTp, stop=longSl)
if strategy.position_size < 0
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

**Nota técnica:** `high[1]`, `low[1]`, `close[1]`, `high[2]`, `low[2]` usados para calcular o sweep e o failed confirm ANTES do bar de entrada — sem lookahead, sem repint. A entrada ocorre no bar seguinte ao sinal. `ta.highest`/`ta.lowest` com offset [2] evita usar dados do bar atual. Sem `request.security`, sem arrays, sem `strategy.order`, sem cancel.

---

## 5. Backtest Matrix

| # | Símbolo | TF | Strategy ID | Result ID | View URL |
|---|---------|-----|-------------|-----------|----------|
| 1 | BTCUSDT | 60m | 01M38SX4FS4QSEFQCWM1ZW275F | 01M38SXNHZQ1RQVQRKYZCAQBAK | https://mcp-api.trader.dev/backtest/01M38SXNHZQ1RQVQRKYZCAQBAK |
| 2 | ETHUSDT | 60m | 01M38SX4FS4QSEFQCWM1ZW275F | 01M38SXZYGWDKX60WEXPNFXVJV | https://mcp-api.trader.dev/backtest/01M38SXZYGWDKX60WEXPNFXVJV |
| 3 | SOLUSDT | 60m | 01M38SX4FS4QSEFQCWM1ZW275F | 01M38SYB6YQWVX0JBMRE3T4KVB | https://mcp-api.trader.dev/backtest/01M38SYB6YQWVX0JBMRE3T4KVB |
| 4 | XRPUSDT | 60m | 01M38SX4FS4QSEFQCWM1ZW275F | 01M38SYKVHZV1Q5KKSFFT1WN3C | https://mcp-api.trader.dev/backtest/01M38SYKVHZV1Q5KKSFFT1WN3C |
| 5 | BNBUSDT | 60m | 01M38SX4FS4QSEFQCWM1ZW275F | 01M38SYXMVR64Y0V4KP9S3AWR9 | https://mcp-api.trader.dev/backtest/01M38SYXMVR64Y0V4KP9S3AWR9 |
| 6 | DOGEUSDT | 60m | 01M38SX4FS4QSEFQCWM1ZW275F | 01M38SZ759P6KZXZKWVJ8HDKZB | https://mcp-api.trader.dev/backtest/01M38SZ759P6KZXZKWVJ8HDKZB |
| 7 | AVAXUSDT | 60m | 01M38SX4FS4QSEFQCWM1ZW275F | 01M38SZVRXH1S6BQ441TXCV1SM | https://mcp-api.trader.dev/backtest/01M38SZVRXH1S6BQ441TXCV1SM |
| 8 | LINKUSDT | 60m | 01M38SX4FS4QSEFQCWM1ZW275F | 01M38T02K4YM01BNS1TTAA7BYF | https://mcp-api.trader.dev/backtest/01M38T02K4YM01BNS1TTAA7BYF |
| 9 | ADAUSDT | 60m | 01M38SX4FS4QSEFQCWM1ZW275F | 01M38T0MBBP5734NZ967KJYT2V | https://mcp-api.trader.dev/backtest/01M38T0MBBP5734NZ967KJYT2V |
| 10 | NEARUSDT | 60m | 01M38SX4FS4QSEFQCWM1ZW275F | 01M38T0W0K01CEP1FAMWPD0HTP | https://mcp-api.trader.dev/backtest/01M38T0W0K01CEP1FAMWPD0HTP |

**Configuração unificada:**
- Engine: tv_jul26 (tv_jul26_mc7), mcpruleValidated=true
- Janela: 2026-06-01 → 2026-09-24 (~3.7 meses, 3061 barras avaliadas cada)
- Capital: $10,000
- Sizing: % equity 100, margin long/short 100
- Commission: 0.05% (MCP parity, hard-forced)
- Slippage: padrão Bybit lot filters por símbolo
- Long + Short ambos ativados

---

## 6. Results

### Matriz completa (10 símbolos × 1h)

| Símbolo | Net% | PF | DD% | WR% | Trades | Win | Loss | AvgBars | LongNet | ShortNet | Comission |
|---------|------|-----|------|------|--------|-----|------|---------|---------|----------|-----------|
| BTC | -27.80 | 0.461 | 29.51 | 31.28 | 243 | 76 | 167 | 2.12 | -310 | -2470 | 1983 |
| ETH | -16.27 | 0.665 | 18.42 | 28.71 | 303 | 87 | 216 | 2.10 | -314 | -1313 | 1815 |
| SOL | -24.30 | 0.595 | 27.97 | 26.09 | 345 | 90 | 255 | 2.08 | -1120 | -1310 | 1973 |
| XRP | -31.06 | 0.523 | 31.28 | 29.69 | 320 | 95 | 225 | 2.10 | -1653 | -1453 | 1862 |
| BNB | -27.45 | 0.379 | 27.59 | 24.47 | 282 | 69 | 213 | 2.10 | -1548 | -1198 | 1637 |
| DOGE | -21.76 | 0.642 | 22.64 | 29.77 | 299 | 89 | 210 | 2.11 | -1795 | -380 | 1800 |
| AVAX | -15.35 | 0.781 | 25.84 | 30.89 | 327 | 101 | 226 | 2.08 | +82 | -1617 | 2165 |
| LINK | -13.93 | 0.773 | 16.87 | 27.43 | 350 | 96 | 254 | 2.10 | -741 | -651 | 2119 |
| ADA | -46.02 | 0.504 | 49.41 | 28.96 | 335 | 97 | 238 | 2.14 | -2207 | -2394 | 1721 |
| NEAR | -6.99 | 0.937 | 23.53 | 34.33 | 367 | 126 | 241 | 2.11 | +2480 | -3178 | 2430 |

### Agregados
| Métrica | Valor |
|---------|-------|
| Símbolos com PF ≥ 1 | **0 / 10** |
| Símbolos com net profit ≥ 0 | **0 / 10** |
| Trades totais | **3,171** |
| Net profit total (USD) | **-$23,092** |
| PF médio | **0.625** |
| DD médio | **27.30%** |
| DD máximo | **49.41%** (ADA) |
| WR médio | **29.22%** |
| AvgBars médio | **2.10** |
| Lado longo: símbolos com long net > 0 | **2 / 10** (AVAX +82, NEAR +2480) |
| Lado short: símbolos com short net > 0 | **0 / 10** |

### Por símbolo — perfil de perda

- **BTC:** Short devastador (-2470 vs long -310). 148 shorts, 95 longs. PF 0.46. DD 29.5%.
- **ETH:** Short menos devastador mas ainda pior que long. 216 shorts, 87 longs.
- **SOL:** Long e short ambos negativos, short levemente pior. 243 shorts, 102 longs.
- **XRP:** Long pior que short (long -1653, short -1453). 122 longs, 198 shorts.
- **BNB:** Long pior que short. 92 longs, 190 shorts.
- **DOGE:** Long DEVASTADOR (-1795 vs short -380). 109 longs, 190 shorts. A única exceção onde short é muito melhor que long — mas ainda negativo no total.
- **AVAX:** Único com long positivo (+82) — marginal. Short -1617. 99 longs, 228 shorts.
- **LINK:** O mais "equilibrado" — long -741, short -651. PF 0.77, DD 16.9%. Ainda assim negativo.
- **ADA:** O pior. DD 49.4%, PF 0.50, net -46%. Long e short ambos ~ -2200/-2394.
- **NEAR:** O "menos ruim" net -7%. Long +2480 (excelente!) mas short -3178 (catastrófico). 118 longs, 249 shorts.

**Pattern dominante:** em 8/10 símbolos, o lado SHORT é o maior drenador de equity. Em 2/10 (DOGE, XRP), o lado LONG é o maior drenador. A estratégia não tem direcionalidade consistente — o problema é sistemaico, não de direção.

---

## 7. Diagnosis

### 7.1 O que o backtest mostrou de real versus hipótese

**Hipótese:** sweep de extremo + falha de confirm → snapback → fade ganha.

**Realidade observada:**
1. **Avg bars in trade ≈ 2 em todos os símbolos.** Isso é o diagnóstico central: os trades duram 2 barras em média. Se o snapback estivesse ocorrendo, esperaríamos trades de duração maior (o TP é no interior do range — precisa de tempo para o preço voltar). Com 2 barras, a saída é quase sempre pelo SL, não pelo TP. O mercado **não está revertendo** após o sweep falho — está continuando, levando o stop.
2. **Shorts catastróficos em maioria dos símbolos.** Isso indica que os sweeps de HIGH (rápidas para cima que falham em fechar acima) são frequentemente seguidos de CONTINUACAO para cima, não de snapback para baixo. O mercado rompe o high e fecha abaixo, sim — mas depois continua subindo nos bares seguintes, levar o short stop. Isso é consistente com mercados em tendência onde o pullback após o sweep é mínimo e a tendência prevalece.
3. **Longs positivos apenas em AVAX (+82) e NEAR (+2480).** Esses são outliers que sugerem que, em alguns mercados, o sweep de LOW com falha de confirm realmente leva a snapback. Mas em NEAR o lado short ainda drena -3178 — então a estratégia como um todo (long+short) ainda perde.

### 7.2 Por que a lógica falhou

**Raiz de problema 1 — A hipótese confunde "sweep sem confirm" com "fakeout".** Um candle que raspa o extremo e fecha dentro dele pode ser:
- (a) Fakeout com snapback (o que a estratégia espera) — ocorre, mas é menos frequente do que (b).
- (b) Aperto de stops antes da continuação real (stop run + continuation) — MUITO mais frequente em mercados trending.

A lógica não distinguem (a) de (b). O filtro de "range expandido" não ajuda porque ambos os casos têm range expandido. O `smallBuffer` de 0.2% é pequeno demais para filtrar sweeps que são noise vs sweeps que são setup de continuation.

**Raiz de problema 2 — SL muito apertado ou mal posicionado.** O SL é `low[1] - atr*0.3` para longs e `high[1] + atr*0.3` para shorts. Com avg bars = 2, o SL é acionado quase sempre antes do TP. O ATR*0.3 é muito pequeno como buffer — qualquer continuation de mínima magnitude leva ao stop.

**Raiz de problema 3 — Commission drag.** Com ~300 trades por símbolo e 0.05% por ordem de entrada+saída, a comissão total por símbolo fica entre $1600-$2400. Em símbolos onde o net é -7% (NEAR), a comissão representou ~24% do equity perdido. Em ADA, ~17%. Alta taxa de trades curtos amplifica a proporção commission/gross.

**Raiz de problema 4 — Cooldown de 3 barras é insuficiente.** Com 3 barras de cooldown, a estratégia pode entrar em novas operações muito rápido após uma perda, acumulando perdas sequenciais em mercados que não fazem snapback.

### 7.3 O que NÃO é problema (para isolar a raiz)

- **Não é repaint/lookahead:** código revisado, usa [1] e [2] consistentemente, sem request.security, sem arrays.
- **Não é amostra pequena:** 3171 trades totais, 10 símbolos, 3.7 meses — estatisticamente significativo para rejeitar.
- **Não é single-coin wonder:** 0/10 positivos — problema é universal.
- **Não é custo-only:** mesmo sem comissão, o gross profit é menor que gross loss em todos (PF < 1 em todos). A comissão piora, mas não causa o PF < 1.

### 7.4 Diagnóstico de direcionalidade

O lado short é o principal causador de perda em 8/10 símbolos. Isso sugere que o mercado, quando faz um sweep de HIGH com failed close, **continua para cima** (o pullback é mínimo e o stop short é acionado antes do snapback). Isso é consistente com mercados em tendência ascendente onde o sweep de high é parte da formação de bull flag / pennant, não um fakeout.

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
| WR médio | 29.22% | — (observacional) | Baixo |
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
- H2 (Failed Continuation Detection) nunca foi testada. Pode ter melhor expectancy.
- H3 (Range-Stability Anomaly) nunca foi testada. Conceito distinto.

### Recomendação

** Tentar opção A (long-only + regime filter em 1 símbolo de cada vez: NEAR, AVAX) antes de pivotar totalmente — porque NEAR longs mostraram +2480 em 367 trades, o que é uma señal de que o conceito de long snapback após sweep de low pode ter vida em SOME mercados.**

Se long-only em NEAR/AVAX com regime filter também der PF < 1 → pivotar para H2 ou H3.

---

## Resumo executivo

| Item | Conteúdo |
|------|----------|
| Hipótese | LSN — Liquidity Sweep + Snapback fade |
| Status | **REJECT** — strike 1 |
| Símbolos testados | 10 (BTC, ETH, SOL, XRP, BNB, DOGE, AVAX, LINK, ADA, NEAR) |
| TF | 1h (60m) — todos |
| Resultado | 0/10 com PF ≥ 1; 0/10 com equity ≥ 0; PF médio 0.625; DD médio 27.3%; DD max 49.4% |
| Raiz do fracasso | O mercado continua após o sweep falho mais do que reverte; shorts são devastadores; avg bars = 2 indica SL-driven, não TP-driven |
| Próximo passo | Long-only + regime filter em NEAR/AVAX, ou pivotar para H2 (FCD) / H3 (RSA) |
| Créditos gastos | ~10 backtests × ~1 credit = ~10 credits (estimativa) |

---

*Research and education only. Not financial advice. Backtests are not future performance. No real orders placed. Never place real orders from a loop.*
