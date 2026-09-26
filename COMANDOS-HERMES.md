# COMANDOS-HERMES — cole isto no Hermes Agent Desktop
> **STATUS (2026-09-24 15:00):** Desk OK. MCP + 4 profiles + 5 crons. Gateway researcher ON. **Telegram live** (`@Trade_seabot`, `upstage/solar-pro4`, painel `http://192.168.18.12:8765/`, `scripts/send_telegram.py`). **Aba ANÁLISE no painel** (equity+zonas DD, underwater, mensal, stats, trades, Monte Carlo 500 — `scripts/export_analysis.py`, 564 cards). **Painel restaurado 727 rows** (researcher ciclo 06 sobrescreveu `data.json` com 8 rows; recuperado de `data.js` via `scripts/restore_data_json.py`; blindagem: **`scripts/panel_upsert.py` é o único caminho de update** — loop/01/02/06 + AGENTS.md dos 3 perfis atualizados). Free stack: top40 · 31 Candidate + 10 Incubate · 287 net>0. **Cross-TF rsi-t200b**: MIXED (1h 0/8 · 2h 3/8 · 4h 8/8). **MCP verify SL 1.8/TP 1.5**: soft 8/8 · strict 6/8 · MCP_CONFIRMED — ainda **ESTACIONAR**. **Créditos 37 — só verificação**. TxFlow: `docs/TXFLOW.md`.

> Ordem importa. Execute bloco por bloco. Depois de cada bloco, confirme a saída antes de seguir.

---

## BLOCO 0 — Instalar Hermes (PowerShell, uma vez)

Abra **PowerShell** e cole:

```powershell
iex (irm https://hermes-agent.nousresearch.com/install.ps1)
```

Depois reinicie o terminal e valide:

```powershell
hermes --version
hermes doctor
```

---

## BLOCO 1 — Setup inicial (cole no chat do Hermes)

Cole exatamente isto no chat do Hermes (`hermes` ou Desktop):

```text
Rode o wizard de setup completo (hermes setup). Quero:
- Provider: OpenRouter (ou o que eu indicar)
- Model padrão: um modelo barato para volume (ex: gpt-5 mini / llama) e me avise quando terminar para eu trocar o modelo forte só nos profiles gertrude e builder.
- Toolsets: terminal, files, web, MCP, cron, delegate.
- Depois rode hermes tools e me liste o que ficou ativo.
```

---

## BLOCO 2 — MCP do Trader Dev (backtest)

Ainda no chat do Hermes:

```text
Adicione o MCP server Trader Dev neste projeto com transporte streamable HTTP:

URL: https://mcp.trader.dev/mcp?key=<PK_TOKEN>
nome: trader-dev

Depois liste as tools do trader-dev com tools/list e me mostre:
- whoami
- get_credits
- as tools de backtest: run_backtest, quick_backtest, optimize_strategy, compare_backtests, create_strategy, fork_strategy, search_strategies

Não chame nenhuma tool de escrita ainda, só confirme disponibilidade e autenticação.
```

Se o Hermes pedir comando shell equivalente, confirme com ele que o caminho é o MCP remoto streamable HTTP acima (hermes mcp add trader-dev --url https://mcp.trader.dev/mcp?key=<PK_TOKEN>).

---

## BLOCO 3 — Workspace do projeto

```text
Use o diretório de trabalho C:\Users\seares\Desktop\botrade para toda esta sessão.
Leia os arquivos:
- SKILL.md
- PLANO.md
- WORKBOOK.md
- agents\gertrude\AGENTS.md
- agents\researcher\AGENTS.md
- agents\builder\AGENTS.md
- agents\optimizer\AGENTS.md

Crie as pastas de dados se não existirem:
- data\reports
- data\approvals
- data\parked
- data\rejected
- data\dispatch
- data\incubation
- dashboard

Confirme que entende o pipeline: researcher/builder/optimizer escrevem relatórios; gertrude aprova ou estaciona; nada de ordem real.
```

---

## BLOCO 4 — Profiles dos 4 bots (uma vez)

```text
Crie 4 profiles Hermes isolados (HERMES_HOME próprio, skills e cron próprios):

1. gertrude  — leia agents\gertrude\SOUL.md e agents\gertrude\AGENTS.md
2. researcher — leia agents\researcher\SOUL.md e agents\researcher\AGENTS.md
3. builder    — leia agents\builder\SOUL.md e agents\builder\AGENTS.md
4. optimizer  — leia agents\optimizer\SOUL.md e agents\optimizer\AGENTS.md

Para cada profile:
- Copie o SOUL.md como personalidade
- Copie o AGENTS.md como playbook (regras + roteamento de tools)
- Garanta que o MCP trader-dev está disponível nesse profile
- Não plugar gateway de mensagens em todos (o gateway fica só em gertrude e default)

Confirme com: hermes -p gertrude config get ; idem para os outros.
```

---

## BLOCO 5 — Gateway Telegram (controle remoto)

Primeiro crie o bot com **@BotFather** no Telegram e copie o token. Depois:

```text
Configure o gateway Telegram apenas no profile gertrude com este token: <SEU_TOKEN>
Rode hermes -p gertrude gateway setup e hermes -p gertrude gateway start.
No Telegram, me mande /start no bot e depois /sethome neste chat.
Confirme com hermes -p gertrude gateway status.
```

(No vídeo ele também liga WhatsApp — opcional: `hermes gateway setup` –’ whatsapp, só depois que o Telegram estiver estável.)

---

## BLOCO 6 — ONBOARDING (primeira conversa com o desk)

Cole este prompt (é o WORKBOOK resumido):

```text
Onboarding do trading desk:

1. Confirme trader-dev MCP conectado: chame whoami e get_credits.
2. Rode tools/list do trader-dev e confirme as tools de backtest.
3. Explique em 5 linhas o pipeline: researcher –’ builder/optimizer –’ gertrude (aprova/estaciona) –’ incubação –’ humano.
4. Diga quais métricas você usa para APROVAR (PF–¥1.3, DD–¤30%, –¥50 trades, –¥2 TFs, sem repaint).
5. NO execute backtest ainda. Só confirmação de ambiente.
```

---

## BLOCO 7 — PRIMEIRO BACKTEST (prova de vida)

```text
Backteste uma estratégia simples de média móvel (EMA crossover 20/50) em BTCUSDT no timeframe 1h usando o trader-dev.
Reporte: net profit, profit factor, max drawdown, win rate, trades, e dê veredito honesto (Reject/Watchlist/Incubate/Candidate/Production candidate).
```

---

## BLOCO 8 — PAINEL DE CONTROLE

Cole o prompt de `dashboard/painel-de-controle.md` (ou o resumo):

```text
Construa um painel de controle local em dashboard\index.html (+ dashboard\data.json) para todas as estratégias que você codificar e backtestar em Pine Script.
Cada card deve mostrar: nome, pares, timeframe, status (draft/incubate/candidate/rejected), net profit, profit factor, max drawdown, win rate, trades, data do último backtest, veredito, e botão para copiar o Pine Script.
Inclua filtro por veredito e por win rate. Atualize data.json a cada novo relatório em data\reports\.
```

---

## BLOCO 9 — CRON LOOPS (o coração do vídeo)

Ainda no chat do Hermes (ele cria os cron jobs em linguagem natural):

### Researcher (15 min)

```text
Agende um cron a cada 15 minutos no profile researcher:
"Leia C:\Users\seares\Desktop\botrade\loop\01-quant-mathematician.md e execute um ciclo completo. Escreva o relatório em data\reports\- com timestamp e entregue um resumo de 5 linhas no Telegram."
```

### Builder (15 min)

```text
Agende um cron a cada 15 minutos no profile builder:
"Leia C:\Users\seares\Desktop\botrade\loop\02-builder.md e execute um ciclo: refine o Pine da última hipótese aprovada para draft, rode backtest, atualize dashboard\data.json, escreva relatório em data\reports\."
```

### Optimizer (15 min)

```text
Agende um cron a cada 15 minutos no profile optimizer:
"Leia C:\Users\seares\Desktop\botrade\loop\06-strategy-optimizer.md e execute um ciclo: search_strategies –’ 1 candidato –’ 1 fork –’ 1 mudança –’ backtest multi-par –’ compare_backtests –’ relatório em data\reports\."
```

### Gertrude (30 min)

```text
Agende um cron a cada 30 minutos no profile gertrude:
"Leia C:\Users\seares\Desktop\botrade\loop\00-gertrude-desk-manager.md e execute: varra data\reports\ novos, classifique APROVAR/ESTACIONAR/REJEITAR, escreva em data\approvals\ ou data\parked\, e me mande o resumo no Telegram."
```

### Risk audit (60 min)

```text
Agende um cron a cada 60 minutos no profile gertrude:
"Leia C:\Users\seares\Desktop\botrade\loop\08-risk-manager.md e audite 1 estratégia do book (demote se red flag). Relatório em data\reports\risk\."
```

Liste os jobs com `/cron` ou `hermes -p gertrude cron list` para confirmar.

---

## BLOCO 10 — LOOP CONTNUO (estilo /loop do vídeo)

Se preferir o loop em sessão (como o `/loop 15m` do vídeo), no chat do researcher:

```text
/loop 15m leia C:\Users\seares\Desktop\botrade\loop\01-quant-mathematician.md e execute um ciclo completo, salvando o relatório em data\reports\.
```

---

## BLOCO 11 — INCUBAO (depois de Candidate)

```text
Mova a estratégia <NOME> para incubação:
- Crie data\incubation\<NOME>.md com: data de início, pine, pares, tf, métricas do backtest original.
- Agende um cron diário no profile gertrude: "Re-backteste todas as estratégias em data\incubation\ e anote a curva nova; avise no Telegram quando atingir 20 trades ou 3 meses."
```

---

## BLOCO 12 — GATE DE APROVAO LIVE (etapa humana)

Quando Gertrude marcar `Production candidate` + incubação OK:

```text
Estou pronto para conectar ao TradingView. Gere:
1. O Pine Script final formatado para colar no TradingView (strategy() com SL/TP).
2. As instruções de alerta (message + URL do Trigger.trade).
3. Um checklist humano: confirmar comissões/slippage, tamanho pequeno, sub-account da corretora.
NO ative nada você mesmo — eu executo.
```

---

## Comandos úteis (shell)

```powershell
hermes -p gertrude            # chat do Gertrude
hermes -p researcher          # chat do Researcher
hermes -p builder             # chat do Builder
hermes -p optimizer           # chat do Optimizer
hermes -p gertrude gateway start
hermes -p gertrude cron list
hermes mcp                    # listar MCPs
hermes doctor                 # diagnóstico
```

---

## Checklist de conclusão

- [x] Hermes instalado e `hermes doctor` limpo
- [x] MCP trader-dev conectado (49 tools, streamable HTTP) — `hermes mcp test trader-dev`
- [x] 4 profiles criados com SOUL/AGENTS/skills
- [ ] Telegram do Gertrude (opcional — sem token no ambiente)
- [x] Primeiro backtest BTCUSDT 1h feito (Reject) — data\reports\2026-09-23-1645-researcher-ema20-50-btc1h.md
- [x] Painel de controle em `dashboard/index.html`
- [x] 5 cron jobs ativos (15/15/15/30/60) + gateway rodando
- [x] `data/` populado com os primeiros relatórios
- [x] Nenhuma ordem real colocada
- [x] Discovery batch 144+24 → Mission Control (`dashboard/index.html`)
