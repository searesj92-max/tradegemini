# Gertrude Decision — High-WR leaderboard / public forks (G91, Vanta, Donchian, etc.)

Date: 2026-09-23
Report source: data/reports/2026-09-23-1820-high-wr-synthesis.md · data/reports/2026-09-23-1816-notrail-fork.md · data/reports/2026-09-23-1809-high-wr-batch.md · data/reports/2026-09-23-1800-high-wr-batch.md · data/reports/2026-09-23-1725-discovery-batch.md

Metrics (síntese dos relatórios):
- Public leaderboard "safe filtered": 40 linhas classificadas como Candidate, mas todas com trailing, muitas single-pair, algumas com PF > 10 (provável artefacto de engine ou regime específico não replicável).
- No-trail public forks (96): 95/95 rejeitados — ao remover trailing, PF < 1 em todos, DD 76–99%.
- g91-tight: WR até 66.6% mas PF 0.92 e DD 99% — alta taxa de acerto sem expectancy.
- Desk gate de alta WR (WR≥50 · PF≥1.3 · DD≤30 · multi-par · sem trailing): 0/176 linhas locais + 0/95 forks públicos passaram.
- Leaderboard rows com PF > 10 e DD < 1% em SOL 15min: suspeita de artefacto de engine ou condições muito específicas — verificar independentemente se alguém aprovar.

Verdict: **REJEITAR** (para book)

Rationale (por classe):
1. Public forks com trailing removido: REJEITAR — PF < 1 em todos, DD catastrófico sem trailing.
2. g91-tight / vanta-tight (alta WR, TP apertado): REJEITAR — PF < 1, DD > 90%, são loteria de pequenas vitórias.
3. Public leaderboard "Candidate" sem trailing verificado: NÃO APROVAR — muitos são single-pair, trail-dependent, PF inflado. Aguardar verificação MCP prévia a qualquer decisão.
4. Nenhum atende o gate de alta WR multi-par sem trailing do desk.

Next step: não incluir nenhuma linha pública com trailing no book de incubação. Se quiser investigar as linhas SOL 15min com PF extremo, fazer verificação MCP individual antes de qualquer classificação.

Human required: sim — caso haja interesse em investigate as linhas de leaderboard com PF > 10, preciso de confirmação humana para despachar verificação MCP (não é automático — pode ser artefacto).

Note: nenhuma decisão de aprovação foi tomada sobre leaderboard. Trata-se apenas de rejeição das linhas que falharam no gate.
