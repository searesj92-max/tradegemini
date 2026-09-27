# Trader Dev Research Report — Multi-Pair Robustness Matrix

**Data**: 2026-09-27 15:43 UTC
**Universo**: Top 10 Hyperliquid Perps (BTC, ETH, SOL, AVAX, SUI, DOGE, NEAR, LINK, ARB, OP)
**Capital por Posição**: $20.00 USDC @ 10x | **Custos**: Taker 0.035% + Slippage 0.05%
**Blindagem**: SL Dinâmico ATR + Ratchet Breakeven (+30% ROE)

---

## 1. Veredito Executivo das Famílias Multi-Par

| Estratégia / Família | TF | Pares Positivos | PF Agregado | PnL Total ($) | Win Rate % | Trades | Veredito Gertrude |
|---|---|---|---|---|---|---|---|
| **Reversão à Média Bollinger Bands + RSI** | 1h | 4/10 | 73.00 | $1.9% | 83.3% | 6 | **CANDIDATE** |
| **Dual-Engine Sniper (Pullback + Confluência)** | 1h | 0/10 | 0.70 | $-217.5% | 37.7% | 653 | **REJECT** |
| **Pullback Macro Institucional (EMA200 + RSI)** | 2h | 5/10 | 0.91 | $-17.9% | 47.3% | 131 | **REJECT** |
| **Confluência Donchian Breakout + Volume** | 1h | 0/10 | 0.68 | $-170.8% | 37.0% | 495 | **REJECT** |

---

## 2. Análise Detalhada dos Pares das Estratégias Vencedoras

### Família: Reversão à Média Bollinger Bands + RSI
| Moeda | Profit Factor | Lucro Líq. % | PnL ($) | Max DD % | Win Rate % | Trades | Status |
|---|---|---|---|---|---|---|---|
| SOL | 0.00 | -0.1% | $-0.13 | 0.1% | 0.0% | 1 | ⚠️ OBSERVAÇÃO |
| BTC | 0.00 | +0.0% | $+0.00 | 0.0% | 0.0% | 0 | ⚠️ OBSERVAÇÃO |
| ETH | 99.00 | +0.7% | $+0.72 | 0.1% | 100.0% | 1 | ✅ APROVADA |
| AVAX | 99.00 | +0.5% | $+0.50 | 0.1% | 100.0% | 2 | ✅ APROVADA |
| SUI | 0.00 | +0.0% | $+0.00 | 0.0% | 0.0% | 0 | ⚠️ OBSERVAÇÃO |
| DOGE | 0.00 | +0.0% | $+0.00 | 0.0% | 0.0% | 0 | ⚠️ OBSERVAÇÃO |
| NEAR | 99.00 | +0.2% | $+0.16 | 0.1% | 100.0% | 1 | ✅ APROVADA |
| LINK | 0.00 | +0.0% | $+0.00 | 0.0% | 0.0% | 0 | ⚠️ OBSERVAÇÃO |
| ARB | 99.00 | +2.6% | $+2.64 | 0.1% | 100.0% | 1 | ✅ APROVADA |
| OP | 0.00 | +0.0% | $+0.00 | 0.0% | 0.0% | 0 | ⚠️ OBSERVAÇÃO |

