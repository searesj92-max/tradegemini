"""Live Position & Ratchet Trailing Stop Monitor for Hyperliquid Mainnet.
Runs continuously, synchronizing live on-chain state to dashboard/live_positions.json.
Automatically raises Stop Loss on Hyperliquid orderbook at each +30% ROE increment.
"""
from __future__ import annotations

import json
import math
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from hyperliquid_executor import HyperliquidExecutor, TRAILING_STATE, ORDERS_LOG
from send_telegram import send

OUTPUT_JSON = ROOT / "dashboard" / "live_positions.json"


def run_monitor():
    print("[*] Iniciando Motor de Monitoramento Ao Vivo Hyperliquid Mainnet...")
    executor = HyperliquidExecutor()
    TRAILING_STEP_PCT = 30.0
    active_snapshot: dict[str, dict] = {}

    while True:
        try:
            status = executor.get_account_status()
            open_pos = status.get("open_positions", [])
            
            # Load trailing state
            state = {}
            if TRAILING_STATE.exists():
                try:
                    state = json.loads(TRAILING_STATE.read_text(encoding="utf-8"))
                except Exception:
                    pass

            # Load recent orders from journal
            recent_orders = []
            if ORDERS_LOG.exists():
                try:
                    recent_orders = json.loads(ORDERS_LOG.read_text(encoding="utf-8"))
                except Exception:
                    pass

            formatted_positions = []

            for pos in open_pos:
                coin = pos["coin"]
                roe = pos["roe_pct"]
                entry = pos["entry_px"]
                is_buy = pos["side"] == "LONG"
                lev = pos["leverage"]
                size = abs(pos["size"])
                unrealized_pnl = pos["unrealized_pnl"]

                # Get current mid / mark price
                current_price = entry + (unrealized_pnl / size if is_buy else -unrealized_pnl / size)
                try:
                    dex_mids = executor.info.all_mids()
                    if coin in dex_mids:
                        current_price = float(dex_mids[coin])
                except Exception:
                    pass

                # Coin trailing state
                coin_state = state.get(coin, {
                    "is_buy": is_buy,
                    "entry_px": entry,
                    "size": size,
                    "current_sl": entry * (0.976 if is_buy else 1.024),
                    "leverage": lev,
                    "ratchet_stage": 0,
                    "highest_roe": roe
                })

                current_sl = coin_state.get("current_sl", entry * 0.976)
                current_stage = coin_state.get("ratchet_stage", 0)
                highest_roe = max(coin_state.get("highest_roe", 0.0), roe)
                coin_state["highest_roe"] = highest_roe

                # Ratchet targets
                next_ratchet_stage = current_stage + 1
                next_ratchet_roe = next_ratchet_stage * TRAILING_STEP_PCT
                price_gain_needed = (next_ratchet_roe / lev) / 100.0
                next_ratchet_price = entry * (1.0 + price_gain_needed) if is_buy else entry * (1.0 - price_gain_needed)

                # Progress percentage towards next ratchet
                prev_roe_floor = current_stage * TRAILING_STEP_PCT
                progress_pct = 0.0
                if next_ratchet_roe > prev_roe_floor:
                    progress_pct = max(0.0, min(100.0, ((roe - prev_roe_floor) / (next_ratchet_roe - prev_roe_floor)) * 100.0))

                # Stop loss distance
                sl_distance_pct = ((current_price - current_sl) / current_price * 100) if is_buy else ((current_sl - current_price) / current_price * 100)

                # Stage name
                stage_names = {
                    0: "Estágio 0: Stop Loss Inicial (2.0x ATR)",
                    1: "Estágio 1: Breakeven (Risco Zero Blindado!)",
                    2: "Estágio 2: Lucro Travado em +30% ROE ($1.50 Garantido)",
                    3: "Estágio 3: Lucro Travado em +60% ROE ($3.00 Garantido)",
                    4: "Estágio 4: Lucro Travado em +90% ROE ($4.50 Garantido)"
                }
                stage_name = stage_names.get(current_stage, f"Estágio {current_stage}: Lucro Travado em +{(current_stage-1)*30}%")

                # Check if target stage reached
                target_stage = int(roe // TRAILING_STEP_PCT)
                if target_stage > current_stage and target_stage >= 1:
                    new_sl = 0.0
                    if target_stage == 1:
                        new_sl = entry * 1.002 if is_buy else entry * 0.998
                        print(f"\n🎯 [RATCHET ESTÁGIO 1] Lucro bateu {roe:+.2f}% (+30% atingido!). Elevando SL para Breakeven (${new_sl:.4f}) - RISCO ZERO!")
                    else:
                        locked_roe = (target_stage - 1) * TRAILING_STEP_PCT
                        price_gain = (locked_roe / lev) / 100.0
                        new_sl = entry * (1.0 + price_gain) if is_buy else entry * (1.0 - price_gain)
                        print(f"\n🚀 [RATCHET ESTÁGIO {target_stage}] Lucro bateu {roe:+.2f}%. Elevando SL para ${new_sl:.4f} (Garantindo +{locked_roe:.0f}% de lucro)!")

                    if executor.exchange:
                        try:
                            coin_meta = executor.universe.get(coin, {})
                            sz_dec = int(coin_meta.get("szDecimals", 2))
                            factor = 10 ** sz_dec
                            clean_size = math.floor(size * factor) / factor
                            clean_sl = round(float(f"{new_sl:.5g}"), 6 - sz_dec)

                            executor.exchange.order(
                                coin,
                                not is_buy,
                                clean_size,
                                clean_sl,
                                {"trigger": {"triggerPx": clean_sl, "isMarket": True, "tpsl": "sl"}}
                            )
                            current_sl = clean_sl
                            current_stage = target_stage
                            coin_state["current_sl"] = clean_sl
                            coin_state["ratchet_stage"] = target_stage
                            coin_state["updated_at"] = datetime.now(timezone.utc).isoformat()
                            state[coin] = coin_state
                            TRAILING_STATE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
                            print(f"[+] Stop Loss atualizado na Hyperliquid para ${clean_sl}!")

                            # Dispatch Telegram notification
                            try:
                                if target_stage == 1:
                                    tg_msg = (
                                        f"🎯 *RATCHET ESTÁGIO 1 ATINGIDO! (RISCO ZERO BLINDADO)*\n\n"
                                        f"🟢 *{coin}/USDC · {pos['side']}*\n"
                                        f"• *ROE Atingido:* +{roe:.2f}%\n"
                                        f"• *Novo Stop Loss:* ${clean_sl:.4f} (Preço de Entrada)\n"
                                        f"• *Blindagem:* Daqui para frente é impossível perder dinheiro neste trade!\n\n"
                                        f"🌐 *Painel:* http://192.168.18.12:8765/"
                                    )
                                else:
                                    locked_pct = (target_stage - 1) * TRAILING_STEP_PCT
                                    tg_msg = (
                                        f"🚀 *RATCHET ESTÁGIO {target_stage} ATINGIDO!*\n\n"
                                        f"🟢 *{coin}/USDC · {pos['side']}*\n"
                                        f"• *ROE Atingido:* +{roe:.2f}%\n"
                                        f"• *Novo Stop Loss:* ${clean_sl:.4f}\n"
                                        f"• *Lucro Mínimo Garantido:* +{locked_pct:.0f}% ROE (${(locked_pct/100.0)*pos['margin_used']:.2f})\n\n"
                                        f"🌐 *Painel:* http://192.168.18.12:8765/"
                                    )
                                send(tg_msg)
                            except Exception as tg_err:
                                print(f"[Telegram Aviso] {tg_err}")

                        except Exception as e:
                            print(f"[-] Erro ao atualizar SL: {e}")

                # Take Profit targets
                tp1 = entry * 1.0358 if is_buy else entry * 0.9642
                tp2 = entry * 1.0596 if is_buy else entry * 0.9404
                tp3 = entry * 1.0953 if is_buy else entry * 0.9047

                formatted_positions.append({
                    "coin": coin,
                    "side": pos["side"],
                    "size": size,
                    "entry_px": entry,
                    "current_price": round(current_price, 4),
                    "unrealized_pnl": round(unrealized_pnl, 4),
                    "roe_pct": round(roe, 2),
                    "highest_roe": round(highest_roe, 2),
                    "margin_used": pos["margin_used"],
                    "leverage": lev,
                    "current_sl": round(current_sl, 4),
                    "sl_distance_pct": round(sl_distance_pct, 2),
                    "next_ratchet_roe": next_ratchet_roe,
                    "next_ratchet_price": round(next_ratchet_price, 4),
                    "ratchet_stage": current_stage,
                    "ratchet_stage_name": stage_name,
                    "progress_pct": round(progress_pct, 1),
                    "tp1": round(tp1, 4),
                    "tp2": round(tp2, 4),
                    "tp3": round(tp3, 4),
                    "is_zero_risk": current_stage >= 1
                })

            # Detect closed positions
            current_coins = {p["coin"]: p for p in formatted_positions}
            for closed_coin, prev_pos in list(active_snapshot.items()):
                if closed_coin not in current_coins:
                    try:
                        pnl = prev_pos.get("unrealized_pnl", 0.0)
                        roe = prev_pos.get("roe_pct", 0.0)
                        emoji = "🟢" if pnl >= 0 else "🔴"
                        sign = "+" if pnl >= 0 else ""
                        tg_closed = (
                            f"🏁 *OPERAÇÃO FINALIZADA NA HYPERLIQUID*\n\n"
                            f"• *Ativo:* {closed_coin}/USDC\n"
                            f"• *Preço Entrada:* ${prev_pos.get('entry_px', 0):.2f}\n"
                            f"• *Último Resultado:* {emoji} {sign}${pnl:.4f} ({sign}{roe:.2f}% ROE)\n"
                            f"• *Status:* Posição encerrada (alvo ou stop atingido).\n\n"
                            f"🌐 *Painel:* http://192.168.18.12:8765/"
                        )
                        send(tg_closed)
                    except Exception as err:
                        print(f"[Telegram Closed Alerta] {err}")
                    del active_snapshot[closed_coin]

            # Update active snapshot
            for c_name, p in current_coins.items():
                active_snapshot[c_name] = p

            # Save state
            TRAILING_STATE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")

            # Build full live JSON payload for dashboard
            perps_equity = status.get("perps_account_value", 0.0)
            spot_usdc = status.get("spot_usdc_balance", 0.0)
            total_equity = perps_equity + spot_usdc
            margin_used = status.get("total_margin_used", 0.0)

            payload = {
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "network": "MAINNET (Dinheiro Real)",
                "address": status.get("address", ""),
                "total_equity": round(total_equity, 2),
                "perps_equity": round(perps_equity, 2),
                "spot_usdc": round(spot_usdc, 2),
                "margin_used": round(margin_used, 2),
                "available_margin": round(total_equity - margin_used, 2),
                "positions_count": len(formatted_positions),
                "positions": formatted_positions,
                "recent_orders": recent_orders[-10:]
            }

            OUTPUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

        except Exception as e:
            print(f"[Erro no Monitor] {e}")

        time.sleep(3)


if __name__ == "__main__":
    run_monitor()
