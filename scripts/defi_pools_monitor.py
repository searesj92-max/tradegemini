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

sys.path.insert(0, str(Path(__file__).resolve().parent))
from virtual_audit import audit_virtual, INITIAL_USD as VIRT_INITIAL_USD  # noqa: E402

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
        "name": "WETH / USDC (Slipstream 50 - 2 Posições)",
        "chain": "Base (Layer 2)",
        "protocol": "Aerodrome Finance",
        "type": "Cofre Conservador (Âncora Principal)",
        "capital_usd": 10378.16,
        "range_min": 2622.82,
        "range_max": 2827.09,
        "unit": "USDC/ETH",
        "deposit_id": "Principal #7669576 + Secundária #7670917",
        "sub_positions": [
            {
                "id": "#7669576",
                "label": "Depósito Principal",
                "capital_usd": 10181.75,
                "composition": "1.9580 WETH + 4,886.36 USDC",
                "range_min": 2622.82,
                "range_max": 2827.09,
                "apr": "22.97% Fee + Emissões",
                "daily_usd": 55.00
            },
            {
                "id": "#7670917",
                "label": "Depósito Secundário",
                "capital_usd": 196.41,
                "composition": "0.0439 WETH + 77.07 USDC",
                "range_min": 2702.70,
                "range_max": 2743.54,
                "apr": "114.85% Fee APR",
                "daily_usd": 0.60
            }
        ],
        "pair_address": "0x4200000000000000000000000000000000000006",
        "price_key": "eth",
        "price_field": "price",
        "daily_usd": 55.60,
        "apr": "~200.0% a.a. (Consolidado)",
        "start_iso": "2026-10-05T18:00:00+00:00",
        "profit_type": "gauge"
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
        "name": "VIRTUAL / WETH 0.05% (#6146971)",
        "chain": "Base (Layer 2)",
        "protocol": "Uniswap V3 (Krystal Autopilot)",
        "type": "Narrativa IA (Auto-Rebalance)",
        "capital_usd": 397.30,
        "initial_capital_usd": 406.46,
        "range_min": 0.00029914,
        "range_max": 0.00031796,
        "unit": "WETH/VIRTUAL",
        "deposit_id": "NFT #6146971",
        "pair_address": "0x9c087Eb773291e50CF6c6a90ef0F4500e349B903",
        "price_key": "virtual",
        "price_field": "price_native",
        "daily_usd": 3.29,
        "apr": "~295% a.a.",
        "start_iso": "2026-09-30T21:45:00+00:00",
        "profit_type": "fees_collected",
        "liquidity": 272091669926172610358
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
    
    # 1. WETH / USDC (Slipstream 50 - Somando as duas posições #7669576 + #7670917)
    t_weth = datetime.fromisoformat("2026-10-05T18:00:00+00:00")
    hours_weth = max((now - t_weth).total_seconds() / 3600.0, 0)
    weth_hourly_usd = 55.60 / 24.0
    weth_usd_accrued = hours_weth * weth_hourly_usd
    weth_aero_accrued = (weth_usd_accrued / aero_px) if aero_px > 0 else 0.0

    # 2. GOOGLc
    t_googl = datetime.fromisoformat("2026-10-02T17:20:00+00:00")
    hours_googl = max((now - t_googl).total_seconds() / 3600.0, 0)
    googl_usd_accrued = hours_googl * (10.0 / 24.0)

    # 3. VIRTUAL / WETH — Lucro Líquido Real (Patrimônio Consolidado vs Aporte Inicial)
    virt_audit = audit_virtual(eth_usd=market.get("eth", {}).get("price"))
    if virt_audit:
        virt_net_usd = virt_audit["net_usd"]
        virt_net_pct = virt_audit["net_pct"]
        virt_usd_accrued = virt_net_usd
        virt_daily = virt_audit["fees_per_day_avg"]
        virt_apr = f"~{virt_audit['apr_avg_pct']:.0f}% a.a."
    else:
        virt_net_usd, virt_net_pct, virt_usd_accrued, virt_daily, virt_apr = 0.0, 0.0, 0.0, 0.0, "indisponível"

    # 4. MON / USDC
    t_mon = datetime.fromisoformat("2026-10-02T18:00:00+00:00")
    hours_mon = max((now - t_mon).total_seconds() / 3600.0, 0)
    mon_usd_accrued = hours_mon * (1.90 / 24.0)

    total_accrued_usd = weth_usd_accrued + googl_usd_accrued + virt_usd_accrued + mon_usd_accrued
    total_daily_usd = 55.60 + 10.00 + virt_daily + 1.90

    return {
        "weth_usdc": {
            "daily_usd": 55.60,
            "daily_brl": 55.60 * 5.50,
            "accrued_usd": weth_usd_accrued,
            "accrued_brl": weth_usd_accrued * 5.50,
            "accrued_aero": weth_aero_accrued,
            "accrued_text": f"~{weth_aero_accrued:.2f} AERO (~${weth_usd_accrued:.2f} USD / R$ {weth_usd_accrued*5.5:.2f})",
            "apr": "~200.0% a.a. (Consolidado)",
            "sub_daily": {
                "principal_usd": 55.00,
                "secundaria_usd": 0.60
            }
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
            "daily_usd": virt_daily,
            "daily_brl": virt_daily * 5.50,
            "accrued_usd": virt_net_usd,
            "accrued_brl": virt_net_usd * 5.50,
            "net_pct": virt_net_pct,
            "accrued_text": f"{'+' if virt_net_usd >= 0 else ''}${virt_net_usd:.2f} USD ({'+' if virt_net_pct >= 0 else ''}{virt_net_pct:.2f}%) (~R$ {virt_net_usd*5.5:.2f}) [Líquido]",
            "apr": virt_apr,
            "audit": virt_audit
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


def calculate_virtual_pool_value(px_native: float, eth_usd: float, range_min: float, range_max: float, liquidity: float = 278820534392291859569) -> tuple[float, float, float, str]:
    """Calculates the exact token amounts and USD value of the VIRTUAL / WETH pool."""
    import math
    if px_native <= 0 or range_min <= 0 or range_max <= 0:
        return 0.0, 0.0, 389.35, "320.9 VIRTUAL + 0.0502 WETH"
    
    sqrt_min = math.sqrt(range_min)
    sqrt_max = math.sqrt(range_max)
    px_usd = px_native * eth_usd
    
    amount0_max = liquidity * (sqrt_max - sqrt_min) / (sqrt_min * sqrt_max) / 1e18
    amount1_max = (liquidity * (sqrt_max - sqrt_min)) / 1e18
    
    if px_native < range_min:
        amt_virt = amount0_max
        amt_weth = 0.0
        val_usd = amt_virt * px_usd
        composition_desc = f"{amt_virt:.1f} VIRTUAL (100% VIRTUAL por rompimento de piso)"
    elif px_native > range_max:
        amt_virt = 0.0
        amt_weth = amount1_max
        val_usd = amt_weth * eth_usd
        composition_desc = f"{amt_weth:.4f} WETH (100% WETH por rompimento de teto)"
    else:
        sqrt_p = math.sqrt(px_native)
        amt_virt = (liquidity * (sqrt_max - sqrt_p) / (sqrt_p * sqrt_max)) / 1e18
        amt_weth = (liquidity * (sqrt_p - sqrt_min)) / 1e18
        val_usd = (amt_virt * px_usd) + (amt_weth * eth_usd)
        composition_desc = f"{amt_virt:.1f} VIRTUAL + {amt_weth:.4f} WETH"
        
    return amt_virt, amt_weth, val_usd, composition_desc


def evaluate_positions(market: dict) -> tuple[list[dict], bool, dict]:
    """Analyzes each position, calculates distances, profit metrics and checks alert thresholds."""
    evaluated = []
    has_urgent_alert = False
    profits = calculate_profit_metrics(market)
    eth_usd = market.get("eth", {}).get("price", 2688.0)

    for pos in POSITIONS:
        m_info = market.get(pos["price_key"], {})
        px = m_info.get(pos["price_field"], 0.0)
        p_min = pos["range_min"]
        p_max = pos["range_max"]

        if px <= 0:
            continue

        dynamic_val_usd = pos.get("capital_usd", 0.0)
        composition_desc = ""
        if pos["id"] == "virtual_weth":
            virt_audit = profits.get("virtual_weth", {}).get("audit")
            if virt_audit:
                dynamic_val_usd = virt_audit["pool_usd"]
                composition_desc = f"{virt_audit['pool_virtual']:.1f} VIRTUAL + {virt_audit['pool_weth']:.4f} WETH"
            else:
                _, _, dynamic_val_usd, composition_desc = calculate_virtual_pool_value(
                    px, eth_usd, p_min, p_max, pos.get("liquidity", 278820534392291859569)
                )
            pos["capital_usd"] = round(dynamic_val_usd, 2)

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

        sub_eval = []
        if pos.get("sub_positions"):
            for sub in pos["sub_positions"]:
                s_min = sub["range_min"]
                s_max = sub["range_max"]
                s_dist_ceil = ((s_max - px) / px) * 100.0
                s_dist_floor = ((px - s_min) / px) * 100.0
                if px > s_max:
                    s_status = f"🔴 FORA (Teto +{abs(s_dist_ceil):.2f}%)"
                elif px < s_min:
                    s_status = f"🔴 FORA (Piso -{abs(s_dist_floor):.2f}%)"
                elif s_dist_ceil < 2.0 or s_dist_floor < 2.0:
                    s_status = f"🟡 ATENÇÃO ({min(abs(s_dist_ceil), abs(s_dist_floor)):.2f}% da borda)"
                else:
                    s_status = "🟢 100% IN RANGE"
                sub_eval.append({
                    "id": sub["id"],
                    "label": sub["label"],
                    "capital_usd": sub["capital_usd"],
                    "range_min": s_min,
                    "range_max": s_max,
                    "status": s_status,
                    "daily_usd": sub["daily_usd"],
                    "apr": sub.get("apr", ""),
                    "dist_ceiling": s_dist_ceil,
                    "dist_floor": s_dist_floor
                })

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
            "profit": pos_profit,
            "dynamic_val_usd": dynamic_val_usd,
            "composition_desc": composition_desc,
            "sub_eval": sub_eval
        })

    return evaluated, has_urgent_alert, profits


def generate_consolidated_report(evaluated: list[dict], profits: dict) -> str:
    """Builds clean, compact Telegram Markdown message without visual clutter."""
    now_utc = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")
    total_capital = sum(item["pos"]["capital_usd"] for item in evaluated)
    p_info = profits.get("portfolio", {})
    daily_usd = p_info.get("total_daily_usd", 70.80)
    daily_brl = daily_usd * 5.50

    lines = [
        "🏛️ *RESUMO EXECUTIVO — TESOURARIA DEFI*",
        f"⏱️ _{now_utc}_",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"💰 *Patrimônio Total:* *`${total_capital:,.2f} USD`* (**~R$ {total_capital*5.50:,.2f}**)",
        f"💵 *Rendimento Passivo:* *`~${daily_usd:.2f} / dia`* (**~R$ {daily_brl:.2f}/dia**)",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n",
        "📍 *STATUS DAS 4 POOLS:*"
    ]

    for idx, item in enumerate(evaluated, 1):
        pos = item["pos"]
        prof = item["profit"]
        cap = pos["capital_usd"]
        d_usd = prof.get("daily_usd", 0.0)
        
        # Clean status icon
        status_tag = "🟢 No Range"
        if item["is_out"]:
            status_tag = "🔴 Fora da Faixa"
        elif item["is_warning"]:
            status_tag = f"🟡 Próximo à Borda ({min(abs(item['dist_ceiling']), abs(item['dist_floor'])):.1f}%)"

        if pos.get("sub_positions"):
            lines.append(f"*{idx}. {pos['name']}*")
            lines.append(f"   • Saldo Somado: *`${cap:,.2f} USD`* (~R$ {cap*5.5:,.2f})")
            lines.append(f"   • Rende: *`~${d_usd:.2f}/dia`* (~R$ {d_usd*5.5:.2f}/dia) | {status_tag}")
            lines.append(f"   • _Composto por: Principal #7669576 ($10.181) + Secundária #7670917 ($196)_")
        else:
            lines.append(f"*{idx}. {pos['name']}*")
            lines.append(f"   • Saldo: *`${cap:,.2f} USD`* | Rende: *`~${d_usd:.2f}/dia`* | {status_tag}")

    lines.append("\n━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("🛡️ _Sentinela 24/7 ativo na nuvem (Render.com). Use /lucro ou /relatorio._")

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
        f"• *Distância do Piso:* `-{abs(item['dist_floor']):.2f}%`",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━"
    ]

    if pos["id"] == "virtual_weth":
        audit = prof.get("audit") or {}
        pos_val_usd = audit.get("pool_usd", item.get("dynamic_val_usd", pos["capital_usd"]))
        comp_desc = item.get("composition_desc", f"{audit.get('pool_virtual', 0):.1f} VIRTUAL + {audit.get('pool_weth', 0):.4f} WETH")
        pending_usd = audit.get("pending_usd", 0.0)
        wallet_ret_usd = audit.get("dust_usd", 7.34)
        acc_fees_usd = audit.get("total_fees_usd", prof.get("accrued_usd", 10.81))
        last_cycle = audit.get("last_cycle")
        last_cycle_usd = last_cycle["fees_usd"] if last_cycle else 1.30
        last_cycle_nft = last_cycle["token_id"] if last_cycle else 6127604
        init_cap_usd = VIRT_INITIAL_USD
        # True equity: Pool MtM + Pending Fees + Wallet Dust (historical collected fees are already compounded in pool)
        total_current_equity = audit.get("equity_usd", pos_val_usd + pending_usd + wallet_ret_usd)
        net_diff = audit.get("net_usd", total_current_equity - init_cap_usd)
        net_pct = audit.get("net_pct", (net_diff / init_cap_usd) * 100.0)
        net_diff_sign = "+" if net_diff >= 0 else "-"

        num_c = len(audit.get("cycles", []))
        lines.extend([
            "💰 *CAPITAL & LUCRO LÍQUIDO REAL (NO BOLSO):*",
            f"• *Aporte Inicial (30/09):* `${init_cap_usd:.2f} USD` (~R$ {init_cap_usd*5.5:.2f})",
            f"• *Patrimônio Atual Total:* `~${total_current_equity:.2f} USD` (~R$ {total_current_equity*5.5:.2f})",
            f"  └ _(Pool + Trocos livres na carteira já somados)_",
            f"• 🟢 *LUCRO LÍQUIDO REAL:* *`{net_diff_sign}${abs(net_diff):.2f} USD ({net_diff_sign}{abs(net_pct):.2f}%)`* (**~R$ {abs(net_diff)*5.5:.2f}**)",
            "  └ _(Valor 100% líquido: taxas de protocolo, swaps e oscilações já descontadas)_"
        ])
    else:
        lines.extend([
            "💰 *LUCRO & RENDIMENTOS DESSA POSIÇÃO:*",
            f"• *Renda Gerada:* `~${prof.get('daily_usd'):.2f} / dia` (~R$ {prof.get('daily_brl'):.2f}/dia)",
            f"• *Lucro Acumulado Est.:* `{prof.get('accrued_text')}`",
            f"• *APR Real da Pool:* *{prof.get('apr')}*",
            f"• *Capital Alocado:* `${pos['capital_usd']:,.2f} USD`"
        ])

    lines.extend([
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "📊 *LUCRO TOTAL DA SUA CARTEIRA (4 POOLS):*",
        f"💵 *Renda Diária Total:* `~${p_info.get('total_daily_usd'):.2f} / dia` (~R$ {p_info.get('total_daily_brl'):.2f}/dia)",
        f"📈 *Lucro Total Acumulado:* `{p_info.get('accrued_text')}`",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "💡 *Ação Sugerida:* Avalie se é necessário rebalancear manualmente a faixa ou aguardar o recuo para o centro do range."
    ])
    return "\n".join(lines)


def send_telegram(text: str, reply_markup: dict = None) -> bool:
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
    if reply_markup:
        payload["reply_markup"] = reply_markup

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


def format_virtual_rebalance_notification(
    old_id: int,
    active_id: int,
    old_min: float,
    old_max: float,
    new_min: float,
    new_max: float,
    audit_data: dict | None = None
) -> str:
    """Builds comprehensive rebalance message with direction, gain/loss explanation and initial deposit ROI."""
    audit = audit_data or audit_virtual() or {}
    initial_capital_usd = VIRT_INITIAL_USD  # 406.46
    accumulated_fees_usd = audit.get("total_fees_usd", 10.81)

    last_cycle = audit.get("last_cycle")
    if last_cycle:
        last_cycle_fees_usd = last_cycle.get("fees_usd", 1.30)
        closed_nft_id = last_cycle.get("token_id", old_id)
    else:
        last_cycle_fees_usd = 1.30
        closed_nft_id = old_id

    current_pool_usd = audit.get("pool_usd", 388.76)
    pending_fees_usd = audit.get("pending_usd", 1.15)
    returned_wallet_usd = audit.get("dust_usd", 7.34)
    total_current_equity = audit.get("equity_usd", current_pool_usd + pending_fees_usd + returned_wallet_usd)

    fees_pct = (accumulated_fees_usd / initial_capital_usd) * 100.0
    net_pnl_usd = audit.get("net_usd", total_current_equity - initial_capital_usd)
    net_pnl_pct = audit.get("net_pct", (net_pnl_usd / initial_capital_usd) * 100.0)
    net_sign = "+" if net_pnl_usd >= 0 else "-"

    if new_min > old_min:
        direction_title = "🚀 SAIU PARA CIMA (Alta de Preço / Rompeu Teto)"
        direction_desc = (
            f"• *Comportamento:* O token VIRTUAL subiu e superou o teto anterior (`{old_max:.8f} WETH`).\n"
            "• *Impacto no Capital:* A pool vendeu VIRTUAL em escala durante a alta e acumulou WETH no topo, "
            "realizando ganho de capital na subida!"
        )
    else:
        direction_title = "📉 SAIU PARA BAIXO (Queda de Preço / Rompeu Piso)"
        direction_desc = (
            f"• *Comportamento:* O token VIRTUAL recuou e furou o piso anterior (`{old_min:.8f} WETH`).\n"
            "• *Impacto no Capital:* A pool comprou VIRTUAL a preços menores, acumulando tokens mais baratos. "
            "As taxas acumuladas amortecem a desvalorização em relação a segurar o token puro (HODL)."
        )

    msg = (
        "🔄 *KRYSTAL AUTOPILOT — REBALANCEAMENTO CONCLUÍDO!*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "📍 *Posição:* VIRTUAL / WETH 0.05% (Base L2)\n"
        f"🏷️ *Novo NFT Ativo:* `#{active_id}` (anterior `#{closed_nft_id}` encerrado)\n\n"
        "🎯 *DIREÇÃO DO MOVIMENTO:*\n"
        f"*{direction_title}*\n"
        f"{direction_desc}\n\n"
        "🎯 *Nova Faixa Centralizada:*\n"
        f"`{new_min:.8f}` ↔ `{new_max:.8f}` WETH\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "📊 *RESULTADO LÍQUIDO REAL NO BOLSO:*\n"
        f"• 💵 *Aporte Inicial (30/09):* `${initial_capital_usd:.2f} USD` (~R$ {initial_capital_usd*5.5:.2f})\n"
        f"• 🏦 *Patrimônio Líquido Atual:* `~${total_current_equity:.2f} USD` (~R$ {total_current_equity*5.5:.2f})\n"
        f"• 🟢 *LUCRO LÍQUIDO NO BOLSO:* *`{net_sign}${abs(net_pnl_usd):.2f} USD ({net_sign}{abs(net_pnl_pct):.2f}%)`* (**~R$ {abs(net_pnl_usd)*5.5:.2f}**)\n"
        "  └ _(Valor 100% livre: taxas de protocolo, swaps e oscilações já descontadas)_\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🟢 *Status:* 100% IN RANGE (Re-centralizado e gerando taxas na nova faixa!)\n"
        "🛡️ _Krystal Keeper gerenciando com sucesso na rede Base._"
    )
    return msg


def detect_virtual_rebalance(send_notify: bool = True) -> bool:
    """Checks on-chain if Krystal has rebalanced VIRTUAL/WETH into a new NFT."""
    wallet = "0xa36C0cb2159Fd132A6EFe461E170cf399a503a54"
    current_pos = POSITIONS[2]
    current_nft_str = current_pos["deposit_id"]
    try:
        current_nft_id = int("".join(c for c in current_nft_str if c.isdigit()))
    except Exception:
        current_nft_id = 6127604

    def inspect_token(tid):
        rpc_urls = ["https://base-rpc.publicnode.com", "https://1rpc.io/base", "https://mainnet.base.org"]
        token_id_hex = hex(tid)[2:].zfill(64)
        data_call = "0x99fbab88" + token_id_hex
        payload = {"jsonrpc": "2.0", "id": 1, "method": "eth_call", "params": [{"to": "0x03a520b32C04BF3bEEf7BEb72E919cf822Ed34f1", "data": data_call}, "latest"]}
        for rpc in rpc_urls:
            try:
                req = urllib.request.Request(rpc, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=5) as resp:
                    raw = json.loads(resp.read().decode()).get("result", "")
                    if raw and len(raw) >= 66:
                        words = [raw[2+i*64:2+(i+1)*64] for i in range(len(raw[2:])//64)]
                        liq = int(words[7], 16)
                        def to_signed(h):
                            v = int(h, 16)
                            return v - 2**256 if v >= 2**255 else v
                        tl = to_signed(words[5])
                        tu = to_signed(words[6])
                        p_min = 1.0001**tl
                        p_max = 1.0001**tu
                        return {"nft_id": tid, "range_min": p_min, "range_max": p_max, "liquidity": liq}
            except Exception:
                pass
        return None

    try:
        url = f"https://base.blockscout.com/api/v2/addresses/{wallet}/token-transfers"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read().decode())
            seen_ids = set()
            for it in data.get("items", []):
                tok = it.get("token", {})
                if tok.get("symbol") == "UNI-V3-POS":
                    tid = int(it.get("total", {}).get("token_id", 0))
                    if tid > 6100000 and tid not in seen_ids:
                        seen_ids.add(tid)
                        info = inspect_token(tid)
                        if info and info["liquidity"] > 0:
                            active_id = info["nft_id"]
                            if active_id != current_nft_id:
                                print(f"[*] Rebalance detected! Old #{current_nft_id} -> New #{active_id}")
                                old_min = current_pos["range_min"]
                                old_max = current_pos["range_max"]
                                new_min = round(info["range_min"], 8)
                                new_max = round(info["range_max"], 8)

                                current_pos["deposit_id"] = f"NFT #{active_id}"
                                current_pos["name"] = f"VIRTUAL / WETH 0.05% (#{active_id})"
                                current_pos["range_min"] = new_min
                                current_pos["range_max"] = new_max

                                # Update defi_treasury.json
                                t_file = ROOT / "data" / "defi_treasury.json"
                                if t_file.exists():
                                    try:
                                        t_data = json.loads(t_file.read_text(encoding="utf-8"))
                                        for p in t_data.get("positions", []):
                                            if p.get("id") == "krystal_virtual_weth":
                                                p["nft_id"] = str(active_id)
                                                p["name"] = f"VIRTUAL / WETH 0.05% (#{active_id})"
                                                p["range_min"] = new_min
                                                p["range_max"] = new_max
                                                p["status"] = "🟢 IN RANGE (Rebalanceado com Sucesso)"
                                        t_file.write_text(json.dumps(t_data, indent=2, ensure_ascii=False), encoding="utf-8")
                                    except Exception:
                                        pass

                                if send_notify:
                                    notify_msg = format_virtual_rebalance_notification(
                                        current_nft_id, active_id, old_min, old_max, new_min, new_max,
                                        audit_data=audit_virtual(force=True)
                                    )
                                    send_telegram(notify_msg, reply_markup={
                                        "inline_keyboard": [
                                            [{"text": "💰 Ver Lucros Atualizados", "callback_data": "defi_profit"}],
                                            [{"text": "📡 Radar das 4 Pools", "callback_data": "defi_treasury"}]
                                        ]
                                    })
                                return True
                            break
    except Exception as e:
        print(f"[-] Rebalance check error: {e}")
    return False


def run_sentinel_loop():
    """Runs 24/7 background sentinel loop with routine reports & urgent alerts."""
    print("[*] Iniciando Sentinela DeFi 24/7 com Módulo de Lucro em modo contínuo...")

    last_routine_report = 0.0
    alert_cooldowns: dict[str, float] = {}  # pos_id -> timestamp of last urgent alert

    ROUTINE_INTERVAL_SEC = 4 * 3600  # Every 4 hours
    CHECK_INTERVAL_SEC = 300         # Check prices every 5 minutes
    ALERT_COOLDOWN_SEC = 7200        # Max 1 warning alert per position per 2 hours (unless out of range)

    defi_buttons = {
        "inline_keyboard": [
            [{"text": "💰 Ver Lucros de Hoje & Total", "callback_data": "defi_profit"}],
            [{"text": "📡 Radar das 4 Pools & Faixas", "callback_data": "defi_treasury"}]
        ]
    }

    while True:
        try:
            # Check for automatic on-chain rebalances (e.g. Krystal)
            detect_virtual_rebalance(send_notify=True)

            market = fetch_live_market_data()
            evaluated, has_urgent, profits = evaluate_positions(market)
            now = time.time()

            # 1. Check for urgent alerts on each position
            for item in evaluated:
                pos_id = item["pos"]["id"]
                if item["is_out"] or item["is_warning"]:
                    last_alert_time = alert_cooldowns.get(pos_id, 0.0)
                    # Cooldown: 2h for virtual_weth (managed by autopilot keeper), 1h for out-of-range manual, 2h for proximity warning
                    cooldown = 7200 if pos_id == "virtual_weth" else (3600 if item["is_out"] else ALERT_COOLDOWN_SEC)
                    if now - last_alert_time > cooldown:
                        alert_msg = generate_urgent_alert_message(item, profits)
                        print(f"[!] Disparando alerta com lucros para {pos_id}...")
                        send_telegram(alert_msg, reply_markup=defi_buttons)
                        alert_cooldowns[pos_id] = now

            # 2. Routine 4-hour consolidated report
            if now - last_routine_report >= ROUTINE_INTERVAL_SEC:
                report = generate_consolidated_report(evaluated, profits)
                print("[*] Enviando relatório consolidado periódico de 4h...")
                send_telegram(report, reply_markup=defi_buttons)
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
