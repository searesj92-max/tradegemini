# Relatório de Auditoria e Descarte de Estratégias Inviáveis

**Data da Auditoria**: 2026-09-27 15:39:38 UTC
**Responsável**: Mesa Quantitativa Botrade (Filtro Institucional de Risco & Gertrude)

---

## 1. Sumário Executivo

- **Estratégias Auditadas no Catálogo**: 700
- **Estratégias Descartadas (Arquivadas)**: 488 (69.7%)
- **Estratégias Mantidas (Base Positiva)**: 212 (30.3%)

### Motivos de Descarte (Critérios Rígidos de Hedge Fund):

- 📉 **Lucro Líquido Negativo / Sangria de Taxas**: 319 ocorrências
- ⚠️ **Profit Factor Inferior a 1.10 (Sem Borda Estatística)**: 355 ocorrências
- 🛑 **Veredito de Rejeição Gertrude**: 282 ocorrências
- 🌊 **Drawdown Excessivo (> 35%)**: 268 ocorrências
- 🔬 **Amostragem Insuficiente (< 5 trades)**: 103 ocorrências

---

## 2. Diagnóstico Técnico dos Principais Erros das Estratégias Descartadas

1. **Falta de Borda com Taxas e Slippage**: Estratégias de scalping e cruzamentos de médias curtas (ex: EMA 9/21 sem filtro de volatilidade) sofrem sangria acelerada pelas taxas de taker (0.035%) da Hyperliquid.
2. **Overfitting de Moeda Única (One-Pair Wonders)**: Modelos que mostravam lucro isolado em 1 altcoin de baixa liquidez, mas geravam prejuízo massivo em BTC, ETH ou SOL.
3. **Falta de Stop Loss Dinâmico ou Ratchet**: Estratégias que acumulavam lucros pequenos e devolviam tudo em uma única perna direcional de mercado contra a posição.

---

## 3. Amostra de Estratégias Arquivadas (Top 25 Piores Resultados Descartados)

| ID / Nome | Par | TF | Profit Factor | Lucro Líq. % | Max DD % | Motivo Principal |
|---|---|---|---|---|---|---|
| `loc-ema9-21-PENGU-4h` | PENGUUSDT | 4h | 0.77 | -81.9% | 88.5% | Lucro Líquido Negativo ou Nulo; Profit Factor Inviável (0.77 < 1.10); Classificado como REJEITADO pela Chief of Staff (Gertrude); Drawdown Inaceitável (88.5% > 35%) |
| `loc-ema20-50-ENA-4h` | ENAUSDT | 4h | 0.60 | -78.6% | 81.2% | Lucro Líquido Negativo ou Nulo; Profit Factor Inviável (0.60 < 1.10); Classificado como REJEITADO pela Chief of Staff (Gertrude); Drawdown Inaceitável (81.2% > 35%) |
| `loc-hh-brk-ZRO-4h` | ZROUSDT | 4h | 0.69 | -75.3% | 81.5% | Lucro Líquido Negativo ou Nulo; Profit Factor Inviável (0.69 < 1.10); Classificado como REJEITADO pela Chief of Staff (Gertrude); Drawdown Inaceitável (81.5% > 35%) |
| `loc-hh-brk-BCH-4h` | BCHUSDT | 4h | 0.53 | -75.1% | 76.9% | Lucro Líquido Negativo ou Nulo; Profit Factor Inviável (0.53 < 1.10); Classificado como REJEITADO pela Chief of Staff (Gertrude); Drawdown Inaceitável (76.9% > 35%) |
| `loc-hh-brk-AVAX-4h` | AVAXUSDT | 4h | 0.52 | -75.0% | 78.8% | Lucro Líquido Negativo ou Nulo; Profit Factor Inviável (0.52 < 1.10); Classificado como REJEITADO pela Chief of Staff (Gertrude); Drawdown Inaceitável (78.8% > 35%) |
| `ethusdt-1h-1467` | 1h | 1467 | 0.47 | -74.7% | 75.0% | Lucro Líquido Negativo ou Nulo; Profit Factor Inviável (0.47 < 1.10); Drawdown Inaceitável (75.0% > 35%); Amostragem Insuficiente (-5 trades) |
| `btcusdt-1h-1093` | 1h | 1093 | 0.43 | -71.9% | 72.3% | Lucro Líquido Negativo ou Nulo; Profit Factor Inviável (0.43 < 1.10); Drawdown Inaceitável (72.3% > 35%); Amostragem Insuficiente (-6 trades) |
| `loc-hh-brk-LINK-4h` | LINKUSDT | 4h | 0.62 | -71.0% | 77.7% | Lucro Líquido Negativo ou Nulo; Profit Factor Inviável (0.62 < 1.10); Classificado como REJEITADO pela Chief of Staff (Gertrude); Drawdown Inaceitável (77.7% > 35%) |
| `loc-hh-brk-ENA-4h` | ENAUSDT | 4h | 0.76 | -70.6% | 73.8% | Lucro Líquido Negativo ou Nulo; Profit Factor Inviável (0.76 < 1.10); Classificado como REJEITADO pela Chief of Staff (Gertrude); Drawdown Inaceitável (73.8% > 35%) |
| `loc-ema20-50-MUBARAK-4h` | MUBARAKUSDT | 4h | 0.81 | -67.6% | 86.4% | Lucro Líquido Negativo ou Nulo; Profit Factor Inviável (0.81 < 1.10); Classificado como REJEITADO pela Chief of Staff (Gertrude); Drawdown Inaceitável (86.4% > 35%) |
| `loc-hh-brk-XPL-4h` | XPLUSDT | 4h | 0.63 | -67.5% | 68.4% | Lucro Líquido Negativo ou Nulo; Profit Factor Inviável (0.63 < 1.10); Classificado como REJEITADO pela Chief of Staff (Gertrude); Drawdown Inaceitável (68.4% > 35%) |
| `loc-ema20-50-ONDO-4h` | ONDOUSDT | 4h | 0.64 | -65.3% | 79.5% | Lucro Líquido Negativo ou Nulo; Profit Factor Inviável (0.64 < 1.10); Classificado como REJEITADO pela Chief of Staff (Gertrude); Drawdown Inaceitável (79.5% > 35%) |
| `loc-dc-long-ZRO-4h` | ZROUSDT | 4h | 0.79 | -65.1% | 74.5% | Lucro Líquido Negativo ou Nulo; Profit Factor Inviável (0.79 < 1.10); Classificado como REJEITADO pela Chief of Staff (Gertrude); Drawdown Inaceitável (74.5% > 35%) |
| `xrpusdt-1h-1600` | 1h | 1600 | 0.62 | -65.0% | 66.3% | Lucro Líquido Negativo ou Nulo; Profit Factor Inviável (0.62 < 1.10); Drawdown Inaceitável (66.3% > 35%); Amostragem Insuficiente (-4 trades) |
| `loc-ema9-21-ZEC-4h` | ZECUSDT | 4h | 0.92 | -64.1% | 80.2% | Lucro Líquido Negativo ou Nulo; Profit Factor Inviável (0.92 < 1.10); Classificado como REJEITADO pela Chief of Staff (Gertrude); Drawdown Inaceitável (80.2% > 35%) |
| `loc-dc-long-BCH-4h` | BCHUSDT | 4h | 0.66 | -63.3% | 68.9% | Lucro Líquido Negativo ou Nulo; Profit Factor Inviável (0.66 < 1.10); Classificado como REJEITADO pela Chief of Staff (Gertrude); Drawdown Inaceitável (68.9% > 35%) |
| `loc-ema20-50-NEAR-4h` | NEARUSDT | 4h | 0.72 | -63.1% | 68.8% | Lucro Líquido Negativo ou Nulo; Profit Factor Inviável (0.72 < 1.10); Classificado como REJEITADO pela Chief of Staff (Gertrude); Drawdown Inaceitável (68.8% > 35%) |
| `loc-dc-long-ONDO-4h` | ONDOUSDT | 4h | 0.67 | -63.0% | 65.9% | Lucro Líquido Negativo ou Nulo; Profit Factor Inviável (0.67 < 1.10); Classificado como REJEITADO pela Chief of Staff (Gertrude); Drawdown Inaceitável (65.9% > 35%) |
| `loc-ema9-21-AVAX-4h` | AVAXUSDT | 4h | 0.78 | -62.4% | 81.1% | Lucro Líquido Negativo ou Nulo; Profit Factor Inviável (0.78 < 1.10); Classificado como REJEITADO pela Chief of Staff (Gertrude); Drawdown Inaceitável (81.1% > 35%) |
| `loc-ema9-21-NEAR-4h` | NEARUSDT | 4h | 0.84 | -62.1% | 70.9% | Lucro Líquido Negativo ou Nulo; Profit Factor Inviável (0.84 < 1.10); Classificado como REJEITADO pela Chief of Staff (Gertrude); Drawdown Inaceitável (70.9% > 35%) |
| `adausdt-1h-1590` | 1h | 1590 | 0.74 | -61.9% | 63.3% | Lucro Líquido Negativo ou Nulo; Profit Factor Inviável (0.74 < 1.10); Drawdown Inaceitável (63.3% > 35%); Amostragem Insuficiente (-3 trades) |
| `loc-hh-brk-AAVE-4h` | AAVEUSDT | 4h | 0.77 | -56.1% | 62.4% | Lucro Líquido Negativo ou Nulo; Profit Factor Inviável (0.77 < 1.10); Classificado como REJEITADO pela Chief of Staff (Gertrude); Drawdown Inaceitável (62.4% > 35%) |
| `loc-ema20-50-PENGU-4h` | PENGUUSDT | 4h | 0.81 | -56.0% | 66.0% | Lucro Líquido Negativo ou Nulo; Profit Factor Inviável (0.81 < 1.10); Classificado como REJEITADO pela Chief of Staff (Gertrude); Drawdown Inaceitável (66.0% > 35%) |
| `loc-hh-brk-ONDO-4h` | ONDOUSDT | 4h | 0.74 | -55.9% | 65.7% | Lucro Líquido Negativo ou Nulo; Profit Factor Inviável (0.74 < 1.10); Classificado como REJEITADO pela Chief of Staff (Gertrude); Drawdown Inaceitável (65.7% > 35%) |
| `loc-dc-long-AAVE-4h` | AAVEUSDT | 4h | 0.77 | -55.0% | 66.7% | Lucro Líquido Negativo ou Nulo; Profit Factor Inviável (0.77 < 1.10); Classificado como REJEITADO pela Chief of Staff (Gertrude); Drawdown Inaceitável (66.7% > 35%) |
