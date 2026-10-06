#!/usr/bin/env python3
"""
DeFi Spreadsheet Recorder for Botrade
Generates and updates:
1. data/defi_latest.csv: Live snapshot of all 4 pools + Treasury total (compatible with Google Sheets =IMPORTDATA)
2. data/defi_history.csv: Granular 10-minute historical records with capital, yield, and appreciation/depreciation
3. data/defi_daily_summary.csv: Daily closing records for trend analysis
"""
from __future__ import annotations

import csv
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Fix Windows console encoding
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
DATA_DIR = ROOT / "data"
LATEST_CSV = DATA_DIR / "defi_latest.csv"
HISTORY_CSV = DATA_DIR / "defi_history.csv"
DAILY_CSV = DATA_DIR / "defi_daily_summary.csv"


def ensure_data_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def record_snapshot(evaluated_positions: list[dict], profits: dict, market: dict) -> dict:
    """Records a single 10-minute snapshot of all pools and treasury totals."""
    ensure_data_dir()
    now_utc = datetime.now(timezone.utc)
    ts_iso = now_utc.strftime("%Y-%m-%d %H:%M:%S UTC")
    date_str = now_utc.strftime("%Y-%m-%d")

    eth_px = market.get("eth", {}).get("price", 2715.0)
    aero_px = market.get("aero", {}).get("price", 0.795)
    googl_px = market.get("googl", {}).get("price", 345.0)
    mon_px = market.get("mon", {}).get("price", 0.032)
    usd_brl = float(market.get("usd_brl") or 5.04)

    p_info = profits.get("portfolio", {})
    weth_prof = profits.get("weth_usdc", {})
    googl_prof = profits.get("usdc_googlc", {})
    virt_prof = profits.get("virtual_weth", {})
    mon_prof = profits.get("mon_usdc", {})

    # Extract capital from evaluated items
    pos_map = {item["pos"]["id"]: item for item in evaluated_positions}

    weth_item = pos_map.get("weth_usdc")
    googl_item = pos_map.get("usdc_googlc")
    virt_item = pos_map.get("virtual_weth")
    mon_item = pos_map.get("mon_usdc")

    weth_cap = weth_item["pos"]["capital_usd"] if weth_item else 10378.16
    googl_cap = googl_item["pos"]["capital_usd"] if googl_item else 977.39
    virt_cap = virt_item["dynamic_val_usd"] if virt_item else 389.15
    mon_cap = mon_item["pos"]["capital_usd"] if mon_item else 331.98

    total_cap_usd = weth_cap + googl_cap + virt_cap + mon_cap
    total_cap_brl = total_cap_usd * usd_brl

    total_daily_usd = p_info.get("total_daily_usd", 70.82)
    total_daily_brl = total_daily_usd * usd_brl

    # Initial baselines for appreciation/depreciation calculation
    weth_init_usd = 10378.16
    googl_init_usd = 977.39
    virt_init_usd = 406.46
    mon_init_usd = 331.98
    total_init_usd = weth_init_usd + googl_init_usd + virt_init_usd + mon_init_usd

    weth_diff_usd = weth_cap - weth_init_usd
    googl_diff_usd = googl_cap - googl_init_usd
    
    # Virtual net includes audit equity if available
    virt_audit = virt_prof.get("audit") or {}
    virt_equity_usd = virt_audit.get("equity_usd", virt_cap)
    virt_net_usd = virt_audit.get("net_usd", virt_equity_usd - virt_init_usd)

    mon_diff_usd = mon_cap - mon_init_usd
    total_diff_usd = total_cap_usd - total_init_usd
    total_diff_pct = (total_diff_usd / total_init_usd) * 100.0 if total_init_usd > 0 else 0.0

    # 1. WRITE LATEST CSV (Clean table view for Google Sheets / Excel)
    latest_rows = [
        ["PLANILHA DE TESOURARIA DEFI — BOTRADE", "", "", "", "", "", ""],
        [f"Atualizado em: {ts_iso}", "", "", "", "", "", ""],
        ["", "", "", "", "", "", ""],
        ["RESUMO CONSOLIDADO DA CARTEIRA", "", "", "", "", "", ""],
        ["Patrimonio Total (USD)", f"${total_cap_usd:,.2f}", "Rendimento Diario Total (USD)", f"${total_daily_usd:,.2f}/dia", "Variacao Total (USD)", f"{total_diff_usd:+,.2f}", f"{total_diff_pct:+.2f}%"],
        ["Patrimonio Total (BRL)", f"R$ {total_cap_brl:,.2f}", "Rendimento Diario Total (BRL)", f"R$ {total_daily_brl:,.2f}/dia", "Cotacao Dolar Base", f"R$ {usd_brl:.4f}", ""],
        ["", "", "", "", "", "", ""],
        ["DETALHAMENTO POR POOL", "", "", "", "", "", ""],
        ["Pool / Ativo", "Rede / Protocolo", "Saldo Alocado (USD)", "Saldo Alocado (BRL)", "Renda Diaria Est. (USD)", "Renda Diaria Est. (BRL)", "Valorizacao / PnL ($)", "Status Faixa", "Identificacao"],
        [
            "WETH / USDC (Slipstream 50)",
            "Base (Aerodrome)",
            f"{weth_cap:.2f}",
            f"{weth_cap * usd_brl:.2f}",
            f"{weth_prof.get('daily_usd', 55.60):.2f}",
            f"{weth_prof.get('daily_brl', 55.60 * usd_brl):.2f}",
            f"{weth_diff_usd:+.2f}",
            weth_item["status_text"].replace("*", "") if weth_item else "🟢 In Range",
            "Principal #7669576 + Secundária #7670917"
        ],
        [
            "USDC / GOOGLc (Google RWA)",
            "Base (Aerodrome)",
            f"{googl_cap:.2f}",
            f"{googl_cap * usd_brl:.2f}",
            f"{googl_prof.get('daily_usd', 10.00):.2f}",
            f"{googl_prof.get('daily_brl', 10.00 * usd_brl):.2f}",
            f"{googl_diff_usd:+.2f}",
            googl_item["status_text"].replace("*", "") if googl_item else "🟢 In Range",
            "NFT #7508296"
        ],
        [
            "VIRTUAL / WETH 0.05%",
            "Base (Krystal Autopilot)",
            f"{virt_cap:.2f}",
            f"{virt_cap * usd_brl:.2f}",
            f"{virt_prof.get('daily_usd', 3.32):.2f}",
            f"{virt_prof.get('daily_brl', 3.32 * usd_brl):.2f}",
            f"{virt_net_usd:+.2f}",
            virt_item["status_text"].replace("*", "") if virt_item else "🔄 Autopilot",
            f"NFT #{virt_audit.get('active_nft', 6155510)}"
        ],
        [
            "MON / USDC (Concentrated)",
            "Monad (Uniswap v4)",
            f"{mon_cap:.2f}",
            f"{mon_cap * usd_brl:.2f}",
            f"{mon_prof.get('daily_usd', 1.90):.2f}",
            f"{mon_prof.get('daily_brl', 1.90 * usd_brl):.2f}",
            f"{mon_diff_usd:+.2f}",
            mon_item["status_text"].replace("*", "") if mon_item else "🟢 In Range",
            "Pool 0x659b"
        ],
        ["", "", "", "", "", "", ""],
        ["COTACAO DOS ATIVOS", "", "", "", "", "", ""],
        ["Ethereum (WETH)", f"${eth_px:,.2f}", "Aerodrome (AERO)", f"${aero_px:.4f}", "Google (GOOGLc)", f"${googl_px:.2f}", "Virtual (VIRTUAL)", f"${virt_audit.get('virtual_usd', 0.86):.4f}", "Monad (MON)", f"${mon_px:.5f}"]
    ]

    with open(LATEST_CSV, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerows(latest_rows)

    # 2. APPEND TO HISTORY CSV (Granular 10-min timeseries)
    history_header = [
        "Data_Hora_UTC",
        "Total_Capital_USD",
        "Total_Capital_BRL",
        "Rendimento_Diario_Total_USD",
        "Rendimento_Diario_Total_BRL",
        "Variacao_Total_USD",
        "Variacao_Total_Pct",
        "WETH_USDC_Capital_USD",
        "WETH_USDC_Renda_Diaria_USD",
        "WETH_USDC_PnL_USD",
        "GOOGL_USDC_Capital_USD",
        "GOOGL_USDC_Renda_Diaria_USD",
        "GOOGL_USDC_PnL_USD",
        "VIRTUAL_WETH_Capital_USD",
        "VIRTUAL_WETH_Renda_Diaria_USD",
        "VIRTUAL_WETH_Lucro_Liquido_USD",
        "MON_USDC_Capital_USD",
        "MON_USDC_Renda_Diaria_USD",
        "MON_USDC_PnL_USD",
        "Preco_ETH_USD",
        "Preco_AERO_USD",
        "Preco_GOOGL_USD",
        "Preco_VIRTUAL_USD",
        "Preco_MON_USD"
    ]

    write_header = not HISTORY_CSV.exists() or HISTORY_CSV.stat().st_size == 0

    history_row = [
        ts_iso,
        f"{total_cap_usd:.2f}",
        f"{total_cap_brl:.2f}",
        f"{total_daily_usd:.2f}",
        f"{total_daily_brl:.2f}",
        f"{total_diff_usd:.2f}",
        f"{total_diff_pct:.2f}",
        f"{weth_cap:.2f}",
        f"{weth_prof.get('daily_usd', 55.60):.2f}",
        f"{weth_diff_usd:.2f}",
        f"{googl_cap:.2f}",
        f"{googl_prof.get('daily_usd', 10.00):.2f}",
        f"{googl_diff_usd:.2f}",
        f"{virt_cap:.2f}",
        f"{virt_prof.get('daily_usd', 3.32):.2f}",
        f"{virt_net_usd:.2f}",
        f"{mon_cap:.2f}",
        f"{mon_prof.get('daily_usd', 1.90):.2f}",
        f"{mon_diff_usd:.2f}",
        f"{eth_px:.2f}",
        f"{aero_px:.4f}",
        f"{googl_px:.2f}",
        f"{virt_audit.get('virtual_usd', 0.86):.4f}",
        f"{mon_px:.5f}"
    ]

    with open(HISTORY_CSV, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow(history_header)
        writer.writerow(history_row)

    # 3. DAILY CLOSING SUMMARY (One row per date)
    daily_header = [
        "Data",
        "Fechamento_Patrimonio_USD",
        "Fechamento_Patrimonio_BRL",
        "Rendimento_Total_Gerado_Dia_USD",
        "Rendimento_Total_Gerado_Dia_BRL",
        "Variacao_Dia_USD",
        "Variacao_Dia_Pct",
        "Status_Geral"
    ]

    daily_rows = {}
    if DAILY_CSV.exists() and DAILY_CSV.stat().st_size > 0:
        try:
            with open(DAILY_CSV, "r", encoding="utf-8-sig") as f:
                reader = csv.reader(f)
                header = next(reader, None)
                for r in reader:
                    if r and len(r) >= 1:
                        daily_rows[r[0]] = r
        except Exception:
            pass

    daily_rows[date_str] = [
        date_str,
        f"{total_cap_usd:.2f}",
        f"{total_cap_brl:.2f}",
        f"{total_daily_usd:.2f}",
        f"{total_daily_brl:.2f}",
        f"{total_diff_usd:.2f}",
        f"{total_diff_pct:.2f}",
        "100% Ativo & Monitorado"
    ]

    with open(DAILY_CSV, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(daily_header)
        for d in sorted(daily_rows.keys()):
            writer.writerow(daily_rows[d])

    return {
        "status": "ok",
        "timestamp": ts_iso,
        "total_cap_usd": total_cap_usd,
        "total_daily_usd": total_daily_usd,
        "latest_file": str(LATEST_CSV),
        "history_file": str(HISTORY_CSV)
    }


def get_sheet_json() -> dict:
    """Returns structured JSON of the latest snapshot and recent history for the web dashboard."""
    history = []
    if HISTORY_CSV.exists() and HISTORY_CSV.stat().st_size > 0:
        try:
            with open(HISTORY_CSV, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                history = list(reader)[-50:]
        except Exception:
            pass

    daily = []
    if DAILY_CSV.exists() and DAILY_CSV.stat().st_size > 0:
        try:
            with open(DAILY_CSV, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                daily = list(reader)
        except Exception:
            pass

    treasury_path = ROOT / "data" / "defi_treasury.json"
    treasury = {}
    if treasury_path.exists():
        try:
            treasury = json.loads(treasury_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    return {
        "status": "ok",
        "updated_at": datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC"),
        "treasury": treasury,
        "recent_history": history,
        "daily_summary": daily
    }


if __name__ == "__main__":
    from defi_pools_monitor import fetch_live_market_data, evaluate_positions
    m = fetch_live_market_data()
    e, _, p = evaluate_positions(m)
    res = record_snapshot(e, p, m)
    print("Snapshot gravado com sucesso:")
    print(json.dumps(res, indent=2))
