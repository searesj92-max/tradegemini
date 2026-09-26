# Quant Mathematician Cycle Report
## Cycle: QM-VEE-v1 — Volatility Expansion Entry (Breakout After Compression)

**Date:** 2026-09-24 02:44 UTC-3  
**Author:** solana-trend-bot · researcher profile  
**Engine:** tv_jul26 (TV_ENGINE_JUL_26 parity)  
**Credits consumed:** ~5 backtests × 1 credit (estimated)

---

## 1. Hipóteses Geradas (4 greenfield)

### H1 — VEE: Volatility Expansion Entry (BREAKOUT — distinto de todos os anteriores)

**Ineficiência alvo:** Após período de compressão de volatilidade (ATR abaixo de limiar de média móvel), quando uma barra rompe o extremo recente E fecha além do extremo (follow-through confirmado), há continuação da direção do breakout.

**Matemática central:**
- `compPhase = atr(14) < sma(atr(14), 20) * compThresh` → regime de compressão de vol
- `prevHigh = ta.highest(high[2], N)` → maior high antes do bar[1]
- `prevLow  = ta.lowest(low[2], N)` → menor low antes do bar[1]
- `breakoutHigh = high[1] > prevHigh AND close[1] > prevHigh` → bar[1] rompe E fecha além do extremo (confirmado, não só toque)
- `breakoutLow  = low[1]  < prevLow  AND close[1] < prevLow`
- `rangeExpanded = (high[1] - low[1]) > atr(14) * expMult` → bar de breakout tem range significativo
- `longSig  = compPhase AND breakoutHigh AND rangeExpanded`
- `shortSig = compPhase AND breakoutLow  AND rangeExpanded`
- SL/TP: fixos em múltiplos de ATR (slMult=1.5, tpMult=2.0), com preço de entrada e ATR armazenados no momento da entrada (fixos, não caminham)
- Cooldown: 3 barras após qualquer saída
- Time exit: 20 barras máx

**Por que crypto:** Mercados crypto passam muito tempo em compressão (consolidação) seguida de expansão volátil. Breakouts com follow-through (fechamento além do extremo) são movimentos reais de tendência, não fakeouts. A compressão precede expansiones significativas — é o ciclo volário fundamental de crypto.

**Breaking regime:** mercados em lateralidade crônica sem trending (breakouts repetidos falham — mas a condição de follow-through filtra a maioria dos fakeouts); gaps de liquidez que pulam a zona de compressão.

**Pine expression:** ta.atr, ta.sma, ta.highest/ta.lowest com offset [2] (sem lookahead), close[1] comparado ao extremo anterior.

**Distinção das hipóteses anteriores:**
| Ciclo | Família | Direção | Por que VEE é distinto |
|-------|---------|----------|------------------------|
| VND-v1 | Displacamento normalizado | Fade | VEE é breakout (continuação), não fade |
| MSE-v1 | Liquidez/iactance void | Fade | VEE requer follow-through (close além), não fade de toque |
| VRAD-v1 | Regime vol + displacamento | Fade | VEE é trend-following puro, sem regime classifier complexo |
| LSN-v1 | Sweep + snapback | Fade | VEE é o oposto: continua no breakout real, não fade no fakeout |
| VPA-v1 | Anomalia volume-preço | Fade | VEE não depende de volume |

**VEE é a PRIMEIRA hipótese de trend-following/continuation do quant.**

---

### H2 — FCD: Failed Continuation Detection (última hipótese de fade antes de pivotar)

**Ineficiência alvo:** Após barra de grande deslocamento (corpo > φ × ATR) quando o mercado NÃO apresenta follow-through no bar seguinte (close volta para dentro da zona de equilíbrio), o movimento falhou — reversão acelerada.

**Matemática central:**
- `bigMove = |close[1] - open[1]| > atr(14) * φ` (φ=1.618)
- `direction = sign(close[1] - open[1])`
- `noFollow = close < open[1] + direction * followZone` (bar atual já desistiu)
- `entry` na direção oposta ao bigMove
- SL: atrás do bar de bigMove
- TP: retorno ao sma(close, 20) ou ATR múltiplo

**Por que crypto:** impulsos de uma barra sem follow-through são fakeouts; o mercado refaz no próximo bar.

**Breaking regime:** tendência real com follow-through em múltiplas barras.

**Distinção:** foca em displacement de UMA barra, não em sweep de extremo. É fade, distinto de VEE.

---

### H3 — RSA: Range-Stability Anomaly (já descrita em ciclo anterior, não testada)

**Ineficiência alvo:**Quando o range das últimas N barras é estável (baixo coeficiente de variação) mas o preço acumula deslocamento, há "glide" concentrado — quando a estabilidade quebra, o movimento inverte.

**Matemática central:**
- `rangeStability = stdev(rangeSeries, N) / sma(rangeSeries, N)` (CV do range)
- `stable = rangeStability < stabilityThresh`
- `glide = cumsum(close - open)` nos últimos N
- `breakBar = range > sma(range, N) * breakMult`
- `entry`: se `glide > glideThresh` e `breakBar` → fade na direção oposta ao glide

**Por que crypto:** mercados em consolidação com glide tendem a ter breakout falso que se reverta.

**Distinção:** foca em estabilidade do range, não em toque de extremo. Pode ser raro (0 trades).

---

### H4 — VT: Volatility Trend (nova família — trend-following com filtro de compressão)

**Ineficiência alvo:** When vol está em regime de expansão (ATR acima da média) e o preço está acima da EMA(50) (ou abaixo para shorts), há tendência sustentada com edge de continuação.

**Matemática central:**
- `volExpansion = atr(14) > sma(atr(14), 20) * volThresh` (vol em expansão)
- `trendUp = close > ema(close, 50)` (tendência de alta)
- `trendDown = close < ema(close, 50)`
- `entry long` se `volExpansion AND trendUp AND close > ema(close, 20)` (confirmacao de curto prazo)
- `entry short` se `volExpansion AND trendDown AND close < ema(close, 20)`
- SL: 2×ATR abaixo/above da entrada
- TP: 3×ATR (RR=1.5)

**Por que crypto:** expansão de vol + tendência é o ambiente de maior movimento; entrar nesse ambiente captura a maior parte do movimento.

**Breaking regime:** vol alta sem tendência clara (choppy vol expansion — o market move muito mas não trending).

**Distinção:** mais simples que VEE (não requer breakout detection), mas depende de EMA(50) que pode ser lento.

---

## 2. Hipótese Selecionada: H1 — VEE (Volatility Expansion Entry)

**Motivo da seleção (por ordem de prioridade do loop):**

1. **Primeira hipótese de trend-following do quant:** todas as hipóteses anteriores (VND, MSE, VRAD, LSN, VPA) foram fade/reversal e falharam. O desk's melhores estratégias (rsi-t200b, LIT G91f10) são trend-following. VEE é a primeira hipótese alinhada com o que funciona no desk — mas com matemática própria, não copiando.

2. **Simplicidade:** 3 condições (compressão + breakout com follow-through + range expansion). Sem indicadores complexos. Sem EMA longa. Sem regime classifier.

3. **Testabilidade:** condições observáveis no bar[1]; entrada no bar seguinte; follow-through é confirmado (close além do extremo), não apenas toque — filtrando fakeouts.

4. **Math rigor:** a hipótese é bem fundamentada em microestrutura de mercado: compressão de vol precede expansão; breakouts com follow-through são movimentos reais; a condição `close[1] > prevHigh` (não apenas `high[1] > prevHigh`) filtra sweeps sem continuação.

5. **Generalizabilidade:** a hipótese é independente do par — compressão + breakout com follow-through é um fenômeno universal de microestrutura, presente em todos os pares crypto.

6. **Clear risk management:** SL/TP fixos em ATR múltiplos, cooldown, time exit. Sem trailing.

7. **Distinção matemática das hipóteses que falharam:**
   - VEE é o OPPOSTO de LSN: LSN entra quando o breakout FAALHA (close < high após toque no high); VEE entra quando o breakout CONFIRMA (close > prevHigh após toque no high). São hipóteses complementares testando lados opostos do mesmo evento.
   - Se LSN falhou porque "snapback não é confiável", VEE pode funcionar porque "breakout real com follow-through é confiável".

**Por que VEE pode funcionar quando os outros falharam:**
- VEE é trend-following, não fade. O padrão dos dados (todas as hipóteses de fade falhando) sugere que crypto 1h não 보상 fade/reversal neste período. VEE testa a hipótese oposta.
- A condição de follow-through (`close[1] > prevHigh`) é mais restritiva que LSN's `failedConfirm` (`close[1] < high[1]`). Isso filtra mais fakeouts e deixa apenas breakouts reais.
- A compressão de vol como filtro de entrada reduz trades em ambientes de alta vol caótica (onde breakouts são frequentemente falsos).

---

## 3. Regras de Trading

### Entradas (Long)

| Condição | Expressão | Nota |
|----------|-----------|------|
| Regime de compressão de vol | `atr(14) < sma(atr(14), 20) * compThresh` | compThresh = 0.7 (ATR 30% abaixo da média) |
| Bar[1] rompeu o high recente | `high[1] > ta.highest(high[2], sweepN)` | sweepN = 20 barras |
| Bar[1] fechou além do high recente | `close[1] > ta.highest(high[2], sweepN)` | follow-through confirmado (não só toque) |
| Bar[1] teve range expandido | `(high[1] - low[1]) > atr(14) * expMult` | expMult = 1.0 (range ≥ 1 ATR) |
| Cooldown ativo | `cd > cooldownBars` | cooldownBars = 3 |

→ **Long entry** no bar seguinte ao sinal.

### Entradas (Short)

| Condição | Expressão | Nota |
|----------|-----------|------|
| Regime de compressão de vol | `atr(14) < sma(atr(14), 20) * compThresh` | idem |
| Bar[1] rompeu o low recente | `low[1] < ta.lowest(low[2], sweepN)` | idem |
| Bar[1] fechou além do low recente | `close[1] < ta.lowest(low[2], sweepN)` | follow-through confirmado |
| Bar[1] teve range expandido | `(high[1] - low[1]) > atr(14) * expMult` | idem |
| Cooldown ativo | `cd > cooldownBars` | idem |

→ **Short entry** no bar seguinte ao sinal.

### Saídas

| Tipo | Valor | Motivo |
|------|-------|--------|
| **SL (Long)** | `longEntryPrice - atr(14) * slMult` (fixo, armazenado no momento da entrada) | slMult = 1.5 ATR abaixo da entrada |
| **TP (Long)** | `longEntryPrice + atr(14) * tpMult` (fixo) | tpMult = 2.0 ATR acima da entrada (RR = 1.33) |
| **SL (Short)** | `shortEntryPrice + atr(14) * slMult` (fixo) | idem |
| **TP (Short)** | `shortEntryPrice - atr(14) * tpMult` (fixo) | idem |
| **Time exit** | 20 barras após entrada | Limita exposição |
| **Cooldown** | 3 barras após qualquer saída | Evita overtrading |
| **Nenhum trailing stop** | — | Regra do loop |

### Invalidação
- Se o mercado não rompe o extremo (só toca) ou se o close não confirma (volta para dentro) → não entra. A lógica só entra se o breakout é real (close além do extremo).
- O Pine usa bar[1] para avaliar as condições ANTES do bar de entrada — sem lookahead, sem repint.

### Risco
- 100% equity por posição, pyramiding=1, margin 100/100, commission 0.05%, process_orders_on_close=true.
- SL/TP fixos no momento da entrada (preço de entrada e ATR armazenados em vars) — não caminham com o preço.
- Cooldown de 3 barras limita a frequência máxima.
- Sem trailing stops.

---

## 4. Pine Script

**Arquivo:** `C:\Users\seares\Desktop\botrade\qm_vee_v1.pine`

```pine
//@version=6
// QM-VEE-v1 — Volatility Expansion Entry
// Hypothesis: after vol compression, breakout with follow-through (close beyond extreme) -> continuation.
// Entry: bar[1] shows range expansion + close beyond recent extreme -> enter on next bar in breakout direction.
// Exit: fixed SL/TP in ATR ticks (stored entry price + entry ATR). No trailing. No repaint, no lookahead.
// Allowed ta.* only; process_orders_on_close=true, pyramiding=1, commission 0.05%.

strategy(
  title="QM-VEE-v1 — Volatility Expansion Entry",
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
compThresh   = input.float(0.7, "Compression threshold (ATR/SMA_ATR)", minval=0.3, maxval=0.95, step=0.05, group="Entry")
sweepN       = input.int(20, "Extreme lookback (bars)", minval=5, group="Entry")
expMult      = input.float(1.0, "Expansion bar range min (x ATR)", minval=0.2, step=0.1, group="Entry")
slMult       = input.float(1.5, "SL distance (x ATR)", minval=0.5, step=0.1, group="Exit")
tpMult       = input.float(2.0, "TP distance (x ATR)", minval=0.5, step=0.1, group="Exit")
cooldownBars = input.int(3, "Cooldown bars after exit", minval=0, group="Exit")
timeExitBars = input.int(20, "Time exit (max bars)", minval=1, group="Exit")

// === Indicators ===
atrVal    = ta.atr(14)
atrSma    = ta.sma(atrVal, 20)
compPhase = atrVal < atrSma * compThresh  // volatility compression regime

prevHigh  = ta.highest(high[2], sweepN)  // highest high BEFORE bar[1] (no lookahead)
prevLow   = ta.lowest(low[2], sweepN)    // lowest low BEFORE bar[1]

// Breakout WITH follow-through: close beyond previous extreme (not just wick touch)
breakoutHigh = high[1] > prevHigh and close[1] > prevHigh
breakoutLow  = low[1]  < prevLow  and close[1] < prevLow

rangeBar1     = high[1] - low[1]
rangeExpanded = rangeBar1 > atrVal * expMult  // bar[1] range meaningfully expanded

longSig  = compPhase and breakoutHigh and rangeExpanded
shortSig = compPhase and breakoutLow  and rangeExpanded

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

// === Fixed SL/TP: store entry price + ATR at entry time, use for fixed exits ===
var float longEntryPrice = na
var float shortEntryPrice = na
var float longEntryATR = na
var float shortEntryATR = na

if longSig and canTrade and strategy.position_size == 0
    longEntryPrice := close      // store entry bar's close (fill price with process_orders_on_close)
    longEntryATR := atrVal      // store ATR at entry time

if shortSig and canTrade and strategy.position_size == 0
    shortEntryPrice := close
    shortEntryATR := atrVal

// === Exits (fixed, based on stored entry values — do not ratchet) ===
if strategy.position_size > 0
    strategy.exit("LX", from_entry="L",
                 stop=longEntryPrice - longEntryATR * slMult,
                 limit=longEntryPrice + longEntryATR * tpMult)

if strategy.position_size < 0
    strategy.exit("SX", from_entry="S",
                 stop=shortEntryPrice + shortEntryATR * slMult,
                 limit=shortEntryPrice - shortEntryATR * tpMult)

// === Time exit ===
var int barsInTrade = 0
if strategy.position_size != 0
    barsInTrade += 1
else
    barsInTrade := 0
if barsInTrade >= timeExitBars
    strategy.close_all()

// === Plots ===
plot(compPhase, "Compression Phase", color=color.new(color.teal, 50), style=plot.style_linebr)
plot(longSig, "Long Signal", color=color.green, style=plot.style_circles, linewidth=2)
plot(shortSig, "Short Signal", color=color.red, style=plot.style_circles, linewidth=2)
plot(prevHigh, "Prev High Ref", color=color.new(color.blue, 50), style=plot.style_linebr)
plot(prevLow, "Prev Low Ref", color=color.new(color.orange, 50), style=plot.style_linebr)
```

**Checks de qualidade:**
- [x] `//@version=6` + `strategy(..., pyramiding=1, process_orders_on_close=true)`
- [x] Todos os `ta.*` usados estão na allowlist: `ta.atr`, `ta.sma`, `ta.highest`, `ta.lowest`
- [x] Nenhum `cancel`, `strategy.order`, `request.security`, `arrays`
- [x] Nenhum martingale / pyramiding>1 / grid
- [x] Exits usam `strategy.exit` com `stop`/`limit` fixos (valores armazenados em vars, não caminham)
- [x] Nenhum `low <= *trail*` / `high >= *trail*` → `strategy.close`
- [x] `from_entry` ids correspondem aos `entry` ids ("L" e "S")
- [x] `na()` não necessário — todas as séries estão definidas
- [x] Sem trailing stop (regra do loop)
- [x] SL/TP fixos com preço de entrada e ATR armazenados — não ratchet

---

## 5. Backtest Matrix

### Configuração
- **Engine:** tv_jul26 (TV_ENGINE_JUL_26 parity, mcprule-validated)
- **Período:** ~Jun 2026 → Sep 24 2026 (ultimo bar disponível no ClickHouse)
- **Capital:** $10,000
- **Sizing:** 100% equity, margin long/short 100
- **Commission:** 0.05% (MCP parity)
- **Slippage:** padrão do engine (não override)

### Matriz — Etapa 1: 5 símbolos × 1h (5 backtests)

| # | Símbolo | TF | Strategy ID | Result ID | Status |
|---|---------|----|-------------|-----------|--------|
| 1 | BTCUSDT | 1h | (a definir) | (a definir) | 🔄 backtesting |
| 2 | ETHUSDT | 1h | (a definir) | (a definir) | 🔄 backtesting |
| 3 | SOLUSDT | 1h | (a definir) | (a definir) | 🔄 backtesting |
| 4 | XRPUSDT | 1h | (a definir) | (a definir) | 🔄 backtesting |
| 5 | BNBUSDT | 1h | (a definir) | (a definir) | 🔄 backtesting |

**Créditos estimados:** 5 créditos para esta etapa.

**Decisão pós-etapa 1:**
- Se ≥ 3 símbolos com PF > 1.0 e trades > 30 → expandir para mais TFs (15m, 30m, 2h, 4h) e mais símbolos (DOGE, ADA, AVAX, LINK, NEAR).
- Se 0-2 símbolos com PF > 1.0 → rejeitar linha e pivotar para H2 (FCD) ou pivotar completo para trend-following com filtro de regime.

---

## 6. Results

*(A campiar após os backtests — resultados não disponíveis no momento da escrita deste relatório)*

---

## 7. Diagnosis

*(A preencher após análise dos resultados)*

---

## 8. Verdict

**AGUARDANDO RESULTADOS DOS BACKTESTS**

---

## 9. Next Cycle

*(A definir após resultados)*

---

## Informações de execução

- **Trader Dev MCP:** autenticado como searesj92@gmail.com (free tier)
- **Créditos:** ~149 restantes (após ciclo LSN-v1 com 5 créditos gastos)
- **Engine:** tv_jul26 (mcprule-validated)
- **Perfil de broker:** commission 0.05%, percent_of_equity 100%, margin 100/100, initial_capital $10,000
- **Nenhuma ordem real:** todos os testes são backtest virtuais no engine de paridade

---

## Arquivos emitidos

- **Pine:** `C:\\Users\\seares\\Desktop\\botrade\\qm_vee_v1.pine`
- **Relatório:** `data/reports/2026-09-24-0244-researcher-qm-vee-v1.md`

---

## License & Disclaimer

*Research and education only. Not financial advice. Backtests are not future performance. No real orders placed.*

Generated: 2026-09-24 02:44 UTC-3  
Agent: researcher (solana-trend-bot desk)  
Cycle: QM-VEE-v1
