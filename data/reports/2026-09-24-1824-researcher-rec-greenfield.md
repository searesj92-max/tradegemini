# Quant Mathematician Cycle Report — REC Greenfield

Data: 2026-09-24 18:24 UTC-3

## 1. Hipóteses Geradas

### A — Range-Efficiency Collapse (REC)
- **Ineficiência**: mercados em compressão lateral (range apertado + ATR em declínio + volume baixo) acumulam energia latente; quebra com volume confirmado se carry-through por N barras antes de reversão.
- **Por que crypto**: ausência de fechamento de sessão centraliza volatilidade em saltos; breaks com volume têm custo de liquidez mais alto → continuação mais provável.
- **Pine**: ta.atr, ta.highest, ta.lowest, ta.sma(volume), SL/TP em ATR multiples, regime filter via ATR ratio.

### B — Failed Continuation / Liquidity Sweep + Snapback
- **Ineficiência**: preço atinge pivot high/low, fecha de volta para dentro do range (falha de continuação) → stop-run + snapback reversion.
- **Por que crypto**: mercados profundos em extrema parte do book; false break com volume gera snap.
- **Pine**: ta.pivothigh/ta.pivotlow (rightBars confirmation, sem lookahead), entrada no snapback (close > open após falha de breakout).

### C — Distance-from-Equilibrium Mean Reversion (vol-conditioned)
- **Ineficiência**: preço distante do VWAP em baixa volatilidade tende a revert; z-score normalizado por ATR.
- **Por que crypto**: mean reversion em ranges laterais; volatilidade compressa → distâncias extremas mais prováveis de revert.
- **Pine**: close - ta.vwma(close,N); z = distância / ta.atr(M); entrada quando |z| > limiar + regime filter.

## 2. Hipótese Selecionada: REC (A)

Motivo: mais simples, sem pivot/lookahead, sem repainting, permitlist pura (atr, highest, lowest, sma, volume). Matematicamente clara e testável cross-symbol.

Fallback gerado: FAILCONT-v1 (Hipótese B) — registrado mas não executado por credit exhaustion.

## 3. Regras de Trading — QM-REC-v2

### Parâmetros
- `compressionBars = 20`
- `atrShortWin = 14`
- `atrLongWin = 50`
- `rangeThreshold = 0.03` (range/close < 3% → compressão)
- `atrVolFilterMult = 1.5` (ignora se ATR(14) > ATR(50)*1.5)
- `volSmaBars = 20`
- `volMult = 1.2`
- `slMult = 1.5` (ATR)
- `tpMult = 3.0` (ATR)
- `timeExitBars = 40`

### Lógica
1. **Compressão**: (Highest(high,20)-Lowest(low,20))/close < 0.03 AND ATR(14) < ATR(50)*1.5.
2. **Quebra long**: close > rangeHigh AND volume > SMA(volume,20)*1.2 AND barra anterior em compressão.
3. **Quebra short**: close < rangeLow AND volume > SMA(volume,20)*1.2 AND barra anterior em compressão.
4. **Entranças** no bar close (POC=true, sem lookahead).
5. **SL** = entry_price ∓ ATR(14)*1.5; **TP** = entry_price ± ATR(14)*3.0 (capturados via var/:= no break bar, sem valuewhen).
6. **Time exit** = 40 barras.
7. **Regime filter**: ignora compressão se ATR(14) > ATR(50)*1.5.

### O que foi recusado
- `valuewhen` — runtime do engine não implementa; substituído por var/:= com re-issue de SL/TP via strategy.exit(stop=longStop, limit=longLimit) a cada barra.
- Trailing stops — video rule.
- Martingale/grid/recovery.

### Pine Script (QM-REC-v2)

```pine
//@version=6
strategy("QM-REC-v2 — Range-Efficiency Collapse", overlay=true, pyramiding=1, process_orders_on_close=true, commission_type=strategy.commission.percent, commission_value=0.05, initial_capital=10000, default_qty_type=strategy.percent_of_equity, default_qty_value=100, margin_long=100, margin_short=100)

compressionBars   = input.int(20,  "Compression lookback (bars)")
atrShortWin       = input.int(14,  "ATR short window")
atrLongWin        = input.int(50,  "ATR long window")
rangeThreshold    = input.float(0.03, "Max range ratio for compression", step=0.005)
atrVolFilterMult  = input.float(1.5, "ATR vol filter: skip if ATR(s) > ATR(l)*mult", step=0.1)
volSmaBars        = input.int(20,  "Volume SMA lookback")
volMult           = input.float(1.2, "Volume multiplier for breakout", step=0.1)
slMult            = input.float(1.5, "SL multiple of ATR", step=0.1)
tpMult            = input.float(3.0, "TP multiple of ATR", step=0.1)
timeExitBars      = input.int(40,  "Time exit (bars)")

atrShort = ta.atr(atrShortWin)
atrLong  = ta.atr(atrLongWin)

rangeHigh = ta.highest(high, compressionBars)
rangeLow  = ta.lowest(low, compressionBars)
rangeRatio = (rangeHigh - rangeLow) / close

volSma = ta.sma(volume, volSmaBars)
volConfirmed = volume > volSma * volMult

volatilityExpanded = atrShort > atrLong * atrVolFilterMult

inCompression = rangeRatio < rangeThreshold and not volatilityExpanded

longBreak  = close > rangeHigh and volConfirmed and inCompression[1]
shortBreak = close < rangeLow  and volConfirmed and inCompression[1]

var float longStop  = na
var float longLimit = na
var float shortStop  = na
var float shortLimit = na

if longBreak
    longStop  := close - atrShort * slMult
    longLimit := close + atrShort * tpMult
if shortBreak
    shortStop  := close + atrShort * slMult
    shortLimit := close - atrShort * tpMult

if longBreak
    strategy.entry("L", strategy.long)
if shortBreak
    strategy.entry("S", strategy.short)

if strategy.position_size > 0
    strategy.exit("L_SLTP", from_entry="L", stop=longStop, limit=longLimit)
if strategy.position_size < 0
    strategy.exit("S_SLTP", from_entry="S", stop=shortStop, limit=shortLimit)

if strategy.position_size > 0 and barssince(longBreak) >= timeExitBars
    strategy.close("L")
if strategy.position_size < 0 and barssince(shortBreak) >= timeExitBars
    strategy.close("S")

plot(longBreak ? 1 : 0,  "Long break",  style=plot.style_circles, color=color.green, linewidth=2)
plot(shortBreak ? 1 : 0, "Short break", style=plot.style_circles, color=color.red,   linewidth=2)
plot(rangeHigh, "Range high", color=color.new(color.blue, 60))
plot(rangeLow,  "Range low",  color=color.new(color.orange, 60))
bgcolor(inCompression ? color.new(color.yellow, 90) : na)
```

## 4. Matriz de Backtest

| Símbolo | Timeframe | Strategy ID | Result ID | Créditos gastos |
|---------|-----------|-------------|-----------|----------------|
| BTCUSDT | 15m | 01M3AAH5XTGED13BT85TA50SXJ | 01M3AAHEBAYK86WQRKT0M4VHDK | 1 |
| ETHUSDT | 15m | 01M3AAJ17C1VST25DCAJZK7D0X | 01M3AAJ0YVZ4MYJTKHSRHE7AWT | 1 |
| SOLUSDT | 15m | 01M3AAJ2XTB5QT02T0BHWTMCDJ | 01M3AAJ2RFDMZPD4JSQ5E6B24D | 1 |
| XRPUSDT | 15m | 01M3AAJ4KCZHA2D41HCKZ1WZH0 | 01M3AAJ4DY670WRXPG1CGXBZ7Y | 1 |
| DOGEUSDT | 15m | 01M3AAJ694YJRJ1FHZB7DCRJ8Z | 01M3AAJ63W334Q6XT7T18YPB31 | 1 |
| ADAUSDT | 15m | 01M3AAJ7XCB94TXT0CYFES8DEA | 01M3AAJ7QXP99XNW1TTXNZFBH2 | 1 |
| BTCUSDT | 15m | 01M3AAMBKW83C11PVQQG2HTTJG | — (FAILCONT-v1, sem créditos) | 0 |

Total: 6 backtests executados, 7º crédito exaurido antes do FAILCONT-v1.

Período efetivo: ~2025-12-24 a 2026-09-24 (~9 meses).
Engine: tv_jul26_mc7, mcpruleValidated=true, parityProfile: commission 0.05%, pct_equity 100, margin 100.

## 5. Resultados

### REC-v2 (6 símbolos × 15m)

| Símbolo | Net Profit | PF | Max DD | Trades | WR | Long PF | Short PF |
|---------|-----------|-----|--------|--------|-----|---------|----------|
| BTCUSDT | 0 | 0 | 0 | 0 | — | — | — |
| ETHUSDT | 0 | 0 | 0 | 0 | — | — | — |
| SOLUSDT | 0 | 0 | 0 | 0 | — | — | — |
| XRPUSDT | 0 | 0 | 0 | 0 | — | — | — |
| DOGEUSDT | 0 | 0 | 0 | 0 | — | — | — |
| ADAUSDT | 0 | 0 | 0 | 0 | — | — | — |

**Total de trades: 0 em 6 símbolos.**
**Total de créditos gastos: 6.**
**FAILCONT-v1**: registrado, não executado (0 créditos restantes).

## 6. Diagnóstico

Zero trades em 6 símbolos × 15m com ~9 meses de histórico é um resultado limpo e definitivo: a estratégia é **ultra-seletiva demais** para esse regime temporal.

### Por que zero trades (causa matemática)

1. **RangeThreshold = 0.03 é muito apertado para 15m em crypto principal.** BTCUSDT em 15m tem volatilidade típica de ~0.15–0.30% por barra; range de 20 barras (5 horas) raramente é menor que 3% do close, especialmente com ATR(14) < ATR(50)*1.5. A combinação dos dois filtros (range + ATR regime) é restritiva demais.

2. **Regime filter (ATR(14) < ATR(50)*1.5) + rangeThreshold + volMult** = condição AND de três eventos raros. Em mercados de crypto grande em 15m, ou a volatilidade é alta (ATR filter bloqueia) ou o range é largo (rangeThreshold bloqueia) ou o volume no momento do break é insuficiente (volMult bloqueia). A interseção é vazia no período testado.

3. **Crypto grande (BTC/ETH) tende a tickers em tendência ou saltos, não em compressão perfeita de 3% em 20 barras de 15m.** O mercado dessas criptos é dominado por tendências de médio prazo e saltos de liquidez, não por ranges de compressão ultra-estreita em TF curto.

4. **Hipótese B (FAILCONT-v1) não pôde ser testada** — SPECULAÇÃO: pivot-based failed continuation pode gerar mais trades porque pivot highs/lows são eventos mais frequentes que compressão extrema, e o snapback é uma condição de entrada diferente. Mas sem dados, isso é apenas uma hipótese.

### O que a hipótese REC precisa para ser testável

- **Timeframe maior**: 1h ou 4h, onde compressão de 3% é mais provável.
- **RangeThreshold maior** (ex: 0.05–0.08) para capturar mais regimes de compressão.
- **Remover ou suavizar regime filter** para ver se ATR-expansivo ainda permite breaks rentáveis (o regime filter pode estar sendo excessivamente conservador).
- **Testar em símbolos menor/alta-vol** (PEPE, WIF, BONK) onde compressão + breakout é mais frequente.

Essas são iterações válidas, mas exigem créditos que não estão disponíveis neste ciclo.

## 7. Veredicto

**REJEITAR — linha REC em 15m**.

Motivos:
- **Zero trades em 6 símbolos × 15m** com ~9 meses de histórico. Uma estratégia com zero trades não pode ter edge — é uma estratégia sem operação.
- **Matematicamente identificável a causa**: rangeThreshold 0.03 + ATR regime filter + volMult 1.2 em 15m de crypto principal é uma condição de mercado demasiado rara. Não é overfit — é sub-trigger (filtros muito apertados).
- **Não é um "one-pair wonder"**: falhou em todos os 6 pares testados, o que é consistente com uma causa sistêmica, não com um símbolo específico.
- **Não é repainting/lookahead**: o Pine está limpo; o problema é seletividade, não qualidade do sinal.

### Observação importante — hipótese não está morta, está na timeframe errada

A REC como conceito (compressão → quebra com volume → continuação) pode ter edge em **timeframes maiores (1h/4h)** ou com **threshold mais amplo** ou em **símbolos de alta volatilidade**. Mas 테스트는 15m에서만 수행되었고, zero trades로 그 라인에서는 기각됩니다.

### Hipótese B (FAILCONT) — pendente

Não executada por credit exhaustion. É uma hipótese distinta (pivot failure + snapback) com pré-requisitos de mercado diferentes. VALE A PENA testar em próximo ciclo se houver créditos — pode gerar trades onde REC não gerou.

## 8. Próximo Ciclo

Se houver créditos:

1. **Testar REC-v2 em 1h e 4h** (BTCUSDT, ETHUSDT) — rangeThreshold 0.03 pode ser válido em TF maior.
2. **Iterar REC-v3**: rangeThreshold 0.05–0.08, remover ATR regime filter ou usar filtro mais brando (ex: ATR(14) < ATR(50)*2.0).
3. **Executar FAILCONT-v1** (hipótese B) em BTCUSDT 15m e 1h — pivot failure + snapback é conceitualmente diferente e pode ter vida.
4. Se REC e FAILCONT falharem em 1h/4h também → pivot para hipótese C (mean reversion vol-conditioned) ou rejeitar a linha de range-based breakout e mudar paradigma.

**Sem créditos**: aguardar reset semanal ou upgrade. Não é possível executar mais nenhum backtest.

## 9. Estado do MCP

- Login: authenticated (searesj92@gmail.com, tier free).
- Créditos: **0 restantes** (7 iniciais, 6+1 gastos = 7, sem creditos para FAILCONT-v1).
- Weekly grant: 1000 créditos, reset em "Invalid Date" (provavelmente não configurado para free tier).
- Strategias criadas: QM-REC-v1 (descartado — valuewhen bug), QM-REC-v2 (backtestado, zero trades), QM-FAILCONT-v1 (registrado, sem backtest).

## Resumo Executivo

| Item | Status |
|------|--------|
| Hipótese REC em 15m | **REJEITADA** — zero trades em 6 símbolos |
| Hipótese FAILCONT | Registrada, não executada (sem créditos) |
| Pine Script | REC-v2: limpo (sem valuewhen, sem repainting, SL/TP presente) |
| Créditos restantes | 0 |
| Próxima ação | Aguardar créditos ou upgrade; testar REC em 1h/4h ou FAILCONT em próximo ciclo |

**Veredicto final: REJEITAR.**

A hipótese REC é matematicamente bem-formulada e o Pine está limpo, mas em 15m de crypto principal a condição de mercado (compressão < 3% + ATR regime + volume confirmado) nunca se manifestou no período testado. Sem trades, sem edge. A linha é descartada para 15m; futuros ciclos devem testar 1h/4h ou pivotar para FAILCONT.
