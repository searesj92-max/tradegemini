# Quant Mathematician Cycle Report — Cycle 05

## 1. Hipóteses Geradas

### H1 — Range Efficiency Collapse + Normalized Displacement Reversion (REC-VND)
**Ineficiência:** Após um candle com grande deslocamento normalizado por ATR mas com baixa eficiência de range nos candles seguintes (follow-through fraco), há reversão sistemática. O deslocamento "ineficiente" é seguido de mean reversion porque não há sustentação de volume/alcance real.

**Por que crypto:** Impulsionamentos algos frequentemente falham em sustentar — o primeiro candle grande é frequentemente uma armadilha de liquidez sem follow-through real.

**Cross-symbol:** Universal via normalização ATR. Símbolos com maior volatilidade têm mais eventos, mas mais ruidoso.

**Quebra de regime:** Em tendência forte, o efeito diminui. Filtro de regime necessário (fade contra-tendência).

**Pine expression:** Displacement = |body|/ATR, Range Efficiency = |body|/range, Follow-through = contagens de candles na direção do cuerpo nos próximos N candles.

### H2 — Failed-Breakout-of-Equilibrium-Range (FBER)
**Ineficiência:** Breakout falso de um range de equilíbrio (Donchian) seguido de close de volta dentro do range — reversão sistemática para o interior.

**Por que crypto:** Order books shallow + stop clusters nos extremos → breakouts são frequentemente stop runs, não mudanças de valor.

**Cross-symbol:** Universal, mas a frequência de fakeouts varia.

**Regime:** Mais forte em range-bound, menos em tendência clara. Filtro de tendência necessário.

### H3 — Liquidity Sweep + Asymmetric Reversion (LS-AR)
**Ineficiência:** Sweep de liquidez (preço para além de extremo recente) com wick longo e close para dentro do range → reversão assimétrica para o interior.

**Por que crypto:** Concentração de liquidez nos extremos → preço busca stops, found, snapback.

**Cross-symbol:** Universal, magnitude varia.

**Regime:** Mais forte em compressão volátil. Em expansão, menos confiável.

### H4 — Distance-From-Adaptive-Equilibrium Exhaustion (DFAE)
**Ineficiência:** Preço distante de equilibrium adaptativo (VWAP/EMA) além de K×ATR, com desaceleração de expansão volátil → reversão provável.

**Por que crypto:** Movimentos extremos (liquidation cascades, news spikes) se acoordam rapidamente.

**Cross-symbol:** Universal via normalização.

**Regime:** Mais forte em sideways. Em tendência, preço pode permanecer distante sem reversão. Filtro necessário.

### H5 — Volume-Price Divergence After Range Expansion (VPDE)
**Ineficiência:** Candle de alta energia (high range + high volume) não seguido por high volume na continuação → reversão.

**Por que crypto:** Volume é indicador direto de participação real. Falta de volume de follow-through indica movimento artificial ou único agente grande.

**Cross-symbol:** Universal via volume relativizado.

**Regime:** Melhor após período de compressão. Em tendência contínua, volume decay pode ser normal.

---

## 2. Hipótese Selecionada

**H1 — REC-VND (Range Efficiency Collapse + Normalized Displacement Reversion)**

Motivo: conceitualmente limpa (razões normalizadas, sem parâmetros absolutos), mecanismo específico e testável (deslocamento + follow-through fraco → reversão), cross-symbol via ATR normalização, SL claro (extremo + buffer ATR), anti-soup (não baseada em RSI/MACD/BB).

**Risco:** O filter de follow-through deve ser implementado sem lookahead — a entrada só ocorre após a confirmação do follow-through fraco (candles seguintes ao candle de displacimento já fechados).

---

## 3. Trading Rules (REC-VND-v1)

### Long Entry
- **Condition:** Existem N=2 candles atrás (ref_bar = bar_index - 2) onde:
  - Cuerpo long (close > open) com |body| >= disp_thresh × ATR(14) no candle de reference
  - Range efficiency = |body| / (high-low) >= eff_thresh (candle eficiente na direção long)
  - Dos 2 candles seguintes ao de reference, no máximo ft_max_pass (ex: 1) fecharam acima do close do candle de reference → follow-through fraco confirmado
  - Regime filter: close[ref_bar] < sma(close, 20)[ref_bar] (preço estava abaixo da média — o impulsionamento long é fade da queda)
- **Entry:** No candle atual (bar_index) — strategy.entry executará no próximo open. Usamos dados até o candle atual para decidir.
- **SL:** low[ref_bar] - sl_atr_mult × atr[ref_bar]
- **TP:** open[ref_bar] (preço volta ao início do candle de displacimento — reversão completa da direção do corpo)

### Short Entry
- Mirror: body short (|body| >= disp_thresh × ATR), range efficiency alta (|body|/range >= eff_thresh), follow-through fraco (no máximo ft_max_pass dos próximos candles fecharam abaixo do close do candle de reference), regime filter (close[ref_bar] > sma(close, 20)[ref_bar] — fade da subida).
- SL: high[ref_bar] + sl_atr_mult × atr[ref_bar]
- TP: open[ref_bar]

### Cooldown
- Após entrada long, não entrar long novamente por cooldown candles. Mesma para short. (Permite long e short em direções opostas se cooldown allow.)

### Time Exit
- Se posição aberta por mais de time_exit candles, fechar.

---

## 4. Pine Script

Agora vou codificar em Pine v5.
