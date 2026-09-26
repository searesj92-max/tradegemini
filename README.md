# botrade — AI Trading Desk no Hermes Agent

Réplica funcional do projeto do vídeo **"I Built an INSANELY Profitable AI Trading Bot for FREE (Full Guide)"** (Trading with DaviddTech, 21/09/2026), adaptado para rodar com **Hermes Agent Desktop** no Windows.

## O que é

Um **trading desk multi-agente autônomo** que roda 24/7 dentro do Hermes Agent:

- **Gertrude** (Chief of Staff) — aprova ou estaciona estratégias, despacha trabalho
- **Researcher** — gera hipóteses matemáticas novas e codifica em Pine Script
- **Builder** — constrói e refina estratégias, gera o painel de controle
- **Optimizer** — faz fork, otimiza parâmetros, compara contra baseline

Eles se comunicam por arquivos no workspace, rodam em **cron loops** (a cada 15 min) e usam o **Trader Dev MCP** para backtest em dados de TradingView sem estourar rate limit.

## Fluxo (igual ao vídeo)

```
Researcher (cron 15m) ──hipótese+Pine──▶ Trader Dev MCP (backtest)
        │                                        │
        ▼                                        ▼
   Builder (cron 15m) ◀──resultados──── painel de controle (dashboard)
        │
        ▼
   Gertrude (cron 30m) ──APROVA / ESTACIONA──▶ incubação (20 trades / ~3 meses)
        │
        ▼
   Optimizer (cron 15m) ──fork+sweep──▶ variantes comparadas
        │
        ▼
   Aprovadas → TradingView + Trigger.trade → corretora (humano confirma)
```

## Ferramentas (idênticas ao vídeo)

| Camada | Ferramenta |
|---|---|
| Agente | Hermes Agent (Nous Research) — Desktop/CLI no Windows |
| Modelos | OpenAI (GPT-5.x), Anthropic Claude, OpenRouter — baratos para chatter, fortes para raciocínio |
| Backtest | Trader Dev MCP (`https://mcp.trader.dev/mcp?key=<PK_TOKEN>`) |
| Linguagem | Pine Script (TradingView) |
| Controle remoto | Telegram / WhatsApp via Hermes Gateway |
| Execução live | TradingView alerts → Trigger.trade → corretora (etapa manual/approval) |
| Agendamento | Hermes cron (loops a cada 15/30/60 min) |
| Persistência | `data/` (estratégias, relatórios, aprovações) + Trader Dev |

## Estrutura

```
botrade/
├── README.md                 # este arquivo
├── PLANO.md                  # planejamento completo (arquitetura, regras, cron)
├── COMANDOS-HERMES.md        # COMANDOS para colar no Hermes Desktop
├── SKILL.md                  # skill principal de entrada (rooteador)
├── WORKBOOK.md               # setup guiado passo-a-passo para o agente
├── agents/                   # os 4 bots com SOUL + AGENTS
│   ├── gertrude/             # chief of staff
│   ├── researcher/           # cria estratégias novas
│   ├── builder/              # constrói Pine + painel
│   └── optimizer/            # otimiza parâmetros
├── prompts/                  # prompts copy-paste (versões do vídeo)
├── loop/                     # arquivos de loop 15m por papel
├── skills/                   # skills especialistas (quant, MR, optimizer…)
├── scripts/                  # mcp_client + run_discovery (batch de backtests)
├── dashboard/                # Mission Control (index.html + data.json/data.js)
└── docs/                     # quickstart, guia do agente, disclaimer
```

## Mission Control

Abra `dashboard/index.html` no navegador. Painel completo:

- **Family rollups** (pass/16, mean PF/WR, W/L) + **cards** com net%, PF, MDD, **barra WIN vs LOSS** (wins/losses), trades, expectancy, sharpe, long/short, sparkline
- Filtros: verdict, família, agente, par, TF, origem, **WR≥ / DD≤ / PF≥ / N≥**, sort (PF/WR/net/DD/trades/pass), busca, copy pine
- Fonte de dados: `dashboard/data.json` + `data.js` (merge por `id` — use `scripts/rebuild_dashboard.py` para reconstruir a partir dos relatórios)

Atualizar o lote (queima créditos — baixa frequência; confira `get_credits`):

```powershell
$py = "$env:LOCALAPPDATA\hermes\hermes-agent\venv\Scripts\python.exe"
& $py C:\Users\seares\Desktop\botrade\scripts\run_discovery.py
& $py C:\Users\seares\Desktop\botrade\scripts\run_high_wr.py
& $py C:\Users\seares\Desktop\botrade\scripts\run_notrail_fork.py
& $py C:\Users\seares\Desktop\botrade\scripts\run_batch3.py
& $py C:\Users\seares\Desktop\botrade\scripts\run_batch4_bull.py
# reconstrói painel a partir de relatórios + rows vivos (sem gastar crédito)
& $py C:\Users\seares\Desktop\botrade\scripts\rebuild_dashboard.py
```

### Fluxo free (recomendado — 0 créditos)

```powershell
$py = "$env:LOCALAPPDATA\hermes\hermes-agent\venv\Scripts\python.exe"
& $py C:\Users\seares\Desktop\botrade\scripts\top_universe.py   # top40 Bybit+Binance
& $py C:\Users\seares\Desktop\botrade\scripts\run_local_top40.py # 480 combos locais
& $py C:\Users\seares\Desktop\botrade\scripts\merge_local_dashboard.py
```

- Engine local: `scripts/local_engine.py` (klines cache `data/ohlcv/`, comissão 5bps/lado, conservador).
- Só sobreviventes locais vão para Trader Dev (`quick_backtest` ~1 crédito/linha).
- Detalhes e política de créditos: `docs/FREE-DATA.md`.
- Top40 local: `data/reports/2026-09-23-1944-local-top40.md` — **rsi-t200 10/40 pares**; rows locais no painel (fonte `local-ohlcv`).

Relatórios: `data/reports/*-discovery-batch.md`, `*-high-wr-batch.md`, `*-notrail-fork.md`, `*-batch3*.md`, `*-batch4*.md`, `*-local-top40.md`.  
Síntese high-WR: `2026-09-23-1820-researcher-high-wr-synthesis.md`.  
Batch4 bull/low-risk: `2026-09-23-1923-researcher-batch4-synthesis.md`.  
TxFlow DEX (research): `docs/TXFLOW.md` — API pública “coming soon”; testnet `txflow-testnet.xyz`.  
Free data/stack: `docs/FREE-DATA.md`.

## Início rápido

1. Siga `COMANDOS-HERMES.md` (instala Hermes + MCP + profiles + gateway).
2. Cole o prompt de onboarding do `WORKBOOK.md` no chat do Hermes.
3. Ative os loops: `COMANDOS-HERMES.md` → seção "Cron loops".
4. Gertrude começa a despachar; relatórios chegam no `data/reports/` e no Telegram.

## Aviso

Somente pesquisa e educação. Não coloca ordens reais. Backtest não garante resultado futuro. Antes de qualquer capital real: incubação (forward test) ≥ 20 trades / ~3 meses e aprovação humana.

## Créditos

- Método e prompts base: [DaviddTech/ai-trading-agent](https://github.com/DaviddTech/ai-trading-agent) (MIT)
- Vídeo: https://www.youtube.com/watch?v=V690IKm5G5k
- Agente: [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent)
