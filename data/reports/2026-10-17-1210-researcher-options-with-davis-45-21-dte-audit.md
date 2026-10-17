# Trader Dev Research Report — Auditoria Quantitativa: Método 45-21 DTE (Options With Davis / Tastytrade)

## 1. Goal
Analisar de ponta a ponta o vídeo *"After trading Options for 20 years, I found the BEST way to trade Credit Spreads..."* do canal **Options With Davis** (`https://youtu.be/7nI8Jx-5pVY`), validar matematicamente se a estratégia faz sentido e testar sua lucratividade real no mercado de **Bitcoin (BTC)** ao longo de 5,5 anos (2.000 dias de histórico: Abril/2021 a Outubro/2026), comparando-a com o modelo Sniper Semanal (10 DTE) utilizado na Derive.xyz.

## 2. Strategy or Hypothesis (O que o vídeo ensina)
O vídeo apresenta o protocolo institucional desenvolvido pela equipe de pesquisa da **Tastytrade** para operar travas de crédito (*Bull Put Spreads*):
1. **Prazo de Entrada (45 DTE):** Entrar sempre na janela próxima a **45 dias para o vencimento** (aceitável entre 42 e 55 DTE), sob a premissa de capturar a vantagem onde a volatilidade implícita supera o movimento realizado sem exposição excessiva ao Gamma.
2. **Seleção de Strike (Delta 25 a 35):** Vender a ponta curta com Delta entre **0.25 e 0.35**.
   - *Método 1 (Perpétuo):* Aplicado de forma sistemática/mecânica em índices com viés de alta (SPY/QQQ), reabrindo imediatamente uma nova trava de 45 DTE assim que a anterior é encerrada.
   - *Método 2 (Seletivo):* Aplicado apenas quando o oscilador Estocástico ou RSI indica sobrevenda próximo a um nível de suporte gráfico, posicionando o strike vendido abaixo do suporte.
3. **Regra de Saída Obrigatória (21 DTE ou 50% TP):**
   - Encerrar a operação assim que atingir **50% do crédito máximo** OU quando restarem **21 dias para o vencimento (21 DTE)** — **independentemente de estar no lucro ou no prejuízo**.
4. **Proibição de Stop Loss de Preço Curto:** Demonstra que stops de preço (1x ou 2x o crédito) sofrem violinadas pela expansão temporária de volatilidade (Vega), tendo desempenho inferior ao gerenciamento temporal aos 21 DTE.

## 3. Backtest Matrix
- **Ativo:** `BTCUSDT` (Spot + Precificação Black-Scholes com Skew de Volatilidade Implícita dinâmica calibrada pela volatilidade realizada de 20 dias + prêmio de risco).
- **Período:** `2021-04-26` a `2026-10-16` (`2.000` candles diários — cobrindo Bull Market 2021, Bear Market/FTX 2022, Recuperação 2023 e Ciclo 2024–2026).
- **Capital Base Padronizado:** `$1.000,00 USDC` de margem colateral por operação (sem juros compostos para isolar a qualidade pura do sinal).

## 4. Results (5.5 Anos — 2021 a 2026)

| Cenário / Estratégia | Trades | Win Rate | Lucro Líquido ($1k base) | Profit Factor | Max Drawdown | Perda Média | Pior Perda Única | Ganho / Dia Alocado |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1. Vídeo Método 1 (45→21 DTE, Delta 0.30, TP 50%)** | 115 | 71.3% | **+$4,249.01** | 1.37 | $2,841.26 | -$346.14 | -$865.02 | +$2.19/dia |
| **2. Hold to Expiry (45→0 DTE, Delta 0.30, Sem Saída 21d)** | 43 | 74.4% | **+$3,820.88** | 1.46 | $3,414.77 | -$751.84 | -$1,000.00 | +$1.97/dia |
| **3. Vídeo Método 2 Seletivo (RSI < 42, 45→21 DTE)** | 56 | 71.4% | **+$888.04** | 1.13 | $2,297.09 | -$420.84 | -$769.00 | +$0.89/dia |
| **4. Adaptação Cripto (45→21 DTE, Delta 0.18, TP 50%)** | 138 | 80.4% | **+$3,029.37** | 1.34 | **$2,129.21** | **-$329.29** | **-$672.97** | +$1.57/dia |
| **5. Nosso Sniper Semanal (10→2 DTE, Delta 0.15, TP 80%)** | 339 | **84.4%** | **+$8,242.88** | **1.40** | $2,773.80 | -$388.25 | -$999.73 | **+$4.20/dia** |

## 5. Robustness Analysis & Diagnóstico Quantitativo
1. **A regra dos 21 DTE funciona matematicamente?**
   - **Sim.** Comparando o Cenário 1 (`45→21 DTE`) contra o Cenário 2 (`45→0 DTE Hold`), sair aos 21 DTE reduziu a **perda média em 54%** (de `-$751.84` para `-$346.14`), evitou perdas totais de 100% da margem, diminuiu o Drawdown Máximo em 17% e aumentou o lucro líquido acumulado em +11.2%.
2. **Onde o vídeo acerta em cheio:**
   - Explicar que Stop Loss curto em opções vendidas destrói valor (você realiza prejuízo no pico do medo/Vega exatamente antes do ativo estabilizar).
   - Demonstrar que nas opções de prazo longo (45 dias), os últimos 21 dias concentram o risco de Gamma (oscilação violenta do P&L).
3. **Por que o Sniper Semanal (10 DTE, Delta 0.15) supera o 45→21 DTE no Bitcoin (+$8.242 vs +$4.249)?**
   - **Velocidade do Theta:** O decaimento do tempo nos últimos 10 dias é exponencialmente mais rápido (`+$4.20/dia` vs `+$2.19/dia`).
   - **Distância de Segurança (Delta 0.15 vs 0.30):** No Bitcoin, vender Delta 0.30 para 45 dias fica exposto a tendências macro de baixa. Já vender Delta 0.15 para apenas 7–10 dias eleva a taxa de vitória para **84.4%**.
   - **Microestrutura da Derive.xyz:** Em DEX de opções cripto, vencimentos de 45 dias possuem *spread* Bid/Ask muito mais largo no livro de ofertas do que vencimentos semanais de 7–10 dias.

## 6. Weaknesses
- **Método 1 (Delta 0.30 em 45 DTE):** Sofre drawdowns acentuados em Bear Markets prolongados (como Maio–Novembro de 2022) se não houver filtro de tendência ou rolagem defensiva.
- **Método 2 (Seletivo por RSI sem filtro de regime):** Em cripto, comprar sobrevenda de RSI diário sem checar tendência macro faz o trader vender Puts no início de *crashes* estruturais e ficar de fora de ralis fortes de alta.

## 7. Next Iteration & Aplicação Prática na Carteira do Usuário
1. **Para a trava de Novembro já aberta (`BTC 75k/70k — Vencimento 27/11 — 0.05 BTC`):** Aplicar exatamente a regra de ouro deste vídeo! Como ela foi aberta com ~48 DTE, **não precisamos esperar até 27/11**. Assim que atingir **50% de lucro** ou chegar aos **21 DTE (06/11/2026)**, encerramos para liberar os `$217.75 USDC` de margem sem correr o risco de Gamma do fim de novembro.
2. **Para o capital principal (`0.30 BTC`):** Manter o foco no **Sniper Semanal (7–10 DTE, Delta ~0.15, com saída em 75%–80% TP ou Rolagem de Defesa)**, que entrega quase o dobro de retorno diário (`+$4.20/dia` por `$1k`) com maior liquidez no book da Derive.

## 8. Verdict
**Incubate / Hybrid Adoption** — A regra de saída antecipada (50% TP ou 21 DTE) é aprovada para gerenciar a posição longa de Novembro (27/11), enquanto o modelo Sniper de 10 DTE permanece superior como motor principal de renda semanal no Bitcoin.
