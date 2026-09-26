# Painel de controle — prompt do builder

> Prompt do vídeo para construir o control panel. Cole no profile `builder`.
>
> **STATUS (2026-09-24 15:00):** Mission Control **727 rows + aba ANÁLISE** — http://192.168.18.12:8765/ (WiFi local). **Regra de ouro: nunca reescrever `data.json` à mão** — só via `scripts/panel_upsert.py --rows <file>` (merge por `id` + `.bak`). Em 2026-09-24 o researcher sobrescreveu com 8 rows; recuperado com `scripts/restore_data_json.py`. Botão `analisar` em 564 cards: equity c/ zonas DD anotadas, underwater, mensal, stats, trades, Monte Carlo 500 (`scripts/export_analysis.py`, 0 créditos). Free: `docs/FREE-DATA.md`. rsi-t200b: MCP CONFIRMED SL 1.8/1.5 mas cross-TF só 4h → ESTACIONAR. Telegram: `@Trade_seabot` + `scripts/send_telegram.py`. Créditos MCP: **37**.

```text
Build a control panel for all of the strategies that you've successfully coded and backtested in Pine Script.

Location: C:\Users\seares\Desktop\botrade\dashboard\
Files: index.html (single file, no build step) + data.json (source of truth)

Each strategy card must show:
- name, pairs/symbols, timeframe
- status: draft | incubating | incubate | candidate | production candidate | rejected | parked
- net profit, profit factor, max drawdown, win rate, number of trades
- last backtest date
- verdict (Reject / Watchlist / Incubate / Candidate / Production candidate)
- "Copy Pine Script" button (loads from data/pine/<name>.pine or embedded field)

Features:
- filter by verdict/status
- filter by win rate (slider or min input)
- optionally filter by profit factor and max drawdown
- sort by profit factor / win rate / last backtest
- empty state when no strategies yet
- works offline by double-clicking index.html (fetch data.json may be blocked by file:// — embed data as a JS object in index.html AND keep data.json in sync)

Data update flow:
- After every research/builder/optimizer report in data/reports/, refresh the strategy entry in data.json and regenerate the embedded JS data in index.html.
- When I say "atualiza o painel", re-scan data/reports/ and rebuild.

Style: dark theme, dense quant-desk look, monospace numbers, green/red for profit/loss. No external CDN dependencies.
```

## Estrutura esperada de `data.json`

```json
{
  "updated_at": "ISO-8601",
  "strategies": [
    {
      "name": "QM-VOLCOMP-v1",
      "pairs": ["BTCUSDT", "ETHUSDT", "..."],
      "timeframe": "1h",
      "status": "incubate",
      "net_profit": 0,
      "profit_factor": 0,
      "max_drawdown": 0,
      "win_rate": 0,
      "trades": 0,
      "last_backtest": "YYYY-MM-DD",
      "verdict": "Incubate",
      "pine_path": "data/pine/QM-VOLCOMP-v1.pine",
      "report_path": "data/reports/....md"
    }
  ]
}
```
