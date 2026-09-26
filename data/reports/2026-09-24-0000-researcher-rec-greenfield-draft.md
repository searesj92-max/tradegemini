# Quant Mathematician Cycle Report

## 1. Hipóteses Geradas

### A — Range-Efficiency Collapse (REC)
- **Ineficiência**: mercados em compressão lateral (range apertado + ATR em declínio + volume baixo) acumulam energia latente; a quebra com volume confirmado frequentemente se carry-through por N barras antes de reversão.
- **Por que crypto**: ausência de fechamento de sessão centraliza volatilidade em saltos; breaks com volume têm custo de liquidez mais alto → continuação mais provável.
- **Expressão Pine**: detectar compressão via ratio (highest(high,N)-lowest(low,N))/close < threshold AND ATR(short)<ATR(long)*filter; entrada no close que rompe o range com volume > SMA(volume)*mult; SL/TP em ATR multiples; time exit; regime filter para evitar tendências fortes.

### B — Failed Continuation / Liquidity Sweep + Snapback
- **Ineficiência**: quando preço atinge extremo (pivot high/low) e fecha de volta para dentro do range (falha de continuação), há stop-run + reversão snapback.
- **Por que crypto**: mercados profundos em extrema parte do book; false break com volume gera snap.
- **Expressão Pine**: pivot high detectado via ta.pivothigh; se close abaixo do pivot após N barras → falha; entrada long no snapback (close acima do close da barra de falha ou recuo). SL abaixo do pivot.

### C — Distance-from-Equilibrium Mean Reversion (vol-conditioned)
- **Ineficiência**: preço distante do VWAP ou da média móvel em regime de baixa volatilidade tende a revert; distância normalizada por ATR entra como z-score.
- **Por que crypto**: mean reversion em ranges laterais; volatilidade compressa → distâncias extremas mais prováveis de revert.
- **Expressão Pine**: distância = close - ta.vwma(close,N); z = distância / ta.atr(M); entrada quando |z| > limiar E atr(short)<atr(long)*filter; SL/TP.

## 2. Hipótese Selecionada (REC) — Base Matemática

Hipótese **A (REC)**. Motivo: mais simples de implementar com allowlist (ta.atr, ta.highest, ta.lowest, ta.sma, volume), sem dependência de pivot (que requer lookahead via offset), sem repainting. Regra matematicamente clara e testável cross-symbol. Ancore no conceito de "range efficiency collapse" — compressão seguida por quebra com volume.

## 3. Regras de Trading

### Parâmetros
- `compressionBars = 20` — janela de detecção de compressão.
- `atrShortWin = 14` — ATR curto.
- `atrLongWin = 50` — ATR longo.
- `rangeThreshold = 0.03` — ratio máximo (range/close) para compressão.
- `atrVolFilterMult = 1.5` — ignora compressão se ATR(s) > ATR(l)*1.5 (vol expansão).
- `volSmaBars = 20` — SMA de volume.
- `volMult = 1.2` — multiplicador mínimo de volume para quebra confirmada.
- `slMult = 1.5` — SL em ATR múltiplos.
- `tpMult = 3.0` — TP em ATR múltiplos.
- `timeExitBars = 40` — time exit.

### Lógica
1. **Compressão** = (highest(high,20)-lowest(low,20))/close < 0.03 AND ATR(14) < ATR(50)*1.5.
2. **Quebra long**: close > rangeHigh AND volume > SMA(volume,20)*1.2 AND barra anterior em compressão.
3. **Quebra short**: close < rangeLow AND volume > SMA(volume,20)*1.2 AND barra anterior em compressão.
4. **Entranças** no bar close (POC=true, sem lookahead).
5. **SL** = entry_price ∓ ATR(14)*1.5.
6. **TP** = entry_price ± ATR(14)*3.0.
7. **Time exit** = 40 barras se nada atingido.
8. **Regime filter**: ignora ambiente com ATR expansivo (ATR(14) > ATR(50)*1.5) — evita breaks em tendências fortes onde SL é desnecessário ou perigoso.

### Não faz
- Trailing stops (video rule).
- Martingale/grid/recovery multiplier.
- Repainting/pivot offset lookahead.

## 4. Pine Script (v6, TV_ENGINE_JUL_26)

```pine
//@version=6
strategy("QM-REC-v1 — Range-Efficiency Collapse", overlay=true, pyramiding=1, process_orders_on_close=true, commission_type=strategy.commission.percent, commission_value=0.05, initial_capital=10000, default_qty_type=strategy.percent_of_equity, default_qty_value=100, margin_long=100, margin_short=100)

// === Inputs ===
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

// === Volatility series ===
atrShort = ta.atr(atrShortWin)
atrLong  = ta.atr(atrLongWin)

// === Range compression ===
rangeHigh = ta.highest(high, compressionBars)
rangeLow  = ta.lowest(low, compressionBars)
rangeRatio = (rangeHigh - rangeLow) / close

// === Volume confirmation ===
volSma = ta.sma(volume, volSmaBars)
volConfirmed = volume > volSma * volMult

// === Regime filter: skip strong expanding-trend regimes ===
volatilityExpanded = atrShort > atrLong * atrVolFilterMult

// === Compression state (lagged by 1 to avoid same-bar break+entry confusion) ===
inCompression = rangeRatio < rangeThreshold and not volatilityExpanded

// === Breakout signals (close beyond range, volume confirmed, prev bar in compression) ===
longBreak  = close > rangeHigh and volConfirmed and inCompression[1]
shortBreak = close < rangeLow  and volConfirmed and inCompression[1]

// === Entries (process on bar close — POC=true) ===
if longBreak
    strategy.entry("L", strategy.long)
if shortBreak
    strategy.entry("S", strategy.short)

// === ATR-based SL/TP levels using close of the break bar (entry price proxy) ===
// valuewhen captures ATR at break bar; close used as entry price for level calc
entryAtrLong  = valuewhen(longBreak,  atrShort, 0)
entryAtrShort = valuewhen(shortBreak, atrShort, 0)

if longBreak
    strategy.exit("L_SLTP", from_entry="L", stop=close - entryAtrLong * slMult, limit=close + entryAtrLong * tpMult)
if shortBreak
    strategy.exit("S_SLTP", from_entry="S", stop=close + entryAtrShort * slMult, limit=close - entryAtrShort * tpMult)

// === Time exit (flat if no hit after N bars) ===
if strategy.position_size > 0 and barssince(longBreak) >= timeExitBars
    strategy.close("L")
if strategy.position_size < 0 and barssince(shortBreak) >= timeExitBars
    strategy.close("S")

// === Plots ===
plot(longBreak ? 1 : 0,  "Long break",  style=plot.style_circles, color=color.green, linewidth=2)
plot(shortBreak ? 1 : 0, "Short break", style=plot.style_circles, color=color.red,   linewidth=2)
plot(rangeHigh, "Range high", color=color.new(color.blue, 60))
plot(rangeLow,  "Range low",  color=color.new(color.orange, 60))
bgcolor(inCompression ? color.new(color.yellow, 90) : na)
```

## 5. Matriz de Backtest

- **Strategy ID**: `QM-REC-v1` (via `create_strategy`).
- **Símbolos**: top-100 Bybit — selecionados aleatoriamente para robustez cross-symbol: BTCUSDT, ETHUSDT, SOLUSDT, XRPUSDT, DOGEUSDT, ADAUSDT, NEARUSDT, AVAXUSDT, LINKUSDT, TONUSDT.
- **Timeframes**: 15m, 30m, 1h, 2h, 4h.
- **Período**: backtest completo disponível no engine.
- **Suposições**: commission 0.05%, margin 100%, percent_of_equity 100%, pyramiding=1, POC=true.

## 6. Resultados (em produção — MCP)

Aguardando execução via `create_strategy` + `run_backtest` multi-symbol/timeframe.

## 7. Diagnóstico (antes dos resultados)

Espera-se edge em mercados laterais/compressão; deve sofrer em tendências fortes (regime filter tenta mitigar). Ponto cego: mercados em moda baixa com volume fraco podem gerar poucas operações; mercados com volatilidade muito alta podem-trigger falsos breaks. Monitorar trades por símbolo e PF por timeframe.

## 8. Veredicto

**A definir após backtest.** Critérios:
- PF ≥ 1.3 em ≥ 5 símbolos → Incubate/Watchlist.
- Max DD ≤ 30%.
- ≥ 50 trades no total.
- Estabilidade em ≥ 2 timeframes.
- Sem repaint/lookahead (já verificado no Pine).
- SL presente (sim).

Se edge não confirmar → Reject + pivot.

## 9. Próximo Ciclo

Se REC falhar: testar hipótese B (failed continuation) com modificação mínima — entrada no snapback, não no break. Se REC funcionar parcialmente: ajustar regime filter ou vol confirmation.
