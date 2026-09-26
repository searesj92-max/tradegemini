# Trader Dev Research Report

## 1. Goal

Executar um ciclo verde do Quant Mathematician Loop: gerar hipóteses matemáticas de primeira ordem, selecionar uma, traduzir em regras de trading, submeter ao backtest Trader Dev MCP e documentar o resultado com verdict.

Ciclo: **Cycle 4 — H1 REC-ND (Range-Efficiency Collapse after Normalized Displacement)**

## 2. Strategy or Hypothesis

**Hipótese H1 (REC-ND)** — Range-Efficiency Collapse after Normalized Displacement

- *Ineficiência alvo*: quando preço displaza fortemente da média (displ normalizado) mas o corpo do candle é fraco vs. range total (range efficiency baixo), isso sinaliza falha de continuação — o movimento "chegou longe demais com pouco corpo efetivo", típico de sweeps de liquidez que fecham de volta. Hipótese: reversão de curto prazo.
- *Por que na crypto*: liquidez rasa + stops concentrados → roubos de extremos são estruturais e o fechamento no candle frequentemente volta para dentro do range (fake breakout recorrente).
- *Cross-symbol*: comportamento de range efficiency é agnóstico do ativo — body/range é um conceito puramente geométrico aplicável a qualquer série de preços.
- *Regime de quebra*: tendências fortes (o displ é sustentado, não snap-back) e ambientes de baixo vol (o filtro volExpanding exclui silêncio, mas pode ser inadequado se o mecanismo for compressão-vol, não expansão).
- *Expressão Pine*: displ normalizado = (close - SMA(close, N)) / ATR; rangeEff = |close - open| / (high - low); entrada long quando displ < -thresh AND rangeEff < thresh2 AND volExpanding AND RSI < cap. SL/TP em ATR. Time exit 24b.

## 3. Trading Rules (long/short/exit/SL/TP/filters)

**Long**:
- displ = (close - ta.sma(close, 20)) / ta.atr(14) < -1.2
- rangeEff = |close - open| / (high - low + 1e-9) < 0.4
- volExpanding = ta.atr(14) > ta.sma(ta.atr(14), 20) * 1.1
- rsi(14) < 65 (proteção contra tendência strong long)
- Sem posição long aberta

**Short** (simétrico):
- displ > +1.2
- rangeEff < 0.4
- volExpanding
- rsi(14) > 35

**SL**: 2.0 × ATR(14) abaixo (long) / acima (short) do preço de entrada — **fixo de entrada** (capturado em var, não re-issue dinâmico).

**TP**: 1.5 × ATR(14) acima (long) / abaixo (short) do preço de entrada — **fixo de entrada**.

**Time exit**: 24 barras (contador manual — `barssince` não disponível no engine).

**Sem trailing**, sem martingale, sem grid, sem cancel.

## 4. Pine Script

Fonte em `data/pine/QM-REC-ND-v1.pine` (versão v3 = iteração 1 com SL/TP fixos). A versão v1 e v2 (SL/TP dinâmico) falharam com parser error (`display.none` quebrado, INDENT parser). v1 → v2 migrou para SL/TP fixo em var. Código finais submetidos ao backtest via `quick_backtest`.

### Pseudocode dos filtros (o que importa)

```
displ = (close - sma(close, 20)) / atr(14)
rangeEff = abs(close - open) / (high - low + 1e-9)
volExpanding = atr > sma(atr, 20) * 1.1

longCond  = noPosition and displ < -1.2 and rangeEff < 0.4 and volExpanding and rsi < 65
shortCond = noPosition and displ >  1.2 and rangeEff < 0.4 and volExpanding and rsi > 35
```

Exits: `strategy.exit("LX"/"SX", from_entry, stop=longStopPrice, limit=longTpPrice)` — preços fixos de entrada em var, re-issued toda barra.

Código completo: ver `data/pine/QM-REC-ND-v1.pine`.

## 5. Backtest Matrix

| Correção | Campo | Valor |
|---|---|---|
| Estratégia | ID | `01M39H11K0EXPJNZCTGNMR63YN` (v1), v2, v3 |
| Estratégia | Nome | QM-REC-ND-v1 |
| Símbolo | Display | BYBIT:BTCUSDT.P |
| Timeframe | — | 15m |
| Janela | From–To | Jan 2024 → Sep 2026 (cougido em to: 2026-09-24T10:57Z → 2026-09-24T00:00Z) |
| Engine | — | tv_jul26_mc7 |
| Barras avaliadas | — | 95.928 (100% cobertura) |
| Capital | — | $10,000 |
| Commission | — | 0.05% (forçado pelo MCP) |
| Sizing | — | 100% equity, margin 100/100 |
| Slippage | — | 0 ticks |
| Runs | — | 3 (v1 parser error ×2, v1 backtest final + v2 iteração + v3) |

## 6. Results

### v1 (iteração 0 — SL/TP dinâmico)

| Métrica | Valor |
|---|---|
| Net return | **-97.72%** |
| Final equity | $228 |
| Profit Factor | **0.518** |
| Win rate | 43.43% (975W / 1270L) |
| Total trades | **2245** |
| Max DD | **97.76%** |
| Sharpe | -4.86 |
| Sortino | -2.61 |
| Long trades / net | 1074 / -$3879 |
| Short trades / net | 1171 / -$5892 |
| Commission paid | $3847 |
| Avg trade | -$4.35 |
| Avg win / Avg loss | +$10.78 / -$15.97 (ratio 0.675) |
| Avg bars in trade | 13.63 |
| Largest win / loss | +$173.83 / -$398.62 |
| View URL | https://mcp-api.trader.dev/backtest/01M39H118W0N7WZJ1E8GX387ZE |

### v2/v3 (iteração 1 — SL/TP fixos de entrada)

| Métrica | Valor |
|---|---|
| Net return | **-96.99%** |
| Final equity | $301 |
| Profit Factor | **0.552** |
| Win rate | 42.05% (804W / 1108L) |
| Total trades | **1912** |
| Max DD | **97.04%** |
| Sharpe | -3.91 |
| Sortino | -2.25 |
| Long trades / net | 858 / -$2508 |
| Short trades / net | 1054 / -$7190 |
| Commission paid | $3688 |
| Avg trade | -$5.07 |
| Avg win / Avg loss | +$14.84 / -$19.52 (ratio 0.760) |
| Avg bars in trade | 17.73 |
| Largest win / loss | +$653.37 / -$368.11 |
| View URL | https://mcp-api.trader.dev/backtest/01M39HBZ0XS62HQC0PJY2EBM28 |

### Resumo da linha

| Run | Net% | PF | DD% | Trades | WR |
|---|---|---|---|---|---|
| v1 (SL/TP dinâmico) | -97.72 | 0.518 | 97.76 | 2245 | 43.4% |
| v2/v3 (SL/TP fixo) | -96.99 | 0.552 | 97.04 | 1912 | 42.1% |

## 7. Diagnosis

**Resultado: linha H1 rejeitada — dois strikes, efeito catastrófico em ambos os runs.**

### 7.1 O que foi testado

- Hipótese de reversão via displ normalizado + range-efficiency + vol expanding.
- Duas formulações de exit: dinâmico (re-issue todo barra com preço de mercado) e fixo (var de entrada).
- 1912–2245 trades em ~2.5 anos de BTC 15m.

### 7.2 O que o math diz

**Break-even WR para o RR nominal**:
- TP = +1.5 ATR, SL = -2.0 ATR → RR = 1.5:2.0 = 0.75:1.
- Break-even WR = SL / (TP + SL) = 2.0 / 3.5 = **57.1%**.
- Backtest WR = 42–43%, abaixo do break-even por ~14pp.

**EV esperado por trade (antes de commission)**:
- EV = WR·TP - (1-WR)·SL = 0.43·1.5 - 0.57·2.0 = 0.645 - 1.140 = **-0.495 ATR/trade**.
- Em dólares: ATR de BTC 15m ≈ varios USDT; com -0.495 ATR/trade × ~2000 trades = perda esperada grande.

**Commission como fator dominante**:
- $3847 de commission em v1 sobre $10,000 de capital = **38.5% do capital em costs isolados**.
- Com PF 0.52, o grossProfit de $10,514 cobre apenas parte da grossLoss de $20,286 + commission.

**SL/TP fixo vs dinâmico**: quase sem diferença (-97.72% vs -96.99%). Isso confirma que o problema não é o re-issue dinâmico (fear do `custom_var_trail`), mas **a entry tem EV negativo estrutural**.

### 7.3 Por que a hipótese falha em BTC 15m

1. **Threshold de rangeEff muito fraco**: 0.4 = corpo = 40% do range. Num candle de false breakout, o corpo típico é < 0.2 (pinbar/doji). 0.4 captura candles de "movimento normal num range alto" — não verdadeiros candle de exaustão.
2. **Vol expanding como gatilho é contra-produtivo**: o mecanismo de reversão pós-displ funciona melhor quando o vol está **baixando** (compression de vol pós-movimento), não expandindo. Entrar com volExpanding significa entrar no "calor do momento" quando o snap-back é menos provável.
3. **RR negativo**: no design atual, o TP é 1.5 ATR e SL 2.0 ATR — para que valha, precisaria de win rate > 57%. O backtest mostra ~43%, indicando que o movimentos de reversão real não preenchem o TP antes do stop, ou que o stop é atingido antes do TP tipicamente.
4. **Short pior que long**: em v2, short net = -$7190 vs long net = -$2508. Possível efeito de funding implícito em shorts persistentes em BTC — em live, short contínuo paga funding. Mas no backtest sem funding, a assimetria vem do comportamento do preço: BTC tem tendência long-term upward, então short entries em displ positivo são mais propensas a continuar para cima (stop-out), enquanto long entries em displ negativo têm algum suporte de regime bullish.

### 7.4 O que NÃO é problema

- Parser error nas primeiras versões: caused by `display.none` (recurso quebrado no engine) — não reflete qualidade da estratégia; corrigido.
- `barssince` não implementado no engine: lidado com contador manual `barsInPos`.
- Não é overfitting: há apenas 6 inputs (lenSma, lenAtr, displThresh, reffThresh, volMult, slAtrRanges, tpAtrRanges, rsiCap) — parâmetros mínimos.
- Não é repainting: todas as condições usam close de barra fechada (`process_orders_on_close=true`).
- Não é lookahead.

## 8. Verdict: **REJECT**

**REJEITAR — linha H1 REC-ND descartada.**

Justificativa:
- PF 0.52–0.55 em ambos os runs, longe de 1.0.
- DD ~97% → perda quase total do capital.
- WR 42–43% vs break-even necessário 57.1%.
- 2 runs × 1912–2245 trades mostram efeito consistente e negativo.
- A mudança conceitual de exit (dinâmico → fixo) não trouxe melhoria material: a raiz é o EV negativo da entry.
- Cumpriu dois strikes do ciclo (v1 e v2/v3) sem sinal de vida.

**Não é Watchlist**: PF < 1, DD > 30%, resultado negativo consistente em sample grande.

**Não é incubação**: 요건을 não preenche (PF < 1.3, DD > 30%).

Linha rejeitada. Próxima hipótese na próxima iteração.

## 9. Next Cycle

**Hipótese H4 — Compression-Vol Reversion (CVR)**:

- *Mudança conceitual*: ao invés de entrar com vol **expanding** (H1), entrar com vol **contracting** após displ grande. Rationale: após movimento de displ grande, se o vol está contraindo (ATR shrink vs. SMA ATR), o preço está em fase de "esfriamento" e a reversão para a média é mais provável (vol clustering reverso).
- *Matemática*: displ como antes; volFilter = atr < atrSma * (1 - volShrinkMult), onde volShrinkMult ≈ 0.1 a 0.2.
- *Range-eff threshold*: menor, ~0.25–0.30 (pinbar/doji crisp).
- *SL/TP*: manter fixos de entrada, aumentar RR: TP = 2.0 ATR, SL = 1.5 ATR → RR = 1.33:1, break-even WR = 1.5/3.5 = **42.9%**. Meta: WR > 43% pelo menos.
- *Filtro de regime*: ADX < thresh para evitar entrar em tendência; ou usar `ta.rma` de direção.
- *Cross-symbol*: testar BTC, ETH, SOL, XRP, DOGE, ADA, LINK em 15m e 1h.

**Meta de gate para próxima iteração**: PF > 1.0 em pelo menos 3 de 5 símbolos, WR > break-even (43%), DD < 30%, trades > 100.

**Créditos**: balance atual desconhecido após os 2 runs (cada run = 1 crédito; foram 2 créditos + 1 para o backtest final = 3 créditos gastos, mas o primeiro run falhou com parser error e não contou? — o quick_backtest que completou contou 1 crédito; os dois que deram parser error talvez não tenham cobrado). Vou verificar créditos e prosseguir se houver pelo menos 1 crédito.

**Sem ordem real**: todos os backtests são pesquisa/educação. Nenhuma live execution.
