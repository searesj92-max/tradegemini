#!/usr/bin/env python3
"""
Archive non-positive and failing strategies from dashboard/data.json into rejection memory.
Saves:
- data/rejected/rejected_strategies_memory.json (full JSON dump of discarded strategies)
- data/rejected/rejection_audit_report.md (detailed analytical failure audit)
Updates:
- dashboard/data.json (retaining only viable, positive strategies for subsequent multi-pair enrichment)
"""
import json
import sys
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent.parent
DATA_JSON_PATH = ROOT / "dashboard" / "data.json"
REJECTED_DIR = ROOT / "data" / "rejected"
REJECTED_DIR.mkdir(parents=True, exist_ok=True)

REJECTED_MEM_FILE = REJECTED_DIR / "rejected_strategies_memory.json"
REJECTED_REPORT_FILE = REJECTED_DIR / "rejection_audit_report.md"

def num(v, d=0.0):
    try:
        return float(v) if v is not None else d
    except (ValueError, TypeError):
        return d

def main():
    if not DATA_JSON_PATH.exists():
        print(f"[-] Arquivo {DATA_JSON_PATH} não encontrado.")
        sys.exit(1)

    with open(DATA_JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    all_strats = data.get("strategies", [])
    print(f"[*] Total inicial de estratégias: {len(all_strats)}")

    retained = []
    discarded = []

    reason_counts = {
        "NEGATIVE_NET_PROFIT": 0,
        "LOW_PROFIT_FACTOR": 0,
        "GERTRUDE_REJECT_VERDICT": 0,
        "EXCESSIVE_DRAWDOWN": 0,
        "ZERO_OR_INSUFFICIENT_TRADES": 0
    }

    for s in all_strats:
        pf = num(s.get("profit_factor"))
        net = num(s.get("net_profit_pct"))
        dd = num(s.get("max_drawdown_pct"))
        trades = int(num(s.get("trades")))
        verdict = s.get("verdict", "")
        is_rollup = bool(s.get("is_rollup", False))

        rejection_reasons = []

        if net <= 0:
            rejection_reasons.append("Lucro Líquido Negativo ou Nulo")
            reason_counts["NEGATIVE_NET_PROFIT"] += 1
        if pf < 1.10:
            rejection_reasons.append(f"Profit Factor Inviável ({pf:.2f} < 1.10)")
            reason_counts["LOW_PROFIT_FACTOR"] += 1
        if verdict == "Reject":
            rejection_reasons.append("Classificado como REJEITADO pela Chief of Staff (Gertrude)")
            reason_counts["GERTRUDE_REJECT_VERDICT"] += 1
        if dd > 35.0:
            rejection_reasons.append(f"Drawdown Inaceitável ({dd:.1f}% > 35%)")
            reason_counts["EXCESSIVE_DRAWDOWN"] += 1
        if trades < 5 and not is_rollup:
            rejection_reasons.append(f"Amostragem Insuficiente ({trades} trades)")
            reason_counts["ZERO_OR_INSUFFICIENT_TRADES"] += 1

        if rejection_reasons:
            s_copy = dict(s)
            s_copy["rejection_reasons"] = rejection_reasons
            s_copy["archived_at"] = datetime.now(timezone.utc).isoformat()
            discarded.append(s_copy)
        else:
            retained.append(s)

    print(f"[+] Estratégias Mantidas (Positivas / Candidatas): {len(retained)}")
    print(f"[-] Estratégias Descartadas e Arquivadas na Memória: {len(discarded)}")

    # 1. Save rejected memory JSON
    with open(REJECTED_MEM_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "version": "1.0",
            "archived_at": datetime.now(timezone.utc).isoformat(),
            "total_discarded": len(discarded),
            "reason_summary": reason_counts,
            "discarded_strategies": discarded
        }, f, indent=2, ensure_ascii=False)
    print(f"[+] Memória de rejeições salva em: {REJECTED_MEM_FILE}")

    # 2. Generate detailed Markdown Audit Report
    report_lines = [
        "# Relatório de Auditoria e Descarte de Estratégias Inviáveis",
        "",
        f"**Data da Auditoria**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
        "**Responsável**: Mesa Quantitativa Botrade (Filtro Institucional de Risco & Gertrude)",
        "",
        "---",
        "",
        "## 1. Sumário Executivo",
        "",
        f"- **Estratégias Auditadas no Catálogo**: {len(all_strats)}",
        f"- **Estratégias Descartadas (Arquivadas)**: {len(discarded)} ({len(discarded)/len(all_strats)*100:.1f}%)",
        f"- **Estratégias Mantidas (Base Positiva)**: {len(retained)} ({len(retained)/len(all_strats)*100:.1f}%)",
        "",
        "### Motivos de Descarte (Critérios Rígidos de Hedge Fund):",
        "",
        f"- 📉 **Lucro Líquido Negativo / Sangria de Taxas**: {reason_counts['NEGATIVE_NET_PROFIT']} ocorrências",
        f"- ⚠️ **Profit Factor Inferior a 1.10 (Sem Borda Estatística)**: {reason_counts['LOW_PROFIT_FACTOR']} ocorrências",
        f"- 🛑 **Veredito de Rejeição Gertrude**: {reason_counts['GERTRUDE_REJECT_VERDICT']} ocorrências",
        f"- 🌊 **Drawdown Excessivo (> 35%)**: {reason_counts['EXCESSIVE_DRAWDOWN']} ocorrências",
        f"- 🔬 **Amostragem Insuficiente (< 5 trades)**: {reason_counts['ZERO_OR_INSUFFICIENT_TRADES']} ocorrências",
        "",
        "---",
        "",
        "## 2. Diagnóstico Técnico dos Principais Erros das Estratégias Descartadas",
        "",
        "1. **Falta de Borda com Taxas e Slippage**: Estratégias de scalping e cruzamentos de médias curtas (ex: EMA 9/21 sem filtro de volatilidade) sofrem sangria acelerada pelas taxas de taker (0.035%) da Hyperliquid.",
        "2. **Overfitting de Moeda Única (One-Pair Wonders)**: Modelos que mostravam lucro isolado em 1 altcoin de baixa liquidez, mas geravam prejuízo massivo em BTC, ETH ou SOL.",
        "3. **Falta de Stop Loss Dinâmico ou Ratchet**: Estratégias que acumulavam lucros pequenos e devolviam tudo em uma única perna direcional de mercado contra a posição.",
        "",
        "---",
        "",
        "## 3. Amostra de Estratégias Arquivadas (Top 25 Piores Resultados Descartados)",
        "",
        "| ID / Nome | Par | TF | Profit Factor | Lucro Líq. % | Max DD % | Motivo Principal |",
        "|---|---|---|---|---|---|---|"
    ]

    # Sort discarded by worst net profit
    worst = sorted(discarded, key=lambda x: num(x.get("net_profit_pct")))[:25]
    for w in worst:
        reasons_str = "; ".join(w.get("rejection_reasons", []))
        report_lines.append(
            f"| `{w.get('id')}` | {w.get('symbol', 'MULTI')} | {w.get('timeframe', '—')} | "
            f"{num(w.get('profit_factor')):.2f} | {num(w.get('net_profit_pct')):.1f}% | "
            f"{num(w.get('max_drawdown_pct')):.1f}% | {reasons_str} |"
        )

    with open(REJECTED_REPORT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines) + "\n")
    print(f"[+] Relatório de auditoria salvo em: {REJECTED_REPORT_FILE}")

    # 3. Update dashboard/data.json with only retained
    data["strategies"] = retained
    data["retained_count"] = len(retained)
    data["discarded_count"] = len(discarded)
    data["last_cleaned_at"] = datetime.now(timezone.utc).isoformat()

    with open(DATA_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"[+] dashboard/data.json atualizado com sucesso! ({len(retained)} estratégias ativas).")

if __name__ == "__main__":
    main()
