# Prompt do vídeo — Painel de controle (control panel)

> Prompt original do vídeo: fazer a IA construir um painel para acompanhar todas as estratégias codificadas e backtestadas.

```text
Build a control panel for all of the strategies that you've successfully coded and backtested in Pine Script.

Requirements:
- Store every strategy with: name, symbol/pairs, timeframe, status (draft / incubate / candidate / production candidate / rejected), backtest date.
- For each strategy show the backtest data: net profit, profit factor, max drawdown, win rate, number of trades, average trade.
- Show the equity curve data if available (or a link/placeholder for the curve from Trader Dev).
- Include the Pine Script source for each strategy with a "copy Pine Script" button so I can paste it into TradingView.
- Add filters by status and by win rate (and optionally by profit factor / max drawdown).
- Persist everything to a local JSON file I can inspect, and regenerate the panel from that file.
- When I ask you to "update the panel", re-read my latest research reports and refresh the data.

Build it as a single local HTML file plus a JSON data file in the dashboard folder of this project.
```

**Uso no Hermes:** cole no profile `builder` (primeiro ciclo). Reference: `dashboard/painel-de-controle.md`.
