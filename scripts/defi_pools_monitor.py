#!/usr/bin/env python3
"""
DeFi Pools 24/7 Cloud Sentinel & Multi-Chain Range Monitor
Monitors active concentrated liquidity positions across Base and Monad:
1. WETH / USDC (Aerodrome Slipstream 100 via Mellow #76829985 - Base)
2. USDC / GOOGLc (Aerodrome Slipstream 10 Gauge Staked #7508296 - Base)
3. VIRTUAL / WETH (Uniswap V3 via Krystal Autopilot NFT #6125710 - Base)
4. MON / USDC (Uniswap v4 Concentrated Liquidity - Monad)

Features:
- Live price tracking from DexScreener & CoinGecko
- Live accrued profit, fees and rewards calculation
- Proximity alerts when price is < 2.0% from ceiling or floor
- Immediate out-of-range breach notifications
- Periodic scheduled reports (every 4 hours)
- Telegram alert dispatch with intelligent cooldown/throttling
"""

from __future__ import annotations

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

# Load environment
env_file = ROOT / ".env"
if env_file.exists():
    for line in env_file.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
CHAT_ID = os.environ.get("TELEGRAM_SIGNALS_CHAT_ID", os.environ.get("TELEGRAM_CHAT_ID", "")).strip()

POSITIONS = [
    {
        "id": "weth_usdc",
        "name": "WETH / USDC (Slipstream 100)",
        "chain": "Base (Layer 2)",
        "protocol": "Aerodrome Finance (Mellow)",
        "type": "Cofre Conservador (Âncora)",
        "capital_usd": 10209.27,
        "range_min": 2596.73,
        "range_max": 2785.00,
        "unit": "USDC/ETH",
        "deposit_id": "#76829985",
        "pair_address": "0xcd975e6a5f55137755487f0918b8ca74acce7925",
        "price_key": "eth",
        "price_field": "price",
        "daily_usd": 42.95,
        "apr": "~148.0% a.a.",
        "start_iso": "2026-09-30T12:00:00+00:00",
        "profit_type": "emissions",
        "emissions_per_hour": 2.25
    },
    {
        "id": "usdc_googlc",
        "name": "USDC / GOOGLc (Slipstream 10)",
        "chain": "Base (Layer 2)",
        "protocol": "Aerodrome Finance",
        "type": "Stocks RWA (Staked no Gauge)",
        "capital_usd": 977.39,
        "range_min": 327.05,
        "range_max": 361.09,
        "unit": "USDC/GOOGLc",
        "deposit_id": "#7508296",
        "pair_address": "0xB1987CAD1682841b4b641d50E520777eC5Ab5542",
        "price_key": "googlc",
        "price_field": "price",
        "daily_usd": 10.00,
        "apr": "3,754.0% a.a.",
        "start_iso": "2026-10-02T17:20:00+00:00",
        "profit_type": "gauge"
    },
    {
        "id": "virtual_weth",
        "name": "VIRTUAL / WETH 0.05% (#6125710)",
        "chain": "Base (Layer 2)",
        "protocol": "Uniswap V3 (Krystal Autopilot)",
        "type": "Narrativa IA (Auto-Rebalance)",
        "capital_usd": 406.80,
        "range_min": 0.00027176,
        "range_max": 0.00028885,
        "unit": "WETH/VIRTUAL",
        "deposit_id": "NFT #6125710",
        "pair_address": "0x9c087Eb773291e50CF6c6a90ef0F4500e349B903",
        "price_key": "virtual",
        "price_field": "price_native",
        "daily_usd": 1.32,
        "apr": "~118.7% a.a.",
        "start_iso": "2026-09-30T21:45:00+00:00",
        "profit_type": "fees_collected",
        "base_fees_collected": 7.31
    },
    {
        "id": "mon_usdc",
        "name": "MON / USDC (Concentrated Liquidity)",
        "chain": "Monad (Layer 1)",
        "protocol": "Uniswap v4",
        "type": "Ecossistema Monad",
        "capital_usd": 331.98,
        "range_min": 0.02539,
        "range_max": 0.03716,
        "unit": "USDC/MON",
        "deposit_id": "Uniswap v4 Pool",
        "pair_address": "0x659bD0BC4167BA25c62E05656F78043E7eD4a9da",
        "price_key": "mon",
        "price_field": "price",
        "daily_usd": 1.90,
        "apr": "208.81% a.a.",
        "start_iso": "2026-10-02T18:00:00+00:00",
        "profit_type": "fees"
    }
]


def fetch_json(url: str, timeout: int = 8) -> dict | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"[-] Fetch error ({url}): {e}")
        return None


def fetch_live_market_data() -> dict:
    """Fetch live market data across CoinGecko and DexScreener."""
    data = {}

    # 1. ETH & AERO from CoinGecko
    cg = fetch_json("https://api.coingecko.com/api/v3/simple/price?ids=ethereum,aerodrome-finance&vs_currencies=usd&include_24hr_change=true")
    if cg:
        eth_info = cg.get("ethereum", {})
        aero_info = cg.get("aerodrome-finance", {})
        data["eth"] = {
            "price": float(eth_info.get("usd", 2746.0)),
            "change_24h": float(eth_info.get("usd_24h_change", 0.0))
        }
        data["aero"] = {
            "price": float(aero_info.get("usd", 0.795)),
            "change_24h": float(aero_info.get("usd_24h_change", 0.0))
        }
    else:
        data["eth"] = {"price": 2746.0, "change_24h": 0.0}
        data["aero"] = {"price": 0.795, "change_24h": 0.0}

    # 2. GOOGLc (Base DexScreener)
    ds_googl = fetch_json("https://api.dexscreener.com/latest/dex/pairs/base/0xB1987CAD1682841b4b641d50E520777eC5Ab5542")
    if ds_googl:
        p = ds_googl.get("pair") or (ds_googl.get("pairs") and ds_googl.get("pairs")[0])
        if p:
            data["googlc"] = {
                "price": float(p.get("priceUsd", 344.43)),
                "change_24h": float(p.get("priceChange", {}).get("h24", 0.0)),
                "tvl": float(p.get("liquidity", {}).get("usd", 0.0)),
                "vol24h": float(p.get("volume", {}).get("h24", 0.0))
            }
    if "googlc" not in data:
        data["googlc"] = {"price": 344.43, "change_24h": 0.0, "tvl": 1700000.0, "vol24h": 11000000.0}

    # 3. VIRTUAL / WETH (Base Uniswap V3 DexScreener)
    ds_virt = fetch_json("https://api.dexscreener.com/latest/dex/pairs/base/0x9c087Eb773291e50CF6c6a90ef0F4500e349B903")
    if ds_virt:
        p = ds_virt.get("pair") or (ds_virt.get("pairs") and ds_virt.get("pairs")[0])
        if p:
            data["virtual"] = {
                "price_native": float(p.get("priceNative", 0.0002815)),
                "price_usd": float(p.get("priceUsd", 0.75)),
                "change_24h": float(p.get("priceChange", {}).get("h24", 0.0)),
                "tvl": float(p.get("liquidity", {}).get("usd", 0.0)),
                "vol24h": float(p.get("volume", {}).get("h24", 0.0))
            }
    if "virtual" not in data:
        data["virtual"] = {"price_native": 0.0002815, "price_usd": 0.75, "change_24h": 0.0, "tvl": 2500000.0, "vol24h": 15000000.0}

    # 4. MON / USDC (Monad Uniswap v4 DexScreener)
    ds_mon = fetch_json("https://api.dexscreener.com/latest/dex/pairs/monad/0x659bD0BC4167BA25c62E05656F78043E7eD4a9da")
    if ds_mon:
        p = ds_mon.get("pair") or (ds_mon.get("pairs") and ds_mon.get("pairs")[0])
        if p:
            data["mon"] = {
                "price": float(p.get("priceUsd", 0.03218)),
                "change_24h": float(p.get("priceChange", {}).get("h24", 0.0)),
                "tvl": float(p.get("liquidity", {}).get("usd", 0.0)),
                "vol24h": float(p.get("volume", {}).get("h24", 0.0))
            }
    if "mon" not in data:
        data["mon"] = {"price": 0.03218, "change_24h": 0.0, "tvl": 1475000.0, "vol24h": 3318000.0}

    return data


def calculate_profit_metrics(market: dict) -> dict:
    """Calculates live accrued profit and daily cash flow for all positions."""
    now = datetime.now(timezone.utc)
    aero_px = market.get("aero", {}).get("price", 0.795)
    
    # 1. WETH / USDC
    t_weth = datetime.fromisoformat("2026-09-30T12:00:00+00:00")
    hours_weth = max((now - t_weth).total_seconds() / 3600.0, 0)
    weth_aero_accrued = hours_weth * 2.25
    weth_usd_accrued = weth_aero_accrued * aero_px

    # 2. GOOGLc
    t_googl = datetime.fromisoformat("2026-10-02T17:20:00+00:00")
    hours_googl = max((now - t_googl).total_seconds() / 3600.0, 0)
    googl_usd_accrued = hours_googl * (10.0 / 24.0)

    # 3. VIRTUAL / WETH
    t_virt_latest = datetime.fromisoformat("2026-10-02T19:30:00+00:00")
    hours_virt = max((now - t_virt_latest).total_seconds() / 3600.0, 0)
    virt_usd_accrued = 7.31 + (hours_virt * (1.32 / 24.0))

    # 4. MON / USDC
    t_mon = datetime.fromisoformat("2026-10-02T18:00:00+00:00")
    hours_mon = max((now - t_mon).total_seconds() / 3600.0, 0)
    mon_usd_accrued = hours_mon * (1.90 / 24.0)

    total_accrued_usd = weth_usd_accrued + googl_usd_accrued + virt_usd_accrued + mon_usd_accrued
    total_daily_usd = 42.95 + 10.00 + 1.32 + 1.90

    return {
        "weth_usdc": {
            "daily_usd": 42.95,
            "daily_brl": 42.95 * 5.50,
            "accrued_usd": weth_usd_accrued,
            "accrued_brl": weth_usd_accrued * 5.50,
            "accrued_aero": weth_aero_accrued,
            "accrued_text": f"~{weth_aero_accrued:.1f} AERO (~${weth_usd_accrued:.2f} USD / R$ {weth_usd_accrued*5.5:.2f})",
            "apr": "~148.0% a.a."
        },
        "usdc_googlc": {
            "daily_usd": 10.00,
            "daily_brl": 10.00 * 5.50,
            "accrued_usd": googl_usd_accrued,
            "accrued_brl": googl_usd_accrued * 5.50,
            "accrued_text": f"~${googl_usd_accrued:.2f} USD (~R$ {googl_usd_accrued*5.5:.2f})",
            "apr": "3,754.0% a.a. (Staked)"
        },
        "virtual_weth": {
            "daily_usd": 1.32,
            "daily_brl": 1.32 * 5.50,
            "accrued_usd": virt_usd_accrued,
            "accrued_brl": virt_usd_accrued * 5.50,
            "accrued_text": f"+${virt_usd_accrued:.2f} USD (~R$ {virt_usd_accrued*5.5:.2f}) (Taxas Puras)",
            "apr": "~118.7% a.a."
        },
        "mon_usdc": {
            "daily_usd": 1.90,
            "daily_brl": 1.90 * 5.50,
            "accrued_usd": mon_usd_accrued,
            "accrued_brl": mon_usd_accrued * 5.50,
            "accrued_text": f"~${mon_usd_accrued:.2f} USD (~R$ {mon_usd_accrued*5.5:.2f})",
            "apr": "208.81% a.a."
        },
        "portfolio": {
            "total_daily_usd": total_daily_usd,
            "total_daily_brl": total_daily_usd * 5.50,
            "total_monthly_usd": total_daily_usd * 30,
            "total_monthly_brl": total_daily_usd * 30 * 5.50,
            "total_accrued_usd": total_accrued_usd,
            "total_accrued_brl": total_accrued_usd * 5.50,
            "accrued_text": f"~${total_accrued_usd:.2f} USD (~R$ {total_accrued_usd*5.5:.2f})"
        }
    }


def evaluate_positions(market: dict) -> tuple[list[dict], bool, dict]:
    """Analyzes each position, calculates distances, profit metrics and checks alert thresholds."""
    evaluated = []
    has_urgent_alert = False
    profits = calculate_profit_metrics(market)

    for pos in POSITIONS:
        m_info = market.get(pos["price_key"], {})
        px = m_info.get(pos["price_field"], 0.0)
        p_min = pos["range_min"]
        p_max = pos["range_max"]

        if px <= 0:
            continue

        dist_ceiling_pct = ((p_max - px) / px) * 100.0
        dist_floor_pct = ((px - p_min) / px) * 100.0

        is_out = False
        is_warning = False
        status_text = ""

        if px > p_max:
            status_text = f"🔴 *FORA DO RANGE (ROMPEU O TETO +{abs(dist_ceiling_pct):.2f}%)*"
            is_out = True
            has_urgent_alert = True
        elif px < p_min:
            status_text = f"🔴 *FORA DO RANGE (ROMPEU O PISO -{abs(dist_floor_pct):.2f}%)*"
            is_out = True
            has_urgent_alert = True
        elif dist_ceiling_pct < 2.0:
            status_text = f"🟡 *ATENÇÃO: Apenas +{dist_ceiling_pct:.2f}% do teto!*"
            is_warning = True
            has_urgent_alert = True
        elif dist_floor_pct < 2.0:
            status_text = f"🟡 *ATENÇÃO: Apenas -{dist_floor_pct:.2f}% do piso!*"
            is_warning = True
            has_urgent_alert = True
        else:
            status_text = "🟢 *100% IN RANGE (RENDENDO FORTE)*"

        pos_profit = profits.get(pos["id"], {})

        evaluated.append({
            "pos": pos,
            "current_price": px,
            "dist_ceiling": dist_ceiling_pct,
            "dist_floor": dist_floor_pct,
            "is_out": is_out,
            "is_warning": is_warning,
            "status_text": status_text,
            "change_24h": m_info.get("change_24h", 0.0),
            "profit": pos_profit
        })

    return evaluated, has_urgent_alert, profits


def generate_consolidated_report(evaluated: list[dict], profits: dict) -> str:
    """Builds clean, high-impact Telegram Markdown message with profit breakdown."""
    now_utc = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")
    total_capital = sum(item["pos"]["capital_usd"] for item in evaluated)
    p_info = profits.get("portfolio", {})

    lines = [
        "📡 *SENTINELA DEFI 24/7 — RADAR DE LIQUIDEZ & LUCROS*",
        f"⏱️ _Atualizado em {now_utc}_",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    ]

    for idx, item in enumerate(evaluated, 1):
        pos = item["pos"]
        px = item["current_price"]
        p_min = pos["range_min"]
        p_max = pos["range_max"]
        unit = pos["unit"]
        prof = item["profit"]

        if "WETH/VIRTUAL" in unit:
            px_fmt = f"{px:.8f}"
            min_fmt = f"{p_min:.8f}"
            max_fmt = f"{p_max:.8f}"
        elif "MON" in unit:
            px_fmt = f"${px:.5f}"
            min_fmt = f"${p_min:.5f}"
            max_fmt = f"${p_max:.5f}"
        else:
            px_fmt = f"${px:,.2f}"
            min_fmt = f"${p_min:,.2f}"
            max_fmt = f"${p_max:,.2f}"

        lines.append(f"📍 *{idx}. {pos['name']}* ({pos['chain']})")
        lines.append(f"  • *Preço Atual:* `{px_fmt} {unit}` ({item['change_24h']:+.2f}% 24h)")
        lines.append(f"  • *Sua Faixa:* `{min_fmt}` ↔ `{max_fmt}`")
        lines.append(f"  • *Dist. Teto:* `+{item['dist_ceiling']:.2f}%` | *Piso:* `-{item['dist_floor']:.2f}%`")
        lines.append(f"  • *Status:* {item['status_text']}")
        lines.append(f"  • *Lucro Acumulado:* `{prof.get('accrued_text')}`")
        lines.append(f"  • *Renda Estimada:* `~${prof.get('daily_usd'):.2f}/dia` (APR: *{prof.get('apr')}*)")
        lines.append(f"  • *Capital Alocado:* `${pos['capital_usd']:,.2f} USD` ({pos['deposit_id']})")
        lines.append("")

    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"💰 *Capital Total Alocado:* `${total_capital:,.2f} USD`")
    lines.append(f"📈 *LUCRO TOTAL ACUMULADO:* `{p_info.get('accrued_text')}`")
    lines.append(f"💵 *Renda Diária Est.:* `~${p_info.get('total_daily_usd'):.2f}/dia` (~R$ {p_info.get('total_daily_brl'):.2f}/dia)")
    lines.append(f"🚀 *Projeção Mensal:* `~${p_info.get('total_monthly_usd'):.2f}/mês` (~R$ {p_info.get('total_monthly_brl'):.2f}/mês)")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("🛡️ _Sentinela 24/7 ativo na nuvem (Render.com). Alertas em tempo real e consolidação a cada 4h._")

    return "\n".join(lines)


def generate_urgent_alert_message(item: dict, profits: dict) -> str:
    """Builds urgent targeted alert for a single position nearing or breaking range, WITH ACCRUED PROFIT."""
    pos = item["pos"]
    px = item["current_price"]
    unit = pos["unit"]
    now_utc = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")
    prof = item["profit"]
    p_info = profits.get("portfolio", {})

    if "WETH/VIRTUAL" in unit:
        px_fmt = f"{px:.8f}"
        min_fmt = f"{pos['range_min']:.8f}"
        max_fmt = f"{pos['range_max']:.8f}"
    else:
        px_fmt = f"${px:,.2f}" if px > 10 else f"${px:.5f}"
        min_fmt = f"${pos['range_min']:,.2f}" if pos['range_min'] > 10 else f"${pos['range_min']:.5f}"
        max_fmt = f"${pos['range_max']:,.2f}" if pos['range_max'] > 10 else f"${pos['range_max']:.5f}"

    lines = [
        "🚨 *ALERTA DE BORDA & RENDIMENTOS — SENTINELA DEFI*",
        f"⏱️ _{now_utc}_",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"📍 *Posição:* *{pos['name']}*",
        f"🌐 *Rede:* {pos['chain']} | {pos['protocol']}",
        f"💵 *Preço Atual:* `{px_fmt} {unit}`",
        f"🎯 *Faixa Ativa:* `{min_fmt}` ↔ `{max_fmt}`",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"⚠️ *Situação:* {item['status_text']}",
        f"• *Distância do Teto:* `+{item['dist_ceiling']:.2f}%`",
        f"• *Distância do Piso:* `-{item['dist_floor']:.2f}%`",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "💰 *LUCRO & RENDIMENTOS DESSA POSIÇÃO:*",
        f"• *Renda Gerada:* `~${prof.get('daily_usd'):.2f} / dia` (~R$ {prof.get('daily_brl'):.2f}/dia)",
        f"• *Lucro Acumulado Est.:* `{prof.get('accrued_text')}`",
        f"• *APR Real da Pool:* *{prof.get('apr')}*",
        f"• *Capital Alocado:* `${pos['capital_usd']:,.2f} USD`",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "📊 *LUCRO TOTAL DA SUA CARTEIRA (4 POOLS):*",
        f"💵 *Renda Diária Total:* `~${p_info.get('total_daily_usd'):.2f} / dia` (~R$ {p_info.get('total_daily_brl'):.2f}/dia)",
        f"📈 *Lucro Total Acumulado:* `{p_info.get('accrued_text')}`",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "💡 *Ação Sugerida:* Avalie se é necessário rebalancear manualmente a faixa ou aguardar o recuo para o centro do range."
    ]
    return "\n".join(lines)


def send_telegram(text: str) -> bool:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip() or TOKEN
    chat_id = os.environ.get("TELEGRAM_SIGNALS_CHAT_ID", os.environ.get("TELEGRAM_CHAT_ID", "")).strip() or CHAT_ID
    if not token or not chat_id:
        print("[-] Telegram bot token or chat ID missing.")
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
        with urllib.request.urlopen(req, timeout=10) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            ok = res.get("ok", False)
            print(f"[*] Telegram message sent: {ok}")
            return ok
    except Exception as e:
        print(f"[-] Telegram dispatch error: {e}")
        return False


def run_sentinel_loop():
    """Runs 24/7 background sentinel loop with routine reports & urgent alerts."""
    print("[*] Iniciando Sentinela DeFi 24/7 com Módulo de Lucro em modo contínuo...")

    last_routine_report = 0.0
    alert_cooldowns: dict[str, float] = {}  # pos_id -> timestamp of last urgent alert

    ROUTINE_INTERVAL_SEC = 4 * 3600  # Every 4 hours
    CHECK_INTERVAL_SEC = 300         # Check prices every 5 minutes
    ALERT_COOLDOWN_SEC = 7200        # Max 1 warning alert per position per 2 hours (unless out of range)

    while True:
        try:
            market = fetch_live_market_data()
            evaluated, has_urgent, profits = evaluate_positions(market)
            now = time.time()

            # 1. Check for urgent alerts on each position
            for item in evaluated:
                pos_id = item["pos"]["id"]
                if item["is_out"] or item["is_warning"]:
                    last_alert_time = alert_cooldowns.get(pos_id, 0.0)
                    cooldown = 1800 if item["is_out"] else ALERT_COOLDOWN_SEC
                    if now - last_alert_time > cooldown:
                        alert_msg = generate_urgent_alert_message(item, profits)
                        print(f"[!] Disparando alerta com lucros para {pos_id}...")
                        send_telegram(alert_msg)
                        alert_cooldowns[pos_id] = now

            # 2. Routine 4-hour consolidated report
            if now - last_routine_report >= ROUTINE_INTERVAL_SEC:
                report = generate_consolidated_report(evaluated, profits)
                print("[*] Enviando relatório consolidado periódico de 4h...")
                send_telegram(report)
                last_routine_report = now

        except Exception as e:
            print(f"[-] Erro no loop do sentinela: {e}")

        time.sleep(CHECK_INTERVAL_SEC)


if __name__ == "__main__":
    market_data = fetch_live_market_data()
    eval_list, urgent, prof_data = evaluate_positions(market_data)
    rep = generate_consolidated_report(eval_list, prof_data)
    print(rep)

    if "--send" in sys.argv:
        send_telegram(rep)

    if "--test-alert" in sys.argv and eval_list:
        sample_alert = generate_urgent_alert_message(eval_list[0], prof_data)
        print("\n--- SAMPLE URGENT ALERT WITH PROFIT ---")
        print(sample_alert)
        if "--send" in sys.argv:
            send_telegram(sample_alert)

    if "--loop" in sys.argv:
        run_sentinel_loop()
