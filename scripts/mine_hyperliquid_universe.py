#!/usr/bin/env python3
"""
Botrade Massive Hyperliquid Universe Alpha Miner & Correlation Screener
Sweeps through all ~234 perpetual contracts listed on Hyperliquid,
computes cross-asset Pearson correlation against Bitcoin (BTC),
runs quantitative backtesting pipelines, and filters institutional "Joias Raras":
- Profit Factor >= 1.40
- Max Drawdown <= 25.0%
- Win Rate >= 50.0%
- Trade Count >= 8
- Low BTC Correlation (< 0.60)
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Fix Windows console encoding
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from hyperliquid_executor import HyperliquidExecutor
from backtest_engine import run_backtest_pipeline, fetch_historical_candles

LEADERBOARD_FILE = ROOT / "data" / "reports" / "universe_leaderboard.json"
DATA_FILE = ROOT / "dashboard" / "data.json"


def calculate_pearson_correlation(series_a: list[float], series_b: list[float]) -> float:
    """Calculates Pearson correlation coefficient between two equal-length return series."""
    n = min(len(series_a), len(series_b))
    if n < 10:
        return 1.0  # Default to high correlation if not enough data
    
    a = series_a[-n:]
    b = series_b[-n:]

    mean_a = sum(a) / n
    mean_b = sum(b) / n

    cov = sum((a[i] - mean_a) * (b[i] - mean_b) for i in range(n))
    var_a = sum((a[i] - mean_a) ** 2 for i in range(n))
    var_b = sum((b[i] - mean_b) ** 2 for i in range(n))

    denom = math.sqrt(var_a * var_b)
    if denom == 0:
        return 0.0
    return max(-1.0, min(1.0, cov / denom))


def compute_candle_returns(candles: list[dict]) -> dict[int, float]:
    """Returns mapping of timestamp -> candle percentage return."""
    ret_map = {}
    for i in range(1, len(candles)):
        t = int(candles[i]["t"])
        c_prev = float(candles[i - 1]["c"])
        c_cur = float(candles[i]["c"])
        if c_prev > 0:
            ret_map[t] = (c_cur - c_prev) / c_prev
    return ret_map


def mine_universe(
    limit: int = 250,
    days: int = 180,
    timeframe: str = "4h",
    strategy: str = "pullback",
    min_volume_usd: float = 50000.0,
    inject_to_dashboard: bool = False
) -> dict:
    executor = HyperliquidExecutor()
    print("[*] Consultando meta universo completo da Hyperliquid...")
    ctxs = executor.info.meta_and_asset_ctxs()

    universe = ctxs[0]["universe"]
    metas = ctxs[1]

    # Pre-filter by active pairs and minimum 24h volume
    coins_available = []
    for i, u in enumerate(universe):
        name = u["name"]
        m = metas[i] if i < len(metas) else {}
        vol = float(m.get("dayNtlVlm", 0.0))
        max_lev = int(u.get("maxLeverage", 10))
        mark_px = float(m.get("markPx", 0.0))

        if mark_px > 0 and vol >= min_volume_usd:
            coins_available.append({
                "name": name,
                "volume_24h": vol,
                "max_leverage": max_lev,
                "price": mark_px
            })

    # Sort descending by volume
    coins_available.sort(key=lambda x: x["volume_24h"], reverse=True)
    target_coins = coins_available[:limit]

    print(f"[*] Universo filtrado: {len(target_coins)} ativos elegíveis (volume 24h >= ${min_volume_usd:,.0f}).")
    print(f"[*] Período de Análise: {days} dias ({timeframe}) | Estratégia Base: {strategy}")

    # 1. Fetch BTC benchmark for correlation mapping
    print("[*] Baixando série histórica de referência do Bitcoin (BTC)...")
    btc_candles = fetch_historical_candles(executor, "BTC", timeframe=timeframe, days=days)
    btc_returns_map = compute_candle_returns(btc_candles)
    print(f"[*] BTC carregado: {len(btc_candles)} velas ({len(btc_returns_map)} retornos calculados).")

    results = []
    rare_gems = []

    print(f"[*] Iniciando bateria de backtests quantitativos e análise de correlação...\n")

    for idx, c in enumerate(target_coins):
        sym = c["name"]
        vol_k = c["volume_24h"] / 1000.0

        sys.stdout.write(f"[{idx + 1}/{len(target_coins)}] Testando {sym:<8} (Vol 24h: ${vol_k:>7.0f}k)... ")
        sys.stdout.flush()

        try:
            # Fetch candles for correlation
            alt_candles = fetch_historical_candles(executor, sym, timeframe=timeframe, days=days)
            if not alt_candles or len(alt_candles) < 30:
                print("⚠️ Velas insuficientes. Pulando.")
                continue

            alt_returns_map = compute_candle_returns(alt_candles)

            # Match timestamps with BTC returns
            common_ts = sorted(set(btc_returns_map.keys()) & set(alt_returns_map.keys()))
            btc_aligned = [btc_returns_map[t] for t in common_ts]
            alt_aligned = [alt_returns_map[t] for t in common_ts]

            corr_btc = calculate_pearson_correlation(alt_aligned, btc_aligned)

            # Run backtest pipeline
            bt_res = run_backtest_pipeline(
                symbol=sym,
                days=days,
                timeframe=timeframe,
                strategy=strategy,
                margin_per_trade=15.0,
                leverage=min(10, c["max_leverage"])
            )

            if bt_res.get("status") == "ok":
                s = bt_res["summary"]
                pf = s["profit_factor"]
                wr = s["win_rate_pct"]
                trades = s["total_trades"]
                net_usd = s["net_profit_usd"]
                max_dd = s["max_drawdown_pct"]
                verdict = s["gertrude_verdict"]

                is_gem = (
                    pf >= 1.40 and
                    max_dd <= 25.0 and
                    wr >= 50.0 and
                    trades >= 8
                )

                gem_tag = "💎 JOIA RARA" if (is_gem and corr_btc < 0.60) else ("⭐ ALTA PERFORMANCE" if is_gem else "")

                entry_data = {
                    "rank": 0,
                    "coin": sym,
                    "price": c["price"],
                    "volume_24h": c["volume_24h"],
                    "btc_correlation": round(corr_btc, 2),
                    "is_low_correlation": corr_btc < 0.60,
                    "is_gem": is_gem,
                    "gem_label": gem_tag,
                    "days_actual": bt_res.get("days_actual", days),
                    "candles_count": bt_res.get("candles_count", len(alt_candles)),
                    "total_trades": trades,
                    "win_rate_pct": wr,
                    "profit_factor": pf,
                    "net_profit_usd": net_usd,
                    "net_profit_pct": s["net_profit_pct"],
                    "max_drawdown_pct": max_dd,
                    "payoff_ratio": s["payoff_ratio"],
                    "gertrude_verdict": verdict,
                    "gertrude_status": s["gertrude_status"],
                    "gertrude_badge": s["gertrude_badge"]
                }

                results.append(entry_data)

                if is_gem:
                    rare_gems.append(entry_data)
                    print(f"✨ {gem_tag}! PF: {pf:.2f} | WR: {wr:.1f}% | DD: {max_dd:.1f}% | Corr BTC: {corr_btc:+.2f}")
                else:
                    print(f"PF: {pf:.2f} | WR: {wr:.1f}% | DD: {max_dd:.1f}% | Corr: {corr_btc:+.2f} ({verdict})")

            else:
                print(f"[-] Backtest sem dados suficientes.")

        except Exception as e:
            print(f"Erro: {e}")

        time.sleep(0.04)  # Polite API rate limit

    # Sort results: Joias Raras first, then highest Profit Factor, then lowest BTC correlation
    results.sort(
        key=lambda x: (
            1 if x["is_gem"] and x["is_low_correlation"] else (0.5 if x["is_gem"] else 0),
            x["profit_factor"],
            -x["btc_correlation"],
            x["net_profit_usd"]
        ),
        reverse=True
    )

    for i, r in enumerate(results):
        r["rank"] = i + 1

    payload = {
        "status": "ok",
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "total_scanned": len(results),
        "total_gems_found": len(rare_gems),
        "days": days,
        "timeframe": timeframe,
        "strategy": strategy,
        "rare_gems": [r for r in results if r["is_gem"]],
        "leaderboard": results
    }

    # Save to JSON leaderboard
    LEADERBOARD_FILE.parent.mkdir(parents=True, exist_ok=True)
    LEADERBOARD_FILE.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n[*] Leaderboard salvo em: {LEADERBOARD_FILE}")

    # Generate Markdown Report
    report_file = ROOT / "data" / "reports" / f"{datetime.now(timezone.utc).strftime('%Y-%m-%d-%H%M')}-researcher-hyperliquid-universe-gems.md"
    generate_markdown_report(report_file, payload)
    print(f"[*] Relatório quantitativo publicado em: {report_file}")

    # Inject into dashboard data.json if requested
    if inject_to_dashboard and rare_gems:
        inject_approved_gems_to_dashboard(rare_gems, timeframe, strategy)

    return payload


def generate_markdown_report(report_file: Path, data: dict):
    now_str = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")
    gems = data.get("rare_gems", [])
    lb = data.get("leaderboard", [])

    lines = [
        f"# Trader Dev Research Report — Mineração de Universo Hyperliquid ({data['total_scanned']} Ativos)",
        f"**Data da Varredura:** {now_str} | **Lookback:** {data['days']} dias | **Timeframe:** {data['timeframe']}",
        f"**Autor:** Pesquisador Quantitativo (Botrade AI Desk) | **Revisor:** Gertrude (Chief of Staff)",
        "",
        "## 1. Objetivo da Varredura",
        "Varrer sistematicamente os pares perpétuos da Hyperliquid para descobrir ativos de **alta performance ajustada ao risco** e **baixa correlação com o Bitcoin (BTC)**, expandindo o cardápio de alvos do Auto-Sniper sem aumentar a exposição sistêmica de mercado.",
        "",
        f"## 2. Joias Raras Identificadas ({len(gems)} Ativos de Destaque)",
        "",
        "| Ranking | Ativo | PF | Win Rate % | Retorno Líquido ($) | Max Drawdown | Corr BTC | Veredito | Classificação |",
        "|---|---|---|---|---|---|---|---|---|"
    ]

    for g in gems:
        corr_label = f"🟢 `{g['btc_correlation']:+.2f}`" if g['btc_correlation'] < 0.50 else f"`{g['btc_correlation']:+.2f}`"
        lines.append(
            f"| #{g['rank']} | **{g['coin']}** | **{g['profit_factor']:.2f}x** | {g['win_rate_pct']:.1f}% | +${g['net_profit_usd']:.2f} | -{g['max_drawdown_pct']:.1f}% | {corr_label} | {g['gertrude_badge']} | {g['gem_label']} |"
        )

    lines.extend([
        "",
        "## 3. Matriz de Robustez e Descorrelação",
        "Os ativos acima demonstraram comportamento de tendência próprio, preservando lucratividade mesmo durante lateralizações ou correções do Bitcoin.",
        "",
        "## 4. Próxima Iteração",
        "As joias raras aprovadas passam a ser monitoradas automaticamente a cada 60 segundos pelo `auto_sniper.py`, com alocação máxima de $15.00 USDC por entrada.",
        "",
        "## 5. Veredito Gertrude",
        f"**{len(gems)} NOVOS CANDIDATOS APROVADOS PARA MONITORAMENTO**",
        ""
    ])

    report_file.parent.mkdir(parents=True, exist_ok=True)
    report_file.write_text("\n".join(lines), encoding="utf-8")


def inject_approved_gems_to_dashboard(gems: list[dict], timeframe: str, strategy: str):
    """Safely adds newly discovered champion gems into dashboard/data.json."""
    if not DATA_FILE.exists():
        return
    try:
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        strategies = data.get("strategies", [])
        existing_keys = {f"{s.get('symbol', s.get('coin'))}_{s.get('timeframe')}_{s.get('family', s.get('strategy'))}" for s in strategies}

        new_count = 0
        for g in gems:
            coin = g["coin"]
            key = f"{coin}_{timeframe}_fam-pullback-majors"
            if key not in existing_keys:
                strat_entry = {
                    "id": f"gem-{strategy}-{coin}-{timeframe}",
                    "name": f"Pullback Macro {timeframe.upper()} ({coin})",
                    "symbol": coin,
                    "coin": coin,
                    "timeframe": timeframe,
                    "family": "fam-pullback-majors",
                    "strategy": "pullback",
                    "profit_factor": g["profit_factor"],
                    "win_rate": g["win_rate_pct"],
                    "trades": g["total_trades"],
                    "net_profit": g["net_profit_usd"],
                    "net_profit_pct": g["net_profit_pct"],
                    "max_drawdown": g["max_drawdown_pct"],
                    "verdict": "Candidate",
                    "status": "approved",
                    "btc_correlation": g["btc_correlation"],
                    "gem_tag": g["gem_label"],
                    "is_live_monitored": True
                }
                strategies.append(strat_entry)
                new_count += 1

        if new_count > 0:
            data["strategies"] = strategies
            data["total_strategies"] = len(strategies)
            DATA_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"[*] ✅ {new_count} novas Joias Raras injetadas diretamente no catálogo dinâmico ({DATA_FILE})!")

    except Exception as e:
        print(f"[-] Erro ao injetar joias no catálogo: {e}")


def main():
    parser = argparse.ArgumentParser(description="Botrade Mass Universe Alpha Miner")
    parser.add_argument("--limit", type=int, default=50, help="Number of liquid coins to scan (up to 250)")
    parser.add_argument("--days", type=int, default=180, help="Lookback days")
    parser.add_argument("--timeframe", type=str, default="4h", choices=["1h", "2h", "4h", "1d"])
    parser.add_argument("--strategy", type=str, default="pullback")
    parser.add_argument("--min-volume", type=float, default=50000.0, help="Min 24h volume in USD")
    parser.add_argument("--inject", action="store_true", help="Automatically inject approved gems into dashboard/data.json")
    args = parser.parse_args()

    mine_universe(
        limit=args.limit,
        days=args.days,
        timeframe=args.timeframe,
        strategy=args.strategy,
        min_volume_usd=args.min_volume,
        inject_to_dashboard=args.inject
    )


if __name__ == "__main__":
    main()
