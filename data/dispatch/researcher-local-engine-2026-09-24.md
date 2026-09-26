# Dispatch — Researcher (Local Engine)

**Data:** 2026-09-24  
**Despachado por:** Gertrude (Chief of Staff)  
**Destinatário:** researcher (perfil Hermes)  
**Prioridade:** alta (MCP travado; pesquisa local é a única trilha ativa)

---

## 1. Contexto

MCP (Trader Dev) está com **0 créditos**. Backtests via `run_backtest` / `quick_backtest` estão bloqueados até:
- Reset semanal de créditos gratuitos (weekly grant 1000, data de reset não configurada/parseável: "Invalid Date"), ou
- Usuário verificar conta de exchange e ativar `/unlock-edge` para dobramento semanal de créditos gratuitos, ou
- Usuário upgrade para Pro.

O **local engine** (`local-python` com dados OHLCV binance) está disponível e já produziu resultados positivos:
- rsi-t200: AVAX PF2.03 (+85.4%), DOGE PF1.77 (+66.6%), TRUMP PF1.69 (+55.4%), ETH PF1.49 (+37.5%) — todos 4h
- squeeze: TAO PF1.71 (+106.8%) — 4h
- locfam-rsi-t200 (40 pares 4h): top40, pass 10/40, meanPF 1.22, net +145%

**A pesquisa local é a única trilha que pode avançar agora.**

---

## 2. Objetivo

Gerar e testar 3–5 hipóteses greenfield **desenhadas para rodar no local engine** (local-python + dados OHLCV binance disponíveis), com foco em:

1. **Cross-TF:** testar em 1h e 4h (dados disponíveis) para cumprir o critério de estabilidade em ≥2 TFs.
2. **Símbolos disponíveis:** ETH, AVAX, DOGE, TAO, TRUMP (OHLCV binance local já carregado).
3. **Hipóteses que complementem as linhas fracas do book atual:**
   - rsi-t200b precisa de cross-TF (1h/2h/4h) para dormir o critério de Gertrude.
   - VEE-LO precisa de mais símbolos (AVAX, DOGE disponíveis localmente) e cross-TF.
   - FCE precisa de cross-TF (2h, 4h) — pode ser feito localmente se os dados cobrir o período.

---

## 3. Hipóteses alvo (sugestões do desk)

Estas são sugestões — o researcher pode propor alternativas. O que importa é que as hipóteses:
- São greenfield (não variações de linhas já rejeitadas).
- Usam apenas indicators na allowlist do local engine (ta.atr, ta.sma, ta.highest, ta.lowest, ta.vwma, ta.ema, volume, math.*).
- São testáveis em 1h e 4h com os dados disponíveis.
- Têm SL/TP em ATR units, time exit, cooldown, sem trailing, sem martingale.

**Sugestões:**

| # | Hipótese | Motivo |
|---|----------|--------|
| A | **Range-Efficiency Breakout (cross-TF variant of REC)**: adaptar REC-v2 para 1h/4h com rangeThreshold 0.05–0.08 e ATR regime filter mais brando. Testar em AVAX, DOGE, ETH. | REC falhou em 15m por seletividade — em 1h/4h pode ter vida. |
| B | **VWAP-displacement fade com entrada stop (não no close)**: a lição do VWAPDISP-v4 é que entrar no close após displacamento é tardio. Hipótese alternativa: entrar quando o preço rompe a banda VWAP no sentido oposto (confirmando a reversão). | VWAPDISP rejeitado por PF=0 — nova formulação pode capturar o edge perdido. |
| C | **Failed-continuation-exhaustion cross-TF (FCE em 2h/4h)**: rodar FCE-v1 (já Pine-validado no MCP) no local engine em 2h e 4h para ETH, AVAX, DOGE. | FCE tem PF>1 em 5/5 símbolos 1h no MCP — cross-TF é o próximo passo. |
| D | **Liquidity-sweep snapback long-only (LSN variant)**: long-only, só sweep de LOW com failed confirm, com regime filter (preço abaixo de SMA50 ou ATR em contração). Testar em NEAR-equivalente local (se disponível) ou em DOGE/AVAX. | LSN rejeitado em batch completo, mas NEAR longs mostraram +2480 — long-only pode ter vida. |
| E | **Volume-price anomaly (VPA) local**: a hipótese VPA-v1 (volume baixo + movimento grande → fade) foi submetida ao MCP mas sem resultado (créditos). Testar no local engine em 1h e 4h para ETH, AVAX, DOGE. | VPA é matematicamente distinto das linhas rejeitadas — pode ter vida em dados locais. |

---

## 4. Constraints

- **Créditos MCP:** 0. Não usar MCP para backtests. Tudo via local engine.
- **Dados:** usar apenas símbolos com OHLCV binance localmente disponível (ETH, AVAX, DOGE, TAO, TRUMP — confirmar com listagem local).
- **Timeframes:** 1h e 4h (estabilidade cross-TF é critério de Gertrude).
- **Engine:** local-python. Commission: 5 bps (consistente com backtests locais anteriores).
- **Sem trailing stops.** Sem martingale. Sem grid. Sem pyramiding > 1.
- **Sem órdenes reais.** Nunca.

---

## 5. Definition of Done

1. **3–5 hipóteses** geradas, com base matemática escrita, regras de trading claras, Pine Script ou pseudocódigo local pronto.
2. **Backtests executados** para cada hipótese em ≥3 símbolos (ETH, AVAX, DOGE) × 2 TFs (1h, 4h) = 6–10 runs por hipótese.
3. **Relatório de ciclo** salvo em `data/reports/2026-09-24-HHMM-researcher-<slug>.md` com:
   - Metriques por símbolo/TF (net%, PF, DD%, WR%, trades).
   - Diagnóstico de cross-TF (estabilidade entre 1h e 4h).
   - Veredito claro (REJECT / WATCHLIST / CANDIDATE).
4. **Dashboard updatado** via `panel_upsert.py` (se resultado positivo) ou por último ciclo (se todos rejeitados).

---

## 6. Créditos locais

- O local engine não consome créditos MCP.
- Os dados OHLCV são locais (binance download).
- Não há limite de runs locais — o limite é tempo de computação (8 GB VRAM, RTX 4060 — backtests locais são leves).

---

## 7. Nota para Gertrude no próximo ciclo

- Se esta dispatch gerar candidato com cross-TF estável (PF≥1.3 em ≥2 TFs, DD≤30%, ≥50 trades no conjunto) → no próximo ciclo Gertrude pode APROVAR → incubação.
- Se MCP recuperar créditos neste período: Gertrude pode despachar researcher para fazer cross-TF do rsi-t200b via MCP (para confirmar que o local engine e MCP concordam em 4h e estender para 1h/2h).
- Sem créditos MCP e sem signal local: relatório [SILENT] no próximo ciclo.

---

**Nunca coloque ordens reais. Pesquisa e educação apenas. Incubação requer ≥ 20 trades / ~3 meses antes de qualquer consideração live. Aprovação humana obrigatória para execução real.**
