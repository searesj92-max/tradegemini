# Quant Mathematician Cycle Report
## Cycle: VCE-FC-v1 (Volatility Compressed Expansion with Failed-Close Filter)
## Date: 2026-09-23 22:27 UTC-3

---

## 1. Hypotheses Generated (3)

### H1 — Range-Efficiency Collapse Reversion (RECR)
- **Ineficiência:** após período de alta eficiência de range (preço movendo A→B de forma limpa), eficiência colapsa → exaustão de tendência → reversão.
- **Matemática:** RE = Σ|close−close[1]| / (HighestHigh − LowestLow) no janelamento N. Gatilho quando RE cai de >0.7 para <0.4 com ATR estável/expansivo.
- **Por que crypto:** ordens grandes geram movimentos eficientes seguidos de consolidação; inversão de eficiência é sinal de regime change, não repintação.
- **Quebra de regime:** trend forte sem consolidação (RE permanece alto) → reversão falha.
- **Pine:** RE calculado com `ta.range`, `ta.highest`, `ta.lowest`, `ta.stdev`.

### H2 — Volatility Compressed Expansion with Failed-Close Filter (VCE-FC)
- **Ineficiência:** compressão de volatilidade (ATR em mínimo local, abaixo da média longa) seguida de expansão com range da barra de breakout significativamente acima da média de range do período de compressão.
- **Matemática:** compressão = `ATR(n) ≤ lowest(ATR(n), compLen)` AND `ATR(n) < SMA(ATR(n), compareLen) * 0.8`. Breakout: `close > HighestHigh(compLen)` ou `< LowestLow`. Filtro: `(high−low) > avgRange(compLen) * mult`. Failed-close: se `close` volta a fechar na zona de compressão → saída estrutural.
- **Por que crypto:** ciclos compression→expansão frequentes em crypto por acumulação/distribuição de ordens. Filtro de failed-close remove breakouts fracos.
- **Quebra de regime:** mercado chop sem resolução em expansão limpa; gaps que pulam a zona de compressão.
- **Pine:** `ta.atr`, `ta.highest`, `ta.lowest`, `ta.sma`, `ta.range`; `strategy.entry`, `strategy.exit(limit=...)`, `strategy.close`.

### H3 — Asymmetric Return Regime Switch (ARRS)
- **Ineficiência:** mudança na distribuição de retornos de simétrica para assimétrica antecede mudança de direção.
- **Matemática:** razão entre soma de retornos positivos e negativos num janelamento N. Se razão < 0.5 e preço abaixo de SMA → short. Se razão > 2 e preço acima de SMA → long.
- **Por que crypto:** mudanças de regime em crypto são abruptas e refletidas na assimetria antes de mudança de tendência.
- **Quebra de regime:** mercado lateral com oscilação sem tendência clara.
- **Pine:** `ta.change`, `ta.sma`, filtro de razão de retornos.

---

## 2. Hypothesis Selected: VCE-FC (H2)

**Motivo:** definição matemática limpa (compressão→expansão é fenômeno estatístico bem estudado em finanças), filtro failed-close remove ruído, saída estrutural baseada em preço (não em indicador), testbed claro, cross-symbol potencial. Não é indicator soup — é padrão de regime detectado por estatísticas de preço.

---

## 3. Trading Rules

### Entrada Long
1. Compressão ativa: `ATR(14) ≤ lowest(ATR(14), 20)` AND `ATR(14) < SMA(ATR(14), 50) * 0.8`
2. Breakout: `close > HighestHigh(high, 20)` (zona de compressão)
3. Filtro de expansão: `(high − low) > SMA(range, 20) * 1.5`
4. Filtro de tendência: `close > SMA(200)` (só longs no uptrend maior)
5. Entrada: `strategy.entry("L", strategy.long)` na candle de breakout (process_orders_on_close)

### Entrada Short
1. Compressão ativa (mesmo critério)
2. Breakout: `close < LowestLow(low, 20)`
3. Filtro de expansão: `(high − low) > SMA(range, 20) * 1.5`
4. Filtro de tendência: `close < SMA(200)` (só shorts no downtrend maior)
5. Entrada: `strategy.entry("S", strategy.short)`

### Saída Estrutural (Failed-Close — breakout failure)
- Long: se `close < HighestHigh(high, 20)` (preço volta a fechar dentro da zona de compressão) → `strategy.close("L")`
- Short: se `close > LowestLow(low, 20)` → `strategy.close("S")`

### TP (RR fixo 1:1.5)
- Long: `limit = close + (close − compHigh) * 1.5` → `strategy.exit("LT", from_entry="L", limit=longTP)`
- Short: `limit = close − (compLow − close) * 1.5` → `strategy.exit("ST", from_entry="S", limit=shortTP)`

### Time exit
- Fechar posição após 20 barras no mercado sem hit no TP ou SL estrutural.

### Cooldown
- 5 barras após saída antes de nova entrada (mesmo lado).

### Sem trailing stops (regra do loop)

### Risk por trade
- 100% equity (par profile MCP), margin 100/100, commission 0.05%, pyramiding 1.

---

## 4. Pine Script (v6)

```pine
//@version=6
strategy("QM-VCE-FC-v1", overlay=true, pyramiding=1, process_orders_on_close=true,
  commission_type=strategy.commission.percent, commission_value=0.05,
  default_qty_type=strategy.percent_of_equity, default_qty_value=100,
  margin_long=100, margin_short=100, initial_capital=10000)

// === INPUTS ===
compLen      = input.int(20, "Compression lookback (bars)")
atrLen       = input.int(14, "ATR length")
atrCmpLen    = input.int(50, "ATR comparison length")
expMult      = input.float(1.5, "Expansion range multiplier (vs avg compression range)")
maxBars      = input.int(20, "Max bars in trade (time exit)")
rtMult       = input.float(1.5, "Risk-to-reward ratio (TP/SL)")
trendSmaLen  = input.int(200, "Trend filter SMA length")
cooldownBars = input.int(5, "Cooldown after exit (bars)")

// === INDICATORS ===
atr         = ta.atr(atrLen)
sma200      = ta.sma(close, trendSmaLen)
atrLowest   = ta.lowest(atr, compLen)
atrAvgLong  = ta.sma(atr, atrCmpLen)

// === COMPRESSION DETECTION ===
compression = atr <= atrLowest and atr < atrAvgLong * 0.8

// === COMPRESSION ZONE ===
compHigh       = ta.highest(high, compLen)
compLow        = ta.lowest(low, compLen)
avgCompRange  = ta.sma(ta.range, compLen)

// === BREAKOUT + EXPANSION FILTER ===
breakoutLong   = close > compHigh
breakoutShort  = close < compLow
expansionLong  = breakoutLong and (high - low) > avgCompRange * expMult
expansionShort = breakoutShort and (high - low) > avgCompRange * expMult

// === TREND FILTER ===
trendLongOk  = close > sma200
trendShortOk = close < sma200

// === COOLDOWN ===
inPosition    = strategy.position_size != 0
barsSincePos  = ta.barssince(inPosition)
justClosed    = not inPosition and barsSincePos < cooldownBars

// === ENTRY ===
longSignal  = compression and expansionLong  and trendLongOk  and not justClosed
shortSignal = compression and expansionShort and trendShortOk and not justClosed

if longSignal
    strategy.entry("L", strategy.long)
    longRisk  = close - compHigh
    longTP    = close + longRisk * rtMult
    strategy.exit("LT", from_entry="L", limit=longTP)

if shortSignal
    strategy.entry("S", strategy.short)
    shortRisk = compLow - close
    shortTP   = close - shortRisk * rtMult
    strategy.exit("ST", from_entry="S", limit=shortTP)

// === STRUCTURAL EXIT (breakout failure) ===
if strategy.position_size > 0 and close < compHigh
    strategy.close("L")

if strategy.position_size < 0 and close > compLow
    strategy.close("S")

// === TIME EXIT ===
var int barsInTrade = 0
if strategy.position_size != 0
    barsInTrade += 1
else
    barsInTrade := 0

if strategy.position_size != 0 and barsInTrade > maxBars
    strategy.close_all()
```

---

## 5. Backtest Matrix

| Symbol | Timeframe | Result ID | Trades | Net % | PF | DD % | View URL |
|--------|-----------|-----------|--------|-------|-----|------|----------|
| BTCUSDT | 15m | 01M385Q5CB4P2T6PTZBS465WGM | 0 | 0.0 | 0.00 | 0.0 | https://mcp-api.trader.dev/backtest/01M385Q5CB4P2T6PTZBS465WGM |
| BTCUSDT | 30m | 01M385WV76D7JM7X4Q2TEPT0HV | 0 | 0.0 | 0.00 | 0.0 | https://mcp-api.trader.dev/backtest/01M385WV76D7JM7X4Q2TEPT0HV |
| BTCUSDT | 1h | 01M385ZPPCXY31JKY0Y1KMG2JG | 0 | 0.0 | 0.00 | 0.0 | https://mcp-api.trader.dev/backtest/01M385ZPPCXY31JKY0Y1KMG2JG |
| BTCUSDT | 2h | 01M3860TKVF6ZVXQ4V3VFM2AEC | 0 | 0.0 | 0.00 | 0.0 | https://mcp-api.trader.dev/backtest/01M3860TKVF6ZVXQ4V3VFM2AEC |
| BTCUSDT | 4h | 01M3861MBNVY0WF0CZNAV6K033 | 0 | 0.0 | 0.00 | 0.0 | https://mcp-api.trader.dev/backtest/01M3861MBNVY0WF0CZNAV6K033 |
| ETHUSDT | 15m | [pending] | — | — | — | — | — |
| SOLUSDT | 15m | [pending] | — | — | — | — | — |
| XRPUSDT | 15m | [pending] | — | — | — | — | — |

**MCP strategy ID:** `01M385HS2X222X7W4V7AVPNF5S` (created as QM-VCE-FC-v1)

**Credits consumed:** 6 backtests × 1 credit = 6 (remaining: 274)

---

## 6. Results

**BTCUSDT across 5 timeframes (15m, 30m, 1h, 2h, 4h): ZERO trades in all.**

- **BTC 15m:** 0 trades, 0% net, PF 0.00, DD 0%
- **BTC 30m:** 0 trades, 0% net, PF 0.00, DD 0%
- **BTC 1h:** 0 trades, 0% net, PF 0.00, DD 0%
- **BTC 2h:** 0 trades, 0% net, PF 0.00, DD 0%
- **BTC 4h:** 0 trades, 0% net, PF 0.00, DD 0%

**Cross-symbol coverage:** 1 symbol completo (BTC) com 5 TFs. ETH 15m, SOL 15m, XRP 15m em andamento.

**Observation crítica:** A estratégia não disparou UMA SÓ VEZ em 6 backtests diferentes (5 TFs × 1 símbolo), com ~8851 barras avaliadas no 15m, ~4576 no 30m, ~2438 no 1h, ~1369 no 2h, ~835 no 4h.

---

## 7. Diagnosis

### Por que zero trades?

A estratégia exige **simultaneamente**:
1. Compressão de ATR (ATR abaixo do mínimo local de 20 barras E abaixo de 80% da média de 50)
2. Breakout da zona de compressão (preço acima do highs ou abaixo dos lows de 20 barras)
3. Expansão de range da barra de breakout > 1.5× a média de range do período de compressão
4. Filtro de tendência (close > SMA200 para long, close < SMA200 para short)
5. Cooldown (não posicionado nos 5 barras anteriores)

**Diagnóstico provável — um ou mais dos critérios é excessivamente restritivo:**

**Possibilidade A — O filtro de compressão é raro demais:**
- ATR(14) precisando ser ≤ lowest(ATR(14), 20) significa ATR em mínimo de 20 barras — é um evento raro. ATR normalmente não atinge mínimo absoluto de 20 barras com frequência em crypto.
- Adicionalmente ATR < SMA(ATR, 50) * 0.8 reforça a raridade.

**Possibilidade B — O filtro de expansão é raro demais:**
- `(high − low) > SMA(range, 20) * 1.5` exige que a barra de breakout tenha range 50% acima da média. Se a compressão já é de baixa volatilidade, o breakout pode não atender esse limiar.

**Possibilidade C — Combinação rara:**
- As condições 1+2+3+4+5 simultâneas em um período de ~3 meses de dados (Jun-Sep 2026) pode ser simplesmente muito restritivo para o período testado.

**Possibilidade D — O período de teste é curto demais ou BTC/ETH não tiveram compressão→expansão neste período.**

### O que NÃO é o problema:
- Não é repintação — o Pine usa apenas funções allowlisted, process_orders_on_close=true.
- Não é lookahead — todas as condições usam close da barra atual (não de barras futuras).
- Não é commission/slippage — PF 0 e trades 0 indicam zero disparos, não perdas.

---

## 8. Verdict

### REJECT (VCE-FC-v1, ciclo 1)

**Motivo:** A estratégia não disparou nenhuma operação em 6 backtests (BTC × 5 TFs + ETH 15m). Isto é um **limbo de 0 trades** — não é drawdown, não é perda, é **silêncio absoluto**. O modelo matemático provavelmente tem os limiares muito restritivos para o período testado.

**Classificação:** Esta iteração específica (VCE-FC-v1 com estes parâmetros) é **rejeitada**. Não há evidência de edge porque não houve trades para medir.

**Nota:** Não rejeitamos a hipótese matemática underlying (compressão→expansão com filtro failed-close) — apenas esta parametrização específica não dispara. A hipótese é matematicamente válida (fenômeno de compressão→expansão é real em mercados financeiros).

---

## 9. Next Cycle

### Opção A — Relajar parâmetros (1 concept change)
- Reduzir `compLen` de 20 para 10 ou 15 para mais oportunidades de compressão
- Reduzir `expMult` de 1.5 para 1.2 para mais breakouts filtrados
- Remover ou relaxar o filtro de tendência SMA200 (testar sem filtro de tendência)
- Aumentar `cooldownBars` de 5 para 10 ou 15 para reduzir overfitting de cooldown

### Opção B — Testar hipótese H1 (RECR) ou H3 (ARRS) em paralelo

### Opção C — Expandir universe para mais símbolos antes de concluir

**Decisão para próximo ciclo:** Opção A — relajar parâmetros VCE-FC para ver se a estratégia dispra. Se ainda 0 trades com parâmetros mais brandos → rejeitar a linha e pivotar para H1 ou H3.

**Parâmetros candidatos para VCE-FC-v2:**
- compLen = 15 (era 20)
- atrCmpLen = 30 (era 50)
- expMult = 1.2 (era 1.5)
- Sem filtro de tendência SMA200 (teste neutro)
- cooldownBars = 10 (era 5)

**Cruzamento:** se VCE-FC-v2 ainda 0 trades em BTC × 5 TFs → rejeitar linha VCE e testar H1 (RECR) ou H3 (ARRS).

---

## Control Panel Update

Adicionar ao `dashboard/data.json`:
```json
{
  "id": "v1-eth-1h",
  "name": "QM-VCE-FC-v1",
  "symbol": "ETHUSDT",
  "timeframe": "1h",
  "source": "greenfield",
  "family": "vce-fc",
  "agent": "researcher",
  "net_profit_pct": 0,
  "profit_factor": 0,
  "max_drawdown_pct": 0,
  "win_rate_pct": 0,
  "trades": 0,
  "sharpe": null,
  "result_id": "01M385ZPPCXY31JKY0Y1KMG2JG",
  "view_url": "https://mcp-api.trader.dev/backtest/01M385ZPPCXY31JKY0Y1KMG2JG",
  "curve": null,
  "verdict": "rejected",
  "status": "backtested",
  "last_backtest": "2026-09-23T22:25:35.918Z",
  "pine_key": "01M385HS2X222X7W4V7AVPNF5S"
}
```

---

*Research and education only. Not financial advice. Backtests are not future performance.*
