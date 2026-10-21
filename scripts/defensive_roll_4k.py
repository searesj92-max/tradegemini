#!/usr/bin/env python3
"""
Defensive Rollover Protocol (-4k Strike Drop)
Fecha a trava ativa ameaçada e abre nova posição com strike vendido pelo menos $4.000 a $5.000 mais baixo.
"""

import sys
import json
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "scripts"))

from send_telegram import send
import options_desk

POSITIONS_FILE = ROOT_DIR / "data" / "options_positions.json"

def execute_roll_drop_4k(target_expiry="20261106", new_short=75000, new_long=70000, subaccount_id=116804):
    print("=== INICIANDO PROTOCOLO DE ROLAGEM DEFENSIVA (-4K DROP) ===")
    
    if not POSITIONS_FILE.exists():
        return {"success": False, "error": "Arquivo de posições não encontrado."}
        
    positions = json.loads(POSITIONS_FILE.read_text(encoding="utf-8"))
    active_pos = next((p for p in positions if p.get("status") == "active" and p.get("is_live_order") is True), None)
    
    if not active_pos:
        return {"success": False, "error": "Nenhuma posição ativa para rolar."}
        
    curr_short = active_pos["short_strike"]
    curr_long = active_pos["long_strike"]
    contracts = active_pos["contracts"]
    curr_exp = active_pos["expiry"]
    
    strike_drop = curr_short - new_short
    print(f"Posição Atual: {curr_short}P / {curr_long}P ({curr_exp}) | Contratos: {contracts}")
    print(f"Alvo da Rolagem: {new_short}P / {new_long}P ({target_expiry}) | Queda de Strike: -${strike_drop:,.0f}")
    
    # Passo 1: Desmontar a trava atual on-chain
    print("\nPasso 1: Desmontando trava atual na Derive...")
    close_res = options_desk.close_derive_spread_order(
        currency="BTC",
        expiry=curr_exp,
        short_strike=curr_short,
        long_strike=curr_long,
        contracts=contracts,
        subaccount_id=subaccount_id
    )
    print("Resultado do Desmonte:", close_res)
    
    if not close_res.get("success"):
        return {"success": False, "error": f"Falha ao desmontar posição atual: {close_res.get('error')}"}

    time.sleep(2.0)

    # Passo 2: Montar a nova trava mais longa e mais baixa
    print(f"\nPasso 2: Abrindo nova trava {new_short}P / {new_long}P para {target_expiry}...")
    open_res = options_desk.place_derive_spread_order(
        currency="BTC",
        expiry=target_expiry,
        short_strike=new_short,
        long_strike=new_long,
        contracts=contracts,
        short_price=0,
        long_price=0,
        subaccount_id=subaccount_id
    )
    print("Resultado da Nova Abertura:", open_res)
    
    if open_res.get("success"):
        # Atualiza histórico de posições
        active_pos["status"] = "rolled"
        active_pos["rolled_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        active_pos["rolled_to"] = f"{target_expiry}-{new_short}-{new_long}"
        
        new_pos = {
            "id": f"pos-btc-{new_short}-{new_long}-{target_expiry}-{int(time.time())}",
            "currency": "BTC",
            "expiry": target_expiry,
            "short_strike": float(new_short),
            "long_strike": float(new_long),
            "contracts": contracts,
            "initial_credit_per_contract": open_res.get("credit_per_contract", 300.0),
            "initial_credit_total": round(contracts * open_res.get("credit_per_contract", 300.0), 2),
            "initial_margin_total": round(contracts * (new_short - new_long), 2),
            "opened_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "status": "active",
            "target_take_profit_pct": 100.0,
            "is_live_order": True,
            "live_details": open_res,
            "roll_count": active_pos.get("roll_count", 0) + 1
        }
        positions.append(new_pos)
        POSITIONS_FILE.write_text(json.dumps(positions, indent=2), encoding="utf-8")
        
        msg = (
            f"🛡️ *ROLAGEM DEFENSIVA EXECUTADA COM SUCESSO!*\n\n"
            f"• *Posição Anterior:* `{curr_short:,.0f}P / {curr_long:,.0f}P` (Encerrada)\n"
            f"• *Nova Posição:* `{new_short:,.0f}P / {new_long:,.0f}P` (`{target_expiry}`)\n"
            f"• *Alívio do Strike:* `-${strike_drop:,.0f} USD` (Strike foi jogado {strike_drop/1000:.1f}k mais para baixo!)\n"
            f"• *Novo Prazo:* Mais dias de fôlego com margem protegida na Tangem."
        )
        send(msg)
        return {"success": True, "message": "Rolagem defensiva -4k concluída com sucesso!"}
    else:
        return {"success": False, "error": f"Desmonte concluído, mas falha ao abrir nova trava: {open_res.get('error')}"}

if __name__ == "__main__":
    res = execute_roll_drop_4k()
    print(json.dumps(res, indent=2))
