# Quant Mathematician Cycle Report
## Cycle: QM-FCE-v1 (Failed Continuation Exhaustion)
## Date: 2026-09-24

---

## 1. Hipóteses Geradas (5 greenfield)

### H1 — FCE: Failed Continuation Exhaustion (selecionada)

**Ineficiência alvo:** Quando uma série de barras na mesma direção falha em estender o range máximo (highest high recent não é quebrado) e o close recua para a zona central, há falha de continuation com viés de reversão. A sequência de "alcista que falhou em fazer novo extremo" é mais informativa que a barra única isolada.

**Matemática central:**
- `upperExt = ta.highest(high, lookback)[1]` — topo do regime excluindo bar atual
- `priorHighExt = high[1] > ta.highest(high, lookback)[2]` — bar anterior estendeu o range
- `failHigh = priorHighExt AND high <= upperExt AND close < open` — falha de continuation
- SL: `upperExt + 1.5×ATR` | TP: `close - 1.5×ATR`

**Por que na crypto:** Mercado 24/7 com auction-driven microstructure; movimentos direcionais seguidos de falha súbita quando o lado dominante esgota — posicionamento após falha explora o flip medo/ganância.

**Breaking regime:** mercado em trend monótono puro (sem pullbacks); low vol em range sideways (false signals).

---

### H2 — LQS: Liquidity Sweep + Quick Snapback

**Ineficiência alvo:** When price sweeps a prior significant level (high/low of previous N bars) into a liquidity grab but immediately reverses with strong counter-close — the sweep exhausted the stop runners and a snapback offers favorable risk/reward.

**Matemática central:**
- `sweepHigh = low < ta.lowest(low, N)[1]` (low broke prior low = sweep)
- `snapback = close > open AND close > hl2[1]` (strong reversal confirmation)
- Entry on the close of the snapback bar; SL below sweep extreme; TP based on ATR multiples.

**Por que na crypto:** Crypto markets have concentrated liquidity at obvious levels (prior highs/lows, equal highs/lows); stop clusters get hunted then price snaps back — classic liquidity vacuum + refill.

**Breaking regime:** strong trending markets where the sweep is the start of a new leg, not a fakeout; when multiple sweeps cascade without reversal (one-direction momentum).

---

### H3 — REC: Range Expansion Compression Cycle

**Ineficiência alvo:** Markets cycle between range expansion (volatility burst) and compression (volatility contraction). The entry edge comes at the transition point: after a compression phase (ATR percentile drops below threshold), the first significant expansion in the direction of the prior trend has positive expectancy. The key insight: compression stores energy, but the release direction follows the prior trend bias — counter-trend breakouts from compression fail more often.

**Matemática central:**
- `atrPct = percentrank(atr(14), 50)` — percentile of current ATR relative to recent history
- `compression = atrPct < 25` — volatility compressed (bottom quartile)
- `priorTrend = close > sma(close, 50) ? 1 : close < sma(close, 50) ? -1 : 0` — trend bias
- `expansionBreak = close > ta.highest(high, 20)[1] AND atrPct > 35` — expansion starting
- Long entry if `priorTrend == 1 AND expansionBreak`; Short entry if `priorTrend == -1 AND expansionBreak`
- SL: below expansion start low (long) or above expansion start high (short)
- TP: 2×ATR from entry or signal flatten on opposite condition

**Por que na crypto:** Volatility cycles are pronounced in crypto — prolonged consolidations followed by explosive moves. The direction of the explosive move often follows the prior macro bias (compressed uptrend breaks up more often than down). Counter-trend compression breakouts carry higher failure rate.

**Breaking regime:** choppy sideways markets where priorTrend is ambiguous (close near SMA 50); when compression is followed by a volatility spike in the opposite direction immediately (mean-reversion, not continuation); when the compression period is too short to store meaningful energy (N too small).

---

### H4 — VPA-V2: Volume-Price Anomaly with Regime Filter (iteração com filtro)

**Ineficiência alvo:** Volume-price divergence patterns where price makes a new extreme but volume is declining (divergence) — this is a leading indicator of exhaustion. Different from VRAD: focuses on the VOLUME-PRICE relationship specifically, not displacement normalized by ATR.

**Matemática central:**
- `priceExtHigher = high > ta.highest(high, 20)[1]` — new price extreme
- `volDeclining = volume < ta.sma(volume, 20)[1]` — volume lower than recent average
- `divergence = priceExtHigher AND volDeclining` — price up but volume down = weakness
- Entry: fade the divergence with SL beyond the extreme, TP at mean reversion level
- Regime filter: only take divergence signals when vol regime is not extreme (atr/atr_sma between 0.7 and 1.3) — avoid high-vol chaos

**Por que na crypto:** Volume confirmation is essential in crypto — price moves without volume participation are suspect and often reverse. The combination of new extreme + declining volume + moderate volatility regime creates a higher-probability exhaustion setup than any single factor.

**Breaking regime:** high-volatility breakout regimes where volume naturally spikes with price (divergence doesn't apply); low-liquidity periods where volume is uniformly low (noisy signals); when the divergence is short-lived (one bar only) vs sustained (multiple bars).

---

### H5 — RAE: Return Asymmetry Exploitation

**Ineficiência alvo:** In crypto markets, upward returns tend to be more gradual (drift) while downward returns can be sudden (flash crashes, panic). This asymmetry creates an opportunity: look for setups where the probability distribution of returns shows positive drift but negative skew protection is cheap (via options-equivalent strategies or asymmetric position sizing).

**Matemática central:**
- `returnAsymmetry = ta.sma(close - close[1], 20) / ta.stdev(close - close[1], 20)` — normalized drift vs volatility
- `upDrift = returnAsymmetry > 0.1` — positive drift regime
- `downProtection = close > ta.lowest(low, 20)[1] - 2×atr` — below this = spike risk
- Strategy: take long positions in upDrift regime, but with aggressive downside protection (tight SL relative to ATR, or scale-in only on pullbacks)
- Secondary signal: when returnAsymmetry flips from positive to negative AND volume spikes — reduce/exit longs aggressively
- TP: based on ATR multiples or signal-based exit when drift turns negative

**Por que na crypto:** The drift-vs-burst asymmetry is well-documented in crypto microstructure. Algorithms that exploit this asymmetry can capture the gradual upside while protecting against sudden downside — a structurally favorable risk/reward profile.

**Breaking regime:** when the market enters a panic/crash regime (downward burst dominates); when upDrift is positive but the market is in a low-volatility compression (no meaningful drift to exploit); when the asymmetry flips rapidly (whipsaw).

---

## 2. Hipótese Selecionada: FCE (H1)

**Motivo da seleção (por ordem de prioridade do loop):**

1. **Matematical rigor** — FCE é distintamente diferente de todas as hipóteses dos ciclos anteriores (VND = single-bar fade; VRAD = displacement + regime; VPA = volume anomaly; MSE = liquidity rebalance). FCE explora SEQUENCE de barras, não barra única.

2. **Novidade absoluta** — Nenhum ciclo anterior testou falha de continuation sequence-based. É greenfield puro, não variação de algo testado.

3. **Testabilidade clara** — Condições bem definidas: bar[1] estende range, bar[0] falha em extender + fecha com convicção. Sem ambiguidade.

4. **Generalizabilidade cruz-símbolo** — A lógica de "extensão de range seguida de falha" é universal; não depende de propriedade específica de um símbolo.

5. **LS/TP razoável** — SL baseado no extremum + buffer ATR; TP simétrico. Risk-reward naturalmente favorável se o padrão existe.

6. **Simplicidade** — Poucos inputs, lógica linear, sem indicadores complexos.

**Por que não as outras:**
- H2 (LQS): Similar ao MSE/VPA dos ciclos anteriores — reutilização conceitual, não greenfield puro.
- H3 (REC): Promissora mas mais complexa (requires trend bias + compression detection + expansion detection); demais moving parts para primeiro teste.
- H4 (VPA-V2): Iteração de VPA que já falhou — não greenfield, risco de repetir o mesmo padrão de falha.
- H5 (RAE): Conceito interessante mas mais abstracto; difícil de traduzir em regras de entrada/saída claras sem mais desenvolvimento.

---

## 3. Trading Rules (FCE-v1)

### Long Entry
- Barra anterior (t-1) fez novo extremo alto: `high[1] > ta.highest(high, 20)[2]`
- Barra anterior teve corpo significativo: `|close[1]-open[1]| / atr[1] > 0.3`
- Barra atual (t-0) NÃO estende o extremo: `high <= ta.highest(high, 20)[1]`
- Barra atual fecha abaixo de abrir: `close < open` (conviction de reversão)
- Cooldown: 3 barras após saída antes de nova entrada long

### Short Entry
- Barra anterior (t-1) fez novo extremo baixo: `low[1] < ta.lowest(low, 20)[2]`
- Barra anterior teve corpo significativo: `|close[1]-open[1]| / atr[1] > 0.3`
- Barra atual (t-0) NÃO estende o extremo: `low >= ta.lowest(low, 20)[1]`
- Barra atual fecha acima de abrir: `close > open` (conviction de reversão)
- Cooldown: 3 barras após saída antes de nova entrada short

### Exits
- **SL Long:** `lowerExtPrior - 1.5×ATR` (abaixo do extremo inferior + buffer)
- **TP Long:** `close + 1.5×ATR` (lucro objetivo simétrico)
- **SL Short:** `upperExtPrior + 1.5×ATR` (acima do extremo superior + buffer)
- **TP Short:** `close - 1.5×ATR` (lucro objetivo simétrico)
- **Sem trailing** (regra de latência para broker real)

### Filtros
- `process_orders_on_close=true` (sem lookahead)
- pyramiding=1 (uma posição por direção)
- Cooldown obrigatório após cada trade fechado

---

## 4. Pine Script

```pine
//@version=6
strategy("QM-FCE-v1 — Failed Continuation Exhaustion",
  overlay=true,
  pyramiding=1,
  process_orders_on_close=true,
  commission_type=strategy.commission.percent,
  commission_value=0.05,
  default_qty_type=strategy.percent_of_equity,
  default_qty_value=100,
  margin_long=100,
  margin_short=100,
  initial_capital=10000)

// ── Inputs ──────────────────────────────────────────────
lookback     = input.int(20, "Lookback for extremes")
minDisp      = input.float(0.3, "Min prior-bar displacement (ATR mult)")
slAtRMult    = input.float(1.5, "SL buffer in ATR multiples")
tpAtRMult    = input.float(1.5, "TP in ATR multiples")
cooldown     = input.int(3, "Cooldown bars after exit")

// ── Indicators ──────────────────────────────────────────
atr = ta.atr(14)

// Extremes EXCLUDING current bar (use [1] to shift window)
upperExtPrior = ta.highest(high, lookback)[1]
lowerExtPrior = ta.lowest(low, lookback)[1]

// Prior bar extended the range (made new extreme vs window ending at [2])
priorHighExt = high[1] > ta.highest(high, lookback)[2]
priorLowExt  = low[1]  < ta.lowest(low, lookback)[2]

// Prior bar had meaningful body (not just a wick)
priorBody = math.abs(close[1] - open[1])
priorDisp = priorBody / atr[1]

// ── Failed Continuation ────────────────────────────────
// Bar[1] made new extreme, bar[0] fails to extend + closes with conviction
failHigh = priorHighExt and priorDisp > minDisp and high <= upperExtPrior and close < open
failLow  = priorLowExt  and priorDisp > minDisp and low  >= lowerExtPrior and close > open

// ── Cooldown ────────────────────────────────────────────
var int cdShort = 0
var int cdLong  = 0
var int prevClosed = 0

cdShort := cdShort > 0 ? cdShort - 1 : 0
cdLong  := cdLong  > 0 ? cdLong  - 1 : 0

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

**Strategy ID (MCP):** (a ser gerado pelo backtest)

**Paridade:** commission 0.05%, percent_of_equity 100, margin long/short 100, pyramiding 1

---

## 5. Backtest Matrix — FIRST RUN (BTC 1h only, validation)

**Período:** 2026-08-25 → 2026-09-24 (~1 month)
**Símbolo:** BTCUSDT (Bybit USDT linear perpetual)
**Timeframe:** 1h
**Capital:** $10,000
**Sizing:** 100% equity, margin long/short 100
**Commission:** 0.05%
**Slippage:** 2 ticks

### Resultados

| Métrica | Valor |
|---------|-------|
| Result ID | (a preencher após backtest) |
| Strategy ID | (a preencher após backtest) |
| Trades | (a preencher) |
| Win Rate | (a preencher) |
| Net Profit % | (a preencher) |
| Profit Factor | (a preencher) |
| Max DD % | (a preencher) |
| Avg Trade | (a preencher) |

---

## 6. Diagnóstico Preliminar (antes de ver resultados)

FCE é a primeira hipótese da família "sequence-based exhaustion" testada neste desk. Se mostrar PF > 1 e ≥5 trades em BTC 1h, expandir para matriz 5 símbolos × 1h/2h/4h. Se PF < 0.8 ou < 5 trades, diagnosticar:
- Thresholds muito restritivos (minDisp, lookback)?
- COoldown excessivo?
- O padrão não existe em crypto 1h?

---

## 7. Verdict Preliminar

**AGUARDANDO BACKTEST.** Após resultado:
- PF > 1.3 e ≥ 10 trades → **Watchlist** (expandir matriz)
- PF 1.0–1.3 e ≥ 5 trades → **Watchlist** (iterar threshold)
- PF < 1.0 ou < 5 trades → **REJECT** (provavelmente strike 1 nesta família; pivotar para REC ou LQS)
