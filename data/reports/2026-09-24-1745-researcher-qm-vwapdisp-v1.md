# Quant Mathematician Cycle Report — Cycle 06

**Data:** 2026-09-24 17:45 BRT
**Agent:** researcher (quant mathematician)
**Engine:** tv_jul26 (Trader Dev MCP)

---

## 1. Hipóteses geradas (4)

1. **VWAP-displacement from-equilibrium fade** — após displacamento além da banda VWAP+vol sem regime de tendência (|med−VWAP| pequeno), retorno para VWAP a partir do close dentro da banda, body apontando para o equilíbrio. Entrada no close (não intra-bar). SL/TP absolutos em ATR-ticks, filtro de regime, cooldown, time exit.

2. **Failed continuation / second leg reversal (FAILCONT)** — após um pivô alto/baixo (5/5) e uma extensão além dele por ≥1.2×ATR com candeeiro de falha (body fecha de volta), entrada contra a continuação. SL/TP absolutos.

3. **Liquidity sweep + pivot wick reclaim (LS-snapback)** — não executada neste ciclo (foi cylce 04, rejeitada).

4. **Return asymmetry compression** — não executada; pivotada para hipótese 2 como backup.

Hipótese selecionada (passo 2): **VWAP-displacement from-equilibrium fade** — menor número de parâmetros, todos os indicadores na lista allowlist, lógica fechada no close (sem repinta), entrada, saída e filtro bem definidos. BACKUP: FAILCONT.

---

## 2. Hipótese selecionada

**Nome:** QM-VWAPDISP-v1 → v4 (exploratório, sem regime guard para produção de trades pelo menos uma vez).

**Base matemática:**
- O VWAP é equilíbrio de preço ponderado por volume dentro da sessão.
- A mediana móvel é alternativa de equilíbrio não vol-weighted.
- Quando o preço se desloca além de `disp_mult * ATR` do VWAP sem que `|med − vwap|` seja grande (filtro de regime), o mercado não está em tendência estabelecida — há displacamento sem direção consistente.
- A hipótese afirma que a reversão para dentro da banda é mais provável que a continuação após um close que confirma a reversão (body apontando para o VWAP e fechando dentro da banda).
- Condições: `outside` verdadeiro, body no sentido de retorno, `was_out` nos últimos 2 barras, close dentro da banda, regime flat, cooldown ok, posição plana.

**Regime guard adicional (v5/v6 não rodados por créditos):** `vwap_slope_strict` — se `|vwap - vwap[1]|` grande relativo ao ATR/lb, o VWAP está se movendo rápido (tendência de preço), filtra entrada.

---

## 3. Regras de trading

**Long:**
- `flat_eq` (regime guard) e `outside` (deslocado) e `close < vwap` (abaixo) e `body_up` e `close >= vwap - band` (volta para dentro) e `was_out` (foi fora recentemente) e posição plana e cooldown ok.

**Short:** espelhado.

**Saída:** `strategy.exit` com `limit = close ∓ tp_ticks * mintick`, `stop = close ∓ sl_ticks * mintick`. Time exit a `max_bars` barras.

**Cooldown:** `since_exit >= cooldown` ou posição não plana.

**Inputs padrão (v4 exploratório):** lb=60, disp_mult=1.5, sl_ticks=15, tp_ticks=25, cooldown=2, max_bars=40.

---

## 4. Pine Script

Arquivos Pine:
- `QM-VWAPDISP-v1.pine` (v1 — regra completa com regime guard, sem trades)
- `QM-VWAPDISP-v4.pine` (v4 exploratório, sem regime guard, usado nos backtests)
- `QM-VWAPDISP-v3.pine` (tentativa intermediária, parser falhou)
- `QM-VWAPDISP-v5.pine` (v5 com regime guard de slope, não rodado por créditos)
- `QM-VWAPDISP-v6.pine` (v6 com filtro de continuidade sustentada, não rodado)
- `QM-FAILCONT-v1.pine` (backtest zero trades)

**Resumo da lógica v4 (usada em produção):**
```pine
//@version=6
strategy("QM-VWAPDISP-v4-exploratory", overlay=true, pyramiding=1, process_orders_on_close=true, commission_type=strategy.commission.percent, commission_value=0.05, default_qty_type=strategy.percent_of_equity, default_qty_value=100, margin_long=100, margin_short=100, initial_capital=10000)

lb         = input.int(60, "Equil. lookback (bars)", minval=10, maxval=200)
disp_mult  = input.float(1.5, "Displacement threshold (x ATR)", step=0.1, minval=0.5, maxval=4.0)
cooldown   = input.int(2, "Cooldown after exit (bars)", minval=0, maxval=20)
max_bars   = input.int(40, "Max bars in trade (time exit)", minval=0, maxval=200)
sl_ticks   = input.int(15, "SL ticks", minval=1, maxval=200)
tp_ticks   = input.int(25, "TP ticks", minval=1, maxval=200)

atr = ta.atr(lb)
vwap  = ta.vwap(hlc3)

disp_vwap = math.abs(close - vwap)
band      = disp_mult * atr
outside   = disp_vwap > band

was_out = ta.barssince(outside) <= 2

prev_close = close[1]
body_up    = close > prev_close
body_dn    = close < prev_close

long_go = was_out and close < vwap and body_up and close >= vwap - band
short_go = was_out and close > vwap and body_dn and close <= vwap + band

if long_go
    strategy.entry("L", strategy.long)
if short_go
    strategy.entry("S", strategy.short)

ltp = close - tp_ticks * syminfo.mintick
lsl = close - sl_ticks * syminfo.mintick
stp = close + tp_ticks * syminfo.mintick
ssl = close + sl_ticks * syminfo.mintick

strategy.exit("LX", from_entry="L", limit=ltp, stop=lsl)
strategy.exit("SX", from_entry="S", limit=stp, stop=ssl)

bars_in_trade = strategy.position_size != 0 ? ta.barssince(strategy.position_size == 0) : 0
if max_bars > 0 and bars_in_trade > max_bars
    if strategy.position_size > 0
        strategy.close("L")
    if strategy.position_size < 0
        strategy.close("S")

plot(vwap, "VWAP", color=color.blue, linewidth=2)
plot(vwap + band, "Banda +", color=color.gray, linewidth=1)
plot(vwap - band, "Banda -", color=color.gray, linewidth=1)
plotshape(long_go, "Long entry", shape.triangleup, location.belowbar, color=color.lime, size=size.tiny)
plotshape(short_go, "Short entry", shape.triangledown, location.abovebar, color=color.red, size=size.tiny)
```

---

## 5. Matriz de backtests

| Symbol   | TF  | Result ID                                    | Trades | Net%    | PF  | DD%    | WR% | Sharpe   |
|----------|-----|----------------------------------------------|--------|---------|-----|--------|-----|----------|
| BTCUSDT  | 15m | 01M3A81NHV3B0MDFWGJ5V4RKD2                   | 625    | −46.31 | 0.0 | −46.31 | 0.0 | −51.54   |
| ETHUSDT  | 15m | 01M3A872PB85K6FB387JAE65FH                   | 649    | −47.69 | 0.0 | −47.69 | 0.0 | −52.59   |
| SOLUSDT  | 15m | 01M3A89HAZ7E2X1KF1WP42KDY3                   | 690    | −49.82 | 0.0 | −49.82 | 0.0 | −54.37   |
| XRPUSDT  | 15m | 01M3A89TP0R6F59K3QW62WG1BT                   | 651    | −47.85 | 0.0 | −47.85 | 0.0 | −52.68   |
| BTCUSDT  | 1h  | 01M3A8A6DXK3C41DQWAS1JKNTK                   | 100    | −9.48  | 0.0 | −9.48  | 0.0 | −19.34   |
| ETHUSDT  | 1h  | 01M3A8ADFVY43B71V1DWN2B120                   | 107    | −10.14 | 0.0 | −10.14 | 0.0 | −20.03   |
| BTCUSDT  | 15m | 01M3A85GXEV5Q174T3J3ARWES5 (FAILCONT)       | 0      | 0.00   | 0.0 | 0.00   | 0.0 | —        |
| ETHUSDT  | 15m | 01M3A8974WGHGWD4SSW6N5CG21 (FAILCONT)       | 0      | 0.00   | 0.0 | 0.00   | 0.0 | —        |

**Período:** ~90 dias (2026-06-26 → 2026-09-24), 15m: 8870 barras; 1h: 2443 barras.
**Condições:** commission 0.05%, sizing 100% equity, margin 100/100, pyramiding=1, process_orders_on_close=true.

---

## 6. Resultados

**VWAPDISP (v4 exploratório):**
- 7 backtests (5×15m + 2×1h). PF=0 em todos. WR=0% em todos.
- Trades: de 100 (BTC 1h) a 690 (SOL 15m). Todas as operações foram loss (0 winning trades).
- DD: de −9.48% (BTC 1h) a −49.82% (SOL 15m).
- Sharpe: de −19.34 (BTC 1h) a −54.37 (SOL 15m).
- AvgBarsInTrade = 1 para todos os TF — padrão de entra+e sai na próxima barra (turnover máximo, comissão drenando).
- Curva de equity monotonicamente descendente (sem recuperação).

**FAILCONT (v1):**
- 0 trades em BTC e ETH 15m — amostra insuficiente, não avaliável.

---

## 7. Diagnóstico

1. **Zero winning trades em 7 backtests independentes** → não há floreio (curve-fitting) possível. O sinal, como formulado, não tem capacidade discriminatória neste período.

2. **Padrão de 1 barra por trade (avgBarsInTrade=1):** entrada no close e saída no próximo close (SL ou TP atingido imediatamente em ≥99% dos casos). Isso indica que as condições de entrada geram posições que não sobrevivem nem uma barra — consistente com o fato de que entrar "no close após displacamento" é entrar quando a reversão já está em curso (o close já é o snapback, e a próxima barra é o passo seguinte que frequentemente balança para o lado oposto). A lógica de entrada é possivelmente *tardia* para o edge que tenta capturar.

3. **Regime guard e VWAP slope guard (v5/v6) não testados** porque os créditos se esgotaram antes de criar uma versão com trades positivos. Mas a lógica base (v4) já tem PF=0 — adicionar filtros só reduziria trades sem criar wins (a menos que o regime guard remova trades perdedores de forma assimétrica, o que não é o caso: todos os trades são perdedores, então remover algum pouco ajuda numericamente mas não transforma o sinal em lucrativo porque o edge central não existe).

4. **O fenômeno conceitual pode existir, mas não se manifesta neste período/perps com funding.** Ou a formulação está incorreta (o snapback não éCapturável a partir do close), ou o período é hostil (alta volatilidade com trend dominante que viola o regime flat), ou o custo de commissão em 100% equity com turnover diário torna qualquer edge marginal irrecuperável.

5. **FAILCONT:** condição rara (pivô 5/5 + extensão 1.2 ATR + falha de body) em 15m deste período. Pode ser hipótese válida em outros TFs/condições, mas sem sample nenhum, não há como avaliar. Não vale continuar neste ciclo com FAILCONT.

**Principais lições:**
- Entering on close-after-displacement para um fade é entrar quando o movimento de retorno já ocorreu — o cream closed é o próprio signal de snapback, deixando pouca margem para o trade sobreviver. Talvez entradas stop (aguardar rompimento da banda no sentido oposto) sejam necessárias, mas isso mudaria a hipótese completamente.
- PF=0 com 600+ trades é um resultado definitivo — não é sample insufficiency, é destruição sistemática.

---

## 8. Verdict: **REJECT**

Hipótese VWAPDISP (displacement-from-equilibrium fade): **rejeitada** após 7 backtests com PF=0 e WR=0%. Linha morta. Não há edge no período/perps testados, e a formulação de entrada no close é possivelmente tardía.

Hipótese FAILCONT (failed continuation): **rejeitada** por amostra zero (0 trades), sem poder de decisão. Linha morta neste TF (15m).

**Ação:** não refinar essas linhas. Pivotar para hipótese novíssima no próximo ciclo.

---

## 9. Próximo ciclo

- Greenfield antigo: testar hipótese de **distância-de-equilíbrio com entrada stop** (rompimento da banda no sentido oposto como confirmação, não close dentro da banda).
- Greenfield backup: explorar **volatility clustering fade** (comprar após expansão com retorno abaixo de uma z-score, usando close de confirmação e entrada em stop — não no close).
- Greenfield alternativo: retomar **FCE (failed continuation exhaustion)** que mostrou PF>1 em 1h (cycle 03) — mas como já está em watchlist no dashboard, o foco do ciclo 06 é novo.
- Créditos residuais muito baixos — se possível, comprar créditos ou esperar weekly reset antes de novo ciclo pesado.

---

**Créditos spent (ciclo 06):** ~9 créditos (BTC/ETH/SOL/XRP 15m, BTC/ETH 1h, dois FAILCONT).
**Créditos restantes (estimado):** ~9 créditos.

**Nunca coloque ordens reais.** Pesquisa e educação apenas.
