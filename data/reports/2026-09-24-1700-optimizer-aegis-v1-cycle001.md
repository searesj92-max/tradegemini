# Strategy Optimizer Cycle Report

**Agent**: optimizer (Hermes cron)  
**Date**: 2026-09-24~26 BRT  
**Loop target**: `loop/06-strategy-optimizer.md` — search → fork → ONE change → backtest → compare → report

---

## 1. Consigna

Executar um ciclo completo do loop: buscar um candidato com sinais de vida, forkar, aplicar UMA mudança com hipótese diagnosticada, rodar backtest multi-par/multi-TF, comparar com o original e decidir Keep / Reject / Iterate. Nenhuma ordem real.

---

## 2. Busca (search_strategies)

Critério de filtragem: PF ≥ 1.1, min 50 trades, ordenado por `trades` — o objetivo é achar um candidato com amostra estatisticamente relevante e economia real, não curvas de lucro infladas por um único trade.

Três buscas foram feitas em sequência:

| Busca | Filtro | Resultado destacado |
|---|---|---|
| sharpe | maxDD ≤ 15%, PF ≥ 1.1, sharpe ≥ 0.8, trades ≥ 30 | LITUSDT e SOLUSDT — resultado gritante de overfit (PF 3.4×, DD 7%, 600 trades em 30–60 dias, jornada curta). Estratégias tipo "G91f10" com nomes de PAPER retest: risco real de tunagem no-period. Excluídos: janela curta demais, não generaliza. |
| not sorted | PF ≥ 1.1, trades ≥ 30 | Mesmos resultados de LIT/SOL, sem novidade. |
| trades | PF ≥ 1.1, trades ≥ 50 | MEG resultou: `AEGIS Volatility Expansion Pine Port` (BTCUSDT 5m, PF 2.398, DD 4.39%, WR 55.2%, **63 467 trades**). |

### Por que AEGIS é o candidato escolhido

- **Amostra massiva**: 63k+ trades — raríssimo no MCP; dificilmente é one-trade-wonder.
- **Números plausíveis**: PF 2.4, DD 4.4%, WR 55% — não números de "curva bonita de 30 dias".
- **Janela longa**: ~1.1 anos de candles 5m BTC — cobre múltiplos regimes.
- **Originalidade**: port de código Python (aegis_core) para Pine, sem indicador retail óbvio.
- **Idiomas**: estratégia pública, sem forkedFrom (origem própria).

**Observação de risco de overfit**: PF 2.4 em 5m BTC com 63k trades é um caso que merece diagnóstico — é possível que o filtro de contraction percentile + momentum proxy tenha sido tunado. A análise de robustness abaixo avalia isso.

---

## 3. Estratégia original (AEGIS Volatility Expansion)

### 3.1 Lógica (extraída do Pine via get_strategy)

O algoritmo é um versão Pine de um mean-reversion / breakout com filtro de contração volátil:

1. **Caixa de range**: a cada barra, calcula o maior high / menor low dos últimos `boxBars=12` barras → `boxHigh`, `boxLow`, `boxHeight = boxHigh - boxLow`.
2. **Contraction percentile**: compara a caixa atual com a distribuição dos últimos `contractionLookback=200` caixas. Se a caixa atual está no percentil ≤ `maxContractionPercentile=0.35`, é uma "compressão extrema".
3. **Filtro de ATR da caixa**: `boxAtr = boxHeight / ATR(14)` deve estar entre `minBoxAtr=0.80` e `maxBoxAtr=3.00`. Evita caixas muito pequenas ou muito grandes.
4. **Confirm break**: break long = `close` e `close[1]` acima de `boxHigh + breakoutBuffer` (onde `breakoutBuffer = ATR × minBreakoutAtr=0.10`). Idem para short abaixo do boxLow.
5. **Volume confirm**: `relativeVolume ≥ 1.20` vs SMA(volume, 20) barra anterior.
6. **Momentum proxy**: `close` vs `close[24]` deve ter ≥ 0.15% para long, ≤ −0.15% para short. "Relative strength" same-symbol.
7. **Max demonstração**: drift desde o close de confirmação deve ser ≤ `ATR × 0.40` — não chasing.
8. **Strike implícito**: stop loss = `boxLow − noiseBuffer` (long) / `boxHigh + noiseBuffer` (short), com `noiseBuffer = ATR × 0.25`.
9. **Três TP escalonados**: TP1 = boxHeight × 3, TP2 = boxHeight × 5, TP3 = boxHeight × 8, com split de 34/33/33% do risco.
10. **Filtro de RR implícito mínimo**: `minImpliedGrossRr = 1.80`. Não entra se o RR esperado (boxHeight × tp1Box × qty% / risco) não bater.

### 3.2 Pontos fortes

- Arquitetura de filtro multi-dimensional coerente: só opera em compressão extrema com volume + momentum + RR favorável. Isso é very diferente de "RSI < 30 → long".
- Risco definido antes da entrada: stop loss baseado na estrutura (box low), não em ATR fixo.
- TP escalonado com 3 escalões — coleta lucro em frente e deixa runner.
- `process_orders_on_close=true` + sem request.security — sem repainting óbivio.

### 3.3 Pontos fracos (diagnóstico)

- **Confiabilidade do contraction percentile**: usa `rangeHigh/rangeLow` dos últimos `boxBars` com lookback de 200. Isso é relativamente sensível a janela — uma janela 200 que cobre um regime de alta vol pode never dar percentile baixo, travando o sistema. Se 200 for muito longo, o filtro desaparece.
- **Sensibilidade ao boxBars**: box de 12 barras em 5m BTC = 1 hora. O range de 1h é bem determinado por ATR; combinação com contraction percentile pode gerar muitos falsos negativos (sem operação) porque a caixa de 12 é volátil demais.
- **Momentum proxy same-symbol**: `close[24]` vs `close` é uma medida muito local de "relative strength". Só captura direção local, não força real do ativo.
- **3 TP com risco escalonado**: pode ser ótimo em trending e ruim em range — o primeiro TP é arresetado rápido e o runner sofre.
- **RSI implícito de 1.8**: filtro que bate no RR esperado é bom, mas se a dinâmica de execução for diferente da esperada (slippage, gaps) o RR real pode ser menor.

---

## 4. Fork

### Tentativa

```
mcp__trader_dev__fork_strategy(sourceStrategyId="01KYX9KABBDRMW8Z1N0T8ZFF9N")
→ 403: "fork_requires_paid_plan"
   {"error": "fork_requires_paid_plan", 
    "message": "Forking other users' strategies requires a paid plan."}
```

### Conclusão

O MCP **não permite fork de estratégia de outro usuário sem plano pago**. O `AEGIS Volatility Expansion Pine Port` pertence ao `user_3HHwjsrJo4LH7QpIlpmQ4udqQBW` e o perfil atual (`searesj92@gmail.com`, tier `free`) não tem permissão.

Isso bloqueia a linha **fork → mudança → comparação** que o loop exige. Não é possível comparar um Original vs Fork porque não há Fork.

---

## 5. Diagnóstico de credibilidade do candidato (sem fork)

Como não há fork, fiz uma análise offline do Pine original para avaliar sevale a pena persistir (se créditos/registro mudarem) ou se devemos pivotar.

### 5.1 Coerência matemática da estratégia

| Componente | Avaliação |
|---|---|
| Contraction percentile (window 200, percentile ≤ 35%) | Hipótese razoável: entra em compressão extrema de range. Mas a janela 200 em 5m cobre ~1 dia de candles — pode ser muito curta para capturar compressão estrutural e muito longa para reagir. A métrica é relativa ao histórico recent, não absoluta. |
| Box ATR entre 0.8× e 3× ATR(14) | Filtro sensato de tamanho de caixa: caixas muito pequenas (ruído) e muito grandes (já rompidas) são rejeitadas. Banda larga o suficiente. |
| Confirm break com drift max 0.4× ATR | Evita chasing — bom. |
| Volume ≥ 1.2× baseline | Clássico filtro de validade de break. Pode ter leakage se o breakout ocorrer no início da barra e o volume seja medido após — mas como é `process_orders_on_close` e usa volume da barra de break, é ok. |
| Momentum proxy 24 barras | Muito curto para um proxy de "relative strength". O nome sugere algo mais robusto (ex. RS vs another symbol no Python original). |
| 3 TP escalados com risco implícito 1.8× | RR esperado alto — mas se o mercado reveer após TP1, o runner pode virar negativo. A dinâmica real depende de microstructure. |

### 5.2 Sobre o número de trades (63k) e overfit

63k trades em ~1 ano de 5m BTC = ~173 trades/dia. Para uma estratégia que exige contraction percentile ≤ 35% (top 35% de compressão) + volume + momentum + RR — isso implica frequência moderada. A possibilidade de overfitting é real mas não pode ser confirmada sem executar a estratégia em outros símbolos e TFs.

**Risco de overfit**: o Pine original foi registrado como estratégia própria (não fork) — o autor pode ter otimizado diretamente nos dados do BTC 5m. Os números de PF 2.4 + DD 4.4% com 63k trades são consistentes com uma estratégia que foi tunada nesse par específico. Validar cross-symbol é essencial para confirmar generalização.

---

## 6. Bloqueio: credenciais e credits

### 6.1 Estado da conta MCP

O loop tentou buscar créditos em paralelo (dentro do limite do tool_call). O MCP retornou erro de validação para chamada mista (local + connector na mesma call) — usamos chamada separada. O состояние de créditos não foi obtido diretamente nesta execução (chamada failed).

Do histórico recente (relatório `data/reports/2026-09-24-1500-researcher-qm-vol-reversion-v1.md` e `data/reports/2026-09-24-1615-risk-qm-vol-reversion-v1.md`), a conta está no tier `free` com **créditos zerados** e mensagem de reset "Invalid Date" (campo de weekly reset não parseia).

### 6.2 Implicação

- Backtest com `quick_backtest` ou `run_backtest` consome créditos — sem créditos, não há como validar o candidato nem o fork.
- Fork exige plano pago (403) — mesmo com créditos, sem upgrade não há fork de estratégias de outros usuários.
- Os dois requisitos do ciclo (fork + backtest) estão ambor bloqueados: um por plano, outro por créditos.

---

## 7. Decisão

### 7.1 O que foi possível executar

- [x] Busca de candidatos (search_strategies × 3 configurações)
- [x] Inspeção do Pine (get_strategy)
- [x] Diagnóstico de lógica e riscos de overfit
- [ ] Fork (erro 403 — plano pago necessário)
- [ ] Backtest do fork (impossível sem fork)
- [ ] Comparacão original vs fork (impossível sem fork)

### 7.2 Decisão de ciclo

**NÃO APTO** — ciclo incompleto por bloqueio de infraestrutura. O candidato AEGIS é tecnicamente interessante (lógica coerente, amostra grande, filtros multi-dim) mas não pode ser testado nem melhorado neste ciclo.

**VerDICT: WAIT (bloqueado por plano + créditos)**.

---

## 8. Próximas ações (human-in-the-loop)

O loop precisa de **dois fatores externos** para continuar:

| Bloqueio | O que resolve | Quem decide |
|---|---|---|
| Fork blocked (403) | Upgrade para plano pago no MCP (https://mcp-api.trader.dev/pricing), ou encontrar estratégia própria do usuário `searesj92` para fork interno | Usuário (capital de teste) |
| Credits zerados | Verificar conta de exchange e usar `/unlock-edge` para liberar dobramento semanal, ou aguardar weekly reset (data indefinida) | Usuário |

### Alternativas enquanto isso:

1. **Pivotar para estratégias próprias**: usar `list_strategies` para achar uma estratégia do próprio `searesj92` que tenha sinais de vida — assim o fork é possível (sem plano pago) e os créditos podem ser usados. Se existir uma estratégia própria com PF ≥ 1.2, min trades, cross-symbol fraqueza diagnosticável → fork e melhoria no próximo ciclo.
2. **Focar em desenvolvimento offline**: escrever o Pine de uma nova hipótese (ex. H-C — False Breakout Reversal com liquidity grab signature) e aguardar créditos para submeter ao MCP. Não consome créditos.
3. **Silêncio**: se não há candidato próprio e créditos zerados, o ciclo reporta `[SILENT]` no próximo lançamento — salvo se o usuário resolver os bloqueios.

---

## 9. Rascunho de hipótese para próximo ciclo (caso encontre estratégia própria)

Se um dia houver uma estratégia própria com alça de melhoria, uma das mudanças mais prováveis e com hipótese clara é:

**Mudança: review do momentum proxy (rsLookbackBars) e filtro de regime de tendência**

- **Hipótese**: o momentum proxy de 24 barras (mesmo símbolo) é muito curto e captura ruído local. Substituí-lo por uma medida de regime de tendência (ex. slope do EMA 50 vs ATR, ou ADX threshold) e manter o momentum como confirmação menor pode reduzir falsos quebras em ranges longos e melhorar o PF sem reduzir trades drasticamente.
- **Risco**: adicionar regime filter pode reduzir trades demais e introduzir regime-dependence. Testar em BTC + ETH × 3 TFs.

---

## Painel

Sem backtest executado, não há rows para injetar no dashboard. O `panel_upsert.py` não será chamado.

---

**Relatório gerado automaticamente pelo loop `06-strategy-optimizer.md` (optimizer). Não foram colocadas ordens reais.**
