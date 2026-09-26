# Quant Mathematician Cycle Report

## 1. Hipóteses Geradas

Três hipóteses greenfield foram formuladas para este ciclo:

### VND — Volatility-Normalized Displacement (selecionada)

**Ineficiência alvo:** Uma única vela cujo corpo tem deslocamento normalizado por ATR acima de limiar (φ=1,618) e cuja close está próxima de uma das extremidades (mas sem follow-through) tende a sofrer retração na barra seguinte.

**Por que na crypto:** Microestrutura auction-driven gera displacimentos repentinos sem confirmação; gaps mínimos e mercado 24/7 amplificam o padrão de single-bar extreme sem continuation.

**Expressão Pine:** `displ = |body|/atr`, `clPr = (close-low)/(high-low)`, entrada long se barra anterior bearish + clPr < 0.30 + corpo dominante (>60% do range) + displ > 1.618×atr.

**Breaking regime:** mercados em tendência forte (baixo churn), 램프업 sem pull-back, horário de liquidação concentrada.

### PEC — Post-Expansion Compression

**Ineficiência alvo:** Após período de range elevado e volume alto, volatilidade encolhe abaixo de limiar; entrada na continuação da direção do último breakout quando o squeeze estoura.

**Por que na crypto:** Contraction devolve volatilidade; o breakout do squeezed concentra ordens adiadas; breakout falso é explorável com SL cirúrgico.

### FCE — Failed Continuation Exhaustion

**Ineficiência alvo:** Quando uma série de barras na mesma direção falha em estender o range máximo (highest high recent não é quebrado) e o close recua para a zona central, há falha de continuation com viés de reversão.

**Por que na crypto:** Crypto marca movimentos direcionais seguidos de falha súbita quando o lado dominante esgota — posicionamento após falha explora o flip medo/ganância.

---

## 2. Hipótese Selecionada

**VND** (Volatility-Normalized Displacement).

**Motivo da seleção (por ordem de prioridade do loop):**
1. **Simplicidade** — 1 único sinal de barra, sem agregação de séries, sem múltiplos indicadores.
2. **Testabilidade** — sinal limpo e não-overlap com conhecimento de retail (diferente de RSI/MACD).
3. **Matematical rigor** — normalização por ATR, uso de φ como escala estrutural (não arbitrária), posição do close como fração do range.
4. **Generalizabilidade cruz-símbolo** — a normalização vol faz a mesma condição aplicável a BTC, ETH, SOL, BNB, XRP sem retuning.
5. **Clear risk management** — SL/TP fixos em ticks ATR, cooldown, regime filter opcional.

---

## 3. Regras de Trading

### Entradas

| Direção | Condição (todos no barra anterior, t-1) |
|---------|----------------------------------------|
| Long    | `close[1] < open[1]` (bearish) **E** `clPr[1] < 0.30` (close próximo da low) **E** `bodyShare[1] > 0.60` (corpo domina o range) **E** `displ[1] > 1.618 × atr[14]` |
| Short   | `close[1] > open[1]` (bullish) **E** `clPr[1] > 0.70` (close próximo da high) **E** `bodyShare[1] > 0.60` **E** `displ[1] > 1.618 × atr[14]` |

### Filtro de regime (opcional)

SMA 200 como filtro de tendência: long só se `close` e `close[1]` acima da SMA; short só se abaixo. Se `trendLen=0` → desligado.

### Saídas (SL/TP fixos em ticks, sem trailing — regra de latência))

- **TP:** 40 ticks do preço de entrada (1 tick = 0.0001 USD em pares USDT, mas o valor real é por símbolo via lotFilters Bybit).
- **SL:** 25 ticks do preço de entrada.
- **Cooldown:** 1 barra após sair antes de reentrar.
- **Nenhum trailing** — seguidor de preço via var-trail é rejeitado pelo engine (custom_var_trail) e contra a regra de latência para broker real.

### Invalidação

Se o set-up ocorre mas a posição é invertida pelo sinal oposto antes do fechamento → cooldown reiniciado (já programmatically via `lastTradeBar`).

---

## 4. Pine Script (qm_vnd_v1.pine — versão submetida)

```
//@version=6
strategy(
  title="QM-VND-v1",
  overlay=true,
  pyramiding=1,
  process_orders_on_close=true,
  commission_type=strategy.commission.percent,
  commission_value=0.05,
  initial_capital=10000,
  default_qty_type=strategy.percent_of_equity,
  default_qty_value=100,
  margin_long=100,
  margin_short=100,
)
// QM-VND-v1 — Volatility-Normalized Displacement after single-bar extreme
//
// Math basis (see report): a single candle whose body displacement |ba|/atr
// exceeds a vol-normalized threshold and whose close sits near one extreme
// (but NOT followed through) tends to retrace in the bar after.
// ...
// (ver código completo em: C:\Users\seares\Desktop\botrade\workspace\qm_vnd_v1.pine)
```

---

## 5. Matriz de Backtest

### Configuração

- **Engine:** tv_jul26 (TV_ENGINE_JUL_26 parity) + mc7
- **Período:** ~Jun 2026 → Sep 24 2026 (clamped ao último bar disponível no ClickHouse)
- **Capital:** $10,000
- **Sizing:** 100% equity, margin long/short 100
- **Commission:** 0.05% (mcp parity override; o engine rejeita commission=0)
- **Slippage:** 2 ticks
- **Strategy ID:** `01M38BX167REBFBHNT6Y7VQPVA` (v1)
- **Nota:** cada backtest é um strategyId separado (o engine cria novo strategyId para cada chamada com symbol/TF diferentes — comportamento esperado de adhoc mode).

### Resultados

| Símbolo | TF | Trades | WR% | PF | Net% | MaxDD% | Sharpe | AvgBars | Result ID |
|---------|-----|--------|------|-----|------|--------|--------|---------|-----------|
| BTCUSDT | 1h  | 12     | 33.3 | 0.29 | -2.13 | 2.13 | -2.67 | 2.0 | 01M38BWW1VR7CWBGAF86NEW9VN |
| ETHUSDT | 1h  | 14     | 35.7 | 0.59 | -1.35 | 2.46 | -1.18 | 2.0 | 01M38C30J90HD1NQ1A2X04XE0A |
| SOLUSDT | 1h  | 14     | 28.6 | 0.15 | -1.83 | 2.05 | -3.69 | 2.0 | 01M38C3PNGQZKFSWTV3G9YE7W7 |
| BNBUSDT | 1h  | 11     | 18.2 | 0.17 | -2.30 | 2.30 | -3.14 | 2.0 | 01M38C59B6TDNFJAFZN85TM873 |
| XRPUSDT | 1h  | 19     | 26.3 | 0.56 | -1.92 | 2.76 | -1.54 | 2.2 | 01M38C67DDY9CTPTCQGFZHJD88 |
| BTCUSDT | 4h  | 5      | 0.0  | 0.00 | -1.22 | 1.22 | -3.65 | 2.0 | 01M38C71F0V43BTEEPTVS004BG |

### Observações da matriz

- **Todos os 6 testes estão negativos** (net profit < 0).
- **Profit factor < 1 em todos os casos** (0.15 a 0.59 no 1h; 0 no 4h).
- **Win rate entre 0% e 35.7%** — sem teste com WR > 50%.
- **Avg bars in trade = 2 em todos os casos** — SL ou TP são acertados em ~2 barras; não há trades de durada média/longa.
- **No 4h:** apenas 5 trades, 0 vitórias, PF=0 — o padrão piora no timeframe maior.
- **Crossover long/short:** distribuição mista, sem viés óbvio de um lado (ex: XRP teve 14 shorts vs 5 longs, mas ambos negativos).
- **Sem warnings críticos** (cascade leve presente em alguns testes, mas sem `cascade_exit_pattern_severe`).

### Visualizações (equity curves)

- BTC 1h: https://mcp-api.trader.dev/backtest/01M38BWW1VR7CWBGAF86NEW9VN
- ETH 1h: https://mcp-api.trader.dev/backtest/01M38C30J90HD1NQ1A2X04XE0A
- SOL 1h: https://mcp-api.trader.dev/backtest/01M38C3PNGQZKFSWTV3G9YE7W7
- BNB 1h: https://mcp-api.trader.dev/backtest/01M38C59B6TDNFJAFZN85TM873
- XRP 1h: https://mcp-api.trader.dev/backtest/01M38C67DDY9CTPTCQGFZHJD88
- BTC 4h: https://mcp-api.trader.dev/backtest/01M38C71F0V43BTEEPTVS004BG

---

## 6. Resultado

### Síntese

| Métrica | Valor (média / observação) |
|---------|---------------------------|
| Net profit médio | **-1.8%** (range -1.2% a -2.3%) |
| Profit factor médio | **0.30** (range 0.00–0.59) |
| Win rate médio | **22.2%** (range 0%–35.7%) |
| Trades totais | **75** (11–19 por símbolo/TF) |
| Avg bars in trade | **2.0** — todos os SL/TP batidos rapidamente |
| Sharpe médio | **-2.64** |

### Avaliação em ordem de prioridade do loop

1. **Robustez cruz-símbolo:** ✗ — todos negativos, nenhum símbolo com PF > 1.
2. **Controle de drawdown:** ✓ — MaxDD ≤ 2.8% em todos os testes (limitado pelo TP/SL curto). Mas o DD controlado vem do tamanho pequeno de cada trade, não de gestão ativa.
3. **Profit factor:** ✗ — PF < 1 em todos.
4. **Qualidade média do trade:** ✗ — avg trade -9.6 a -20.9 USDT; ratio avg win/loss < 1 em 5 de 6 testes.
5. **Confiabilidade do count de trades:** ~ — entre 5 e 19 trades por teste; amostra pequena mas não nula.
6. **Estabilidade cruz-TF:** ✗ — BTC 4h teve 0 vitórias e PF=0, pior que 1h.
7. **Simplicidade:** ✓ — código limpo, 1 conceito, sem indicadores adicionais.
8. **Lucro líquido:** ✗ — negativo em todos.

---

## 7. Diagnóstico

### O que o dado diz

O padrão "displacimento de barra única normalizado por ATR com close em extremidade → fade na barra seguinte" **não produz edge** em nenhum dos 6 cenários testados (5 moedas × 1h + BTC 4h).

### Hipóteses de falling

1. **O sinal de close-próximo-extremo não é previsório de reversão:** Após uma vela com corpo dominante e close em uma extremidade, a direção mais provável é continuação (tendência) ou movimento lateral (range), não reversão sistemática. O fade é a posição incorreta.

2. **Limiar φ=1.618 pode ser inadequado:** O valor pode ser muito alto ( poucas barras qualificam, sampled bias) ou muito baixo (include barra normal como "extremo"). Amostra pequena (11–19 trades) não permite diagnóstico de threshold tuning.

3. **SL/TP de 25/40 ticks é muito curto para o padrão:** Se o padrão realmente existisse mas com lag de 3–5 barras, o SL bate antes do TP. O avg bars in trade=2 sugere que o mercado não se move 40 ticks na direção da entry dentro de 2 barras em média — ou que o stop é acertado pelo ruído de 1–2 barras.

4. **O sinal pode estar ocorrendo em regimes incompatíveis:** No BTC 4h, os 5 trades foram todos loss — sugere que o padrão aparece em momentos de alto vol que são seguidos de continuation, não de reversão.

### O que NÃO é o problema

- Não é repainting (cascade leve presente mas sem erro grave; todos os testes deram resultado com mcpruleValidated=true).
- Não é falta de trades (75 no total; 5–19 por teste).
- Não é commission (0.05% é padrão do engine, e os gross losses superam gross profit por fator 2–7×, não explicável apenas por commission).
- Não é lookahead (toda a lógica usa [1] ou series calculadas no bar atual; sem request.security, sem cálculo no bar ilegal).

### Conclusão do diagnóstico

A hipótese VND, como formulada, **não tem edge**. A mudança conceitual mais promissora para o próximo ciclo é testar a hipótese **PEC** (post-expansion compression) ou **FCE** (failed continuation exhaustion), que são matemáticamente distintas de "fade do displacimento" — elas exploram pullback **depois de** uma expansão reconhecida, não na barra seguinte do extremo.

---

## 8. Verdict: **REJECT** (Rejeitado)

**Justificativa:**

- PF < 1 em todos os 6 testes.
- Net profit negativo em todos.
- Win rate < 50% em todos (0% no 4h).
- Não há sinal de estabilidade cruz-símbolo ou cruz-TF.
- O conceito matemático (fade de single-bar displacement) não é suportado pelos dados.

**Classificação no pipeline:**

- **NÃO incubar.** PF insuficiente e sem sinal de vida em nenhum símbolo/TF.
- **NÃO watchlist.** Amostra de 75 trades em 6 configurações não mostra nenhum rastro de edge.
- **REJECT.** Linha VND encerrada neste ciclo.

**Learnings para futuros ciclos:**

1. Single-bar fade de displacimento é hipótese fraca — pivotar para continuation-after-expansion ou failed-continuation exhaustion.
2. SL/TP de 25/40 ticks pode ser muito curto; em hipóteses futuras, experimentar SL/TP mais largo ou baseado em ATR múltiplo (ex: SL=1.5×atr, TP=3×atr).
3. O filtro de regime (SMA 200) estava ativo mas não salvou — sugere que o problema é o sinal, não o regime.

---

## 9. Próximo Ciclo

**Ciclo seguinte (QM-PEC-v1 ou QM-FCE-v1):**

1. Selecionar PEC (post-expansion compression) como hipótese principal.
2. Definir squeeze detection via `ta.stdev(close, N)` % de seu histórico recente + volume anomaly + filter de direção do último breakout.
3. Entry no bar do estouro; SL abaixo dosqueeze low; TP baseado em extent do pré-squeeze range.
4. Backtest em matriz 5 moedas × 1h/4h.

**Condição de parada:** se PEC e FCE também falharem (3 strikes na linha de hipóteses de range/vol), pivotar para outra família conceitual (ex: liquidity sweep + snapback, regime switching).

---

## Anexos

- **Código Pine:** `C:\Users\seares\Desktop\botrade\workspace\qm_vnd_v1.pine`
- **Cidade:** 6 backtests (BTC, ETH, SOL, BNB, XRP no 1h; BTC no 4h)
- **Credits gastos:** 6 créditos (restam ~177)
- **Nenhuma ordem real — pesquisa/educação apenas.**
