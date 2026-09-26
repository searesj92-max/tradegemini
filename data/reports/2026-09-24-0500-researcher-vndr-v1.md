# Quant Mathematician Cycle Report

Data: 2026-09-24 05:00 UTC-03  
Agent: researcher  
Strategy ID: `01M38W9RMJ98JZX1871YRXX0WW`  
Hypothesis code: `VNDR` (Vol-Normalized Displacement Reversion)

---

## 1. Hypotheses Generated

### H1 — Vol-Normalized Displacement Reversion (SELECTED)
**Ineficiência**: em crypto, picos de deslocamento relativo ao equilíbrio local (median rolling) são frequentemente seguidos de meed reversion curto, MAS só quando a volatilidade não está expandindo — quando o ATRPara está subindo, o movimento é regime shift, não overreaction reversível.

**Por que em crypto**: a liquidez é rasa em muitas pairs; ordens de mercado grandes causam displacement + snapback para o nível de equilíbrio mais rápido que em mercados de maior profundidade. O ATR raramente continua subindo indefinidamente em setups de overreaction; quando expande, é tendência, não reversão.

**Cross-symbol**: hipótese genérica — todo par com preço relativo a um rolling median. BTC/ETH como anchors, altcoins como amplifying sample.

**Breaking regime**: tendência forte (ATR expandido + displacement persistente) invalida a reversão — por isso filtramos `atrDelta > 0` para não entrar em regime de expansão.

**Expression em Pine**: `dispZ = |close - ta.median(close, 50)| / ta.atr(14)`; entrada quando `dispZ >= 2.0` e `atrDelta <= 0`; entrada no retorno de 30% do caminho até o equilíbrio; SL = extremo − 0.5 ATR; TP = equilíbrio.

### H2 — Range-Efficiency Collapse After Failed Breakout
**Ineficiência**: quando um candle range (high-low) é esticado em relação à ATR local mas o preço não sustenta o breakout (falso rompimento), um retorno rápido ao interior do range tem edge.

**Expression**: detectar candle com `range > k * ATR`, depois `close`voltar para dentro dos extremos do candle anterior'; entrar na direção oposta ao falso breakout.

**Breaking regime**: true breakout sustentado (preço permanece além do extremo por N barras) invalida.

### H3 — Failed Continuation After Displacement
**Ineficiência**: quando o preço displanta (z-score alto) mas o candle seguinte mostra aceleração faltando (range caindo, volume alto sem preço), o movimento falha e reverte.

**Expression**: `dispZ >= threshold AND ta.range(close,1) / ta.atr(14) < threshold2` → entrada reversora.

**Por que crypto**: mercados de baixa profundidade geram "fake momentum" onde o candle de displacimento é followed por absorção (limit orders) em vez de continuação.

### H4 — Liquidity Sweep + Snapback From Local Extreme
**Ineficiência**: quando o preço limpa um extremo local (low of last N) mas o candle seguinte fecha bem dentro dele (wick longa sem finalização), há snapback.

**Expression**: `pivothigh`/`pivotlow` + condição de wick ratio (`abs(close-open) / range < 0.2` após limpeza de extremo).

### H5 — Volatility Compression → Expansion Mean Reversion
**Ineficiência**: em compressão extrema de volatilidade (`bbw` muito baixo), o primeiro candle de expansão costuma ter mean reversion parcial porque o movimento é inicialmente "false expansion" até confirmar direção.

**Expression**: `ta.bbw < compressed_threshold` → esperar expansão → entrar no retorno parcial.

---

## 2. Hypothesis Selected

**H1 — Vol-Normalized Displacement Reversion (VNDR) v1**

**Base matemática**: o insight central não é "preço longe do equilíbrio → volta" (isso é bagunça indicador clássico). O insight é: **deslocamento normalizado combinado com o SINAL DE VOLATILIDADE** determina se o deslocamento é reversível ou regime shift. Quando o preço está a N ATRs do rolling median mas a volatilidade NÃO está expandindo (ATR flat/caendo), o estado é de overreaction sem trend confirmation — e o retorno ao equilíbrio tem expectancy positivo. Quando o ATR está subindo, o deslocamento é tendência, não reversão.

**Por que é diferente de RSI/BB/impulse**: não usa sobrecompra/sobrevenda clássica; não usa banda de Bollinger. Usa deslocamento em relação ao MEDIAN (robusto a outliers vs mean) e normaliza por ATR. O filtro `atrDelta <= 0` é o componente matemático crucial que separa overreaction de trend.

**Assunção testável e falsificável**: se a hipótese é verdadeira, o filter `atrDelta <= 0` deve mostrar PF melhor que a estratégia sem o filter, e o setup deve ter edge principalmente em mercados range/chop, não em tendência forte.

---

## 3. Trading Rules

### Entrada LONG
- `dispZ >= 2.0` (close a ≥ 2 ATRs abaixo do rolling median de 50 barras)
- `disp < 0` (preço abaixo do equilíbrio)
- `atrDelta <= 0` (volatilidade não está expandindo — filter de regime)
- `not longOn` (sem setup ativo)

**Ação**: marcar `longOn = true`, `longExtLow = low` (marca o extremo do setup).

### Entrada SHORT
- `dispZ >= 2.0` (close a ≥ 2 ATRs acima do rolling median)
- `disp > 0` (preço acima do equilíbrio)
- `atrDelta <= 0`
- `not shortOn`

**Ação**: marcar `shortOn = true`, `shortExtHigh = high`.

### Rastreio de extremo
Enquanto o setup está ativo:
- LONG: `longExtLow := math.min(longExtLow, low)` — baixar com novos mínimos
- SHORT: `shortExtHigh := math.max(shortExtHigh, high)` — subir com novos máximos

### Invalidação do setup (antes de entrar)
O setup é invalidado (e resetado) se:
- `atrDelta > 0` (volatilidade expande → regime shift, não overreaction)
- `close >= eq` (LONG) ou `close <= eq` (SHORT) — preço retorna ao equilíbrio sem entrada

**Nota**: isso evita entrar em setups que já "resolveram" ou que viram regime.

### Entry (execução da ordem)
- **LONG**: `close > longExtLow + revertFrac * (eq - longExtLow)` — preço voltou 30% do caminho do extremo até o equilíbrio
- **SHORT**: `close < shortExtHigh - revertFrac * (shortExtHigh - eq)`

### Exit
- **LONG SL**: `longExtLow - atr * slMult` (0.5 ATR abaixo do extremo do setup)
- **SHORT SL**: `shortExtHigh + atr * slMult` (0.5 ATR acima do extremo)
- **LONG TP**: `eq` (equilíbrio — retirada quando a reversão completa)
- **SHORT TP**: `eq`

**Sem trailing stops** (regra do loop). TP fixo no equilíbrio; SL fixo no ATR-based.

### Filtros adicionais
- `pyramiding=1` (uma posição por direção)
- `process_orders_on_close=true`
- `commission=0.05%`, `margin_long=100`, `margin_short=100`, `initial_capital=10000`
- Sizing: 100% equity (perfil de parity do Trader Dev)

---

## 4. Pine Script

```pine
//@version=6
strategy("QM-VNDR-v1 | Vol-Normalized Displacement Reversion",
  overlay=true, pyramiding=1, process_orders_on_close=true,
  commission_type=strategy.commission.percent, commission_value=0.05,
  initial_capital=10000, default_qty_type=strategy.percent_of_equity,
  default_qty_value=100, margin_long=100, margin_short=100)

// === INPUTS ===
eqLen      = input.int(50,  "Equilibrium length (median window)")
atrLen     = input.int(14,  "ATR length")
zScore     = input.float(2.0, "Displacement Z-score threshold")
revertFrac = input.float(0.30, "Reversion frac to enter (0-1)")
slMult     = input.float(0.50, "SL multiple of ATR beyond extreme")
tpAtEq     = input.bool(true, "TP at equilibrium (vs 1 ATR beyond)")

// === EQUILIBRIUM (rolling median) ===
eq = ta.median(close, eqLen)

// === VOLATILITY ===
atr = ta.atr(atrLen)
atrDelta = atr - atr[1]   // > 0 => expanding, <= 0 => flat/falling

// === DISPLACEMENT (signed, normalized) ===
disp = close - eq          // signed displacement
dispAbs = math.abs(disp)
dispZ = dispAbs / atr      // normalized magnitude

// === STATE TRACKING ===
var float longExtLow   = na
var float shortExtHigh = na
var bool  longOn   = false
var bool  shortOn  = false

// --- new long setup: price far below eq, vol NOT rising ---
newLong  = dispZ >= zScore and disp < 0 and atrDelta <= 0 and not longOn
if newLong
    longOn := true
    longExtLow := low

// --- new short setup: price far above eq, vol NOT rising ---
newShort = dispZ >= zScore and disp > 0 and atrDelta <= 0 and not shortOn
if newShort
    shortOn := true
    shortExtHigh := high

// --- track extremes while active ---
if longOn
    longExtLow := math.min(longExtLow, low)
if shortOn
    shortExtHigh := math.max(shortExtHigh, high)

// --- invalidate setup: vol expands (regime change) or price returns to eq ---
if longOn and (atrDelta > 0 or close >= eq)
    longOn := false
    longExtLow := na
if shortOn and (atrDelta > 0 or close <= eq)
    shortOn := false
    shortExtHigh := na

// === ENTRY: price reverts from extreme by revertFrac of the way back to eq ===
longEntry  = longOn  and not na(longExtLow)  and close > longExtLow  + revertFrac * (eq - longExtLow)
shortEntry = shortOn and not na(shortExtHigh) and close < shortExtHigh - revertFrac * (shortExtHigh - eq)

// === EXIT LEVELS ===
longSL  = longExtLow  - atr * slMult
shortSL = shortExtHigh + atr * slMult
longTP  = tpAtEq ? eq : close + atr
shortTP = tpAtEq ? eq : close - atr

// === EXECUTE ===
if longEntry
    strategy.entry("L", strategy.long)
    strategy.exit("Lx", from_entry="L", stop=longSL, limit=longTP)
if shortEntry
    strategy.entry("S", strategy.short)
    strategy.exit("Sx", from_entry="S", stop=shortSL, limit=shortTP)

// === PLOTS ===
plot(eq, "Equilibrium", color=color.gray, linewidth=1)
plotshape(longEntry, "Long", shape.triangleup, location.belowbar, color.green, size=size.small, title="Long entry")
plotshape(shortEntry, "Short", shape.triangledown, location.abovebar, color.red, size=size.small, title="Short entry")
bgcolor(longOn ? color.new(color.green, 90) : na, title="Long setup")
bgcolor(shortOn ? color.new(color.red, 90) : na, title="Short setup")
```

**O que foi mantido**:
- Filtro `atrDelta <= 0` (matemático, não retail)
- Equilíbrio como median rolling (robusto a outliers)
- Normalização do deslocamento por ATR
- SL baseado em ATR além do extremo do setup
- TP no equilíbrio
- Sem trailing stops

**O que foi rejeitado/omitido**:
- Nenhum indicador de sobrecompra/sobrevenda (RSI, Stoch, BB)
- Nenhum trailing
- Nenhum martingale/grid
- Sem request.security, arrays, cancel, pyramiding > 1

---

## 5. Backtest Matrix

| # | Strategy ID | Symbol | Timeframe | Result ID | View |
|---|-------------|--------|-----------|-----------|------|
| 1 | `01M38W9RMJ98JZX1871YRXX0WW` | BTCUSDT | 1h | `01M38W9ZX7S86KBJF3ZKVVK41W` | [ver](https://mcp-api.trader.dev/backtest/01M38W9ZX7S86KBJF3ZKVVK41W) |
| 2 | `01M38W9RMJ98JZX1871YRXX0WW` | ETHUSDT | 1h | `01M38WB73D67H9PA4E656K298Q` | [ver](https://mcp-api.trader.dev/backtest/01M38WB73D67H9PA4E656K298Q) |
| 3 | `01M38W9RMJ98JZX1871YRXX0WW` | SOLUSDT | 1h | `01M38WBFRENEBA4T2MBS06S50B` | [ver](https://mcp-api.trader.dev/backtest/01M38WBFRENEBA4T2MBS06S50B) |
| 4 | `01M38W9RMJ98JZX1871YRXX0WW` | DOGEUSDT | 1h | `01M38WCBZBQJ15C325G34KW54X` | [ver](https://mcp-api.trader.dev/backtest/01M38WCBZBQJ15C325G34KW54X) |
| 5 | `01M38W9RMJ98JZX1871YRXX0WW` | BTCUSDT | 4h | `01M38WBWQ8QR96PJ5Z549ZZ055` | [ver](https://mcp-api.trader.dev/backtest/01M38WBWQ8QR96PJ5Z549ZZ055) |
| 6 | `01M38W9RMJ98JZX1871YRXX0WW` | ETHUSDT | 4h | `01M38WC1MV1S39NWQPTK1QMRG4` | [ver](https://mcp-api.trader.dev/backtest/01M38WC1MV1S39NWQPTK1QMRG4) |
| 7 | `01M38W9RMJ98JZX1871YRXX0WW` | SOLUSDT | 4h | `01M38WC6K1YGDEN7ZHAB0M0CSC` | [ver](https://mcp-api.trader.dev/backtest/01M38WC6K1YGDEN7ZHAB0M0CSC) |

**Janelas**: 1h → ~120 dias (2456 barras). 4h → ~120 dias (839 barras).  
**Paridade**: commission 0.05%, sizing 100% equity, margin 100/100, initial 10000.

---

## 6. Results

### Resumo

| Symbol | TF | Net% | PF | MaxDD% | WR% | Trades | LongPF | ShortPF |
|---------|-----|------|------|--------|------|--------|--------|---------|
| BTC | 1h | -9.52% | 0.355 | 10.53% | 26.3% | 38 | 0.39 | 0.31 |
| ETH | 1h | -7.04% | 0.508 | 9.93% | 22.9% | 35 | 0.46 | 0.55 |
| SOL | 1h | -6.26% | 0.682 | 10.28% | 20.0% | 40 | 0.56 | 0.72 |
| DOGE | 1h | -21.41% | 0.258 | 22.43% | 15.2% | 46 | 0.34 | 0.20 |
| BTC | 4h | -1.84% | 0.443 | 3.41% | 40.0% | 5 | — | — |
| ETH | 4h | -2.41% | 0.000 | 3.42% | 0.0% | 3 | 0.00 | -241 |
| SOL | 4h | -1.99% | 0.710 | 8.14% | 33.3% | 9 | 0.65 | 0.55 |

**Média 1h (4 símbolos com significativo)**: PF média ≈ 0.45, DD média ≈ 13.3%, WR média ≈ 21%, trades média ≈ 40.  
**Média 4h (3 símbolos)**: PF média ≈ 0.38, DD média ≈ 5.0%, trades média ≈ 5.7.

### Trade-level
- BTC 1h: avg win $52.40, avg loss $52.70, ratio 0.99 — LUZ = PESO (nenhum edge na magnitude)
- SOL 1h: avg win $168.23, avg loss $61.63, ratio 2.73 — os WINS são grandes, mas perde 80% das vezes; grossLoss > grossProfit
- DOGE 1h: avg win $106.31, avg loss $73.98, ratio 1.44 — WINS maiores que LOSSES, mas WR de 15% não compensa (more small wins than big losses compensados?)
  - Verificação: grossProfit $744 / grossLoss $2885 → PF 0.26 → os raros wins grandes não cobrem os perdedores frequentes e maiores em magnitude total
- BTC 4h: apenas 5 trades — sample muito pequeno, não julgável

### Sizing / commission impact
- Commission média: BTC 1h $345, ETH 1h $233, SOL 1h $234, DOGE 1h $239, BTC 4h $49, ETH 4h $10, SOL 4h $58
- Em DOGE (minQty 1, tick 0.00001), as lot sizes são grandes (quantidade nominal alta por $1 equity) → commission alta; mas mesmo desconsiderando commission, o PF não chega a 1.

### Cross-symbol pattern
- Todos os símbolos mostram PF < 1 em todos os TFs
- Sem exceção positiva — não há nenhum par com PF ≥ 1.3 (threshold de incubação)
- Sem símbolo que "salve" a estratégia (não é one-pair-wonder — o problema é sistemático)

---

## 7. Diagnosis

### O que a evidência diz

**Diagnóstico principal: a hipótese tem o sinal no lugar errado, ou o setup é prematuro demais.**

Analisei os componentes:

1. **Filter `atrDelta <= 0` está funcionando como esperado** — ele filtra setups em expansão de volatilidade, o que é bom. Mas o problema é que mesmo filtrado, os setups que chegam a trigger são frequentemente setups onde a "reversão" não tem edge.

2. **TP no equilíbrio é provavelmente muito agressivo**: esperar retorno completo ao median é raro — muitos trades saem por SL antes de chegar ao equilíbrio, e os que chegam ganham pouco porque o TP é "apenas" o equilíbrio, que pode ser atingido parcialmente em barra seguinte.

3. **SL de 0.5 ATR abaixo do extremo é muito apertado para crypto**: em mercados de alta volatilidade com wicks, o extremo registrado no candle de setup é frequentemente testado novamente — 0.5 ATR de buffer não protege contra o wick de re-test. Isso explica os muitos SLs e a baixa win rate.

4. **RevertFrac de 30% pode estar entrando tarde demais ou cedo demais**: entrar no retorno de 30% do caminho pode ser tarde demais em setups onde a reversão é rápida (o preço já "pegou" e está voltando sem dar entry signal), ou cedo demais em setups onde o preço continua displacement.

5. **Sample 4h muito pequeno**: com 3-9 trades nos 4h, não há significância estatística — o 4h pode ter menos setups (menos barras = menos dislocamentos que atingem o threshold), mas também pode ter setups de melhor qualidade (mais tempo para o extremo consolidar). Não podemos concluir nada do 4h com este sample.

6. **Não é overfit**: os parâmetros são gerais (50 median, 14 ATR, 2.0 z-score, 0.3 revert, 0.5 SL) — não foram ajustados para este mercado específico. O resultado negativo é consistente e sistemático, não um caso de "parâmetros para BTC não funcionam em DOGE".

### O que NÃO é o problema
- Não é one-pair-wonder (todos negativos)
- Não é repainting/lookahead (código clean, process_orders_on_close)
- Não é commission-only (mesmo sem commission, PF não chega a 1)
- Não é sample size insuficiente nos 1h (35-46 trades por símbolo — enough para julgar)

### O que é o problema
- **Windowing entry muito restritivo + SL apertado** = poucas entradas que completam o trade em direção ao TP antes de serem stopped
- **TP no equilíbrio é quase impossível de atingir** antes do preço "voltar a sair" — o equilíbrio é um ponto, não uma zona
- **Sem regime classifier real** — `atrDelta <= 0` é um proxy simples, mas não distingue chop de tendência marchando; em tendência, o displacement pode ser seguido de mais displacement, não reversão

---

## 8. Verdict

**REJEITAR — linha VNDR v1 sem edge em crypto.**

**Razão**: em 7 backtests (4 símbolos × 1h + 3 símbolos × 4h), nenhum com PF ≥ 1.3, nenhum com win rate acima de 41%, todos com net profit negativo. O padrão é sistemático (todos os símbolos, ambos os TFs), não um caso isolado. O trade-off médio é negativo (avg win/loss ratio próximo de 1 emBTC/ETH, mas win rate baixa; SOL tem avg win/loss bom mas perde 80%). Comission impacta mas não é a causa raiz.

**Ação**: pivotar para próxima hipótese no próximo ciclo. A linha "vol-normalized displacement reversion com filtro ATR delta" foi testada com 7 símbolos/TFs efalhou — não fazer terceira tentativa na mesma linha (three strikes atingido neste ciclo).

---

## 9. Next Cycle

**Próxima hipótese a testar**: entre H2–H5 do Step 1. Recomendação:

**H2 — Range-Efficiency Collapse After Failed Breakout** é a mais próxima de um conceito testável com regras limpas: detectar candle de faixa longa (range > k×ATR), detectar que o breakout falhou (close voltou para dentro dos extremos), entrar na direção oposta com SL no extremo do candle (ou 1 ATR além), TP em uma fração da faixa.

**Alternativa**: H4 (Liquidity Sweep + Snapback) também tem expressão matemática limpa (pivotlow/pivothigh + wick ratio) e pode ter edge em pairs com liquidez rasa (altcoins) onde sweeps são frequentes e reversões rápidas.

**Para o próximo ciclo**:
- Definir SL/TP antes de codar (não derivar do equilibrio — usar ATR-based distance, não nivel pontual)
- Considerar um TP em ZONA (ex: central do range anterior, ou 50% da distância de displacement) em vez de ponto único
- Considerar SL mais generoso (1.0–1.5 ATR abaixo do extremo) para proteger contra wicks de re-test
- Talvez separar long/short com logics diferentes (crypto tem asymmetry — shorts em altcoins frequentemente têm comportamento diferente de longs)

**Ciclos restantes nesta linha (se pivotar)**: 2 ciclos disponíveis antes do three-strikes total — mas como v1 já é rejeitado, a próxima hy é uma linha nova, não uma continuação da VNDR.

---

## Dashboard Update

Nova linha adicionada ao `data.json`:

```json
{
  "id": "qm-vndr-v1",
  "name": "QM-VNDR-v1 | Vol-Normalized Displacement Reversion",
  "symbol": "multi (BTC,ETH,SOL,DOGE × 1h+4h)",
  "timeframe": "1h / 4h",
  "source": "greenfield",
  "family": "vnder",
  "agent": "researcher",
  "net_profit_pct": -9.52,
  "profit_factor": 0.355,
  "max_drawdown_pct": 10.53,
  "win_rate_pct": 26.3,
  "trades": 38,
  "sharpe": -4.61,
  "result_id": "01M38W9ZX7S86KBJF3ZKVVK41W",
  "view_url": "https://mcp-api.trader.dev/backtest/01M38W9ZX7S86KBJF3ZKVVK41W",
  "curve": [],
  "verdict": "Rejected",
  "status": "rejected",
  "last_backtest": "2026-09-24",
  "pine_key": "01M38W9RMJ98JZX1871YRXX0WW"
}
```

---

## Risk Notice

Pesquisa e educação apenas. Não é aconselhamento financeiro. Backtests não são desempenho futuro. Incubação ≥ 20 trades / ~3 meses antes de qualquer consideração live. Aprovação humana requerida para live.
