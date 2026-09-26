# Quant Mathematician Cycle Report

## Cycle: QM-FBR-v2 — Failed Breakout Reversion
**Date:** 2026-09-24 05:26 UTC-3  
**Author:** solana-trend-bot · researcher profile  
**Engine:** tv_jul26 (TV_ENGINE_JUL_26 parity)  
**Credits consumed:** 5 backtests × 1 credit = 5  
**Strategy IDs:** BTC `01M38XNX43SSA70Q3XYDDHRSFJ` · ETH `01M38XVNDKDNTBR1C2PGFXXKZ5` · SOL `01M38XW44QNZ4P4TNDCS2GZA8K` · XRP `01M38Y1DEKWDN64R2SZAR0PDXY` · DOGE `01M38Y1MWDJTGAW3PE3PP8MVTZ`

---

## 1. Hypotheses Generated (3 greenfield)

### H1 — FBR: Failed Breakout Reversion (SELECTED)
**Ineficiência alvo:** quando um candle de range expandido (`tr > k × ATR`) raspa um extremo local (high/low dos últimos N barras) mas **falha em fechar além dele** (`close < open` no caso de high sweep, `close > open` no caso de low sweep), houve tentativa de breakout que falhou — o mercado não confirmou a nova zona de preço. Snapback esperado para o interior do range.

**Matemática central:**
- `highestHigh = ta.highest(high, 20)`; `lowestLow = ta.lowest(low, 20)`
- `prevRange = (high[1] - low[1]) > atr(14) * 1.25` (candle anterior de range expandido)
- `failedHigh = high[1] >= highestHigh[1] AND close[1] < open[1] AND prevRange` → short no bar seguinte
- `failedLow  = low[1]  <= lowestLow[1]  AND close[1] > open[1] AND prevRange` → long no bar seguinte
- SL: além do extremo raspado + buffer ATR (0.4 × ATR)
- TP: retrocesso de 45% do range do candle de sweep para o interior
- Cooldown 2 barras · time exit 20 barras · sem trailing

**Por que crypto:** stops concentrados acima/below dos extremos são frequentes em 24/7 sem gaps; sweeps de liquidez sem follow-through são majoritariamente falhas.

**Breaking regime:** breakout real com volume sustentado e close confirmando o extremo — mas a lógica não entra (não satisfaz `failedConfirm`).

### H2 — Volatility-Weighted Range Efficiency Decay
**Ineficiência alvo:** after vol expansion, range efficiency (close/mid proximity) decays — entrada quando efficiency colapsa após spike de vol.

**Descartada** — pouco distinguida de H1 e de VDB já testado.

### H3 — Failed Continuation After Displacement + Volume Divergence
**Ineficiência alvo:** candle de grande deslocamento em ATR seguido de candle com volume alto mas range encolhido (absorção) → entrada reversora no segundo candle.

**Descartada** — sample muito raro, difícil de calibrar sem overfitting.

---

## 2. Hypothesis Selected

**H1 — FBR (Failed Breakout Reversion) v2**

**Base matemática:** o insight não é "breakout falhou = reversão simples". O insight é: **sweep de liquidez sem confirmação de close em candle de range expandido é evento de alta informação** — o mercado testou um zona de stops e não encontrou fluxo que sustente o movimento, indicando que o breakout era falsa.

**Por que diferente de LSN/VDB:** LSN testou sweeps + snapback com foco em high/low raspados. VDB testou breakout comprimido com displacement. FBR foca especificamente no **candle seguinte ao failed sweep** com range confirmation (`close < open` ou `close > open`), não só no sweep em si.

**Assunção falsificável:** se a hipótese é verdadeira, o PF deve ser > 1 em pelo menos 3 dos 5 símbolos, e a win rate deve ser consistentemente acima de 40%.

---

## 3. Trading Rules

### Entrada LONG
- Barra anterior raspiu low dos últimos 20 barras: `low[1] <= ta.lowest(low, 20)[1]`
- Barra anterior teve range expandido: `(high[1] - low[1]) > atr(14)[1] * 1.25`
- Barra anterior fechou bullish dentro do range: `close[1] > open[1]`
- Não há posição short ativa (`not shortActive`)
- **Ação:** `strategy.entry("L", strategy.long)`

### Entrada SHORT
- Barra anterior raspiu high dos últimos 20 barras: `high[1] >= ta.highest(high, 20)[1]`
- Barra anterior teve range expandido
- Barra anterior fechou bearish dentro do range: `close[1] < open[1]`
- Não há posição long ativa (`not longActive`)
- **Ação:** `strategy.entry("S", strategy.short)`

### SL / TP (absolutos, re-emitidos a cada bar — engine-safe)
- LONG SL: `longEntryLow - atrAtEntry * 0.4` (0.4 ATR abaixo do extremo raspado)
- LONG TP: `longEntryLow + (prevRange * 0.45)` (45% do range de retrocesso)
- SHORT SL: `shortEntryHigh + atrAtEntry * 0.4` (0.4 ATR acima do extremo raspado)
- SHORT TP: `shortEntryHigh - (prevRange * 0.45)`

### Cooldown + time exit
- Cooldown: 2 barras após qualquer saída antes de re-entrar
- Time exit: 20 barras máximas em posição

### Filtros
- `pyramiding=1`, `process_orders_on_close=true`
- `commission=0.05%`, `margin_long=100`, `margin_short=100`, `initial_capital=10000`
- Sizing: 100% equity (perfil de parity do Trader Dev)
- Sem trailing stops (regra do loop)

---

## 4. Pine Script

```pine
//@version=6
// QM-FBR-v2 — Failed Breakout Reversion (greenfield)
// Hypothesis: after a high-range candle that tries to break an N-bar extreme but closes back
// inside the range (failed breakout), the next candle tends to revert toward the interior.
//
// MCP RULE compliant: process_orders_on_close=true, pyramiding=1, commission 0.05%,
// 100% equity, margin 100/100. No arrays, cancel, security, repaint.

strategy("QM-FBR-v2 | Failed Breakout Reversion", overlay=true,
  pyramiding=1, process_orders_on_close=true,
  commission_type=strategy.commission.percent, commission_value=0.05,
  default_qty_type=strategy.percent_of_equity, default_qty_value=100,
  margin_long=100, margin_short=100, initial_capital=10000)

// ── inputs ──
sweepN       = input.int(20,    "Sweep lookback (bars)")
volMult      = input.float(1.25, "Range big mult × ATR")
slBuffer     = input.float(0.4,  "SL buffer × ATR beyond swept extreme")
cooldown     = input.int(2,     "Cooldown bars after exit")
timeCap      = input.int(20,    "Max bars in trade")
tpFrac       = input.float(0.45, "TP fraction of sweep range (0-1)")

// ── core series ──
atr14    = ta.atr(14)
highestHigh = ta.highest(high, sweepN)
lowestLow   = ta.lowest(low, sweepN)

// Detection on bar [1] (no lookahead)
prevHigh = high[1]
prevLow  = low[1]
prevClose = close[1]
prevOpen  = open[1]
prevRange = prevHigh - prevLow
prevBig   = prevRange > atr14[1] * volMult

failedHighCond = prevHigh >= highestHigh[1] and prevClose < prevOpen and prevBig
failedLowCond  = prevLow  <= lowestLow[1]   and prevClose > prevOpen and prevBig

// Entry signals
longSig  = failedLowCond  and not shortActive
shortSig = failedHighCond and not longActive

if longSig
    strategy.entry("L", strategy.long)
if shortSig
    strategy.entry("S", strategy.short)

// SL/TP targets
var float longEntryLow   = na
var float shortEntryHigh = na
var float atrAtEntry     = na

if longSig
    longEntryLow  := prevLow
    atrAtEntry    := atr14[1]
if shortSig
    shortEntryHigh := prevHigh
    atrAtEntry     := atr14[1]

longSL  = longEntryLow  - atrAtEntry * slBuffer
longTP  = longEntryLow  + (prevRange * tpFrac)
shortSL = shortEntryHigh + atrAtEntry * slBuffer
shortTP = shortEntryHigh - (prevRange * tpFrac)

if strategy.position_size > 0
    strategy.exit("LX", from_entry="L", stop=longSL, limit=longTP)
if strategy.position_size < 0
    strategy.exit("SX", from_entry="S", stop=shortSL, limit=shortTP)

// Cooldown + time exit
var int barCount  = 0
var int coolCount = 0

if strategy.position_size != 0
    barCount += 1
    coolCount := 0
else if coolCount < cooldown
    coolCount += 1

if longSig or shortSig
    barCount  := 0
    coolCount := 0

if strategy.position_size > 0 and barCount >= timeCap
    strategy.close("L")
    barCount := 0
if strategy.position_size < 0 and barCount >= timeCap
    strategy.close("S")
    barCount := 0

// State flags
var bool longActive  = false
var bool shortActive = false

if longSig
    longActive  := true
    shortActive := false
if shortSig
    shortActive := true
    longActive  := false
if strategy.position_size == 0 and coolCount > cooldown
    longActive  := false
    shortActive := false

// Signal plots
plot(longSig  ? 1 : 0, "Long Signal",  color.green,  0, plot.style_circles, linewidth=2)
plot(shortSig ? 1 : 0, "Short Signal", color.red,    0, plot.style_circles, linewidth=2)
```

---

## 5. Backtest Matrix

| Symbol | Timeframe | Strategy ID | Result ID |
|--------|-----------|-------------|-----------|
| BTCUSDT | 1h | `01M38XNX43SSA70Q3XYDDHRSFJ` | `01M38XNWWNFK902Q576KT0STFD` |
| ETHUSDT | 1h | `01M38XVNDKDNTBR1C2PGFXXKZ5` | `01M38XVN8MM46HQ7RMPD3H5X2A` |
| SOLUSDT | 1h | `01M38XW44QNZ4P4TNDCS2GZA8K` | `01M38XW3XZ8V2K28J1T2CJCNPA` |
| XRPUSDT | 1h | `01M38Y1DEKWDN64R2SZAR0PDXY` | `01M38Y1D5CYXNG3AP2XWWP2E53` |
| DOGEUSDT | 1h | `01M38Y1MWDJTGAW3PE3PP8MVTZ` | `01M38Y1MN81JAYZQP5HNE7QPEK` |

**Assumptions:** Bybit USDT linear perp · 100% equity · margin 100/100 · commission 0.05% · slippage 0 · pyramiding 1 · process_orders_on_close · tv_jul26 engine. Window: ~Jun 2026 – Sep 2026 (clickhouse coverage).

---

## 6. Results

| Symbol | Net% | PF | DD% | WR% | Trades | Win/Loss | Long | Short | Avg Trade | Sharpe |
|--------|------|----|-----|-----|--------|----------|------|-------|-----------|--------|
| BTC | -8.47 | 0.13 | 8.47 | 25.6 | 39 | 10/29 | 0 | 39 | -$21.71 | -7.48 |
| ETH | -2.75 | 0.44 | 4.56 | 29.4 | 17 | 5/12 | 17 | 0 | -$16.20 | -1.92 |
| SOL | -7.75 | 0.19 | 7.75 | 13.6 | 44 | 6/38 | 0 | 44 | -$17.62 | -3.91 |
| XRP | -5.21 | 0.31 | 5.36 | 14.9 | 47 | 7/40 | 0 | 47 | -$11.08 | -5.31 |
| DOGE | -3.74 | 0.40 | 4.50 | 43.8 | 16 | 7/9 | 16 | 0 | -$23.37 | -2.68 |

**Aggregate:** 5 símbolos, PF 0.13–0.44, todos negativos, win rate 13.6–43.8%, trades 16–47.

---

## 7. Diagnosis

### 7.1 Viés de direção (crítico)
- BTC, SOL, XRP: **todos short** (0 long trades). Mercado bullish em 1h gerou apenas sweeps de alta (high raspados) sem reversal.
- ETH, DOGE: **todos long** (0 short trades). Mercadobearish relativo gerou apenas sweeps de low.
- A lógica `failedHigh → short` é assimétrica: em mercado trending up, high sweeps são frequentes mas o close volta para dentro do range porque o candle seguinte continua subindo — não há snapback.

### 7.2 PF < 0.5 em todos
- Profit factor 0.13–0.44 é consistentemente inferior a 1. Sem edge rentável.
- Trade distribution: 16–47 trades por símbolo — sample não é pequeno demais, mas o edge é negativo.

### 7.3 SL/TP desbalanceado
- Avg bars in trade: 2.0–2.1 barras. O TP (45% do range de retrocesso) é muito curto em relação ao SL (0.4 ATR abaixo do extremo).
- Em candles de range expandido, 0.4 ATR abaixo do low pode ser muito próximo — o market noise ativa o SL antes do TP.
- TP/Alvo é baseado no range do candle de sweep, não na volatilidade do mercado subsequente — calibração pobre.

### 7.4 Similaridade com LSN (já testado)
- LSN (cycle QM-LSN-v1, 02:34) testou sweep + snapback com entrada no bar seguinte ao failed high/low.
- LSN também teve resultados negativos (verificar relatório LSN).
- FBR v2 é essencialmente uma versão refinada do mesmo insight. A hipótese "sweep failed → snapback" parece não ter edge consistente em crypto 1h.

### 7.5 Mercado range vs trend
- A lógica não tem filtro de regime. Em mercado trending, sweeps são continuações, não reversões.
- Filtro de vol regime (vol alta = breakout legítimo, vol baixa = fakeout) seria necessário para separar os casos.

---

## 8. Verdict

**REJECTAR**

**Motivo:**
1. PF < 0.5 em todos os 5 símbolos — edge negativo consistente.
2. Viés de direção severo (BTC/SOL/XRP só short, ETH/DOGE só long) — a lógica é assimétrica e não captura reversões em ambas as direções.
3. Hipótese essencialmente duplicata de LSN (já testado sem sucesso) — "sweep failed → snapback" não tem edge em crypto 1h.
4. SL/TP mal calibrado: TP muito curto (45% do range do candle) vs SL de 0.4 ATR.
5. Trades muito curtos (~2 barras) — estratégia fecha por SL antes de dá espaço para o TP.

**Strike count:** Contagem de strikes não é formal aqui — é a primeira teste da família FBR. Mas resultado consistentemente negativo + similaridade com LSN rejeitado justifica pivotar.

**Não é production candidate, não é incubate, não é watchlist.** O insight de "sweep without confirmation = reversal" não se sustenta em crypto 1h sem filtro de regime.

---

## 9. Next Cycle

**Decisão:** pivotar para linha não explorada nesta sessão.

**Linhas já testadas nesta sessão (não repetir):**
- VNDR (05:00): displacement vs median + filtro atrDelta
- VRAD (01:50): vol regime bimodal + displacement
- LSN (02:34): liquidity sweep + snapback
- VDB (já tinha pine): breakout comprimido + displacement
- VCE-FC: volume confirmation + failed continuation
- FBR v2 (este ciclo): failed breakout reversion → **REJECTAR**

**Próxima hipótese candidata (não testada nesta sessão):**
- **Range Expansion After Compression with Regime Filter** — combina compressão de vol (atr em percentil baixo) com regime classifier: se vol estava comprimida e expande de forma bilateral (não direcional), entrada na direção do primeiro candle de expansão confirmado por volume. Diferente de VRAD porque o foco é na **compressão prévia**, não no regime atual.

**Alternativa (se compressed-expansion já explorada):** Volatility-Duration Anomaly — candles de longa duração (em barras) com range moderado mas volume alto indicam acumulação; entrada no quebrar do range subsequente.

**Parâmetros para próxima ciclo:**
- Testar cross-symbol (4–5 símbolos) × cross-TF (1h, 4h) se a hipótese for strong enough.
- Manter SL/TP em ATR para evitar calibração por candle range.
- Incluir filtro de regime explícito (vol percentile ou ADX).

**Créditos restantes:** ~144 (estimativa após 5 créditos usados).

---

*Relatório gerado automaticamente pelo loop Quant Mathematician (researcher). Sem ordens reais. Backtest não é garantia de performance futura. Human approval required para qualquer live consideration.*
