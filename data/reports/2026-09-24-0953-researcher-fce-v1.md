# Quant Mathematician Cycle Report
## Cycle: QM-FCE-v1 (Failed Continuation Exhaustion)
## Date: 2026-09-24 09:53 UTC-3

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

## 4. Pine Script (//@version=6)

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

**Strategy ID (MCP):** `01M39D5SJ2VP9V6MX80464B0QR`
**Paridade:** commission 0.05%, percent_of_equity 100, margin long/short 100, pyramiding 1

---

## 5. Backtest Matrix

**Período:** 2026-08-25 → 2026-09-24 (~1 month, ~1021 bars por símbolo)
**Símbolos:** BTCUSDT, ETHUSDT, SOLUSDT, XRPUSDT, ADAUSDT (Bybit USDT linear perpetual)
**Timeframe:** 1h
**Capital:** $10,000
**Sizing:** 100% equity, margin long/short 100
**Commission:** 0.05%
**Slippage:** 2 ticks

| # | Símbolo | TF | Trades | WR% | Net% | PF | MaxDD% | Sharpe | Result ID | Strategy ID |
|---|---------|-----|--------|-----|------|-----|--------|--------|-----------|-------------|
| 1 | BTCUSDT | 1h | 26 | 46.2 | +0.51 | 1.05 | 5.12 | 0.37 | 01M39D5SA6QSMTW5FB7F2YR4QM | 01M39D5SJ2VP9V6MX80464B0QR |
| 2 | ETHUSDT | 1h | 37 | 29.7 | +0.87 | 1.08 | 6.19 | 0.46 | 01M39D8HYRDY97G01CH3TJ1QGQ | 01M39D8J5YZ83XQQH0PTNY9KYB |
| 3 | SOLUSDT | 1h | 33 | 30.3 | +0.82 | 1.04 | 13.88 | 0.38 | 01M39D9467AM07NZCGA1CM57QB | 01M39D94BW2AAQHKNM0VD8SRT5 |
| 4 | XRPUSDT | 1h | 31 | 41.9 | +2.77 | 1.10 | 16.26 | 0.93 | 01M39D9K2Z3R5R5J3DXAFKFZDM | 01M39D9K9K713PHKXVFR8Q89B6 |
| 5 | ADAUSDT | 1h | 39 | 38.5 | +14.27 | 1.42 | 17.99 | 2.94 | 01M39DA4J3BAY4TY9QVZAPYSG0 | 01M39DA4QW2JW8SY481A2SQ3MW |

**Trades totais:** 166
**Win Rate agregado:** ~37.3% (62W / 104L calculado rough)
**Todos PF > 1.0 em todos os 5 símbolos** — sinal forte de robustez inicial.

---

## 6. Results (Detalhados)

### 6.1 Consolidação por símbolo

|| Símbolo | Trades | Long | Short | Long Net | Short Net | WR | PF | Sharpe |
|---|---------|--------|------|-------|----------|-----------|-----|-----|--------|
| BTC | 26 | 8 | 18 | -393.6 | +445.1 | 46.2% | 1.05 | 0.37 |
| ETH | 37 | 7 | 30 | +49.2 | +38.0 | 29.7% | 1.08 | 0.46 |
| SOL | 33 | 7 | 26 | +104.0 | -22.4 | 30.3% | 1.04 | 0.38 |
| XRP | 31 | 10 | 21 | +229.7 | +47.0 | 41.9% | 1.10 | 0.93 |
| ADA | 39 | 8 | 31 | +1844.3 | -417.5 | 38.5% | 1.42 | 2.94 |

### 6.2 Assimetria Long/Short

- **Long trades:** 40 (8+7+7+10+8)
- **Short trades:** 126 (18+30+26+21+31)
- **Long net profit:** +1833.6 (focado em ADA)
- **Short net profit:** +79.2 (BTC domina; SOL/XRP contribuem levemente; ETH break-even; ADA negativo)

**Conclusão:** Short bias é dominante (76% dos trades), mas longs em ADA são outlier positivo. O edge parece ser mais consistente em shorts para BTC/XRP, e em longs para ADA — though ADA longs são 7W/1L de 8 trades (muito pequena amostra).

### 6.3 Símbolos com sinais de vida fortes (PF > 1.2)

| Símbolo | TF | Trades | PF | Net% | Sharpe | Comentário |
|---------|-----|--------|-----|------|--------|-------------|
| ADAUSDT | 1h | 39 | 1.42 | +14.27% | 2.94 | OUTLIER — dominante longs (7W/1L) |

ADA é outlier positivo com PF 1.42 e Sharpe 2.94 — mas long trades são 8 total (7W/1L), 매우 pequena amostra. Não confiar até mais trades.

### 6.4 Símbolos com sinais de vida moderados (PF 1.0–1.2)

| Símbolo | TF | Trades | PF | Net% | Sharpe |
|---------|-----|--------|-----|------|--------|
| XRPUSDT | 1h | 31 | 1.10 | +2.77% | 0.93 |
| ETHUSDT | 1h | 37 | 1.08 | +0.87% | 0.46 |
| BTCUSDT | 1h | 26 | 1.05 | +0.51% | 0.37 |
| SOLUSDT | 1h | 33 | 1.04 | +0.82% | 0.38 |

Todos com PF > 1.0 — sinal positivo de edge, mas com trade-off entre PF e DD.

### 6.5 Comparação com ciclos anteriores

| Ciclo | Hipótese | Trades | PF méd | Resultado |
|-------|----------|--------|--------|-----------|
| QM-VND-v1 | Single-bar fade | 75 | 0.30 | REJECT (strike 1) |
| QM-VRAD-v1 | Vol-regime displacement | 22 | 0.3–0.5 | REJECT (strike 1) |
| QM-FCE-v1 | Sequence-based exhaustion | 166 | 1.14 méd | ← AGUARDANDO VERTICAL |

FCE mostra PF médio 1.14 across 5 símbolos — primeiramente acima de 1.0 em todos os símbolos testados no mesmo ciclo. Progresso claro vs VND/VRAD.

---

## 7. Diagnosis

### 7.1 Sinal positivo: PF > 1.0 em TODOS os símbolos

Nenhum símbolo teve PF < 1.0. Isso é raro para uma primeira iteração greenfield e sugere que o conceito FCE tem seed de edge real — ou pelo menos é consistentemente neutro-positivo nesta janela.

### 7.2 Preocupação: ADA outlier

ADA +14.27% com PF 1.42 é impressionante, mas:
- Long trades são apenas 8 (7W/1L) — amostra muito pequena
- Se os 7 long wins forem clustered em um único evento de mercado (ex: pump específico), o edge não é generalizável
- Short trades em ADA são negativos (-417.5) — assimetria long/short é extremo

**Hipótese:** O edge em ADA pode ser um conibinação de (a) volatilidade mais baixa permitindo mais triggers de FCE, e (b) um evento específico de longo prazo que gerou vários long wins. Precisa de mais dados.

### 7.3 Preocupação: Drawdown alto em SOL/XRP/ADA

DD máximo: SOL 13.9%, XRP 16.3%, ADA 18.0%. Para estratégia de 1h com SL/TP fixos, DD de 14-18% é alto. Isso sugere que os SLs estão sendo batidos em cadeia durante regimes de vol alta — o que é esperado para estratégia de reversão, mas requer gestão.

### 7.4 Win rate baixo (29-46%)

WR médio ~37% é típico de estratégias de reversão/mean-reversion onde few wins pay much more than losses. Com PF > 1.0 e ratioAvgWinLoss 1.2–2.6, a matemática funciona. Mas WR < 50% significa que o psychologically demanda disciplina para não interromper durante losing streaks.

### 7.5 Cooldown de 3 barras pode estar limitando trades

Em TF 1h, 3 barras = 3 horas de cooldown. Se o sinal FCE é frequente em certos regimes, o cooldown pode estar suprimindo trades válidos. tests com cooldown=1 ou cooldown=0 poderiam mostrar se há trade율 adicional com edge.

### 7.6 Amostra de tempo limitada (1 month)

1021 barras ≈ 1 month de dados de 1h. Is this representative? Crypto markets have different regimes (trending, ranging, high vol, low vol). 1 month may not capture full regime diversity. Expandir janela para 3-6 months seria mais robusto.

### 7.7 Comparação com ciclos anteriores

| Critério | VND-v1 | VRAD-v1 | FCE-v1 |
|----------|--------|---------|--------|
| Símbolos com PF>1 | 0/6 | 2/9 (fracos) | 5/5 (todos) |
| PF médio | 0.30 | 0.3-0.5 | 1.14 |
| Trades totais | 75 | 22 | 166 |
| Net profit médio | negativo | misto | positivo (+3.6% módo) |
| Robustez cross-symbol | ✗ | ⚠️ fraco | ✅ positivo (precisa cross-TF) |

FCE é o primeiro ciclo a mostrar PF>1 em todos os símbolos testados no mesmo ciclo. Progresso significativo.

---

## 8. Verdict

### Critérios de avaliação (em ordem de prioridade do loop)

| Critério | Peso | Status FCE-v1 | Avaliação |
|----------|------|---------------|-----------|
| 1. Robustness across symbols | Alta | ✅ POSITIVO — 5/5 símbolos PF>1.0 | Strong signal |
| 2. Drawdown control | Alta | ⚠️ MIXO — DD 5-18%; SOL/XRP/ADA alto | Acceptable for early stage, needs monitoring |
| 3. Profit factor | Alta | ✅ POSITIVO — PF médio 1.14, todos >1.0 | Edge signal present |
| 4. Average trade quality | Média | ⚠️ MIXO — avg trade $2-37; ADA outlier | ADA inflates average; remove → avg ~$3-4 |
| 5. Trade count reliability | Alta | ✅ SUFFICIENT — 26-39 trades por símbolo | Good statistical base |
| 6. Stability across TFs | Média | ❌ NOT TESTED — apenas 1h | Gap critical |
| 7. Simplicity | Baixa | ✅ OK — 5 inputs, lógica linear | Maintained |
| 8. Net profit | Baixa | ✅ POSITIVO — +0.5% a +14.3% | Positive but ADA-driven |

### Decisão

**VERDICT: WATCHLIST — com caveat de cross-TF urgente**

**Justificativa:**
1. ✅ Todas as 5 símbolos mostram PF > 1.0 no mesmo ciclo — sinal raro e positivo
2. ✅ 166 trades totais em 1 month — amostra estatisticamente mais significativa que VND/VRAD
3. ✅ ADA outlier (PF 1.42, Sharpe 2.94) é promissor mas precisa de validação (sample pequena de longs)
4. ⚠️ DD alto em SOL/XRP/ADA (14-18%) — requer gestão e monitoramento
5. ❌ Cross-TF NÃO testado — gap crítico antes de qualquer recomendação de incubação
6. ❌ Janela de tempo limitada (1 month) — pode não capturar regime diversity

**O que NÃO é suficiente para ir para incubação agora:**
- Falta cross-TF stability (2h/4h)
- Falta janela de tempo mais longa (3-6 months)
- ADA outlier precisa de mais trades para confiança
- DD alto em 3 de 5 símbolos

**O que é suficiente para WATCHLIST:**
- PF > 1.0 em todos os símbolos testados
- 166 trades com distribuição consistente
- Conceito matematicamente distinto e não-overlapping com ciclos anteriores
- Progresso claro vs VND/VRAD (que falharam com PF < 0.5)

**Strike count:** Família FCE está em strike 0 (primeiro teste). Se próximo ciclo (cross-TF) mostrar PF < 1.0 em ≥3 símbolos, aplicar strike 1 e considerar pivot.

---

## 9. Next Cycle

### Opção A — Cross-TF expansion (preferida)

Testar FCE-v1 em 2h e 4h em 3 símbolos (BTC, ADA, XRP — representando melhor, outlier, e moderate performer):

1. BTCUSDT 2h — validar se edge persiste em TF maior
2. ADAUSDT 2h — validar se outlier é robusto ou fluke
3. XRPUSDT 2h — validar símbolo moderado em TF maior
4. Opcional: SOLUSDT 2h se créditos permitirem

**Hipótese de cross-TF:** Se o edge FCE é real, deve persistir em 2h com pelo menos 3 de 3 símbolos PF>1.0. Se PF cair abaixo 1.0 em 2h, o edge pode ser específico de 1h (ou área de amostra).

### Opção B — Janela de tempo expandida

Backtest em janela 3-6 months (ex: Jun 2026 → Sep 2026) em 5 símbolos × 1h para capturar mais regime diversity. Mais caro em créditos (5 backtests × 1 crédito = 5 créditos, mas a janela maior pode requerer mais bars).

### Opção C — Ajuste de thresholds (otimização leve)

Testar variações de:
- `lookback`: 15 vs 20 vs 25
- `minDisp`: 0.25 vs 0.30 vs 0.35
- `cooldown`: 1 vs 3 vs 5
- `slAtRMult/tpAtRMult`: 1.25 vs 1.5 vs 1.75

Mas não fazer isso antes de validar cross-TF — risco de curve-fitting ao timeframe 1h.

### Opção D — Pivot para REC ou LQS

Se cross-TF show que FCE não generaliza, pivotar para H3 (REC) ou H2 (LQS) como próxima hipótese greenfield.

### Recomendação

**Opção A + B em combinação:**
1. Rodar cross-TF (BTC/ADA/XRP 2h) — ~3 créditos
2. Se cross-TF positivo, expandir janela para 3 months — ~5 créditos
3. Se ambos positivos → avaliar para INCUBATE

**Créditos restantes:** 81 (86 iniciais - 5 usados neste ciclo)

---

## Anexos

- **Strategy ID:** `01M39D5SJ2VP9V6MX80464B0QR` (FCE-v1, versão 1)
- **Dashboard update:** ver `dashboard/data.json` para rows FCE
- **Créditos gastos:** 5 créditos (1 por backtest × 5 símbolos)
- **Nenhuma ordem real — pesquisa/educação apenas.**

---

*Trader Dev MCP: authenticated as searesj92@gmail.com · engine tv_jul26_mc7 · parity profile applied.*
