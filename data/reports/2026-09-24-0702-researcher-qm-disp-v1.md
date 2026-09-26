# Quant Mathematician Cycle Report
## 1. Hypotheses Generated

**H1 — Volatility-Normalized Displacement Snapback (SELECTED)**
Ineficiência: Quando o preço se desloca significativamente da sua mediana rolling (normalizado por ATR) e ao mesmo tempo a eficiência de range (close position dentro do corpo da barra) colapsa + a volatilidade contrai, há um sinal de exaustão de impulso e provável snapback de curto prazo.
Por que crypto: Alta beta e overreaction são características do mercado crypto; movimentos dispacionais muitas vezes exageram e voltam.
Cruzamento de símbolos: Hipótese é paramétrica (ATR + mediana), deveria generalizar para pares líquidos.
Regime de quebra: Tendências fortes unidirecionais (momentum sostenido sem contração de vol) — o sinal dispara no fim do pullback e o preço segue.
Expressão Pine: `percentile_nearest_rank` para equilíbrio, `atr` para normalização, eficiência de range customizada, contração de ATR como confirmação.

**H2 — Range-Efficiency Collapse Mean Reversion**
Idêntica em estrutura mas sem normalização por ATR — só range efficiency colapsado como entrada. Menos robusta, testada implicitamente via H1.

**H3 — Volume-Price Displacement Reversion**
Usaria OBV/PVT divergence para detectar deslocamento price-volume anômalo. Não implementada — H1 escolhida por simplicidade e maior fundamentação matemática.

**H4 — Failed Continuation After Volatility Expansion**
Entrada após expansão de vol seguida de falha de continuação (range de barra menor que média). SimILAR a H1 mas foco no setup de falha, não no deslocamento. Não escolhida — H1 abrange o mesmo territory com menos parâmetros.

## 2. Hypothesis Selected

**H1 — Volatility-Normalized Displacement Snapback (QM-DISP-v1)**

Matematicamente: o trade busca reversões de curto prazo após deslocamento anômalo do preço em relação à sua tendência central (mediana rolling), confirmado por (a) eficiência de range baixa (barras desequilibradas, típicas de climax/panic) e (b) contração de volatilidade (ATR < SMA do ATR), indicando exaustão do movimento.

O raciocínio é: preço viajou muito (displacement > 2x ATR) → as barras mostram eficiência de range caótica (fechamentos próximos aos extremos) → volatilidade contrai (o movimento acabou) → espera-se mean reversion.

## 3. Trading Rules

**Entrada Long:**
- `disp = |close - median(close, 20)| / ATR(14) >= 2.0`
- `close < median` (preço abaixo do equilíbrio)
- `effAvg = SMA(eff, 5) < 0.45` (eficiência de range colapsada)
- `ATR < SMA(ATR, 3)` (volatilidade contraindo)
- Cooldown: 2 barras após última saída

**Entrada Short:**
- Mesmas condições mas `close > median`

**Stop Loss:** 30 ticks de ATR a partir do preço de entrada
**Take Profit:** 40 ticks de ATR a partir do preço de entrada
**Cooldown:** 2 barras
**Max duration:** TP/SL hardcode (sem time exit)

**Regime filter:** Nenhum — estratégia pura, sem filtro de tendência.

## 4. Pine Script

Arquivo: `qm_disp_v1.pine` (disponível no repo)
Resumo: //@version=6, estratégia `QM-DISP-v1`, overlay, pyramiding=1, process_orders_on_close=true, commission 0.05%, equity 100%.

## 5. Backtest Matrix

| Symbol      | Timeframe | Result ID                                    | Trades | Net Profit % | PF    | Max DD % | WR %  |
|-------------|-----------|----------------------------------------------|--------|-------------|-------|----------|-------|
| BTCUSDT     | 1h        | 01M393EAX8N9XVAE1GHR34TCPC                   | 35     | -8.38%      | 0.13  | 8.38%    | 28.6% |
| ETHUSDT     | 1h        | 01M393G9X3HRSSHDY605XM7SXA                   | 38     | -0.13%      | 0.97  | 4.48%    | 31.6% |
| SOLUSDT     | 1h        | 01M393GZWJ34522MZ0M98E0X1N                   | 47     | -6.44%      | 0.39  | 7.58%    | 29.8% |
| DOGEUSDT    | 15m       | 01M393J6NCB2FHY055HW8FXY1Z                   | 175    | -11.33%     | 0.43  | 11.90%   | 25.1% |

Provavelmente mais símbolos teriam piorado. Matriz parada em 4 para decisão.

## 6. Results

**Aggregate (4 símbolos):**
- Soma de trades: 295
- Todos com PF < 1 (0.13–0.97)
- Todos com net profit negativo (-0.13% a -11.33%)
- Win rate entre 25% e 32%
- Short bias massivo: 72% das operação são short em média
- Longs tiveram resultado ligeiramente melhor que shorts em ETH (longNetProfit +133 vs short -146), mas não salva a estratégia

**Worst case:** DOGEUSDT 15m: -11.33%, PF 0.43, DD 11.9%, 175 trades — amostra grande mas sem edge.

**Best case:** ETHUSDT 1h: -0.13%, PF 0.97 — quase break-even mas sem edge positivo.

## 7. Diagnosis

**O que deu errado:**

1. **A hipótese matemática não se sustentou:** deslocamento normalizado + colapso de range efficiency + contração de vol NÃO gerou expectativa positiva. Isso é um resultado válido — a hipótese foi testada e rejeitada pela evidência.

2. **Viés de short excessivo:** 72–75% das operações são short. Isso sugere o sinal short dispara muito mais frequentemente que o long, mas os shorts são menos rentáveis — possivelmente porque em crypto o longo tende a terasy momentum positivo que o curto não captura.

3. **SL/TP proporcional a ATR pode ser inadequado:** 30/40 ticks de ATR é uma proporção fixa que pode ser muito curta para a escala de reversão real. Mas ajustar isso sem entender o mecanismo seria curve-fitting.

4. **Sem regime filter:** Em trending markets (que são comuns em crypto), o snapback não acontece — o preço continua. A estratégia entra no fim do pullback e o preço vai contra.

5. **Cooldown de 2 barras é curto demais** — pode estar entrando em séries de perdas consecutivas sem pausa suficiente.

**Não é um problema de amostra:** DOGEUSDT com 175 trades mostra que mesmo com amostra grande o edge não existe.

## 8. Verdict

**REJECT**

A hipótese QM-DISP-v1 (Volatility-Normalized Displacement Snapback) foi testada em 4 símbolos/timeframes, totalizando 295 trades, e mostrou:
- Profit factor < 1 em todos os casos (0.13–0.97)
- Net profit negativo em todos os casos
- Win rate baixa (25–32%)
- Sem robustez cross-symbol

A hipótese matemática não se sustentou. Isso é um resultado válido de pesquisa — descartar uma linha sem edge é progresso. Nenhum sinal de life was found. Recomenda-se **pivoting** para outra linha de pesquisa no próximo ciclo.

**Three-strikes rule:** Esta é a primeira tentativa nesta linha. Mas o resultado é elegantemente negativo (todos os símbolos concordam). Não justifica mais ciclos nesta mesma hipótese sem modificação conceitual fundamental.

## 9. Next Cycle

**Possíveis direções para o próximo ciclo:**

1. **Regime-aware displacement:** Adicionar um classificador de regime (trend vs chop) e só operar o snapback no regime chop. A hipótese original não filtrava — talvez o edge exista só em sideways.

2. **Failed breakout confirmation:** Em vez de displacement puro, esperar um breakout falho (preço vai além de nivel, volta, volume desaparece) — conceitualmente relacionado mas com trigger diferente.

3. **Volume-displacement divergence:** Usar OBV/PVT para confirmar que o deslocamento price não tem volume correspondente — volumes falsos são mais propensos a reversão.

4. **Pivot para outra família:** A dartboard de descoberta mostrou estratégias com vantagem (rsi-t200 4h local, squeeze TAO) — talvez valha a pena investigar essas linhas já com signs of life.

**Recomendação:** Pivoting. Nem incubar nem watchlist — rejeitar e tentar outra hipótese no próximo ciclo.

---

**Report metadata:**
- Gerado por: Quant Mathematician (researcher)
- Data: 2026-09-24
- Strategy ID: QM-DISP-v1 (criada como 01M393D5NS0YG7152AYWBE7Y4A no Trader Dev)
- Créditos gastos: ~4 backtests rápidos
- Nenhuma ordem real colocada.
