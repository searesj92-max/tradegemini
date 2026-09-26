# Trader Dev Research Report — Batch 3 (Expanded Universe)

## 1. Goal
Testar mais estratégias em **mais ativos** e filtrar o que sobrevive ao gate do desk (PF≥1.3, DD≤30%, trades≥40, net>0, multi-par, sem trailing).

## 2. Strategy / Hypothesis
10 famílias: RSI+trend (3 variants — a que sobreviveu antes) · vol-displacement · failed continuation · range efficiency · Donchian regime · EMA pullback · BB pinch · momentum z-score.

## 3. Pine Script Changes
- Sem trailing · SL+TP em ATR · `process_orders_on_close` · commission 0 · pyramiding 1  
- Greenfield quant (não copiar leaderboard)

## 4. Backtest Matrix
- **16 ativos 4h**: BTC ETH SOL XRP DOGE AVAX LINK ADA BNB NEAR APT ARB OP INJ ATOM FIL  
- Window: 2025-01-01 → 2026-09-01 · Engine tv_jul26 · 160 combos · 0 erros  
- 1h screen: pendente (créditos)

## 5. Results
Dashboard: **615 rows** · stats: Candidates 42 (leaderboard, trail) · Incubate 11 · Watchlist 153 · Reject 409

### Pairs pass / 16 (desk gate local: PF≥1.3 · DD≤30 · trades≥40 · net>0)
| Strategy | pass | meanPF | meanWR | best net |
|---|---:|---:|---:|---:|
| **rsi-t200b** | **8/16** | **1.69** | 35.4% | 71.0% |
| **rsi-t200** | **6/16** | 1.22 | 35.0% | 97.8% |
| **rsi-t100** | **5/16** | 1.37 | 37.0% | 48.5% |
| bb-pinch | 1/16 | 0.88 | 26.9% | 30.1% |
| demais 6 | 0/16 | — | — | — |

### Top rows (rsi-t200b)
- ARB +71% PF 2.20 DD 11% · OP +67% PF 1.92 DD 17% · AVAX +51% PF 2.99 DD 14%  
- ATOM +35% PF 1.71 · INJ +28% PF 1.46 · XRP +28% PF 1.84 · ETH +44% PF 3.65 (39 trades)

### Incubate labels (batch local)
rsi-t200: XRP AVAX LINK ADA OP FIL · rsi-t200b: ARB OP INJ ATOM · rsi-t100: OP

## 6. Robustness Analysis
- **Família RSI+trend filter é a única multi-par estável** (5–8/16 pares).  
- Hypotheses quant novas (displacement, fail-cont, range-eff, mom-z) **não passaram** no 4h.  
- voldisp = 0 trades (condição contraditória) → descartar.  
- failcont/rangeeff = amostra pequena → não avaliáveis.

## 7. Weaknesses
- WR médio ~35% (gate high-WR 50% não atingido — esperado em MR com TP>SL).  
- 4h only nesta rodada; 1h/2h faltam para confirmação TF.  
- Candidates 42 no painel são **leaderboard com trailing** — não aprováveis pelo desk.

## 8. Next Iteration
1. Confirmar **rsi-t200b** em 1h+2h nos 8 pares que passaram.  
2. Gertrude classificar Incubates → incubação ou parked.  
3. Otimizar só SL/TP de rsi-t200b (1 mudança).  
4. Créditos: ~287 após este lote.

## 9. Verdict
| Family | Verdict |
|---|---|
| rsi-t200b (8/16, PF 1.69) | **Incubate candidate** — melhor do book local |
| rsi-t200 / rsi-t100 | **Incubate / Watchlist** multi-par |
| bb-pinch / mom-z / dc / emapb / rangeeff / failcont / voldisp | **Reject** neste ciclo |
| Leaderboard trail WR 60–85% | **Reject** (regra: sem trailing) |

**Melhor resultado atual do desk local:** `rsi-t200b` · 4h · 8/16 pares · mean PF 1.69 · DD ≤ 25% na maioria.
