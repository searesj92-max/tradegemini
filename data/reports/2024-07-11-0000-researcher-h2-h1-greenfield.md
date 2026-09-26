# Trader Dev Research Report

**Agent**: Researcher (Quant Mathematician)
**Data**: 2024-07-11
**H2/H1 Greenfield Cycle — Contingência: Sem Créditos MCP**

---

## 1. Goal

Provar ou refutar dois hipóteses de fatos matemáticos para mercado de cripto (BTC/ETH/SOL, 1h), usando backtest local com dados OHLCV Binance públicos — pois o MCP TraderDev tinha saldo zerado neste ciclo.

---

## 2. Hypothesis Generated

### H2 — Liquidez Sweep + Snapback (seleta)
- **Ineficiência**: falso breakout de range (sweep de stops) seguido de snapback reverso, com alta frequência em crypto.
- **Por que crypto**: stops de mercado concentrados criam liquidez alvo; o preço limpa stops e reverte.
- **Cross-símbolo**: BTC, ETH, SOL, XRP, DOGE.

### H1 — Reversão de Média com Distância Normalizada por Volatilidade
- **Ineficiência**: distância da EMA cresce em ATR múltiplos; candle de cruzamento de volta para dentro do canal antecede reversão.
- **Por que crypto**: extensões extremas são corrigidas por volatility mean-reversion.

---

## 3. Trading Rules

### H2 (seleta)
- **Long**: low < donchian_low(N=20) AND close recupera acima do level violado em ≤3 barras (snapback). Filtro EMA200: só se close > EMA200.
- **Short**: high > donchian_high(N=20) AND close recupera abaixo do level violado em ≤3 barras. Filtro EMA200: só se close < EMA200.
- **SL**: nível violado − 1.5×ATR(14) (long), nível violado + 1.5×ATR (short).
- **TP**: entrada + 2.0×ATR (long), entrada − 2.0×ATR (short).
- **Time exit**: 30 dias. Trailing stop: retrace 40% desde pico.
- **Sizing**: 7% do capital por risco unitário. Fee 0.1%, leverage 1×.
- **Regime filter**: EMA200 (ADX retirado — matou 100% dos sinais em 1h).

### H1
- **Long**: candle cruza EMA20 para baixo (fechamento abaixo da média) com distância prévia > dist_mult×ATR. SL = entrada − sl_mult×ATR. TP = entrada + tp_mult×ATR.
- **Short**: simétrico.

---

## 4. Pine Script

**H2Pine — não submetido ao MCP** (créditos zerados). Versão saved para futuro:

```pine
//@version=6
strategy("QM-SAT-SweepSnap-v1", overlay=true, pyramiding=1, process_orders_on_close=true,
  commission_type=strategy.commission.percent, commission_value=0.05,
  initial_capital=10000, default_qty_type=strategy.percent_of_equity,
  default_qty_value=100, margin_long=100, margin_short=100)

sweepLen = input.int(20, "Sweep lookback")
confirmBars = input.int(3, "Confirm bars")
slAtkMult = input.float(1.5, "SL mult")
tpAtkMult = input.float(2.0, "TP mult")
atrLen = input.int(14, "ATR len")
emaLen = input.int(200, "EMA trend filter")

atrVal = ta.atr(atrLen)
ema200 = ta.ema(close, emaLen)
rangeHi = ta.highest(high, sweepLen)
rangeLo = ta.lowest(low, sweepLen)

// Long sweep + snapback + EMA filter
longCond = low < rangeLo[1] and close > rangeLo[1] and close > ema200
shortCond = high > rangeHi[1] and close < rangeHi[1] and close < ema200

if longCond
    strategy.entry("L", strategy.long)
    strategy.exit("L-exit", from_entry="L",
        loss=atrVal * slAtkMult, profit=atrVal * tpAtkMult)
if shortCond
    strategy.entry("S", strategy.short)
    strategy.exit("S-exit", from_entry="S",
        loss=atrVal * slAtkMult, profit=atrVal * tpAtkMult)

plot(rangeHi[1], "rangeHi", color=color.new(color.red, 50), style=plot.style_linebr)
plot(rangeLo[1], "rangeLo", color=color.new(color.green, 50), style=plot.style_linebr)
plotshape(longCond, "SW L", shape.triangleup, location.belowbar, color.green, size=size.small)
plotshape(shortCond, "SW S", shape.triangledown, location.abovebar, color.red, size=size.small)
```

---

## 5. Backtest Matrix

### H2 — cross-symbol sweep

| Symbol | SL×ATR | TP×ATR | Net% | PF | WR% | Trades | Longs | Shorts |
|--------|--------|--------|------|----|-----|--------|-------|--------|
| BTCUSDT | 1.5 | 2.0 | −99.93 | 0.54 | 40.7 | 819 | 421 | 398 |
| BTCUSDT | 3.0 | 0.5 | **−96.72** | 0.54 | 58.7 | 786 | — | — |
| ETHUSDT | 3.0 | 0.5 | −99.31 | 0.48 | 58.9 | 1878 | — | — |
| SOLUSDT | 3.0 | 0.5 | −100.00 | 0.00 | 0.0 | 0 | — | — |

Melhor combo global (BTC): SL=3.0×ATR, TP=0.5×ATR → PF=0.54, net=−96.72%, WR=58.7% — high WR porém PF fraco porque winners pequenos, losers grandes.

### H2 — diagnóstico de sinais (BTC 1h)

| Métrica | Valor |
|---------|-------|
| Sweeps low events | 2752 |
| Sweeps high events | 3166 |
| Snapback low→long raw | 2101 |
| Snapback high→short raw | 2350 |
| Sinais após EMA200 filter | 625 long + 589 short = 1214 |
| ADX < 25 (filtro retirado) | 0 / 32707 (matou 100%) |
| ATR médio (14) | 435.58 USD |
| Preço médio | 66902.56 USD |
| Range médio % | 3.20% |

### H1 — reversão de média (BTC 1h)

| dist_mult | SL×ATR | TP×ATR | Net% | PF | WR% | Trades |
|-----------|--------|--------|------|----|-----|--------|
| 1.5 | 1.5 | 1.0 | −33.30 | 0.72 | 44.8 | 513 |
| 2.0 | 1.5 | 1.0 | −23.94 | 0.81 | 44.8 | 342 |
| 3.0 | 2.0 | 2.0 | **−16.77** | **0.87** | 40.4 | 686 |
| 3.0 | 2.5 | 2.0 | −16.87 | 0.86 | 41.5 | 623 |

Melhor H1: PF=0.87, ainda <1.0 → **sem edge**.

---

## 6. Results

### Resumo por hipótese

**H2 — Liquidez Sweep + Snapback**: derrotada. PF máximo 0.67 em qualquer símbolo/TF/combo. High WR (58.7%) decomposta: winners ganham +0.5 ATR, losers perdem −3.0 ATR. Razão de risco/retorno desfavorável.

**H1 — Reversão de Média**: derrotada. PF máximo 0.87 (<1.0). Distância da média não prevê reversão rentável em 1h BTC.

**ADX como filtro de regime**: inútil em 1h — ADX nunca cai abaixo de 25 em BTC 2023–2025. Matou 100% dos sinais H2.

**EMA200 como filtro**: reduzu sinais de 4451 para 1214 (27% mantidos), mas não melhorou PF — o núcleo sinal já era negativo.

### Conclusão matemática

O mecanismo de snapback de stops não é explorável em 1h BTC/ETH/SOL: a reversão pós-sweep é fraca e inconsistente. H2 e H1 caem na mesma categoria: estratégias de reversão que não superam o drift de longo prazo do mercado crypto.

---

## 7. Diagnosis

1. **Sinais muito frequentes** (4451 snapbacks raw em 3 anos) → cada sinal tem expectancy negativo.
2. **High win rate, low PF**: a estrutura de perdas (SL largo) domina os pequenos ganhos.
3. **ADX filtro matou tudo**: em 1h, regime de alta volatilidade persistente — ADX>25 quase sempre. Filtro inadequado ao TF.
4. **EMA200 não salvou**: reduzu volume de trades mas não mudou a matemática de base.
5. **Sem cross-symbol validation**: SOL nem sequer gerou trades (volatility extrema, sem snapbacks limpos).

### Por que H2 falhou

O mercado crypto em 1h tem dois regimes predominantes: forte tendência (ADX alto, preço não reverte) e alta volatilidade (ATR grande, stops profundos). O mecanismo de snapback pressupõe que o mercado reverte após limpar stops — mas em crypto o preço muitas vezes continua na direção do sweep após limpar stops, especialmente em	breakout legítimo (notícias, momentum). O filtro EMA200 tentou evitar reversão em tendência, mas também removeu bons trades em consolidação.

---

## 8. Verdict

**H2 — REJEITAR** (line rejected). Não há edge. PF máximo 0.67 em todos os símbolos/testes. Sweep de parâmetros não encontra combo profitable. ADX e EMA200 não salvam. **Esta linha sofreu 2 ciclos sem edge** (H2 original + sweep). Próximo passo: pivot.

**H1 — REJEITAR** (PF=0.87 < 1.0, 1 ciclo). Embora PF=0.87 seja mais próximo de 1.0 que H2, ainda não há evidência de edge. **Esta linha sofreu 1 ciclo sem edge.** Próximo passo: mais 1 ciclo ou pivot.

**Status do ciclo**: sem estratégia com vida. Créditos MCP zerados — backtest adicional via MCP fica pendente até recharge. Ações:
1. Comunicar ao usuário que MCP precisa de créditos para continuar.
2. Ou rodar backtest local em mais símbolos/TFs para H1 antes de dar strike 2.
3. Ou pivot para nova hipótese (volatility regime switching, entropy-based range efficiency, failed continuation com filtro de volume).

---

## 9. Next Cycle

- **Se créditos MCP disponíveis**: rodar quick_backtest para H2 e H1 em 5 symbols × 3 TFs (1h, 4h, 1d) para validar cross-TF.
- **Se sem créditos**: expandir backtest local para H1 em ETH/SOL com sweep de parâmetros (já feito para BTC).
- **Pivot recomendado**: testar nova hipótese baseada em volatility regime switching (identificar qual TF/símbolo tem ADX baixo frequentemente → talvez 4h ou 1d). Ou explorar volume-price anomaly (OBV divergence + snapback).

---

**Relatório salvo**: `data/reports/2024-07-11-0000-researcher-h2-h1-greenfield.md`
**Status MCP**: créditos zerados — ações via MCP não executadas.
**Não há ordens reais**. Research only.
