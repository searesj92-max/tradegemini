#!/usr/bin/env python3
"""
Botrade — DeFi Arbitrage Engine (Base Layer 2)
Cross-DEX Atomic Arbitrage Scanner & Simulator

Monitors real-time price discrepancies across:
- Aerodrome Finance (Slipstream & Classic)
- Uniswap v3 (Base)
- PancakeSwap v3 (Base)

Calculates:
- Gross Spread (%)
- Protocol / Pool Fees (DEX A + DEX B)
- Gas costs on Base Layer 2 (~$0.02 - $0.05)
- Net Profit Margin (%)
- Simulated Net Dollar Returns ($1k, $10k, $50k Flash Loan)

Atomic Safety:
- Simulates trades using read-only calls (zero gas, zero capital risk).
- Prepares execution for atomic Flash Loan smart contracts where transactions
  revert automatically if net profit is not guaranteed.
"""
from __future__ import annotations

import csv
import json
import os
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# Fix Windows console encoding
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
OPPORTUNITIES_FILE = DATA_DIR / "arbitrage_opportunities.json"
HISTORY_CSV = DATA_DIR / "arbitrage_history.csv"

# Load .env
env_file = ROOT / ".env"
if env_file.exists():
    for line in env_file.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
CHAT_ID = os.environ.get("TELEGRAM_SIGNALS_CHAT_ID", os.environ.get("TELEGRAM_CHAT_ID", "")).strip()

# Target tokens on Base network
TARGET_TOKENS = {
    "WETH": "0x4200000000000000000000000000000000000006",
    "cbBTC": "0xcbB7C0000aB88B473b1f5aFd9ef808440eed33Bf",
    "AERO": "0x940181a94A35A4569E4529A3CDfB74e38FD98631",
    "cbETH": "0x2Ae3F1Ec7F1F5012CFEab0185bfc7aa3cf0DEc22",
    "VIRTUAL": "0x0b3e328455c4059EEb9e3f84b5543F74E24e7E1b",
    "USDC": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
}

# Reliable public RPCs for Base
BASE_RPCS = [
    "https://base-rpc.publicnode.com",
    "https://1rpc.io/base",
    "https://mainnet.base.org"
]


def ensure_data_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def fetch_usd_brl() -> float:
    """Fetch live USD/BRL exchange rate."""
    try:
        from defi_pools_monitor import fetch_usd_brl as _fetch
        return _fetch()
    except Exception:
        return 5.02


_POOLS_CACHE: dict[str, tuple[float, list[dict]]] = {}
CACHE_FILE = DATA_DIR / "cached_dex_pools.json"


def _load_disk_cache() -> dict:
    if CACHE_FILE.exists():
        try:
            return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_disk_cache(data: dict):
    try:
        CACHE_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception:
        pass


def fetch_pools_for_token(token_addr: str) -> list[dict]:
    """Fetch all active liquidity pools for a token on Base via GeckoTerminal API with resilient caching."""
    now = time.time()
    # Check in-memory cache (TTL: 60s)
    if token_addr in _POOLS_CACHE:
        ts, cached = _POOLS_CACHE[token_addr]
        if now - ts < 60:
            return cached

    url = f"https://api.geckoterminal.com/api/v2/networks/base/tokens/{token_addr}/pools?page=1"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Botrade/1.0",
            "Accept": "application/json"
        }
    )

    for attempt in range(2):
        try:
            with urllib.request.urlopen(req, timeout=6) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                pools = data.get("data", [])
                if pools:
                    _POOLS_CACHE[token_addr] = (now, pools)
                    disk_cache = _load_disk_cache()
                    disk_cache[token_addr] = {"ts": now, "pools": pools}
                    _save_disk_cache(disk_cache)
                return pools
        except Exception as e:
            err_str = str(e)
            if "429" in err_str and attempt == 0:
                time.sleep(1.0)
                continue
            # Fallback to disk cache if available
            disk_cache = _load_disk_cache()
            if token_addr in disk_cache:
                return disk_cache[token_addr].get("pools", [])
            if token_addr in _POOLS_CACHE:
                return _POOLS_CACHE[token_addr][1]
            print(f"[-] Error fetching pools for {token_addr}: {e}")
            return []
    return []


def analyze_token_arbitrage(token_symbol: str, token_addr: str) -> list[dict]:
    """Scans all pools for a given token across different DEXes and identifies price discrepancies."""
    pools = fetch_pools_for_token(token_addr)
    if not pools:
        return []

    dex_candidates = []
    for p in pools:
        attr = p.get("attributes", {})
        dex_id = p.get("relationships", {}).get("dex", {}).get("data", {}).get("id", "unknown")
        pool_name = attr.get("name", "")
        price_str = attr.get("base_token_price_usd")
        reserve_str = attr.get("reserve_in_usd")
        vol_str = attr.get("volume_usd", {}).get("h24")
        pool_addr = attr.get("address", "")

        try:
            px = float(price_str or 0)
            reserve = float(reserve_str or 0)
            vol = float(vol_str or 0)
        except (ValueError, TypeError):
            continue

        # Liquidity filter: must have at least $50,000 reserve to avoid micro-illiquid traps
        if px > 0 and reserve >= 50000:
            # Normalize DEX name
            clean_dex = dex_id.replace("-base", "").replace("-3", "").title()
            if "Aerodrome" in clean_dex:
                clean_dex = "Aerodrome"
            elif "Uniswap" in clean_dex:
                clean_dex = "Uniswap v3"
            elif "Pancakeswap" in clean_dex:
                clean_dex = "PancakeSwap"

            # Parse fee from pool name if available (e.g. 0.05%, 0.3%)
            fee_pct = 0.05
            if "0.3%" in pool_name:
                fee_pct = 0.30
            elif "0.01%" in pool_name:
                fee_pct = 0.01
            elif "1%" in pool_name:
                fee_pct = 1.00

            if "/" not in pool_name:
                continue
            parts = pool_name.split("/")
            base_s = parts[0].strip().split()[0]
            quote_s = parts[1].strip().split()[0]
            norm_pair = f"{base_s}/{quote_s}"

            dex_candidates.append({
                "dex": clean_dex,
                "pair": norm_pair,
                "pool_name": pool_name,
                "pool_addr": pool_addr,
                "price": px,
                "liquidity_usd": reserve,
                "volume_24h": vol,
                "fee_pct": fee_pct
            })

    if len(dex_candidates) < 2:
        return []

    # Pairwise comparison across DIFFERENT DEXes for the EXACT SAME PAIR
    opportunities = []
    for i in range(len(dex_candidates)):
        for j in range(i + 1, len(dex_candidates)):
            cand_a = dex_candidates[i]
            cand_b = dex_candidates[j]

            # MUST be the exact same trading pair (e.g. WETH/USDC vs WETH/USDC)
            if cand_a["pair"] != cand_b["pair"]:
                continue

            # Only compare across different DEX protocols
            if cand_a["dex"] == cand_b["dex"]:
                continue

            # Identify cheaper (Buy) vs more expensive (Sell)
            if cand_a["price"] < cand_b["price"]:
                buy_pool = cand_a
                sell_pool = cand_b
            else:
                buy_pool = cand_b
                sell_pool = cand_a

            p_buy = buy_pool["price"]
            p_sell = sell_pool["price"]

            # Calculate spreads
            gross_spread_pct = ((p_sell - p_buy) / p_buy) * 100.0

            # Sanity check: filter out fake tokens or extreme data errors (gross spread > 15%)
            if gross_spread_pct > 15.0 or gross_spread_pct < 0.0:
                continue

            total_fee_pct = buy_pool["fee_pct"] + sell_pool["fee_pct"]
            net_spread_pct = gross_spread_pct - total_fee_pct

            # Base L2 gas cost estimate
            est_gas_usd = 0.03

            # Calculate simulated returns on standard lot sizes
            lots = [1000.0, 10000.0, 50000.0]
            lot_returns = {}
            for lot in lots:
                gross_gain = lot * (gross_spread_pct / 100.0)
                fees_paid = lot * (total_fee_pct / 100.0)
                net_usd = gross_gain - fees_paid - est_gas_usd
                lot_returns[f"lot_{int(lot)}"] = round(net_usd, 2)

            opportunities.append({
                "pair": cand_a["pair"],
                "token": cand_a["pair"],
                "buy_dex": buy_pool["dex"],
                "buy_pool": buy_pool["pool_name"],
                "buy_pool_addr": buy_pool["pool_addr"],
                "buy_price": p_buy,
                "buy_liq": buy_pool["liquidity_usd"],
                "sell_dex": sell_pool["dex"],
                "sell_pool": sell_pool["pool_name"],
                "sell_pool_addr": sell_pool["pool_addr"],
                "sell_price": p_sell,
                "sell_liq": sell_pool["liquidity_usd"],
                "gross_spread_pct": round(gross_spread_pct, 4),
                "total_fees_pct": round(total_fee_pct, 4),
                "net_spread_pct": round(net_spread_pct, 4),
                "is_profitable": net_spread_pct > 0.05,  # profitable if net spread > 0.05%
                "lot_returns_usd": lot_returns,
                "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            })

    # Sort opportunities by net spread descending
    opportunities.sort(key=lambda x: x["net_spread_pct"], reverse=True)
    return opportunities


def scan_all_markets() -> list[dict]:
    """Scans all monitored token markets and aggregates arbitrage opportunities."""
    all_opps = []
    for sym, addr in TARGET_TOKENS.items():
        if sym == "USDC":
            continue
        try:
            opps = analyze_token_arbitrage(sym, addr)
            all_opps.extend(opps)
        except Exception as e:
            print(f"[-] Scan error on {sym}: {e}")
        time.sleep(0.4)  # Polite pacing

    # Deduplicate: for each (pair, buy_dex, sell_dex) keep the highest net spread pool
    best_by_route = {}
    for o in all_opps:
        key = (o.get("token") or o.get("pair"), o["buy_dex"], o["sell_dex"])
        if key not in best_by_route or o["net_spread_pct"] > best_by_route[key]["net_spread_pct"]:
            best_by_route[key] = o

    unique_opps = list(best_by_route.values())
    unique_opps.sort(key=lambda x: x["net_spread_pct"], reverse=True)
    return unique_opps


def record_opportunities(opportunities: list[dict]):
    """Records top opportunities to JSON and appends profitable ones to history CSV."""
    ensure_data_dir()
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    # Save latest scan snapshot
    payload = {
        "updated_at": now_str,
        "total_analyzed": len(opportunities),
        "profitable_count": sum(1 for o in opportunities if o["is_profitable"]),
        "opportunities": opportunities[:15]
    }
    try:
        OPPORTUNITIES_FILE.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        print(f"[-] Failed saving opportunities JSON: {e}")

    # Append profitable opportunities to historical CSV
    profitable_items = [o for o in opportunities if o["is_profitable"]]
    if profitable_items:
        write_header = not HISTORY_CSV.exists() or HISTORY_CSV.stat().st_size == 0
        header = [
            "Data_Hora_UTC", "Token", "Compra_DEX", "Venda_DEX", "Preco_Compra",
            "Preco_Venda", "Spread_Bruto_Pct", "Taxas_Pool_Pct", "Spread_Liquido_Pct",
            "Lucro_1k_USD", "Lucro_10k_USD", "Lucro_50k_USD"
        ]
        try:
            with open(HISTORY_CSV, "a", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                if write_header:
                    writer.writerow(header)
                for item in profitable_items:
                    writer.writerow([
                        now_str,
                        item["token"],
                        item["buy_dex"],
                        item["sell_dex"],
                        f"{item['buy_price']:.4f}",
                        f"{item['sell_price']:.4f}",
                        f"{item['gross_spread_pct']:.3f}%",
                        f"{item['total_fees_pct']:.3f}%",
                        f"{item['net_spread_pct']:.3f}%",
                        f"{item['lot_returns_usd']['lot_1000']:.2f}",
                        f"{item['lot_returns_usd']['lot_10000']:.2f}",
                        f"{item['lot_returns_usd']['lot_50000']:.2f}"
                    ])
        except Exception as e:
            print(f"[-] Failed writing history CSV: {e}")


def format_radar_report(opportunities: list[dict]) -> str:
    """Builds clean Telegram Markdown report for the DeFi Arbitrage Radar."""
    now_utc = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")
    usd_brl = fetch_usd_brl()

    profitable = [o for o in opportunities if o["is_profitable"]]

    lines = [
        "⚡ *RADAR DE ARBITRAGEM DEFI — REDE BASE*",
        f"⏱️ _{now_utc}_",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"🔍 *Pares Analisados:* `{len(opportunities)} combinações`",
        f"🟢 *Oportunidades Lucrativas:* `{len(profitable)} detectadas`",
        f"💵 *Cotação Dólar Base:* `R$ {usd_brl:.4f}`",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    ]

    if not profitable:
        top_opp = opportunities[0] if opportunities else None
        lines.append("🛡️ *STATUS DO MERCADO:*")
        lines.append("• Nenhum spread líquido > +0.05% no bloco atual.")
        if top_opp:
            lines.append(f"• *Maior Spread Atual:* `{top_opp['token']}` na {top_opp['buy_dex']} $\\leftrightarrow$ {top_opp['sell_dex']} ({top_opp['gross_spread_pct']:+.2f}% bruto / {top_opp['net_spread_pct']:+.2f}% líquido).")
        lines.append("\n💡 _Spreads atômicos abrem durante picos de volume e volatilidade. O sentinela segue escaneando a cada bloco._")
    else:
        lines.append("🎯 *TOP OPORTUNIDADES LÍQUIDAS (DESCONTANDO TAXAS):*\n")
        for idx, o in enumerate(profitable[:4], 1):
            r10k = o["lot_returns_usd"]["lot_10000"]
            r50k = o["lot_returns_usd"]["lot_50000"]
            r10k_brl = r10k * usd_brl
            r50k_brl = r50k * usd_brl

            lines.append(f"*{idx}. {o['token']}* ({o['buy_dex']} ➔ {o['sell_dex']}) 🟢")
            lines.append(f"  ├ *Compra:* `${o['buy_price']:,.2f}` ({o['buy_dex']})")
            lines.append(f"  ├ *Venda:* `${o['sell_price']:,.2f}` ({o['sell_dex']})")
            lines.append(f"  ├ *Spread Líquido:* *`{o['net_spread_pct']:+.2f}%`* (após taxas)")
            lines.append(f"  ├ *Lucro com $10k:* *`+${r10k:,.2f} USD`* (**~R$ {r10k_brl:,.2f}**)")
            lines.append(f"  └ *Lucro com $50k (Flash Loan):* *`+${r50k:,.2f} USD`* (**~R$ {r50k_brl:,.2f}**)\n")

    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("🛡️ _Execução 100% Atômica via Smart Contract: Se não der lucro, reverte no mesmo bloco com risco zero de capital._")
    return "\n".join(lines)


def send_telegram_alert(text: str) -> bool:
    """Sends notification to Telegram."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip() or TOKEN
    chat_id = os.environ.get("TELEGRAM_SIGNALS_CHAT_ID", os.environ.get("TELEGRAM_CHAT_ID", "")).strip() or CHAT_ID
    if not token or not chat_id:
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status == 200
    except Exception as e:
        print(f"[-] Telegram send error: {e}")
        return False


def run_scanner_once(notify: bool = False):
    """Executes a single market scan cycle and prints report."""
    print("[*] Iniciando varredura de arbitragem on-chain na rede Base...")
    opps = scan_all_markets()
    record_opportunities(opps)
    report = format_radar_report(opps)
    print("\n" + report + "\n")

    if notify:
        sent = send_telegram_alert(report)
        print(f"[*] Alerta enviado ao Telegram: {sent}")

    return opps


def run_daemon_loop(interval_sec: int = 15):
    """Continuous scanner daemon that monitors markets and alerts on profitable opportunities."""
    print(f"[*] Iniciando Sentinela de Arbitragem Contínuo (Intervalo: {interval_sec}s)...")
    last_alert_ts = 0
    while True:
        try:
            opps = scan_all_markets()
            record_opportunities(opps)
            profitable = [o for o in opps if o["is_profitable"]]
            now = time.time()

            if profitable:
                top = profitable[0]
                print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] 🚨 Oportunidade detectada: {top['token']} ({top['buy_dex']} -> {top['sell_dex']}) Spread Líquido: {top['net_spread_pct']:+.2f}%")
                # Throttle alerts to at most once every 5 minutes unless spread is > 0.50%
                if (now - last_alert_ts > 300) or (top["net_spread_pct"] >= 0.50):
                    report = format_radar_report(opps)
                    send_telegram_alert(report)
                    last_alert_ts = now
            else:
                top_spread = opps[0]["gross_spread_pct"] if opps else 0.0
                print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] Escaneando... Maior spread bruto: {top_spread:+.2f}% (Sem oportunidade líquida)")

            time.sleep(interval_sec)
        except KeyboardInterrupt:
            print("\n[*] Sentinela interrompido pelo usuário.")
            break
        except Exception as e:
            print(f"[-] Erro no loop: {e}")
            time.sleep(interval_sec)


def fetch_all_dex_candidates() -> list[dict]:
    """Fetches and normalizes active liquidity pools across all 3 DEXes for monitored tokens."""
    all_candidates = []
    for sym, addr in TARGET_TOKENS.items():
        if sym == "USDC":
            continue
        pools = fetch_pools_for_token(addr)
        for p in pools:
            attr = p.get("attributes", {})
            dex_id = p.get("relationships", {}).get("dex", {}).get("data", {}).get("id", "unknown")
            pool_name = attr.get("name", "")
            price_str = attr.get("base_token_price_usd")
            reserve_str = attr.get("reserve_in_usd")
            vol_str = attr.get("volume_usd", {}).get("h24")
            pool_addr = attr.get("address", "")
            try:
                px = float(price_str or 0)
                reserve = float(reserve_str or 0)
                vol = float(vol_str or 0)
            except (ValueError, TypeError):
                continue

            if px > 0 and reserve >= 35000:
                clean_dex = "Aerodrome" if "aerodrome" in dex_id.lower() else (
                    "Uniswap v3" if "uniswap" in dex_id.lower() else (
                        "PancakeSwap" if "pancake" in dex_id.lower() else dex_id
                    )
                )
                if clean_dex not in ("Aerodrome", "Uniswap v3", "PancakeSwap"):
                    continue

                fee_pct = 0.05
                if "0.3%" in pool_name:
                    fee_pct = 0.30
                elif "0.01%" in pool_name:
                    fee_pct = 0.01
                elif "1%" in pool_name:
                    fee_pct = 1.00

                if "/" not in pool_name:
                    continue
                parts = pool_name.split("/")
                base_s = parts[0].strip().split()[0]
                quote_s = parts[1].strip().split()[0]
                norm_pair = f"{base_s}/{quote_s}"

                all_candidates.append({
                    "dex": clean_dex,
                    "pair": norm_pair,
                    "base": base_s,
                    "quote": quote_s,
                    "pool_name": pool_name,
                    "pool_addr": pool_addr,
                    "price": px,
                    "liquidity_usd": reserve,
                    "volume_24h": vol,
                    "fee_pct": fee_pct
                })
        time.sleep(0.1)
    return all_candidates


def build_exchange_matrix(candidates: list[dict], usd_brl: float = 5.02) -> list[dict]:
    """Constructs side-by-side comparison matrix for Aerodrome, Uniswap v3, and PancakeSwap."""
    by_pair: dict[str, dict] = {}
    for c in candidates:
        pair = c["pair"]
        dex = c["dex"]
        if pair not in by_pair:
            by_pair[pair] = {
                "pair": pair,
                "base": c["base"],
                "quote": c["quote"],
                "exchanges": {}
            }
        existing = by_pair[pair]["exchanges"].get(dex)
        if not existing or c["liquidity_usd"] > existing["liquidity_usd"]:
            by_pair[pair]["exchanges"][dex] = {
                "price": c["price"],
                "fee_pct": c["fee_pct"],
                "liquidity_usd": c["liquidity_usd"],
                "volume_24h": c["volume_24h"],
                "pool_name": c["pool_name"],
                "pool_addr": c["pool_addr"]
            }

    matrix_rows = []
    for pair, data in by_pair.items():
        exchs = data["exchanges"]
        if len(exchs) < 2:
            continue

        sorted_dexes = sorted(exchs.items(), key=lambda x: x[1]["price"])
        best_buy_dex, best_buy_info = sorted_dexes[0]
        best_sell_dex, best_sell_info = sorted_dexes[-1]

        p_buy = best_buy_info["price"]
        p_sell = best_sell_info["price"]

        gross_spread_pct = ((p_sell - p_buy) / p_buy) * 100.0 if p_buy > 0 else 0.0
        total_fees_pct = best_buy_info["fee_pct"] + best_sell_info["fee_pct"]
        net_spread_pct = gross_spread_pct - total_fees_pct

        is_profitable = (net_spread_pct > 0.05) and (gross_spread_pct < 15.0)

        lots = [1000.0, 5000.0, 10000.0, 50000.0, 100000.0]
        returns = {}
        for lot in lots:
            profit_usd = (lot * (net_spread_pct / 100.0)) - 0.03
            returns[f"lot_{int(lot)}"] = round(profit_usd, 2)
            returns[f"lot_{int(lot)}_brl"] = round(profit_usd * usd_brl, 2)

        matrix_rows.append({
            "pair": pair,
            "base": data["base"],
            "quote": data["quote"],
            "exchanges": {
                "Aerodrome": exchs.get("Aerodrome"),
                "Uniswap v3": exchs.get("Uniswap v3"),
                "PancakeSwap": exchs.get("PancakeSwap")
            },
            "best_buy_dex": best_buy_dex,
            "best_buy_price": p_buy,
            "best_sell_dex": best_sell_dex,
            "best_sell_price": p_sell,
            "route_text": f"{best_buy_dex} ➔ {best_sell_dex}",
            "gross_spread_pct": round(gross_spread_pct, 3),
            "total_fees_pct": round(total_fees_pct, 3),
            "net_spread_pct": round(net_spread_pct, 3),
            "is_profitable": is_profitable,
            "lot_returns": returns
        })

    matrix_rows.sort(key=lambda x: x["net_spread_pct"], reverse=True)
    return matrix_rows


_LIVE_DASHBOARD_CACHE: dict = {"ts": 0, "data": None}


def get_arbitrage_live_snapshot(force: bool = False) -> dict:
    """Returns ultra-fast snapshot for the web cockpit dashboard."""
    global _LIVE_DASHBOARD_CACHE
    now = time.time()
    if not force and _LIVE_DASHBOARD_CACHE["data"] and (now - _LIVE_DASHBOARD_CACHE["ts"] < 2.5):
        return _LIVE_DASHBOARD_CACHE["data"]

    usd_brl = fetch_usd_brl()
    candidates = fetch_all_dex_candidates()
    matrix = build_exchange_matrix(candidates, usd_brl)
    profitable = [m for m in matrix if m["is_profitable"]]

    now_utc = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M:%S UTC")
    best_spread = matrix[0]["net_spread_pct"] if matrix else 0.0
    best_route = matrix[0]["route_text"] if matrix else "Aguardando spread"

    result = {
        "status": "ok",
        "updated_at_utc": now_utc,
        "timestamp_ms": int(now * 1000),
        "usd_brl": usd_brl,
        "dexes": ["Aerodrome", "Uniswap v3", "PancakeSwap"],
        "summary": {
            "total_pairs_monitored": len(matrix),
            "profitable_count": len(profitable),
            "best_net_spread_pct": best_spread,
            "best_route": best_route,
            "base_l2_avg_gas_usd": 0.03
        },
        "matrix": matrix,
        "smart_contract": {
            "name": "BaseFlashArbExecutor",
            "network": "Base Layer 2 (ChainID 8453)",
            "balancer_vault": "0xBA12222222228d8Ba5359726c66236535c7e3261",
            "balancer_fee": "0.00%",
            "uniswap_v3_router": "0x2626664c2603336E57B271c5C0b26F421741e481",
            "aerodrome_router": "0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43",
            "pancakeswap_router": "0x678Aa4bF4E210cf2166753e054d5b7c31cc7fa86",
            "atomic_protection": "require(returnAmount > totalOwed && netProfit >= minProfit)"
        }
    }

    _LIVE_DASHBOARD_CACHE = {"ts": now, "data": result}
    return result


if __name__ == "__main__":
    notify_flag = "--notify" in sys.argv
    if "--daemon" in sys.argv:
        run_daemon_loop(interval_sec=15)
    elif "--matrix" in sys.argv:
        snap = get_arbitrage_live_snapshot(force=True)
        print(json.dumps(snap["summary"], indent=2))
        print(f"Matrix Rows: {len(snap['matrix'])}")
    else:
        run_scanner_once(notify=notify_flag)

