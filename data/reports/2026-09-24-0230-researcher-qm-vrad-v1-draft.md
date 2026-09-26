# Quant Mathematician Cycle Report
## Cycle: QM-VRAD-v1 (Volatility-Regime Adjusted Displacement)
## Date: 2026-09-24

---

## 1. Hipóteses Geradas (3 greenfield)

### H1 — VRAD: Volatility-Regime Adjusted Displacement

**Ineficiência alvo:** O mesmo deslocamento de preço (movimento absoluto) tem significado diferente dependendo do regime de volatilidade recente. Em regime de volatilidade ELEVADA, um deslocamento grande com volume acima da média é sinal de breakout genuíno (continuação). Em regime de volatilidade COMPRIMIDA, um deslocamento grande com volume abaixo da média é sinal de fakeout/stop-run (reversão). A chave é que a volatilidade normaliza o deslocamento e o regime classifica a interpretação.

**Matemática central:**
- `atr = ta.atr(14)` — volatilidade de curto prazo
- `atr_sma = ta.sma(atr, 50)` — baseline de volatilidade
- `volRegime = atr / atr_sma` — regime: >1 vol alta, <1 vol baixa
- `disp = math.abs(close - open) / atr` — deslocamento em unidades de ATR (normalizado)
- `volNorm = volume / ta.sma(volume, 20)` — volume normalizado
- **Long momentum:** `volRegime > 1.15 AND disp > 0.75 AND volNorm > 1.25 AND close > open AND close > close[1]`
- **Short momentum:** `volRegime > 1.15 AND disp > 0.75 AND volNorm > 1.25 AND close < open AND close < close[1]`
- **Long reversão:** `volRegime < 0.85 AND disp > 1.25 AND volNorm < 0.75 AND close < open AND close > close[1]`
- **Short reversão:** `volRegime < 0.85 AND disp > 1.25 AND volNorm < 0.75 AND close > open AND close < close[1]`
- SL: 2.5 ATR | TP: 1.0 ATR ou saída por sinal oposto

**Por que na crypto:** Mercados 24/7 sem gaps → deslocamentos são detectáveis. Volatilidade varia dramaticamente entre regimes (bull, chop, panic). A mesma magnitude de candle tem interpretação diferente — isso é a ineficiência.

**Breaking regime:** trend monótono puro (sem pullbacks); vol extremamente baixa (sem líquido para ser stop-ran); horário de baixa liquidez (semana, fim de semana).

---

### H2 — RCE: Range Compression Energy

**Ineficiência alvo:** Após período de compressão de range (ATR em percentil baixo), o mercado "coil" acumula energia. O primeiro breakout com confirmação de volume tende a ter maior sucesso que breakouts de mercados já expandidos. A ineficiência é que o mercado não precifica adequadamente o estado de compressão como precursor de movimento.

**Matemática central:**
- `atrPct = ta.percentrank(atr(14), 50)` — ATR em percentil
- `compression = atrPct < 30` — regime comprimido (30% dos últimos 50 dias)
- `breakoutRange = math.abs(close - close[1]) / atr(14) > 0.8`
- `volumeConfirm = volume > ta.sma(volume, 20) * 1.3`
- `direction = close > open ? 1 : -1`
- Entrada: `compression[1] AND breakoutRange AND volumeConfirm` na direção do candle

**Por que na crypto:** Mercados de crypto passam muito tempo em consolidação; compressão é comum; breakouts de compression são frequentes.

**Breaking regime:** mercado já em tendência forte (compressão não se aplica); compression sem volume (fake compression).

---

### H3 — AVE: Asymmetric Volume-Energy Divergence

**Ineficiência alvo:** Quando dois candles consecutivos têm deslocamento similar em ATR mas volumes opostos (um acima da média, outro abaixo), há divergência de energia que precede reversão. O candle com volume alto "é real", o com volume baixo "é fraco" — a combinação sugere que o mercado está dividido e o lado fraco perde.

**Matemática central:**
- `disp1 = math.abs(close[1] - open[1]) / atr(14)`
- `disp2 = math.abs(close - open) / atr(14)`
- `vol1 = volume[1] / ta.sma(volume, 20)`
- `vol2 = volume / ta.sma(volume, 20)`
- `divergent = disp1 > 0.6 AND disp2 > 0.6 AND vol1 > 1.3 AND vol2 < 0.7`
- `direction = close[1] > open[1] ? -1 : 1` (follow o lado forte)
- Entrada na direção do candle de volume alto

**Por que na crypto:** Fragmentação de volume entre exchanges; candles de volume alto em uma exchange podem não refletir o mercado completo; divergência de energia é detectável.

**Breaking regime:** tendência forte unidirecional (ambos os candles no mesmo sentido com volume alto); mercado muito illiquid (volumes irreais).

---

## 2. Hipótese Selecionada: VRAD (H1)

**Motivo da seleção:**
1. **Dupla entrada:** momentum + reversão → mais chances de trades que H2/H3 (que são single-direction)
2. **Normalização por ATR:** adaptável entre símbolos (BTC move 2%, SOL move 8%) e timeframes
3. **Regime classifier:** insight matemático genuíno — o mesmo evento tem interpretação diferente por regime
4. **Contrasta com ciclos anteriores:** VPA usou threshold fixo (%) sem normalização de vol; VRAD usa ATR e regime classifier
5. **Testabilidade:** condições claras, sem ambiguidade

**Risco:** Se os thresholds forem muito estritos → 0 trades (modo VPA/MSE). Solução: usar percentis dinâmicos onde possível e começar com thresholds moderados.

---

## 3. Trading Rules

### Entradas Long
| Condição | Valor |
|---|---|
| Regime vol | `atr/atr_sma > 1.15` |
| Deslocamento | `\|close-open\|/atr > 0.75` |
| Volume | `volume/sma(vol,20) > 1.25` |
| Direção | `close > open AND close > close[1]` |

### Entradas Short
| Condição | Valor |
|---|---|
| Regime vol | `atr/atr_sma > 1.15` |
| Deslocamento | `\|close-open\|/atr > 0.75` |
| Volume | `volume/sma(vol,20) > 1.25` |
| Direção | `close < open AND close < close[1]` |

### Entradas Long (Reversão)
| Condição | Valor |
|---|---|
| Regime vol | `atr/atr_sma < 0.85` |
| Deslocamento | `\|close-open\|/atr > 1.25` |
| Volume | `volume/sma(vol,20) < 0.75` |
| Direção | `close < open AND close > close[1]` |

### Entradas Short (Reversão)
| Condição | Valor |
|---|---|
| Regime vol | `atr/atr_sma < 0.85` |
| Deslocamento | `\|close-open\|/atr > 1.25` |
| Volume | `volume/sma(vol,20) < 0.75` |
| Direção | `close > open AND close < close[1]` |

### Exits
- **SL:** 2.5 ATR da entrada (absoluto)
- **TP:** 1.0 ATR da entrada (absoluto)
- **Cooldown:** 5 barras após saída antes de nova entrada na mesma direção
- **Invalidação:** se o candle de entrada não fecha no sentido da entrada dentro de 2 barras → sair

### Filtros
- Sem trade se `atr < 0.0001` (vol essencialmente zero)
- Max 1 posição por direção (pyramiding=1)

---

## 4. Pine Script

```pine
//@version=6
strategy("QM-VRAD-v1 — Volatility-Regime Adjusted Displacement",
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
atrLen    = input.int(14, "ATR length")
atrSmaLen = input.int(50, "ATR SMA regime length")
volSmaLen = input.int(20, "Volume SMA length")
dispThreshMom = input.float(0.75, "Displacement threshold (momentum)")
dispThreshRev = input.float(1.25, "Displacement threshold (reversion)")
volRegimeHigh = input.float(1.15, "Vol regime high threshold")
volRegimeLow  = input.float(0.85, "Vol regime low threshold")
volNormHigh   = input.float(1.25, "Volume norm high threshold")
volNormLow    = input.float(0.75, "Volume norm low threshold")
slAtrVert    = input.float(2.5, "SL in ATR multiples")
tpAtrVert    = input.float(1.0, "TP in ATR multiples")
cooldown     = input.int(5, "Cooldown bars after exit")

// ── Indicators ──────────────────────────────────────────
atr = ta.atr(atrLen)
atr_sma = ta.sma(atr, atrSmaLen)
vol_sma = ta.sma(volume, volSmaLen)
volRegime = atr / atr_sma
disp = math.abs(close - open) / atr
volNorm = volume / vol_sma

// ── Direction ───────────────────────────────────────────
bullishBody = close > open
bearishBody = close < open
bullishClose = close > close[1]
bearishClose = close < close[1]

// ── Entry Conditions ────────────────────────────────────
// Momentum Long
momLongCond = volRegime > volRegimeHigh and disp > dispThreshMom and volNorm > volNormHigh and bullishBody and bullishClose
// Momentum Short
momShortCond = volRegime > volRegimeHigh and disp > dispThreshMom and volNorm > volNormHigh and bearishBody and bearishClose
// Reversion Long (fade bearish fakeout)
revLongCond = volRegime < volRegimeLow and disp > dispThreshRev and volNorm < volNormLow and bearishBody and bullishClose
// Reversion Short (fade bullish fakeout)
revShortCond = volRegime < volRegimeLow and disp > dispThreshRev and volNorm < volNormLow and bullishBody and bearishClose

// ── Cooldown ────────────────────────────────────────────
var int momLongCD = 0
var int momShortCD = 0
var int revLongCD = 0
var int revShortCD = 0

momLongCD := momLongCD > 0 ? momLongCD - 1 : 0
momShortCD := momShortCD > 0 ? momShortCD - 1 : 0
revLongCD := revLongCD > 0 ? revLongCD - 1 : 0
revShortCD := revShortCD > 0 ? revShortCD - 1 : 0

// ── Entries ─────────────────────────────────────────────
if momLongCond and momLongCD == 0 and strategy.position_size == 0
    strategy.entry("L", strategy.long)

if momShortCond and momShortCD == 0 and strategy.position_size == 0
    strategy.entry("S", strategy.short)

if revLongCond and revLongCD == 0 and strategy.position_size == 0
    strategy.entry("RL", strategy.long)

if revShortCond and revShortCD == 0 and strategy.position_size == 0
    strategy.entry("RS", strategy.short)

// ── Exits (SL/TP per entry) ─────────────────────────────
atrSL = atr * slAtrVert
atrTP = atr * tpAtrVert

// Long exits
if strategy.position_size > 0
    strategy.exit("L_exit", from_entry="L", stop=close - atrSL, limit=close + atrTP)
    strategy.exit("RL_exit", from_entry="RL", stop=close - atrSL, limit=close + atrTP)

// Short exits
if strategy.position_size < 0
    strategy.exit("S_exit", from_entry="S", stop=close + atrSL, limit=close - atrTP)
    strategy.exit("RS_exit", from_entry="RS", stop=close + atrSL, limit=close - atrTP)

// ── Cooldown reset on exit ──────────────────────────────
if strategy.position_size == 0 and strategy.closedtrades > 0
    // cooldown is tracked per-entry via var ints above
    // reset all cooldown on any close
    momLongCD := cooldown
    momShortCD := cooldown
    revLongCD := cooldown
    revShortCD := cooldown

// ── Plots (debug) ───────────────────────────────────────
plot(atr_sma, "ATR SMA", color=color.gray, linewidth=1)
plot(disp * 10, "Disp x10", color=disp > dispThreshMom ? color.green : color.red, linewidth=1)
bgcolor(momLongCond ? color.new(color.green, 90) : revLongCond ? color.new(color.blue, 90) : na, title="Long signal")
bgcolor(momShortCond ? color.new(color.red, 90) : revShortCond ? color.new(color.orange, 90) : na, title="Short signal")
```

---

## 5. Backtest Matrix

| # | Symbol | Timeframe | Strategy ID |
|---|---|---|---|
| 1 | BTCUSDT | 1h | QM-VRAD-v1 |
| 2 | BTCUSDT | 2h | QM-VRAD-v1 |
| 3 | BTCUSDT | 4h | QM-VRAD-v1 |
| 4 | ETHUSDT | 1h | QM-VRAD-v1 |
| 5 | ETHUSDT | 2h | QM-VRAD-v1 |
| 6 | ETHUSDT | 4h | QM-VRAD-v1 |
| 7 | SOLUSDT | 1h | QM-VRAD-v1 |
| 8 | SOLUSDT | 2h | QM-VRAD-v1 |
| 9 | SOLUSDT | 4h | QM-VRAD-v1 |
| 10 | XRPUSDT | 1h | QM-VRAD-v1 |
| 11 | XRPUSDT | 2h | QM-VRAD-v1 |
| 12 | XRPUSDT | 4h | QM-VRAD-v1 |
| 13 | BNBUSDT | 1h | QM-VRAD-v1 |
| 14 | BNBUSDT | 2h | QM-VRAD-v1 |
| 15 | BNBUSDT | 4h | QM-VRAD-v1 |
| 16 | ADAUSDT | 1h | QM-VRAD-v1 |
| 17 | ADAUSDT | 2h | QM-VRAD-v1 |
| 18 | ADAUSDT | 4h | QM-VRAD-v1 |

Total: 18 backtests × 1 credit = 18 credits estimados.

---

## 6. Results (pending)

*Em branco — aguardando execução do backtest.*

---

## 7. Diagnosis (pending)

*Em branco — aguardando resultados.*

---

## 8. Verdict (pending)

*Em branco — aguardando resultados.*

---

## 9. Next Cycle

- Se PF ≥ 1.3 em ≥ 3 símbolos, expandir para mais símbolos + más TFs (15m, 30m)
- Se PF entre 1.0–1.3, ajustar thresholds (dispThresh, volNorm) e re-testar
- Se 0 trades em ≥ 5 símbolos, pivotar para RCE (H2) com thresholds mais brandos
- Se max DD > 30%, ajustar SL multiplier (atenuar risco)

---

**Créditos disponíveis:** 166 (free tier)
**Verificação de créditos:** confirmada via `get_credits`
**Next step:** criar estratégia + submeter ao backtest em lote

---

*Nenhuma ordem real — pesquisa/educação apenas.*
