# Quant Mathematician Cycle Report

**Cycle**: 4
**Agent**: researcher
**Date**: 2026-02-26 16:00 BRT
**Status**: Completed — PF heterogêneo; diagnóstico claro; decisão: Watchlist (Estacionar)

---

## 1. Hypotheses Generated

**H1 — Range Efficiency Collapse + Volatility-Normalized Displacement Reversion (REA)**
Ineficiência: quando o preço é deslocado do equilíbrio (SEMA) por ≥ τ ATR e o candle tem expansão de range (range/ATR ≥ ν) mas baixa *range efficiency* (|corpo|/range < ε), há indicação de failed follow-through — movimentação de liquidez sem continuação. Tendência de mean reversion curta.
Por que crypto: false breakouts e liquidity sweeps sem continuação são abundantes em pares com baixa tendência.
Expression: `d=(c−sma)/atr`; `re=|body|/range`; entrada long quando `d < −τ` ∧ `range/ATR ≥ ν` ∧ `re < ε`.

**H2 — Failed Breakout Confirmation (Liquidity Sweep + Snapback)**
Ineficiência: rompimento de extremo recente seguido de candle de fechamento dentro do range anterior (snapback).
Expression: break de `ta.highest(high, N)` com `close` abaixo do nível no candle seguinte.

**H3 — Volatility Compression → Expansion Asymmetric Entry**
Ineficiência: compressão de volatilidade (ATR baixo em janela) precede expansão; entrada na direção do primeiro candle de expansão com confirmação de close.
Expression: ATR rolling mínimo + candle de expansão > threshold.

**H4 — Return Asymmetry (Skewness) Regime Filter**
Ineficiência: assimetria de retornos em crypto é regime-dependente; skewness negativo → continuidade de queda; skewness positivo → reversão.
Expression: skewness da janela como filtro de entrada.

**H5 — Distance-from-Equilibrium with Volume Anomaly**
Ineficiência: deslocamento do VWAP/SMA + anomalia de volume (OBV divergente ou volume > mediana) confirma/rejeita direção.
Expression: `|c−sma|` combinado com `volume > ta.median(volume, N)`.

---

## 2. Hypothesis Selected

**H1 (REA)** — simplicidade (3 parâmetros principais: tau, epsilon, nu), testabilidade clara, base matemática de range efficiency + deslocamento normalizado, potencial de generalização cross-symbol, regras de risco explícitas (SL/TP em ATR, cooldown, proteção de tendência).

---

## 3. Trading Rules

### Entradas
- **Long**: `d < −τ` (preço abaixo do equilíbrio por ≥ τ ATR) **E** `range/ATR ≥ ν` (expansão de range) **E** `range_efficiency < ε` (corpo pequeno dentro de range grande = failed follow-through).
- **Short**: espelho (`d > +τ`, mesma condição de range efficiency e expansão).

### Filtros
- **Proteção de tendência**: não entrar long se o deslocamento oposto (`d`) for muito grande (max_dopposite); evita entrar contra tendência forte.
- **Cooldown**: entrar só após `cooldown_bars` desde o último exit (previne stacking no mesmo movimento).

### Exits (SL/TP em ATR, sem trailing stops)
- **Long TP**: `min(SMA_eq, close + tp_atr × ATR)` — mean reversion ao equilíbrio, capped por distância ATR fixa.
- **Long SL**: `close − sl_atr × ATR`.
- **Short TP**: `max(SMA_eq, close − tp_atr × ATR)`.
- **Short SL**: `close + sl_atr × ATR`.

### Parâmetros-base
- tau = 1.5, epsilon = 0.35, nu = 1.0, sl_atr = 2.0, tp_atr = 1.5, SMA_eq = 50, cooldown = 3, max_dopposite = 2.5.

---

## 4. Pine Script

Ver arquivo: `data/pines/QM-RangeEfficiencyReversion-v1.pine`

A estratégia é //@version=6, sem repaint, sem lookahead, com strategy.exit SL/TP absoluto em ATR, sem trailing, com proteção de tendência e cooldown. Submission via `quick_backtest` com parâmetros de parity profile (commission 0.05%, 100% equity, margin 100, pyramiding 1, process_orders_on_close).

---

## 5. Backtest Matrix

| Symbol | Timeframe | Strategy ID | Result ID | Trades | Periodo |
|--------|-----------|-------------|-----------|--------|---------|
| BTCUSDT | 1h | 01M39JYZBZXWJJTZ3ZEE8BH7FX | 01M39JYZ36CHWKXSG8G0J72TS1 | 180 | Jan 2025 – Fev 2026 |
| ETHUSDT | 1h | 01M39K3DQ4ZN8FAHZVZB13WX69 | 01M39K3D995FE9WVGTQ76M6NJJ | 219 | Jan 2025 – Fev 2026 |
| SOLUSDT | 1h | 01M39K453J2AKT2A55JXMT1B4T | 01M39K43DA99YDMXJN56T9YNNF | 207 | Jan 2025 – Fev 2026 |

Engine: tv_jul26_mc7 · Parity profile aplicado (commission 0.05%, 100% equity, margin 100, pyramiding 1).
Cobertura: 103% em todos os símbolos.

---

## 6. Results

### BTCUSDT 1h — **FALHA**
- Net: **-23.2%** ($10,000 → $7,680)
- PF: **0.73**
- DD: **31.1%**
- WR: **40.6%** (73W / 107L)
- Trades: 180 (78L / 102S)
- Long net: +$33 · Short net: **-$2,353**
- Avg trade: -$12.89
- Sharpe: -1.63 · Sortino: -0.62
- Avg bars in trade: 7.7

### ETHUSDT 1h — **SUCESSO (isolado)**
- Net: **+40.5%** ($10,000 → $14,051)
- PF: **1.34**
- DD: **11.5%**
- WR: **44.3%** (97W / 122L)
- Trades: 219 (71L / 148S)
- Long net: **+$2,878** · Short net: **+$1,173**
- Avg trade: +$18.50
- Sharpe: **1.48** · Sortino: 0.62
- Avg bars in trade: 8.0

### SOLUSDT 1h — **FALHA**
- Net: **-18.4%** ($10,000 → $8,160)
- PF: **0.87**
- DD: **37.8%**
- WR: **36.7%** (76W / 131L)
- Trades: 207 (61L / 146S)
- Long net: -$1,513 · Short net: -$327
- Avg trade: -$8.89
- Sharpe: -0.59 · Sortino: -0.21
- Avg bars in trade: 7.3

### Aggregado matriz (não ponderal)
- PF médio: (0.73 + 1.34 + 0.87) / 3 = **0.98**
- DD médio: (31.1 + 11.5 + 37.8) / 3 = **26.8%**
- Trades total: 606
- 1 de 3 símbolos com PF > 1.0

---

## 7. Diagnosis

### O que funciona (ETH)
- ETH apresenta regime mean-reverting mais claro: a estratégia captura reversões após expansão sem follow-through.
- Longs e shorts ambos positivos — a hipótese de range efficiency collapse opera em ambos os lados.
- DD controlado (11.5%) e Sharpe positivo (1.48).

### O que fracassa (BTC, SOL) e por quê
- **Bias de short excessivo**: em BTC, 102 short trades geraram -$2,353 de prejuízo; em SOL, 146 short trades, -$327. Os longs em BTC quase neutros (+$33 em 78 trades).
- **Proteção de tendência insuficiente**: a condição `max_dopposite` não filtra efetivamente movimentos trending. BTC e SOL em 1h têm regimes trending onde entrada contra-ação (especialmente short) é destrutiva.
- **Range efficiency collapse não é universal**: quando o mercado está em tendência, expansão de range com corpo pequeno pode ser *consolidation antes de continuação* (flag), não failed follow-through. A interpretação da anomalia é regime-dependente.

### Análise por lado
| Symbol | Long Net | Short Net | Conclusão |
|--------|----------|-----------|-----------|
| BTC | +$33 | -$2,353 | Short bias destrutivo; longs neutros |
| ETH | +$2,878 | +$1,173 | Ambos positivos — hipótese válida em ETH |
| SOL | -$1,513 | -$327 | Ambos negativos — falha geral |

### Conclusão diagnóstica
A hipótese H1 (REA) **não é universal**. Ela opera em regimes onde o mercado alterna entre expansão sem follow-through e mean reversion — caractística mais comum em ETH (e possivelmente em altcoins menos trending) do que em BTC ou SOL em 1h. A lógica é parcialmente correta mas o filtro de regime é insuficiente.

---

## 8. Verdict

### Critérios de avaliação (ordem de prioridade do loop)
1. **Robustez cross-symbol**: ❌ 1/3 símbolos com PF > 1 (ETH). BTC e SOL fracassam.
2. **Controle de drawdown**: ❌ DD de 31% (BTC) e 37.8% (SOL) violam limite de 30%.
3. **Profit factor**: ⚠️ PF médio 0.98 — abaixo de 1.0 agregado.
4. **Qualidade de trade**: ⚠️ Avg trade negativo em BTC (-$12.89) e SOL (-$8.89); positivo em ETH (+$18.50).
5. **Contagem de trades**: ✅ 606 trades — amostra adequada.
6. **Estabilidade cross-TF**: ⚪ Não testado (só 1h).
7. **Simplicidade**: ✅ 3 parâmetros principais — bom.
8. **Lucro líquido**: ❌ Negativo em 2/3 símbolos.

### Decisão: **Watchlist (Estacionar)**
- **Não rejeitar** porque a hipótese mostra sinal de vida em ETH (PF 1.34, DD 11.5%, Sharpe 1.48, longs e shorts positivos) — a lógica subjacente tem validade em regime adequado.
- **Não incubar** porque não há robustez cross-symbol (1/3 passa) e DD viola limite em 2/3.
- A lógica de range efficiency collapse é parcialmente correta; o problema é a **falta de regime classifier robusto** e o **viés de short não filtrado**.

---

## 9. Next Cycle

### Iteração planejada (um conceito principal)
**Adicionar regime classifier baseado em tendência**: antes de entrar, verificar se o mercado está em regime trending ou mean-reverting. Opções:
- **ADX filter**: se ADX > threshold, não entrar (mercado trending → evitar reversão).
- **Slope do SMA**: se SMA(50) tem inclinação forte no sentido oposto à entrada, skip.
- **Regime de range vs ATR histórico**: se o range atual é consistentemente maior que ATR histórico sem reversão, é tendência.

### Direção alternativa
- Explorar H2 (Failed Breakout Confirmation) como hipótese independente — pode capturar o padrão que H1 não captura (snapback after false breakout).
- Testar H1 apenas em **longs** com filtros mais estritos — remover shorts entirely e ver se o long-only version é viável (reduzir o bias de short destrutivo).

### Testes cross-TF
- Executar H1 em 4h para ETH e BTC — ver se o regime classifier (ou a própria lógica) generaliza para timeframe maior onde menos ruído de range efficiency.

### Sample de símbolos adicionais
- Adicionar XRP, ADA para ver se a hipótese generaliza para low-cap altcoins (menos trending, mais mean-reverting).

---

## 10. Risk Notice

Pesquisa e educação apenas. Não é aconselhamento financeiro. Backtests não são indicativos de desempenho futuro. Nenhuma ordem real foi colocada. Incubação requer ≥ 20 trades / ~3 meses e aprovação humana antes de qualquer consideração de live.

---

*Relatório gerado automaticamente pelo ciclo 4 do Quant Mathematician Loop (Hermes cron, profile `researcher`).*
