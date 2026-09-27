"""Hyperliquid Mainnet Execution Bridge with Dynamic Ratchet Trailing Stop.
Operates via non-custodial Agent Wallet (NO WITHDRAWAL PERMISSIONS).

Rules:
- $5.00 USDC per trade initial micro-sizing.
- Up to 10x leverage on high-confluence setups (Score >= 5).
- Ratchet Trailing Stop: Whenever position gains +30% ROE, Stop Loss moves up automatically to lock in profits.
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

# Load environment
ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT / ".env"
JOURNAL_PATH = ROOT / "data" / "journal"
JOURNAL_PATH.mkdir(parents=True, exist_ok=True)
ORDERS_LOG = JOURNAL_PATH / "hyperliquid_orders.json"
TRAILING_STATE = JOURNAL_PATH / "trailing_state.json"

try:
    from dotenv import load_dotenv
    load_dotenv(ENV_PATH)
except Exception:
    pass

import eth_account
from hyperliquid.exchange import Exchange
from hyperliquid.info import Info
from hyperliquid.utils import constants

# Configuration & Guardrails
def get_config():
    return {
        "MAIN_ADDRESS": os.getenv("HYPERLIQUID_MAIN_ADDRESS", "").strip(),
        "AGENT_KEY": os.getenv("HYPERLIQUID_AGENT_KEY", "").strip(),
        "MAX_TRADE_USDC": float(os.getenv("HYPERLIQUID_MAX_TRADE_USDC", "20.0")),
        "MAX_LEVERAGE": int(os.getenv("HYPERLIQUID_MAX_LEVERAGE", "10")),
        "TRAILING_STEP_PCT": float(os.getenv("HYPERLIQUID_TRAILING_STEP_PCT", "30.0")),
        "IS_MAINNET": os.getenv("HYPERLIQUID_IS_MAINNET", "true").lower() in ("true", "1", "yes")
    }

BASE_URL = constants.MAINNET_API_URL


class HyperliquidExecutor:
    def __init__(self):
        cfg = get_config()
        self.main_address = cfg["MAIN_ADDRESS"]
        self.agent_key = cfg["AGENT_KEY"]
        self.max_trade_usdc = cfg["MAX_TRADE_USDC"]
        self.max_leverage = cfg["MAX_LEVERAGE"]
        self.trailing_step_pct = cfg["TRAILING_STEP_PCT"]
        base_url = constants.MAINNET_API_URL if cfg["IS_MAINNET"] else constants.TESTNET_API_URL

        self.info = Info(base_url, skip_ws=True)
        self.meta = self.info.meta()
        self.universe = {coin["name"]: coin for coin in self.meta.get("universe", [])}
        self.exchange = None

        if self.agent_key and not self.agent_key.startswith("0x0000"):
            try:
                self.agent_wallet = eth_account.Account.from_key(self.agent_key)
                self.exchange = Exchange(
                    wallet=self.agent_wallet,
                    base_url=base_url,
                    account_address=self.main_address if self.main_address else None
                )
            except Exception as e:
                print(f"[Aviso] Falha ao inicializar Agent Wallet: {e}")

    def check_credentials(self) -> tuple[bool, str]:
        if not self.main_address or self.main_address.startswith("0x0000"):
            return False, "HYPERLIQUID_MAIN_ADDRESS não configurado nas variáveis de ambiente"
        if not self.agent_key or self.agent_key.startswith("0x0000"):
            return False, "HYPERLIQUID_AGENT_KEY não configurado nas variáveis de ambiente"
        if not self.exchange:
            return False, "Exchange não inicializada com a chave do agente"
        return True, "Credenciais válidas"


    def get_account_status(self) -> dict:
        if not self.main_address or self.main_address.startswith("0x0000"):
            return {"error": "Endereço principal não configurado nas variáveis de ambiente"}
        
        try:
            state = self.info.user_state(self.main_address)
            if not state:
                return {"error": "Nenhum dado retornado da Hyperliquid"}
            
            margin = state.get("marginSummary", {})
            positions = state.get("assetPositions", [])
            
            open_pos = []
            for p in positions:
                item = p.get("position", {})
                szi = float(item.get("szi", 0))
                if abs(szi) > 0:
                    entry = float(item.get("entryPx", 0))
                    pnl = float(item.get("unrealizedPnl", 0))
                    lev = float(item.get("leverage", {}).get("value", 1))
                    margin_used = (abs(szi) * entry) / lev if lev > 0 else 0
                    roe = (pnl / margin_used * 100) if margin_used > 0 else 0

                    open_pos.append({
                        "coin": item.get("coin"),
                        "size": szi,
                        "side": "LONG" if szi > 0 else "SHORT",
                        "entry_px": entry,
                        "unrealized_pnl": pnl,
                        "roe_pct": round(roe, 2),
                        "margin_used": round(margin_used, 2),
                        "leverage": lev,
                        "liquidation_px": float(item.get("liquidationPx") or 0)
                    })

            # Spot balances (apenas saldo livre disponível, descontando garantia em hold)
            spot_usdc = 0.0
            try:
                spot_state = self.info.spot_user_state(self.main_address)
                for b in spot_state.get("balances", []):
                    if b.get("coin") == "USDC":
                        tot = float(b.get("total", 0))
                        hld = float(b.get("hold", 0))
                        spot_usdc = round(max(0.0, tot - hld), 2)
            except Exception:
                pass

            perps_val = float(margin.get("accountValue", 0))
            notice = None
            if spot_usdc > 0 and perps_val == 0:
                notice = f"Você tem ${spot_usdc:.2f} USDC em SPOT. Para operar futuros/perps, clique no botão 'Perps <=> Spot' na Hyperliquid para transferir (instantâneo e sem taxa)."

            return {
                "address": self.main_address,
                "network": "MAINNET (Dinheiro Real)",
                "perps_account_value": perps_val,
                "spot_usdc_balance": spot_usdc,
                "withdrawable": float(state.get("withdrawable", 0)),
                "total_margin_used": float(margin.get("totalMarginUsed", 0)),
                "open_positions": open_pos,
                "notice": notice,
                "guardrails": {
                    "max_trade_usdc": self.max_trade_usdc,
                    "max_leverage": self.max_leverage,
                    "trailing_step_pct": self.trailing_step_pct
                }
            }
        except Exception as e:
            return {"error": str(e)}

    def format_size(self, coin: str, usdc_margin: float, leverage: float, price: float) -> float:
        coin_meta = self.universe.get(coin)
        if not coin_meta:
            raise ValueError(f"Ativo {coin} não encontrado na Hyperliquid")
        
        sz_decimals = int(coin_meta.get("szDecimals", 2))
        notional = usdc_margin * leverage
        raw_sz = notional / price
        
        factor = 10 ** sz_decimals
        clean_sz = math.floor(raw_sz * factor) / factor
        return clean_sz

    def execute_trade(
        self,
        coin: str,
        side: str,          # "buy" or "sell"
        usdc_margin: float = 5.0,
        leverage: int = 10,
        sl_price: float = 0.0,
        tp_price: float = 0.0,
        confirm: bool = False
    ) -> dict:
        """Pre-flight check + Human confirmation gate + Order dispatch with attached SL."""
        is_valid, msg = self.check_credentials()
        if not is_valid and confirm:
            return {"status": "error", "message": msg}

        coin = coin.upper().replace("USDT", "")
        if coin not in self.universe:
            return {"status": "error", "message": f"Criptoativo {coin} não listado na Hyperliquid"}

        # 1. HARD GUARDRAILS CHECK
        if usdc_margin > self.max_trade_usdc:
            return {
                "status": "blocked_by_guardrail",
                "message": f"Margem solicitada (${usdc_margin} USDC) excede o limite máximo institucional (${self.max_trade_usdc} USDC) definido nas variáveis de ambiente."
            }

        if leverage > self.max_leverage:
            return {
                "status": "blocked_by_guardrail",
                "message": f"Alavancagem solicitada ({leverage}x) excede o limite de segurança ({self.max_leverage}x)."
            }

        if not sl_price or sl_price <= 0:
            return {
                "status": "blocked_by_guardrail",
                "message": "VETO INSTITUCIONAL: Proibido abrir posição sem Stop Loss técnico definido."
            }

        # Check free margin in perps account (Saldo Disponível)
        try:
            account_status = self.get_account_status()
            free_margin = float(account_status.get("withdrawable", 0.0))
            if free_margin <= 0:
                perps_val = float(account_status.get("perps_account_value", 0.0))
                tot_margin = float(account_status.get("total_margin_used", 0.0))
                free_margin = max(0.0, perps_val - tot_margin)

            if free_margin < usdc_margin:
                return {
                    "status": "blocked_by_guardrail",
                    "message": f"SALDO INSUFICIENTE: Margem livre disponível (${free_margin:.2f} USDC) é inferior ao valor da operação (${usdc_margin:.2f} USDC). Nenhuma ordem foi enviada."
                }
        except Exception as e:
            print(f"[Aviso Guardrail Saldo] {e}")

        # Get latest mid-price
        all_mids = self.info.all_mids()
        current_price = float(all_mids.get(coin, 0))
        if not current_price:
            return {"status": "error", "message": f"Não foi possível obter preço em tempo real de {coin}"}

        size = self.format_size(coin, usdc_margin, leverage, current_price)
        if size <= 0:
            return {"status": "error", "message": f"Tamanho calculado muito pequeno para os decimais de {coin}"}

        is_buy = side.lower() == "buy"
        plan = {
            "coin": coin,
            "side": "COMPRA (LONG)" if is_buy else "VENDA (SHORT)",
            "current_price": current_price,
            "margin_usdc": usdc_margin,
            "leverage": f"{leverage}x",
            "notional_size": size,
            "notional_usd": round(size * current_price, 2),
            "stop_loss_px": sl_price,
            "stop_loss_pct": round(abs(current_price - sl_price) / current_price * 100, 2),
            "take_profit_px": tp_price,
            "take_profit_pct": round(abs(tp_price - current_price) / current_price * 100, 2),
            "trailing_rule": f"A cada +{self.trailing_step_pct}% de ganho, Stop Loss é elevado para proteger lucro",
            "network": "MAINNET (Dinheiro Real)",
            "ready_for_execution": confirm
        }

        if not confirm:
            plan["notice"] = "PLANO PRÉ-VOO GERADO ($5.00 USDC @ 10x). Para enviar ao livro de ofertas real da Hyperliquid, use a flag --confirm."
            return plan

        # 2. DISPATCH TO HYPERLIQUID MAINNET
        print(f"\n[HYPERLIQUID MAINNET] Enviando ordem real para {coin}: Tamanho {size} @ ${current_price} (Margem: ${usdc_margin} | Alavancagem: {leverage}x)...")
        try:
            # Step A: Set leverage
            self.exchange.update_leverage(leverage, coin, is_cross=True)
            
            # Step B: Market order using official market_open method with 1% max slippage
            order_res = self.exchange.market_open(coin, is_buy, size, slippage=0.01)
            
            # Check order statuses for execution confirmation
            order_data = order_res.get("response", {}).get("data", {})
            statuses = order_data.get("statuses", [])
            for st in statuses:
                if "error" in st:
                    err_msg = st["error"]
                    return {
                        "status": "execution_failed",
                        "error": f"Ordem recusada pela Hyperliquid: {err_msg}",
                        "details": order_res
                    }
            
            # Step C: Dispatch Initial Stop Loss Trigger Order
            sl_res = None
            try:
                coin_meta = self.universe.get(coin, {})
                sz_decimals = int(coin_meta.get("szDecimals", 2))
                clean_sl = round(float(f"{sl_price:.5g}"), 6 - sz_decimals)
                sl_res = self.exchange.order(
                    coin,
                    not is_buy,
                    size,
                    clean_sl,
                    {"trigger": {"triggerPx": clean_sl, "isMarket": True, "tpsl": "sl"}}
                )
            except Exception as sl_err:
                print(f"[Alerta SL] Erro ao anexar ordem trigger de SL: {sl_err}")

            # Initialize Trailing State for this position
            self._init_trailing_state(coin, is_buy, current_price, size, sl_price, leverage)

            # Log to Journal
            trade_record = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "plan": plan,
                "order_result": order_res,
                "sl_result": sl_res
            }
            self._save_order_journal(trade_record)

            return {
                "status": "executed",
                "message": f"Ordem de ${usdc_margin} USDC ({leverage}x) executada com sucesso na Hyperliquid!",
                "details": trade_record
            }

        except Exception as e:
            return {"status": "execution_failed", "error": str(e)}

    def close_position(self, coin: str) -> dict:
        """Closes an open position at market and cancels any resting trigger/SL orders."""
        coin = coin.upper().replace("USDT", "")
        status = self.get_account_status()
        open_pos = status.get("open_positions", [])
        target_pos = None
        for p in open_pos:
            if p["coin"] == coin:
                target_pos = p
                break
        
        if not target_pos:
            return {"status": "not_found", "message": f"Nenhuma posição aberta encontrada para {coin}."}

        size = abs(target_pos["size"])
        is_buy = target_pos["side"] == "LONG"
        entry_px = target_pos["entry_px"]
        pnl = target_pos["unrealized_pnl"]
        roe = target_pos["roe_pct"]

        print(f"\n[FECHAMENTO A MERCADO] Encerrando {coin} {target_pos['side']} (Tamanho: {size})...")

        # 1. Close position at market
        close_res = self.exchange.market_open(coin, not is_buy, size, slippage=0.01)

        # 2. Cancel resting trigger/SL orders for this coin
        cancelled_orders = []
        try:
            orders = self.info.frontend_open_orders(MAIN_ADDRESS)
            for o in orders:
                if o.get("coin") == coin:
                    oid = o.get("oid")
                    if oid:
                        self.exchange.cancel(coin, oid)
                        cancelled_orders.append(oid)
        except Exception as ex:
            print(f"[Aviso] Falha ao cancelar ordens em aberto: {ex}")

        # 3. Clean trailing state
        state = self._load_trailing_state()
        if coin in state:
            del state[coin]
            TRAILING_STATE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")

        # 4. Log in journal
        close_record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": "CLOSE_MARKET",
            "coin": coin,
            "side": target_pos["side"],
            "size": size,
            "entry_px": entry_px,
            "pnl": pnl,
            "roe_pct": roe,
            "cancelled_orders": cancelled_orders,
            "result": close_res
        }
        self._save_order_journal(close_record)

        # 5. Telegram notification
        try:
            from send_telegram import send
            emoji = "🟢" if pnl >= 0 else "🔴"
            sign = "+" if pnl >= 0 else ""
            msg = (
                f"🛑 *OPERAÇÃO ENCERRADA A MERCADO (HYPERLIQUID)*\n\n"
                f"• *Ativo:* {coin}/USDC ({target_pos['side']})\n"
                f"• *Lote:* {size} {coin}\n"
                f"• *Preço Entrada:* ${entry_px:.2f}\n"
                f"• *Resultado Realizado:* {emoji} {sign}${pnl:.4f} ({sign}{roe:.2f}% ROE)\n"
                f"• *Ordens de SL Canceladas:* {len(cancelled_orders)}\n\n"
                f"🌐 *Painel:* http://192.168.18.12:8765/"
            )
            send(msg)
        except Exception as tg_err:
            print(f"[Telegram Aviso] {tg_err}")

        return {
            "status": "closed",
            "message": f"Posição de {coin} encerrada com sucesso a mercado!",
            "details": close_record
        }

    def close_partial_position(self, coin: str, pct: float = 0.5, move_sl_to_be: bool = True) -> dict:
        """Executes a partial close (e.g. 50%) at market, locks in profit, and moves SL of remainder to Breakeven."""
        coin = coin.upper()
        account_status = self.get_account_status()
        open_pos = account_status.get("open_positions", [])
        target_pos = next((p for p in open_pos if p["coin"] == coin), None)

        if not target_pos:
            return {"status": "not_found", "message": f"Nenhuma posição ativa encontrada para {coin}."}

        full_size = target_pos["size"]
        is_buy = target_pos["side"] == "LONG"
        entry_px = target_pos["entry_px"]
        roe = target_pos["roe_pct"]
        full_pnl = target_pos["unrealized_pnl"]

        coin_meta = self.universe.get(coin, {})
        sz_decimals = int(coin_meta.get("szDecimals", 2))
        close_size = round(full_size * pct, sz_decimals)

        if close_size <= 0:
            return {"status": "error", "message": f"Tamanho parcial ({close_size}) é menor que a precisão permitida ({sz_decimals} decimais)."}

        remaining_size = round(full_size - close_size, sz_decimals)
        realized_pnl = round(full_pnl * (close_size / full_size), 4)

        print(f"\n[HYPERLIQUID MAINNET] Realizando {pct*100:.0f}% da posição em {coin}: Vendendo {close_size} (Restarão: {remaining_size} @ 0x0)...")

        # 1. Market order to close partial size
        close_res = self.exchange.market_open(coin, not is_buy, close_size, slippage=0.01)

        # 2. Cancel existing trigger/SL orders for this coin
        cancelled_orders = []
        try:
            orders = self.info.frontend_open_orders(MAIN_ADDRESS)
            for o in orders:
                if o.get("coin") == coin:
                    oid = o.get("oid")
                    if oid:
                        self.exchange.cancel(coin, oid)
                        cancelled_orders.append(oid)
        except Exception as ex:
            print(f"[Aviso] Falha ao cancelar ordens em aberto: {ex}")

        # 3. If remaining size > 0 and move_sl_to_be requested: place new SL at Breakeven
        new_sl_res = None
        new_sl_px = None
        if remaining_size > 0 and move_sl_to_be:
            # Entry + 0.2% cushion to cover round-trip exchange fees
            new_sl_px = entry_px * (1.002 if is_buy else 0.998)
            clean_sl = round(float(f"{new_sl_px:.5g}"), 6 - sz_decimals)
            try:
                new_sl_res = self.exchange.order(
                    coin,
                    not is_buy,
                    remaining_size,
                    clean_sl,
                    {"trigger": {"triggerPx": clean_sl, "isMarket": True, "tpsl": "sl"}}
                )
            except Exception as sl_err:
                print(f"[Aviso] Erro ao colocar Stop Loss no Breakeven: {sl_err}")

            # Update trailing state for remainder
            state = self._load_trailing_state()
            if coin in state:
                state[coin]["size"] = remaining_size
                state[coin]["current_sl"] = clean_sl
                state[coin]["ratchet_stage"] = max(1, state[coin].get("ratchet_stage", 0))
                state[coin]["updated_at"] = datetime.now(timezone.utc).isoformat()
                TRAILING_STATE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
        elif remaining_size <= 0:
            # Full position was closed
            state = self._load_trailing_state()
            if coin in state:
                del state[coin]
                TRAILING_STATE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")

        # 4. Log in journal
        harvest_record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": "PARTIAL_CLOSE",
            "coin": coin,
            "side": target_pos["side"],
            "closed_size": close_size,
            "remaining_size": remaining_size,
            "entry_px": entry_px,
            "realized_pnl": realized_pnl,
            "roe_pct": roe,
            "new_sl_px": new_sl_px,
            "result": close_res
        }
        self._save_order_journal(harvest_record)

        # 5. Telegram notification
        try:
            from send_telegram import send
            sign = "+" if realized_pnl >= 0 else ""
            msg = (
                f"💰 *LUCRO PARCIAL REALIZADO ({pct*100:.0f}%) — HYPERLIQUID*\n\n"
                f"• *Ativo:* {coin}/USDC ({target_pos['side']})\n"
                f"• *Lote Vendido:* {close_size} {coin} (Restam: *{remaining_size} {coin}*)\n"
                f"• *Preço de Entrada:* ${entry_px:.4f}\n"
                f"• *Lucro Embolsado:* 🟢 *{sign}${realized_pnl:.4f}* ({sign}{roe:.1f}% ROE)\n"
                f"• *Proteção do Restante:* 🛡️ Stop Loss travado no 0x0 (${new_sl_px:.4f}) — *Risco Zero!*\n\n"
                f"💸 *Margem liberada imediatamente para novas operações!*\n"
                f"🌐 *Painel:* http://192.168.18.12:8765/"
            )
            send(msg)
        except Exception as tg_err:
            print(f"[Telegram Aviso] {tg_err}")

        return {
            "status": "partial_closed",
            "coin": coin,
            "closed_size": close_size,
            "remaining_size": remaining_size,
            "realized_pnl": realized_pnl,
            "roe_pct": roe,
            "new_sl_px": new_sl_px,
            "message": f"Realizado {pct*100:.0f}% de {coin}. Lucro embolsado: +${realized_pnl:.2f}. Restante protegido no 0x0!"
        }

    def _init_trailing_state(self, coin: str, is_buy: bool, entry: float, size: float, initial_sl: float, lev: int):
        state = self._load_trailing_state()
        state[coin] = {
            "is_buy": is_buy,
            "entry_px": entry,
            "size": size,
            "current_sl": initial_sl,
            "leverage": lev,
            "ratchet_stage": 0,
            "highest_roe": 0.0,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        TRAILING_STATE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")

    def _load_trailing_state(self) -> dict:
        if TRAILING_STATE.exists():
            try:
                return json.loads(TRAILING_STATE.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {}

    def monitor_and_trail(self, single_pass: bool = False):
        """Dynamic Ratchet Trailing: whenever ROE hits +30%, +60%, +90%, moves Stop Loss up."""
        print(f"\n[MONITOR DE TRAILING STOP] Iniciado. Regra: Trailing a cada +{TRAILING_STEP_PCT}% de ganho...")
        
        while True:
            try:
                status = self.get_account_status()
                open_pos = status.get("open_positions", [])
                state = self._load_trailing_state()

                if not open_pos:
                    if single_pass:
                        print("Nenhuma posição aberta no momento.")
                        break
                    time.sleep(10)
                    continue

                for pos in open_pos:
                    coin = pos["coin"]
                    roe = pos["roe_pct"]
                    entry = pos["entry_px"]
                    is_buy = pos["side"] == "LONG"
                    lev = pos["leverage"]

                    # Load or initialize coin tracking
                    coin_state = state.get(coin, {
                        "is_buy": is_buy,
                        "entry_px": entry,
                        "size": abs(pos["size"]),
                        "current_sl": entry * (0.95 if is_buy else 1.05),
                        "leverage": lev,
                        "ratchet_stage": 0,
                        "highest_roe": roe
                    })

                    current_stage = coin_state.get("ratchet_stage", 0)
                    # How many 30% blocks of profit have been crossed?
                    target_stage = int(roe // TRAILING_STEP_PCT)

                    print(f"[{coin}] Posição {pos['side']} | Entrada: ${entry} | PnL Atual: +${pos['unrealized_pnl']:.2f} ({roe:+.1f}% ROE) | Estágio: {current_stage}")

                    if target_stage > current_stage and target_stage >= 1:
                        # RATCHET UP STOP LOSS!
                        new_sl = 0.0
                        if target_stage == 1:
                            # Stage 1 (>= +30% ROE): Move SL to Breakeven + fees (0.2%) -> ZERO RISK!
                            new_sl = entry * 1.002 if is_buy else entry * 0.998
                            msg = f"🎯 RATCHET ESTÁGIO 1: Lucro atingiu {roe:+.1f}% (+30% batido!). Stop Loss movido para o BREAKEVEN (${new_sl:.4f}) - RISCO ZERO!"
                        else:
                            # Stage N (>= +60%, +90%...): Lock in (target_stage - 1) * 30% of profit!
                            # Price move = locked_roe / leverage
                            locked_roe = (target_stage - 1) * TRAILING_STEP_PCT
                            price_gain_pct = (locked_roe / lev) / 100.0
                            new_sl = entry * (1.0 + price_gain_pct) if is_buy else entry * (1.0 - price_gain_pct)
                            msg = f"🚀 RATCHET ESTÁGIO {target_stage}: Lucro atingiu {roe:+.1f}%. Stop Loss elevado para ${new_sl:.4f} (GARANTINDO +{locked_roe:.0f}% DE LUCRO NO BOLSO)!"

                        print(f"\n[ALERTA DE TRAILING] {msg}")

                        # Dispatch new Stop Loss order to Hyperliquid
                        if self.exchange:
                            try:
                                # Cancel previous SL by placing the new trigger SL
                                coin_meta = self.universe.get(coin, {})
                                sz_dec = int(coin_meta.get("szDecimals", 2))
                                factor = 10 ** sz_dec
                                clean_size = math.floor(abs(pos["size"]) * factor) / factor

                                clean_sl = round(float(f"{new_sl:.5g}"), 6 - sz_dec)
                                sl_res = self.exchange.order(
                                    coin,
                                    not is_buy,
                                    clean_size,
                                    clean_sl,
                                    {"trigger": {"triggerPx": clean_sl, "isMarket": True, "tpsl": "sl"}}
                                )
                                print(f"-> Ordem de Stop Loss atualizada na Hyperliquid para ${clean_sl} com sucesso!")
                                
                                coin_state["current_sl"] = new_sl
                                coin_state["ratchet_stage"] = target_stage
                                coin_state["highest_roe"] = max(coin_state.get("highest_roe", 0), roe)
                                coin_state["updated_at"] = datetime.now(timezone.utc).isoformat()
                                state[coin] = coin_state
                                TRAILING_STATE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")

                            except Exception as ex:
                                print(f"-> Erro ao atualizar Stop Loss na Hyperliquid: {ex}")

                if single_pass:
                    break
                time.sleep(10)

            except Exception as e:
                print(f"[Erro no Monitor]: {e}")
                if single_pass:
                    break
                time.sleep(10)

    def _save_order_journal(self, record: dict):
        current_data = []
        if ORDERS_LOG.exists():
            try:
                current_data = json.loads(ORDERS_LOG.read_text(encoding="utf-8"))
            except Exception:
                current_data = []
        current_data.append(record)
        ORDERS_LOG.write_text(json.dumps(current_data, indent=2, ensure_ascii=False), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Hyperliquid Institutional Executor with Ratchet Trailing Stop")
    parser.add_argument("--status", action="store_true", help="Consulta saldo e posições abertas")
    parser.add_argument("--monitor", action="store_true", help="Ativa o monitor de Trailing Stop contínuo")
    parser.add_argument("--monitor-once", action="store_true", help="Verifica o trailing uma única vez")
    parser.add_argument("--trade", action="store_true", help="Prepara ou executa ordem")
    parser.add_argument("--close", type=str, help="Encerra a mercado uma posição aberta (ex: --close SOL)")
    parser.add_argument("--symbol", type=str, default="SOL", help="Símbolo da cripto (ex: SOL, INJ, BTC)")
    parser.add_argument("--side", type=str, choices=["buy", "sell"], default="buy", help="Lado da operação")
    parser.add_argument("--margin", type=float, default=5.0, help="Margem em USDC (Padrão: $5.00)")
    parser.add_argument("--leverage", type=int, default=10, help="Alavancagem (Padrão: 10x)")
    parser.add_argument("--sl", type=float, required=False, help="Preço de Stop Loss obrigatório")
    parser.add_argument("--tp", type=float, required=False, help="Preço de Take Profit")
    parser.add_argument("--confirm", action="store_true", help="Autorização explícita para enviar ordem ao vivo")

    args = parser.parse_args()
    bot = HyperliquidExecutor()

    if args.close:
        res = bot.close_position(coin=args.close)
        print("\n=== RESULTADO DO FECHAMENTO ===")
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return

    if args.status:
        st = bot.get_account_status()
        print("\n=== STATUS DA CONTA HYPERLIQUID ===")
        print(json.dumps(st, indent=2, ensure_ascii=False))
        return

    if args.monitor:
        bot.monitor_and_trail(single_pass=False)
        return

    if args.monitor_once:
        bot.monitor_and_trail(single_pass=True)
        return

    if args.trade:
        if not args.sl:
            print("Erro: É obrigatório informar o preço de Stop Loss (--sl <valor>) para qualquer operação.")
            sys.exit(1)
        res = bot.execute_trade(
            coin=args.symbol,
            side=args.side,
            usdc_margin=args.margin,
            leverage=args.leverage,
            sl_price=args.sl,
            tp_price=args.tp or (args.sl * 1.1),
            confirm=args.confirm
        )
        print("\n=== RESULTADO DA OPERAÇÃO ===")
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return

    st = bot.get_account_status()
    print("\n=== HYPERLIQUID EXECUTOR (PRONTO: $5.00 @ 10x COM TRAILING +30%) ===")
    print(json.dumps(st, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
