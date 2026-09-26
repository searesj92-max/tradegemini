# Dispatch — Optimizer

Date: 2026-09-23
Dispatcher: gertrude (chief of staff)
Priority: NEXT

## Goal

Otimizar **apenas SL/TP** da estratégia `rsi-t200b` (família RSI+trend filter, 4h), mantendo intactos entries e exits de sinal.

## Strategy
- ID/name: rsi-t200b (RSI com trend filter, 4h) — o melhor do book local (8/16 pares, mean PF 1.69)
- Baseline: versão já backtestada com os parâmetros atuais de SL/TP
- Change ONE thing: sweep de SL/TP multiples (ex. SL 1.0–2.0 ATR, TP 2.0–4.0 ATR) em grid pequeno

## Constraints
- Símbolos: os 8 pares que passaram no batch 3 (ETH, AVAX, ARB, OP, ATOM, INJ, XRP, SOL)
- TFs: manter 4h apenas nesta rodada (cross-TF será próxima etapa após otimização)
- Credits disponíveis: 280 (free tier); gastar com moderação
- Engine: tv_jul26

## Definition of done
- Backtest rsi-t200b com ≥3 combinações de SL/TP nos 8 pares
- Resultados reportados em data/reports/ com matriz de comparação vs baseline
- Critério de melhoria: PF subir sem DD aumentar acima de 30% e sem reduzir trades para abaixo de 40 por par
- Se nenhuma combinação melhorar significativamente → reportar e estacionar; não forçar

## Regra obrigatória
- Nenhuma mudança em entradas/saidas de sinal — apenas SL/TP
- Nenhum trailing, nenhum martingale, nenhum tamanho fixo de posição
- Commision 0.05% (paridade MCP)

## Nota do despachante
- rsi-t200b é ESTACIONAR, não incubação. Otimização é etapa exploratória — não promover a produção.
- Após otimização, Gertrude reavaliará para possível incubator se PF subir e houver cross-TF.

Agency: optimizer
