#!/usr/bin/env python3
"""
Hyperliquid Funding Rate & Short Squeeze Radar
Monitors real-time hourly funding rates across all 234 Hyperliquid perp assets.
Highlights:
- Extreme Negative Funding (Short Squeeze candidates: shorts pay longs huge APR).
- Extreme Positive Funding (Over-leveraged Long candidates: longs pay shorts).
- Open Interest and 24h Notional Volume.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

# Fix Windows console encoding
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from hyperliquid_executor import HyperliquidExecutor


def fetch_funding_radar(min_volume_usd: float = 100000.0) -> dict:
    """Fetches and analyzes real-time funding rates across all Hyperliquid perp assets."""
    executor = HyperliquidExecutor()
    ctxs = executor.info.meta_and_asset_ctxs()

    universe = ctxs[0]["universe"]
    metas = ctxs[1]

    items = []
    for i, u in enumerate(universe):
        coin = u["name"]
        m = metas[i] if i < len(metas) else {}

        try:
            funding_hourly = float(m.get("funding", 0.0))
            mark_px = float(m.get("markPx", 0.0))
            oi_tokens = float(m.get("openInterest", 0.0))
            vol_24h = float(m.get("dayNtlVlm", 0.0))
            premium = float(m.get("premium", 0.0))

            oi_usd = oi_tokens * mark_px
            apr_pct = funding_hourly * 24.0 * 365.0 * 100.0
            daily_pct = funding_hourly * 24.0 * 100.0

            # Filter low-liquidity dust
            if vol_24h < min_volume_usd and oi_usd < 50000.0:
                continue

            # Classify signal
            if apr_pct <= -25.0:
                signal = "🔥 ALTO RISCO DE SHORT SQUEEZE (Shorts pagando Longs)"
                signal_type = "squeeze"
                color = "green"
            elif apr_pct <= -10.0:
                signal = "🟢 FUNDING NEGATIVO FAVORÁVEL"
                signal_type = "favorable_long"
                color = "green"
            elif apr_pct >= +50.0:
                signal = "⚠️ OVER-LEVERAGED LONGS (Longs pagando Shorts)"
                signal_type = "overheated"
                color = "red"
            else:
                signal = "⚪ NEUTRO"
                signal_type = "neutral"
                color = "muted"

            items.append({
                "coin": coin,
                "price": mark_px,
                "funding_hourly": funding_hourly,
                "apr_pct": round(apr_pct, 2),
                "daily_pct": round(daily_pct, 4),
                "oi_usd": round(oi_usd, 2),
                "vol_24h_usd": round(vol_24h, 2),
                "premium_pct": round(premium * 100.0, 3),
                "signal": signal,
                "signal_type": signal_type,
                "color": color,
                "max_leverage": u.get("maxLeverage", 10)
            })
        except Exception:
            continue

    # Sort into Squeeze (Negative) and Overheated (Positive)
    top_negative = sorted([x for x in items if x["apr_pct"] < 0], key=lambda x: x["apr_pct"])[:15]
    top_positive = sorted([x for x in items if x["apr_pct"] > 0], key=lambda x: x["apr_pct"], reverse=True)[:15]

    return {
        "status": "ok",
        "timestamp": int(time.time()),
        "total_scanned": len(universe),
        "total_analyzed": len(items),
        "top_negative_squeeze": top_negative,
        "top_positive_overheated": top_positive,
        "all_items": sorted(items, key=lambda x: x["apr_pct"])
    }


def main():
    parser = argparse.ArgumentParser(description="Hyperliquid Funding Rate & Short Squeeze Radar")
    parser.add_argument("--min-vol", type=float, default=100000.0, help="Min 24h volume in USD")
    args = parser.parse_args()

    print("[*] Escaneando taxas de funding na Hyperliquid...")
    res = fetch_funding_radar(min_volume_usd=args.min_vol)

    print("\n" + "=" * 70)
    print("🔥 TOP 10 OPORTUNIDADES DE SHORT SQUEEZE (Funding Negativo Extremo)")
    print("    Shorts pagam juros por hora para os Longs. Alta assimetria de alta!")
    print("=" * 70)
    print(f"{'Moeda':<10} {'Preço':<12} {'APR Anual':<14} {'Yield/Dia':<12} {'Open Interest':<14} {'Vol 24h'}")
    print("-" * 70)
    for x in res["top_negative_squeeze"][:10]:
        print(f"{x['coin']:<10} ${x['price']:<11.4f} {x['apr_pct']:>+.1f}%/ano   {x['daily_pct']:>+.2f}%/dia   ${x['oi_usd']/1000:>7.1f}k      ${x['vol_24h_usd']/1000:>7.1f}k")

    print("\n" + "=" * 70)
    print("⚠️ TOP 10 MERCADOS SOBRECARREGADOS EM LONG (Funding Positivo Extremo)")
    print("    Longs pagam juros caros por hora. Risco de 'Long Squeeze' e correção!")
    print("=" * 70)
    print(f"{'Moeda':<10} {'Preço':<12} {'APR Anual':<14} {'Custo/Dia':<12} {'Open Interest':<14} {'Vol 24h'}")
    print("-" * 70)
    for x in res["top_positive_overheated"][:10]:
        print(f"{x['coin']:<10} ${x['price']:<11.4f} {x['apr_pct']:>+.1f}%/ano   {x['daily_pct']:>+.2f}%/dia   ${x['oi_usd']/1000:>7.1f}k      ${x['vol_24h_usd']/1000:>7.1f}k")


if __name__ == "__main__":
    main()
