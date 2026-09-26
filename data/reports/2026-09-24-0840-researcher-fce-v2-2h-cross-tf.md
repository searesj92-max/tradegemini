# Quant Mathematician Cycle Report — Cycle 05
## Data: 2026-09-24 08:40 UTC-3 · Agent: researcher · Engine: tv_jul26_mc7

---

## 1. Hipóteses Geradas (5 greenfield)

### H1 — FCE-2H: Cross-TF Generalização de Failed Continuation Exhaustion (SELECIONADA)

**Ineficiência alvo:** O padrão FCE (barra que estende o extremo seguida de barra que falha em extender + close convincente na direção oposta) é um fenômeno de microstructure de curto prazo. Ao transferir para 2h, a hipótese é que o mesmo mecanismo (exaustão de liquidity após extensão de range) persiste, mas com menos sinais e maior robustez por bar.

**Matemática central:** Identical ao FCE-v1, mas em 2h. Lookback=20, minDisp=0.3, slAtRMult=1.5, tpAtRMult=1.5, cooldown=3 (mantidos para isolar efeito de TF).

**Por que na crypto:** Liquidity exhaustion é um fenômeno multi-escala. Se o padrão é real, deve emergir em diferentes granularidades temporais.

**Breaking regime:** Trend monótono sem pullbacks; low-vol range sideways.

---

### H2 — FCE-4H: Generalização para 4h (janela mais longa)

**Ineficiência alvo:** Em 4h, cada sinal FCE representa 4 horas de formação — potencialmente mais significativo.

**Risco:** Janela de 1 month em 4h = ~180 barras — amostra muito pequena para significance estatística. Trade count pode ser < 10 por símbolo.

---

### H3 — FCE-WIDER: Lookback Ampliado (20→30) com Cooldown Reduzido (3→1)

**Ineficiência alvo:** Lookback de 20 barras pode estar muito curto para capturar extremos relevantes. Lookback 30 barras filtra mais ruído. Cooldown 1 permite mais trades.

**Risco:** Lookback maior pode reduzir drasticamente o número de sinais.

---

### H4 — FCE-ASYMP: SL/TP Assimétrico (SL 1.75×ATR, TP 1.25×ATR)

**Ineficiência alvo:** O FCE-v1 usou SL/TP simétrico. A lógica do padrão FCE é que a falha de continuation gera uma reversão imediata — TP deve ser alcançado rápido. SL mais largo protege contra falsos quebras; TP mais apertado captura reversão rápida.

**Risco:** TP muito apertado pode resultar em trades que "quase alcançam" o TP mas não fecham, e depois hit SL.

---

### H5 — FCE-VOLREGIME: Filtro de Regime de Volatilidade (ATR/ATR_SMA entre 0.7 e 1.5)

**Ineficiência alvo:** Adicionar filtro de volatilidade para evitar entrar em explosões de vol (onde o padrão é seguido de continuation real) e em low-vol (onde sinais são ruído).

**Risco:** Filtro pode suprimir muitos sinais em regimes onde o padrão ainda funciona.

---

## 2. Hipótese Selecionada

**H1 — FCE-2H: Cross-TF Generalização de Failed Continuation Exhaustion.**

**Motivo da seleção (ordem de prioridade do loop):**

1. **Robustez cross-TF é o gap crítico identificado pelo ciclo anterior.** O relatório FCE-v1 explicitamente recomendou "Opção A — Cross-TF expansion" como próximo passo.
2. **Greenfield puro dentro da família.** Não é fork de nenhuma estratégia do DB; não é re-packaging de indicador retail.
3. **Simplicidade:** mesma lógica, apenas mudança de TF. Isolamento de variável: se 2h performa diferente de 1h, sabemos que o efeito é dependente de escala temporal.
4. **Eficiência de créditos:** 3 backtests × 1 crédito = 3 créditos. Com 62 disponíveis, investimento modesto para validação crítica.
5. **Matematicamente bem fundamentado:** A hipótese de multi-escala para exhaustion patterns é coerente com a literatura de microstructure.

**Símbolos selecionados para 2h:**
- **BTCUSDT** — home pair, referência de robustez
- **ADAUSDT** — outlier positivo no ciclo anterior (PF 1.42), precisa de validação cross-TF
- **XRPUSDT** — performer moderado (PF 1.10), teste de consistência

---

## 3. Trading Rules (FCE-2H — identical logic to FCE-v1, TF changed)

### Entrada Long
- Barra anterior (t-1) fez novo extremo alto em janela de 20 barras: `high[1] > ta.highest(high, 20)[2]`
- Barra anterior teve corpo significativo: `|close[1]-open[1]| / atr[1] > 0.3`
- Barra atual (t-0) NÃO estende o extremo: `high <= ta.highest(high, 20)[1]`
- Barra atual fecha abaixo de abrir: `close < open` (conviction de reversão)
- Cooldown: 3 barras após saída antes de nova entrada long

### Entrada Short
- Barra anterior (t-1) fez novo extremo baixo: `low[1] < ta.lowest(low, 20)[2]`
- Barra anterior teve corpo significativo: `|close[1]-open[1]| / atr[1] > 0.3`
- Barra atual (t-0) NÃO estende o extremo: `low >= ta.lowest(low, 20)[1]`
- Barra atual fecha acima de abrir: `close > open`
- Cooldown: 3 barras após saída antes de nova entrada short

### Exits
- **SL Long:** `lowerExtPrior - 1.5×ATR`
- **TP Long:** `close + 1.5×ATR`
- **SL Short:** `upperExtPrior + 1.5×ATR`
- **TP Short:** `close - 1.5×ATR`
- Sem trailing (regra de latência)

### Filtros
- `process_orders_on_close=true` (sem lookahead)
- pyramiding=1
- Cooldown obrigatório
- Comission 0.05%, equity 100%, margin 100/100, slippage 2 ticks

---

## 4. Pine Script

Arquivo: `data/pines/QM-FCE-v2-2H.pine`

```pine
//@version=6
strategy("QM-FCE-v2-2H — Failed Continuation Exhaustion (2h cross-TF)", 
  overlay=true, pyramiding=1, process_orders_on_close=true,
  commission_type=strategy.commission.percent, commission_value=0.05,
  default_qty_type=strategy.percent_of_equity, default_qty_value=100,
  margin_long=100, margin_short=100, initial_capital=10000)

// ── Inputs ──────────────────────────────────────────────
lookback     = input.int(20, "Lookback for extremes")
minDisp      = input.float(0.3, "Min prior-bar displacement (ATR mult)")
slAtRMult    = input.float(1.5, "SL buffer in ATR multiples")
tpAtRMult    = input.float(1.5, "TP in ATR multiples")
cooldown     = input.int(3, "Cooldown bars after exit")

// ── Indicators ──────────────────────────────────────────
atr = ta.atr(14)

// Extremes EXCLUDING current bar
upperExtPrior = ta.highest(high, lookback)[1]
lowerExtPrior = ta.lowest(low, lookback)[1]

// Prior bar extended the range
priorHighExt = high[1] > ta.highest(high, lookback)[2]
priorLowExt  = low[1]  < ta.lowest(low, lookback)[2]

// Prior bar body
priorBody = math.abs(close[1] - open[1])
priorDisp = priorBody / atr[1]

// ── Failed Continuation ────────────────────────────────
failHigh = priorHighExt and priorDisp > minDisp and high <= upperExtPrior and close < open
failLow  = priorLowExt  and priorDisp > minDisp and low  >= lowerExtPrior and close > open

// ── Cooldown ────────────────────────────────────────────
var int cdShort = 0
var int cdLong  = 0
var int prevClosed = 0

cdShort := cdShort > 0 ? cdShort - 1 : 0
cdLong  := cdLong > 0 ? cdLong  - 1 : 0

if strategy.closedtrades > prevClosed
    cdShort := cooldown
    cdLong  := cooldown
    prevClosed := strategy.closedtrades

// ── Entries ─────────────────────────────────────────────
if failHigh and cdShort == 0 and strategy.position_size == 0
    strategy.entry("S", strategy.short)

if failLow and cdLong == 0 and strategy.position_size == 0
    strategy.entry("L", strategy.long)

// ── Exits ───────────────────────────────────────────────
if strategy.position_size < 0
    slPrice = upperExtPrior + atr * slAtRMult
    tpPrice = close - atr * tpAtRMult
    strategy.exit("SX", from_entry="S", stop=slPrice, limit=tpPrice)

if strategy.position_size > 0
    slPrice = lowerExtPrior - atr * slAtRMult
    tpPrice = close + atr * tpAtRMult
    strategy.exit("LX", from_entry="L", stop=slPrice, limit=tpPrice)

// ── Plots ───────────────────────────────────────────────
plot(upperExtPrior, "upperExt", color.new(color.red, 50))
plot(lowerExtPrior, "lowerExt", color.new(color.green, 50))
```

Estratégias criadas no MCP:
- `QM-FCE-v2-2H-BTC` → ID `01M39NXRBE3TAV1P9CZKCEX2ZD` (BTCUSDT, 2h)
- `QM-FCE-v2-2H-ADA` → ID `01M39NYW0K9G7FJTSJXDEAF8N1` (ADAUSDT, 2h)
- `QM-FCE-v2-2H-XRP` → ID `01M39NZ98WVNX51TGPKJ5ZSKJC` (XRPUSDT, 2h)

---

## 5. Backtest Matrix

| # | Símbolo | TF | Strategy ID | Result ID | Trades | WR% | Net% | PF | DD% | Sharpe | Long/Short PF | View URL |
|---|---------|-----|------------|-----------|--------|-----|------|-----|------|--------|---------------|----------|
| 1 | BTCUSDT | 2h | `01M39NXRBE3TAV1P9CZKCEX2ZD` | `01M39NZW63FFNBGR1T4C6XT0B8` | 40 | 30.0 | **−7.51** | 0.65 | 10.84 | −1.40 | L +0.02 / S −0.77 | https://mcp-api.trader.dev/backtest/01M39NZW63FFNBGR1T4C6XT0B8 |
| 2 | ADAUSDT | 2h | `01M39NYW0K9G7FJTSJXDEAF8N1` | `01M39P08J8TKW02GXCWGBFA3RP` | 66 | 27.3 | **−14.02** | 0.79 | 30.22 | −0.94 | L +0.01 / S −1.43 | https://mcp-api.trader.dev/backtest/01M39P08J8TKW02GXCWGBFA3RP |
| 3 | XRPUSDT | 2h | `01M39NZ98WVNX51TGPKJ5ZSKJC` | `01M39P0GB0B6RPGC9TE03WBAD7` | 45 | 37.8 | **−13.57** | 0.64 | 21.81 | −1.38 | L −0.72 / S −0.63 | https://mcp-api.trader.dev/backtest/01M39P0GB0B6RPGC9TE03WBAD7 |

**Período:** 2026-08-25 → 2026-09-24 (~1 month, 2h, ~1374 bars avaliados)
**Capital:** $10,000
**Sizing:** 100% equity, margin 100/100
**Commission:** 0.05%
**Slippage:** 2 ticks (Bybit lot filters aplicados)

---

## 6. Results (Detalhados)

### 6.1 BTCUSDT 2h

| Métrica | Valor |
|---------|-------|
| Trades | 40 (10 long, 30 short) |
| Win Rate | 30.0% (12W / 28L) |
| Net Profit | **−7.51%** (−$750.62) |
| Profit Factor | 0.65 |
| Max Drawdown | 10.84% |
| Avg Win / Avg Loss | $115.83 / −$76.45 (ratio 1.52) |
| Avg Bars in Trade | 10.38 |
| Sharpe / Sortino | −1.40 / −0.72 |
| Commission Paid | $287.51 |
| Long Net / Short Net | +$22.27 / −$772.90 |
| Cascade Ratio | 1.33 (30 unique entries, 40 total trades) |

**Diagnóstico:** Short bias dominante (75% dos trades). Longs tiveram resultado quase break-even (+$22). Shorts foram destruidores (−$773). O padrão FCE em 2h em BTC parece gerar muitos sinais curtos que falham.

---

### 6.2 ADAUSDT 2h

| Métrica | Valor |
|---------|-------|
| Trades | 66 (13 long, 53 short) |
| Win Rate | 27.3% (18W / 48L) |
| Net Profit | **−14.02%** (−$1,401.71) |
| Profit Factor | 0.79 |
| Max Drawdown | 30.22% |
| Avg Win / Avg Loss | $300.72 / −$141.97 (ratio 2.12) |
| Avg Bars in Trade | 10.65 |
| Sharpe / Sortino | −0.94 / −0.62 |
| Commission Paid | $305.63 |
| Long Net / Short Net | +$25.84 / −$1,427.55 |
| Cascade Ratio | 1.94 (34 unique entries, 66 total trades) |

**Diagnóstico:** O outlier positivo de ADA em 1h (PF 1.42, +14.27%) **não se repete em 2h**. Em 2h, ADA é o pior performer em termos absolutos (−14%, DD 30%). Short trades são massivamente negativos (−$1,428). Long trades são mínimos positivos (+$26) — mas com apenas 13 trades, não é estatisticamente confiável.

---

### 6.3 XRPUSDT 2h

| Métrica | Valor |
|---------|-------|
| Trades | 45 (15 long, 30 short) |
| Win Rate | 37.8% (17W / 28L) |
| Net Profit | **−13.57%** (−$1,357.15) |
| Profit Factor | 0.64 |
| Max Drawdown | 21.81% |
| Avg Win / Avg Loss | $140.73 / −$133.91 (ratio 1.05) |
| Avg Bars in Trade | 14.42 |
| Sharpe / Sortino | −1.38 / −0.85 |
| Commission Paid | $258.73 |
| Long Net / Short Net | −$722.63 / −$634.52 |
| Cascade Ratio | 1.61 (28 unique entries, 45 total trades) |

**Diagnóstico:** Maior win rate (37.8%) mas ratio avg win/loss é quase 1.05 — perda líquida em cada trade. Longs E shorts são negativos em XRP, diferente de BTC/ADA onde longs foram neutros/positivos.

---

### 6.4 Comparação Cross-TF: FCE-v1 (1h) vs FCE-v2 (2h)

| Métrica | FCE-v1 (1h, 5 símbolos) | FCE-v2 (2h, 3 símbolos) | Delta |
|---------|-------------------------|--------------------------|-------|
| PF médio | 1.14 | 0.69 | **−0.45** |
| Símbolos PF>1 | 5/5 (100%) | 0/3 (0%) | **−100%** |
| Trades totais | 166 | 151 | −15 |
| Net médio | +3.6% | −11.7% | **−15.3 pp** |
| WR médio | 37.3% | 31.7% | −5.6 pp |
| Gap cross-TF | Não testado | **FALHOU** | — |

**Conclusão cruz-TF:** O edge que apareceu em 1h **não generaliza para 2h**. O PF cai de 1.14 para 0.69; a porcentagem de símbolos com PF>1 cai de 100% para 0%.

---

## 7. Diagnóstico

### 7.1 O que funcionou no 1h mas falhou no 2h

O padrão FCE em 1h mostrou PF > 1.0 em todos os 5 símbolos testados. Isso foi atribuído a:
- Exaustão de liquidity em microstructure de 1h (ordens stop, rebalancing algorítmico)
- Alta frequência de sinais (166 trades em 1 month)
- ADA como outlier positivo (long trades em ADA foram 7W/1L)

Em 2h:
- Os mesmos mecanismos de microstructure estão menos presentes (menos bars, mais "oficial" cada extremo)
- Sinais são mais raros e menos confiáveis
- ADA inverte de outlier positivo para pior performer
- Shorts são consistentemente negativos em todos os 3 símbolos

**Interpretação:** O padrão FCE em 1h pode ser um fenômeno de alta frequência que não escala para timescales maiores. Isso não invalida o conceito em princípio, mas indica que o edge é **dependente de escala temporal** — o que limita severamente sua utilidade prática.

---

### 7.2 Short bias como problema comum

Em todos os 3 símbolos em 2h, short trades são a maioria e tiveram resultado negativo. Em 1h, shorts em BTC/XRP foram positivos. A inversão de performance de shorts entre 1h e 2h sugere que o padrão FCE captura um fenômeno de "falha de continuation ascendente" mais do que "falha de continuation descendente" em 1h — e esse fenômeno não persiste em 2h.

---

### 7.3 Cascade ratio elevado em ADA

ADA em 2h: cascade ratio 1.94 (66 trades de 34 entradas únicas). Isso significa que o sistema está entrando múltiplas vezes em sequência curta após o cooldown — o que pode indicar que o padrão FCE está gerando sinais clustered em tempos de alta vol, onde a estratégia entra e sai repetidamente sem coletar edge.

---

### 7.4 Janela de 1 month pode ser insuficiente em 2h

1374 bars em 2h = ~114 dias de dados. Mas trades efetivos começam em ~2026-08-25 (datas reais dos trades nos resultados). A cobertura de trades é de ~1 month apenas. Em TFs maiores, janelas mais longas são necessárias para significance estatística. Um ciclo com janela 3-6 months em 2h poderia mostrar resultados diferentes — mas os resultados atuais são claramente negativos.

---

## 8. Verdict

### REJEITAR — Família FCE em strike 1

**Rationale:**

1. **Cross-TF falhou completamente.** FCE-v1 em 1h: PF ≥ 1.0 em todos os 5 símbolos. FCE-v2 em 2h: PF 0.64–0.79 em todos os 3 símbolos — todos abaixo de 1.0.

2. **O outlier de ADA em 1h não se repete.** ADA foi o símbolo mais promissor em 1h (PF 1.42, Sharpe 2.94). Em 2h, ADA é o pior performer (−14%, DD 30%). Isso sugere que o positivo em 1h foi um fluke de sample ou específico de alta frequência.

3. **Shorts consistentemente negativos em 2h.** Em 1h, shorts em BTC/XRP eram positivos. Em 2h, shorts são negativos em todos os 3 símbolos. O padrão FCE parece ser assimétrico (funciona mais em shorts que em longs em 1h; em 2h nem isso).

4. **PF médio 0.69 vs 1.14 em 1h.** Queda de 45% no PF médio ao transitar de 1h para 2h — não é uma variação menor, é uma inversão de sinal.

5. **Sem símbolo com PF > 1.0.** Após testar 3 símbolos em 2h, nenhum tem PF > 1.0. Para comparecido com 1h (5/5 com PF > 1.0), isso é uma falha robusta.

**Strike count:** Família FCE está em **strike 1** (primeiro teste cross-TF falhou).

**O que seria necessário para revisitar:**
- Testar em TFs MENORES (30m) — verificar se o edge é específico de alta frequência
- Testar com janela mais longa (3-6 months) em 2h — porém os resultados são negativos o suficiente que janela maior provavelmente não ajudaria
- Modificar o padrão FCE (lookback maior, SL/TP assimétrico, filtro de regime) e testar novamente

**Decisão:** Strike 1 aplicado. Se o próximo ciclo na família FCE (com modificação ou TF diferente) também falhar, a família será abandonada (strike 2 → strike 3 → abandono).

---

## 9. Next Cycle

### Opção A — Pivot para nova família (REC: Range Expansion Compression)

H3 dos ciclos anteriores (Range Expansion Compression Cycle) permanece inexplorada. A hipótese é: após fase de compressão de volatilidade (ATR percentile < 25), o primeiro breakout em direção do trend anterior tem edge positivo. Esta é uma hipótese greenfield distinta de FCE e merece investigação.

### Opção B — Investigar FCE em 30m (alta frequência)

Se o edge FCE é específico de alta frequência, 30m pode mostrar resultados intermediários entre 1h (PF 1.14) e 2h (PF 0.69). Mas isto requer mais créditos e é uma investigação de "last hope" para a família FCE antes de abandono.

### Opção C — Novas hipóteses greenfield

Gerar 5 novas hipóteses em um campo matemático diferente (ex: volatility clustering regimes, return asymmetry, entropy-based positioning).

### Recomendação

**Opção A — Pivot para REC (Range Expansion Compression Cycle).** A família FCE já tem strike 1; continuar investigando a mesma família sem modificação clara é risco de strike 2. REC é uma hipótese com matemática sólida (ciclos de volatilidade são bem documentados em crypto) e foi identificada como promissora nos ciclos anteriores mas nunca testada.

**Créditos restantes:** 59 (62 iniciais − 3 usados neste ciclo)

---

## Anexos

- **Strategy IDs:** QM-FCE-v2-2H-BTC (`01M39NXRBE3TAV1P9CZKCEX2ZD`), QM-FCE-v2-2H-ADA (`01M39NYW0K9G7FJTSJXDEAF8N1`), QM-FCE-v2-2H-XRP (`01M39NZ98WVNX51TGPKJ5ZSKJC`)
- **Pine source:** `data/pines/QM-FCE-v2-2H.pine`
- **Créditos gastos:** 3 créditos (1 por backtest × 3 símbolos)
- **Nenhuma ordem real — pesquisa/educação apenas.**

---

*Trader Dev MCP: authenticated as searesj92@gmail.com · engine tv_jul26_mc7 · parity profile applied.*
