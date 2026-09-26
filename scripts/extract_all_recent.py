#!/usr/bin/env python3
"""
Extract panel rows from all recent reports.
Uses line-by-line parsing to handle markdown tables and JSON blocks.
Handles encoding variability and Windows \r\n line endings.
"""
from __future__ import annotations
import json, re, sys
from pathlib import Path

ROOT = Path(r"C:\Users\seares\Desktop\botrade")
SCRIPTS = ROOT / "scripts"

# Reports que podem ter linhas para o painel (backtest via MCP ou local)
REPORTAS_COM_LINHAS = [
    ROOT / "data/reports/2026-09-26-1530-researcher-h2-h1-greenfield.md",
    ROOT / "data/reports/2026-09-24-2300-researcher-lsn-v1-batch.md",
    ROOT / "data/reports/2026-09-24-1824-researcher-rec-greenfield.md",
    ROOT / "data/reports/2026-09-24-1618-researcher-qm-fcs-v1.md",
    ROOT / "data/reports/2026-09-23-2036-optimizer-rsi-t200b-crosstf-local.md",
    ROOT / "data/reports/2026-09-23-1951-optimizer-rsi-t200b-sltp-local.md",
    ROOT / "data/reports/2026-09-23-1949-optimizer-rsi-t200b-sltp-local.md",
]

def extract_json_blocks_lines(report_path: Path) -> list[dict]:
    """Extrai blocos JSON usando análise linha a linha."""
    txt = report_path.read_text(encoding="utf-8")
    lines = txt.splitlines()  # splitlines lida com \r\n, \n, \r
    rows = []
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        # Detectar início de bloco fenced
        if stripped in ("```", "```json", "```jsonlang") or \
           (stripped.startswith("```") and len(stripped) <= 15):
            # Coletar linhas até o fechamento
            block_lines = []
            for j in range(i + 1, len(lines)):
                inner = lines[j].strip()
                if inner == "```":
                    break
                block_lines.append(lines[j])
            
            block_text = "\n".join(block_lines)
            if not block_text.strip():
                continue
            
            # Tentar parse JSON
            try:
                payload = json.loads(block_text)
            except json.JSONDecodeError as e:
                print(f"  JSON decode error em {report_path.name}:{i+1}: {e}", file=sys.stderr)
                print(f"  Preview: {block_text[:100]!r}", file=sys.stderr)
                continue
            
            # Extrair rows
            if isinstance(payload, dict):
                if isinstance(payload.get("strategies"), list):
                    for s in payload["strategies"]:
                        if isinstance(s, dict) and (s.get("id") or s.get("name")):
                            rows.append(s)
                elif payload.get("id") or payload.get("name"):
                    rows.append(payload)
            elif isinstance(payload, list):
                for item in payload:
                    if isinstance(item, dict) and (item.get("id") or item.get("name")):
                        rows.append(item)
    
    return rows

def extract_from_tables(report_path: Path) -> list[dict]:
    """Extrai linhas de tabelas markdown com colunas de backtest."""
    txt = report_path.read_text(encoding="utf-8")
    # Procurar tabelas que contenham Strategy ID ou Result ID
    tables = []
    lines = txt.splitlines()
    
    for i, line in enumerate(lines):
        if line.startswith("|") and ("Strategy ID" in line or "Result ID" in line or "View URL" in line):
            # Esta é uma linha de cabeçalho de tabela
            header = [c.strip() for c in line.split("|")[1:-1]]
            # Lê o separador
            sep_line = lines[i+1] if i+1 < len(lines) else ""
            # Lê linhas de dados até encontrar linha vazia ou outra seção
            data_lines = []
            for j in range(i+2, len(lines)):
                dl = lines[j]
                if not dl.startswith("|"):
                    break
                data_lines.append(dl)
            
            if data_lines:
                for dl in data_lines:
                    cells = [c.strip() for c in dl.split("|")[1:-1]]
                    if len(cells) >= len(header):
                        row = {}
                        for h, c in zip(header, cells):
                            row[h.lower().replace(" ", "_")] = c
                        tables.append(row)
    
    processed = []
    for t in tables:
        # Extrair campos relevantes
        row = {}
        
        # ID do resultado (pode estar em Strategy ID ou Result ID ou em View URL)
        strategy_id = t.get("strategy_id") or t.get("strategyid") or ""
        result_id = t.get("result_id") or t.get("resultid") or ""
        
        # View URL pode conter o result_id
        view_url = t.get("view_url") or t.get("viewurl") or ""
        view_result_id = ""
        if view_url and "/backtest/" in view_url:
            view_result_id = view_url.split("/backtest/")[-1].strip()
        
        # Determinar símbolo e timeframe
        symbol = ""
        timeframe = ""
        
        # Procurar linha com símbolo-nome no texto do relatório
        # usamos a tabela de resultados principais
        if "símbolo" in t or "symbol" in t:
            symbol = t.get("símbolo") or t.get("symbol") or ""
        if "tf" in t or "timeframe" in t or "time_frame" in t:
            timeframe = t.get("tf") or t.get("timeframe") or t.get("time_frame") or ""
        
        # Se a tabela é a de resultados gerais, tente inferir
        # Os resultados do LSN têm "Símbolo" | "Net%" | "PF" | etc.
        if not symbol:
            # Tenta extrair do nome da estratégia ou de outros campos
            for key in t:
                if "net" in key.lower():
                    try:
                        row["net_profit_pct"] = float(t[key])
                    except (ValueError, TypeError):
                        pass
        
        # Número de trades
        trades_val = None
        for key in t:
            if "trade" in key.lower() and "count" not in key.lower():
                try:
                    trades_val = int(float(t[key]))
                except (ValueError, TypeError):
                    pass
        if trades_val is not None:
            row["trades"] = trades_val
        
        processed.append({
            "raw": t,
            "view_result_id": view_result_id,
        })
    
    return processed

def main():
    all_rows = []
    
    print("=" * 70, file=sys.stderr)
    print("EXTRACTION REPORT", file=sys.stderr)
    print("=" * 70, file=sys.stderr)
    
    for report_path in REPORTAS_COM_LINHAS:
        if not report_path.exists():
            print(f"\n[SKIP] {report_path.name} — arquivo não encontrado", file=sys.stderr)
            continue
        
        print(f"\n{'─'*70}", file=sys.stderr)
        print(f"Relatório: {report_path.name}", file=sys.stderr)
        print(f"{'─'*70}", file=sys.stderr)
        
        # Método 1: blocos JSON
        json_rows = extract_json_blocks_lines(report_path)
        print(f"JSON blocks extraídos: {len(json_rows)} rows", file=sys.stderr)
        for r in json_rows:
            print(f"  ✓ {r.get('id')} | {r.get('name')[:40] if r.get('name') else 'N/A'} | {r.get('symbol')} {r.get('timeframe')} | PF={r.get('profit_factor')} | net={r.get('net_profit_pct')} | trades={r.get('trades')}", file=sys.stderr)
        
        # Método 2: tabelas
        table_info = extract_from_tables(report_path)
        print(f"Tabelas com Strategy/Result ID: {len(table_info)} tabelas", file=sys.stderr)
        for ti in table_info[:5]:
            print(f"  info: view_result_id={ti['view_result_id']}", file=sys.stderr)
        if len(table_info) > 5:
            print(f"  ... e mais {len(table_info)-5} tabelas", file=sys.stderr)
        
        all_rows.extend(json_rows)
    
    print(f"\n{'='*70}", file=sys.stderr)
    print(f"TOTAL: {len(all_rows)} rows extraídas", file=sys.stderr)
    print(f"{'='*70}", file=sys.stderr)
    
    if all_rows:
        out_path = SCRIPTS / "panel_rows_all_recent.json"
        out_path.write_text(json.dumps(all_rows, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Salvo em {out_path}", file=sys.stderr)
        print(f"\nPara ingerir no painel:", file=sys.stderr)
        print(f"  python scripts/panel_upsert.py --rows scripts/panel_rows_all_recent.json", file=sys.stderr)
    else:
        print("\nERRO: Nenhuma row encontrada em nenhum relatório", file=sys.stderr)
        print("Verificar se os relatórios têm blocos JSON ou tabelas com Strategy/Result ID", file=sys.stderr)

if __name__ == "__main__":
    main()
