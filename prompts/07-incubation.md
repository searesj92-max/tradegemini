# Prompt — Incubação (forward test do vídeo)

> A etapa que o vídeo mais enfatiza: nunca confiar no backtest cedo demais.

```text
Put strategy <NOME> into incubation (forward testing):

1. Create data/incubation/<NOME>.md with:
   - start date
   - Pine Script source
   - pairs, timeframe
   - original backtest metrics (net profit, PF, max DD, WR, trades)
   - success criteria: >= 20 trades AND/OR ~3 months forward, PF still >= 1.2, max DD not exceeded, still trading (not dead)
2. Update dashboard status to "incubating".
3. Schedule a DAILY cron on profile gertrude:
   "Re-backtest every strategy in data/incubation/ with Trader Dev, append the new equity point to data/incubation/<name>.md (green = backtest, pink = forward), and notify me on Telegram only if:
    - trades reached >= 20, or
    - 3 months passed, or
    - the strategy stopped trading, or
    - forward metrics degraded badly vs backtest."
4. Never mark incubating → production without my explicit approval after reading the forward curve.
```
