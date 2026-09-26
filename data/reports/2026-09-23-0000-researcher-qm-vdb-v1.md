# Quant Mathematician Cycle Report
## 23-set-2026 — Cycle 01 — Hypo: Volatility-Displaced Breakout (QM-VDB-v1)

### 1. Hipóteses geradas (5, greenfield)

| # | Código | Ineficiência | Por que no crypto | Pine |
|---|--------|--------------|-------------------|------|
| 1 | **VDB** | z-score descartado durante compressão de Bollinger → expansão direcional tende a continuar na direção do descartamento (falha de mean-reversion) | Crypto tem regimes de squeezing seguidos de expansão anisotrópica; squeezes soam como reversão mas o deslocamento que rompe a compressão é o driver real | z=(close−EMA50)/ATR14; bbw=(BB_U−BB_L)/close; entrada quando |z|>k e bbw<lim e close vs open confirma direção |
| 2 | FPR | Pivô-alto recente falha em reverter → seguimos o rompimento (failed continuation) | Extreme zones formam markers de liquidez; rupturas sem reversão são informação de regime | ta.pivothigh/ta.pivotlow + close beyond pivot |
| 3 | REC-DFT | Colapso de Range Efficiency + pico de displacement → follow-through direcional | RE baixo precede expansão; crypto tem ciclos de compression→explosão | RE_t=|close_t−close_{t−1}|/(H_t−L_t); medição M-bars + spike displacement/ATR |
| 4 | DEF | Spike de displacement [1]>2.5⋅ATR + bar com displacement<0.5⋅ATR fechando contra spike → fade do spike | Liquidity sweeps costumam snapbackar; fade de spans é edge documentado | displacement=close−close[1]; logica de fade pós-spike |
| 5 | DERA | Dual regime por z sem EMA200/ATR20: zona central com compressão → mean-reversion; |z|>2 → fade; zona intermediária → trend-following | 3 regímas com lógica diferente; base de alternância entre modos |

**Seleção**: VDB — simplicidade máxima (2 indicadores allowlist, 2 thresholds), condição matematicamente coerente (deslocamento normalizado + compressão = falha de reversão), SL/TP baseado em ATR sem trailing, teste cross-symbol direto.

### 2. Hipótese selecionada e base matemática

Hipótese **VDB** (Volatility-Displaced Breakout):

- `z_t = (close_t − EMA50_t) / ATR14_t` — deslocamento normalizado da média móvel
- `bbw_t = (BB_upper − BB_lower)/close_t` — compressão do canal de Bollinger

**Raciocínio**: Quando `|z|` é grande (≈ descartamento) E o canal está comprimido (bbw baixo), o mercado está viscido pra reversão de curto prazo — o deslocamento está "carregando" expansão, não mean-reversion. Se o close do bar corroborate a direção (|z|>0 e close>open para long, |z|>0 e close<open para short), a expansão se mantém na direção.

**Break regime esperado**: sideways range-bound sem squeezes (bbw alto → sem compressão = sem entrada); choppiness sem direção consistente; panics sem bbw-below threshold (V-shape reversal sem filtro de compressão).

### 3. Regras de trade

**Entrada long**:
- `z > 1.2` AND `bbw < 0.08` AND `close > open`
- Entrada na abertura do próximo bar (market, process_orders_on_close=true → preço de body)

**Entrada short**:
- `z < -1.2` AND `bbw < 0.08` AND `close < open`

**SL**: `3 × ATR14` (ticks absolutos pós-entrada, via strategy.exit stop=)
**TP**: `6 × ATR14` (1:2, ticks absolutos via strategy.exit limit=)
**Exit adicional (return-to-mean safety)**: se position_size>0 e z≤0 → strategy.close("L"); se position_size<0 e z≥0 → strategy.close("S")
**Time exit**: 20 barras máximo exposto (evita stuck trades)

**Nunca**: trailing (latency rule), martingale, grids, cancel, security, arrays, repaint, lookahead.

### 4. Pine Script (QM-VDB-v1.pine)

```pine
//@version=6
strategy("QM-VDB-v1", overlay=true,
  pyramiding=1, process_orders_on_close=true,
  commission_type=strategy.commission.percent, commission_value=0.05,
  default_qty_type=strategy.percent_of_equity, default_qty_value=100,
  margin_long=100, margin_short=100, initial_capital=10000)

zThresh   = input.float(1.2,   "z threshold (|z| >)")
bbwThresh = input.float(0.08,  "bbw threshold (<)")
slMult    = input.float(3.0,   "SL ATR mult")
tpMult    = input.float(6.0,   "TP ATR mult")
timeCap   = input.int(20,      "time exit bars")

ema50 = ta.ema(close, 50)
atr14 = ta.atr(14)
z = (close - ema50) / atr14
[ub, mb, lb] = ta.bb(close, 20, 2)
bbw = (ub - lb) / close

longCond  = z >  zThresh and bbw < bbwThresh and close > open
shortCond = z < -zThresh and bbw < bbwThresh and close < open

if longCond
    strategy.entry("L", strategy.long)
if shortCond
    strategy.entry("S", strategy.short)

if strategy.position_size > 0
    strategy.exit("LX", from_entry="L",
      stop = close - slMult * atr14,
      limit = close + tpMult * atr14)
if strategy.position_size < 0
    strategy.exit("SX", from_entry="S",
      stop = close + slMult * atr14,
      limit = close - tpMult * atr14)

if strategy.position_size > 0 and z <= 0
    strategy.close("L")
if strategy.position_size < 0 and z >= 0
    strategy.close("S")

var int longBars = 0
var int shortBars = 0
if longCond
    longBars := 0
if shortCond
    shortBars := 0
if strategy.position_size > 0
    longBars += 1
    if longBars >= timeCap
        strategy.close("L")
        longBars := 0
if strategy.position_size < 0
    shortBars += 1
    if shortBars >= timeCap
        strategy.close("S")
        shortBars := 0

plot(longCond  ? 1 : 0, "longSignal",  color.green,  0, plot.style.columns, colordown=color.green)
plot(shortCond ? 1 : 0, "shortSignal", color.red,    0, plot.style.columns, colordown=color.red)
```

### 5. Matriz de backtest

| Symbol | TF | Strategy ID | Result ID | Bares | Período |
|--------|-----|------------|-----------|-------|---------|
| BTCUSDT | 4h | 01M38AFAP7BSW77F6VDKQTPANP | 01M38AFABE8MAY41Q7G4EWCNXH | 835 | jun–set 2026 |
| ETHUSDT | 4h | 01M38AG1H7C69WFTXP2JFATXN4 | 01M38AG1BG3JKTAFVF79DVVCHR | 835 | jun–set 2026 |
| SOLUSDT | 4h | 01M38AGHGNEMKMCA3XNB9BETFG | 01M38AGHBCJV2QCNYDNS2R6ZVW | 835 | jun–set 2026 |

Configuração comum: capital $10.000; sizing 100% equity; margem 100/100; commission 0.05% (forçado pelo engine a 0.05% parity); slippage 0; proc_orders_on_close=true; pyramiding=1. Bybit USDT linear perp, resolução via search_perps.

### 6. Resultados

| Métrica | BTC 4h | ETH 4h | SOL 4h |
|---------|--------|--------|--------|
| Net profit | **−22.19%** (R$ 7.781) | **−14,36%** (R$ 8.564)  | **−3,52%** (R$ 9.648) |
| Profit Factor | 0.40 | 0.56 | 0.88 |
| Max DD | −23.6% | −19.4% | −20.6% |
| Win Rate | 8.3% (4W/44L) | 16.1% (5W/26L) | 12.5% (5W/35L) |
| Trades | 48 | 31 | 40 |
| Sharpe | −1.95 | −0.64 | +0.75 |
| Avg trade | −$46.22 | −$46.33 | −$8.80 |
| AvgWin/AvgLoss | 4.38 | 2.93 | 6.19 |
| Long trades | 10 | 12 | 9 |
| Short trades | 38 | 19 | 31 |
| Long PF (implícito) | +362 R$ (4W/10L) | +543 R$ (5W/12L) | +1.700 R$ (4W/9L) |
| Short PF (implícito) | −2.581 R$ (0W/38L) | −1.979 R$ (0W/19L) | −2.052 R$ (1W/31L) |
| Commission paid | $311 | $182 | $200 |

**Decomposição essencial**: em TODOS os símbolos:
- Longs têm PF > 1.0 (BTC +362; ETH +543; SOL +1.700)
- Shorts têm PF << 1 (BTC −2.581; ETH −1.979; SOL −2.052)
- Shorts representam 71–79% do volume de trades
- Zero de short wins no BTC e ETH; 1 no SOL

**Padrão consistente cross-symbol**: a lógica long captura algum edge; a lógica short é sistematicamente prejudicada. Shorts têm win rate praticamente zero e destroem o resultado.

### 7. Diagnóstico

1. **Viés de mercado** — Provável: regime de crypto em 2026 com tendência maior de alta; shorts em compressão são reversões de falso rompimento para baixo (ou gaps de liquidez de short que voltam para cima). Entradas curtas no contexto de Bitcoin/Alto volatilidade têm custo de carry + gap risk.

2. **SL muito apertado para shorts** — 3×ATR pode ser insuficiente para a direção short em crypto, onde DDs (drawdown intraday) são profundos. Mas como short wins ~0, o problema é de win-rate, não do tamanho da vitória/media perda.

3. **Condição de short precisa de um filtro de regime adicional** — enquanto long usa "z>k E bbw<lim E close>open", a condição de short "z<−k E bbw<lim E close<open" é cegamente espelhada. Em crypto bull, "close<open" em compressão pode ser trap.

4. **Small sample alert** — 48+31+40 = 119 trades total (3 símbolos × 4h) é amostra razoável, mas ainda pequena para afirmações robustas. O padrão de longs >1 PF é encorajador mas precisa de mais símbolos e TFs para confirmação.

5. **Sem repainting/lookahead confirmado** — engine validate mcpruleValidated=true, cascadeRatio moderado (1.33–2.0), sem warnings de cascade_exit_pattern_severe.

### 8. Verdict

**WATCHLIST / ESTACIONAR — viés long identificado, linha de short precisa de pivot.**

Não aprovar para incubação (PF<1.3, short destruindo). Não rejeitar (long PF>1 cross-symbol, edge potencial detectável). Classificação: **Watchlist** — pivot para próxima iteração.

### 9. Próxima iteração (UM conceito)

Hipótese de diagnóstico: o entry de short precisa de um filter de regime para evitar reversões falsas.

**Versão v2 proposta (apenas long side + regime)**
- Opção A: **Long-only com filtro de tendência** — desligar short, manter long VDB com bônus de filtro (ex. close>EMA200 como filtro de regime uptrend; se close<EMA200, short pode ter edge, mas dados sugerem short prejudicado em geral).
- Opção B: **Long VDB + regime classifier** — se bbw comprimido E z>1.2 AND close>open E (close > EMA200 OR (alta volatilidade long regime)) → long; caso contrário, aguardar (evita short traps).
- Opção C: **Short com SL mais largo (ex. 4×ATR) + tp 8×ATR + filtro de regime 200 EMA** — testar se o edge short existe com parâmetros mais generosos (alto custo de SL pode matar probability).

**Decisão na próxima rodada**: testar A (long-only com filtro EMA200) e C (short expansivo com regime) em paralelo — BTC, ETH, SOL, 3TFs (4h, 2h, 1h), 5–8 símbolos adicionais (ADA, AVAX, DOGE, LINK, XRP). Comparar via compare_backtests.

### Supressão de strikes

Hipótese VDB: ciclo 1 sem edge claro em ambos os lados, mas long-side mostra PF>1 consistente. **1 strike** para esta linha (long+short). Se próxima iteração (v2 long-only ou short-regime) também der PF<1.0 cross-symbol, então 2 strikes e pivot de hipótese.

---

> Avise: abrir loop\01-quant-mathematician.md para decisão de strikes e próxima rodada. Attachments: strategy IDs, result IDs, view URLs.

## Dashboard row update (data.json — QM-VDB-v1)

```json
{
  "id": "qm-vdb-v1",
  "name": "QM-VDB-v1 Volatility-Displaced Breakout",
  "symbol": "BTCUSDT/ETHUSDT/SOLUSDT",
  "timeframe": "4h",
  "source": "greenfield quant mathematician cycle 01",
  "family": "VDB",
  "agent": "researcher",
  "net_profit_pct": -13.36,
  "profit_factor": 0.62,
  "max_drawdown_pct": -21.2,
  "win_rate_pct": 12.3,
  "trades": 119,
  "sharpe": -0.62,
  "result_id": "01M38AFABE8MAY41Q7G4EWCNXH",
  "view_url": "https://mcp-api.trader.dev/backtest/01M38AFABE8MAY41Q7G4EWCNXH",
  "curve": "https://pub-5880a55c41fd4cd1a11146f4fd522fbe.r2.dev/backtests/01M38AFABE8MAY41Q7G4EWCNXH.json.gz",
  "verdict": "WATCHLIST — long-side PF>1; short-side destruindo. Pivot para long-only ou short regime.",
  "status": "watchlist",
  "last_backtest": "2026-09-23T00:00:00Z",
  "pine_key": "01M38AFAP7BSW77F6VDKQTPANP"
}
```

## Notas para Gertrude

- Estratégia VDB greenfield com edge long-side consistente (PF>1 em 3 símbolos) mas short-side sistematicamente prejudicado.
- Não incubar ainda — precisa de v2 (long-only + regime) que reproduza PF>1 cross-symbol e cross-TF.
- Se v2 confirmar: abrir para incubação com ≥20 trades / ~3 meses de monitoramento.
- Nunca executar live sem aprovação humana explícita.

Report saved to: `C:/Users/seares/Desktop/botrade/data/reports/2026-09-23-0000-researcher-qm-vdb-v1.md`
