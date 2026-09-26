# Quant Mathematician Cycle Report

**Date:** 2026-09-24 15:32 UTC  
**Agent:** researcher  
**Hypothesis code:** QM-VRSR-v1 (Volatility-Regime Switch Reversion)  
**MCP strategy ID:** 01M3ABT7XEY2KNP07DWRVAZMVM  
**Symbol:** BTCUSDT | BYBIT:BTCUSDT.P  
**Timeframe (submission):** 1h  
**Status:** Backtest blocked — free credits exhausted (no Pro/subscription, no exchange-verification credit boost claimed). Cycle stops at evidence-collection stage.

---

## 1. Hypotheses Generated (greenfield, no DB search)

### H1 — QM-VRSR-v1: Volatility-Regime Switch Reversion | **SELECTED**
- **Inefficiency:** Em crypto, expansão de volatilidade (ATR curto/Longo > threshold) frequentemente precede ou co-ocorre com regimes de maior imprevisibilidade de curto prazo. Nesse ambiente, uma vela com **baixa eficiência de range** (`|close−open|/(high−low)` pequeno) que *supostamente* continua em uma direção (ret > 0 para long, ret < 0 para short) mas o preço está distante do equilíbrio de médio prazo (linreg 50) é, historicamente, uma **falha de continuação**: o sinal de sentido igual ao que a vela "dizia" é enganoso; a correção tende a voltar ao equilíbrio.
- **Por que em crypto:** Liquitidy fragmentada, gap de funding, micro-estruturas de HH/LH mais ruidosas — expansão de vol é mais sugestiva de regime instável do que em mercados centralizados.
- **Cross-symbol:** Conceito de "vol regime × falha de continuação em distância do equilíbrio" é agnóstico a símbolo — testável em top-100 bybit.
- **Regime que quebra:** tendência forte e persistente (preço rasteira acima do linreg sem expansão — H1 não dispara) ou chop de vol baixa (não ativa filtro de vol).
- **Expressão Pine:** `volRatio > thresh` AND `close < linreg` AND `ret > 0` AND `range_eff < thresh` → long; mirror para short. SL em ATR_short × mult; time exit.

### H2 — Liquidity Sweep + Pivot Snapback
- **Ineficiência:** Toque abaixo de um pivot recente (pivotlow) seguido de fechamento acima e baixa vol → reversão.
- **Por que em crypto:** sweeps de liquidez estrutural são frequentes; snapback post-sweep é um padrão de microestrutura.
- **Problema neste ciclo:** risco de repaint sutil em definição de pivot; classificação preferiu H1.

### H3 — Pure Range-Efficiency Fade (sem vol filter)
- **Simplificação extrema:** entrar em baixa eficiência de range quando price está longe do close anterior.
- **Problema:** sem filtro de regime, confina-se ao ruído de chop de baixa vol. Rejeitada como base deste ciclo.

### (H4–H5 não gerados este ciclo; mantidos em reserva: distance-from-VWAP (muito explorado); failed-continuation sem vol (fragil).)

---

## 2. Hypothesis Selected (math basis)

**QM-VRSR-v1** — integra três séries:

1. **Volatility expansion ratio**: `R_t = ATR_short(14) / ATR_long(50)`. Quando `R_t > 1.30`, o mercado está em expansão de vol recente vs. baseline — proxy de regime instável/turbulento.
2. **Distance from equilibrium**: `D_t = close − linreg(close, 50, 0)`. Posição relativa ao equilíbrio de médio prazo.
3. **Range efficiency (RE)**: `RE_t = |close−open| / (high−low)`. Vela "low RE" tem corpo pequeno relativo ao range total → sinal de direção fraco; em regime expandido com distância do equilíbrio, a continuação sugerida pela vela é estatisticamente francamente duvidosa.

**Regra de entrada long (todas as condições):**
- `R_t > 1.30` (vol expandida)
- `close < linreg_50` (abaixo do equilíbrio)
- `ret_t = (close−close[1])/close[1] > 0` (vela "sugestiva de alta")
- `RE_t < 0.35` (baixa eficiência)
- Sem posição long aberta (`position_size ≤ 0`)

**Regra de entrada short:** espelho (`R_t > 1.30`, `close > linreg`, `ret < 0`, `RE < 0.35`, sem posição short).

**Por que é matematicamente plausível:** a falha de continuação ("failed continuation") em mercados voláteis com preço distante do equilíbrio é um padrão de mean-reversion condicional — não um indicador de tendência, não uma cruz de MA. O filtro de vol evita chirping no chop.

---

## 3. Trading Rules

### Entries
- **Long:** `volExpanded AND belowEq AND ret>0 AND lowRE AND pos<=0` → `strategy.entry("L", strategy.long)`
- **Short:** `volExpanded AND aboveEq AND ret<0 AND lowRE AND pos>=0` → `strategy.entry("S", strategy.short)`

### Exits
- **SL:** `abs(SL) = ATR_short(14) × slMult` (mult input 1.50). Stop price absoluto recalculado ogni bar com `strategy.exit(stop=...)`, re-emitido ogni bar (engine-safe).
- **Time exit:** `maxBars = 40` (1h → ~40h ≈ 1.7 dia). `strategy.close(id)` se `bar_index − entryBar >= maxBars`.
- **Sem trailing custom var → usado `strategy.exit(stop=...)` com ratchet** (seguro para engine tv_jul26).
- **Sem TP fixo** neste v1 (design escolheu SL + time como delimitadores de risco; TP pode ser adicionado na iteração se houver trades).

### Invalidação
- Se vol cair abaixo threshold antes do fechamento da posição, a lógica não mexe (não há saída por vol contraction — por enquanto). Isso é uma fraqueza documentada.

### Filtros de regime/vol
- Vol expansion threshold: 1.30
- Range efficiency threshold: 0.35
- SL ATR mult: 1.50

### Max duration
- 40 barras (time exit).

### Risk per trade
- 100% equity (per MCP parity profile; não é recomendação de risco real — é o perfil de engine).

### Cooldown
- Não há cooldown nesta versão; a lógica `pos<=0` / `pos>=0` impede sobreposição natural do mesmo lado. Cooldown explícito pode ser adicionado na iteração.

---

## 4. Pine Script (v6, engine tv_jul26; sem repaint, sem lookahead)

```pine
//@version=6
strategy("QM-VRSR-v1 | Volatility-Regime Switch Reversion",
  overlay=true,
  pyramiding=1,
  process_orders_on_close=true,
  commission_type=strategy.commission.percent,
  commission_value=0.05,
  default_qty_type=strategy.percent_of_equity,
  default_qty_value=100,
  margin_long=100,
  margin_short=100,
  initial_capital=10000)

// — Inputs —
atrShortLen  = input.int(14, "ATR Short Len", minval=2)
atrLongLen   = input.int(50, "ATR Long Len", minval=5)
volExpThresh = input.float(1.30, "Vol Expansion Threshold", minval=1.05, step=0.05)
eqLen        = input.int(50, "Equilibrium Linreg Len", minval=10)
reThresh     = input.float(0.35, "Max Range Efficiency", minval=0.05, step=0.05)
slMult       = input.float(1.50, "SL ATR Mult", minval=0.5, step=0.1)
maxBars      = input.int(40, "Max Bars in Trade", minval=1)

// — Indicators —
atrShort = ta.atr(atrShortLen)
atrLong  = ta.atr(atrLongLen)
volRatio = atrShort / atrLong
volExpanded = volRatio > volExpThresh

eqLine  = ta.linreg(close, eqLen, 0)
belowEq = close < eqLine
aboveEq = close > eqLine

ret  = (close - close[1]) / close[1]
re   = math.abs(close - open) / math.max(high - low, 0.0000001)
lowRE = re < reThresh

// — Long setup: vol expand + below eq + positive ret + low range efficiency —
longCond = volExpanded and belowEq and ret > 0 and lowRE and strategy.position_size <= 0

// — Short setup: mirror —
shortCond = volExpanded and aboveEq and ret < 0 and lowRE and strategy.position_size >= 0

// — Entry bars for time exit —
var int longEntryBar  = na
var int shortEntryBar = na

if longCond
    strategy.entry("L", strategy.long)
    longEntryBar := bar_index

if shortCond
    strategy.entry("S", strategy.short)
    shortEntryBar := bar_index

// — Exits —
if strategy.position_size > 0
    longSL = strategy.position_avg_price - atrShort * slMult
    strategy.exit("LX", from_entry="L", stop=longSL)
    if bar_index - longEntryBar >= maxBars
        strategy.close("L")

if strategy.position_size < 0
    shortSL = strategy.position_avg_price + atrShort * slMult
    strategy.exit("SX", from_entry="S", stop=shortSL)
    if bar_index - shortEntryBar >= maxBars
        strategy.close("S")

// — Plots —
plot(eqLine, "Equilibrium (linreg)", color=color.blue, linewidth=2)
plot(longCond ? 1 : 0, "Long Signal", style=plot.style_columns, color=color.green, transp=80)
plot(shortCond ? 1 : 0, "Short Signal", style=plot.style_columns, color=color.red, transp=80)
```

**Comentário de redação:** PLUG PEDIDO de trailing custom var → seguido o pattern allowed com `strategy.exit(stop=...)` reemitido ogni bar. Nenhuma função de usuário, array, request.security, cancel, ou martingale.

---

## 5. Backtest Matrix

| Symbol | Timeframe | Submission | Note |
|--------|-----------|------------|------|
| BTCUSDT | 1h | 2025-01-01 → 2026-01-01 | Planeado; **não executado** — créditos esgotados |

**Plano (se créditos disponíveis):** 5–10 pares aléatorios do top-100 Bybit × 15m/30m/1h/2h/4h, long+short, histórico suficiente.

**O que foi feito:** estratégia criada no MCP em modo dev, Pine validado contra regras de codegen (v6, process_orders_on_close, pyramiding=1, commission 0.05%, % equity 100, margin 100/100, sem forbidden calls). Backtest real não pôde rodar.

---

## 6. Results

**Não há resultados de backtest.** O job `run_backtest` retornou:

```
ERROR — You have no credits remaining. Free credits reset on Invalid Date.
Upgrade to Pro, or verify exchange account at /unlock-edge to double free credits weekly.
```

Sem `resultId`, sem `jobId` de backtest executado, sem trades, sem KPIs. Relatório não pode afirmar PF, DD, win rate, net profit.

**Cycle output portanto é um documento de hipótese + código validado + diagnóstico de infraestrutura.** Veredicto reflete isso.

---

## 7. Diagnosis (pré-backtest, baseado no design)

### Pontos fortes do design
- Não é indicador de tendência nem retail soup.
- Filtro de vol expansion reduz chirping em chop de baixa vol.
- SL em ATR expandido (vol regime) é coerente: stops que se dilatation com a volatilidade.
- Time exit delimita risco de trade estagnado.
- Regra clean e testável; poucos parâmetros (7 inputs).
- Potencialmente cross-symbol e cross-TF.

### Riscos / fragilidades esperadas
- **Trade count:** filtros combinados (vol expand + distância do equilíbrio + ret direcional + low RE) podem ser raros em alguns símbolos/TF → amostra pequena.
- **Só longs ou só shorts?** A lógica é simétrica, mas em regimes de tendência, uma direção pode dominar. Precisa de diagnóstico de asymmetry.
- **SL muito apertado/loose?** slMult 1.50 × ATR_short em vol expandida pode ser loose (preço pode não voltar antes do time exit). Ou pode ser tight se ATR_short já decai.
- **Falta TP:** sem TP, o trade espera SL ou time exit. Em um mercado que se move na direção do trade, a posição pode ser lucrativa e então dar revert — isso é uma escolha de design, não necessariamente erro, mas reduz a captura de gain.
- **Vol contraction não sai:** se vol cair durante o trade, não há saída → risco de trade longo com vol decay (pode ser OK, pode ser ruim).
- **Um único símbolo de calibração (BTC):** os inputs foram escolhidos de forma genérica, mas sem backtest multi-símbolo não há evidência de robustez.

### O que o backtest teria revelado (se tivesse rodado)
- Distribuição de trades por símbolo/TF.
- PF, DD, win rate, trades por lado.
- Se o edge é real ou fruto de um ou dois símbolos.
- Se STOPs são hit frequentemente (vol expandida + SL apertado) ou se o time exit domina.

---

## 8. Verdict

```
[VERDICT] WATCHLIST — crédito insuficiente para validação
```

Motivo: estratégia greenfield QM-VRSR-v1 foi escrita, validada em MCP (código no formato engine tv_jul26, sem forbidden calls, com SL e time exit), e submetida em modo dev. Não foi possível executar backtest porque a conta MCP está em tier free com créditos esgotados neste janela. Sem backtest, não há evidência de edge — não se pode classificiar como Incubate ou Candidate.

**Condição para avançar:** créditos disponíveis (Pro, ou exchange-verification para crédito gratuito duplo semanal, ou reset de crédito gratuito), e então:
1. Backtest no BTC 1h janela 2025-01-01 → 2026-01-01.
2. Se PF ≥ 1.3 e DD controlado e ≥ 50 trades em ≥ 2 TFs → ampliar para top-100 Bybit × 15m/30m/1h/2h/4h.
3. Diagnóstico de asymmetry long/short e de símbolo.

Se após 3 ciclos na linha VRSR não houver edge consistente → pivot para outra hipótese (ex: liquidity sweep + snapback, com cuidado de repaint; ou range-efficiency com filtro de ADX como proxy de regime).

---

## 9. Next Cycle

Se créditos disponíveis no futuro:

1. **Executar o backtest** QM-VRSR-v1 no BTC 1h (2025→2026).
2. **Se vida:** multi-symbol/TF matrix. Comparar long vs short PF; diagnosticar se edge é assimétrico.
3. **Iteração possível (um conceito por ciclo):**
   - Adicionar TP fraco (ex.: 50% em 1.0× ATR_short) para capturar gains sem trailing.
   - Filtro de ADX para evitar chop de baixa vol (se diagnosticar chirping).
   - Cooldown explícito de N barras entre entradas.
   - Vol contraction exit (se diagnosticar que esperar vol cair é ruim).

Se **sem créditos** no próximo ciclo: o loop manda reportar e parar. Não há mais ação possível neste ciclo sem infraestrutura.

---

## Anexo: Satélites do ciclo

- **Arquivo Pine submetido ao MCP:** `01M3ABT7XEY2KNP07DWRVAZMVM` (dev).
- **Scripts locais:** `loop\01-quant-mathematician.md` (leitura), `scripts/panel_upsert.py` (disponível; não executado porque sem backtest para registrar).
- **Relatórios prévios da linha:** diversos no `data/reports/` (p.ex. `qm-lsn-v1`, `qm-vrad-v1`, `qm-fcs-v1`, `rec-greenfield`).

---

*Compromisso de pesquisa:* edge real ou refutação honesta. Sem backtest há apenas hipótese — portanto: WATCHLIST, não incubação. Nunca ordens reais.
