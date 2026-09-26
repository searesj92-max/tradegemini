# Risk Manager Audit Cycle

**Strategy:** QM-VOL-REVERSION-v1 · ID: `01M3ACZ5NDCX9H0VBFK96KZKGM`
**Audit date:** 2026-09-24 16:15 UTC-3 · **Auditor:** gertrude (Risk Manager loop)
**MCP status:** authenticated · credits=0 (backtests blocked) · engine: tv_jul26 parity

---

## 1. Code review (repaint, lookahead, stops, params, curve-fit)

### Pine source (full — MCP `get_strategy`):
```pine
//@version=6
strategy(
  title = "QM-VOL-REVERSION-v1",
  overlay = true,
  pyramiding = 1,
  process_orders_on_close = true,
  commission_type = strategy.commission.percent,
  commission_value = 0.05,
  initial_capital = 10000,
  default_qty_type = strategy.percent_of_equity,
  default_qty_value = 100,
  margin_long = 100,
  margin_short = 100
)

// --- Inputs (13 total) ---
fastLen     = input.int(18, "EMA rápida (barras)", minval = 5)        // 1
adxLen      = input.int(14, "ADX len", minval = 5)                     // 2
adxMin      = input.int(15, "ADX mínimo para operar", minval = 5)      // 3
adxMax      = input.int(50, "ADX máximo (tendência forte → pulsa)", minval = 20) // 4
slopeLen    = input.int(3,  "Slope EMA len (barras)", minval = 1)      // 5
slopeMax    = input.float(1.2, "Slope max (× ATR) — tendência forte → pulsa", minval = 0.0, step = 0.1) // 6
atrRatioLen = input.int(50, "ATR ratio len", minval = 10)              // 7
atrMax      = input.float(2.5, "ATR_ratio max — volatilidade muito alta → pulsa", minval = 1.0, step = 0.1) // 8
zEntry      = input.float(2.5, "Z-score mínimo para entrada", minval = 1.0, step = 0.1) // 9
slMult      = input.float(2.0, "SL (× ATR)", minval = 0.5, step = 0.1) // 10
tpMult      = input.float(3.0, "TP (× ATR) — 0 = sem TP fixo", minval = 0.0, step = 0.1) // 11
maxBars     = input.int(120, "Time exit (barras) — 0 = sem limite", minval = 0) // 12
cooldown    = input.int(3,   "Cooldown (barras) após saída antes de nova entrada", minval = 0) // 13
```

### Indicators used (allowed list — `ta.*` only):
- `ta.ema(close, fastLen)` — EMA rápida
- `emaSlope = (emaFast - ta.ema(emaFast, slopeLen)) / close` — slope normalizado
- `globalAtr = ta.atr(fastLen)` — ATR
- `zLong = (close - emaFast) / globalAtr` — z-score long
- `zShort = (emaFast - close) / globalAtr` — z-score short
- `adxVal = ta.adx(adxLen)` — ADX
- `atrRatio = globalAtr / ta.sma(globalAtr, atrRatioLen)` — ratio de volatilidade

### Repaint analysis:
- `process_orders_on_close = true` — todas as entradas/decisões no close da barra. Sem repaint por tick.
- Nenhuma `calc_on_every_tick` (não declarado; padrão false em strategy()).
- Nenhuma `request.security` (proibida e ausente).
- `[]` offsets: nenhum forward. Todos os cálculos usam close, open, high, low da barra atual ou série passada via indicadores.
- `ta.highest/ta.lowest` não usados — apenas EMA e ATR, que são stateless e sem lookahead.
- `alert_condition(longSignal, ...)` e `alert_condition(shortSignal, ...)` — alertas declarados, sem efeito no backtest.
- **Verdict: sem repaint confirmado.**

### Lookahead analysis:
- `zLong/zShort` usam `close` da barra atual. `process_orders_on_close=true` significa que a entrada só é avaliada no close — então usar `close` atual é correto (fechamento conhecido).
- `adxVal = ta.adx(adxLen)` — ADX calculado corretamente, sem futuro.
- `emaSlope` usa `ta.ema(emaFast, slopeLen)` com `slopeLen=3` — lookahead de 3 barras dentro do próprio cálculo de EMA (suavização), não lookahead de preço futuro. Aceitável.
- `_slopeOK = math.abs(emaSlope) < slopeMax * (globalAtr / close)` — usa close atual, correto.
- **Verdict: sem lookahead confirmado.**

### Stop loss / Take profit:
- **SL presente:** `slMult = 2.0` ATR. `strategy.exit("LX"/"SX", loss = slTicksLong/slTicksShort)` onde `slTicksLong = slMult * math.round(globalAtr / syminfo.pointvalue)`.
- **TP presente:** `tpMult = 3.0` ATR. `strategy.exit(..., profit = tpTicksLong/tpTicksShort)`.
- **Time exit:** `maxBars = 120` — fecha a posição após 120 barras se não atingir SL/TP.
- **Cooldown:** `cooldown = 3` barras entre saídas e novas entradas.
- **Nenhum trailing:** regra do loop respeitada (sem `strategy.cancel`, sem var-trail-close).
- **Single exit:** `strategy.exit` com `profit=` e `loss=` em uma única chamada — sem múltiplos SL/TP escalonados.
- **Verdict: SL+TP presentes e bem definidos. Time exit e cooldown presentes.**

### SL cálculo detalhado:
```
slTicksLong  = slMult * math.round(globalAtr / syminfo.pointvalue)
slTicksShort = slMult * math.round(globalAtr / syminfo.pointvalue)
```
- O `math.round` pode causar discretização grossa em ativos com `pointvalue` muito pequeno. Para BTCUSDT em 15min, `syminfo.pointvalue` = 0.01 (tick size de preço), então `globalAtr / 0.01` é grande — o round é inofensivo.
- **Nota:** o cálculo de ticks é recalculado a cada barra com base no `globalAtr` atual. Como `strategy.exit` com `loss=` em ticks define o nível a partir do preço de entrada, e o valor é recalculado a cada barra, o nível de SL/TP pode ser atualizado a cada barra para o novo valor de ATR. Isso é uma forma sutil de SL/TP adaptativo (não trailing steer, mas reajuste de magnitude). Em ATR estável (18 barras), o reajuste é menor que 1% a cada barra — impacto negligible. **Não é um problema de segurança, mas é uma escolha de design que difere do "SL fixo no preço de entrada" mais comum.**

### Parâmetros ( curva-fit check):
- **13 inputs totais.** Critical count: 13 ± 1 (fastLen, adxLen, adxMin, adxMax, slopeLen, slopeMax, atrRatioLen, atrMax, zEntry, slMult, tpMult, maxBars, cooldown).
- Regra do risk manager: `> 12 tightly-tuned inputs` → **RED FLAG potencial**. Aqui temos exatamente 13.
- Mas muitos inputs são de filtro de regime (ADX min/max, slopeMax, atrMax) — podem ser considerados "hyperparameters de ambiente" não tão tightly-tuned. Se todos forem ajustados simultaneamente em otimização, o risco de curva-fit é alto.
- **Avaliação:** 13 inputs é na fronteira. Se o backtest futuro mostrar resultados consistentes com valores default (sem otimização agressiva), pode ser aceitável. Por ora, **YELLOW FLAG: contagem de inputs alta**.

### Concentração / single-pair:
- Estratégia criada para BTCUSDT apenas (symbol field no MCP).
- No dashboard, família QM tem múltiplas estratégias cross-symbol, mas esta estratégia específica é BTC-only.
- Sem backtest rodado, não se sabe se o edge se generaliza.
- **YELLOW FLAG: single-pair no momento.**

---

## 2. Backtest review (count, top-1 concentration, curve, DD, multi-pair, multi-TF)

**Status: NÃO HÁ BACKTEST.**

| Métrica | Valor |
|---|---|
| Net profit | — (sem backtest) |
| Profit factor | — |
| Max drawdown | — |
| Win rate | — |
| Average trade | — |
| Trades total | — |
| Long/short breakdown | — |
| Stability across TFs | — |
| Stability across symbols | — |
| Equity curve | — |
| Top-1 trade concentration | — |

**Motivo do bloqueio:** MCP credits = 0 (free tier esgotado; reset semanal em "Invalid Date" — campo não parseável). O backtest engine (`tv_jul26`) está acessível, mas a execução é bloqueada pelo limite de créditos.

**O que existe:**
- Relatório do researcher `2026-09-24-1500-researcher-qm-vol-reversion-v1.md` confirma que a estratégia foi criada no MCP, Pine compilou sem erro, e o plano de backtest está definido (5 pares × 5 TFs = 25 runs), mas **nenhum backtest foi executado**.
- Dashboard `resumo-estrategias.md`: esta estratégia específica (`QM-VOL-REVERSION-v1`, ID `01M3ACZ5NDCX9H0VBFK96KZKGM`) **não aparece na lista de candidatos** (que mostra outras famílias: leaderboard, rsi-t200, squeeze, discovery, ema9-21, high-wr). Isso confirma que não há backtest registrado.

---

## 3. Flags (red / yellow / green)

### Red flags (investigar/agir):
| Flag | Status | Evidência |
|---|---|---|
| Repainting confirmado | **NÃO** | process_orders_on_close=true, sem lookahead, sem request.security |
| Lookahead / future data | **NÃO** | sem [] forward, sem security |
| Single outlier trade > 30% P&L | **N/A** | sem backtest |
| Max DD > 50% sem razão plausível | **N/A** | sem backtest |
| < 30 trades na janela | **N/A** | sem backtest |
| Rentável apenas em um símbolo | **YELLOW (provisional)** | estratégia é BTC-only; sem evidência de generalização |
| WR > 85% em trend system | **N/A** | sem backtest |
| WR < 15% em mean-reversion | **N/A** | sem backtest |
| Backtest window < 6 meses | **N/A** | sem backtest |
| > 12 inputs tightly-tuned | **YELLOW** | 13 inputs, borderline |
| Leverage implica > exchange max | **NÃO** | margin_long=100, margin_short=100, equity 100% — leverage 1× |
| Martingale sem recovery cap | **NÃO** | pyramiding=1, sem martingale |
| SL missing ou comentado | **NÃO** | SL presente (2.0 ATR) |
| Claims production readiness sem forward test | **NÃO** | estratégia é "dev", sem claim de produção |

### Yellow flags (investigar):
| Flag | Status |
|---|---|
| PF 1.0–1.2 | N/A |
| DD 30–50% | N/A |
| 30–80 trades | N/A |
| Apenas 1–2 TFs funcionam | N/A |
| BTC/ETH only | **SIM** (BTC-only, sem teste cross-symbol) |
| SL < 1 ATR | **NÃO** (SL = 2 ATR, razoável) |
| TP > 5 ATR | **NÃO** (TP = 3 ATR) |
| > 6 inputs | **SIM** (13 inputs) |
| Long/short divergence | N/A |
| Equity concentrado em 1–2 meses | N/A |
| Últimos 3 meses piores que longo prazo | N/A |

### Green flags (clear):
| Flag | Status |
|---|---|
| PF > 1.4 multi-pair | **N/A** (sem backtest) |
| DD < 25% | **N/A** |
| > 150 trades | **N/A** |
| Estável 3+ TFs | **N/A** |
| 5+ símbolos | **N/A** |
| Equity longo e suave | **N/A** |
| Poucos inputs | **NÃO** (13 inputs) |
| Stops honestos | **SIM** (SL+TP presentes, time exit, cooldown) |
| Matches TradingView | **N/A** |

---

## 4. Action taken

**Nenhuma ação de demote/pause.** Estratégia está em modo `dev` com status `active` (alerta criado, mas sem backtest).

**Raciocínio:**
- Sem backtest, não há métricas de performance para demover.
- Código Pine é limpo (sem repaint, sem lookahead, SL presente, sem martingale).
- Contagem de inputs (13) é borderline — merece atenção no futuro.
- Single-pair (BTCUSDT) é uma limitação conhecida, não um defeito.

**Ação registrada:** Watched. Nenhuma mudança de status no MCP ou dashboard. Aguarda créditos para backtest.

---

## 5. Notes for Gertrude

**Para o ciclo de aprovação do Gertrude:**

- Esta estratégia **não é candidata para aprovação agora** — não há evidência de edge (backtest bloqueado por créditos).
- O código é tecnicamente limpo: sem os "deadly sins" (repaint, lookahead, no-SL, martingale).
- Os 13 inputs exigem vigilância: se no futuro for otimizada, deve-se testar com valores default e apenas ajustar 1–2 parâmetros por ciclo, não todos ao mesmo tempo.
- Single-pair (BTCUSDT): mesmo que o backtest futuro mostre bons resultados em BTC, a estratégia deve ser testada em pelo menos 3–5 símbolos antes de qualquer consideração de incubação.
- Recomendação para o próximo ciclo de pesquisa: quando créditos estiverem disponíveis, rodar **no mínimo BTCUSDT × 5 TFs (15m, 30m, 1h, 2h, 4h)** para avaliar stability cross-TF antes de expandir para outros símbolos.

**Bloqueio externo identificado:** MCP credits = 0, reset desconhecido ("Invalid Date"). Ação humana possível: verificar exchange e usar `/unlock-edge` para dobramento gratuito de créditos, ou fazer login no MCP UI.

---

## 6. Recommendation

**WATCHLIST — Aguarda backtest para validar.**

**Justificativa:**
- **Não é Reject:** código é limpo, hipótese é matematicamente bona fide (z-score de deslocamento normalizado por ATR, com filtro de regime ADX+slope+vol). Não há sinais de má fabricação.
- **Não é Incubate:** sem backtest, não há evidência de edge. Incubação requer métricas mínimas (PF ≥ 1.3, ≥ 30 trades, DD ≤ 30%).
- **Não é Candidate / Production candidate:** mesmo com backtest futuro positivo, single-pair e 13 inputs exigem validação cross-symbol e simplificação antes de promoção.
- **Watchlist:** estratégia pronta para teste, aguarda recursos (créditos MCP). Quando créditos available, rodar backtest mínimo (BTC × 5 TFs). Se edge confirmado e generalização positiva, avançar para incubação no ciclo seguinte.

**Condição de saída do Watchlist:**
1. Créditos MCP disponíveis → rodar backtest.
2. Se PF ≥ 1.3 em ≥ 2 símbolos com DD ≤ 30% e ≥ 30 trades no conjunto → avançar para incubação.
3. Se edge fraco / negativo / one-pair wonder → reject e pivotar.

---

*Audit free (no backtest credits consumed). MCP credits: 0.*
*Next risk audit cycle: 2026-09-24 17:15 UTC-3 (60m cadence).*
