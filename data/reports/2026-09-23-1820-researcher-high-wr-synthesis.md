# Trader Dev Research Report — High-WR Desk Synthesis

**Date**: 2026-09-23-1820  
**Agent**: researcher + optimizer (batch scripts)  
**Engine**: tv_jul26 · window 2025-01-01 → 2026-09-01  
**Matrix**: 8 crypto perps × 4h/1h · commission 0.05% (public forks) / 0% (local mcprule)  
**Credits**: high-WR local 176 + no-trail 96 (1 IncompleteRead) + prior discovery  

---

## 1. Goal

Find strategies with **high win rate AND desk-safe metrics**: PF ≥ 1.3, max DD ≤ 30%, WR ≥ 50%, trades ≥ 40, multi-pair, SL present, **no trailing**, no repaint/lookahead.

## 2. Strategy / Hypothesis tested

| Batch | Design | Count |
|---|---|---:|
| High-WR local | trend-pullback, regime MR, sweep, squeeze, RSI+EMA trend | 176 |
| Public leaderboard | top WR≥50 / PF≥1.3 / DD≤25 (safe filter) | 16 → dashboard 40 rows |
| No-trail public forks | G91, Vanta RSI2, LTC EMA9-VWAP, EMA4-VWAP ± tight TP | 96 |

## 3. Pine Script changes (no-trail forks)

- Removed **all** `trail_points` / `trail_offset` / trailing Donchian stop  
- Hard **SL + TP** fixed in ATR (`stop=` + `limit=`)  
- Removed G91 hard-coded `time` window  
- Kept commission 0.05% on public lineage  

Files: `data/pine/nt-*.pine`, `data/pine/pub-*.pine`, `data/pine/hw-*.pine`

## 4. Backtest matrix

Symbols: BTC ETH SOL XRP DOGE AVAX LINK ADA  
TFs: 4h (primary), 1h  
Reports:  
- `2026-09-23-1809-high-wr-batch.md`  
- `2026-09-23-1816-notrail-fork.md`  
Dashboard: **455 rows** (`dashboard/data.json` + `data.js`)

## 5. Results

### 5.1 High-WR gate (WR≥50 · PF≥1.3 · DD≤30 · trades≥40 · net>0)

| Source | Pass / total rows |
|---|---:|
| Local high-WR (176) | **0 / 176** |
| No-trail public (96) | **0 / 95** (1 network error) |
| Leaderboard (public, often 1 pair + trailing) | 40 / 40 by numeric filter only |

### 5.2 Best local risk-adjusted (not WR≥50, but honest edge candidates)

| Strategy | Pair | TF | Net% | PF | DD% | WR% | Trades | Verdict |
|---|---|---|---:|---:|---:|---:|---:|---|
| rsi-t200 | AVAXUSDT | 4h | 97.83 | 1.80 | 12.33 | 39.64 | 111 | Watchlist |
| rsi-t200 | ADAUSDT | 4h | 39.16 | 1.46 | 22.30 | 39.39 | 99 | Watchlist |
| rsi-t200 | XRPUSDT | 4h | 41.21 | 1.72 | 18.92 | 38.10 | 84 | Watchlist |
| rsi-t200 | LINKUSDT | 4h | 29.49 | 1.33 | 21.61 | 37.50 | 96 | Watchlist |
| squeeze | XRPUSDT | 4h | 45.96 | 1.51 | 11.89 | 29.67 | 91 | Watchlist |

`rsi-t200` shows **multi-pair signs of life** (4h) but mean WR ≈ 36–40% — fails WR≥50 gate.

### 5.3 No-trail public forks — verdict histogram

All families: **Reject**. Tight-TP variants raise WR (g91-tight often 50–66%) but PF < 1 and DD 76–99% — **higher WR is not an edge when expectancy is negative**.

## 6. Robustness analysis

1. **Leaderboard high WR is trailing-dependent.** Every inspected public top scorer (G91, Vanta, LTC Codex, BTC EMA4-VWAP, SOL Donchian) exits via trail (or trail + loss). Desk rules ban trailing → those KPIs are not reproducible under desk rules.  
2. **Tight TP inflates WR without profit.** g91-tight / vanta-tight: WR often ≥50% on 1h, still net ≈ −95%. Classic “lottery of small wins.”  
3. **G91 date-window was overfit** (hard-coded `time` range). Removing it → all Reject.  
4. **Local designs** did not reach WR≥50 multi-pair; best local family is regime-filtered RSI mean-reversion (`rsi-t200`) on 4h.

## 7. Weaknesses

- No strategy currently meets the **full** high-WR desk gate multi-pair.  
- Local batch commission=0 vs public 0.05% — local numbers slightly optimistic.  
- Leaderboard rows with net% in thousands are single-pair / trail / possible engine artifacts — **not approved candidates**.  
- 1 IncompleteRead on vanta-nt/AVAXUSDT/1h (cosmetic gap).

## 8. Next iteration (suggested)

1. **Do not chase WR≥50 with trail-free fixed TP** on the same public entries — already falsified.  
2. Prioritise **expectancy + DD control** (`rsi-t200` family): optimize SL/TP only, add 2nd TF confirmation, never re-introduce trail.  
3. Optional: higher-WR via **regime filter quality** (ADX/vol rank), not tighter TP.  
4. Hold credits; ~800 left after this wave.

## 9. Verdict

| Item | Decision |
|---|---|
| Leaderboard “safe high-WR” (trail, 1 par) | **REJEITAR** para book (não repro sob regras do desk) |
| High-WR local (WR≥50 multi-par) | **NÃO ENCONTRADO** nesta rodada |
| No-trail public forks | **REJEITAR** (0 passam no gate) |
| `rsi-t200` · 4h multi-par | **ESTACIONAR / Watchlist** — sinais de vida, WR < 50 |
| `squeeze` · XRPUSDT · 4h | **ESTACIONAR** — PF/DD bons, WR baixo |
| Qualquer aprovação → incubação | **NÃO** — gate de WR multi-par não passou |

**Desk summary**: high win rate under desk rules (SL fixo, sem trailing, multi-par) is **hard**; public leaderboard WR is mostly trail artifact. Prefer PF/DD robustness over headline WR.

---

*Risk notice: research only. Not financial advice. Backtest ≠ future performance. No real orders.*
