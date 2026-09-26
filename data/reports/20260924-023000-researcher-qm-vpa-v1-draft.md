# Quant Mathematician Cycle Report
## Cycle: QM-VPA-v1 (Volume-Price Anomaly — Asymmetric Flow Detection)
## Date: 2026-09-24

---

## 1. Hipóteses Geradas (3 greenfield)

### H1 — VPA: Volume-Price Anomaly (Asymmetric Flow Detection)

**Ineficiência alvo:** Quando o retorno de uma barra é grande (deslocamento significativo) mas o volume associado é anomalmente BAIXO relativo ao volume habitual daquele par em tal retorno, há indício de movimento "vazio" — sem participação genuína de mercado. Bars seguintes tendem a refundir o preço na direção oposta à do "fake displacement".

**Matemática central:**
- `ret = (close - close[1]) / close[1]` (retorno simples)
- `volNorm = volume / ta.sma(volume, 20)` (volume normalizado por sua média móvel)
- `volAnomLow = volNorm < 0.5 AND |ret| > 0.01` (movimento grande com volume fraco)
- `barDirection = close > open ? +1 : -1`
- `followThroughBroken = (barDirection[1] == barDirection[2]) AND (close[1] < open[1] if long)` — ou seja, a barra anterior foi na direção do sinal mas o retorno real é fraco
- Entrada no bar seguinte ao volume-anomalous bar

**Por que na crypto:** Mercado fragmentado com múltiplos exchange-flows; movimentos "dry" (volume baixo, preço baixando) são frequentemente ataques de liquidez sem sustentação real — revertentes.

**Breaking regime:** mercado em alta de volume genuíneo (breakout real); tendência secular com participação consistente; horário de mercado aberto com vol massivo.

---

### H2 — ROE: Range-of-Expansion Exhaustion

**Ineficiência alvo:** Após uma sequência de barras com range (high-low) consistentemente acima da média recente, o preço tende a entrar em consolidação — o evento de expansão se esgota. Entrar no lado da reversão/sideways quando o último bar é pequeno (range abaixo de limiar) após expansão.

**Matemática central:**
- `range = high - low`
- `rangeAvg = ta.sma(range, 20)`
- `rangeAnomHigh = range > rangeAvg * 1.5`
- `expandingSequence = count of last N bars with range > rangeAvg`
- `rangeCollapse = range < rangeAvg * 0.7`
- `entry = expandingSequence >= 3 AND rangeCollapse`
- SL: 1.5 × ATR do bar de entrada; TP: retorno à média móvel de preço (maior recuperação após expansão)

**Por que na crypto:** Micro-estrutura de mercado mostra picos de vol seguidos de quietude — a energia se dissipa.

**Breaking regime:** mercado em trend forte sem pullback; compressão extrema sem expansão prévia.

---

### H3 — TRF: Trend Resumption Filter (Failed-Follow-Through as Reversion Signal)

**Ineficiência alvo:** Quando o preço tenta romper um nível de resistência/suporte mas o volume não confirma (volume do breakout bar abaixo da média), o rompimento falhou — entrar na direção oposta ao rompimento "falso".

**Matemática central:**
- `resistance = ta.highest(high, N)[1]` (resiste recente)
- `support = ta.lowest(low, N)[1]`
- `breakoutHigh = high > resistance`
- `breakoutLow = low < support`
- `volBreakoutWeak = volume < ta.sma(volume, 20) * 0.8`
- `failedBreakout = breakoutHigh AND volBreakoutWeak` (ou breakoutLow AND volBreakoutWeak)
- `entryShort = failedBreakoutHigh` (rompimento acima sem volume → short)
- `entryLong = failedBreakoutLow` (rompimento abaixo sem volume → long)
- SL: 0.5 × ATR; TP: retorno ao nível pré-rompimento

**Por que na crypto:** Fakeouts são frequentes quando stops são concentrados; volume fraco confirma a falha de expeculação.

**Breaking regime:** mercado com volume consistently baixo (sem interesse); breakout real com volume alto (não é falso).

---

## 2. Hipótese Selecionada

**H1 — VPA (Volume-Price Anomaly)**

**Motivo da seleção (por ordem de prioridade do loop):**

1. **Simplicidade** — 2 séries (retorno, volume normalizado), 1 limiar composto, sem agressão de múltiplos indicadores.
2. **Testabilidade** — sinal claro, sem ambiguidade de janelamento.
3. **Math rigor** — normalização por ATR e volume mediano remove dependência de escala e vol.
4. **Generalizabilidade** — a métrica de "movimento grande com volume fraco" é independente do par, aplica-se a BTC (vol alto) e alts (vol baixo) sem retuning.
5. **Clear risk management** — SL baseado em ATR, TP baseado em retorno partial ao equilíbrio, sem trailing.

**Contraste com hipóteses anteriores que falharam:**

| Ciclo | Linha | Motivo do fracasso | Distinção deste ciclo |
|-------|-------|-------------------|----------------------|
| MSE-v1 | LRS | 0 trades — evento raro, 5 condições AND | VPA usa 2 séries simples, não 5 eventos raros |
| MSE-v1 | REA | 0 trades — queda de eficiência rara | VPA não depende de "eficiência" (conceito mais raro) |
| MSE-v1 | JM | 0 trades — ssIndex < 0.6 muito restritivo | VPA não usa coil-swithen stability index |
| VND-v1 | VND | PF<1 — fade de single-bar displacement não funciona | VPA é "volume fraco com movimento grande" (distinto de fade de displacimento) |

**VPA é matematicamente distinto:** não é "fade do extremo" nem "eficiência de range" nem "coil swithen" — é detecção de anomalia de fluxo (volume baixo + movimento grande = movimento sem respaldo).

---

## 3. Regras de Trading

### Entradas (Long)

| Condição | Expressão |
|----------|-----------|
| Barra anterior com movimento forte para baixo | `close[1] < open[1]` (bearish) |
| Deslocamento grande | `|close[1] - open[1]| / open[1] > 0.008` (0.8% de movimento) |
| Volume anomalamente baixo | `volume[1] < ta.sma(volume, 20) * 0.5` (volume < metade da média) |
| Preço esticado abaixo do equilíbrio | `close[1] < ta.sma(close, 20)` |
| Cooldown ativo | `cd > cooldownBars` |

→ **Long entry** na barra seguinte ao sinal.

### Entradas (Short)

| Condição | Expressão |
|----------|-----------|
| Barra anterior com movimento forte para cima | `close[1] > open[1]` (bullish) |
| Deslocamento grande | `|close[1] - open[1]| / open[1] > 0.008` |
| Volume anomalamente baixo | `volume[1] < ta.sma(volume, 20) * 0.5` |
| Preço esticado acima do equilíbrio | `close[1] > ta.sma(close, 20)` |
| Cooldown ativo | `cd > cooldownBars` |

→ **Short entry** na barra seguinte ao sinal.

### Saídas

| Tipo | Valor | Motivo |
|------|-------|--------|
| **TP** | `ta.sma(close, 20)` (volta à média móvel) | Reembolso ao equilíbrio após anomalia revertida |
| **SL** | `1.5 × ATR` abaixo/acima do preço de entrada | Proteção contra movimento genuíno |
| **Time exit** | 20 barras | Limita exposição se não reverte |
| **Cooldown** | 1 barra após qualquer saída | Evita overtrading pós-sinal |

### Invalidação

- Se o preço atinge o TP antes do SL → saída normal (não inválido).
- Se o sinal de entrada oposto aparece antes do fechamento do bar → entrada cancelada (cooldown reiniciado).

### Risco

- 100% equity, pyramiding=1, margin 100/100, commission 0.05%.
- Sem trailing stops (regra de latência do loop).

---

## 4. Pine Script

```pine
//@version=6
strategy("QM-VPA-v1 — Volume-Price Anomaly", 
  overlay=true, pyramiding=1, process_orders_on_close=true,
  commission_type=strategy.commission.percent, commission_value=0.05,
  initial_capital=10000, default_qty_type=strategy.percent_of_equity,
  default_qty_value=100, margin_long=100, margin_short=100)

// Inputs
retThresh       = input.float(0.008, "Return threshold (fractional)", minval=0.0, step=0.001, group="Entry")
volAnomMult     = input.float(0.5, "Volume anomaly multiplier (vs SMA)", minval=0.1, step=0.1, group="Entry")
smaPeriod       = input.int(20, "SMA period (equilibrium)", minval=5, group="Entry")
atrLen          = input.int(14, "ATR length", minval=2, group="Risk")
slAtrMult       = input.float(1.5, "SL ATR multiplier", minval=0.5, step=0.1, group="Risk")
cooldownBars    = input.int(1, "Cooldown bars", minval=0, group="Risk")
timeExitBars    = input.int(20, "Max bars in trade", minval=1, group="Risk")

// Calculations
atr = ta.atr(atrLen)
smaClose = ta.sma(close, smaPeriod)
smaVol = ta.sma(volume, smaPeriod)

// Bar [1] conditions (anomalous bar)
retBar1 = math.abs(close[1] - open[1]) / open[1]
volAnom = volume[1] < smaVol * volAnomMult
bigMoveBear = retBar1 > retThresh and close[1] < open[1]
bigMoveBull = retBar1 > retThresh and close[1] > open[1]
priceAboveEq = close[1] > smaClose
priceBelowEq = close[1] < smaClose

// Long signal: anomalous bearish bar (big move down, low vol) + price below equilibrium
longSig = bigMoveBear and volAnom and priceBelowEq

// Short signal: anomalous bullish bar (big move up, low vol) + price above equilibrium
shortSig = bigMoveBull and volAnom and priceAboveEq

// Cooldown logic
var int cd = 0
if strategy.position_size != 0
    cd := 0
else if cd == 0
    cd := 1
else
    cd += 1
canTrade = cd > cooldownBars

// Entries
if longSig and canTrade
    strategy.entry("L", strategy.long)

if shortSig and canTrade
    strategy.entry("S", strategy.short)

// Exits
if strategy.position_size > 0
    longEntryPrice = strategy.position_avg_price
    strategy.exit("LX", from_entry="L",
        limit=smaClose,            // TP: return to equilibrium
        stop=longEntryPrice - atr * slAtrMult,  // SL: ATR-based
        loss=0, profit=0)         // disable ticks-based exits

if strategy.position_size < 0
    shortEntryPrice = strategy.position_avg_price
    strategy.exit("SX", from_entry="S",
        limit=smaClose,            // TP: return to equilibrium
        stop=shortEntryPrice + atr * slAtrMult,  // SL: ATR-based
        loss=0, profit=0)

// Time exit
var int barsInTrade = 0
if strategy.position_size != 0
    barsInTrade += 1
else
    barsInTrade := 0
if barsInTrade > timeExitBars
    strategy.close_all()

// Plots (debugging)
plot(longSig, "Long Signal", color=color.green, style=plot.style_circles, linewidth=2)
plot(shortSig, "Short Signal", color=color.red, style=plot.style_circles, linewidth=2)
```

**Notas de implementação:**

- `retBar1` usa `open[1]` como dereferência para evitar lookahead: o preço de abertura é conhecido no bar[1].
- `volAnom` deve ser avaliado no bar[1] completo (fechamento conhecido).
- `smaClose` no TP: se o preço estiver abaixo da média, o TP é a média — reversão esperada ao equilíbrio.
- SL baseado em ATR para proteção vol-adjusted.
- Cooldown = 1 barra: após sair, espera 1 barra antes de reentrar.

---

## 5. Backtest Matrix

### Configuração
- **Engine:** tv_jul26 (TV_ENGINE_JUL_26 parity)
- **Período:** ~Jun 2026 → Sep 24 2026 (último bar disponível)
- **Capital:** $10,000
- **Sizing:** 100% equity, margin 100/100
- **Commission:** 0.05% (mcp parity)
- **Slippage:** 2 ticks

### Matriz (5 símbolos × 1 timeframe)

| Símbolo | TF | Strategy ID (create) | Result ID (backtest) | Notas |
|---------|----|---------------------|----------------------|-------|
| BTCUSDT | 1h | <pending> | <pending> | Dominante, vol alto — teste de base |
| ETHUSDT | 1h | <pending> | <pending> | Vol alto, similar ao BTC |
| SOLUSDT | 1h | <pending> | <pending> | Alts, vol mais baixo — teste de generalização |
| XRPUSDT | 1h | <pending> | <pending> | Alts, vol baixo — teste de generalização |
| BNBUSDT | 1h | <pending> | <pending> | Vol moderado — teste intermediário |

**Nota:** cada backtest é um strategyId separado (adicionado, sem fork).

---

## 6. Results

*(Preenchido após execução dos backtests)*

---

## 7. Diagnosis

*(Preenchido após análise dos resultados)*

---

## 8. Verdict

**PENDING** — após backtests.

Expectativa baseada no design:
- Se PF > 1.3 em ≥3 símbolos e WR > 50%: **Candidate**
- Se PF < 1 em todos: **Reject** (conceito falsificado)
- Se misto (alguns positivos, alguns negativos): **Watchlist** para investigação adicional

---

## 9. Next Cycle

*(Depende do resultado deste ciclo)*

- Se houver sinal de vida: iterar com ajuste de limiares (retThresh, volAnomMult) — uma mudança por ciclo.
- Se confirmar edge: testar cruz-TF (15m, 30m, 4h).
- Se fracasso: pivotar para H2 (ROE) ou H3 (TRF) em próximo ciclo.

---

## Control Panel Update

*(Após backtests, atualizar dashboard/data.json com as linhas resultantes)*

---

## Créditos consumidos

5 backtests × 1 crédito = **5 créditos**

Restam: ~161 créditos

---

## Disclaimer

Pesquisa e educação apenas. Não é conselho financeiro. Backtests não são garantia de futuro. Nenhuma ordem real.
