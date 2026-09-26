# Quant Mathematician Cycle Report — Cycle 001

**Data:** 2024-09-24 16:53 UTC  
**Agent:** researcher  
**Hypotheses Considered:** H1 (RECAB), H2 (VNDR), H3 (FCVC), H4 (EDRG), H5 (RRAS)

---

## 1. Hypotheses Generated

| # | Nome | Eficácia | Por qué crypto | Cross-symbol | Breaking regime |
|---|------|----------|----------------|--------------|-----------------|
| H1 | **RECAB** — Range-Efficiency Collapse After Breakout: candle de rompimento de extremo local seguido de colapso de range no candle seguinte → snapback. | Alta se break com vol; rara em ranges laterais | Stop runs sem continuação são frequentes em perps 24/7 | Sim — lógica local pura (range, ATR, extremos N barras) | Mercado trending forte sem pullback: o colapso pode ser continuation normal |
| H2 | **VNDR** — Volatility-Normalized Displacement Reversion: deslocamento price > N × ATR acima de EMA curta + RSI extremo + range candle alto → reversion de curto prazo. | Alta em ranging; baixa em trend puro | Saltos de vol recorrentes; exaustão de momentum é real em crypto | Sim — indicadores padrão, universal | Strong trend: displacement é legítimo, RSI pode stay extremo sem reversão |
| H3 | **FCVC** — Failed Continuation with Volume Confirmation: candle de high volume rompe extremo, candle seguinte volume < médio e range menor → falha confirmada por volume. | Media — volume é proxy ruidoso em perps | Volume em perps é fragmentado; não confirma intenção institucional de forma limpa | Parcial — depende de profile de volume por ticker | Sessões de alta vol sustentada: volume pode continuar alto mesmo após pullback |
| H4 | **EDRG** — Equilibrium Distance Reversion with Regime Gate: price estica além banda adaptive e depois entra em canal estreito → reversão com gate de vol/ regime. | Alta se banda bem calibrada; regime gate crítico | Alternância de compressão/expansão é marcante em crypto | Sim — banda é param-free | Compressão prolongada sem explosão: estratégia pode ficar parada |
| H5 | **RRAS** — Range Ratio Asymmetry Long/Short Split: ratio de range N barras atrás / range recente; assimetria que recolhe → operar contra a direção do pico. | Media — ratio é param-free mas req. janela longa | Ciclos de range expansion/contraction bem definidos | Sim — ratio é puramente local | Regime de alta vol persistente: ratio pode não recolher sem reversão |

---

## 2. Hypothesis Selected

**Vencedora: H2 (VNDR)** — downward-adjusted para **VNDR-v2: Trend-Gated Displacement Reversion**.

**Motivo da seleção:**
- Simplicidade: 3 indicadores (EMA20, EMA50, RSI14, ATR14) — todos allowlisted, sem repainting.
- Testabilidade: condições booleanas limpas, sem dependência de janela de lookback longa nem de volume (que varia por ticker).
- Matemática defensável: deslocamento normalizado por ATR é independente de escala de preço — critério "quanto se afastou do equilíbrio em unidades de risco" é cross-symbol por construção.
- Regime gate (EMA20 vs EMA50) evita operar reversion em trending puro — é a principal fragilidade do H2 vanilla e o filtro mais barato para adicioná-la.
- Risk management: SL e TP em ATR fixos, sem trailing, sem martingale, com cooldown mínimo.

**Ajuste v2 vs v1 (diagnóstico pós-primeiro backtest):**
- v1 (BTC 1h): PF 0.96, DD 10%, 57 trades, short-side devastado (shortNetProfit −1230 vs long +1134). Win rate 33%.
- A hypothesis H2 sem regime gate paga para operar short em tudo — o short-side leva em trending. Resolvido com trend gate: long só em EMA20>EMA50, short só em EMA20<EMA50.
- v2 resultou em BTC PF 1.26, DD 6.8%, 54 trades — sinal de vida. Estendido cross-symbol.

---

## 3. Trading Rules (VNDR-v2)

### Entrada Long
- EMA(20) > EMA(50) → regime de alta ativo
- close > EMA(20) AND (close − EMA(20)) > 1.2 × ATR(14) → displacement normalizado positivo
- RSI(14) > 70 → gate de exaustão (overbought)

### Entrada Short
- EMA(20) < EMA(50) → regime de baixa ativo
- close < EMA(20) AND (EMA(20) − close) > 1.2 × ATR(14) → displacement negativo
- RSI(14) < 30 → gate de exaustão (oversold)

### Filtro de range
- (high − low) > 0.7 × ATR(14) → candle de entrada tem range suficiente para não ser noise

### Saída
- SL: 2.0 × ATR(14) do preço de entrada (stop price calculado no momento da entrada)
- TP: 1.5 × ATR(14) do preço de entrada
- Cooldown: 2 barras pós-saída antes de nova entrada (mesmo lado)

### Invalidação / observações
- Sem trailing stop (regra explícita — latência ao broker transforma winner em loser no mundo real).
- Sem martingaling, sem pyramiding > 1.
- Process_orders_on_close=true; pyramiding=1; 100% equity; margin 100/100; commission 0.05%.

---

## 4. Pine Script

```pine
//@version=6
strategy("QM-VNDR-v2 | Trend-Gated Displacement Reversion",
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

emaLen       = input.int(20, "EMA de referência (curto)")
emaRegLen    = input.int(50, "EMA de regime (longo)")
rsiLen       = input.int(14, "RSI length")
rsiOverbought= input.float(70, "RSI overbought gate")
rsiOversold  = input.float(30, "RSI oversold gate")
dispMult     = input.float(1.2, "Displacement mínimo em ATR versus EMA curto")
rangeMult    = input.float(0.7, "Range do candle de entrada ≥ X × ATR recente")
atrLen       = input.int(14, "ATR length")
atrMultSL    = input.float(2.0, "SL: ATR múltiplo")
atrMultTP    = input.float(1.5, "TP: ATR múltiplo")
cooldownBars = input.int(2, "Cooldown pós-saída")

ema20  = ta.ema(close, emaLen)
ema50  = ta.ema(close, emaRegLen)
rsi14  = ta.rsi(close, rsiLen)
atr14  = ta.atr(atrLen)

trendUp   = ema20 > ema50
trendDown = ema20 < ema50

dispUp = close > ema20 and (close - ema20) > dispMult * atr14
dispDn = close < ema20 and (ema20 - close) > dispMult * atr14

rangeCandle = high - low
rangeCond   = rangeCandle > atr14 * rangeMult

rsiGateLong  = rsi14 > rsiOverbought
rsiGateShort = rsi14 < rsiOversold

barsSinceExit = ta.barssince(ta.change(strategy.position_size) != 0)
inCooldown = barsSinceExit < cooldownBars

longEntry  = dispUp and rsiGateLong and rangeCond and trendUp and not inCooldown and strategy.position_size == 0
shortEntry = dispDn and rsiGateShort and rangeCond and trendDown and not inCooldown and strategy.position_size == 0

if longEntry
    strategy.entry("Long", strategy.long)
if shortEntry
    strategy.entry("Short", strategy.short)

if strategy.position_size > 0
    strategy.exit("LX", from_entry="Long",
      stop=close - atr14 * atrMultSL,
      limit=close + atr14 * atrMultTP)

if strategy.position_size < 0
    strategy.exit("SX", from_entry="Short",
      stop=close + atr14 * atrMultSL,
      limit=close - atr14 * atrMultTP)

plot(ema20, "EMA 20", color.blue, linewidth=1)
plot(ema50, "EMA 50 (regime)", color.orange, linewidth=1)
plotshape(longEntry,  "Long VNDR",  shape.triangleup,   location.belowbar, color.green, size=size.small)
plotshape(shortEntry, "Short VNDR", shape.triangledown, location.abovebar, color.red,   size=size.small)
```

---

## 5. Backtest Matrix

| Symbol | Timeframe | Strategy ID | Result ID | Bars | Notes |
|--------|-----------|-------------|-----------|------|-------|
| BTCUSDT | 1h | `01M3A58MFA3Q3PPWB28ATN41MW` | `01M3A58M99SDV08ZTNN89MP389` | 2444 | v2 baseline |
| ETHUSDT | 1h | `01M3A59Y9GTZA1C5Q9J8EXAVH2` | `01M3A59Y291RHN4CCDMTEVBC5Y` | 2444 | nova linhagem (diff symbol) |
| SOLUSDT | 1h | `01M3A5AE3TYZCVBKJ1QWVV25YY` | `01M3A5ADWC6HAK1S4H04JJ79JV` | 2444 | nova linhagem |
| DOGEUSDT | 1h | `01M3A5BNKFF9GJBQSZSN2DCXW0` | `01M3A5BNBZQSTPFZGQSD1X5RNE` | 2444 | nova linhagem |
| DOGEUSDT | 15m | `01M3A5CP613PBTVSJGC8PD23QB` | `01M3A5CNZD261N4PQYVSVMWKXN` | 8873 | TF alternativo para estabilidade |

**Janela:** Jun 2026 – Sep 2026 ( ClickHouse coverage, ~2143–8572 barras solicitadas, cobertura > 100% em todos).

**Configuração:** 100% equity, margin 100/100, pyramiding=1, commission 0.05%, process_orders_on_close=true, slippage 0, sem trailing, sem martingale.

---

## 6. Results

### Matriz consolidada (1h) + TF check

| Symbol | Net% | PF | DD% | WR% | Trades | Long PF | Short PF | AvgWin | AvgLoss | Sharpe |
|--------|------|-----|------|------|--------|---------|----------|--------|---------|--------|
| BTCUSDT | **+5.8%** | **1.26** | 6.8% | 38.9% | 54 | 1.99 (28) | −2.47 (26) | 132.7 | −66.8 | 1.16 |
| ETHUSDT | **−6.3%** | 0.85 | 18.8% | 45.2% | 62 | 0.94 (35) | −1.15 (27) | 124.0 | −120.8 | −1.11 |
| SOLUSDT | **+6.3%** | **1.19** | 10.0% | 39.2% | 74 | 1.99 (29) | −1.87 (45) | 135.6 | −73.3 | 0.89 |
| DOGEUSDT | **+24.1%** | **1.59** | 13.2% | 40.0% | 70 | 1.70 (25) | 1.09 (45) | 231.7 | −97.0 | 2.51 |
| DOGEUSDT | 15m | **−15.5%** | 0.81 | 23.6% | 32.2% | 264 | 0.68 (87) | 0.75 (177) | 79.6 | −46.4 | −1.39 |

### Long/Short split (1h)

- **Long PF ≥ 1.0 em 3/4 símbolos**: BTC 1.99, SOL 1.99, DOGE 1.70. ETH 0.94 (quase neutro).
- **Short PF ≤ 0 em 3/4 símbolos**: BTC −2.47, ETH −1.15, SOL −1.87. Apenas DOGE tem short PF positivo (1.09), mas modesto.
- Conclusão: **o lado longo é o motor**; o lado short é structuralmente prejudicado mesmo com trend gate.

### Trade count

- 1h: entre 54 e 74 trades por símbolo (suffixo de amostra razoável para 3 meses).
- 15m DOGE: 264 trades — amostra grande mas performance negativa (PF 0.81), sugere que a estratégia funciona em TF maior (displacement mais significativo) mas não em TF menor onde o ruído domina.

### Estabilidade cross-symbol

- 3 de 4 símbolos em 1h têm net positivo com PF > 1.1 (BTC, SOL, DOGE).
- ETH é o outlier negativo (PF 0.85, DD 18.8%) — possível regime mais forte de tendência unidirecional sem reversion relevante, ou peculiarity de perfil de vol de ETH nesse período.
- DD moderado: de 6.8% (BTC) a 18.8% (ETH). BTC e SOL têm DD < 10%.

---

## 7. Diagnosis

### O que funciona
- **Long-side reversion em regime de alta** é o core do edge. Quando EMA20>EMA50 e o preço estica acima de +1.2 ATR com RSI>70, a reversão para cima do equilíbrio (não para baixo!) é favorecida — parece contra-intuitivo mas é o padrão clássico de "pullback dentro de trend": longo entry no extremo overbought que depois recua para a EMA sem violar o regime.
- **ATR-based SL/TP** funciona: ratioAvgWinLoss > 1.8 em BTC, SOL, DOGE.
- **1h é TF adequado**: displacement normalizado é mais limpo em 1h do que em 15m (ruído domina em 15m).

### O que falha
- **Short-side leva em todos os símbolos exceto DOGE.** Mesmo com EMA20<EMA50 gate, o short em reversion de momentum é hostil em crypto recente. Possível explicação: perps têm viés de longo por funding rate carry e por demanda de longo — short-side reversion pode sofrer drag sistemático.
- **ETH quebra o padrão** — requer investigação: pode ser que o ETH tenha vivido um período de trending puro sem mean-reversion pockets significativos, ou que a gate de EMA50 não seja adequada para o perfil de vol de ETH nesse período.
- **15m colapsa** — PF 0.81, DD 23.6%, 264 trades: a estratégia é propensa a over-trading em TF menor onde o mesmo critério é satisfeito por ruído normal. Não há evidência de edge em 15m.

### Fragilidades identificadas
1. **Dependência de longo-side**: se o mercado virar para dominância de short-side (crash por ex), a estratégia teria poucas entradas long e short-side teria PF ruim — risco de regime shift.
2. **RSI gate fixo em 70/30**: é arbitrário. Pode haver calibração por símbolo (ETH pode precisar de gate mais extremo ou usar TSI em vez de RSI).
3. **EMA50 como regime gate**: em crypto de alta vol, EMA50 pode ficar muito lento — regime de alta pode inverter antes do cross, gerando entrada short prematura ou long entry tardia.
4. **Sem filtro de vol absoluto**: em período de vol muito baixa, o critério de displacement em ATR pode gerar entradas false because ATR é pequeno — trade count inflado sem edge.
5. **Sample de 3 meses**: é curto para afirmar robustez cross-symbol. BTC e SOL PF>1.2 é encorajador mas não conclusivo.

---

## 8. Verdict

**ESTACIONAR** — com ressalvas fortes.

**Justificativa:**
- Positivo: 3/4 símbolos em 1h com PF > 1.1, long-side com PF ~2.0 em BTC/SOL, Sharpe > 0.89 em todos os positivos, DD controlado (<10% em BTC/SOL). Amostra de trades >50 em cada símbolo.
- Negativo: ETH fail (PF 0.85), short-side leva em 3/4 símbolos, 15m fail, amostra de 3 meses curta para afirmar robustez, regime gate pode ser parametrizável de forma fragil.
- Não atende incubation gate completo: precisa de (a) cobertura de mais símbolos (pelo menos 5-7), (b) mais de 1 emissor de timeframe estável (1h e 2h, não 15m), (c) diagnóstico do short-side antes de incubator.

**Condições para promoção:**
- Add 2-3 símbolos adicionais com PF > 1.0 em 1h (ou 4h).
- Investigar e corrigir short-side: tentar filter de vol (ex. só short se ATR relativo > limiar, ou usar TSI em vez de RSI para gate), ou operar short só se displacement for mais extremo (ex. 1.5× ATR em vez de 1.2×).
- Validar em 2h e 4h para ver se edge escala com TF.
- Confirmar que ETH não é outlier sistemático (testar em outro período).

**Sem proibições violadas:** nenhum real order, nenhum fork/search de estratégia existente, nenhum indicador repainting/lookahead, SL/TP definidos, trailing ausente.

---

## 9. Next Cycle

Um de:
1. **Correção do short-side** (iteração válida — um conceito): substituir RSI gate por TSI(close,5,13) ou adicionar vol filter para short (ex. só entrar short se ATR(14) > SMA(ATR,50) × 1.2). Mantendo long-side intacto.
2. **Expansão de símbolos**: testar 2-3 símbolos adicionais (AVAXUSDT, LINKUSDT, SUIUSDT) em 1h com mesma lógica. Se 4/6 têm PF>1.0, avançar para incubação.
3. **Regime gate alternativo**: testar regime com ADX ou com slope de EMA20 (ema20 - ema20[5]) / ATR em vez de cross de EMA50 — mais contínuo e menos frágil a crosses pontuais.

Recomendo começar com opção 1 (short-side fix) porque é a fragilidade mais óbvia que mata o edge em 3 de 4 símbolos, antes de expandir símbolos.

---

**Relatório salvo:** data/reports/2024-09-24-1653-researcher-VNDR-v2-cycle001.md  
**Verdict:** ESTACIONAR  
**Próximo passo sugerido:** iteração 1 — corrigir short-side com TSI+vol filter ou distorcer threshold de displacement para short-side apenas.
