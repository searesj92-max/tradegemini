# Gertrude Decision — FTMO Guardrailed SOL Donchian Breakout (Optimizer Verify)

Date: 2026-09-24
Report source: data/reports/2026-09-24-1618-optimizer-ftmo-sol-donchian.md
Metrics (verified / not verified): **Not verified** — ciclo incompleto. Backtest não executado (credits = 0). Nenhum número novo para verificar.

Verdict: **ESTACIONAR** → data/parked/

Rationale:
- Candidato original com números gritantes: PF 12.96, DD 0.59%, WR 82%, 1374 trades, net +262% em SOLUSDT 15m — estrutura honesta (Donchian breakout + 200 SMA filter + vol expansion + ATR trail + hard SL 1.5 ATR + FTMO daily/max-loss halts).
- Transparente, sem repaint/lookahead, risco definido antes da entrada, halts de drawdown controlados.
- Hipótese de melhoria clara e de baixo risco: trail de 0.03 ATR → 0.05 ATR ( ONE change). Hard SL preservado.
- Bloqueios infráestrutura: fork bloqueado (403, plano pago) e backtest bloqueado (credits = 0). Recreate da estratégia foi feito (nova ID 01M3ADK4BXZZQVXDF022WPP7J0), mas quick_backtest falhou com "no credits remaining".
- Sem backtest do baseline reproduce nem do modified, não é possível classificar. Nenhum número reportado para não fabricar.

Next step (requer ação externa):
1. Restaurar créditos Trader Dev (buy_credits ou /unlock-edge).
2. Re-run baseline reproduce backtest em SOLUSDT 15m (sanidade antes de modificar).
3. Run modified version (atrMult 0.05) no mesmo janela/símbolo.
4. Se melhoria confirma em SOL 15m → expandir multi-pair/multi-TF (ETH, BTC, 15m/30m/1h).
5. Compare via compare_backtests → decide keep/iterate/reject.

Human required: **yes** — créditos zerados e fork bloqueado exigem ação do usuário.

Blockers:
- quick_backtest: "You have no credits remaining. Your free credits reset on Invalid Date."
- fork_strategy: 403 fork_requires_paid_plan (conta free)
