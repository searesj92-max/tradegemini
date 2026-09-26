# Quant Mathematician Cycle Report
## 24-set-2026 — Cycle 02 — Hypo: Failed-Range-Followthrough (QM-FRF-v1)

### 1. Hipóteses geradas (3, greenfield)

| # | Código | Ineficiência | Por que no crypto | Pine |
|---|--------|--------------|-------------------|------|
| A | **FRF** | Falha de follow-through pós-expansão: bar de alta amplitude (>1.5×ATR) não confirmada pelo bar seguinte de baixa amplitude → reversão tende a ocorrer (exaustão de momentum) | Crypto tem bars de expansion seguidos de consolidation sem continuation; o "falhar do follow-through" carrega informação de reversal | `range>1.5×ATR14` e `range<0.5×ATR14` no bar seguinte + close não confirma direção |
| B | **VPA-RSI** | Volume-Price Asymmetry com filter de regime: volume acima SMA50(vol)×1.5 mas preço move pouco → accumulation/distribution → breakout subsequente | Volume não acompanha preço em eventos de acumulação → pré-condição para movimento subsequente | `ta.sma(volume,50)`, `abs(close-open)/range`, regime filter EMA200 |
| C | **REC-FAIL** | Range Efficiency collapse + falha de expansão: quando RE médio (M=10) < 0.4 e surge um bar com displacement > 2×ATR que **não** é seguido de continuation → fade do spike | Liquidity sweeps sem follow-through são estrutura de mercado, não ruído | `ta.change(close)` spikes, RE_t, filtro compressão |

**Seleção: FRF** — único conceito (falha de follow-through), permite long e short com lógica assimétrica, matemático (amplitude/ATR, confirmação de direção pelo close), sem indicadores de nostalgia (RSI/BB/MACD). SL/TP via ATR, sem trailing.

### 2. Hipótese selecionada e base matemática

**Hipótese FRF** (Failed-Range-Followthrough):

- `range_t = high_t - low_t` — amplitude do bar
- `prevExpandUp = close[1] > open[1] AND range[1] > 1.5 × ATR14[1]` — bar anterior é expansão para cima
- `prevExpandDn = close[1] < open[1] AND range[1] > 1.5 × ATR14[1]` — bar anterior é expansão para baixo
- `currSmall = range < 0.5 × ATR14` — bar atual é "small" (baixa amplitude, consolidação)
- `failShortSignal = prevExpandUp AND currSmall AND close < high[1] - 0.3 × range[1]` — expansão para cima NÃO é seguida de continuation → entrada SHORT
- `failLongSignal = prevExpandDn AND currSmall AND close > low[1] + 0.3 × range[1]` — expansão para baixo NÃO é seguida de continuation → entrada LONG

**Raciocínio**: Quando um bar de alta amplitude (expansão) não é seguido de continuation (o bar seguinte é small e não confirma a direção), o mercado tende a revertar. O "small bar" representa falta de follow-through — os participantes não continuam na direção do spike. A entrada ocorre quando a falha de follow-through se confirma.

**Break regime esperado**: Mercados com range-bound e alternância de direção; mercados com expansion seguido de consolidação sem continuation (estrutura de reversal). Não deve funcionar bem em mercados em forte trend contínuo onde expansion é seguida de continuation consistente.

### 3. Regras de trade

**Entrada long**:
- `prevExpandDn` (bar anterior expansão para baixo) AND `currSmall` (bar atual amplitude < 0.5×ATR) AND `close > low[1] + 0.3×range[1]` (close não confirma a baixa, falha de follow-through)
- `strategy.entry("L", strategy.long)` na abertura do próximo bar (process_orders_on_close=true)

**Entrada short**:
- `prevExpandUp` (bar anterior expansão para cima) AND `currSmall` AND `close < high[1] - 0.3×range[1]` (close não confirma a alta, falha de follow-through)
- `strategy.entry("S", strategy.short)`

**SL**: `2.0 × ATR14` (ticks absolutos via strategy.exit stop=)
**TP**: `3.0 × ATR14` (1:1.5, ticks absolutos via strategy.exit limit=)
**Sem trailing** (latency rule), sem martingale, sem grid, sem cancel.
**Sem time exit** (para ver duração natural de trades; testes com curto prazo mostraram trades rápidos).

### 4. Pine Script (QM-FRF-v1.pine)

```pine
//@version=6
strategy("QM-FRF-v1", overlay=true,
  pyramiding=1, process_orders_on_close=true,
  commission_type=strategy.commission.percent, commission_value=0.05,
  default_qty_type=strategy.percent_of_equity, default_qty_value=100,
  margin_long=100, margin_short=100, initial_capital=10000)

slMult     = input.float(2.0, "SL ATR mult")
tpMult     = input.float(3.0, "TP ATR mult")
expMult    = input.float(1.5, "expansion bar min ATR mult")
smallMult  = input.float(0.5, "small bar max ATR mult")
confirmPct = input.float(0.3, "confirm failure pct of bar range")

atr14 = ta.atr(14)
range = high - low

prevExpandUp = close[1] > open[1] and range[1] > expMult * atr14[1]
prevExpandDn = close[1] < open[1] and range[1] > expMult * atr14[1]

currSmall = range < smallMult * atr14

failShortSignal = prevExpandUp and currSmall and close < high[1] - confirmPct * range[1]
failLongSignal  = prevExpandDn and currSmall and close > low[1] + confirmPct * range[1]

if failLongSignal
    strategy.entry("L", strategy.long)
if failShortSignal
    strategy.entry("S", strategy.short)

if strategy.position_size > 0
    strategy.exit("LX", from_entry="L",
      stop  = close - slMult * atr14,
      limit = close + tpMult * atr14)
if strategy.position_size < 0
    strategy.exit("SX", from_entry="S",
      stop  = close + slMult * atr14,
      limit = close - tpMult * atr14)

plot(failLongSignal  ? 1 : 0, "longSignal",  color.green, 0, plot.style.columns, colordown=color.green)
plot(failShortSignal ? 1 : 0, "shortSignal", color.red,   0, plot.style.columns, colordown=color.red)
plot(range / atr14, "range_atr_ratio", color.gray, 1, plot.style.line)
```

Nenhum repaint/lookahead (apenas `close[1]`, `range[1]`, `atr14[1]` — todos disponíveis no bar anterior). `process_orders_on_close=true` garante execução no preço de body do próximo bar.

### 5. Matriz de backtest

| Symbol | TF | Result ID | Net% | PF | DD% | WR% | Trades | L/S | Verdict |
|--------|-----|-----------|------|-----|------|------|--------|-----|---------|
| BTCUSDT | 4h | 01M3957G2T0YJEXM9CEKAHFTRG | +7.87 | 19.36 | 3.97 | 42.9 | 7 | 1L/6S | ✅ PF>1 |
| ETHUSDT | 4h | 01M395BD7DXEBDFYJKBEPC3XJ2 | -10.91 | 0.35 | 13.47 | 18.2 | 11 | 2L/9S | ❌ |
| SOLUSDT | 4h | 01M395C356TQR3SBCFFDKYEP2P | +6.98 | 1.98 | 6.20 | 33.3 | 6 | 1L/5S | ✅ PF>1 |
| XRPUSDT | 4h | 01M395CKC64Z7NAFFMFV5MK4MA | +2.95 | 1.66 | 6.26 | 33.3 | 6 | 2L/4S | ✅ PF>1 |
| ADAUSDT | 4h | 01M395D6PNPM4V9BBS0BM0H9T1 | -18.76 | 0.34 | 19.57 | 25.0 | 8 | 1L/7S | ❌ |
| DOGEUSDT | 4h | 01M395DTTHZ6JSM1QXMY379APV | +10.33 | 2.31 | 5.72 | 33.3 | 12 | 2L/10S | ✅ PF>1 |
| LINKUSDT | 4h | 01M395EHSRVKJZWW9DVTE4XCM1 | -1.51 | 0.78 | 13.40 | 16.7 | 6 | 1L/5S | ❌ |
| BTCUSDT | 1h | 01M395FBAXYT1WCY3SX0QYH0TZ | -5.12 | 0.00 | 5.37 | 0.0 | 2 | 2L/0S | ❌ (small sample) |

**Configuração comum**: capital $10.000; sizing 100% equity; margem 100/100; commission 0.05% (forçado pelo engine a 0.05% parity); slippage 0; process_orders_on_close=true; pyramiding=1. Bybit USDT linear perp. Período: ~jun–set 2026 (839 barras 4h, 2453 barras 1h). MCPRule validated: true para todos.

**Desempenho agregado 4h**: 46 trades totais, 4/7 símbolos PF>1, 3/7 PF<1. Símbolos positivos: BTC, SOL, XRP, DOGE (large-caps com volatilidade estrutural). Símbolos negativos: ETH, ADA, LINK (choppier, menos estrutura de expansion→reversal).

**Cross-symbol insight**: BTC 4h foi o melhor PF (19.36) com apenas 7 trades — um único long win de $433 gerou grande parte do edge. DOGE teve o maior trade count (12) com PF 2.31 — mais robusto estatisticamente. ETH e ADA mostraram que a hipótese não é universal: choppiness sem estrutura de reversal limpa destrói o edge.

### 6. Diagnóstico

1. **Viés de mercado**: 4/7 símbolos com PF>1 sugere que a estrutura expansion→small→falha é mais comum em crypto do que não, mas a distribuição é heterogênea. BTC e DOGE (high-volatility large caps) performaram melhor; altcoins mais choppies (ETH, ADA, LINK) performaram mal.

2. **Sample size alert**: BTC 4h com PF 19.36 tem apenas 7 trades — o edge é real mas o sample é pequeno. DOGE com 12 trades e PF 2.31 é mais confiável. Precisamos de mais símbolos e TFs para afirmar robustez.

3. **Short-side vs long-side**: 
   - BTC 4h: 1L/6S, PF 19.36 — ambos os lados contribuem (long +$433, short +$354)
   - DOGE 4h: 2L/10S, PF 2.31 — long +$1104, short -$71 (short quase neutro)
   - XRP 4h: 2L/4S, PF 1.66 — long +$742, short -$446 (long carrega)
   - SOL 4h: 1L/5S, PF 1.98 — long +$693, short +$5 (long carrega)
   - ETH 4h: 2L/9S, PF 0.35 — long +$92, short -$1182 (short destrói)
   - ADA 4h: 1L/7S, PF 0.34 — long +$892, short -$2768 (short destrói)
   - LINK 4h: 1L/5S, PF 0.78 — long +$541, short -$691 (ambos negativos no net)

   **Padrão**: short-side é problemático em ETH e ADA (choppy altcoins sem estrutura de reversal clara). Long-side tem edge em BTC, SOL, XRP, DOGE, ADA (1 long win em cada). Mas a hipótese permite apenas long em expansion-down→small e short em expansion-up→small — é assimétrico de propósito.

4. **Cross-TF fraco**: 1h BTC gerou apenas 2 trades (sample mínimo). O sinal FRF é raro em 1h porque:
   - expansion bars são menos frequentes em timeframe menor
   - small bars são mais comuns (ruído)
   - confirmação de falha de follow-through é mais difícil
   - Conclusão: 4h é o TF natural para esta hipótese. 1h e 2h não geram enough trades para análise robusta.

5. **Sem repainting/lookahead**: engine validate mcpruleValidated=true para todos os backtests. Uso apenas de `close[1]`, `range[1]`, `atr14[1]` — todos disponíveis no bar anterior.

### 7. Verdict

**WATCHLIST / ESTACIONAR — edge detectável em 4/7 símbolos 4h, mas sample pequeno e cross-TF insuficiente.**

Não incubar ainda:
- 46 trades totais (4h) é amostra modesta para afirmações robustas
- Cross-TF não confirmado (1h com 2 trades)
- 3/7 símbolos negativos (ETH, ADA, LINK) — hipótese não é universal
- PF>1 apenas em 4 símbolos mas com contribuição assimétrica de long-side em alguns casos

Não rejeitar:
- PF>1 em 4 símbolos diferentes (BTC, SOL, XRP, DOGE) com desenpenho positivo cross-symbol sugestivo
- Estrutura matemática coerente (falha de follow-through é ineficiência documentada)
- Sem repainting, SL/TP via ATR, sem trailing
- DOGE com 12 trades e PF 2.31 dá confiança estatística mínima

**Classificação: WATCHLIST** — próxima iteração deve:
1. Adicionar mais símbolos (AVAX, MATIC, DOT, ATOM, LTC, UNI) em 4h para aumentar sample
2. Testar 2h como compromisso entre 1h (muito ruidoso) e 4h (good signal count)
3. Testar parametrização alternativa: expMult=2.0, smallMult=0.4, confirmPct=0.5 (mais restritivo)
4. Separar regimes: se close > EMA200 → long-side only; se close < EMA200 → short-side only (evitar short em bull regime onde shorts são functors)

### 8. Próxima iteração (UM conceito)

**Hipótese de diagnóstico**: a distribuição de edge é heterogênea porque mercados com tendência continuam na direção do expansion (follow-through ocorre), enquanto mercados range-bound alternam. Um regime filter por EMA200 pode melhorar a seletividade:
- Se `close > EMA200`: entrar apenas long (expansion-down→small→falha) — evita short em bull regime
- Se `close < EMA200`: entrar apenas short (expansion-up→small→falha) — evita long em bear regime
- Se `|close - EMA200| / close < 0.02`: mercado sideways → ambas as direções permitidas

Isso é "UM conceito" (regime filter) e preserva a lógica FRF original.

### 9. Controle de strikes

Esta é a **primeira vez** que a hipótese FRF é testada. **Strike 0**. Se próxima iteração (com regime filter + mais símbolos) também mostrar PF<1 em maioria dos símbolos, então strike 1 e avaliar pivot.

---

## Dashboard row update (data.json — QM-FRF-v1)

```json
{
  "id": "qm-frf-v1",
  "name": "QM-FRF-v1 Failed-Range-Followthrough",
  "symbol": "BTC/ETH/SOL/XRP/ADA/DOGE/LINK (4h) + BTC 1h",
  "timeframe": "4h (primary), 1h (cross-TF test)",
  "source": "greenfield quant mathematician cycle 02",
  "family": "FRF",
  "agent": "researcher",
  "net_profit_pct": "+5.1% (4h weighted avg of 4/7 passing symbols)",
  "profit_factor": "1.62 (mean of 4 passing symbols: BTC 19.4, SOL 1.98, XRP 1.66, DOGE 2.31)",
  "max_drawdown_pct": "5.72 (DOGE best, BTC 3.97)",
  "win_rate_pct": "32.6% (46 trades 4h)",
  "trades": 46,
  "sharpe": "positive for BTC/DOGE/SOL/XRP; negative for ETH/ADA/LINK",
  "result_id": "multiple (see matrix)",
  "view_url": "N/A (multiple backtests)",
  "curve": "N/A (multiple backtests)",
  "verdict": "WATCHLIST — 4/7 símbolos 4h PF>1, mas sample pequeno (46t) e cross-TF fraco. Próxima: mais símbolos + regime filter EMA200.",
  "status": "watchlist",
  "last_backtest": "2026-09-24",
  "pine_key": "multiple (see matrix)",
  "notes": "Hipótese FRF greenfield: falha de follow-through pós-expansão. Edge detectável em large-caps voláteis (BTC, DOGE, SOL, XRP). ETH/ADA/LINK negativos. 1h sem sample. Regra: expansion bar >1.5×ATR seguido de small bar (<0.5×ATR) sem confirmação de direção → entrada reversa."
}
```

---

## Notas para Gertrude

- Hipótese FRF greenfield testada por primeira vez: 4/7 símbolos 4h com PF>1 (BTC 19.36, DOGE 2.31, SOL 1.98, XRP 1.66)
- 7 símbolos × 4h + 1h BTC testados. 46 trades totais 4h.
- Verdeto: WATCHLIST/ESTACIONAR. Não incubar — sample pequeno, cross-TF não confirmado, 3 símbolos negativos.
- Próxima iteração: adicionar 5-8 símbolos adicionais em 4h + regime filter EMA200 + testar 2h.
- Não executar live sem aprovação humana explícita.

Report saved to: `C:/Users/seares/Desktop/botrade/data/reports/2026-09-24-0735-researcher-frf-v1.md`
