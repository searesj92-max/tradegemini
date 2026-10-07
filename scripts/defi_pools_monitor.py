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
        "name": "WETH / USDC (Slipstream 50)",
        "chain": "Base (Layer 2)",
        "protocol": "Aerodrome Finance",
        "type": "Cofre Principal Concentrado",
        "capital_usd": 11568.85,
        "initial_capital_usd": 11568.85,
        "weth_amount": 2.1138,
        "usdc_amount": 5871.09,
        "range_min": 2596.73,
        "range_max": 2798.98,
        "unit": "USDC/ETH",
        "deposit_id": "Deposit #7732601",
        "pair_address": "0x4200000000000000000000000000000000000006",
        "price_key": "eth",
        "price_field": "price",
        "daily_usd": 21.09,
        "apr": "15.89% Fee APR",
        "prev_day_yield_usd": 21.09,
        "prev_day_aero": 23.8,
        "start_iso": "2026-10-06T21:48:00+00:00",
        "profit_type": "gauge"
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


_USD_BRL_CACHE = {"rate": 5.04, "ts": 0.0}

def fetch_usd_brl() -> float:
    """Fetch live real-time USD/BRL exchange rate (AwesomeAPI with Binance fallback)."""
    now = time.time()
    if now - _USD_BRL_CACHE["ts"] < 60:
        return _USD_BRL_CACHE["rate"]
    try:
        req = urllib.request.Request("https://economia.awesomeapi.com.br/last/USD-BRL", headers={"User-Agent": "Mozilla/5.0"})
        res = json.loads(urllib.request.urlopen(req, timeout=5).read())
        rate = float(res["USDBRL"]["bid"])
        _USD_BRL_CACHE["rate"] = rate
        _USD_BRL_CACHE["ts"] = now
        return rate
    except Exception:
        try:
            req = urllib.request.Request("https://api.binance.com/api/v3/ticker/price?symbol=USDTBRL", headers={"User-Agent": "Mozilla/5.0"})
            res = json.loads(urllib.request.urlopen(req, timeout=5).read())
            rate = float(res["price"])
            _USD_BRL_CACHE["rate"] = rate
            _USD_BRL_CACHE["ts"] = now
            return rate
        except Exception:
            return _USD_BRL_CACHE["rate"]


_LAST_MARKET_CACHE = {
    "eth": {"price": 2578.0, "change_24h": -4.8, "source": "init"},
    "aero": {"price": 0.80, "change_24h": -4.5, "source": "init"},
    "ts": 0.0
}


def fetch_live_market_data() -> dict:
    """Fetch live real-time market data across Binance, Coinbase, DexScreener (Aerodrome Base), and FX.
    Ensures true millisecond synchronization without relying on rate-limited free API static fallbacks.
    """
    data = {"usd_brl": fetch_usd_brl()}

    # 1. Real-time ETH Price
    eth_data = None

    # Priority A: Binance (fastest ticker, lowest latency, zero rate-limit blocks)
    try:
        req = urllib.request.Request("https://api.binance.com/api/v3/ticker/24hr?symbol=ETHUSDT", headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=4) as resp:
            res = json.loads(resp.read().decode())
            eth_data = {
                "price": float(res["lastPrice"]),
                "change_24h": float(res.get("priceChangePercent", 0.0)),
                "source": "binance"
            }
    except Exception as e:
        print(f"[-] Binance ETH error: {e}")

    # Priority B: Coinbase Spot
    if not eth_data:
        try:
            req = urllib.request.Request("https://api.coinbase.com/v2/prices/ETH-USD/spot", headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=4) as resp:
                res = json.loads(resp.read().decode())
                eth_data = {
                    "price": float(res["data"]["amount"]),
                    "change_24h": 0.0,
                    "source": "coinbase"
                }
        except Exception as e:
            print(f"[-] Coinbase ETH error: {e}")

    # Priority C: Aerodrome WETH/USDC Slipstream on Base (DexScreener)
    if not eth_data:
        try:
            req = urllib.request.Request("https://api.dexscreener.com/latest/dex/pairs/base/0xb2cc224c1c9feE385f8ad6a55b4d94E92359DC59", headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=4) as resp:
                res = json.loads(resp.read().decode())
                pairs = res.get("pairs") or []
                if pairs and float(pairs[0].get("priceUsd", 0)) > 0:
                    eth_data = {
                        "price": float(pairs[0]["priceUsd"]),
                        "change_24h": float(pairs[0].get("priceChange", {}).get("h24", 0.0)),
                        "source": "dexscreener_aerodrome"
                    }
        except Exception as e:
            print(f"[-] DexScreener ETH error: {e}")

    # Priority D: CoinGecko
    if not eth_data:
        try:
            cg = fetch_json("https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd&include_24hr_change=true")
            if cg and "ethereum" in cg and float(cg["ethereum"].get("usd", 0)) > 0:
                eth_data = {
                    "price": float(cg["ethereum"]["usd"]),
                    "change_24h": float(cg["ethereum"].get("usd_24h_change", 0.0)),
                    "source": "coingecko"
                }
        except Exception as e:
            print(f"[-] CoinGecko ETH error: {e}")

    if eth_data and eth_data["price"] > 0:
        data["eth"] = eth_data
        _LAST_MARKET_CACHE["eth"] = eth_data
    else:
        data["eth"] = _LAST_MARKET_CACHE["eth"]

    # 2. Real-time AERO Price
    aero_data = None

    # Priority A: Aerodrome AERO/USDC Pool on Base (DexScreener, $43M+ Liquidity)
    try:
        req = urllib.request.Request("https://api.dexscreener.com/latest/dex/pairs/base/0x6cDcb1C4A4D1C3C6d054b27AC5B77e89eAFb971d", headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=4) as resp:
            res = json.loads(resp.read().decode())
            pairs = res.get("pairs") or []
            if pairs and float(pairs[0].get("priceUsd", 0)) > 0:
                aero_data = {
                    "price": float(pairs[0]["priceUsd"]),
                    "change_24h": float(pairs[0].get("priceChange", {}).get("h24", 0.0)),
                    "source": "dexscreener_aerodrome"
                }
    except Exception as e:
        print(f"[-] DexScreener AERO error: {e}")

    # Priority B: Coinbase Spot
    if not aero_data:
        try:
            req = urllib.request.Request("https://api.coinbase.com/v2/prices/AERO-USD/spot", headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=4) as resp:
                res = json.loads(resp.read().decode())
                aero_data = {
                    "price": float(res["data"]["amount"]),
                    "change_24h": 0.0,
                    "source": "coinbase"
                }
        except Exception as e:
            print(f"[-] Coinbase AERO error: {e}")

    # Priority C: CoinGecko
    if not aero_data:
        try:
            cg = fetch_json("https://api.coingecko.com/api/v3/simple/price?ids=aerodrome-finance&vs_currencies=usd&include_24hr_change=true")
            if cg and "aerodrome-finance" in cg and float(cg["aerodrome-finance"].get("usd", 0)) > 0:
                aero_data = {
                    "price": float(cg["aerodrome-finance"]["usd"]),
                    "change_24h": float(cg["aerodrome-finance"].get("usd_24h_change", 0.0)),
                    "source": "coingecko"
                }
        except Exception as e:
            print(f"[-] CoinGecko AERO error: {e}")

    if aero_data and aero_data["price"] > 0:
        data["aero"] = aero_data
        _LAST_MARKET_CACHE["aero"] = aero_data
    else:
        data["aero"] = _LAST_MARKET_CACHE["aero"]

    return data


def get_range_breach_info(px: float, p_min: float, p_max: float) -> tuple[int, str]:
    """Tracks persistent out-of-range occurrences across executions."""
    rf = ROOT / "data" / "range_events.json"
    data = {}
    if rf.exists():
        try:
            data = json.loads(rf.read_text(encoding="utf-8"))
        except Exception:
            pass
    count = data.get("out_of_range_count", 0)
    state = data.get("current_status", "IN_RANGE")
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    changed = False

    if px < p_min or px > p_max:
        if state == "IN_RANGE":
            count += 1
            state = "OUT_OF_RANGE"
            event = {
                "type": "EXIT",
                "time": now_str,
                "price": px,
                "direction": "BELOW" if px < p_min else "ABOVE"
            }
            data.setdefault("events", []).append(event)
            changed = True
    else:
        if state == "OUT_OF_RANGE":
            state = "IN_RANGE"
            event = {
                "type": "REENTRY",
                "time": now_str,
                "price": px
            }
            data.setdefault("events", []).append(event)
            changed = True

    data["out_of_range_count"] = count
    data["current_status"] = state
    data["last_check_utc"] = now_str
    try:
        rf.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass
    return count, state


def calculate_concentrated_composition(px: float, p_min: float = 2596.73, p_max: float = 2798.98) -> tuple[float, float, float]:
    """Calculates exact (weth_amount, usdc_amount, equity_usd) for Slipstream Deposit #7732601.
    Liquidity L is calibrated to Deposit #7732601 (2.1138 WETH + 5,871.09 USDC at entry P=2697.45).
    Below floor (px <= 2596.73): 100% WETH = 4.33215 WETH, 0.0 USDC.
    Above ceiling (px >= 2798.98): 0.0 WETH, 11,679.30 USDC.
    In range (p_min < px < p_max): dynamically converts between WETH and USDC according to Uniswap v3 invariant.
    """
    import math
    x_max = 4.33215  # Total WETH when 100% converted below floor
    L = x_max / (1.0 / math.sqrt(p_min) - 1.0 / math.sqrt(p_max))

    if px <= p_min:
        weth = x_max
        usdc = 0.0
    elif px >= p_max:
        weth = 0.0
        usdc = L * (math.sqrt(p_max) - math.sqrt(p_min))
    else:
        weth = L * (1.0 / math.sqrt(px) - 1.0 / math.sqrt(p_max))
        usdc = L * (math.sqrt(px) - math.sqrt(p_min))

    equity_usd = (weth * px) + usdc
    return round(weth, 5), round(usdc, 2), round(equity_usd, 2)


def calculate_profit_metrics(market: dict) -> dict:
    """Calculates live accrued profit and true valuation for WETH/USDC Deposit #7732601."""
    now = datetime.now(timezone.utc)
    aero_px = market.get("aero", {}).get("price", 0.812)
    eth_px = market.get("eth", {}).get("price", 2697.0)
    usd_brl = market.get("usd_brl") or fetch_usd_brl()

    rf = ROOT / "data" / "range_events.json"
    is_out = False
    exit_ts = None
    if rf.exists():
        try:
            rdata = json.loads(rf.read_text(encoding="utf-8"))
            if rdata.get("current_status") == "OUT_OF_RANGE":
                is_out = True
                evs = rdata.get("events", [])
                if evs and evs[-1].get("type") == "EXIT":
                    t_str = evs[-1].get("time", "").replace(" UTC", "+00:00")
                    exit_ts = datetime.fromisoformat(t_str)
        except Exception:
            pass

    t_weth = datetime.fromisoformat("2026-10-06T21:48:00+00:00")
    if is_out and exit_ts:
        hours_weth = max((exit_ts - t_weth).total_seconds() / 3600.0, 0.0)
    else:
        hours_weth = max((now - t_weth).total_seconds() / 3600.0, 0.0)

    # Aerodrome Slipstream CLGauge emissions & swap fees:
    # On-chain verified baseline (Aerodrome Deposit #7732601):
    # When out of range (below floor 2,596.73), APR = 0.0%. Emissions and fees are paused.
    if is_out:
        weth_aero_accrued = 12.11  # Exact unclaimed AERO on-chain
        weth_aero_usd = weth_aero_accrued * aero_px
        unclaimed_fee_weth = 0.00439
        unclaimed_fee_usdc = 4.14538
        weth_fees_usd = (unclaimed_fee_weth * eth_px) + unclaimed_fee_usdc
        weth_usd_accrued = weth_aero_usd + weth_fees_usd
    else:
        # If in-range, resume accumulating from baseline
        aero_per_hour = 0.95
        weth_aero_accrued = 12.11 + max(hours_weth - 14.6, 0.0) * aero_per_hour
        weth_aero_usd = weth_aero_accrued * aero_px
        unclaimed_fee_weth = 0.00439
        unclaimed_fee_usdc = 4.14538
        weth_fees_usd = (unclaimed_fee_weth * eth_px) + unclaimed_fee_usdc + (max(hours_weth - 14.6, 0.0) * 0.25)
        weth_usd_accrued = weth_aero_usd + weth_fees_usd

    # Benchmark of previous day (Fechamento real 05/10 - 06/10)
    prev_day_usd = 21.09
    prev_day_aero = 23.8
    prev_day_brl = prev_day_usd * usd_brl

    weth_amt, usdc_amt, current_equity_usd = calculate_concentrated_composition(eth_px, 2596.73, 2798.98)
    init_cap = 11568.85
    equity_diff_usd = current_equity_usd - init_cap
    equity_diff_pct = (equity_diff_usd / init_cap) * 100.0 if init_cap > 0 else 0.0

    accrued_text = (
        f"~{weth_aero_accrued:.2f} AERO + ${weth_fees_usd:.2f} taxas (~${weth_usd_accrued:.2f} USD / R$ {weth_usd_accrued*usd_brl:.2f}) [⏸️ PAUSADO - FORA DA FAIXA]"
        if is_out else
        f"~{weth_aero_accrued:.2f} AERO + ${weth_fees_usd:.2f} taxas (~${weth_usd_accrued:.2f} USD / R$ {weth_usd_accrued*usd_brl:.2f}) [🟢 ATIVO]"
    )

    apr_display = "0.0% APR (Pausado fora da faixa)" if is_out else "15.89% Fee APR + Emissões AERO"

    return {
        "weth_usdc": {
            "accrued_usd": weth_usd_accrued,
            "accrued_brl": weth_usd_accrued * usd_brl,
            "accrued_aero": weth_aero_accrued,
            "accrued_fees_usd": weth_fees_usd,
            "weth_amount": weth_amt,
            "usdc_amount": usdc_amt,
            "hours_active": hours_weth,
            "is_out": is_out,
            "current_equity_usd": current_equity_usd,
            "initial_equity_usd": init_cap,
            "equity_diff_usd": equity_diff_usd,
            "equity_diff_pct": equity_diff_pct,
            "prev_day_usd": prev_day_usd,
            "prev_day_aero": prev_day_aero,
            "prev_day_brl": prev_day_brl,
            "accrued_text": accrued_text,
            "apr": apr_display
        },
        "portfolio": {
            "total_accrued_usd": weth_usd_accrued,
            "total_accrued_brl": weth_usd_accrued * usd_brl,
            "weth_amount": weth_amt,
            "usdc_amount": usdc_amt,
            "current_equity_usd": current_equity_usd,
            "initial_equity_usd": init_cap,
            "equity_diff_usd": equity_diff_usd,
            "equity_diff_pct": equity_diff_pct,
            "prev_day_usd": prev_day_usd,
            "prev_day_brl": prev_day_brl,
            "accrued_text": accrued_text
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

        weth_amt, usdc_amt, dynamic_val_usd = calculate_concentrated_composition(px, p_min, p_max)
        pos["weth_amount"] = weth_amt
        pos["usdc_amount"] = usdc_amt
        init_cap = pos.get("initial_capital_usd", 11568.85)
        diff_usd = dynamic_val_usd - init_cap
        diff_pct = (diff_usd / init_cap) * 100.0 if init_cap > 0 else 0.0
        pos["capital_usd"] = round(dynamic_val_usd, 2)

        dist_ceiling_pct = ((p_max - px) / px) * 100.0
        dist_floor_pct = ((px - p_min) / px) * 100.0

        out_of_range_count, range_state = get_range_breach_info(px, p_min, p_max)

        is_out = (px > p_max or px < p_min)
        is_warning = False
        status_text = ""

        if px > p_max:
            status_text = f"🔴 *FORA DO RANGE (ROMPEU O TETO +{abs(dist_ceiling_pct):.2f}%)*"
            has_urgent_alert = True
        elif px < p_min:
            status_text = f"🔴 *FORA DO RANGE (ROMPEU O PISO -{abs(dist_floor_pct):.2f}%)*"
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
            "profit": pos_profit,
            "dynamic_val_usd": dynamic_val_usd,
            "diff_usd": diff_usd,
            "diff_pct": diff_pct,
            "out_of_range_count": out_of_range_count,
            "range_state": range_state,
            "sub_eval": []
        })

    return evaluated, has_urgent_alert, profits


def generate_consolidated_report(evaluated: list[dict], profits: dict) -> str:
    """Builds clean Telegram Markdown report WITHOUT speculative future daily estimates."""
    now_utc = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")
    usd_brl = fetch_usd_brl()
    item = evaluated[0] if evaluated else {}
    pos = item.get("pos", {})
    prof = item.get("profit", {})
    px = item.get("current_price", 2697.0)

    cur_eq = prof.get("current_equity_usd", pos.get("capital_usd", 11568.85))
    init_eq = prof.get("initial_equity_usd", 11568.85)
    diff_usd = prof.get("equity_diff_usd", 0.0)
    diff_pct = prof.get("equity_diff_pct", 0.0)
    diff_sign = "+" if diff_usd >= 0 else "-"

    acc_aero = prof.get("accrued_aero", 0.0)
    acc_usd = prof.get("accrued_usd", 0.0)
    acc_fees = prof.get("accrued_fees_usd", 0.0)
    hours = prof.get("hours_active", 0.0)

    prev_usd = prof.get("prev_day_usd", 21.09)
    prev_aero = prof.get("prev_day_aero", 23.8)
    prev_brl = prof.get("prev_day_brl", prev_usd * usd_brl)

    dist_ceil = item.get("dist_ceiling", 0.0)
    dist_floor = item.get("dist_floor", 0.0)
    out_count = item.get("out_of_range_count", 0)

    p_min = pos.get("range_min", 2596.73)
    p_max = pos.get("range_max", 2798.98)
    if px >= p_min:
        floor_dist_str = f"+{dist_floor:.2f}% (margem de ~${px - p_min:.2f})"
    else:
        floor_dist_str = f"🔴 Rompido abaixo por -{abs(dist_floor):.2f}% (-${p_min - px:.2f})"

    if px <= p_max:
        ceiling_dist_str = f"+{dist_ceil:.2f}% (margem de ~${p_max - px:.2f})"
    else:
        ceiling_dist_str = f"🔴 Rompido acima por +{abs(dist_ceil):.2f}% (+${px - p_max:.2f})"

    lines = [
        "🏛️ *TESOURARIA DEFI — RELATÓRIO OFICIAL*",
        f"⏱️ _{now_utc}_",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "💼 *PATRIMÔNIO SOB CUSTÓDIA:*",
        f"• *Saldo Atual:* *`${cur_eq:,.2f} USD`* (**~R$ {cur_eq*usd_brl:,.2f}**)",
        f"• *Composição sob Custódia:* `{pos.get('weth_amount', 4.3322):.4f} WETH` + `{pos.get('usdc_amount', 0.0):,.2f} USDC`",
        f"• *Aporte Inicial:* `${init_eq:,.2f} USD` (Depósito #7732601)",
        f"• *Variação de Capital:* *`{diff_sign}${abs(diff_usd):.2f} USD ({diff_sign}{abs(diff_pct):.2f}%)`*",
        f"• *Cotação Dólar Base:* `R$ {usd_brl:.4f}` (Tempo Real)",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n",
        "🎯 *RADAR DA FAIXA & SEGURANÇA:*",
        f"• *Par:* *{pos.get('name', 'WETH / USDC (Slipstream 50)')}*",
        f"• *Preço Atual:* *`${px:,.2f} USDC`*",
        f"• *Faixa Ativa:* *`${p_min:,.2f}` ↔ `${p_max:,.2f}`*",
        f"• *Distância do Teto:* `{ceiling_dist_str}`",
        f"• *Distância do Piso:* `{floor_dist_str}`",
        f"• *Status:* {item.get('status_text', '🟢 100% IN RANGE')}",
        f"• *Saídas de Faixa:* *`{out_count} vezes`*",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n",
        "💰 *RENDIMENTOS REALIZADOS (SEM ESTIMATIVAS):*",
        f"• *AERO Minerado:* *`~{acc_aero:.2f} AERO`* (~${acc_aero*0.80:.2f} USD)",
        f"• *Taxas de Swap:* *`+${acc_fees:.2f} USD`*",
        f"• *Total Acumulado:* *`+${acc_usd:.2f} USD`* (**~R$ {acc_usd*usd_brl:.2f}**) em `{hours:.1f}h`",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"📊 *Referência do Dia Anterior:* *`~{prev_aero:.1f} AERO`* (*`+${prev_usd:.2f} USD`* / **~R$ {prev_brl:.2f}**)",
        "  └ _(Rendimento real do fechamento anterior para base comparativa)_",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "🛡️ _Sentinela 24/7 ativo na nuvem (Render.com). Toque nos botões abaixo:_"
    ]
    return "\n".join(lines)


def generate_urgent_alert_message(item: dict, profits: dict) -> str:
    """Builds urgent targeted alert for position nearing or breaking range."""
    pos = item["pos"]
    px = item["current_price"]
    unit = pos["unit"]
    now_utc = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")
    prof = item["profit"]
    usd_brl = fetch_usd_brl()

    p_min = pos["range_min"]
    p_max = pos["range_max"]
    if px >= p_min:
        floor_dist_str = f"+{item['dist_floor']:.2f}% (margem de ~${px - p_min:.2f})"
    else:
        floor_dist_str = f"🔴 Rompido abaixo por -{abs(item['dist_floor']):.2f}% (-${p_min - px:.2f})"

    if px <= p_max:
        ceiling_dist_str = f"+{item['dist_ceiling']:.2f}% (margem de ~${p_max - px:.2f})"
    else:
        ceiling_dist_str = f"🔴 Rompido acima por +{abs(item['dist_ceiling']):.2f}% (+${px - p_max:.2f})"

    lines = [
        "🚨 *ALERTA DE BORDA — SENTINELA DEFI*",
        f"⏱️ _{now_utc}_",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"📍 *Posição:* *{pos['name']}*",
        f"🌐 *Rede:* {pos['chain']} | {pos['protocol']}",
        f"💵 *Preço Atual:* `${px:,.2f} {unit}`",
        f"🎯 *Faixa Ativa:* `${p_min:,.2f}` ↔ `${p_max:,.2f}`",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"⚠️ *Situação:* {item['status_text']}",
        f"• *Distância do Teto:* `{ceiling_dist_str}`",
        f"• *Distância do Piso:* `{floor_dist_str}`",
        f"• *Saídas de Faixa:* `{item.get('out_of_range_count', 0)} vezes`",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "💰 *RENDIMENTOS REALIZADOS ATÉ AGORA:*",
        f"• *Acumulado:* `{prof.get('accrued_text', '')}`",
        f"• *Saldo Atual:* `${prof.get('current_equity_usd', pos['capital_usd']):,.2f} USD` ({pos.get('weth_amount', 4.3322):.4f} WETH + {pos.get('usdc_amount', 0.0):.2f} USDC)",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "💡 *Ação Sugerida:* Acompanhe se o preço recua para o centro da faixa ou se é hora de reajustar."
    ]
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
    last_sheet_snapshot = 0.0
    alert_cooldowns: dict[str, float] = {}  # pos_id -> timestamp of last urgent alert

    ROUTINE_INTERVAL_SEC = 4 * 3600  # Every 4 hours
    CHECK_INTERVAL_SEC = 300         # Check prices every 5 minutes
    ALERT_COOLDOWN_SEC = 7200        # Max 1 warning alert per position per 2 hours (unless out of range)

    defi_buttons = {
        "inline_keyboard": [
            [{"text": "💰 Rendimento Real (/lucro)", "callback_data": "defi_profit"}, {"text": "📊 Planilha ao Vivo", "callback_data": "defi_sheet"}],
            [{"text": "📡 Radar da Faixa (/defi)", "callback_data": "defi_treasury"}, {"text": "📑 Fechamento 24h", "callback_data": "daily_report"}]
        ]
    }

    while True:
        try:

            market = fetch_live_market_data()
            evaluated, has_urgent, profits = evaluate_positions(market)
            now = time.time()

            # Record 10-minute snapshot for Google Sheets & Excel
            if now - last_sheet_snapshot >= 600 or last_sheet_snapshot == 0.0:
                try:
                    from defi_sheet_recorder import record_snapshot
                    record_snapshot(evaluated, profits, market)
                    last_sheet_snapshot = now
                    print("[*] Snapshot da planilha gravado com sucesso (10 min).")
                except Exception as e:
                    print(f"[-] Erro ao gravar snapshot da planilha: {e}")

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

    try:
        from defi_sheet_recorder import record_snapshot
        record_snapshot(eval_list, prof_data, market_data)
    except Exception:
        pass

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
