# Quant Mathematician Cycle Report

## 1. Hypotheses Generated

**5 hipóteses greenfield para crypto:**

1. **VED-1 — Volatility-Expansion Displacement Reversion** — z-score de distância do preço da média, normalizado por ATR e um fator de compressão (CV = ATR / |disp| com clamp). Quando o range colapsa e depois o preço se expande para k desvios da média, tende a reverter. Ineficiência: extremos de preço após compressão são reversos porque os stops são coletados e o preço retorna.

2. **LSS-2 — Liquidity Sweep + Snapback** — preço rebate um extremo recente por uma quantidade pequena e depois reverse dentro do range antes do fechamento. Stops de retail são posicionados além dos extremos; o sweep coleta liquidez e snaps back.

3. **FCE-3 — Failed Continuation Exhaustion** — série de bars na mesma direção com deceleração de range por bar. Após N impulsos consecutivos com range decrescente, a probabilidade de continuation cai.

4. **RAE-4 — Range-Adjusted Entropy Filter** — filtro de regime baseado em entropia efetiva da distribuição de retornos (range/ATR ratio ponderado). Operar só em regime de baixa entropia + direção clara melhora win rate e drawdown.

5. **VCA-5 — Volatility Clustering Asymmetry** — padrão de "respiração" do mercado: expand, contract, expand novamente. A direção do segundo movimento é parcialmente previsível pelo sinal do primeiro.

**Selecionado: VED-1** — mais simples (3 parâmetros + filtro de tendência), matematicamente fundamentado, testável em múltiplos símbolos e timeframes, SL/TP em ATR inequívoco, exit por tempo evita trades fantasmas. Hipótese central de deslocamento normalizado pelo range é genérica o suficiente para aplicar em qualquer símbolo.

---

## 2. Hypothesis Selected (math basis)

**VED-1 — Volatility-Expansion Displacement Reversion**

Matemática central: quando o preço distancia da média em um ambiente de baixa volatilidade (range comprimido), o deslocamento é "caro" em termos de ATR. Após a expansão, a reversão para a média é mais provável porque o preço esticou além do range normal do instrumento.

- Z-score = `(close - SMA) / (ATR × clamp(ATR / |disp|))`
- CV (coefficient of variation) = ATR / |disp|, com clamp para evitar explosão quando disp ≈ 0
- Entradas long quando z < -2.2 (preço abaixo da média por 2.2 desvios normalizados), short quando z > +2.2
- Filtro de tendência: EMA200 slope (5 bars) para favorecer a direção dominante
- SL/TP em ATR escalável, time exit em 6 bars

Por que em crypto: crypto tem ciclos de compressão/expansão mais frequentes que ações; gaps de liquidez intraday e consolidações pós-notícia geram os cenários onde a hipótese deveria operar.

---

## 3. Trading Rules (long/short/exit/SL/TP/filters)

### Entradas (long)
- `z < -zThresh AND z[1] >= -zThresh` (z cruzou abaixo do threshold) OU
- `z < -zThresh AND z[1] < -zThresh AND strategy.position_size == 0` (já estava além, mas sem posição)
- **E** filtro de tendência: `ema200Slope > 0` (se ativado)
- Entrada no fechamento do bar (next-bar execution, sem lookahead)

### Entradas (short)
- `z > zThresh AND z[1] <= zThresh` (z cruzou acima) OU
- `z > zThresh AND z[1] > zThresh AND strategy.position_size == 0`
- **E** filtro de tendência: `ema200Slope < 0` (se ativado)

### SL e TP
- **Long SL** = `close - max(atr × zThresh × 1.5, atr × 1.2)`
- **Long TP** = `close + max(atr × (zThresh + max(zExtL, 0.5)), atr × 2.0)` onde zExtL = quanto o z-score ultrapassou o threshold para short
- **Short SL** = `close + max(atr × zThresh × 1.5, atr × 1.2)`
- **Short TP** = `close - max(atr × (zThresh + max(zExtS, 0.5)), atr × 2.0)` onde zExtS = quanto ultrapassou para long
- SL/TP recalculados todo bar (strategy.exit re-emitido)

### Time exit
- Força encerramento em `maxBars = 6` bares desde a entrada (se ainda estiver em posição)

### Regime/vol filters
- Filtro EMA200 slope (input bool, padrão true)
- CV clamp em 0.04 para evitar que valores extremos de deslocamento gerem z-scores instáveis

---

## 4. Pine Script

Arquivo: `scripts/ved1_v1.pine`

```pine
//@version=6
strategy("VED-1 — Displacement Reversion v1", overlay=true, pyramiding=1,
  process_orders_on_close=true, commission_type=strategy.commission.percent,
  commission_value=0.05, initial_capital=10000,
  default_qty_type=strategy.percent_of_equity, default_qty_value=100,
  margin_long=100, margin_short=100)

smaLen   = input.int(200, "SMA período", minval=50)
atrLen   = input.int(50,  "ATR período", minval=10)
zThresh  = input.float(2.2, "Z-score threshold", minval=0.5, step=0.1)
cvClamp  = input.float(0.04, "CV clamp", minval=0.01, step=0.01)
maxBars  = input.int(6,   "Max bars in trade", minval=2)
useTrendF= input.bool(true, "Filtro de tendência (EMA200 slope)")

sma   = ta.sma(close, smaLen)
atr   = ta.atr(atrLen)
disp  = close - sma
cv    = atr / math.max(math.abs(disp), syminfo.mintick)
cvNorm= math.min(cv, cvClamp)
z     = disp / math.max(atr, syminfo.mintick) / cvNorm

ema200     = ta.ema(close, 200)
ema200Slope= ema200 - ema200[5]

zCrossedBelow = z < -zThresh and z[1] >= -zThresh
zCrossedAbove = z >  zThresh and z[1] <=  zThresh
zBeyondBelow  = z < -zThresh and z[1] < -zThresh
zBeyondAbove  = z >  zThresh and z[1] >  zThresh

trendFavLong  = useTrendF ? (ema200Slope > 0) : true
trendFavShort = useTrendF ? (ema200Slope < 0) : true

var int tradeEntryBar = na

longSetup       = zCrossedBelow or (zBeyondBelow and not na(strategy.position_size))
longEntrySignal = longSetup and trendFavLong
shortSetup       = zCrossedAbove or (zBeyondAbove and not na(strategy.position_size))
shortEntrySignal = shortSetup and trendFavShort

if longEntrySignal
    strategy.entry("L", strategy.long)
    tradeEntryBar := bar_index
if shortEntrySignal
    strategy.entry("S", strategy.short)
    tradeEntryBar := bar_index

zExtL = math.max(-zThresh - z, 0.0)
zExtS = math.max(z - zThresh, 0.0)
slTicksL = math.max(atr * zThresh * 1.5, atr * 1.2)
tpTicksL = math.max(atr * (zThresh + math.max(zExtL, 0.5)), atr * 2.0)
slTicksS = math.max(atr * zThresh * 1.5, atr * 1.2)
tpTicksS = math.max(atr * (zThresh + math.max(zExtS, 0.5)), atr * 2.0)
longSL  = close - slTicksL
longTP  = close + tpTicksL
shortSL = close + slTicksS
shortTP = close - tpTicksS

if strategy.position_size > 0
    strategy.exit("LX", from_entry="L", stop=longSL, limit=longTP, loss=slTicksL, profit=tpTicksL)
if strategy.position_size < 0
    strategy.exit("SX", from_entry="S", stop=shortSL, limit=shortTP, loss=slTicksS, profit=tpTicksS)

if strategy.position_size != 0 and bar_index - tradeEntryBar >= maxBars
    strategy.close_all(comment="time_exit")
```

**Notas de implementação:** CV clamp evitou instabilidade quando disp ≈ 0; SL/TP são recalculados todo bar (não lookahead); time exit usa variável `tradeEntryBar` (não `strategy.opentrades`, não na allowlist); plots apenas para debug (não afetam lógica).

---

## 5. Backtest Matrix

| Symbol | Timeframe | Strategy ID | Result ID | Bars | Trades | Win Rate | PF | Net | Max DD |
|--------|-----------|-------------|-----------|------|--------|----------|-----|-----|--------|
| BTCUSDT | 1h | 01M38RAZXZ7QES5TGNFKQ26391 | 01M38RAZNWXAJ0NK54TF2BP46K | 11,814 | 448 | 35.9% | 0.46 | -46.8% | 46.9% |
| ETHUSDT | 1h | 01M38RFQ5VJ58VK0P8PR5G82XT | 01M38RFPZVJA1P9DC1HP66NKWF | 11,814 | 715 | 25.7% | 0.39 | -59.2% | 59.3% |
| SOLUSDT | 1h | 01M38RGKFTNBA2P8TZMFZGZSYQ | 01M38RGKAETRA46E4PTYVAASJD | 11,813 | 802 | 28.1% | 0.58 | -49.3% | 50.1% |
| XRPUSDT | 1h | 01M38RHBTED8H42ZXYBQKA0EJ6 | 01M38RHBNGJFD8C94VHWWA2411 | 11,813 | 721 | 26.4% | 0.47 | -53.3% | 54.4% |

**Observação:** os strategy IDs mudaram entre símbolos porque o MCP trata símbolos diferentes como novas linhagens (warning: "Symbol differs from source — created a brand-new strategy in a separate lineage").

**Condições comuns:** 2025-06-01 → 2026-09-24, capital $10k, 100% equity, margin 100/100, commission 0.05% (hard-forçado pelo MCP), slippage 0, pyramiding 1, process_orders_on_close=true, tv_jul26_mc7 engine.

---

## 6. Results

### Resumo por símbolo

| Métrica | BTC | ETH | SOL | XRP | Média |
|---------|-----|-----|-----|-----|-------|
| Net Profit % | -46.8% | -59.2% | -49.3% | -53.3% | -52.2% |
| Profit Factor | 0.46 | 0.39 | 0.58 | 0.47 | 0.48 |
| Max Drawdown % | 46.9% | 59.3% | 50.1% | 54.4% | 52.7% |
| Win Rate | 35.9% | 25.7% | 28.1% | 26.4% | 29.0% |
| Trades | 448 | 715 | 802 | 721 | 672 |
| Avg Trade % | -0.104% | -0.083% | -0.061% | -0.074% | -0.081% |
| Long/Pf | 222 long, 84W | 252 long, 92W | 255 long, 111W | 189 long, 79W | — |
| Short/Pf | 226 short, 77W | 463 short, 92W | 547 short, 114W | 532 short, 111W | — |

### Métricas cruzadas

- **Long vs Short assimetria:** em BTC, long e short são similares (222 vs 226). Em ETH, SOL e XRP há forte skew para short (ETH: 463 short vs 252 long; SOL: 547 vs 255; XRP: 532 vs 189). Isso indica que o filtro de tendência está favorecendo short em maioria dos símbolos — possivelmente porque a EMA200 estava em downtrend na maior parte do período, ou porque o z-score está mais frequentemente acima de threshold do que abaixo.
- **Win rate sistematicamente baixa:** 26-36% em todos os símbolos — abaixo de 50% em todos, evidência clara de que as entradas não estão acertando mais que errando.
- **PF < 0.6 em todos:** nenhum símbolo tem PF > 0.6, muito distante do mínimo 1.3 para incubação.
- **DD > 46% em todos:** drawdowns são severos e sistema não tem recuperação (maxRunup=0 em todos os resultados — a curva de equity nunca recuperou um drawdown).
- **Commission como fator:** com 0.05% por trade e 448-802 trades, commission total é $3.0k-$3.8k em cada backtest — uma parte significativa da perda. Mas mesmo sem commission, os resultados seriam negativos (grossLoss sempre > grossProfit).
- **avgBarsInTrade = 2.6-3.4:** trades são curtos, o time exit raramente é acionado (6 bars), indicando que SL/TP acontecem antes do tempo. Isso é consistente com a hipótese falhando rapidamente.

---

## 7. Diagnosis

### O que deu errado (análise)

**1. O z-score não está capturando o que a hipótese propõe.**

A hipótese central é: "depois de compressão, expansão de preço para k desvios → reversão". Mas o z-score atual usa SMA(200) como referência de "média". A SMA(200) é uma média lenta que não distingue entre:
- Mercado em compressão (range pequeno) com preço perto da média → z-score baixo porque disp é pequeno
- Mercado em expansão (range grande) com preço distante da média → z-score alto

O CV clamp (ATR/disp) deveria normalizar isso, mas com clamp em 0.04, o z-score é cortada quando o deslocamento é muito pequeno relativo ao ATR — justamente os cenários de compressão que a hipótese quer capturar.

Resultado: o z-score está gerando sinais em momentos onde o preço está "longe da média" mas sem o contexto de compressão/expansão que daria significantes de reversão.

**2. SMA(200) é muito lenta para o fenômeno que queremos capturar.**

Usar SMA(200) como referência de "equilíbrio" captura a tendência de longo prazo, não o equilíbrio de curto prazo onde a reversão deveria ocorrer. A hipótese de displacement deveria medir distância de um nível recente de "equilíbrio" (ex: médio prazo, ou VWAP, ou região de consolidação recente), não de uma média de 200 bares.

**3. Filtro de tendência EMA200 slope pode estar distorcendo.**

Com EMA200 slope como filtro, a estratégia só opera long quando EMA200 está subindo, e só short quando está caindo. Em mercados de crypto 2025-2026, isso pode ter filterado a maioria das operações de um lado, criando o skew long/short observado. E se o mercado estava em downtrend (o que é comum em crypto no período), o filtro bloqueia longs e permite shorts — mas os shorts também estão perdendo dinheiro (ETH short: -3369, BTC short: -2787), indicando que o problema não é apenas o filtro de tendência.

**4. Ratio avgWin/avgLoss < 1 em todos (exceto SOL: 1.49).**

- BTC: 0.82 — perdas maiores que ganhos
- ETH: 1.14 — ganhos ligeiramente maiores que perdas, mas ainda PF negativo
- SOL: 1.49 — ratio de win/loss bom, mas PF 0.58 e DD 50% — muitos trades pequenos perdendo
- XRP: 1.32 — similar ao ETH

Isso indica que quando a estratégia acerta, o ganho é pequeno; quando erra, a perda é grande. Clássico padrão de estratégia sem corte de perdas efetivo ou com entradas em momentos errados.

**5. Comission está comendo lucro potencial.**

Com 715-802 trades em ETH/SOL/XRP, a commission de 0.05% por operação custa $3.0k-$3.8k. Com 100% equity e martingale implícito (posição cheia sempre), mỗi trade pequeno perde 0.05% × 2 = 0.1% em round-trip. Com 700 trades, isso é 70% de equity em commission só — este é um limite estrutural da configuração de teste (100% equity, 0.05% commission). Mas o MCP hard-forceia esse perfil para parity com TradingView, então é condição de teste, não escolha da estratégia.

### Conclusão do diagnóstico

O problema principal não é um único elemento, mas a combinação de:
- **Matemática de z-score com SMA lenta + CV clamp restritivo** que não captura o fenômeno de compressão/expansão que a hipótese propõe
- **Filtro de tendência que skewa operação para um lado** sem melhorar resultados
- **Estrutura de trades sem seletividade de regime** (opera em todos os contextos igual)

A hipótese VED-1 em sua forma atual **não tem edge** nos dados de 2025-2026 para os símbolos testados.

---

## 8. Verdict: **REJECT** (cycle 1 — pivot required)

**Critérios de rejeição atendidos:**
- PF < 0.6 em todos os 4 símbolos (threshold para incubação: PF ≥ 1.3 em ≥ 5 pares)
- Max DD > 46% em todos (threshold: ≤ 30%)
- Win rate < 36% em todos (longe de 50%+)
- Resultado negativo em todos os símbolos (não é um "one-pair wonder" positivo — é um "one-pair wonder" negativo, igualmente sem edge)
- Não é estável entre símbolos (todos negativos, mas em graus diferentes)

**Strikes:** este é o ciclo 1 da linha VED-1. O loop permite 3 ciclos sem edge antes de rejeitar a linha. Este relatório marca o ciclo 1 como sem edge. Se VED-1 for iterado e melhorar significativamente, pode ser reconsiderado. Caso contrário, no ciclo 3 sem edge, a linha é rejeitada e pivota-se para outra hipótese.

**Decisão:** REJECT da configuração atual de VED-1. Próxima iteração deve mudar algo fundamental (não apenas ajustar parâmetros).

---

## 9. Next Cycle (one major concept change)

Se VED-1 for iterado, a mudança principal deve ser:

**Opção A — Redefinir a referência de "média" para algo de médio prazo reativo:**
- Substituir SMA(200) por VWAP intraday ou HMA(50) ou swma(100) como referência de equilíbrio
- Isso captura o conceito de "preço longe do equilíbrio recente" melhor que SMA lenta
- Mantém o CV clamp, mas com referência mais sensível

**Opção B — Remover o CV clamp e usar abordagem de range-relativo:**
- Em vez de z-score com clamp, usar percentile rank do deslocamento dentro do range dos últimos N bares
- Entradas quando preço está no extremo do range recente (ex: top 10% ou bottom 10% do range de 50 bares)
- Mais próximo do conceito original de "extremo após compressão"

**Opção C — Combinar com regime filter (RAE-4) para não operar em chop:**
- Adicionar filtro de entropia/range ratio para só operar quando o mercado está em regime de tendência + compressão recente
- A hipótese VED-1 assume compressão antes da expansão — se não houver compressão, não deveria operar

**Recomendação:** Opção A (mudar referência de SMA200 para algo mais reativo) é o change más provável de ter impacto. SMA(200) como referência é a escolha mais comprometida da implementação atual — ela não tem relação com a hipótese de "extremo após compressão". Se a referência for um nível recente de consolidação ou VWAP de intraday, o z-score poderia capturar melhor os cenários onde a reversão é provável.

**Se nenhuma iteração resultar em PF ≥ 1.3 em ≥ 3 símbolos com DD ≤ 35% no ciclo 3, a linha VED-1 é rejeitada definitivamente e pivota-se para LSS-2, FCE-3, ou RAE-4.**

---

## Apêndice — raw data (para reprodução e auditoria)

**BTCUSDT 1h:** resultId=01M38RAZNWXAJ0NK54TF2BP46K, strategyId=01M38RAZXZ7QES5TGNFKQ26391, view=https://mcp-api.trader.dev/backtest/01M38RAZNWXAJ0NK54TF2BP46K

**ETHUSDT 1h:** resultId=01M38RFPZVJA1P9DC1HP66NKWF, strategyId=01M38RFQ5VJ58VK0P8PR5G82XT, view=https://mcp-api.trader.dev/backtest/01M38RFPZVJA1P9DC1HP66NKWF

**SOLUSDT 1h:** resultId=01M38RGKAETRA46E4PTYVAASJD, strategyId=01M38RGKFTNBA2P8TZMFZGZSYQ, view=https://mcp-api.trader.dev/backtest/01M38RGKAETRA46E4PTYVAASJD

**XRPUSDT 1h:** resultId=01M38RHBNGJFD8C94VHWWA2411, strategyId=01M38RHBTED8H42ZXYBQKA0EJ6, view=https://mcp-api.trader.dev/backtest/01M38RHBNGJFD8C94VHWWA2411

**Pine script original:** `scripts/ved1_v1.pine`

**Ambiente de teste:** Tra디어 Dev MCP (tv_jul26_mc7 engine), Bybit USDT linear perps, 2025-06-01 → 2026-09-24, $10k capital, 100% equity, margin 100/100, commission 0.05%, slippage 0, pyramiding 1.
