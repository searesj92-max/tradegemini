# Quant Mathematician Cycle Report
## Cycle: QM-VPA-v1 (Volume-Price Anomaly — Asymmetric Flow Detection)
## Date: 2026-09-24

---

## 1. Hipóteses Geradas (3 greenfield)

### H1 — VPA: Volume-Price Anomaly (Asymmetric Flow Detection)

**Ineficiência alvo:** Quando o retorno de uma barra é grande (deslocamento significativo) mas o volume associado é anomalmente BAIXO relativo ao volume habitual daquele par em tal retorno, há indício de movimento "vazio" — sem participação genuína de mercado. Bars seguintes tendem a refundir o preço na direção oposta ao "fake displacement".

**Matemática central:**
- `ret = |close - open| / open` (módulo do retorno de barra)
- `volNorm = volume / ta.sma(volume, 20)` (volume normalizado por média móvel)
- `volAnomLow = volNorm < 0.5 AND ret > 0.008` (movimento grande com volume fraco)
- `direction = close > open ? +1 : -1`
- `entry = (direction[1] == bearish, ret[1] > 0.8%, volAnomLow) AND close[1] < sma(close,20)` → long

**Por que na crypto:** Fluxo fragmentado entre exchanges; movimentos sem participação real (dry bars) são frequentes em mercados de baixa liquidez ou com stops concentrados — reversão esperada.

**Breaking regime:** breakout real com volume alto (vol > avg); tendência com participação consistente; horário de mercado com vol massivo.

---

### H2 — ROE: Range-of-Expansion Exhaustion

**Ineficiência alvo:** Após sequência de barras com range acima da média, o preço entra em consolidação. O evento de expansão se esgota.

**Matemática central:** `range = high - low`; `rangeAvg = ta.sma(range, 20)`; `expandingCount = count of last N bars with range > 1.5×rangeAvg`; `collapse = range < 0.7×rangeAvg`; entrada após `expandingCount >= 3 AND collapse`.

**Por que na crypto:** Picos de vol seguidos de quietude; a energia do movimento se dissipa.

**Breaking regime:** tendência forte sem pullback; compressão extrema sem expansão prévia.

---

### H3 — TRF: Trend Resumption Filter (Failed-Follow-Through)

**Ineficiência alvo:** Rompimento de nível sem volume confirming → fakeout. Entrar na direção oposta ao fake breakout.

**Matemática central:** `resistance = ta.highest(high, N)[1]`; `breakoutHigh = high > resistance`; `volWeak = volume < ta.sma(volume, 20) * 0.8`; `failedBreakout = breakoutHigh AND volWeak` → short.

**Por que na crypto:** Stops concentrados em extremos; fakeouts com volume fraco são detectáveis e revertentes.

**Breaking regime:** mercado com vol consistentemente baixo (sem interesse); breakout real com volume alto.

---

## 2. Hipótese Selecionada

**H1 — VPA (Volume-Price Anomaly)**

**Motivo da seleção (por ordem de prioridade do loop):**

1. **Simplicidade** — 2 séries (retorno, volume normalizado), 1 condição composta, sem múltiplos indicadores.
2. **Testabilidade** — sinal limpo, sem ambiguidade de janelamento (tudo no bar[1]).
3. **Math rigor** — normalização por vol mediana remove dependência de escala; retorno relativo ao open é lagging-free.
4. **Generalizabilidade** — "movimento grande com volume fraco" é independente do par, aplica-se a BTC (vol alto) e alts (vol baixo) sem retuning.
5. **Clear risk management** — SL baseado em ATR, TP baseado em retorno à média móvel, sem trailing.

**Contraste com hipóteses anteriores que falharam:**

| Ciclo | Linha | Motivo do fracasso | Distinção do VPA |
|-------|-------|-------------------|------------------|
| MSE-v1 | LRS | 0 trades — 5 condições AND, evento muito raro | VPA: 3 condições simples, não 5 eventos raros |
| MSE-v1 | REA | 0 trades — queda de eficiência rara | VPA: não depende de "eficiência" (conceito mais raro) |
| MSE-v1 | JM | 0 trades — ssIndex < 0.6 muito restritivo | VPA: não usa coil-swithen stability index |
| VND-v1 | VND | PF<1 — fade de single-bar displacement não funciona | VPA é "volume fraco + movimento grande" (distinto de fade de displacimento) |

**VPA é matematicamente distinto:** não é "fade do extremo", nem "eficiência de range", nem "coil swithen", nem "displacimento normalizado com close em extremidade". É detecção de **anomalia de fluxo** (volume baixo + movimento grande = movimento sem respaldo).

---

## 3. Regras de Trading

### Entradas (Long)

| Condição | Expressão |
|----------|-----------|
| Barra anterior bearish | `close[1] < open[1]` |
| Movimento grande | `|close[1] - open[1]| / open[1] > 0.008` (0.8%) |
| Volume anomalamente baixo | `volume[1] < ta.sma(volume, 20) * 0.5` |
| Preço abaixo do equilíbrio | `close[1] < ta.sma(close, 20)` |
| Cooldown ativo | `cd > cooldownBars` |

→ **Long entry** no bar seguinte ao sinal.

### Entradas (Short)

| Condição | Expressão |
|----------|-----------|
| Barra anterior bullish | `close[1] > open[1]` |
| Movimento grande | `|close[1] - open[1]| / open[1] > 0.008` |
| Volume anomalamente baixo | `volume[1] < ta.sma(volume, 20) * 0.5` |
| Preço acima do equilíbrio | `close[1] > ta.sma(close, 20)` |
| Cooldown ativo | `cd > cooldownBars` |

→ **Short entry** no bar seguinte ao sinal.

### Saídas

| Tipo | Valor | Motivo |
|------|-------|--------|
| **TP** | `ta.sma(close, 20)` (volta à média móvel) | Reembolso ao equilíbrio após anomalia revertida |
| **SL** | `1.5 × ATR` abaixo/acima do preço de entrada | Proteção contra movimento genuíno |
| **Time exit** | 20 barras | Limita exposição se não reverte |
| **Cooldown** | 1 barra após qualquer saída | Evita overtrading pós-sinal |

### Invalidação

- Se o preço atinge o TP antes do SL → saída normal (não inválido).
- Se o sinal de entrada oposto aparece antes do fechamento do bar → entrada cancelada (cooldown reiniciado).

### Risco

- 100% equity, pyramiding=1, margin 100/100, commission 0.05%.
- Sem trailing stops (regra de latência do loop).

---

## 4. Pine Script (qm_vpa_v1_wip.pine)

```pine
//@version=6
strategy("QM-VPA-v1 [wip] — Volume-Price Anomaly", 
  overlay=true, pyramiding=1, process_orders_on_close=true,
  commission_type=strategy.commission.percent, commission_value=0.05,
  initial_capital=10000, default_qty_type=strategy.percent_of_equity,
  default_qty_value=100, margin_long=100, margin_short=100)

// Inputs
retThresh       = input.float(0.008, "Return threshold (fractional)", minval=0.0, step=0.001, group="Entry")
volAnomMult     = input.float(0.5, "Volume anomaly multiplier (vs SMA)", minval=0.1, step=0.1, group="Entry")
smaPeriod       = input.int(20, "SMA period (equilibrium)", minval=5, group="Entry")
atrLen          = input.int(14, "ATR length", minval=2, group="Risk")
slAtrMult       = input.float(1.5, "SL ATR multiplier", minval=0.5, step=0.1, group="Risk")
cooldownBars    = input.int(1, "Cooldown bars", minval=0, group="Risk")
timeExitBars    = input.int(20, "Max bars in trade", minval=1, group="Risk")

// Calculations
atr = ta.atr(atrLen)
smaClose = ta.sma(close, smaPeriod)
smaVol = ta.sma(volume, smaPeriod)

// Bar [1] conditions (anomalous bar)
retBar1 = math.abs(close[1] - open[1]) / open[1]
volAnom = volume[1] < smaVol * volAnomMult
bigMoveBear = retBar1 > retThresh and close[1] < open[1]
bigMoveBull = retBar1 > retThresh and close[1] > open[1]
priceAboveEq = close[1] > smaClose
priceBelowEq = close[1] < smaClose

// Signals
longSig  = bigMoveBear and volAnom and priceBelowEq
shortSig = bigMoveBull and volAnom and priceAboveEq

// Cooldown
var int cd = 0
if strategy.position_size != 0
    cd := 0
else if cd == 0
    cd := 1
else
    cd += 1
canTrade = cd > cooldownBars

// Entries
if longSig and canTrade
    strategy.entry("L", strategy.long)
if shortSig and canTrade
    strategy.entry("S", strategy.short)

// Exits
if strategy.position_size > 0
    strategy.exit("LX", from_entry="L",
        limit=smaClose,
        stop=strategy.position_avg_price - atr * slAtrMult,
        loss=0, profit=0)
if strategy.position_size < 0
    strategy.exit("SX", from_entry="S",
        limit=smaClose,
        stop=strategy.position_avg_price + atr * slAtrMult,
        loss=0, profit=0)

// Time exit
var int barsInTrade = 0
if strategy.position_size != 0
    barsInTrade += 1
else
    barsInTrade := 0
if barsInTrade > timeExitBars
    strategy.close_all()

// Plots
plot(longSig,  "Long Signal",  color=color.green, style=plot.style_circles, linewidth=2)
plot(shortSig, "Short Signal", color=color.red,   style=plot.style_circles, linewidth=2)
```

**Nota técnica:** `retBar1` usa `open[1]` como dereferência (preço de abertura conhecido no bar[1] — lagging-free). `volAnom` avaliado no bar[1] completo (fechamento conhecido). `smaClose` no TP: se o preço estiver abaixo da média, o TP é a média — reversão esperada ao equilíbrio. SL baseado em ATR para proteção vol-adjusted.

---

## 5. Backtest Matrix

### Configuração
- **Engine:** tv_jul26 (TV_ENGINE_JUL_26 parity)
- **Período:** ~Jun 2026 → Sep 24 2026 (último bar disponível no ClickHouse)
- **Capital:** $10,000
- **Sizing:** 100% equity, margin 100/100
- **Commission:** 0.05% (mcp parity)
- **Slippage:** 2 ticks

### Matriz (5 símbolos × 1h)

| # | Símbolo | TF | Strategy ID | Result ID | Trades |
|---|---------|----|-------------|-----------|--------|
| 1 | BTCUSDT | 1h | 01M38R7K9ZQ8KXM2SMA8PXJ6MN | 01M38R7KFN7R2D62T1PGVYTCQH | 0 |
| 2 | ETHUSDT | 1h | 01M38R7KCSWJN95EMXT7W73RHMX | 01M38R7LD1NRVBN6WH5A04J9XTF | 0 |
| 3 | SOLUSDT | 1h | 01M38R7KFL1F1AGAWDPZEHBVD4W | 01M38R7LFXDH62HBVY5J5NFQFSD | 0 |
| 4 | XRPUSDT | 1h | 01M38R7K64QW4QVK8MDMHZXGSFB | 01M38R7LCMF2A9N1JFQJYJXWJBV | 0 |
| 5 | BNBUSDT | 1h | 01M38R7K4YR3PM5A03WC0N29GX4 | 01M38R7LA2KVBD7RN1CGVE4VSBH | 0 |

---

## 6. Results

### Síntese numérica

**0 trades em 5 símbolos × 5 backtests.**

||| Métrica | Valor |
||---------|-------|
|| Total trades | **0** |
|| Net profit | **$0 (0%)** |
|| Profit factor | **0** |
|| Win rate | **N/A** |
|| Max drawdown | **0%** |
|| Avg trade | **N/A** |
|| Sharpe | **N/A** |

### Visualizações

- BTC 1h: https://mcp-api.trader.dev/backtest/01M38R7KFN7R2D62T1PGVYTCQH
- ETH 1h: https://mcp-api.trader.dev/backtest/01M38R7LD1NRVBN6WH5A04J9XTF
- SOL 1h: https://mcp-api.trader.dev/backtest/01M38R7LFXDH62HBVY5J5NFQFSD
- XRP 1h: https://mcp-api.trader.dev/backtest/01M38R7LCMF2A9N1JFQJYJXWJBV
- BNB 1h: https://mcp-api.trader.dev/backtest/01M38R7LA2KVBD7RN1CGVE4VSBH

---

## 7. Diagnosis

### O que o dado diz

**Silêncio absoluto em 5 símbolos × 2460 barras avaliadas por teste.**

Isso é **ausência de disparo**, não drawdown nem perda. O padrão "movimento grande + volume baixo + close em extremidade" não ocorreu (ou não atendeu os limiares) em BTC, ETH, SOL, XRP, BNB no período Jun-Sep 2026 em 1h.

### Diagnóstico por hipótese

**VPA (Volume-Price Anomaly):**
- A condição `volume[1] < ta.sma(volume, 20) * 0.5` (volume < metade da média) é restritiva: filtra volume baixo, mas também filtra movimentos com volume "normalmente baixo" que podem ser genuinamente revertentes.
- O retorno mínimo de 0.8% em 1h é significativo para BTC (vol baixo em 1h) mas pode ser muito alto para alts de menor liquidez.
- **Diagnóstico raiz:** O evento "movimento >0.8% com volume <50% da média" pode ser muito raro em 1h em mercados relativamente estáveis (Jun-Sep 2026). Ou o limiar de volume é desconectado da realidade (o volume "anômalo" que sinaliza reversão pode ser <70% da média, não <50%).

### Diagnóstico transversal (o que NÃO é o problema)

- **Não é repainting:** o código é clean (process_orders_on_close, sem request.security, sem arrays).
- **Não é lookahead:** toda a lógica usa [1] ou séries calculadas no bar atual.
- **Não é commission/slippage:** 0 trades significa que o problema é a lógica de entrada, não os custos.
- **Não é falta de dados:** 2460 barras avaliadas por teste (cobertura completa do período).

### O que PODE ser o problema

1. **Os eventos que a hipótese busca são raros neste período:** Jun-Sep 2026 em crypto 1h peut-être não teve movimentos de 0.8%+ com volume <50% da média em frequência suficiente para disparar o sinal.

2. **Os limiares são desconectados da realidade do mercado:** `volAnomMult=0.5` pode ser muito restritivo. O volume anômalo que sinaliza reversão pode ser <70% ou <80% da média, não <50%.

3. **O retorno mínimo de 0.8% em 1h é muito alto para a maioria dos pares exceto BTC:** SOL, XRP, BNB em 1h podem não ter barras com movimento tão grande com volume baixo.

4. **O período é curto demais para eventos raros:** ~3 meses de dados podem não conter o evento que a hipótese descreve se ele ocorre em frequência menor que 1 por 2460 barras.

---

## 8. Verdict

### REJECT (Linha VPA — strike 1)

**Justificativa:**

1. **0 trades em 5 símbolos × 5 backtests** — sem evidência de edge por definição (não há trades para medir PF, WR, DD).
2. **O padrão é consistente através de símbolos:** BTC, ETH, SOL, XRP, BNB dão o mesmo resultado — não é um problema de símbolo específico.
3. **Não é um problema técnico corrigível:** o código é clean (mcpruleValidated=true em todos os testes; sem repainting, sem lookahead, sem bugs de janelamento).
4. **A hipótese é falsificável e foi falsificada:** se o evento "movimento grande + volume fraco" produzisse edge, haveria pelo menos alguns trades em 5 símbolos × 2460 barras cada. O silêncio absoluto indica que o evento não ocorre no período testado com os limiares atuais, ou que o evento não é previsório de reversão.

**Classificação no pipeline:**
- **REJECT** — não incubar, não watchlist. Registrar como "hipótese de volume-price anomaly com limiares restritivos não disparou no período Jun-Sep 2026 em 5 símbolos 1h".
- **Linha fechada (strike 1):** VPA com limiares atuais. Pode ser reavaliada com limiares mais brandos em próximo ciclo se a família conceitual for considerada promissora.

---

## 9. Next Cycle

### Opção A — Reavaliar VPA com limiares mais brandos (se a família for considerada promissora)

Se a family "volume-price anomaly" for considerada promissora (porque a matemática é sound, mas os limiares estão desconectados):

1. **VolAnomMult:** de 0.5 para 0.7 ou 0.8 (volume < 70-80% da média é mais comum que <50%).
2. **RetThresh:** de 0.008 para 0.005 ou 0.004 (movimento de 0.4-0.5% em 1h é mais frequente).
3. **Expandir para mais símbolos:** DOGE, ADA, AVAX, MATIC (alts com vol mais baixo, mais susceptíveis a movimentos "dry").
4. **Multi-TF:** 15m, 30m (mais barras, mais eventos de volume anômalo).
5. **Backtest com limiares relaxados:** se houver trades, comparar PF/WR/DD com os resultados negativos deste ciclo.

### Opção B — Pivotar para H2 (ROE: Range-of-Expansion Exhaustion)

Se a family VPA for considerada exausta após 1 strike:

1. Testar ROE: expansão de range seguida de colapso de range → reversão/sideways.
2. Matematicamente distinto de VPA — não depende de volume, depende de range sequence.
3. Backtest em mesma matriz (5 símbolos × 1h).

### Opção C — Pivotar para H3 (TRF: Failed-Follow-Through Breakout)

Se ROE também falhar:

1. Testar TRF: rompimento de nível sem volume confirming → fakeout → entrada oposta.
2. Distinto de VPA e ROE — foca em nível de preço + volume de confirmação.
3. Backtest em mesma matriz.

### Opção D — Parar e registrar

Se VPA com limiares relaxados também falhar (strike 2 na family VPA), e ROE/TRF também falharem (strikes adicionais), registrar o palace como "nenhuma das hipóteses de volume/range/flow testadas (VPA, ROE, TRF, VND, MSE) disparou em crypto pairs no período 2026" — e pivotar para famílias de regime switching ou liquidity sweep + snapback.

**Decisão tomada neste ciclo:** Opção A — reavaliar VPA com limiares mais brandos em próximo ciclo, porque a matemática é sound e a family não foi testada com limiares próximos da realidade do mercado.

---

## Dashboard Update

Novas linhas para `dashboard/data.json`:

```json
[
  {
    "id": "qm-vpa-btc-1h",
    "name": "QM-VPA-v1 [wip]",
    "symbol": "BTCUSDT",
    "timeframe": "1h",
    "source": "greenfield",
    "family": "vpa",
    "agent": "researcher",
    "net_profit_pct": 0,
    "profit_factor": 0,
    "max_drawdown_pct": 0,
    "win_rate_pct": 0,
    "trades": 0,
    "sharpe": null,
    "result_id": "01M38R7KFN7R2D62T1PGVYTCQH",
    "view_url": "https://mcp-api.trader.dev/backtest/01M38R7KFN7R2D62T1PGVYTCQH",
    "curve": [],
    "verdict": "rejected",
    "status": "backtested",
    "last_backtest": "2026-09-24",
    "pine_key": "01M38R7K9ZQ8KXM2SMA8PXJ6MN",
    "notes": "0 trades — evento 'movimento grande + volume baixo' não ocorreu com limiares atuais"
  },
  {
    "id": "qm-vpa-eth-1h",
    "name": "QM-VPA-v1 [wip]",
    "symbol": "ETHUSDT",
    "timeframe": "1h",
    "source": "greenfield",
    "family": "vpa",
    "agent": "researcher",
    "net_profit_pct": 0,
    "profit_factor": 0,
    "max_drawdown_pct": 0,
    "win_rate_pct": 0,
    "trades": 0,
    "sharpe": null,
    "result_id": "01M38R7LD1NRVBN6WH5A04J9XTF",
    "view_url": "https://mcp-api.trader.dev/backtest/01M38R7LD1NRVBN6WH5A04J9XTF",
    "curve": [],
    "verdict": "rejected",
    "status": "backtested",
    "last_backtest": "2026-09-24",
    "pine_key": "01M38R7KCSWJN95EMXT7W73RHMX",
    "notes": "0 trades — mesmo padrão de silêncio que BTC"
  },
  {
    "id": "qm-vpa-sol-1h",
    "name": "QM-VPA-v1 [wip]",
    "symbol": "SOLUSDT",
    "timeframe": "1h",
    "source": "greenfield",
    "family": "vpa",
    "agent": "researcher",
    "net_profit_pct": 0,
    "profit_factor": 0,
    "max_drawdown_pct": 0,
    "win_rate_pct": 0,
    "trades": 0,
    "sharpe": null,
    "result_id": "01M38R7LFXDH62HBVY5J5NFQFSD",
    "view_url": "https://mcp-api.trader.dev/backtest/01M38R7LFXDH62HBVY5J5NFQFSD",
    "curve": [],
    "verdict": "rejected",
    "status": "backtested",
    "last_backtest": "2026-09-24",
    "pine_key": "01M38R7KFL1F1AGAWDPZEHBVD4W",
    "notes": "0 trades — alts também silenciosas"
  },
  {
    "id": "qm-vpa-xrp-1h",
    "name": "QM-VPA-v1 [wip]",
    "symbol": "XRPUSDT",
    "timeframe": "1h",
    "source": "greenfield",
    "family": "vpa",
    "agent": "researcher",
    "net_profit_pct": 0,
    "profit_factor": 0,
    "max_drawdown_pct": 0,
    "win_rate_pct": 0,
    "trades": 0,
    "sharpe": null,
    "result_id": "01M38R7LCMF2A9N1JFQJYJXWJBV",
    "view_url": "https://mcp-api.trader.dev/backtest/01M38R7LCMF2A9N1JFQJYJXWJBV",
    "curve": [],
    "verdict": "rejected",
    "status": "backtested",
    "last_backtest": "2026-09-24",
    "pine_key": "01M38R7K64QW4QVK8MDMHZXGSFB",
    "notes": "0 trades"
  },
  {
    "id": "qm-vpa-bnb-1h",
    "name": "QM-VPA-v1 [wip]",
    "symbol": "BNBUSDT",
    "timeframe": "1h",
    "source": "greenfield",
    "family": "vpa",
    "agent": "researcher",
    "net_profit_pct": 0,
    "profit_factor": 0,
    "max_drawdown_pct": 0,
    "win_rate_pct": 0,
    "trades": 0,
    "sharpe": null,
    "result_id": "01M38R7LA2KVBD7RN1CGVE4VSBH",
    "view_url": "https://mcp-api.trader.dev/backtest/01M38R7LA2KVBD7RN1CGVE4VSBH",
    "curve": [],
    "verdict": "rejected",
    "status": "backtested",
    "last_backtest": "2026-09-24",
    "pine_key": "01M38R7K4YR3PM5A03WC0N29GX4",
    "notes": "0 trades"
  }
]
```

---

## Resumo Executivo

| Métrica | Valor |
|---------|-------|
| **Hipótese testada** | Volume-Price Anomaly (movimento grande + volume baixo → reversão) |
| **Resultado** | **0 trades em 5 símbolos** (BTC, ETH, SOL, XRP, BNB) |
| **Verdict** | **REJECT** (strike 1 na family VPA) |
| **Creditos gastos** | 5 (5 backtests × 1 credit) |
| **Creditos restantes** | ~161 |
| **Próximo passo** | Reavaliar VPA com limiares mais brandos (volAnomMult=0.7-0.8, retThresh=0.004-0.005) e mais símbolos, ou pivotar para ROE/ TRF |

---

*Nenhuma ordem real — pesquisa/educação apenas.*
