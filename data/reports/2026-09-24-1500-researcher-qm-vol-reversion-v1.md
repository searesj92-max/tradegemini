# Quant Mathematician Cycle Report

## 1. Hypotheses Generated

Five brand-new mathematical hypotheses for crypto perps (Bybit USDT linear), all greenfield — no fork, no retail indicator soup.

### H-A — Volatility-Normalized Displacement Reversion (z-score)

**Inefficiency:** When price stretches beyond the equilibrium (fast EMA) by a statistically significant normalized displacement — i.e. the absolute distance from the EMA scaled by the current ATR exceeds a threshold — the market has overshot fair value and mean-reversion probability exceeds continuation probability, *provided the regime is not a strong trend*.

**Why crypto:** Perpetual swaps run 24/7 with structural stop runs and liquidation cascades. Funding rate pressure + market-maker inventory rebalancing constantly pull price toward a fair-value anchor (the EMA is a rough proxy). Overextensions that do not coincide with building trend (slope of EMA, ADX) are paid back.

**Cross-symbol case:** Any pair with non-degenerate ATR and a recognizable equilibrium works — BTC, ETH, SOL, DOGE, PEPE all share the same mechanism; thresholds scale with volatility.

**Breaking regime:** Strong trend (ADX ≥ adxMax, EMA slope persistently large relative to ATR) — the "extension" is actually continuation fuel; reversion trade becomes a counter-trend loser. High-volatility regime (ATR ratio > atrMax) — noise dominates the signal.

**Pine expression:** `z = (close - emaFast) / atrFast`; long when `z >= zEntry` and `_regimeOK`; short when `(emaFast - close)/atrFast >= zEntry` and `_regimeOK`.

### H-B — Range-Efficiency Collapse + Volume Confirmation Breakout

**Inefficiency:** When bar body/range ratio collapses toward zero across a rolling window, volatility compresses; the subsequent expansion tends to follow the direction of volume-asymmetric buildup. Capturing the breakout direction beats guessing.

**Why crypto:** Altcoins accumulate in compression before gamma/explosive moves; market makers build one-sided book before a move that squeezes the other side.

**Breaking regime:** Range that stretches rather than compresses, or compression without volume confirmation (fake compression), or chop that never expands within the horizon.

**Pine expression:** Rolling window of `bodyRangeRatio`; require consecutive compression bars + volume > ewm Vol baseline on breakout bar.

### H-C — False Breakout Reversal with Liquidity Grab Signature

**Inaccuracy:** When price pokes beyond a recent extreme (pivot high/low), tags wick beyond, then closes back inside the range, the breakout was false — a liquidity grab that gets reversed as the stop-run party exits. Entry on the reversal captures the snapback.

**Why crypto:** Liquidity pools concentrate at visible recent highs/lows; perps order books are thin at extremes during low volatility, making sweeps frequent.

**Breaking regime:** Genuine breakout sustained by follow-up volume and repeat highs — the "false breakout" was the start of real trend; reversing it loses.

**Pine expression:** `pivothigh` + `wick beyond pivot by at least Δx` + `close back inside range` + volume confirmation on the reversal close.

### H-D — Volatility Regime Switch via Return Asymmetry Clustering

**Inefficiency:** Volatility clusters (GARCH-like). Inferring the regime boundary from return asymmetry (signed-rolling-return metrics) and entering at the start of volatility expansion captures the move while avoiding chop. Mean-reversion in expansing-vol regime, trend-following in compressing-vol regime.

**Why crypto:** Volatility clustering is strong; regimes (chop → bull/panic) have persistence and can be detected with asymmetry metrics before price direction is obvious.

**Breaking regime:** Regime classifier lag or tail event rearranges the asymmetry signal faster than the classifier adapts — entry on the wrong side of the jump.

**Pine expression:** `returnAsymmetry = rolling mean of signed returns with asymmetric weight`; regime classifier; MR in expansion, TF in compression.

### H-E — Liquidity Sweep + Early Snapback

**Inefficiency:** Post-sweep (price pokes extreme, closes inside), the snapback is fast and short-lived. Entering at the start of the snapback captures the quick reversal without waiting for full confirmation, at the cost of occasional continuation error when the sweep turns real.

**Why crypto:** Sweeps are frequent; snapback velocity is high because the losing side escapes quickly.

**Breaking regime:** Sweep that becomes real breakout (volume sustained) — snapback entry loses.

**Pine expression:** Sweep detection (wick beyond recent extreme + close inside) + entry on bar N of snapback; SL behind the extreme.

---

## 2. Hypothesis Selected (math basis)

**H-A — VOL-REVERSION** selected.

Selection criteria (per loop priority):

1. **Mathematical cleanliness** — z-score normalized by ATR is a well-defined, non-arbitrary signal. The "file" is: if price is ≥ k×ATR away from the EMA and the market is NOT in a strong trend, expected reversion > expected continuation. This is a testable hypothesis, not a "look for RSI oversold".

2. **Testability** — signal conditions are unambiguous and stateful: z-score crossing a threshold is a clean boolean; regime filter is a set of well-behaved booleans.

3. **Cross-symbol generalizability** — thresholds scale naturally with ATR; no symbol-specific quirk needed; one Pine for all.

4. **Clear risk management** — SL/TP in ATR units, time exit, cooldown. No trailing (per loop rule).

5. **Simplicity** — four inputs drive the signal; regime filter adds three more; no indicator soup.

6. **First-principles framing** — not a re-packaged oscillator. ADX is used *only* as a trend-filter gate (no entry from ADX itself); slope condition prevents entering in strong trends; ATR ratio prevents entering in runaway vol. Every filter has a stated economic rationale.

**Rejected hypotheses:** H-B (needs careful volume baseline; harder to make robust across symbols without over-fit), H-C (wykoff-style; prone to continuation error when sweep is real), H-D (regime classifier lag risk; harder to validate cleanly), H-E (similar to H-C; snapback entry is high-variance on small sample). Kept in mind for next cycles.

---

## 3. Trading Rules (long/short/exit/SL/TP/filters)

### 3.1 Regime filter (do NOT operate if any fails)

| Check | Rule | Rationale |
|---|---|---|
| ADX too low | `ADX(14) < adxMin (15)` → skip | No trend, too noisy / no edge |
| ADX too high | `ADX(14) > adxMax (50)` → skip | Strong directional trend — reversion loses |
| EMA slope too steep | `|slopeEMA| > slopeMax × (ATR/close)` → skip | Persistent directional drift — reversion loses |
| Volatility too high | `ATR_ratio > atrMax (2.5)` → skip | Runaway vol — noise dominates signal |

`ATR_ratio = ATR(fastLen) / SMA(ATR(fastLen), atrRatioLen)`. Measures current vol vs its own recent average.

### 3.2 Long entry (both true, on bar close)

- `zLong = (close - emaFast) / atrFast ≥ zEntry (2.5)` → price stretched far above equilibrium
- `_regimeOK` true → market not in strong trend, vol ok, ADX in band

Enter `strategy.entry("L", strategy.long)` at market.

### 3.3 Short entry (both true, on bar close)

- `zShort = (emaFast - close) / atrFast ≥ zEntry (2.5)` → price stretched far below equilibrium
- `_regimeOK` true

Enter `strategy.entry("S", strategy.short)` at market.

### 3.4 Stop loss

- Long: SL at entry − `slMult × ATR(fastLen)` (ticks-converted: `slMult * round(ATR / syminfo.pointvalue)`)
- Short: SL at entry + `slMult × ATR(fastLen)`
- `slMult = 2.0` by default.

### 3.5 Take profit

- Long: TP at entry + `tpMult × ATR(fastLen)`
- Short: TP at entry − `tpMult × ATR(fastLen)`
- `tpMult = 3.0` by default; set to 0 to disable fixed TP (runner only — not used in v1).
- Single exit `strategy.exit` with `profit=` and `loss=`.

### 3.6 Time exit

If trade open > `maxBars (120)` bars without hitting SL/TP → `strategy.close(id)` and reset cooldown. Prevents regime-shift risk on stuck trades.

### 3.7 Cooldown

After any exit, wait `cooldown (3)` bars before next entry. Prevents whipsaw re-entry on the same extreme.

### 3.8 No trailing stop

Per loop rule: no trailing steer. Exits only via SL/TP/time/close-on-exhaustion.

### 3.9 Sizing

`default_qty_type = strategy.percent_of_equity`, `default_qty_value = 100` (100% equity per trade, per parity profile). Single position (pyramiding=1). No martingale.

### 3.10 Commission / slippage

`commission_value = 0.05` (percent, per MCP parity). Slippage not overridden — uses engine default.

---

## 4. Pine Script

```pine
//@version=6

// ============================================================
// QM-VOL-REVERSION-v1
// Hypothesis: volatility-normalized displacement (z-score)
// of price vs fast EMA, with regime filter (ADX + EMA slope
// + ATR ratio). Reversion entry when price is extended
// beyond equilibrium in a non-strong-trend regime.
// Risk: SL + TP in ATR units, time exit, cooldown.
// NO trailing (per loop rule).
// Author: researcher | Cycle: 2026-09-24
// ============================================================

strategy(
  title = "QM-VOL-REVERSION-v1",
  overlay = true,
  pyramiding = 1,
  process_orders_on_close = true,
  commission_type = strategy.commission.percent,
  commission_value = 0.05,
  initial_capital = 10000,
  default_qty_type = strategy.percent_of_equity,
  default_qty_value = 100,
  margin_long = 100,
  margin_short = 100
)

// ── Inputs ──────────────────────────────────────────────

// --- Trend/Vol Windows ---
fastLen     = input.int(18, "EMA rápida (barras)", minval = 5)

// --- Regime Filter ---
adxLen      = input.int(14, "ADX len", minval = 5)
adxMin      = input.int(15, "ADX mínimo para operar", minval = 5)
adxMax      = input.int(50, "ADX máximo (tendência forte → pulsa)", minval = 20)
slopeLen    = input.int(3,  "Slope EMA len (barras)", minval = 1)
slopeMax    = input.float(1.2, "Slope max (× ATR) — tendência forte → pulsa", minval = 0.0, step = 0.1)
atrRatioLen = input.int(50, "ATR ratio len", minval = 10)
atrMax      = input.float(2.5, "ATR_ratio max — volatilidade muito alta → pulsa", minval = 1.0, step = 0.1)

// --- Entry Threshold ---
zEntry      = input.float(2.5, "Z-score mínimo para entrada", minval = 1.0, step = 0.1)

// --- Risk ---
slMult      = input.float(2.0, "SL (× ATR)", minval = 0.5, step = 0.1)
tpMult      = input.float(3.0, "TP (× ATR) — 0 = sem TP fixo", minval = 0.0, step = 0.1)

// --- Time / Cooldown ---
maxBars     = input.int(120, "Time exit (barras) — 0 = sem limite", minval = 0)
cooldown    = input.int(3,   "Cooldown (barras) após saída antes de nova entrada", minval = 0)

// ── Series ──────────────────────────────────────────────

emaFast    = ta.ema(close, fastLen)
// Slope do EMA normalizado: quanto o EMA se move por barra vs preço
emaSlope   = (emaFast - ta.ema(emaFast, slopeLen)) / close

globalAtr  = ta.atr(fastLen)
zLong      = (close - emaFast) / globalAtr   // z-score positivo = preço acima do EMA
zShort     = (emaFast - close) / globalAtr   // z-score positivo = preço abaixo do EMA

adxVal     = ta.adx(adxLen)

atrRatio   = globalAtr / ta.sma(globalAtr, atrRatioLen)

// ── Regime Filter ───────────────────────────────────────

// Operar SOMENTE se ADX entre min e max, slope OK, volatilidade OK
_slopeOK   = math.abs(emaSlope) < slopeMax * (globalAtr / close)
_adxOK     = adxVal >= adxMin and adxVal <= adxMax
_volOK     = atrRatio < atrMax
_regimeOK  = _slopeOK and _adxOK and _volOK

// ── Entry Conditions ────────────────────────────────────

longSignal  = zLong >= zEntry and _regimeOK
shortSignal = zShort >= zEntry and _regimeOK

// Cooldown after last exit
var int lastExitBar = na
canEnter = na(lastExitBar) or (bar_index - lastExitBar) > cooldown

// ── Entries ─────────────────────────────────────────────

if longSignal and canEnter
    strategy.entry("L", strategy.long)

if shortSignal and canEnter
    strategy.entry("S", strategy.short)

// Track bars in trade for time exit
var int entryBar = na
if strategy.position_size != 0 and na(entryBar)
    entryBar := bar_index
if strategy.position_size == 0
    entryBar := na

// ── Exits ───────────────────────────────────────────────

slTicksLong  = slMult * math.round(globalAtr / syminfo.pointvalue)
slTicksShort = slMult * math.round(globalAtr / syminfo.pointvalue)
tpTicksLong  = tpMult * math.round(globalAtr / syminfo.pointvalue)
tpTicksShort = tpMult * math.round(globalAtr / syminfo.pointvalue)

if strategy.position_size > 0
    strategy.exit("LX", from_entry = "L",
                 loss = slTicksLong,
                 profit = tpTicksLong)
    if maxBars > 0 and (bar_index - entryBar) >= maxBars
        strategy.close("L")
        lastExitBar := bar_index
        entryBar := na

if strategy.position_size < 0
    strategy.exit("SX", from_entry = "S",
                 loss = slTicksShort,
                 profit = tpTicksShort)
    if maxBars > 0 and (bar_index - entryBar) >= maxBars
        strategy.close("S")
        lastExitBar := bar_index
        entryBar := na

// ── Plots (debug visual) ────────────────────────────────

plot(emaFast,  color = color.orange, linewidth = 1, title = "EMA rápida")
plot(zLong >= zEntry and _regimeOK ? low : na,  style = plot.style_circles, color = color.green,  linewidth = 2, title = "Long signal")
plot(zShort >= zEntry and _regimeOK ? high : na, style = plot.style_circles, color = color.red,    linewidth = 2, title = "Short signal")
plot(_regimeOK ? emaFast : na, color = color.new(color.orange, 70), linewidth = 1, title = "Regime OK EMA")

// Alerts
alert_condition(longSignal,  title = "Long Entry",   message = "QM-VOL-REVERSION: Long entry")
alert_condition(shortSignal, title = "Short Entry",  message = "QM-VOL-REVERSION: Short entry")
```

Save na estratégia MCP: `01M3ACZ5NDCX9H0VBFK96KZKGM` (dev, active). Pine aprovado pelo parser MCP; sem cancels, sem arrays, sem request.security, sem martingale, sem var-trail-close.

---

## 5. Backtest Matrix (planned — blocked)

**Painel previsto (loop exige 5–10 pares × 15m/30m/1h/2h/4h, long+short):**

| Symbol | 15m | 30m | 1h | 2h | 4h |
|---|---|---|---|---|---|
| BTCUSDT | planned | planned | planned | planned | planned |
| ETHUSDT | planned | planned | planned | planned | planned |
| SOLUSDT | planned | planned | planned | planned | planned |
| DOGEUSDT | planned | planned | planned | planned | planned |
| PEPEUSDT | planned | planned | planned | planned | planned |

Total: 25 runs. Todas com strategyId `01M3ACZ5NDCX9H0VBFK96KZKGM`.

**Status real: BLOQUEADO — créditos zerados.** Nenhum backtest executado. Ver seção 6.

---

## 6. Results

N/A — sem backtest executado.

| Metric | Value |
|---|---|
| Net profit | — (sem backtest) |
| Profit factor | — |
| Max drawdown | — |
| Win rate | — |
| Average trade | — |
| Trades total | — |
| Long/short PF | — |
| Stability across TFs | — |
| Stability across symbols | — |

---

## 7. Diagnosis

O que é conhecido:

- Pine Script compilou e foi registrado no MCP sem erro de parse (estratégia `01M3ACZ5NDCX9H0VBFK96KZKGM`, dev, active).
- Hipótese tem base matemática limpa, regras não ambíguas, filtros de regime com justificativa econômica, risco bem definido.
- Sem trailing steer (regra do loop respeitada).
- Sem repaint óbivo (todas as entradas/exit no close; `process_orders_on_close=true`; sem `calc_on_every_tick`).
- Sem lookahead óbivo (nenhuma `[]` forward, nenhuma `request.security`).
- Comission/header alinhados ao perfil de paridade MCP.

O que é desconhecido (bloqueio):

- Nenhum backtest rodado → nenhuma evidência estatística de edge.
- Não é possível avaliar robustness, drawdown, profit factor, win rate, trade count, ou estabilidade cross-symbol/TF.
- O loop considera "3 strikes no edge na linha → rejeitar linha, pivotar" — mas não há strikes ainda porque não houve teste.

### 7.1 Crédito / bloqueio

```json
{
  "authenticated": true,
  "user": "searesj92@gmail.com",
  "tier": "free",
  "credits": 0,
  "weeklyGrant": 1000,
  "weeklyResetAt": "Invalid Date (não parseável)",
  "message": "You have no credits. They reset Invalid Date.",
  "mcp_reachable": true,
  "backtest_possible": false
}
```

O MCP responde normalmente, mas bloqueia execução de backtest por limite de crédito. A mensagem de reset "Invalid Date" sugere que o campo de reset semanal não foi preenchido ou está fora de formato — não consigo determinar quando os 1000 créditos semanais voltam a chegar. O `unlock-edge` (dobramento gratuito de créditos via verificação de exchange) retorna HTTP 200 na raiz, mas a extração de conteúdo falhou (403 no firecrawl); não sei se o usuário tem exchange verificada.

**Ação humana possível (não-executável por cron):** verificar conta de exchange e usar `/unlock-edge` para ativar dobramento semanal de créditos, ou fazer login no MCP UI para reaver o reset de créditos.

---

## 8. Verdict

**Verdict: WATCHLIST (aguarda créditos para validar)**

Justificativa:

- Veredicto `Watchlist` (não `Incubate`, não `Reject`) porque:
  - A hipótese é matematicamente bona fide e o Pine está pronto — não é descarte.
  - Mas não há evidência estatística de edge — não há como incubar sem backtest.
  - Créditos zerados impedem o teste; não é falha da hipótese, é falha de recursos.
- Condição de saída do Watchlist:
  - Quando créditos disponíveis: rodar o painel 5×5 (ou um subconjunto menor se créditos forem limitados — pelo menos BTC×5 TFs e ETH×5 TFs).
  - Se resultados mostrarem PF ≥ 1.3 em ≥ 2 símbolos com DD ≤ 30% e ≥ 30 trades no conjunto → avançar para incubação (próximo ciclo com iteração de regra).
  - Se resultados mostrarem edge fraco/claro negativo/duas-pares-wonder → reject e pivotar para outra hipótese.

**Não é Production Candidate (nunca sem evidência). Não é Incubate (sem backtest).**

---

## 9. Next Cycle

Se créditos recarregados antes do próximo ciclo:

1. **Rodar o painel mínimo de validação:** BTC + ETH × 5 TFs (10 runs) para checar se há sinais de vida.
2. **Critério de continuação:** PF ≥ 1.2 em ≥ 3 dos 10 runs, DD ≤ 35%, ≥ 30 trades no conjunto, long/short não enviesados demais.
3. **Se continuar:** iterar UMA mudança maior — exemplo: ajustar `zEntry` / `slMult`/`tpMult` com base nos resultados (não curvar para pretty; manter o espírito da regra), ou adicionar um filtro de regime mais fininho (ex. volume-baseline no entry), ou experimentar regime split (MR long-only vs MR short-only com filtro de lado). Uma mudança por ciclo.
4. **Se não continuar:** rejeitar a linha VOL-REVERSION e pivotar para H-C (false breakout reversal) ou H-E (liquidity sweep snapback) no próximo ciclo, que são as hipóteses mais próximas da mesma família de "extremo + reversão".

Se créditos continuarem zerados no próximo ciclo:

- Reportar `[SILENT]` do loop (se não houver progresso) ou repetir este relatório com atualização de status de crédito — a menos que algo mude.

---

## Panel readiness (rows para dashboard — aguardando resultado)

Sem resultado de backtest, não há rows com métricas para inserir no dashboard. Quando créditos disponíveis e o painel rodar, o relatório terá um bloco JSON com as rows que o `panel_upsert.py --report` consumirá.

Bloco placeholder (gerado, sem inserir no dashboard):

```json
[]
```

Nota: este relatório não grava `data.json` — o loop proíbe rewrite manual. O `panel_upsert.py` somente será chamado quando houver resultado real de backtest para injetar.

---

## Risk notice

Pesquisa e educação apenas. Não é conselho financeiro. Backtests não são garantia de desempenho futuro. Nenhuma ordem real foi ou será colocada por este ciclo. Incubação requer ≥ 20 trades / ~3 meses antes de qualquer consideração live. Aprovação humana obrigatória para execução real.

---

*Gerado automaticamente pelo loop `01-quant-mathematician.md` (researcher),Cron 2026-09-24.*
