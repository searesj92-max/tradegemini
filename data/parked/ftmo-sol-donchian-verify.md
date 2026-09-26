# Gertrude Decision — FTMO Guardrailed SOL Donchian Breakout (verify)

Date: 2026-09-24
Report source: data/reports/2026-09-24-1618-optimizer-ftmo-sol-donchian.md
Metrics (verified / not verified): NÃO VERIFICADO — métricas originais do leaderboard (PF 12.96, DD 0.59%, 1374 trades, WR 82%) não foram reproduzidas por falta de crédits. Fork bloqueado (free tier não permite fork).
Verdict: ESTACIONAR
Rationale: Estratégia com sinais de vida extremos no leaderboard (PF 12.96, DD < 1%, 1374 trades) — estruturalmente interessante: Donchian breakout + 200 SMA filter + vol expansion + ATR trail 0.03 + hard SL 1.5 ATR + FTMO daily/max-loss halts. Transparente, sem repaint/lookahead. Porém: (1) métricas não foram reproduzidas neste ciclo; (2) único par (SOL 15m) — insuficiente para robustez; (3) fork bloqueado pelo tier free. Não pode classificar como APROVAR sem reprodução independente e multi-par.
Next step: Prioridade alta quando crédits retornarem: (1) reproduzir baseline no mesmo window (2025-02-25 → 2026-01-24) para sanity check; (2) variar trail de 0.03 → 0.05 ATR (single change); (3) estender para ETH/BTC em 15m/30m/1h. Comparar via compare_backtests.
Human required: no (aguardar crédits; ação humana opcional: verificar se account tier pode ser upgradado ou se exchange verification libera crédits grátis)
