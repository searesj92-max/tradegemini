"""Batch 4 synthesis — bull/low-risk desk report (Gertrude-ready)."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

ROOT = Path(r"C:\Users\seares\Desktop\botrade")
ts = datetime.now().strftime("%Y-%m-%d-%H%M")

md = f"""# Trader Dev Research Report — Batch 4 Bull / Low Risk

## 1. Goal
Encontrar estratégias **long-only de baixo risco** para o rally atual de BTC (WR bom, DD controlado), gate desk multi-par.

## 2. Strategy or Hypothesis
7 designs bull: pullback em tendência, higher-high breakout, RSI+trend long, squeeze long, EMA golden pullback, Donchian long+ADX, momentum dip z-score.

## 3. Pine Script Changes
- Long-only · SL+TP ATR · sem trailing · `process_orders_on_close` · commission 0 · pyramiding 1
- Pines: `data/pine/b4-*.pine`

## 4. Backtest Matrix
- **12 ativos · 4h** · window 2025-01-01 → 2026-09-01 · engine tv_jul26
- **84 combos · 0 erros**
- Gate: PF≥1.3 · DD≤30 · trades≥40 · net>0 · (WR≥50 = bonus Candidate)

## 5. Results
| Strategy | pass/12 | meanPF | meanWR | bestNet |
|---|---:|---:|---:|---:|
| **b4-rsi-t-l** | **0/12** | 0.99 | **54.5%** | +24.5% |
| b4-mom-dip | 0/12 | 0.88 | 52.9% | +17.0% |
| b4-gold-pb | 0/12 | 0.87 | 49.9% | +24.1% |
| b4-dc-long | 0/12 | 0.89 | 41.6% | +30.8% |
| b4-sq-long | 0/12 | 0.80 | 40.7% | +14.1% |
| b4-hh-brk | 0/12 | — | — | 0 trades |
| b4-bull-pb | 0/12 | — | — | 0 trades |

**Melhores linhas (WR alto, amostra <40 trades):**
- rsi-t-l · AVAX · net +24.5% · PF 2.08 · DD 11.9% · **WR 71.4%** · 14 trades
- rsi-t-l · ETH · net +14.4% · PF 1.36 · DD 8.8% · **WR 64.3%** · 28 trades
- rsi-t-l · BNB · net +7.3% · PF 1.28 · DD 14.5% · **WR 66.7%** · 18 trades
- sq-long · ARB · net +14.1% · PF 1.58 · DD 20.6% · WR 66.7% · 9 trades
- mom-dip · SOL · net +17.0% · PF 1.09 · DD 23.6% · WR 59.3% · 91 trades

**Verdicts:** Reject 29 · Watchlist 55 · Candidate 0 · Incubate 0

## 6. Robustness Analysis
- **WR alto existe no bull long-only** (mean 50–55% em rsi-t-l/mom-dip) mas **PF médio ≤ 0.99** → expectancy ~0 no gate.
- Amostras de trades <40 na maioria dos “WR 60%+” → **não estatísticamente sólido**.
- **hh-brk / bull-pb = 0 trades em 12 pares** → entradas demais restritivas no window (crossover+pullback simultâneo); diagnosticar e afrouxar 1 condição se re-testar.
- Família **rsi-t200b (batch3, long+short com filtro)** segue como melhor multi-par do book local (8/16, PF 1.69) — bull-only não a superou com trades≥40.

## 7. Weaknesses
- Nenhum passa no gate multi-par com trades≥40.
- Long-only perde o short edge do rsi-trend bilateral.
- commission 0 local (mcprule) — números levemente otimistas vs 0.05%.

## 8. Next Iteration
1. **Afrouxar hh-brk/bull-pb** (1 condição) e re-rodar só essas 2 × 12 pares (24 créditos) se houver interesse.
2. Cruzar **rsi-t-l** com filtro ADX/vol-rank para subir PF mantendo WR.
3. Confirmar **rsi-t200b** em 1h/2h nos 8 pares que passaram (batch3) — prioridade incubação.
4. Créditos ~192 — reservar para cross-TF do rsi-t200b.

## 9. Verdict
| Item | Decision |
|---|---|
| b4-rsi-t-l (WR 54.5%, PF 0.99, 0/12 gate) | **ESTACIONAR** — melhor WR bull, falta trades/PF |
| b4-mom-dip / gold-pb | **ESTACIONAR** fraco |
| b4-dc-long / sq-long | **REJEITAR** nesta forma |
| b4-hh-brk / b4-bull-pb | **REJEITAR** (0 trades) — rework opcional |
| rsi-t200b bilateral 4h (batch3) | **INCUBATE candidate** — melhor do book |

**Síntese:** long-only bull puro não entregou edge multi-par com amostra suficiente; o melhor caminho de baixo risco no rally segue **rsi-trend com filtro** (bilateral ou rsi-t-l refinado), com foco em PF/DD e confirmação cross-TF.

---
*Research only. Not financial advice. Backtest ≠ future. No real orders. Generated {ts}.*
"""

out = ROOT / "data" / "reports" / f"{ts}-researcher-batch4-synthesis.md"
out.write_text(md, encoding="utf-8")
print("wrote", out)
