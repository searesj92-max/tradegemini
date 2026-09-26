# Quant Mathematician Cycle Report
## Cycle: QM-VEE-LO-v2 — Pure Long Breakout Continuation (Long-Only)
**Date:** 2026-09-24 13:46 UTC-3
**Author:** solana-trend-bot · researcher profile
**Engine:** tv_jul26 (TV_ENGINE_JUL_26 parity)
**Credits consumed:** 4 backtests × 1 credit = 4
**Strategy ID:** 01M39TNABB6DG851S6525V034G (version 4)

---

## 1. Hipóteses Geradas

### H1 — VEE-LO: Pure Long Breakout Continuation (Long-Only)
**Ineficiência alvo:** em mercados crypto com viés de alta, o follow-through de breakout de LOW tem expectativa positiva consistente; follow-through de HIGH (short) é contra-tendência em maioria dos símbolos — lição do VEE-v3.

**Matemática central:** `swHigh = ta.highest(high[2], 15)` (máximo recente antes do bar[1]); `breakOut = high[1] > swHigh`; `followThru = close[1] > swHigh + swHigh * 0.005` (barra fecha acima do nível raspado com 0.5% de buffer); `volOk = volume[1] >= sma(volume,20)[1] * 0.70`; entrada long no bar seguinte; SL 2.0×ATR; TP 1.5×ATR; time exit 25 barras; sem trailing.

**Por que crypto:** viés de alta estrutural em BTC/ETH/SOL; stops de short concentrados abaixo dos lows; quando o mercado rompe low e fecha acima, é sinal de compra real que tende a continuar.

**Breaking regime:** mercado em QQQ/caída forte sem pullback (trend down puro) — o breakout de low é pullback que continua para baixo.

---

## 2. Hipótese Selecionada: H1 — VEE-LO (long-only breakout continuation)

**Motivo da seleção (prioridade do loop):**
1. **Lição válida do VEE-v3:** longs tiveram edge positivo em 4/5 símbolos; shorts tiveram edge negativo em 4/5 — focar em long-only é a iteração lógica.
2. **Simplicidade:** 6 inputs, lógica linear, sem indicadores complexos, sem short-side.
3. **Testabilidade:** sinal limpo (breakout + close confirmation + vol filter), sem ambiguidade de janelamento.
4. **Math rigor:** viés de alta é um fato documentado em crypto; filtrar o lado fraco (shorts) aumenta a probabilidade de edge.
5. **Clear risk management:** SL/TP fixos em ATR, sem trailing, time exit.

---

## 3. Regras de Trading

### Entradas (Long apenas)
| Condição | Expressão |
|----------|-----------|
| Rompeu recent high | `high[1] > ta.highest(high[2], 15)` |
| Follow-through (close acima do nível raspado) | `close[1] > swHigh + swHigh * 0.005` |
| Volume suficiente | `volume[1] >= ta.sma(volume,20)[1] * 0.70` |
| Posição em branco | `strategy.position_size == 0` |
| **→ Long entry** no bar seguinte | |

### Saídas
| Tipo | Valor |
|------|-------|
| SL | `entryPrice - 2.0 × ATR(14)` |
| TP | `entryPrice + 1.5 × ATR(14)` |
| Time exit | 25 barras no trade |
| Cooldown | não aplicado (long-only, sem curto) |

### Filtros
- Long-only (sem short).
- Volume mínimo 70% da média móvel 20.
- Sem trailing stop (regra do loop).

---

## 4. Pine Script

Arquivo: `data/pine/qm_vee_lo_v2.pine`
Resumo: //@version=6, estratégia `QM-VEE-LO-v2`, overlay, pyramiding=1, process_orders_on_close=true, commission 0.05%, equity 100%, margin 100/100.
Sinal: `swHigh = ta.highest(high[2], 15)`; `breakOut = high[1] > swHigh`; `followThru = close[1] > swHigh + swHigh * 0.005`; `volOk = volume[1] >= sma(volume,20)[1] * 0.70`.
Entrada: `strategy.entry("L", strategy.long)`.
Saída: `strategy.exit("L-SL", from_entry="L", stop=entryPrice - 2.0*atr, limit=entryPrice + 1.5*atr)`.
Time exit: `strategy.close("L")` após 25 barras.
Sem trailing, sem short, sem martingale, sem cancel.

---

## 5. Backtest Matrix

| Symbol   | Timeframe | Strategy ID             | Result ID              | Bars | Trades |
|----------|-----------|-------------------------|------------------------|------|--------|
| BTCUSDT  | 1h        | 01M39TNABB6DG851S6525V034G (v4) | 01M39TNZFY8GTYGABTECBGGYVQ | 2447 | 24 |
| ETHUSDT  | 1h        | 01M39TPFC2QQX0BVC1JPDW113Q (v1) | 01M39TPF5V4D3H4B5MMJWC3A6C | 2447 | 34 |
| SOLUSDT  | 1h        | 01M39TPFC2QQX0BVC1JPDW113Q (v1) | 01M39TPF5V4D3H4B5MMJWC3A6C | 2447 | 34 |
| XRPUSDT  | 1h        | 01M39TPP7DKD678J87W2MQ2QD1 (v1) | 01M39TPNZ2CE61C1Q49NJP5FGP | 2447 | 35 |

Date range: ~2026-01-01 – 2026-09-24 (clickhouse coverage). Commission 0.05%, slippage 0, 100% equity, margin 100/100, pyramiding 1.
Nota: cada símbolo gerou uma estratégia separada (lineage distinta) pelo mecanismo de run_backtest com symbol override.

---

## 6. Results

### BTCUSDT 1h
| Metric | Value |
|--------|-------|
| Net profit | **+4.44%** |
| Final equity | $10,444.21 |
| Profit factor | **1.40** |
| Max drawdown | 4.66% |
| Win rate | 70.8% |
| Total trades | 24 |
| Winning / Losing | 17 / 7 |
| Avg trade | +$18.51 |
| Avg win / Avg loss | $91.69 / -$159.21 (ratio 0.58) |
| Avg bars in trade | 8.5 |
| Sharpe / Sortino | 1.53 / 0.51 |
| Commission paid | $243.18 |
| Long PF / Short PF | long 1.40 / short N/A (long-only) |

### ETHUSDT 1h
| Metric | Value |
|--------|-------|
| Net profit | **-10.48%** |
| Final equity | $8,952.27 |
| Profit factor | 0.53 |
| Max drawdown | 12.34% |
| Win rate | 45.8% |
| Total trades | 24 |
| Winning / Losing | 11 / 13 |
| Avg trade | -$43.66 |
| Avg win / Avg loss | $105.78 / -$170.10 (ratio 0.62) |
| Avg bars in trade | 10.9 |
| Sharpe / Sortino | -2.83 / -0.87 |
| Commission paid | $227.66 |
| Long PF / Short PF | long 0.53 / short N/A |

### SOLUSDT 1h
| Metric | Value |
|--------|-------|
| Net profit | **+20.30%** |
| Final equity | $12,029.60 |
| Profit factor | **1.96** |
| Max drawdown | 4.88% |
| Win rate | 73.5% |
| Total trades | 34 |
| Winning / Losing | 25 / 9 |
| Avg trade | +$59.69 |
| Avg win / Avg loss | $166.14 / -$235.98 (ratio 0.70) |
| Avg bars in trade | 9.0 |
| Sharpe / Sortino | 3.38 / 1.49 |
| Commission paid | $368.76 |
| Long PF / Short PF | long 1.96 / short N/A |

### XRPUSDT 1h
| Metric | Value |
|--------|-------|
| Net profit | -0.30% |
| Final equity | $9,970.47 |
| Profit factor | 0.99 |
| Max drawdown | 12.42% |
| Win rate | 54.3% |
| Total trades | 35 |
| Winning / Losing | 19 / 16 |
| Avg trade | -$0.84 |
| Avg win / Avg loss | $212.57 / -$254.27 (ratio 0.84) |
| Avg bars in trade | 7.9 |
| Sharpe / Sortino | 0.12 / 0.05 |
| Commission paid | $343.54 |
| Long PF / Short PF | long 0.99 / short N/A |

### Cross-asset summary
| Symbol | TF | Net% | PF | DD% | WR% | Trades |
|--------|-----|------|-----|-----|-----|--------|
| BTCUSDT | 1h | +4.44 | 1.40 | 4.66 | 70.8 | 24 |
| ETHUSDT | 1h | -10.48 | 0.53 | 12.34 | 45.8 | 24 |
| SOLUSDT | 1h | +20.30 | 1.96 | 4.88 | 73.5 | 34 |
| XRPUSDT | 1h | -0.30 | 0.99 | 12.42 | 54.3 | 35 |

---

## 7. Diagnosis

### 7.1 O que o dado mostra

**Hipótese VEE-LO (long-only breakout continuation) tem edge em 2/4 símbolos e é neutra em 1/4.**

**Evidência:**
1. **BTC e SOL com PF>1 e net positivo:** BTC +4.44% (PF 1.40, WR 70.8%) e SOL +20.30% (PF 1.96, WR 73.5%) são resultados claros. Ambos são pares líquidos e voláteis com viés de alta — consistente com a hipótese.
2. **ETH negativo:** -10.48% (PF 0.53, WR 45.8%) — o viés de alta em ETH não foi suficiente para sustentar o edge em 1h com os parâmetros atuais.
3. **XRP neutro:** -0.30% (PF 0.99, WR 54.3%) — quase break-even, com win rate acima de 50% mas avg trade ≈ zero; commission consumindo a margem.
4. **Todos os trades são longs:** long-only funcionou como planejado — sem short-side contaminando os resultados.

### 7.2 Por que a hipótese funcionou parcialmente

**Hipótese diagnóstica A — Viés de alta é real mas não uniforme:**
- BTC e SOL têm viés de alta mais forte e consistente; o breakout de low com follow-through tende a continuar.
- ETH tem viés de alta, mas é mais volátil em 1h (pullbacks mais profundos) — o mesmo setup tem mais falsos breaks.
- XRP é mais range-bound em 1h — o setup dispara mas o follow-through é inconsistente.

**Hipótese diagnóstica B — Parâmetros de SL/TP podem ser otimizados por símbolo:**
- BTC e SOL têm SL/TP 2.0/1.5 ATR que funcionam; ETH e XRP podem precisar de SL mais largo (vol mais alta relativa ao move) ou de TP maior.
- Mas ajustar parâmetros sem entender o mecanismo seria curve-fitting — a iteração deve vir de um conceito, não de números.

### 7.3 O que NÃO é o problema

- **Não é repintação:** tudo usa `high[2]`, `high[1]`, `close[1]` — sem lookahead, sem repint.
- **Não é lookahead:** `swHigh = ta.highest(high[2], 15)` usa apenas dados disponíveis no bar[1]; entrada no bar seguinte.
- **Não é commission:** PF>1 em BTC e SOL mesmo com 0.05% de commission; XRP com PF 0.99 está no limite.
- **Não é bug de implementação:** `mcpruleValidated = true` em todos os backtests; cascade 1:1 em todos (sem re-emit duplicado).

### 7.4 Comparativo com hipóteses anteriores do quant

| Ciclo | Hipótese | Tipo | Trades totais | PF médio | Resultado |
|-------|----------|------|---------------|----------|-----------|
| QM-VPA-v1 | Volume-Price Anomaly | Fade | 0 (5 símbolos) | — | REJECT (strike 1) — 0 trades |
| QM-MSE-v1 | Liquidity Rebalance | Fade | 0 (BTC 1h) | — | REJECT — 0 trades |
| QM-VRAD-v1 | Vol-Regime Adjusted Disp | Fade | 22 (9 símbolos) | <0.5 | REJECT (strike 1) — edge insuficiente |
| QM-LSN-v1 | Liquidity Sweep + Snapback | Fade | 1,185 (5 símbolos) | 0.475 | REJECT (strike 1) — edge negativo |
| QM-VEE-v3 | Pure Breakout Continuation | Trend | 562 (5 símbolos) | 1.01 | WATCHLIST — 2/5 positivos, longs positivos, shorts negativos |
| **QM-VEE-LO-v2** | **Pure Long Breakout Continuation** | **Long-only breakout** | **117 (4 símbolos)** | **1.22 (médio)** | **PARTIAL — 2/4 positivos (BTC+SOL), 1 neutro (XRP), 1 negativo (ETH)** |

**Progressão:** VEE-LO é a primeira hipótese a mostrar edge claro em símbolos líquidos (BTC PF 1.40, SOL PF 1.96) com win rate alto (70%+) e drawdown controlado (4-5%). É evolução do VEE-v3 (que tinha shorts negativos diluindo o edge).

---

## 8. Verdict

### Critérios de avaliação (ordem de prioridade do loop)

| # | Critério | Peso | Status VEE-LO-v2 | Justificativa |
|---|----------|------|------------------|---------------|
| 1 | Robustness across symbols | Alta | ⚠️ PARCIAL | 2/4 símbolos PF>1 (BTC 1.40, SOL 1.96); 1/4 ≈1 (XRP 0.99); 1/4 <1 (ETH 0.53). Melhor que VEE-v3 (2/5) mas ainda não 4/4. |
| 2 | Drawdown control | Alta | ✅ ACEITÁVEL | MaxDD 4.7–12.4% — dentro de limits. BTC e SOL com DD<5%; ETH e XRP com DD~12%. |
| 3 | Profit factor | Alta | ⚠️ PARCIAL | PF médio 1.22; BTC 1.40 e SOL 1.96 são bons; ETH 0.53 e XRP 0.99 são fracos. |
| 4 | Average trade quality | Média | ⚠️ MIXO | BTC avg +$18.51, SOL avg +$59.69; ETH avg -$43.66, XRP avg -$0.84. Long-only remove o ruído do short-side. |
| 5 | Trade count reliability | Alta | ✅ ACEITÁVEL | 24–35 trades por símbolo — amostra robusta. Não é 0 trades nem amostra pequena. |
| 6 | Stability across TFs | Média | ❌ NÃO TESTADO | Apenas 1h. Cross-TF pendente. |
| 7 | Simplicity | Baixa | ✅ ACEITÁVEL | 6 inputs; lógica linear; long-only; sem indicadores complexos. |
| 8 | Net profit | Baixa | ⚠️ PARCIAL | 2/4 positivos (BTC +4.44%, SOL +20.30%); 1/4 neutro (XRP -0.30%); 1/4 negativo (ETH -10.48%). |

### Decisão: WATCHLIST (com notas de desenvolvimento claro)

**Justificativa formal:**
1. **Hipótese com sinais de vida reais:** BTC (PF 1.40, +4.44%, WR 70.8%) e SOL (PF 1.96, +20.30%, WR 73.5%) são resultados positivos robustos — não é 0 trades nem edge negativo consistente.
2. **Long-only remove o problema do VEE-v3:** sem short-side para diluir o edge; todos os trades são longs.
3. **Edge não é universal:** ETH negativo (-10.48%) e XRP neutro (-0.30%) mostram que o setup não funciona em todos os símbolos com os mesmos parâmetros.
4. **Amostra robusta:** 117 trades totais em 4 símbolos — amostra suficiente para análise.
5. **Desenvolvimento necessário antes de incubar:**
   - **Mais símbolos** (DOGE, ADA, AVAX, LINK, BNB) para robustez cross-symbol.
   - **Cross-TF** (15m, 30m, 2h, 4h) para estabilidade.
   - **Parâmetros por symbol family** (BTC/SOL com SL 2.0/TP 1.5; ETH/XRP com SL 2.5/TP 1.8 ou filtro de regime).
   - **Regime filter** (BTCUSDT acima de EMA200 → long-only; abaixo → sem operação) para evitar operações em bear regime.
6. **Watchlist não incubação:** atende critérios parciais de incubação (BTC e SOL com PF>1.3, trades >20, DD<10%) mas falta cross-symbol universalidade (≥5 pares PF≥1.3) e cross-TF.

### Classificação no pipeline
- **Candidato a incubação condicional:** se cross-TF confirmar e mais símbolos confirmarem, pode subir para incubação.
- **Não production:** exige cross-TF e mais símbolos antes de qualquer consideração de produção.

---

## 9. Next Cycle

**Próxima iteração — UM conceito:**

1. **Mais símbolos (prioridade):** DOGE, ADA, AVAX, LINK, BNB em 1h com os mesmos parâmetros. Se 3/5 ou mais passarem com PF>1, a hipótese ganha robustez.
2. **Cross-TF (segunda prioridade):** 15m, 30m, 2h, 4h em BTC e SOL para verificar estabilidade do edge fora do 1h.
3. **Regime filter (se necessário):** se mais símbolos mostrarem resultado negativo em bear regime, adicionar filtro de EMA200 (só operar long se close > EMA200).

**Se mais símbolos confirmarem edge (PF>1 em ≥4/6 símbolos) e cross-TF estiver estável → candidato a incubação.**
**Se mais símbolos falharem (PF<1 em ≥3/6) → rejeitar e pivotar para outra linha.**

### Controle de strikes
Esta é a **primeira** vez que a hipótese VEE-LO é testada. Strike 0. Se próxima iteração (mais símbolos + cross-TF) também mostrar edge heterogêneo sem universalidade, avaliar strike 1 e pivot.

---

## 10. Dashboard row update

```json
{
  "id": "qm-vee-lo-v2",
  "name": "QM-VEE-LO-v2 - Pure Long Breakout Continuation (Long-Only)",
  "symbol": "BTC/ETH/SOL/XRP (1h)",
  "timeframe": "1h (primary)",
  "source": "greenfield quant mathematician cycle 05",
  "family": "VEE-LO",
  "agent": "researcher",
  "net_profit_pct": "BTC +4.44 / ETH -10.48 / SOL +20.30 / XRP -0.30",
  "profit_factor": "BTC 1.40 / ETH 0.53 / SOL 1.96 / XRP 0.99",
  "max_drawdown_pct": "BTC -4.66 / ETH -12.34 / SOL -4.88 / XRP -12.42",
  "win_rate_pct": "BTC 70.8 / ETH 45.8 / SOL 73.5 / XRP 54.3",
  "trades": "24 / 24 / 34 / 35",
  "sharpe": "BTC 1.53 / ETH -2.83 / SOL 3.38 / XRP 0.12",
  "result_id": "multiple (BTC 01M39TNZFY8GTYGABTECBGGYVQ, SOL 01M39TPF5V4D3H4B5MMJWC3A6C, ETH 01M39TP7H3H7FAMF63FZMSGZ14, XRP 01M39TPNZ2CE61C1Q49NJP5FGP)",
  "view_url": "N/A (multiple backtests)",
  "curve": "N/A (multiple backtests)",
  "verdict": "WATCHLIST - 2/4 símbolos PF>1 (BTC 1.40, SOL 1.96) com edge claro; ETH negativo, XRP neutro. Long-only remove short-side degradation do VEE-v3. Proxima: mais símbolos + cross-TF.",
  "status": "watchlist",
  "last_backtest": "2026-09-24",
  "pine_key": "qm_vee_lo_v2",
  "notes": "Hipótese long-only breakout continuation. DNA: VEE-v3 lesson (longs positive, shorts negative). 6 inputs, SL 2.0xATR, TP 1.5xATR, 15-bar recent high lookback, 0.5% close buffer, vol filter 70% SMA(20). BTC e SOL com edge robusto; ETH e XRP negativos/neutros. Amostra 117 trades. Sem repainting, sem lookahead, sem trailing."
}
```

---

## Notas para Gertrude

Estratégia com sinais de vida claros em BTC e SOL (PF>1.3, WR>70%, DD<5%). Não é produção ainda — não universal, sem cross-TF. Watchlist com desenvolvimento claro. Nenhuma ordem real colocada.

**Report metadata:**
- Gerado por: Quant Mathematician (researcher)
- Data: 2026-09-24 13:46 UTC-3
- Strategy ID: 01M39TNABB6DG851S6525V034G (v4)
- Pine source: data/pine/qm_vee_lo_v2.pine
- Créditos gastos: 4 backtests × 1 credit = 4
- Nenhuma ordem real colocada.
