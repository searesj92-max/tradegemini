# Loop Roles — o desk 24/7 (adaptado para Hermes)

No vídeo original (Claude Code) usa-se `/loop 15m read loop/XX.md`. No **Hermes**, o equivalente é um **cron job em linguagem natural** por profile (ver `COMANDOS-HERMES.md` Bloco 9).

## Hard rule — somente TradingView-native

Toda estratégia deve ser backtestável em **TradingView com Pine Script e OHLCV**.

**Sem:** funding off-chain · arbitragem cross-exchange · sentimento (Fear&Greed, social) · on-chain Glassnode · options flow · depth de exchange externa.

**Com:** OHLCV (request.security com lookahead_off) · volume · TAs nativas · multi-TF · multi-símbolo (BTC/ETH ratio) · date/time math (sessões, halving, lua) · ATR/vol/range · pivots/swings/Donchian/Bollinger/Keltner.

## Arquivos de loop

| Arquivo | Profile | Intervalo | Papel |
|---|---|---|---|
| `00-gertrude-desk-manager.md` | gertrude | 30m | Survey → aprova/estaciona → despacha → Telegram |
| `01-quant-mathematician.md` | researcher | 15m | Hipóteses greenfield + Pine + backtest |
| `02-builder.md` | builder | 15m | Refina Pine + painel de controle |
| `06-strategy-optimizer.md` | optimizer | 15m | Fork + 1 mudança + compare |
| `08-risk-manager.md` | gertrude | 60m | Auditoria free (red/yellow/green) |

> Os roles 03–05, 07, 09–14 do repo original (trend, vol, breakout, position, drawdown, overfit, MTF, liquidity, moon, pattern) podem ser adicionados depois copiando de `DaviddTech/ai-trading-agent/loop/` (MIT) para esta pasta e agendando no profile correspondente.

## Combinação recomendada (24/7)

| Cadência | Role | Por quê |
|---|---|---|
| 15m | researcher | pipeline de ideias |
| 15m | builder | Pine sempre refinado + painel vivo |
| 15m | optimizer | melhora o book existente |
| 30m | gertrude desk-manager | gate de aprovação |
| 60m | gertrude risk | auditoria barata |
| 6h | overfit detector (futuro) | pega curve-fits |
| diário | incubation re-backtest | forward curve (pink) |

## Disciplina de loop

1. Somente TradingView-native.
2. Cada fire é **independente** — não assuma contexto anterior.
3. Um ciclo produtivo por fire: 1 estratégia, 1 job, 1 relatório.
4. Persistir no Trader Dev (`create_strategy`/`update_strategy`) e em `data/reports/` — não só no chat.
5. Fail fast: sem candidato / MCP errado → reporte e pare.
6. Vereditos honestos: Reject / Watchlist / Incubate / Candidate / Production candidate.
7. **Nenhum loop negocia ao vivo.** Live exige revisão humana.

## Roster de especialistas (repo original, para expandir)

Coordenação: `00` · Criação: `01–05` · Otimização: `06–07` · Risco: `08–10` · Estrutural: `11–12, 14` · Experimental: `13`.
