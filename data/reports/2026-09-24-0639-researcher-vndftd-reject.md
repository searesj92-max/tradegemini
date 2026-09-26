# Trader Dev Research Report — QM-VND-FTD v1/v1b

## 1. Goal
Testar hipótese H1 de greenfield: "Volatility-Normalized Displacement + Follow-Through Decay" (VND-FTD) — após um deslocamento grande de preço (normalizado por ATR) com follow-through fraco, o mercado exaure e o trade de reversão (fade) tem expectativa positiva.

## 2. Strategy Hypothesis (H1 — VND-FTD)
**Matemática central:** 
- Trigger bar detecta `|close[1] - close[n+1]| / ATR[1] > threshD` (big move normalizado)
- Follow-through: `|close - close[1]| / ATR < normBigMove × decay`
- Se follow-through fraco → exaustão → fade no contra
- Filtro de regime: evitar operação quando distância do preço da EMA > `emaDist` ATR (evitar mean-reversion em tendência)
- SL: extremo do big move + buffer ATR
- TP: 1× ATR na direção da reversão
- Cooldown: 5 barras após operação

## 3. Pine Script Changes
- v1 (BTC/ETH/SOL 1h): sem confirmação — entrada automática quando condição de exaustão detectada
- v1b (BTC/ETH/SOL 1h): adicionado bar de confirmação — candle do bar atual fecha em direção contrária ao big move (confirmLong: close > open AND close > triggerClose; confirmShort: close < open AND close < triggerClose)

## 4. Backtest Matrix

| Symbol | TF  | Version | Net %   | PF    | DD %  | WR %  | Trades | Long PF (net) | Short PF (net) |
|--------|-----|---------|---------|-------|-------|-------|--------|----------------|----------------|
| BTC    | 1h  | v1      | -16.94  | 0.498 | 17.79 | 28.45 | 116    | —              | —              |
| ETH    | 1h  | v1      | -9.26   | 0.780 | 15.07 | 29.94 | 157    | —              | —              |
| SOL    | 1h  | v1      | -20.80  | 0.565 | 24.66 | 23.42 | 158    | —              | —              |
| BTC    | 1h  | v1b     | -18.91  | 0.388 | 19.20 | 31.25 | 112    | —              | —              |
| ETH    | 1h  | v1b     | +1.94   | 1.072 | 6.94  | 37.10 | 124    | Long +7.8%     | Short -5.9%    |
| SOL    | 1h  | v1b     | -19.30  | 0.541 | 22.95 | 22.29 | 157    | —              | —              |

**Observações críticas:**
- v1b ETH foi o único positivou, com PF marginal 1.07 e Sharpe 0.74.
- BTC e SOL continuaram negativos em v1b.
- Confirmação reduziu trades ligeiramente mas não salvou BTC/SOL.
- Não testado em altcoins — crypto geralmente mais eficiente em 1h que ETH.

## 5. Diagnosis

**O que o backtest diz:**
- Não há edge universal: 5 dos 6 backtests negativos; o único positivo (ETH v1b) tem PF 1.07 que é insuficiente para ir além de watchlist, sem consistência cross-symbol.
- WR baixo (~23–37%) sugere que os stops estão sendo batidos com frequência — o big move frequentemente continua apesar do follow-through fraco, especialmente em BTC e SOL.
- ETH v1b mostra que em pelo menos um ativo a lógica tem pequena expectativa positiva, mas sem robustez cross-símbolo.
- Curva de equity de BTC e SOL mostra drawdowns consistentes sem recuperação — sem indicação de regime onde a estratégia funciona.

**Por que falhou:**
- A hipótese H1 assume que follow-through fraco após big move → reversal. Realidade: big moves frequentemente são inícios de nova fase (breakout sustentado), não exaustão. O filtro de regime (EMA distância) não foi suficiente para isolar condições de mean-reversion.
- BTC e SOL (maior liquidez, mais institucional) têm mais tendências sustentadas — o setup de fade é hostil.
- SL baseado no extremo do big move pode ser muito apertado em barras de follow-through (o continuum do big move pode atingir o stop e depois reverter — mas sem creditar o trade).

**Three-strikes analysis:**
- Strike 1: v1 BTC negativo
- Strike 2: v1b BTC negativo (com confirmação)
- Strike 3: SOL negativo em v1 e v1b
- ETH positivo marginalmente, mas sem replicação em outros símbolos.
- Conclusão: 3 strikes na linha H1. Sem evidência de edge universal.

## 6. Verdict: **REJECT**

**Rationale:**
- Não há edge replicável cross-symbol em 1h para H1 (VND-FTD).
- PF < 1 em 5/6 backtests, DD > 6% em todos, WR baixo.
- O único positivo (ETH v1b) é marginal (PF 1.07, Sharpe 0.74) e não se generaliza.
- Three strikes nos critérios deste loop: 3+ configurações sem edge consistente.
- Não incubar, não watchlist. Pivô obrigatório.

## 7. Next Cycle
Pivotar para H2 alternativa ou nova hipótese. Sugestões:
- **H2 — Failed-continuation confirmation with volatility regime**: em vez de fade imediato, esperar confirmação de falha de continuation + compressão de vol (range contraction após expansion) para entry; TP objetiva retorno ao ponto médio do range de compressão.
- **H3 — Distance-from-equilibrium with median-based reversion**: usar mediana móvel (mais robusta) e entrar quando preço se afasta > limiar com sinal de reversão de volatilidade (ctx de compression).
- Validar em múltiplos símbolos e TFs antes de julgamento.

## 8. Risk Notice
Pesquisa e educação. Backtest ≠ desempenho futuro. Operação real requer aprovação humana. Nenhuma ordem real foi colocada.

## 9. Files
- Pine v1: `C:/Users/seares/Desktop/botrade/tmp_qm_vndftd_v1.pine`
- Pine v1b: `C:/Users/seares/Desktop/botrade/tmp_qm_vndftd_v1b.pine`
- Backtest BTC v1: `01M391Y8PQ486MM78QW3CBT1X9`
- Backtest ETH v1: `01M391ZS9M291AZGE5JNCCXYW8`
- Backtest SOL v1: `01M3921E3P815261A1S21WM7DH`
- Backtest BTC v1b: `01M39266KA4FZ7WZKHN8PESX72`
- Backtest ETH v1b: `01M3926TK9MDGB17Z6DYZH1PYJ`
- Backtest SOL v1b: `01M3927CPPV8V4QM4JNKA7VXMK`
