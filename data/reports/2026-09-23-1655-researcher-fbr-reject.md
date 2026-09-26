# Quant Mathematician Cycle Report — Cycle 01

**Date**: 2026-09-23 16:55 UTC-3  
**Agent**: researcher (Quant Mathematician loop)  
**Strategy**: QM-FBR-v1 / v2 — Failed Breakout Reversal (H2)  
**Status**: REJECT — line abandoned  

---

## 1. Hipóteses Geradas

### H1: Volatility-Regime Adaptive Mean-Reversion (VRAMR)
- ATR-normalized distance from EMA; operar só em regimes de vol baixa (constrição)
- Math basis: vol clustering → mean-reversion acceleration during compression
- Bancado: não selecionado nesta iteração

### H2: Failed Breakout Reversal (FBR) — selecionada
- Ineficiência: liquidity sweep + snapback após rejeição de breakout
- Por que crypto: livros de ordens shallow → sweeps frequentes
- Math basis: preço que toca extremo recent e fecha de volta → reversão esperada
- Pine expression: `low <= ta.lowest(low, N)[1] and close > that low`

### H3: Range Efficiency Collapse (REC)
- Compressão de range → expansão subsequente
- Não bancado nesta iteração

### H4: Distance-from-Equilibrium Exhaustion (DFEE)
- Distância da EMA em ATR sem pullback → exhaustion → mean-reversion
- Não bancado nesta iteração

---

## 2. Hipótese Selecionada

**H2 (FBR)** — simplicidade, parametrização mínima (lookback, vol filter, ADX regime filter), matematicamente transparente. Risco bem definido: SL estende-se além do sweepped extreme.

---

## 3. Regras de Trading

### Entrada Long
1. `low <= ta.lowest(low, lookback)[1]` — sweep do low recente
2. `close > ta.lowest(low, lookback)[1]` — snapback para dentro do range
3. `close > close[1]` — confirmação de momentum positivo
4. `atrRatio < volThresh` — filtro de vol (evita pánico)
5. `adx < adxThresh` (v2) — regime range / não-trending

### Entrada Short
1. `high >= ta.highest(high, lookback)[1]` — sweep do high recente
2. `close < ta.highest(high, lookback)[1]` — snapback
3. `close < close[1]` — momentum negativo
4. Mesmos filtros de vol e regime

### Stop Loss
- Long: `sweepLow[1] - slBuffer * atr` (abaixo do sweepped low + buffer)
- Short: `sweepHigh[1] + slBuffer * atr`

### Take Profit
- Long: `entryPrice + tpMult * atr`
- Short: `entryPrice - tpMult * atr`

### Time Exit
- Se posição aberta por > `maxBars` bars → close forçado

### Cooldown
- `cooldown` bars entre entradas na mesma direção

---

## 4. Pine Script

`data/pine/FBR-01.pine` (v1) e `data/pine/FBR-02.pine` (v2 com ADX)  

v1: vol filter somente (ATR ratio)  
v2: + ADX regime filter (`ta.dmi`)  

Strategy header MCP-compliant: 100% equity, margin 100/100, commission 0.05%, pyramiding 1, process_orders_on_close=true.

---

## 5. Backtest Matrix

### v1 — BTC 1h (baseline)
| Métrica | Valor |
|---|---|
| Net | -87.9% |
| PF | 0.63 |
| Max DD | 88.0% |
| Win rate | 23.4% (222W/725L) |
| Trades | 947 |
| Commission | $3,625 |

### v2 — BTC 1h (+ADX)
| Métrica | Valor |
|---|---|
| Net | -61.9% |
| PF | 0.64 |
| Max DD | 62.2% |
| Win rate | 19.4% (91W/377L) |
| Trades | 468 |
| Commission | $2,903 |

### v2 — Multi-símbolo (ETH, SOL, XRP, 1h)
| Symbol | Net% | PF | DD% | WR% | Trades |
|---|---|---|---|---|---|
| ETH | -34.6 | 0.87 | 38.7 | 19.5 | 565 |
| SOL | -44.2 | 0.86 | 53.9 | 19.5 | 745 |
| XRP | -42.0 | 0.84 | 46.1 | 19.5 | 615 |

Todos negativos. Nenhum symbol salvou a hipótese.

---

## 6. Diagnóstico

**O que o ADX melhorou**: trade count caiu 50% no BTC (947→468), max DD caiu de 88% para 62%. O filtro de regime funcionou como esperado — eliminou sinais em tendências fortes.

**O que não melhorou**: PF ficou ~0.64 (estável), win rate caiu de 23.4% para 19.4%. Isso indica que os trades restantes (em regimes range) também não têm edge — os sweeps em range são frequentemente continuation, não reversal.

**Padrão observado**: 
- Win rate ~19-23% em todos os símbolos → estrutura de perdas dominante
- Avg winning trade 2-3× avg losing trade (ratio avg win/loss 2-3.5) → reward:risk tem potencial, mas frequência de acerto insuficiente
- Sortino ~ -0.25 a -1.8 → risco ajustado negativo em todos

**Conclusão matemática**: A hipótese H2 falhou. Failed breakout não é edge consistente em crypto perp 1h — pelo menos com esta formulação. O conceito pode ter vida em timeframe maior ou com filtros adicionais de confirmação (ex: volume squeeze), mas nesta forma é rejeitável.

---

## 7. Fraquezas Identificadas

1. **Confirmação fraca**: `close > close[1]` como filtro de momentum é muito barato — não distingue swing real de noise.
2. **Sem filtro de estrutura**: não considera se o sweep é parte de um pullback legítimo em tendência — apenas ADX, que é lagging.
3. **SL fixo em ATR**: pode ser muito apertado em assets voláteis (BTC) ou muito largo em assets quietos (XRP), sem adaptação por símbolo.
4. **Sem filtro de tempo**: maxBars=30 é curto para mean-reversion e longo para continuation — parâmetro arbitrário.
5. **Os 4 símbolos testados têm performance consistentemente negativa** — não há "one coin wonder".

---

## 8. Veredito

### REJEITAR — line H2 (FBR) abandonada

Motivo: três strikes em uma iteração (v1 BTC -87.9%, v2 BTC -61.9%, multi-symbol todos negativos). PF < 1 em todos os casos. DD alto. Win rate abaixo do necessário para 보상rar risco.

**Linha H2 está morta**. Pivot para próxima hipótese na próxima iteração.

---

## 9. Próxima Iteração

**Proposer H3 (Range Efficiency Collapse — REC)** ou **H4 (Distance-from-Equilibrium Exhaustion — DFEE)** na próxima rodada:

- **H3**: ratio ATR / true range → detecção de compressão extrema → entrada no início da expansão com vol confirmation
- **H4**: |close - EMA| / ATR como z-score → quando > limiar e momentum fade → entrada reversa

Ambos têm grounding matemático mais forte que H2. Vou deixar BTC 1h como baseline de sanity e expandir para 3-5 símbolos no lançamento.

**Recomendação**: não reinventar a roda — parâmetros de entrada devem ser adaptados por símbolo (lookback, ATR multiplier) usando dados históricos, não values genéricos.

---

*Relatório gerado pelo Quant Mathematician loop. Créditos restantes após este ciclo: ~988. Stratégia QM-FBR-v2 salva em `data/pine/FBR-02.pine` para referência, mas line está rejeitada.*
