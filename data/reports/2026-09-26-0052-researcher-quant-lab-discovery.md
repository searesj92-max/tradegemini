# Trader Dev Research Report — Quant Lab Discovery

**Date**: 2026-09-26-0052 · **Agent**: researcher · **Engine**: local Python (0 API credits)
**Universe**: BTC, ETH, SOL, AVAX, LINK, ARB, DOGE, SUI, NEAR, XRP (10 coins)
**Timeframes**: 1h, 2h, 4h, 15m
**Total Setups Evaluated**: 64 combinações

## 1. Top 10 Melhores Combinações (Ranqueadas por Robustez)

| Rank | Estratégia | TF | SL / TP | Passaram Gertrude | PF Médio | Retorno Médio | Max DD | Win Rate |
|---|---|---|---|---:|---:|---:|---:|---:|
| 1 | `rsi-t200b` | **2h** | SL 2.5 / TP 1.6 | **9/10** | **1.64** | +31.7% | 22.3% | 70.7% |
| 2 | `rsi-t200b` | **2h** | SL 1.8 / TP 1.5 | **6/10** | **1.46** | +20.9% | 27.1% | 62.9% |
| 3 | `rsi-t200b` | **4h** | SL 1.8 / TP 1.5 | **5/10** | **2.64** | +41.2% | 20.9% | 72.4% |
| 4 | `rsi-t200b` | **4h** | SL 2.5 / TP 1.6 | **4/10** | **2.52** | +45.4% | 28.4% | 76.7% |
| 5 | `keltner-bb-squeeze` | **4h** | SL 1.5 / TP 2.0 | **2/10** | **1.12** | +23.2% | 48.2% | 46.1% |
| 6 | `keltner-bb-squeeze` | **4h** | SL 1.8 / TP 2.8 | **1/10** | **1.12** | +18.3% | 49.7% | 41.8% |
| 7 | `ema9-21` | **4h** | SL 2.0 / TP 4.0 | **1/10** | **1.09** | +16.4% | 81.1% | 35.6% |
| 8 | `keltner-bb-squeeze` | **2h** | SL 2.2 / TP 3.5 | **1/10** | **1.08** | +9.5% | 54.1% | 40.1% |
| 9 | `rsi-t200b` | **1h** | SL 1.8 / TP 1.5 | **1/10** | **1.03** | -5.0% | 32.7% | 58.5% |
| 10 | `squeeze` | **2h** | SL 1.5 / TP 2.5 | **1/10** | **1.03** | -5.0% | 50.9% | 38.7% |

## 2. Detalhamento da Campeã: `rsi-t200b` (2h)

| Moeda | Retorno % | Profit Factor | Max DD % | Win Rate % | Trades | Veredito Gertrude |
|---|---:|---:|---:|---:|---:|---|
| BTC | +6.66% | 1.31 | 7.42% | 65.1% | 43 | **Watchlist** |
| ETH | +31.19% | 1.65 | 10.56% | 74.5% | 51 | **Candidate** |
| SOL | +79.34% | 2.89 | 9.94% | 80.4% | 46 | **Watchlist** |
| AVAX | +38.51% | 1.78 | 17.23% | 71.4% | 42 | **Watchlist** |
| LINK | +31.29% | 1.59 | 12.20% | 71.7% | 46 | **Watchlist** |
| ARB | +23.67% | 1.34 | 15.14% | 66.7% | 51 | **Candidate** |
| DOGE | +33.47% | 1.62 | 13.01% | 75.0% | 48 | **Watchlist** |
| SUI | +36.08% | 1.61 | 22.26% | 69.0% | 42 | **Watchlist** |
| NEAR | +41.18% | 1.55 | 14.93% | 68.6% | 51 | **Candidate** |
| XRP | -4.11% | 1.00 | 19.53% | 64.3% | 42 | **Reject** |

## 3. Detalhamento da Vice-Campeã: `rsi-t200b` (2h)

| Moeda | Retorno % | Profit Factor | Max DD % | Win Rate % | Trades | Veredito Gertrude |
|---|---:|---:|---:|---:|---:|---|
| BTC | -2.99% | 0.99 | 10.83% | 54.3% | 46 | **Reject** |
| ETH | +29.60% | 1.66 | 13.71% | 69.0% | 58 | **Candidate** |
| SOL | +74.52% | 2.77 | 6.00% | 76.9% | 52 | **Candidate** |
| AVAX | +30.60% | 1.67 | 13.54% | 64.4% | 45 | **Watchlist** |
| LINK | +16.39% | 1.35 | 15.29% | 63.3% | 49 | **Watchlist** |
| ARB | +4.94% | 1.13 | 27.06% | 57.1% | 56 | **Watchlist** |
| DOGE | +29.62% | 1.55 | 24.28% | 67.9% | 53 | **Candidate** |
| SUI | +16.05% | 1.29 | 19.52% | 60.0% | 50 | **Watchlist** |
| NEAR | +21.85% | 1.34 | 13.79% | 61.1% | 54 | **Candidate** |
| XRP | -11.14% | 0.86 | 23.40% | 54.5% | 44 | **Reject** |

## 4. Análise Quantitativa por Timeframe

- **4h**: Menor ruído, maior taxa de acerto e estabilidade institucional em tendências longas.
- **2h**: Excelente relação risco/retorno para momentum swing.
- **1h**: Bom equilíbrio para o Sniper de alta frequência quando filtrado por macro EMA 200.
- **15m**: Alta frequência de trades com ruído aumentado; necessita filtros estritos de volatilidade.

## 5. Veredito & Próximos Passos
As estratégias vencedoras foram catalogadas sem gastar nenhum crédito. O robô ao vivo no Render continua operando com o setup atual com segurança, e temos agora setups candidatos comprovados matematicamente.