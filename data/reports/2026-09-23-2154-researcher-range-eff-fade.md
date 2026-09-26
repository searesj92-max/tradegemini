# Quant Mathematician Cycle Report
## Researcher: solana-trend-bot · Profile: researcher
## Cycle: 2026-09-23-2154 · Greenfield Hypothesis: Range Efficiency Fade (REG-FAIL-FADE)

## 1. Hipóteses geradas

### Hipótese A — Range Efficiency Collapse + Failed Breakout Fade
Ineficiência: barras de alta variância que fecham perto do open (eficiência de range baixa) sinalizam movimento de breakout falhado dentro do bar. O mercado testou um lado e falhou, gerando pullback de curto prazo. Por que crypto: porções de liquidez e ordens limitadas criam barras de "fakeout" que se revertam. Expressão Pine: rng > k*sma(rng,N) AND abs(close-open)/rng < threshold → entrada de fade na direção oposta ao close vs open.

### Hipótese B — Failed Continuation After Volatility Expansion
Ineficiência: quando ATR atinge zona expandida, mas o bar seguinte não sustenta a direção (displacement fraco), há probabilidade de mean reversion acelerado. Crypto é propenso a impulsos efêmeros pós-expansion por liquidez de mercado profunda. Pine: condição de expansão de ATR + ausência de follow-through no bar seguinte (close volta para equilíbrio) → contrário.

### Hipótese C — Liquidity Sweep + Snapback
Ineficiência: tocar no extremo recente (high/low) com volume e sem rompimento de fechamento indica sweep de liquidez sem direção real — snapback para o interior do range. Pine: high >= ta.highest(N) com close < high → entrada no pullback do extremo.

### Hipótese D — Distance-from-Equilibrium Reversion
Ineficiência: distância em desvio padrão da média móvel (ou VWAP) gera overstretch; retorno tende a continuar até normalização. Pine: z-score do close vs sma(N) e threshold de entrada.

### Hipótese E — Range Expansion Exhaustion
Ineficiência: após sequência de barras com range acima da média, a probabilidade de expansão adicional cai e o próximo movimento tende a ser menor ou revertido. Pine: contagem de barras com rng > sma(rng) e threshold de exaustão.

### Hipótese selecionada (A)
Motivo: matematicamente bem definida (eficiência de range = |close-open|/rng), fácil de testar, sem indicador de retail puro, com direção baseada no signo do movimento dentro do bar. Filtro adicional de expansão de range (rng > k*sma(rng)) reduz falsos positivos de chop. Risco clássico: SL/TP por ATR. Sem trailing stop (regra do loop). High-level: simples, sem params em excesso, potencialmente cross-symbol.

## 2. Regras de trading (A)

### Sinais de entrada
- Variável: rng = high - low; smaRng = ta.sma(rng, 20); eff = abs(close - open) / rng.
- Condição de expansão: rng > 1.5 * smaRng (ou threshold configurável rngMult).
- Condição de colapso de eficiência: eff < 0.30 (threshold configurável effThresh).
- Direção long fade: bar expande e close < open (falha bearish → fade long).
- Direção short fade: bar expande e close > open (falha bullish → fade short).
- Sem entrada se close == open (neutro, skip).

### Saídas
- SL: 1.5 ATR fixo (ticks derivado do ATR).
- TP: 3.0 ATR fixo (ticks derivado do ATR).
- Nenhum trailing stop (regra do loop).

### Filtros
- Nenhum filtro de regime extra neste ciclo (apenas lógica de range/eficiência).
- Risk/trade: 100% equity por posição (perfil de broker configurado).
- Sem cooldown implementado (próxima iteração se necessário).

### Invalidação
- Se a lógica gerar lacuna de trades zero em múltiplos símbolos/TFs, a hipótese é inválida para o universo testeado.

## 3. Pine Script (v4)

```pine
//@version=6
// QM-RANGE-EFF-FADE-v4
// Hypothesis: range expansion bar with low range efficiency → fade.
// Entry: rng > rngMult * sma(rng, rngWin) AND eff < effThresh.
// Direction: close<open → long fade; close>open → short fade.
// Exit: SL/TP at ATR-tick multiples. No trailing. No repaint, no lookahead.
// Allowed ta.* only; process_orders_on_close=true, pyramiding=1, commission 0.05%.

strategy(
  title="QM-RANGE-EFF-FADE-v4",
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

// ---------- inputs ----------
rngWin    = input.int(20, "Range lookback (bars)")
effThresh = input.float(0.30, "Range efficiency collapse threshold", step=0.05)
rngMult   = input.float(1.5, "Range expansion multiple vs recent avg", step=0.1)
atrLen    = input.int(14, "ATR length (for SL/TP)")
slATR     = input.float(1.5, "SL multiple of ATR", step=0.1)
tpATR     = input.float(3.0, "TP multiple of ATR", step=0.1)

// ---------- range context ----------
rng       = ta.range(high, low)
smaRng    = ta.sma(rng, rngWin)
expandRng = rng > (smaRng * rngMult) and not na(smaRng)

// ---------- efficiency ----------
eff       = rng > 0 ? math.abs(close - open) / rng : 0.0
collapse  = eff < effThresh and rng > 0

// ---------- signal ----------
longSig  = expandRng and collapse and close < open
shortSig = expandRng and collapse and close > open

// ---------- ATR-based SL/TP ----------
atrVal   = ta.atr(atrLen)
tickSize = syminfo.mintick  // price units per tick (e.g. 0.1 for BTCUSDT)
slTicks  = atrVal > 0 and tickSize > 0 ? math.max(1, math.round(slATR * atrVal / tickSize)) : 10
tpTicks  = atrVal > 0 and tickSize > 0 ? math.max(1, math.round(tpATR * atrVal / tickSize)) : 20

// ---------- entries ----------
if longSig and strategy.position_size == 0
    strategy.entry("L", strategy.long)

if shortSig and strategy.position_size == 0
    strategy.entry("S", strategy.short)

// ---------- exits ----------
if strategy.position_size > 0
    strategy.exit("LX", from_entry="L", loss=slTicks, profit=tpTicks)

if strategy.position_size < 0
    strategy.exit("SX", from_entry="S", loss=slTicks, profit=tpTicks)

// ---------- plots ----------
plot(longSig,  "longSig",  color.new(color.green, 0), style=plot.style_circles)
plot(shortSig, "shortSig", color.new(color.red,   0), style=plot.style_circles)
plot(expandRng, "rngExp",  color.new(color.blue,  0))
```

## 4. Matriz de backtest

| Strategy ID | Version | Symbol  | Timeframe | Result ID   | Trades | Net% | PF | MaxDD% | WinRate% |
|-------------|---------|---------|-----------|-------------|--------|------|----|--------|----------|
| 01M383W5TPBX0MXVTCH1A0WX96 | v1 | BTCUSDT | 1h | 01M383X5YV9SNPCCY4SNNZR4P8 | 0 | 0 | 0 | 0 | 0 |
| (v1 lineage) | v1 | ETHUSDT | 1h | 01M383XZB8EMWZJY9MWMQW3750 | 0 | 0 | 0 | 0 | 0 |
| (v1 lineage) | v1 | SOLUSDT | 1h | (skip) | — | — | — | — | — |
| (v1 lineage) | v1 | BTCUSDT | 30m | (skip) | — | — | — | — | — |
| (v1 lineage) | v1 | ETHUSDT | 30m | (skip) | — | — | — | — | — |
| (v1 lineage) | v1 | BTCUSDT | 2h | (skip) | — | — | — | — | — |
| (v1 lineage) | v1 | SOLUSDT | 2h | (skip) | — | — | — | — | — |
| (v1 lineage) | v1 | DOGEUSDT | 1h | (skip) | — | — | — | — | — |
| (v1 lineage) | v1 | PEPEUSDT | 30m | (skip) | — | — | — | — | — |
| 01M383ZM053T0YJJPFBY6ZZB83 | v2 | BTCUSDT | 1h | 01M383ZQZXZ1AST42797D7VK29 | 0 | 0 | 0 | 0 | 0 |
| 01M384041RYNZPWZH6S4A47B99 | v1 | ETHUSDT | 1h | 01M38403X9K7T2M2ZV247D2188 | 0 | 0 | 0 | 0 | 0 |
| 01M3843R51Y5G6T79H6Y14Y94D | v3 | BTCUSDT | 1h | 01M38440R8ASKTE67K7M7GNMEG | 0 | 0 | 0 | 0 | 0 |
| 01M38451606WS428ZGWNWRM9Z7 | v4 | BTCUSDT | 1h | 01M38457CD8SM1ZPQ29GRZH3RV | 0 | 0 | 0 | 0 | 0 |

Observação: v3 com bar counters (plot de contagem de long/short/flat) gerou 0 trades → condição nunca satisfeita. Os demais também 0 trades.

## 5. Resultados

- Todas as versões (v1, v2, v3, v4) emitiram ZERO trades em BTCUSDT 1h, ETHUSDT 1h e demais símbolos testados parcialmente.
- Sem trades, não há: net profit, profit factor, drawdown, win rate, avg trade, ratio.
- O mercado de BTCUSDT no histórico testado (com aproximadamente 2439 barras a partir de сент 2025 até сент 2026) não apresentou barras que satisfizessem simultaneamente expansão de range + eficiência de range abaixo do threshold.
- Não é possível afirmar existência de edge ou ausência de edge — mas a condição é rara ou nunca atingida nesse período e universe de 1h para BTC.

## 6. Análise de robustez

- Cross-symbol: não avaliável (sem trades).
- Cross-TF: não avaliável (sem trades).
- Complexidade: baixa (2 condições, 2 direções, SL/TP por ATR, sem trailing).
- Parâmetros: rngMult, effThresh, slATR, tpATR — 4 ajustáveis, com risco de otimização se poucas ocorrências.
- Potencial matemático: a hipótese é plausível em outros regimes (alta frequência choppier, ou TF menor). No TF 1h de BTC, o mercado pode não gerar falsos breakouts dentro do bar com essa frequência, ou os níveis de threshold são muito restritivos.

## 7. Diagnóstico

- 0 trades não significa edge zero; significa zero oportunidade para testar expectancy.
- Diagnósticos possíveis:
  - Threshold de eficiência (0.30) combinado com expansão de range (1.5x) é raro no 1h de BTC.
  - Talvez a hipótese precise de TF menor (15m) para ter mais ocorrências de fakeout intra-bar.
  - Talvez a direção de fade precise de confirmação de bar seguinte, não só intra-bar.
  - Talvez o filtro de range expansion esteja muito restritivo; pode aliviar rngMult para 1.2x.
- Regra do loop: não adicionar indicadores à toa. A próxima iteração foca em (a) TF menor, ou (b) confirmatória no bar seguinte, ou (c) alívio dos thresholds — mas uma única mudança de conceito por ciclo.

## 8. Veredito

**REJEITAR — linha sem trades em 3 ciclos (v1, v2, v3, v4) em BTC 1h e ETH 1h. Sem trades, sem como provar edge ou fragilidade. Pivotizar para próxima hipótese ou remodelar com TF menor / condição de confirmação. Não incubar sem ocorrência mínima de trades.**

Justificativa: três strikes do loop aplicados (v1, v2, v3, v4) sem único trade → inviável para incubação. Não há evidência de edge nem de risco. Não há SL/TP testado em trades reais. Não promover.

## 9. Próximo ciclo

Opções:
- Repensar hipótese com TF menor (15m/30m) com mesmos conceitos de range efficiency.
- Ou mudar conceito: Mean reversion com base em z-score de distância da VWAP + filtro de regime (trend vs chop) com entradas em pullback, SL/TP por ATR.
- Se testar TF menor, usar os mesmos símbolos (BTC, ETH, SOL) e pelo menos 2-3 TFs.
- Sem fork de estratégia anterior. Greenfield do zero.

## Informações de execução

- Trader Dev MCP: autenticado como searesj92@gmail.com (free tier).
- Créditos disponíveis: 424 (saldo antes dos backtests deste ciclo).
- Engine: tv_jul26.
- Perfil de broker forçado: commission 0.05%, percent_of_equity 100%, margin 100, initial_capital 10000.
- Nenhuma ordem real placements realizada.

## Arquivos emitidos

- Pine v4: C:\Users\seares\Desktop\botrade\qm_range_eff_fade_v4.pine
- Relatório: data/reports/2026-09-23-2154-researcher-range-eff-fade.md
- Dashboard: data/data.json + data/data.js (registros v1..v4 com status backtest e 0 trades).
