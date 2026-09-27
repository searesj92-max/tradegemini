# Trader Dev Research Report — Multi-Pair Robustness Matrix

**Data**: 2026-09-27 15:40 UTC
**Universo**: Top 10 Hyperliquid Perps (BTC, ETH, SOL, AVAX, SUI, DOGE, NEAR, LINK, ARB, OP)
**Capital por Posição**: $20.00 USDC @ 10x | **Custos**: Taker 0.035% + Slippage 0.05%
**Blindagem**: SL Dinâmico ATR + Ratchet Breakeven (+30% ROE)

---

## 1. Veredito Executivo das Famílias Multi-Par

| Estratégia / Família | TF | Pares Positivos | PF Agregado | PnL Total ($) | Win Rate % | Trades | Veredito Gertrude |
|---|---|---|---|---|---|---|---|
| **Dual-Engine Sniper (Pullback + Confluência)** | 1h | 0/10 | 0.00 | $0.0% | 0.0% | 0 | **REJECT** |
| **Pullback Macro Institucional (EMA200 + RSI)** | 2h | 0/10 | 0.00 | $0.0% | 0.0% | 0 | **REJECT** |
| **Confluência Donchian Breakout + Volume** | 1h | 0/6 | 0.00 | $0.0% | 0.0% | 0 | **REJECT** |
| **Reversão à Média Bollinger Bands + RSI** | 1h | 0/9 | 0.00 | $0.0% | 0.0% | 0 | **REJECT** |

---

## 2. Análise Detalhada dos Pares das Estratégias Vencedoras

