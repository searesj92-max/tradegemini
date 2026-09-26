# Quickstart

## 1. Instalar Hermes (Windows / PowerShell)

```powershell
iex (irm https://hermes-agent.nousresearch.com/install.ps1)
hermes doctor
```

## 2. Setup + provider

No chat do Hermes: siga `COMANDOS-HERMES.md` Bloco 1 (ou rode `hermes setup`).

## 3. Instalar Trader Dev MCP

No chat do Hermes (Bloco 2) ou via config do Hermes:

```text
MCP server "trader-dev", transporte streamable HTTP, URL https://mcp.trader.dev/mcp?key=<PK_TOKEN>
```

## 4. Onboarding

Cole no chat:

```text
Read C:\Users\seares\Desktop\botrade\SKILL.md and C:\Users\seares\Desktop\botrade\WORKBOOK.md
and help me build the AI hedge fund desk using Trader Dev MCP.
Confirm trader-dev is connected (whoami + get_credits + tools/list).
```

## 5. Primeiro backtest

```text
Backtest a simple EMA 20/50 crossover strategy on BTCUSDT 1h using trader-dev.
Report profit factor, max drawdown, win rate. Reject overfit results.
```

## 6. Escolher modo de pesquisa

- Estratégia nova: `skills/quant-mathematician/SKILL.md` (researcher)
- Mean reversion: `skills/mean-reversion-engineer/SKILL.md`
- Melhorar existente: `skills/strategy-optimizer/SKILL.md` (optimizer)
- Sizing: `skills/position-optimizer/SKILL.md`

## 7. Ler o relatório

Procure: robustez entre pares/TFs, max DD, profit factor, média por trade, nº de trades, se um trade outlier explica o resultado.

## 8. Ativar loops

`COMANDOS-HERMES.md` Bloco 9 (crons 15/15/15/30/60).

## 9. Incubação

Depois de `Candidate`: `COMANDOS-HERMES.md` Bloco 11.
