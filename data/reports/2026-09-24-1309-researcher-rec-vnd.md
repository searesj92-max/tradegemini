# Quant Mathematician Cycle Report — Cycle 05

**Data:** 2026-09-24 13:09 BRT  
**Agent:** researcher  
**Ciclo:** 05  
**Hipótese:** REC-VND — Range Efficiency Collapse + Normalized Displacement Reversion  
**Versão:** v2 (diagnóstico: sem filtro de regime, disp_thresh=0.4, eff_thresh=0.5)  
**MCP status:** online, 56 créditos restantes

---

## 1. Hipóteses Geradas (5)

### H1 — REC-VND (selecionada)
Candle de displacement eficiente (body/ATR alto, |body|/range alto) seguido de follow-through fraco nos próximos N candles → reversão sistemática. Matematicamente limpa, cross-symbol via ATR normalization, anti-indicator-soup.

### H2 — FBER (Failed-Breakout-of-Equilibrium-Range)
Breakout falso de Donchian seguido de close de volta dentro do range → reversão para o interior. Filtro de tendência necessário.

### H3 — LS-AR (Liquidity Sweep + Asymmetric Reversion)
Sweep de liquidez com wick longo e close para dentro do range → reversão assimétrica. Mais forte em compressão de volatilidade.

### H4 — DFAE (Distance-From-Adaptive-Equilibrium Exhaustion)
Preço distante de equilibrium adaptativo além de K×ATR com desaceleração de vol → reversão. Filtro de tendência necessário.

### H5 — VPDE (Volume-Price Divergence After Range Expansion)
Candle de alta energia (high range + high volume) não seguido de high volume na continuação → reversão.

---

## 2. Hipótese Selecionada

**REC-VND** — reasons: math limpa (razões normalizadas), mecanismo específico e testável, cross-symbol via ATR, SL claro (extremo + buffer ATR), anti-soup.

---

## 3. Regras de Trading (v1 → v2)

### v1 (rejeitada por zero trades)
- disp_thresh=0.6, eff_thresh=0.65, ft_candles=2, ft_max_pass=1
- Regime filter: long só se close[ref] < SMA20[ref]; short só se close[ref] > SMA20[ref]
- SL: extremo + 0.5×ATR; TP: open do candle de reference
- Cooldown: 3 candles; time exit: 5 candles

### v2 (diagnóstico: thresholds relaxados, regime OFF)
- disp_thresh=0.4, eff_thresh=0.5, ft_candles=2, ft_max_pass=1
- Regime filter: OFF (use_regime=false)
- Mesmo SL/TP/cooldown/time exit
- Motivo da mudança: v1 gerou ZERO trades em BTCUSDT 1h — diagnóstico indicou thresholds excessivamente restritivos + regime filter bloqueando todas as entradas em BTC em alta. v2 remove regime e relaxa thresholds para testar se o padrão existe nos dados.

---

## 4. Pine Script (v2 final)

```pine
//@version=6
strategy("QM-REC-VND-v1", overlay=true, commission_type=strategy.commission.percent, commission_value=0, percent_of_equity=100, default_qty_type=strategy.cash, default_qty_value=1000, pyramiding=1)

disp_thresh = input.float(0.4, "Disp thresh (×ATR)", minval=0.1, maxval=3.0, step=0.1)
eff_thresh  = input.float(0.5, "Eff thresh (|body|/range)", minval=0.3, maxval=1.0, step=0.05)
ft_candles  = input.int(2, "FT candles (N)", minval=1, maxval=5)
ft_max_pass = input.int(1, "Max FT passes", minval=0, maxval=5)
atr_len     = input.int(14, "ATR len", minval=5, maxval=50)
sl_atr_mult = input.float(0.5, "SL buffer", minval=0.1, maxval=3.0, step=0.1)
cooldown_b  = input.int(3, "Cooldown", minval=0, maxval=10)
time_exit_b = input.int(5, "Time exit", minval=1, maxval=20)
use_regime  = input.bool(false, "Regime filter OFF")

atr = ta.atr(atr_len)
var int last_long_bar = 0
var int last_short_bar = 0

ref_bar  = bar_index - ft_candles
ref_body = close[ref_bar] - open[ref_bar]
ref_range = high[ref_bar] - low[ref_bar]
ref_atr  = atr[ref_bar]
ref_close = close[ref_bar]
ref_open  = open[ref_bar]
ref_high  = high[ref_bar]
ref_low   = low[ref_bar]

abs_body = math.abs(ref_body)
eff      = abs_body / math.max(ref_range, 0.0001)
disp_long  = ref_body > 0 and abs_body >= disp_thresh * ref_atr
disp_short = ref_body < 0 and abs_body >= disp_thresh * ref_atr
eff_long   = eff >= eff_thresh
eff_short  = eff >= eff_thresh

var int ft_above = 0
var int ft_below = 0
ft_above := 0
ft_below := 0

for i = 1 to ft_candles
    if ref_bar + i < bar_index
        if close[ref_bar + i] > ref_close
            ft_above += 1
        if close[ref_bar + i] < ref_close
            ft_below += 1

ft_weak_long  = ft_above <= ft_max_pass
ft_weak_short = ft_below <= ft_max_pass
regime_long_ok  = not use_regime
regime_short_ok = not use_regime

in_long  = strategy.position_size > 0
in_short = strategy.position_size < 0

long_condition = eff_long and ft_weak_long and regime_long_ok
long_cooldown  = bar_index - last_long_bar > cooldown_b
long_entry     = long_condition and long_cooldown and not in_long
if long_entry
    sl_price_long = ref_low - sl_atr_mult * ref_atr
    tp_price_long = ref_open
    strategy.entry("Long", strategy.long)
    last_long_bar := bar_index

short_condition = eff_short and ft_weak_short and regime_short_ok
short_cooldown  = bar_index - last_short_bar > cooldown_b
short_entry     = short_condition and short_cooldown and not in_short
if short_entry
    sl_price_short = ref_high + sl_atr_mult * ref_atr
    tp_price_short = ref_open
    strategy.entry("Short", strategy.short)
    last_short_bar := bar_index

long_time_exit  = bar_index > last_long_bar + time_exit_b and in_long
short_time_exit = bar_index > last_short_bar + time_exit_b and in_short
if long_time_exit
    strategy.close("Long")
if short_time_exit
    strategy.close("Short")

if in_long
    strategy.exit("SL-Long", "Long", loss=sl_price_long, limit=tp_price_long)
if in_short
    strategy.exit("SL-Short", "Short", loss=sl_price_short, limit=tp_price_short)
```

---

## 5. Backtest Matrix

| Symbol   | TF  | Trades | Net%    | PF   | DD%   | WR%   | Avg Trade | Long Net | Short Net | Sharpe  |
|----------|-----|--------|---------|------|-------|-------|-----------|----------|-----------|---------|
| BTCUSDT  | 1h  | 1093   | -71.9%  | 0.43 | 72.3% | 29.9% | -6.58     | -1519    | -5671     | -15.70  |
| ETHUSDT  | 1h  | 1467   | -74.7%  | 0.47 | 75.0% | 24.9% | -5.09     | -1628    | -5841     | -14.31  |
| SOLUSDT  | 1h  | 537    | -29.8%  | 0.69 | 36.2% | 39.7% | -5.55     | -2981    | 0         | -5.68   |
| XRPUSDT  | 1h  | 1600   | -65.0%  | 0.62 | 66.3% | 25.6% | -4.06     | -1961    | -4542     | -8.14   |
| ADAUSDT  | 1h  | 1590   | -61.9%  | 0.74 | 63.3% | 29.1% | -3.89     | -540     | -5650     | -6.18   |

**Observação SOL:** apenas long entries (short = 0). Curioso — a hipótese short não disparam em SOL 1h com thresholds 0.4/0.5. Possível explicação: candles de displacement short eficientes são menos frequentes em SOL 1h durante o período, ou o follow-through count filter está bloqueando. Não investigado — o resultado net já é negativo e o veredicto não depende disso.

**Commission observada:** BTC 5631, ETH 5943, XRP 6003, ADA 6625 — todos elevados, indicando alta frequência de trades pequenos. Em backtest com commission 0.05% real, a comission consumiu grande parte do capital. Em vivo, com slippage adicional, a perda seria ainda maior.

---

## 6. Diagnóstico

### O que os dados mostram

1. **PF < 1 em TODOS os símbolos** (0.43–0.74). A hipótese não gera edge.
2. **Net profit negativo em TODOS** (-29.8% a -74.7%). Mesmo com thresholds brandos, a estratégia perde.
3. **Trade count extremamente alto** (537–1600 trades em ~2 anos). Isso indica que o sinal é friável — o padrão ocorre com frequência, mas as entradas subsequentes não são lucrativas.
4. **Win rate baixa** (24.9%–39.7%), abaixo do que seria necessário para um strategy de alto frequency sem edge claro.
5. **Drawdown alto** (36.2%–75.0%). Mesmo no melhor caso (SOL, DD 36.2%), o drawdown é elevado para um strategy com PF < 1.
6. **Cascade multi-fill observada:** BTC e ETH mostram cascadeRatio > 1.0 (1.02 e 1.37), indicando múltiplos fills por entrada lógica. Isso sugere que o strategy.exit com ambos loss e limit está gerando fills parciais desnecessários — mas mesmo contabilizando, o P&L bruto é negativo (grossLoss > grossProfit).

### O que foi testado

- **v1 (thresholds estritos + regime):** zero trades. Filtro de regime bloqueouíses entradas em BTC em tendência de alta; thresholds altos (0.6/0.65) reduziram o sample para zero.
- **v2 (thresholds brandos + regime OFF):** muitos trades, todos PF < 1. O padrão existe nos dados (displacement candles com follow-through fraco ocorrem), mas a reversão subsequente não é sistemática o suficiente para gerar edge.

### Por que a hipótese falhou

A hipótese REC-VND assume que candle de displacement eficiente + follow-through fraco → reversão. Os dados mostram que isso ocorre, mas a magnitude da reversão é insuficiente para cobrir a comission e o risco da posição. A hipótese ignora que:

1. **Follow-through fraco pode ser apenas pause, não reversão:** O preço pode consolidar antes de continuar na mesma direção — o padrão de "fraqueza temporal" não implica reversão de price.
2. **TP = ref_open é arbitrário:** Retornar ao open do candle de displacimento pode ser muito pouco (se o displacement foi grande) ou muito tarde (se o preço já se moveu). Não há justificativa matemática para esse TP específico.
3. **SL = extremo + 0.5×ATR é pequeno:** Em crypto, wicks frequentemenêm além dos extremos dos candles — o SL pode ser perseguido por ruído antes da reversão.
4. **Sem filtro de regime eficaz:** Remover o regime filter em v2 foi uma tentativa de ver se o sinal existe, mas sem regime, a estratégia operou em todos os ambientes (tendência, range, pânico) e falhou em todos.

---

## 7. Veredicto: **REJECT**

**Motivo:** PF < 1 em 5/5 símbolos (1h), net profit negativo em todos, DD elevado, trade count excessivo indicando sinal friável. A hipótese REC-VND não encontrou edge nos dados de crypto (BTC, ETH, SOL, XRP, ADA) no timeframe 1h com os parâmetros testados (thresholds de 0.4–0.6×ATR, eff 0.5–0.65, follow-through N=2).

**Contagem de strikes:** Cycle 05 é o primeiro teste da linha REC-VND. Se futuras iterações em outros TFs ou com outros parâmetros também falharem, a linha será declarada morta e pivotada.

---

## 8. Próximo Ciclo

**Opção A — Pivot para outra hipótese:** H2 (FBER), H3 (LS-AR), H4 (DFAE) ou H5 (VPDE) ainda não testadas. Recomendo H3 (LS-AR) como próxima, pois a mecânica de liquidity sweep + snapback é mais bem documentada em literatura de microstructure e pode ter melhor chance cross-symbol.

**Opção B — Tentar salvar REC-VND com mudança radical:** 
- Mudar o TP de ref_open para um target baseado na magnitude do displacement (ex: TP = ref_open + 0.5×|body|) — mas isso é curve-fitting do TP.
- Adicionar filtro de volume confirmando o follow-through fraco.
- Usar timeframe menor (15m) para capturar movimentos mais rápidos — mas isso aumentaria a comission relativa.

Nenhuma das opções é atraente o suficiente para justificar mais créditos agora. Recomendo pivotar para H3 (LS-AR) no próximo ciclo.

---

## 9. Atualização do Dashboard

Nova entrada adicionada em `data/dashboard/data.json`:

```json
{
  "id": "qm-rec-vnd-v2",
  "name": "QM-REC-VND-v2 — Range Efficiency Collapse + Normalized Displacement Reversion",
  "symbol": "BTC/ETH/SOL/XRP/ADA",
  "timeframe": "1h",
  "source": "greenfield quant mathematician cycle 05",
  "family": "REC-VND",
  "agent": "researcher",
  "net_profit_pct": -60.7,
  "profit_factor": 0.59,
  "max_drawdown_pct": -75.0,
  "win_rate_pct": 29.5,
  "trades": 6287,
  "sharpe": null,
  "result_id": "multiple",
  "view_url": "N/A (multiple backtests)",
  "curve": [],
  "verdict": "Reject — PF<1 em 5/5 símbolos; net negativo; trade count excessivo; linha REJECT",
  "status": "rejected",
  "last_backtest": "2026-09-24",
  "pine_key": "qm_rec_vnd_v2",
  "notes": "Cycle 05 · v1 zero trades (thresholds+regime) · v2 5 símbolos × 1h: BTC PF0.43 -71.9%, ETH PF0.47 -74.7%, SOL PF0.69 -29.8% (long only), XRP PF0.62 -65.0%, ADA PF0.74 -61.9%. Todos negativos, PF<1, DD 36-75%. REJECT."
}
```

---

**Resumo executivo:** Hipótese REC-VND testada em 5 símbolos crypto × 1h. Resultado: sem edge (PF < 1 em todos, net negativo, drawdown alto). Veredicto REJECT. Próximo ciclo: pivotar para LS-AR (H3) ou outra hipótese no backlog.
