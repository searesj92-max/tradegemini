# PLANO — Trading Desk multi-agente no Hermes

Planejamento completo baseado no vídeo V690IKm5G5k (DaviddTech) e no repo MIT `DaviddTech/ai-trading-agent`.

---

## 1. Objetivo

Reproduzir o "AI hedge fund desk" do vídeo usando **Hermes Agent Desktop** como orquestrador:

- 4 agentes especializados (profiles Hermes isolados)
- Loops recorrentes (cron) a cada 15–30 minutos
- Backtest via **Trader Dev MCP** (dados TradingView, sem rate-limit/ban)
- Controle remoto por **Telegram/WhatsApp**
- Painel de controle local para acompanhar estratégias
- Pipeline de **incubação** antes de qualquer live

---

## 2. Arquitetura

```
                    ┌─────────────────────────────┐
                    │   Hermes Desktop (Windows)  │
                    │   gateway + cron + MCP      │
                    └──────────────┬──────────────┘
                                   │
        ┌──────────────┬───────────┼───────────┬──────────────┐
        ▼              ▼           ▼           ▼              ▼
   [gertrude]     [researcher]  [builder]  [optimizer]   (default/op)
   Chief of Staff  Hipóteses+   Pine+painel  fork+sweep
   aprova/estaciona  backtest
        │              │           │           │
        └──────────────┴─────┬─────┴───────────┘
                             ▼
                   Trader Dev MCP (SSE)
                   create/backtest/optimize/compare
                             │
                             ▼
                   data/ + Trader Dev cloud
                   (relatórios, curva, trades)
                             │
                             ▼
              Telegram/WhatsApp (relatórios + gate de aprovação)
                             │
              (humano) TradingView + Trigger.trade → corretora
```

### Profiles Hermes (isolamento total)

| Profile | Modelo sugerido | Função | Cron |
|---|---|---|---|
| `gertrude` | Claude / GPT forte (raciocínio) | Chief of Staff: lê relatórios, APROVA ou ESTACIONA, despacha, reporta no Telegram | 30 min |
| `researcher` | GPT barato (volume) | Gera 3–5 hipóteses matemáticas, codifica Pine, backtesta | 15 min |
| `builder` | GPT forte (código) | Refina Pine, mantém painel de controle, exporta scripts | 15 min |
| `optimizer` | GPT barato + MCP optimize | Fork + sweep de parâmetros, compara vs baseline | 15 min |
| `default` | misto | Humano interage, setup, comandos avulsos | — |

**Regra de custo do vídeo:** nunca deixar agentes "conversarem" entre si por tokens caros — comunicação só por arquivos em `data/` + relatórios compactos. Modelo barato para volume; modelo forte só para Gertrude e código crítico.

---

## 3. Papéis e responsabilidades (bots)

### 3.1 Gertrude — Chief of Staff
- Lê `data/reports/*.md` novos desde a última rodada
- Classifica: `APROVAR → incubação` | `ESTACIONAR` | `REJEITAR`
- Critérios de aprovação (do vídeo/repo):
  - Profit factor ≥ 1.3 em ≥ 5 pares
  - Max drawdown ≤ 30%
  - ≥ 50 trades
  - Estável em ≥ 2 timeframes próximos
  - Sem repaint/lookahead
  - Sem SL desativado, sem martingale ilimitado
- Escreve `data/approvals/` + notifica no Telegram
- Despacha próximo papel em `data/dispatch/`

### 3.2 Researcher — cria do zero
- Só hipóteses greenfield (nada de copiar estratégia pronta)
- Workflow: 3–5 hipóteses → escolhe 1 → regras → Pine → `create_strategy` → `run_backtest` 5–10 pares × 15m/30m/1h/2h/4h
- Relatório no formato padrão com veredito

### 3.3 Builder — constrói e documenta
- Pega hipóteses/regras e gera Pine limpo (no-repaint, no-lookahead, SL/TP)
- Mantém o **painel de controle** (`dashboard/`) atualizado com: status, métricas, curva, Pine copiável
- Exporta Pine para colar no TradingView

### 3.4 Optimizer — melhora o que já existe
- `search_strategies` → escolhe candidato com "sinais de vida" → `fork_strategy` → UMA mudança → backtest multi-par/TF → `compare_backtests`
- Veredito: keep / reject / iterate
- Proibido: otimizar para lucro bruto só; esconder drawdown

---

## 4. Regras duras (hard rules)

1. **TradingView-native apenas** — só OHLCV + Pine. Sem funding, on-chain, sentimento off-chain.
2. **Sem repaint, sem lookahead, sem dado futuro.**
3. **SL e TP definidos de entrada** (o vídeo odeia trailing stop — atrasa a ordem e coloca em loss).
4. **Veredito honesto sempre:** Reject / Watchlist / Incubate / Candidate / Production candidate.
5. **Prioridade de métrica:** robustez entre pares > drawdown > profit factor > qualidade do trade > contagem > estabilidade TF > simplicidade > lucro líquido (por último).
6. **Nenhum loop coloca ordem real.** Live só após incubação + aprovação humana.
7. **Incubação obrigatória:** ≥ 20 trades ou ~3 meses de forward test antes de considerar capital real.
8. **1 candidato, 1 mudança, 1 comparação por ciclo** (atribuição de causa).

---

## 5. Pipeline de aprovação (gate)

```
Researcher/Builder/Optimizer → data/reports/
         │
         ▼ (a cada 30m)
Gertrude lê relatórios
         │
   ┌─────┼─────────┬────────────┐
   ▼     ▼         ▼            ▼
APROVAR ESTACIONAR REJEITAR   PERGUNTAR
→ incubação → data/parked/ → data/rejected/ → Telegram (humano)
   │
   ▼ (após 20 trades / 3 meses, re-backtest)
Humano: copia Pine → TradingView → alert → Trigger.trade → corretora
```

Aprovação de qualquer mudança com efeito colateral (promoção a "production candidate", ativação de alert) só via **gate no Telegram** — padrão do vídeo.

---

## 6. Cron (agendamento)

| Job | Profile | Intervalo | Comando-resumo |
|---|---|---|---|
| research-loop | researcher | 15m | lê `loop/01-quant-mathematician.md` e executa |
| build-loop | builder | 15m | lê `loop/02-builder.md` e executa |
| optimize-loop | optimizer | 15m | lê `loop/06-strategy-optimizer.md` e executa |
| desk-manager | gertrude | 30m | lê `loop/00-gertrude-desk-manager.md` e executa |
| risk-audit | gertrude | 60m | lê `loop/08-risk-manager.md` e executa |

Entrega de cada job: `data/reports/` + Telegram home channel.

---

## 7. Ferramentas externas

| Ferramenta | Uso | Onde configurar |
|---|---|---|
| Trader Dev MCP | backtest/optimize Pine em nuvem | `hermes mcp` / config.yaml |
| TradingView | gráficos + alerts finais | manual |
| Trigger.trade | alerta → Telegram/corretora (free, anônimo) | site |
| Telegram BotFather | token do gateway | `hermes gateway setup` |
| OpenAI / Anthropic / OpenRouter | modelos | `hermes model` |

---

## 8. Segurança

- API keys só em `%LOCALAPPDATA%\hermes\.env` (nunca no repo).
- Sem chaves de corretora nos agentes — execução live é etapa humana/Trigger.trade.
- Gate de aprovação humana para qualquer estado "production".
- Disclaimer em `docs/DISCLAIMER.md` — exibir antes de qualquer discussão de deploy.

---

## 9. Entregáveis deste projeto

- [x] Estrutura completa de pastas
- [x] 4 agentes (SOUL.md + AGENTS.md)
- [x] Prompts do vídeo/repo (MIT) em `prompts/`
- [x] Loops 15m em `loop/`
- [x] Skills especialistas em `skills/`
- [x] `COMANDOS-HERMES.md` (colar no Desktop)
- [x] `SKILL.md` + `WORKBOOK.md`
- [x] Prompt do painel de controle em `dashboard/`
- [x] Mission Control implementado (`dashboard/index.html` + `data.json`/`data.js`)
- [x] Discovery batch 144 local + 24 leaderboard → `scripts/run_discovery.py`
- [x] High-WR batch 176 local + leaderboard → `scripts/run_high_wr.py`
- [x] No-trail public forks 96 → `scripts/run_notrail_fork.py` (0 passam no gate)
- [x] Síntese high-WR → `data/reports/2026-09-23-1820-researcher-high-wr-synthesis.md`
- [x] Batch3 expanded 16 ativos × 10 strat → `scripts/run_batch3.py` (rsi-t200b 8/16)
- [x] Docs (quickstart, agent guide, disclaimer)

## 10. Fora de escopo (por enquanto)

- Execução 100% automática sem humano (o vídeo também não faz)
- Forex/stocks (Trader Dev hoje: crypto)
- Otimização por Monte Carlo/walk-forward completo (roadmap)
