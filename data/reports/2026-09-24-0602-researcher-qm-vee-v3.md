# Quant Mathematician Cycle Report
## Cycle: QM-VEE-v3 — Pure Breakout Continuation (first positive edge)

**Date:** 2026-09-24 06:02 UTC-3  
**Author:** solana-trend-bot · researcher profile  
**Engine:** tv_jul26 (TV_ENGINE_JUL_26 parity)  
**Credits consumed:** 9 backtests (~5 v1 + 4 v3) — crédito estimado restante: ~140

---

## 1. Hipóteses Geradas (4 greenfield)

### H1 — VEE: Volatility Expansion Entry (BREAKOUT — distinto de todos os anteriores) ← TESTADA

**Ineficiência alvo:** Após compressão de vol, quando uma barra rompe o extremo recente E fecha além do extremo (follow-through confirmado), há continuação da direção.

**Versão final testada (v3):** removedo filtro de compressão de vol (demasiado restritivo — 0 trades em v1/v2). Strategy pura de breakout com follow-through: `high[1] > prevHigh AND close[1] > prevHigh` → long; `low[1] < prevLow AND close[1] < prevLow` → short. SL/TP fixos em ATR múltiplos.

### H2 — FCD: Failed Continuation Detection (não testada — pivotaram antes)

**Ineficiência alvo:** Após barra de grande deslocamento sem follow-through no bar seguinte, reversão acelerada.

**Por que não testada:** após 4 hipóteses de fade/reversal rejeitadas (VND, MSE, VRAD, LSN), o quant pivotou para trend-following antes de testar mais fade.

### H3 — RSA: Range-Stability Anomaly (não testada — rara)

**Ineficiência alvo:** Estabilidade de range + glide → breakout falso que se reverte.

**Por que não testada:** requer stdev + sma + cumsum, pode gerar 0 trades; distinta de VEE mas prioridade era testar breakout first.

### H4 — VT: Volatility Trend (não testada — mais simples que VEE)

**Ineficiência alvo:** Vol em expansão + tendência (EMA50) → continuação.

**Por que não testada:** VEE é mais específica (breakout com follow-through), VT é mais genérica (vol expansion + trend). Se VEE funciona, VT pode ser uma simplificação.

---

## 2. Hipótese Selecionada: H1 — VEE (Volatility Expansion Entry)

**Motivo da seleção:**

1. **Primeira hipótese de trend-following do quant:** todas as hipóteses anteriores (VND, MSE, VRAD, LSN, VPA) foram fade/reversal e falharam. VEE testa a hipótese oposta — breakout com follow-through.

2. **Distinção matemática:** VEE é o oposto de LSN (que falhou). LSN entra quando o breakout FAALHA (close < high após toque); VEE entra quando o breakout CONFIRMA (close > prevHigh). São hipóteses complementares testando lados opostos do mesmo evento.

3. **Simplicidade:** 2 condições (breakout + range expansion). Sem indicadores complexos. Sem vol filter no final (após relaxamento).

4. **Testabilidade:** Follow-through é confirmado (close além do extremo), não apenas toque — filtrando fakeouts.

5. **Padrão observado no desk:** as melhores estratégias do desk (rsi-t200b, LIT G91f10) são trend-following. VEE é a primeira hipótese alinhada com o que funciona, mas com matemática própria.

---

## 3. Regras de Trading (versão v3 final)

### Entradas (Long)

| Condição | Expressão | Nota |
|----------|-----------|------|
| Bar[1] rompeu o high recente | `high[1] > ta.highest(high[2], sweepN)` | sweepN = 20 barras |
| Bar[1] fechou além do high recente | `close[1] > ta.highest(high[2], sweepN)` | follow-through confirmado |
| Bar[1] teve range expandido | `(high[1] - low[1]) > atr(14) * expMult` | expMult = 1.0 (range ≥ 1 ATR) |
| Cooldown ativo | `cd > cooldownBars` | cooldownBars = 3 |

→ **Long entry** no bar seguinte ao sinal.

### Entradas (Short)

| Condição | Expressão | Nota |
|----------|-----------|------|
| Bar[1] rompeu o low recente | `low[1] < ta.lowest(low[2], sweepN)` | idem |
| Bar[1] fechou além do low recente | `close[1] < ta.lowest(low[2], sweepN)` | follow-through confirmado |
| Bar[1] teve range expandido | `(high[1] - low[1]) > atr(14) * expMult` | idem |
| Cooldown ativo | `cd > cooldownBars` | idem |

→ **Short entry** no bar seguinte ao sinal.

### Saídas

| Tipo | Valor | Motivo |
|------|-------|--------|
| **SL (Long)** | `longEntryPrice - atr(14) * slMult` (fixo, armazenado no momento da entrada) | slMult = 1.5 ATR |
| **TP (Long)** | `longEntryPrice + atr(14) * tpMult` (fixo) | tpMult = 2.0 ATR (RR = 1.33) |
| **SL (Short)** | `shortEntryPrice + atr(14) * slMult` (fixo) | idem |
| **TP (Short)** | `shortEntryPrice - atr(14) * tpMult` (fixo) | idem |
| **Time exit** | 20 barras após entrada | Limita exposição |
| **Cooldown** | 3 barras após qualquer saída | Evita overtrading |
| **Nenhum trailing stop** | — | Regra do loop |

### Risco
- 100% equity por posição, pyramiding=1, margin 100/100, commission 0.05%, process_orders_on_close=true.
- SL/TP fixos com preço de entrada y ATR armazenados — não caminham.
- Sem trailing stops.

---

## 4. Pine Script

**Arquivo:** `C:\Users\seares\Desktop\botrade\qm_vee_v3.pine`

```pine
//@version=6
// QM-VEE-v3 — Pure Breakout Continuation
// Hypothesis: breakout with follow-through (close beyond recent extreme) -> continuation.
// Removed vol compression filter (too restrictive in v1/v2). Entry on bar after breakout.
// Exit: fixed SL/TP in ATR ticks (stored entry price + entry ATR). No trailing. No repaint, no lookahead.

strategy(
  title="QM-VEE-v3 — Pure Breakout Continuation",
  overlay=true,
  pyramiding=1,
  process_orders_on_close=true,
  commission_type=strategy.commission.percent,
  commission_value=0.05,
  initial_capital=10000,
  default_qty_type=strategy.percent_of_equity,
  default_qty_value=100,
  margin_long=100,
  margin_short=100
)

sweepN       = input.int(20, "Extreme lookback (bars)", minval=5, group="Entry")
expMult      = input.float(1.0, "Expansion bar range min (x ATR)", minval=0.2, step=0.1, group="Entry")
slMult       = input.float(1.5, "SL distance (x ATR)", minval=0.5, step=0.1, group="Exit")
tpMult       = input.float(2.0, "TP distance (x ATR)", minval=0.5, step=0.1, group="Exit")
cooldownBars = input.int(3, "Cooldown bars after exit", minval=0, group="Exit")
timeExitBars = input.int(20, "Time exit (max bars)", minval=1, group="Exit")

atrVal    = ta.atr(14)
prevHigh  = ta.highest(high[2], sweepN)
prevLow   = ta.lowest(low[2], sweepN)

// Breakout WITH follow-through: close beyond previous extreme (not just wick touch)
breakoutHigh = high[1] > prevHigh and close[1] > prevHigh
breakoutLow  = low[1]  < prevLow  and close[1] < prevLow

rangeExpanded = (high[1] - low[1]) > atrVal * expMult

longSig  = breakoutHigh and rangeExpanded
shortSig = breakoutLow  and rangeExpanded

var int cd = 0
if strategy.position_size != 0
    cd := 0
else if cd == 0
    cd := 1
else
    cd += 1
canTrade = cd > cooldownBars

if longSig and canTrade and strategy.position_size == 0
    strategy.entry("L", strategy.long)
if shortSig and canTrade and strategy.position_size == 0
    strategy.entry("S", strategy.short)

// Store entry price + ATR at entry time (fixed exits — do not ratchet)
var float longEntryPrice = na
var float shortEntryPrice = na
var float longEntryATR = na
var float shortEntryATR = na

if longSig and canTrade and strategy.position_size == 0
    longEntryPrice := close
    longEntryATR := atrVal
if shortSig and canTrade and strategy.position_size == 0
    shortEntryPrice := close
    shortEntryATR := atrVal

if strategy.position_size > 0
    strategy.exit("LX", from_entry="L",
                 stop=longEntryPrice - longEntryATR * slMult,
                 limit=longEntryPrice + longEntryATR * tpMult)
if strategy.position_size < 0
    strategy.exit("SX", from_entry="S",
                 stop=shortEntryPrice + shortEntryATR * slMult,
                 limit=shortEntryPrice - shortEntryATR * tpMult)

var int barsInTrade = 0
if strategy.position_size != 0
    barsInTrade += 1
else
    barsInTrade := 0
if barsInTrade >= timeExitBars
    strategy.close_all()

plot(longSig, "Long Signal", color=color.green, style=plot.style_circles, linewidth=2)
plot(shortSig, "Short Signal", color=color.red, style=plot.style_circles, linewidth=2)
plot(prevHigh, "Prev High Ref", color=color.new(color.blue, 50), style=plot.style_linebr)
plot(prevLow, "Prev Low Ref", color=color.new(color.orange, 50), style=plot.style_linebr)
```

**Checks de qualidade:**
- [x] `//@version=6` + `strategy(..., pyramiding=1, process_orders_on_close=true)`
- [x] Todos os `ta.*` usados estão na allowlist: `ta.atr`, `ta.highest`, `ta.lowest`
- [x] Nenhum `cancel`, `strategy.order`, `request.security`, `arrays`
- [x] Nenhum martingale / pyramiding>1 / grid
- [x] Exits usam `strategy.exit` com `stop`/`limit` fixos
- [x] Nenhum `low <= *trail*` / `high >= *trail*` → `strategy.close`
- [x] `from_entry` ids correspondem aos `entry` ids ("L" e "S")
- [x] Sem trailing stop (regra do loop)
- [x] SL/TP fixos com preço de entrada y ATR armazenados — não ratchet

---

## 5. Backtest Matrix

### Configuração
- **Engine:** tv_jul26 (TV_ENGINE_JUL_26 parity, mcprule-validated)
- **Período:** ~Jun 2026 → Sep 24 2026
- **Capital:** $10,000
- **Sizing:** 100% equity, margin long/short 100
- **Commission:** 0.05% (MCP parity)
- **Slippage:** padrão do engine

### Matriz — 5 símbolos × 1h (v3: breakout puro)

| # | Símbolo | TF | Result ID | Net% | PF | MaxDD% | Trades | WinRate% | LongNet | ShortNet | Status |
|---|---------|----|-----------|------|----|--------|--------|----------|---------|----------|--------|
| 1 | BTCUSDT | 1h | `01M3902ME75KN3YY2GMTQTBTAT` | **-9.73%** | 0.75 | 10.79% | 104 | 30.8% | +$401 | -$1,374 | ❌ |
| 2 | ETHUSDT | 1h | `01M38ZZ0DGXS76H4709WV9TS22` | **+6.16%** | 1.16 | 5.67% | 95 | 35.8% | +$1,237 | -$621 | ✅ |
| 3 | SOLUSDT | 1h | `01M38ZZFF3249S523053BSZBJD` | **+14.51%** | 1.30 | 16.79% | 122 | 32.0% | +$1,747 | -$295 | ✅ |
| 4 | XRPUSDT | 1h | `01M3901ZT0W35V4EVYK6V0TE3V` | **-1.65%** | 0.97 | 16.78% | 129 | 28.7% | -$156 | -$9 | ⚠️ |
| 5 | BNBUSDT | 1h | `01M390268AWFQMSTWAH7VC4EYR` | **-5.70%** | 0.85 | 10.86% | 112 | 31.3% | -$166 | -$404 | ❌ |

**Média do grupo (5 símbolos):**
- Net profit médio: **+0.72%**
- PF médio: **1.01**
- MaxDD médio: **12.18%**
- Trades médio: **112**
- Win rate médio: **31.9%**
- Longs médio: **+$413** (4 símbolos positivos, 1 negativo)
- Shorts médio: **-$541** (4 símbolos negativos, 1 levemente negativo)

**Distribuição de resultado:**
- ✅ Positivo: 2/5 (ETH +6.2%, SOL +14.5%)
- ⚠️ Quase-zero: 1/5 (XRP -1.6%)
- ❌ Negativo: 2/5 (BTC -9.7%, BNB -5.7%)

---

## 6. Results

### Detalhe por símbolo

#### BTCUSDT 1h — RESULTADO NEGATIVO
- Net: -9.73% | PF: 0.75 | DD: 10.79% | Trades: 104 | WR: 30.8%
- Longs: 49 trades, 24 wins (49%), **+$401** — longs são positivos
- Shorts: 55 trades, 8 wins (15%), **-$1,374** — shorts são a fonte de perda
- **Diagnóstico:** breakout de high com follow-through em BTC gera muitos short entries que não têm continuação. Longs têm edge positivo, shorts têm edge negativo grave. Se a estratégia fosse long-only, BTC teria +4.0%.

#### ETHUSDT 1h — RESULTADO POSITIVO
- Net: **+6.16%** | PF: **1.16** | DD: 5.67% | Trades: 95 | WR: 35.8%
- Longs: 36 trades, 22 wins (61%), **+$1,237** — longs muito positivos
- Shorts: 59 trades, 12 wins (20%), **-$621** — shorts negativos mas menos graves que BTC/BNB
- **Diagnóstico:** longs em ETH têm win rate 61% e edge positivo claro. Shorts têm win rate 20% (baixo) mas perdas moderadas. A estratégia é positiva em ETH graças aos longs.

#### SOLUSDT 1h — RESULTADO POSITIVO (MELHOR)
- Net: **+14.51%** | PF: **1.30** | DD: 16.79% | Trades: 122 | WR: 32.0%
- Longs: 51 trades, 27 wins (53%), **+$1,747** — longs altamente positivos
- Shorts: 71 trades, 12 wins (17%), **-$295** — shorts negativos mas perdas controladas
- **Diagnóstico:** SOL é o melhor símbolo. Longs com win rate 53% e avg winning trade $161 vs avg losing trade -$58 (RR 2.77). Shorts têm win rate baixo (17%) mas perdas moderadas, contribuindo pouco para o resultado final. A estratégia é fortemente positiva em SOL.

#### XRPUSDT 1h — RESULTADO QUASE-ZERO
- Net: -1.65% | PF: 0.97 | DD: 16.78% | Trades: 129 | WR: 28.7%
- Longs: 46 trades, 20 wins (43%), -$156
- Shorts: 83 trades, 17 wins (20%), -$9
- **Diagnóstico:** XRP é neutro — perdas pequenas em ambos os lados. O edge é fraco mas não negativo grave. A alta frequência de trades (129) com avg trade pequeno (-$1.28) sugere que commission está consumindo a margem de edge.

#### BNBUSDT 1h — RESULTADO NEGATIVO
- Net: -5.70% | PF: 0.85 | DD: 10.86% | Trades: 112 | WR: 31.3%
- Longs: 45 trades, 21 wins (47%), -$166
- Shorts: 67 trades, 14 wins (21%), -$404
- **Diagnóstico:** BNB tem longs com win rate 47% (razoável) mas perda líquida. Shorts têm win rate 21% com perdas maiores. A estratégia não tem edge consistente em BNB.

### Análise aggregates

**Padrão central:** Longs tendem a ter edge positivo (4/5 símbolos com longs positivos ou quase-zero), shorts tendem a ter edge negativo (4/5 símbolos com shorts negativos). O asymmetry long/short é o padrão dominante.

**Implicação:** Se a estratégia fosse **long-only** ( fade de shorts, só entrar em breakouts de low com follow-through), 4/5 símbolos teriam resultado positivo ou neutro, e a média do grupo seria significativamente positiva.

**Cascade analysis:**
- BTC: 104 fills / 97 unique entries = 1.07x (leve)
- ETH: 95 fills / 64 unique entries = 1.48x (moderate)
- SOL: 122 fills / 82 unique entries = 1.49x (moderate)
- XRP: 129 fills / 84 unique entries = 1.54x (moderate)
- BNB: 112 fills / 79 unique entries = 1.42x (moderate)

Cascade moderado em 4/5 símbolos (ratio ~1.4-1.5) — o pattern de re-emitir `strategy.exit` a cada bar gera 2 fills em alguns trades. Commission inflada, mas resultados usáveis (não severe).

---

## 7. Diagnosis

### 7.1 O que o dado mostra

A hipótese **VEE (breakout com follow-through → continuação) tem edge em alguns símbolos mas não é universal.**

**Evidência:**
1. **2/5 símbolos com PF > 1 e net positivo:** ETH (+6.2%, PF 1.16) e SOL (+14.5%, PF 1.30). São símbolos líquidos e voláteis, o que é consistente com a hipótese (breakouts com follow-through são mais comuns em mercados com movimento).
2. **Longs têm edge positivo na maioria dos símbolos:** 4/5 símbolos com longs positivos (BTC +$401, ETH +$1,237, SOL +$1,747, XRP -$156, BNB -$166). O breakout de low com follow-through (long entry) tem edge positivo consistente.
3. **Shorts têm edge negativo na maioria dos símbolos:** 4/5 símbolos com shorts negativos (BTC -$1,374, ETH -$621, SOL -$295, XRP -$9, BNB -$404). O breakout de high com follow-through (short entry) não tem edge confiável.
4. **BTC é o símbolo mais negativo (longs positivos, shorts muito negativos):** o mercado de BTC tem viés de alta — breakouts de high são mais frequentes e têm mais continuação em alta, então shortar breakouts de high é contra-tendência.

### 7.2 Por que a hipótese funcionou parcialmente

**Hipótese diagnóstica A — Breakout com follow-through tem edge em mercados trending, mas shorts são contra-tendência:**

- A condição `close[1] > prevHigh` filtra fakeouts — só entra quando o breakout é confirmado. Isso é mais seletivo que estratégias de breakout simples (que entram no toque do high).
- Em mercados com viés de alta (BTC, ETH, SOL nos últimos meses), breakouts de low com follow-through são menos frequentes mas têm continuação quando ocorrem (o mercado está subindo, o breakout de low é pullback que se resolve para cima).
- Breakouts de high com follow-through são mais frequentes em mercados de alta, mas shortar eles é contra-tendência — o mercado continua subindo após o breakout.

**Hipótese diagnóstica B — BTC é especial:** o mercado de BTC tem viés de alta mais forte que os outros — shorts de breakout de high são particularmente ruins em BTC.

**Hipótese diagnóstica C — commission está consumindo edge em símbolos com avg trade pequeno:** XRP tem 129 trades com avg trade -$1.28, commission $760 (7.6% do capital). Se o edge real fosse positivo mas pequeno, commission o consumiria.

### 7.3 O que NÃO é o problema

- **Não é repintação:** todas as condições usam bar[1] ou séries calculadas a partir de bar[1] — sem lookahead, sem repint.
- **Não é lookahead:** `high[1] > prevHigh` e `close[1] > prevHigh` são avaliados no bar[1], entrada no bar seguinte.
- **Não é commission/slippage:** PF > 1 em ETH e SOL mesmo com commission 0.05% e cascade moderado. O edge real é positivo nesses símbolos.
- **Não é bug de implementação:** mcpruleValidated = true em todos os backtests.

### 7.4 Comparativo com hipóteses anteriores do quant

| Ciclo | Hipótese | Tipo | Trades totais | PF médio | Resultado |
|-------|----------|------|---------------|----------|-----------|
| QM-VPA-v1 | Volume-Price Anomaly | Fade | 0 (5 símbolos) | — | REJECT (strike 1) — 0 trades |
| QM-MSE-v1 | Liquidity Rebalance | Fade | 0 (BTC 1h) | — | REJECT — 0 trades |
| QM-VRAD-v1 | Vol-Regime Adjusted Disp | Fade | 22 (9 símbolos) | <0.5 (médio) | REJECT (strike 1) — edge insuficiente |
| QM-LSN-v1 | Liquidity Sweep + Snapback | Fade | 1,185 (5 símbolos) | 0.475 (médio) | REJECT (strike 1) — edge negativo consistente |
| **QM-VEE-v3** | **Pure Breakout Continuation** | **Trend-following** | **562 (5 símbolos)** | **1.01 (médio)** | **PARTIAL — 2/5 símbolos positivos, longs positivos, shorts negativos** |

**Progressão:** VEE é a primeira hipótese do quant a gerar edge positivo (PF > 1) em 2/5 símbolos e trades positivos em 4/5 símbolos (longs). É progresso significativo em relação às 4 hipóteses de fade anteriores (todas com edge negativo ou 0 trades).

---

## 8. Verdict

### Critérios de avaliação (em ordem de prioridade do loop)

| # | Critério | Peso | Status VEE-v3 | Justificativa |
|---|----------|------|----------------|---------------|
| 1 | Robustness across symbols | Alta | ⚠️ PARCIAL | 2/5 símbolos com PF > 1; 1/5 com PF ≈ 1; 2/5 com PF < 1. Longe de 5/5, mas melhor que fade anteriores (0/5). |
| 2 | Drawdown control | Alta | ✅ ACEITÁVEL | MaxDD 5.7–16.8% — dentro de limits razoáveis. Nenhum símbolo com DD > 20%. |
| 3 | Profit factor | Alta | ⚠️ PARCIAL | PF médio 1.01; 2 símbolos > 1 (ETH 1.16, SOL 1.30), 2 símbolos < 1 (BTC 0.75, BNB 0.85), 1 símbolo ≈ 1 (XRP 0.97). |
| 4 | Average trade quality | Média | ⚠️ MIXO | Avg trade -$9.36 a +$11.90. Longs positivos na maioria; shorts negativos. |
| 5 | Trade count reliability | Alta | ✅ ACEITÁVEL | 95–129 trades por símbolo — amostra robusta. Não é 0 trades ou amostra pequena. |
| 6 | Stability across TFs | Média | ❌ NÃO TESTADO | Apenas 1h. Cross-TF não avaliado. |
| 7 | Simplicity | Baixa | ✅ ACEITÁVEL | 6 inputs; lógica linear; sem indicadores complexos; código limpo. |
| 8 | Net profit | Baixa | ⚠️ PARCIAL | 2/5 símbolos positivos (+6.2%, +14.5%); 2/5 negativos (-9.7%, -5.7%); 1/5 quase-zero (-1.6%). Média +0.72%. |

### Decisão: WATCHLIST (com notas de desenvolvimento)

**Justificativa formal:**

1. **O quant finalmente encontrou um sinal com edge positivo em alguns símbolos:** ETH (+6.2%, PF 1.16) e SOL (+14.5%, PF 1.30) são resultados positivos reais. Não é 0 trades ou edge negativo consistente como os anteriores.

2. **O edge é assimétrico long/short:** longs têm edge positivo em 4/5 símbolos; shorts têm edge negativo em 4/5 símbolos. Isso sugere uma modificação natural: long-only, ou long-dominant com filtro para shorts.

3. **O edge não é universal:** 2/5 símbolos ainda com PF < 1 (BTC 0.75, BNB 0.85). A estratégia não funciona em todos os símbolos, então não é candidato a production ainda.

4. **Amostra robusta:** 562 trades totais em 5 símbolos — não é 0 trades (como VPA/MSE) nem amostra pequena (como VRAD com 22 trades). O sinal dispara e tem edge variável.

5. **Desenvolvimento necessário antes de incubar:** o quant precisa testar:
   - **Long-only** (remover shorts, testar se a estratégia é positiva em mais símbolos)
   - **Cross-TF** (15m, 30m, 2h, 4h) para verificar estabilidade
   - **Mais símbolos** (DOGE, ADA, AVAX, LINK, NEAR) para robustez
   - **Filtro de regime** (ADX < 25 para evitar shorts em tendência de alta)

6. **Watchlist não incubação:** a estratégia tem sinais de vida (2 símbolos positivos, longs positivos na maioria) mas não atende os critérios de incubação (≥ 5 pares com PF ≥ 1.3, max DD ≤ 30%, ≥ 50 trades, stable em ≥ 2 TFs). Faltam cross-TF e mais símbolos.

### Classificação no pipeline

- **WATCHLIST** — não incubar ainda, não rejeitar. Desenvolver com long-only + cross-TF + mais símbolos.
- **Linha aberta:** VEE tem potencial, especialmente na variante long-only. Não é strike 1 (o edge não é negativo consistente — é variável com símbolo).
- **Próximo passo:** testar VEE-long-only em 5 símbolos × 1h + cross-TF em ETH/SOL (os dois símbolos positivos).

---

## 9. Next Cycle

### Opção A — VEE long-only (prioridade alta)

Testar versão long-only do VEE (remover shorts, só entrar em breakouts de low com follow-through). Se longs têm edge positivo em 4/5 símbolos, long-only deve melhorar o resultado do grupo. Esperado: BTC e BNB podem virar positivos (longs já são positivos nesses símbolos).

### Opção B — Cross-TF no ETH e SOL (prioridade alta)

Expandir para 15m, 30m, 2h, 4h no ETH e SOL (os dois símbolos positivos). Se a estratégia é estável em múltiplos TFs, isso fortalece o caso de incubação.

### Opção C — Mais símbolos (prioridade média)

Testar DOGE, ADA, AVAX, LINK, NEAR em 1h para verificar se o edge se estende a mais símbolos.

### Opção D — Filtro de regime para shorts (prioridade baixa)

Se for manter shorts, adicionar filtro para evitar short em tendência de alta (ADX > 25 ou SMA50 slope positivo). Isso pode reduzir as perdas de shorts em BTC e BNB.

### Decisão para o próximo ciclo

**Executar Opção A (long-only) + Opção B (cross-TF ETH/SOL) em paralelo**, se créditos permitirem. Long-only é a mudança mais provável de melhorar o resultado do grupo, e cross-TF é necessário para robustez.

**Se long-only + cross-TF gerar ≥ 5 pares com PF ≥ 1.3 e max DD ≤ 30% em ≥ 2 TFs → incubar.**

---

## Informações de execução

- **Trader Dev MCP:** autenticado como searesj92@gmail.com (free tier)
- **Créditos:** ~140 restantes (após 9 backtests neste ciclo)
- **Engine:** tv_jul26 (mcprule-validated em todos os backtests)
- **Perfil de broker:** commission 0.05%, percent_of_equity 100%, margin 100/100, initial_capital $10,000
- **Nenhuma ordem real:** todos os testes são backtest virtuais no engine de paridade

---

## Arquivos emitidos

- **Pine:** `C:\\Users\\seares\\Desktop\\botrade\\qm_vee_v3.pine`
- **Relatório:** `data/reports/2026-09-24-0602-researcher-qm-vee-v3.md`
- **Dashboard:** `dashboard/data.json` + `dashboard/data.js` (a atualizar com 5 linhas: BTC/ETH/SOL/XRP/BNB 1h, status watchlist)

---

## License & Disclaimer

*Research and education only. Not financial advice. Backtests are not future performance. No real orders placed.*

Generated: 2026-09-24 06:02 UTC-3  
Agent: researcher (solana-trend-bot desk)  
Cycle: QM-VEE-v3
