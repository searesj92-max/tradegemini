# Dispatch — researcher-local-greenfield-2026-09-24

**Data:** 2026-09-24
**Destinatário:** researcher (Quant Mathematician)
**Prioridade:** NEXT (imediato)
**Créditos MCP:** 0 (bloqueio ativo — todas as operações MCP estão impedidas)

---

## 1. Objetivo

Em ambiente de crédits zerados, manter o pipeline vivo através de:

(a) **Geração de novas hipóteses matemáticas** que possam ser testadas LOCALMENTE (engine local-python com OHLCV binance) quando o MCP estiver indisponível.

(b) **Preparação dePine scripts** para as hipóteses já em ESTACIONAR que são prioridade quando crédits retornarem: QM-VEE-LO-v2 (watchlist, PF 1.40-1.96 em BTC/SOL), QM-VWAPDISP-v4 (exploratório), QM-REC-v2 (greenfield), FTMO SOL Donchian (candidate, não verificado).

(c) **Documentar o block de crédits** para o humano review — incluir no relatório: tempo de Espera estimado, alternativas (upgrade, exchange verification, local engine).

## 2. Constraints

- **Nenhum backtest MCP** até crédits retornarem (get_credits = 0, weeklyResetAt = Invalid Date).
- **Local engine:** usar `scripts/run_local_sltp_sweep.py` ou equivalente para testes locais com commission=0 (discrever gap vs MCP 0.05%).
- **Sem ordens reais.** Sem live alerts. Sem promoção para produção.
- **Um conceito por relatório** — não mesclar hipóteses.

## 3. Definition of done

- Relatório em `data/reports/YYYY-MM-DD-HHMM-researcher-<slug>.md` com:
  - 3-5 hipóteses matemáticas novas (first-principles, não indicator soup)
  - Seleção de 1 hipótese com Pine draft completo (v6, permitlist, sem repaint/lookahead, SL presente)
  - Pine salvo em `data/pine/`
  - Se possível: 1+ backtest local executado com resultados (mesmo que commission=0)
  - Verdict claro: REJECT / WATCHLIST / ESTACIONAR
- Dashboard atualizado com nova linha (se houver backtest)

## 4. Prioridade de hipóteses a explorar (sugestão)

1. **FCE cross-TF** — Failed Continuation Exhaustion já tem PF 1.04-1.42 em 5 símbolos 1h (watchlist). Testar 15m/30m/2h/4h localmente para ver se edge se mantém. Este é o candidato mais maduro para credit-free exploration.

2. **REC-VND pivot** — Linha REC-VND rejeitada (PF 0.43-0.74 em 5 símbolos). Próxima iteração sugerida pelo próprio relatório: HS-AR (Liquidity Sweep + Asymmetric Reversion) ou DFAE. Testar localmente.

3. **VEE-LO expansão** — Já tem edge em BTC/SOL (PF 1.40/1.96). Testar mais símbolos (DOGE, ADA, AVAX, LINK, BNB) e cross-TF localmente. Este é o candidato com sinais de vida mais fortes.

4. **Novas hipóteses greenfield** — a partir de observações matemáticas frescas, não de retail indicator soup.

## 5. Nota para Gertrude (próximo ciclo)

- Se crédits MCP voltarem neste ciclo: dispatchar optimizer para FTMO SOL Donchian (reprodução + trail loosening) ou rsi-t200b SL/TP sweep.
- Se crédits continuarem zerados por >1 semana: considerar dispatchar builder para panel de controle sobre as hipóteses em watchlist, ou researcher para ciclo local puramente.
- Nenhum APROVAR neste ciclo — todos ESTACIONAR. Nenhuma produção.
