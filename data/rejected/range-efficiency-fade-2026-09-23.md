# Gertrude Decision — range-efficiency fade (QM-RANGE-EFF-FADE, v1–v4)

Date: 2026-09-23
Report source: data/reports/2026-09-23-2154-researcher-range-eff-fade.md · data/reports/2026-09-23-1853-batch3-expanded.md (b3-rangeeff)

Metrics:
- v1 BTC 1h: 0 trades · v2 BTC 1h: 0 trades · v3 BTC 1h: 0 trades · v4 BTC 1h: 0 trades
- b3-rangeeff (4h): 0/16 pares · LINK 5 trades · APT 4 trades · BTC 10 trades · todos PF < 1.5 ou com poucos trades
- 3+ iterações sem ocorrência mínima de trades em BTC 1h; 4 versões testadas, 0 trades em BTC e ETH.

Verdict: **REJEITAR**

Rationale:
- Zero trades nas versões v1–v4 em BTC 1h e ETH 1h → não há dados para afirmar edge ou fragilidade.
- O padrão de "três strikes sem trades" invalida a hipótese nesta forma e neste universo (1h BTC).
- b3-rangeeff em 4h: poucos trades, PF insuficiente, sem robustez — linha também sem sinais de vida.
- Não há SL/TP testado em trades reais → não incubar, não watchlist.
- Hipótese pode ter vida em TF menor ou com confirmação no bar seguinte, mas o loop já investiu 4 versões; pivotar é correto.

Next step: linha abandonada. Proxima hipótese de greenfield lá na área de mean-reversion com regime filter, ou pivotar para EMA-based designs com filtro de regime (já com sinais de vida no book).

Human required: no (decisão de rejeição é automática; próxima rodada via dispatch).
