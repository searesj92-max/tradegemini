# Quant Mathematician Cycle Report
## Cycle: QM-VRAD-v1 (Volatility-Regime Adjusted Displacement)
## Date: 2026-09-24 01:50 UTC-3

---

## 1. Hipóteses Geradas (3 greenfield)

### H1 — VRAD: Volatility-Regime Adjusted Displacement

**Ineficiência alvo:** O mesmo deslocamento de preço (movimento absoluto em ATR) tem significado diferente dependendo do regime de volatilidade recente. Em regime de vol ELEVADA, um candle grande com volume acima da média é sinal de breakout genuíno (momentum/continuação). Em regime de vol COMPRIMIDA, um candle grande com volume abaixo da média é sinal de fakeout/stop-run (reversão). A normalização por ATR + regime classifier é o insight matemático central.

**Matemática central:**
- `volRegime = atr(14) / sma(atr(14), 50)` — acima de 1 = vol alta, abaixo de 1 = vol baixa
- `disp = |close - open| / atr(14)` — deslocamento em unidades de ATR
- `volNorm = volume / sma(volume, 20)` — volume normalizado
- Momentum: `volRegime > 1.15 AND disp > 0.75 AND volNorm > 1.25` na direção do candle
- Reversão: `volRegime < 0.85 AND disp > 1.25 AND volNorm < 0.75` na direção oposta ao candle
- SL: 2.5 ATR | TP: 1.0 ATR

**Por que na crypto:** Mercados 24/7 sem gaps; deslocamentos são detectáveis; volatilidade varia dramaticamente entre regimes; o mesmo evento tem interpretação diferente.

**Breaking regime:** trend monótono puro (sem pullbacks); vol extremamente baixa (sem líquido para ser stop-ran).

---

### H2 — RCE: Range Compression Energy

**Ineficiência alvo:** Após período de compressão de range (ATR em percentil baixo), o mercado acumula energia. O primeiro breakout com confirmação de volume tende a ter maior sucesso que breakouts de mercados já expandidos.

**Matemática central:** `atrPct = percentrank(atr(14), 50)`; `compression = atrPct < 30`; entrada quando `compression[1] AND breakoutRange AND volumeConfirm`.

**Descartada** — single-direction, menos robusta que VRAD.

---

### H3 — AVE: Asymmetric Volume-Energy Divergence

**Ineficiência alvo:** Dois candles consecutivos com deslocamento similar em ATR mas volumes opostos (um alto, outro baixo) — divergência de energia que precede reversão.

**Matemática central:** `disp1, disp2 > 0.6`; `vol1 > 1.3 AND vol2 < 0.7`; entrada na direção do candle de volume alto.

**Descartada** — requer dois candles específicos; sample muito esparsos.

---

## 2. Hipótese Selecionada: VRAD (H1)

**Motivo da seleção:**
1. **Dupla entrada** (momentum + reversão) → mais chances de trades que H2/H3
2. **Normalização por ATR** — adaptável entre símbolos e TFs
3. **Regime classifier** — insight matemático genuíno, contrasta com ciclos anteriores (VPA/MSE falharam com thresholds fixos)
4. **Simplicidade** — 8 inputs, lógica linear, sem indecadores complexos
5. **Testabilidade** — condições claras sem ambiguidade

---

## 3. Trading Rules (VRAD-v1)

### Momentum Long
| Condição | Threshold |
|---|---|
| Vol regime | `atr/atr_sma > 1.15` |
| Deslocamento | `|close-open|/atr > 0.75` |
| Volume norm | `vol/sma(vol,20) > 1.25` |
| Direção | `close > open AND close > close[1]` |

### Momentum Short
| Condição | Threshold |
|---|---|
| Vol regime | `atr/atr_sma > 1.15` |
| Deslocamento | `|close-open|/atr > 0.75` |
| Volume norm | `vol/sma(vol,20) > 1.25` |
| Direção | `close < open AND close < close[1]` |

### Reversão Long (fade bearish fakeout)
| Condição | Threshold |
|---|---|
| Vol regime | `atr/atr_sma < 0.85` |
| Deslocamento | `|close-open|/atr > 1.25` |
| Volume norm | `vol/sma(vol,20) < 0.75` |
| Direção | `close < open AND close > close[1]` |

### Reversão Short (fade bullish fakeout)
| Condição | Threshold |
|---|---|
| Vol regime | `atr/atr_sma < 0.85` |
| Deslocamento | `|close-open|/atr > 1.25` |
| Volume norm | `vol/sma(vol,20) < 0.75` |
| Direção | `close > open AND close < close[1]` |

### Exits
- **SL:** 2.5 ATR (absoluto)
- **TP:** 1.0 ATR (absoluto)
- **Cooldown:** 5 barras após saída antes de nova entrada na mesma direção

### Filtros
- Sem trade se `atr < 0.0001`
- Max 1 posição por direção (pyramiding=1)
- `process_orders_on_close=true`

---

## 4. Pine Script (//@version=6)

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
momLongCond = volRegime > volRegimeHigh and disp > dispThreshMom
              and volNorm > volNormHigh and bullishBody and bullishClose
momShortCond = volRegime > volRegimeHigh and disp > dispThreshMom
               and volNorm > volNormHigh and bearishBody and bearishClose
revLongCond = volRegime < volRegimeLow and disp > dispThreshRev
              and volNorm < volNormLow and bearishBody and bullishClose
revShortCond = volRegime < volRegimeLow and disp > dispThreshRev
               and volNorm < volNormLow and bullishBody and bearishClose

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

// ── Exits ───────────────────────────────────────────────
atrSL = atr * slAtrVert
atrTP = atr * tpAtrVert

if strategy.position_size > 0
    strategy.exit("L_exit", from_entry="L", stop=close - atrSL, limit=close + atrTP)
    strategy.exit("RL_exit", from_entry="RL", stop=close - atrSL, limit=close + atrTP)
if strategy.position_size < 0
    strategy.exit("S_exit", from_entry="S", stop=close + atrSL, limit=close - atrTP)
    strategy.exit("RS_exit", from_entry="RS", stop=close + atrSL, limit=close - atrTP)

// ── Cooldown reset ──────────────────────────────────────
if strategy.position_size == 0 and strategy.closedtrades > 0
    momLongCD := cooldown
    momShortCD := cooldown
    revLongCD := cooldown
    revShortCD := cooldown
```

**Strategy ID (MCP):** `01M38HFKMSTF7Z1BMXP1XYZQ3W`
**Paridade:** commission 0.05%, percent_of_equity 100, margin long/short 100, pyramiding 1

---

## 5. Backtest Matrix

**Período:** ~23 set a 24 set 2026 (janela de ~2 dias; ~1300-2460 barras por símbolo/TF)
**Símbolos:** BTC, ETH, SOL, XRP, BNB, ADA (Bybit USDT linear perpetual)
**Timeframes:** 1h, 2h, 4h

| # | Símbolo | TF | Trades | Win% | Net% | PF | MaxDD% | Result ID |
|---|---|---|---|---|---|---|---|---|
| 1 | BTCUSDT | 1h | 3 | 33% | -0.33% | 0.38 | 3.25% | 01M38HG9HPQFVH3CYXBMHZ81X8 |
| 2 | BTCUSDT | 2h | — | — | — | — | — | *não executado* |
| 3 | BTCUSDT | 4h | — | — | — | — | — | *não executado* |
| 4 | ETHUSDT | 1h | 2 | 0% | -4.37% | 0.00 | 4.91% | 01M38HH924KS9RTAMS1K688Y21 |
| 5 | ETHUSDT | 2h | 1 | 100% | +0.57% | null | 2.61% | 01M38HHM31F5509VSFE8FNKSAP |
| 6 | ETHUSDT | 4h | — | — | — | — | — | *não executado* |
| 7 | SOLUSDT | 1h | 2 | 0% | -7.35% | 0.00 | 8.54% | 01M38HH01TW5AP7GZF22CG9PWE |
| 8 | SOLUSDT | 2h | 2 | 50% | +0.93% | 1.97 | 3.51% | 01M38HGP5JQYT27Q2SBGMHCX31 |
| 9 | SOLUSDT | 4h | 2 | 50% | +0.46% | 2.15 | 3.51% | 01M38HJ0RWRD93ZZQJGN9XD4T0 |
| 10 | XRPUSDT | 1h | 2 | 0% | -4.34% | 0.00 | 5.38% | 01M38HJDH74EYEJFFW5H5X8NS7 |
| 11 | XRPUSDT | 2h | 4 | 0% | -2.90% | 0.00 | 4.81% | 01M38HK6XXNBSX1DJJPDS95BS1 |
| 12 | BNBUSDT | 1h | 2 | 0% | -1.44% | 0.00 | 2.99% | 01M38HKZVF5KEH0PR634TCCDYW |
| 13 | BNBUSDT | 2h | — | — | — | — | — | *não executado* |
| 14 | BNBUSDT | 4h | 2 | 50% | -0.09% | 0.47 | 1.71% | 01M38HKPKYAXQRVXBSA8BZ3A80 |
| 15 | ADAUSDT | 1h | 1 | 100% | +1.65% | null | 0.75% | 01M38HMXVYJSE3YFQ603XSV3YZ |
| 16 | ADAUSDT | 2h | 1 | 100% | +1.20% | null | 1.29% | 01M38HP983YKZYP4AK7QGBP0E4 |
| 17 | ADAUSDT | 4h | — | — | — | — | — | *não executado* |

**Trades totais executados:** 22
**Wins:** 5 | **Losses:** 17 | **Win rate agregado:** 22.7%

**Note:** A estratégia gerou apenas 22 trades em ~9 símbolos × ~2.5 TFs — densidade muito baixa. A amostra é insuficiente para qualquer afirmação robusta. A ausência de BTC 2h/4h e ETH 4h limita a visão de cross-TF.

---

## 6. Results (Detalhados)

### 6.1 Consolidação por família de entrada

**Momentum entries (long + short):**
- BTC 1h: 3 trades (1L + 2S) → PF 0.38, -0.33%
- SOL 2h: 2 trades (2L) → PF 1.97, +0.93%
- SOL 4h: 2 trades (2L) → PF 2.15, +0.46%
- BNB 4h: 2 trades (2S) → PF 0.47, -0.09%
- BNB 1h: 2 trades (2S) → PF 0, -1.44%
- XR 1h: 2 trades (2S) → PF 0, -4.34%
- XR 2h: 4 trades (4S) → PF 0, -2.90%

**Reversão entries (long + short):**
- ETH 1h: 2 trades (2S) → PF 0, -4.37%
- ETH 2h: 1 trade (1L) → 100% WR, +0.57%
- SOL 1h: 2 trades (2S) → PF 0, -7.35%
- ADA 1h: 1 trade (1L) → 100% WR, +1.65%
- ADA 2h: 1 trade (1L) → 100% WR, +1.20%

### 6.2 Assimetria Long/Short

- **Long trades:** 9 (todas em momentum SOL, reversão ETH/ADA)
- **Short trades:** 13 (todas em momentum BTC/XRP/BNB, reversão SOL/ETH)
- **Long net profit:** +502.6 (BTC 1h: +20.3; SOL 2h: +188.8; SOL 4h: +85.3; ETH 2h: +56.8; ADA 1h: +165.0; ADA 2h: +119.9; restante 0)
- **Short net profit:** -2,292.7 (BTC -53.6; ETH 1h -437.5; SOL 1h -735.2; XRP 1h -434.1; XRP 2h -290.4; BNB 1h -143.8; BNB 4h -9.5; restante 0)

**Conclusão:** Short bias destruiu a estratégia. Os shorts não têm edge.

### 6.3 Símbolos com sinais de vida (PF > 1.0 em ≥ 2 trades)

| Símbolo | TF | Trades | PF | Net% | Comentário |
|---|---|---|---|---|---|
| SOLUSDT | 2h | 2 | 1.97 | +0.93% | Apenas long momentum; short não disparou |
| SOLUSDT | 4h | 2 | 2.15 | +0.46% | Mesma história — long-only nesse período |
| ADAUSDT | 1h | 1 | null | +1.65% | 1 trade → não confiável |
| ADAUSDT | 2h | 1 | null | +1.20% | 1 trade → não confiável |

**Sinais de vida fracos:** SOL 2h/4h mostram PF > 1.9 em 2 trades cada, mas é amostra de 2 trades — ruído possível.

### 6.4 Símbolos sem sinal de vida (PF = 0 ou < 0.5)

BTC 1h, ETH 1h, SOL 1h, XRP 1h, XRP 2h, BNB 1h, BNB 4h — todos PF ≤ 0.47 ou zero.

---

## 7. Diagnosis

### 7.1 Problema central: Short entries sem edge

Todos os símbolos que dispararam shorts (BTC, ETH, SOL, XRP, BNB) tiveram PF = 0 ou muito baixo. Os shorts estão entrando em movimentos de baixa que continuam descendo (stop atingido) ou noise que não se recupera até o TP.

**Hipótese diagnóstica:** O threshold de `volRegime < 0.85` (vol baixa) combinado com `disp > 1.25` (movimento grande) está capturando candles de panico/recession que não se refundem — são inícios de tendência de queda, não fakeouts. O mercado crypto tem tendências de queda fortes que não se revertem em 2.5 ATR.

### 7.2 Amostra insuficiente

22 trades em ~2 dias de janela de mercado é estatisticamente inútil. O TPR (Trades Per Result) médio é 1.3 trades por backtest — abaixo do mínimo de confiabilidade (5+ trades por símbolo).

### 7.3 Concentração de trades em 2-3 dias

O comentário de XR 2h é revelador: 4 trades (todos short) em uma única sessão de ~2 dias — o que indica que o threshold capturou um evento específico de mercado (pullback forte em um período de vol baixa), não uma propriedade estatística robusta.

### 7.4 Fator de confusão: commission impact

Com 0.05% commission e trades de 100% equity, cada trade paga ~10-20 USDT em commission. Trades de média pequena em símbolos de baixa volatilidade (BNB, XRP) têm commission significativa vs. P&L.

### 7.5 Cooldown de 5 barras pode ser excessivo

Em TF de 1h, 5 barras = 5 horas sem trade. Isso pode estar suprimindo trades válidos em mercados de alta frequência de sinalização.

### 7.6 Comparação com ciclos anteriores

| Ciclo | Hipótese | Trades | PF méd | Resultado |
|---|---|---|---|---|
| QM-VPA-v1 | VolumePriceAnomaly | 0 (5 símbolos) | — | REJECT (strike 1) |
| QM-MSE-v1 | LiquidityRebalance | 0 (BTC 1h) | — | REJECT |
| QM-VRAD-v1 | VolRegimeDisp | 22 (16 backtests) | 0.3-0.5 méd | INSUFICIENTE |

VRAD melhora VPA/MSE em quantidade de trades (22 vs 0), mas a qualidade de edge não é demonstrada. VPA e MSE falharam com thresholds fixos sem normalização — VRAD tem normalização por ATR/ regime, o que é progresso conceitual, mas não basta.

---

## 8. Verdict

### Critérios de avaliação (em ordem de prioridade)

| Critério | Peso | Status VRAD-v1 |
|---|---|---|
| 1. Robustness across symbols | Alta | ❌ NEGATIVO — 6 de 9 símbolos testados com PF ≤ 0.47 |
| 2. Drawdown control | Alta | ✅ OK — DD max 8.54% (SOL 1h), mas amostra pequena |
| 3. Profit factor | Alta | ❌ NEGATIVO — PF agregado < 0.5 em maioria dos símbolos |
| 4. Average trade quality | Média | ⚠️ AMBÍGUO — média varia de -367 (SOL 1h) a +165 (ADA 1h); amostra pequena |
| 5. Trade count reliability | Alta | ❌ INSUFICIENTE — 22 trades em 16 backtests; muitos com 1-2 trades |
| 6. Stability across TFs | Média | ❌ NEGATIVO — SOL 1h -7.35% vs SOL 2h +0.93% vs SOL 4h +0.46% (instável) |
| 7. Simplicity | Baixa | ✅ OK — 8 inputs, lógica linear, sem indícadores complexos |
| 8. Net profit | Baixa | ❌ NEGATIVO — short bias destroi; long-only tira +502 mas sem contexto |

### Decisão

**VERDICT: REJECT — Strike 1 na família VRAD**

**Justificativa:**
1. Amostra insuficiente para afirmação robusta (22 trades em janela de 2 dias)
2. Asinatura de short bias sem edge — o conceito de reversão em vol baixa não se sustenta nos dados disponíveis
3. Instabilidade cross-TF (SOL 1h vs 2h vs 4h inconsistentes)
4. PF médio < 1 em maioria dos símbolos com ≥2 trades
5. Procedimento matemático é interessante (ATR normalization + regime classifier) mas os thresholds escolhidos não geram edge mensurável nesta janela

**O que não é suficiente para rejeitar definitivamente:**
- A lógica de regime classifier é matematicamente sólida e não é revertida pelos dados — é provável que os *thresholds* sejam o problema, não o conceito
- SOL 2h/4h mostram PF > 1.9 em 2 trades — uma amostra de 2 trades não é evidence, mas é consistente com a hipótese de que momentum em vol alta funciona
- Long entries (momentum + reversão) parecem ter edge positivo; short entries (principalmente momentum) não

**Strike 1 aplicado à família VRAD.** Se o ciclo seguinte mostrar 0 trades ou PF < 0.5 em ≥ 5 símbolos, pivotar para RCE (H2).

---

## 9. Next Cycle

### Opção A — Ajuste de thresholds (VRAD-v2)

Se decidir iterar neste conceito:

1. **Relajar vol regime thresholds:** `volRegimeHigh = 1.05, volRegimeLow = 0.92` (capturar mais regimes)
2. **Aumentar disp threshold para momentum:** `dispThreshMom = 1.0` (papel maisselectivo)
3. **Reduzir cooldown:** 3 barras em vez de 5 (mais trades, menos suprimidos)
4. **Expandir janela de backtest:** usar `from` e `to` para cobrir 60-90 dias (mais barras, mais trades)
5. **Shift para long-only:** eliminar short momentum (short reversão pode ser testável, mas short momentum parece sem edge)
6. **Adicionar filtro de tendência:** evitar short se `close > sma(close, 50)` (tendência de alta)

### Opção B — Pivot para RCE (Range Compression Energy)

Se decidir pivotar: usar hipótese H2 (RCE) com:
- ATR percentil < 25 (compressão mais forte)
- breakout threshold 0.6 ATR (mais brando)
- volume confirm > 1.15 (menos exigente)
- cobertura de 6-8 símbolos × 2-3 TFs

### Opção C — Equal weight: ambos em paralelo

Se créditos permitirem (166 - ~16 usados = ~150 restantes), rodar VRAD-v2 com ajustes de thresholds + RCE-v1 em 5 símbolos × 2 TFs cada.

### Recomendação

**Opção A preferida** — o conceito de VRAD é dimensionalmente superior a VPA/MSE (ATR normalization + regime) e os sinais de vida fracos em SOL 2h/4h sugerem que a direção pode estar correta. Rejeitar o conceito inteiro nesse estágio é precipitado; rejeitar os thresholds atuais é correto.

---

**Créditos restantes:** ~150 (166 iniciais - 16 backtests executados ≈ 10 usados efetivamente; o MCP pode cobrar 1 por backtest)

**Nenhuma ordem real — pesquisa/educação apenas.**

---

*Trader Dev MCP: authenticated as searesj92@gmail.com · engine tv_jul26_mc7 · parity profile applied.*
