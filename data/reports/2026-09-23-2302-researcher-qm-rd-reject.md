# Quant Mathematician Cycle Report
## 1. Hypotheses Generated

### H1 — QM-RD: Reversion after Volatility-Normalized Displacement with Range-Efficiency Filter
**Inabilidade:** quando preço se desloca do equilíbrio local (SMA em múltiplos de ATR) mas os últimos 3 barras mostram alta ineficiência de range (soma(TR,3) / net range alto = confusão interna sem direção limpa) E a volatilidade corrente é estável (ATR < 1.3× sua média móvel de 20), o mercado mostrou reação excessiva sem follow-through genuíno. A combinação de (a) distância do equilíbrio, (b) baixa eficiência direcional, (c) volatilidade não-expandida sugere reversão de curto prazo.

**Por que crypto:** papeis altamente voláteis overreagem a choques de liquidez e depois voltam quando não há flow direcional limpo; ranges internos de 3 barras capturam a fase de consolidação pós-erupção.

**Breaking regime:** tendência forte com expansão de vol (ATR > 1.3× média) — aí o deslocamento é genuíno, não revertem; também regimes de compressão extrema onde métrica é espúria.

**Pine expression:** SMA equilibrium · displacement = |close - SMA| / ATR · inefficiency = sum(TR,3)/netRange3 · volStable = ATR/ATR_avg20 < 1.3 · entry iff displacement > 1.5 AND inefficiency > 1.5 AND volStable AND on correct side of SMA.

### H2 — QM-FC: Failed Continuation after Volatility Expansion Decay
Após pico de ATR relativo (ATR/ATR_avg > 1.5), se vol clustering decai e preço não apresenta continuação na direção do pico em N barras, o breakout falhou e reverte. Por que crypto: falsos rompimentos frequentes em alts de baixa liquidez. Breaking: tendência macro com vol sustentada. **Não testado neste ciclo.**

### H3 — QM-RE: Range-Efficiency MR with Binary Regime Filter (ADX)
Quando fechamento é fraco vs range (closing / total range baixo) enquanto preço está esticado do rolling median, há provável reversão. Filtro ADX: baixo = chop (operar), alto = trend (não operar). Por que crypto: ranges ineficientes revertem, mas só em chop; em trend o mesmo sinal é continuation bait. **Não testado neste ciclo.**

---

## 2. Hypothesis Selected (math basis)

**QM-RD** — simplicidade (3 condições + 2 filtros), testabilidade direta, edge matemático claro: deslocamento normalizado + ineficiência de range + estabilidade de vol. A hipótese é falsificável: se as condições de entrada geram mais perdas que ganhos com PF < 1, a edge está refutada.

**Matemática:** 
- Displacement normalizado por ATR torna o sinal comparável entre pares de vol diferente.
- Inefficiency = TR_sum / net_range mede quão "barato" foi o movimento real em relação ao movimento possível (se ineficiente, o preço fez muito ruído pouco progresso direcional).
- Vol stability exclui idas onde o deslocamento é genuinamente novo regime (ATR expandindo), que são casos de trend onde MR falha.

---

## 3. Trading Rules

**Equilíbrio:** SMA(20) como ancor for local fair value.

**Entrada Long:**
- close < SMA (preço abaixo do equilíbrio)
- displacement > 1.5 × ATR (esticado abaixo)
- inefficiency > 1.5 (range interno ineficiente nos últimos 3 barras)
- volStable (ATR < 1.3 × ATR_avg20)
- cooldown ativo

**Entrada Short:**
- close > SMA
- displacement > 1.5 × ATR (esticado acima)
- inefficiency > 1.5
- volStable
- cooldown ativo

**SL:** 2.5 × ATR (fixo no preço de entrada, não trailing).
**TP:** 1.0 × ATR (fixo).
**Time exit:** 20 barras máximas (força saída se não reverte).
**Cooldown:** 5 barras após qualquer saída.
**Risco:** 100% equity, 1 unidade, pyramiding=1.

**Nenhum trailing stop** (regra do vídeo: trailing atrasa preenchimento e converte winners em losses).

---

## 4. Pine Script (v2 — fixed ta.sum runtime gap)

```pine
//@version=6
strategy("QM-RD v2 — Reversion after Displacement + Range-efficiency filter",
  overlay=true,
  pyramiding=1,
  process_orders_on_close=true,
  commission_type=strategy.commission.percent,
  commission_value=0.05,
  initial_capital=10000,
  default_qty_type=strategy.percent_of_equity,
  default_qty_value=100,
  margin_long=100,
  margin_short=100)

// === Inputs ===
displacementThreshold = input.float(1.5, "Displacement threshold (x ATR)", minval=0.5, step=0.1, group="Entry")
inefficiencyThreshold  = input.float(1.5, "Inefficiency threshold (TR sum / net range)", minval=0.5, step=0.1, group="Entry")
volStabilityMult      = input.float(1.3, "Max ATR / avg ATR (vol stability)", minval=1.0, step=0.1, group="Entry")
smaPeriod             = input.int(20, "SMA period (equilibrium anchor)", minval=5, group="Entry")
atrPeriod             = input.int(14, "ATR period", minval=5, group="Entry")

slAtrMult    = input.float(2.5, "SL — ATR multiplier", minval=0.5, step=0.1, group="Exit")
tpAtrMult    = input.float(1.0, "TP — ATR multiplier", minval=0.5, step=0.1, group="Exit")
timeExitBars = input.int(20, "Time exit (max bars)", minval=1, group="Exit")
cooldownBars = input.int(5, "Cooldown (bars after exit)", minval=0, group="Exit")

// === Core metrics ===
atr = ta.atr(atrPeriod)
sma = ta.sma(close, smaPeriod)
displacement = math.abs(close - sma) / atr

// Manual 3-bar rolling TR sum (no ta.sum — runtime gap)
tr0 = ta.tr
tr1 = ta.tr[1]
tr2 = ta.tr[2]
trSum3 = (not na(tr0) ? tr0 : 0) + (not na(tr1) ? tr1 : 0) + (not na(tr2) ? tr2 : 0)

netRange3 = math.max(ta.highest(high, 3) - ta.lowest(low, 3), 1e-9)
inefficiency = trSum3 / netRange3

// Vol stability: current ATR vs its own average
atrAvg20 = ta.sma(atr, 20)
volStable = (atr / atrAvg20) < volStabilityMult

// === Entry conditions ===
longSig  = close < sma and displacement > displacementThreshold and inefficiency > inefficiencyThreshold and volStable
shortSig = close > sma and displacement > displacementThreshold and inefficiency > inefficiencyThreshold and volStable

// === Cooldown ===
var int cd = 0
if strategy.position_size != 0
    cd := 0
else if cd == 0
    cd := 1
else
    cd += 1
canTrade = cd > cooldownBars

// === Fixed SL/TP vars (set at entry, not moving) ===
var float longSL = na
var float longTP = na
var float shortSL = na
var float shortTP = na

// === Entries ===
if longSig and canTrade
    strategy.entry("L", strategy.long)
    longSL := close - slAtrMult * atr
    longTP := close + tpAtrMult * atr

if shortSig and canTrade
    strategy.entry("S", strategy.short)
    shortSL := close + slAtrMult * atr
    shortTP := close - tpAtrMult * atr

// === Exits: fixed SL/TP ===
if strategy.position_size > 0 and not na(longSL)
    strategy.exit("LX", from_entry="L", stop=longSL, limit=longTP)
if strategy.position_size < 0 and not na(shortSL)
    strategy.exit("SX", from_entry="S", stop=shortSL, limit=shortTP)

// === Time exit ===
var int entryBar = na
if strategy.position_size != 0 and na(entryBar)
    entryBar := bar_index
if strategy.position_size == 0
    entryBar := na
if not na(entryBar) and (bar_index - entryBar) >= timeExitBars
    strategy.close(strategy.position_size > 0 ? "L" : "S")

// === Reset SL/TP vars when flat ===
if strategy.position_size == 0
    longSL := na
    longTP := na
    shortSL := na
    shortTP := na

// === Plots ===
plot(sma, "SMA (equilibrium)", color=color.gray, linewidth=1)
plot(displacement > displacementThreshold and close < sma ? low - atr * 0.3 : na, "Long zone", color=color.new(color.green, 70), style=plot.style_circles, linewidth=1)
plot(displacement > displacementThreshold and close > sma ? high + atr * 0.3 : na, "Short zone", color=color.new(color.red, 70), style=plot.style_circles, linewidth=1)
```

---

## 5. Backtest Matrix

| Symbol | TF | Strategy ID | Result ID | Notes |
|---|---|---|---|---|
| BTCUSDT | 1h | QM-RD-v2 (01M3882MMX6EX2MNDZS4ZD08GV) | 01M3882MF6S32RRZXZBB1WDXFB | Single pair, single TF — diagnostic |

**Assumptions:** Bybit linear USDT perp · commission 0.05% · 100% equity · margin 100/100 · pyramiding 1 · process on bar close · slippage 0 ticks. Window: Jun 2026 → Sep 23 2026 (~2437 barras, 114% coverage).

---

## 6. Results

| Metric | Value |
|---|---|
| Net Profit | **-30.72%** ($10,000 → $6,928) |
| Profit Factor | **0.25** |
| Max Drawdown | **-31.53%** |
| Win Rate | **19.54%** (17W / 70L / 0E) |
| Total Trades | **87** |
| Avg Trade | **-$35.31** (-0.353% r) |
| Avg Win | +$59.41 (22 barras) |
| Avg Loss | -$58.31 (8.3 barras) |
| Win/Loss ratio | 1.019 (perdas maiores e mais frequentes) |
| Long Trades | 24 (11W, net -$591) |
| Short Trades | 63 (6W, net -$2,481) |
| Sharpe | -6.49 |
| Sortino | -3.56 |
| Commission Paid | $628 |

**Equity curve:** unimodal descendente, drawdown profundo no meio do período. Sem runup registrado (maxRunup = 0).

---

## 7. Diagnosis

**O que os números dizem:**
- PF 0.25 é claramente inferior a 1.0 — edge negativo, não neutro.
- 70 perdedores em 87 trades: a condição de entrada está disparando com frequência demais e a direção esperada (reversão) não se realiza na maioria dos casos.
- Trades perdidos duram 8.3 barras em média, vencedores 22 — quando acerta, demora para se resolver; mas acerta demais pouca.
- Short trades são 72% do volume e tiveram PF desastroso (6W em 63L). O mercado de BTC em 1h neste período teve movimentos descendentes de alto range eficiente (não ineficiente) — a estratégia short entrou em setups onde o preço quebra de fato para baixo, não reverte.

**Diagnóstico raiz (hipótese, não indicador):**
1. **Inefficiency threshold muito low:** trSum3/netRange3 > 1.5 captura qualquer período com um candle com gap/inside bar. Em BTC em 1h, esses padrões frequentemente são pré-sinais de movimentos reais, não estouro de reversão. O threshold está demasiado solto.
2. **Vol stability filtra os melhores setups possíveis?** A regra `ATR < 1.3 × ATR_avg20` exclui períodos de expansão de vol. Pode ser que os melhores trades MR ocorram justamente no início da expansão (deslocamento grande + ineficiência), e a vol stability está cortando esses casos.
3. **A relação SL/TP (2.5/1.0) é muito orientada para perda:** SL 2.5× ATR permite que o trade rode bastante antes de sair, mas TP 1× ATR é rígido e o preço frequentemente não volta 1 ATR em 20 barras no contexto de market noise.
4. **Não há regime filter (ADX):** entrou em trend-down de BTC e shortou sem perceber que era tendência, não chope.

**Não é overfitting:** há 87 trades, parâmetros são concetuais, não curva-fits. O resultado é uma falsificação clara da hipótese na sua forma inicial.

---

## 8. Verdict: REJECT

**Critério:** PF 0.25, DD 31.5%, win rate 19.5%, edge negativo consistente. Não atende a nenhum limiar de robustez (PF ≥ 1.0 nem próximo). Strategy é refutada para BTC/1h como escrita.

**Montagem:** não incubar. Não colocar no dashboard como candidato. Registrar como "teste falsificado com evidência" e pivotar.

---

## 9. Next Cycle

**Possível iteração (se testar de novo):**
- Adicionar regime binary filter: ADX(14) < 25 (apenas operar em chop) — remove trend bait.
- Ajustar inefficiency threshold para 2.5+ (apenas ranges muito confusos).
- Remover volStability (permitir ATR expandindo se inefficiency alto — o deslocamento pode ser a oportunidade).
- Aumentar TP para 1.5× ATR e reduzir SL para 2.0× (razão de risco 1.33, não 2.5).
- Split long/short com lógicicas diferentes (no mercado de BTC, long pode ter edge diferente de short).
- Teste multi-par (ETH, XRP, DOGE) e multi-TF (15m, 30m, 2h, 4h) antes de condenar totalmente.

**Hipóteses H2 e H3 ainda disponíveis para próximos ciclos.**

**Observação de crédito:** próximo ciclo deve começar com análise teórica mais rigorosa antes de codar — os parâmetros desta versão eram pouco justificados por pré-análise.

---

*Relatório gerado automaticamente pelo loop 01-quant-mathematician.md (researcher profile).*
*Tradar Dev MCP: authenticated as searesj92@gmail.com · engine tv_jul26_mc7 · parity profile applied.*
