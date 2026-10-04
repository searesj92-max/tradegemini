#!/usr/bin/env python3
"""
On-chain auditor for the VIRTUAL / WETH Krystal Autopilot position (Uniswap V3, Base).

Reads everything from the chain instead of hardcoded numbers:
- every rebalance cycle (DecreaseLiquidity + Collect logs) -> real fees per closed NFT
- active NFT (highest tokenId with liquidity > 0) -> range, liquidity, token amounts
- pending (uncollected) fees via a static `collect` call
- dust returned to the wallet by the Krystal keeper

IMPORTANT accounting note: Krystal compounds collected fees into the next NFT.
So "pool value + wallet dust + pending fees" already CONTAINS all collected fees.
Collected fees must never be added on top again (that would double count).
"""

from __future__ import annotations

import json
import math
import time
import urllib.request
from datetime import datetime, timezone

WALLET = "0xa36C0cb2159Fd132A6EFe461E170cf399a503a54"
NPM = "0x03a520b32C04BF3bEEf7BEb72E919cf822Ed34f1"
POOL = "0x9c087Eb773291e50CF6c6a90ef0F4500e349B903"
VIRTUAL_TOKEN = "0x0b3e328455c4059eeb9e3f84b5543f74e24e7e1b"
WETH_TOKEN = "0x4200000000000000000000000000000000000006"
RPCS = ["https://base-rpc.publicnode.com", "https://1rpc.io/base", "https://mainnet.base.org"]
UA = {"User-Agent": "Mozilla/5.0"}

# Initial deposit (tx 0xb5e6cbaa..., 2026-09-30 21:45 UTC): 0.152261 WETH sent, 0.000642 WETH returned
INITIAL_WETH = 0.151619
INITIAL_USD = 406.46
INITIAL_HODL_VIRTUAL = 252.2202   # what the first NFT received after the swap
INITIAL_HODL_WETH = 0.077139      # 0.076497 in NFT + 0.000642 dust
START_ISO = "2026-09-30T21:45:55+00:00"
MIN_TOKEN_ID = 6100000

TOPIC_DEC = "0x26f6a048ee9138f2c0ce266f322cb99228e8d619ae2bff30c67f8dcf9d2377b4"
TOPIC_COLLECT = "0x40d0efd1a53d60ecbf40971b9daf7dc90178c3aadc7aab1765632738fa8b8f01"

_TX_CACHE: dict[str, dict] = {}      # tx hash -> parsed closes (immutable once mined)
_RESULT_CACHE: dict = {"ts": 0.0, "data": None}
RESULT_TTL_SEC = 240


def _get(url: str, timeout: int = 15) -> dict:
    last_err = None
    for _ in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
                return json.loads(r.read().decode())
        except Exception as e:
            last_err = e
            time.sleep(1)
    raise last_err


def _rpc_call(to: str, data: str, sender: str | None = None) -> str | None:
    call = {"to": to, "data": data}
    if sender:
        call["from"] = sender
    payload = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "eth_call", "params": [call, "latest"]}).encode()
    for url in RPCS:
        try:
            req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json", **UA})
            with urllib.request.urlopen(req, timeout=10) as r:
                res = json.loads(r.read().decode())
                if res.get("result"):
                    return res["result"]
        except Exception:
            continue
    return None


def _signed(v: int, bits: int = 256) -> int:
    return v - (1 << bits) if v >= (1 << (bits - 1)) else v


def _words(hexdata: str) -> list[int]:
    h = hexdata[2:]
    return [int(h[i * 64:(i + 1) * 64], 16) for i in range(len(h) // 64)]


def _paginated(url: str, max_pages: int = 10) -> list[dict]:
    items, params = [], ""
    for _ in range(max_pages):
        d = _get(url + params)
        items.extend(d.get("items", []))
        nxt = d.get("next_page_params")
        if not nxt:
            break
        params = "?" + "&".join(f"{k}={v}" for k, v in nxt.items())
    return items


def _parse_tx_closes(tx_hash: str) -> dict:
    """Returns {token_id: {"principal": (v, w), "collected": (v, w)}} for NFTs closed in this tx."""
    if tx_hash in _TX_CACHE:
        return _TX_CACHE[tx_hash]
    logs = _paginated(f"https://base.blockscout.com/api/v2/transactions/{tx_hash}/logs", max_pages=4)
    closes: dict[int, dict] = {}
    for lg in logs:
        topics = lg.get("topics") or []
        addr = ((lg.get("address") or {}).get("hash") or "").lower()
        if not topics or addr != NPM.lower():
            continue
        if topics[0] == TOPIC_DEC:
            w = _words(lg["data"])
            closes.setdefault(int(topics[1], 16), {})["principal"] = (w[1] / 1e18, w[2] / 1e18)
        elif topics[0] == TOPIC_COLLECT:
            w = _words(lg["data"])
            closes.setdefault(int(topics[1], 16), {})["collected"] = (w[1] / 1e18, w[2] / 1e18)
    _TX_CACHE[tx_hash] = closes
    return closes


def _position(token_id: int) -> dict | None:
    raw = _rpc_call(NPM, "0x99fbab88" + hex(token_id)[2:].zfill(64))
    if not raw or len(raw) < 2 + 64 * 12:
        return None
    w = _words(raw)
    tl, tu = _signed(w[5]), _signed(w[6])
    return {"token_id": token_id, "tick_lower": tl, "tick_upper": tu, "liquidity": w[7],
            "range_min": 1.0001 ** tl, "range_max": 1.0001 ** tu}


def _pending_fees(token_id: int) -> tuple[float, float]:
    mx = hex((1 << 128) - 1)[2:].zfill(64)
    data = "0xfc6f7865" + hex(token_id)[2:].zfill(64) + WALLET[2:].lower().zfill(64) + mx + mx
    raw = _rpc_call(NPM, data, sender=WALLET)
    if not raw:
        return 0.0, 0.0
    return int(raw[2:66], 16) / 1e18, int(raw[66:130], 16) / 1e18


def _eth_usd_fallback() -> float:
    try:
        d = _get("https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd", timeout=8)
        return float(d["ethereum"]["usd"])
    except Exception:
        return 2690.0


def audit_virtual(eth_usd: float | None = None, force: bool = False) -> dict | None:
    """Full on-chain audit. Cached for RESULT_TTL_SEC. Returns None only if nothing could be read."""
    now_ts = time.time()
    if not force and _RESULT_CACHE["data"] and now_ts - _RESULT_CACHE["ts"] < RESULT_TTL_SEC:
        cached = dict(_RESULT_CACHE["data"])
        if eth_usd:
            _reprice(cached, eth_usd)
        return cached

    try:
        eth_usd = eth_usd or _eth_usd_fallback()

        # 1) on-chain pool price
        s0 = _rpc_call(POOL, "0x3850c7bd")
        sqrt_p = int(s0[2:66], 16) / 2 ** 96
        px = sqrt_p ** 2  # WETH per VIRTUAL

        # 2) every tx touching the wallet with a Uniswap position NFT
        items = _paginated(f"https://base.blockscout.com/api/v2/addresses/{WALLET}/token-transfers")
        nft_txs: dict[str, str] = {}
        token_ids: set[int] = set()
        dust_v = dust_w = 0.0
        tx_tokens: dict[str, list] = {}
        for it in items:
            sym = (it.get("token") or {}).get("symbol")
            h = it.get("transaction_hash")
            if not h:
                continue
            tx_tokens.setdefault(h, []).append(it)
            if sym == "UNI-V3-POS":
                tid = int((it.get("total") or {}).get("token_id") or 0)
                if tid > MIN_TOKEN_ID:
                    token_ids.add(tid)
                    nft_txs[h] = it.get("timestamp") or ""
        # dust returned by Krystal inside position txs
        for h in nft_txs:
            for it in tx_tokens.get(h, []):
                sym = (it.get("token") or {}).get("symbol")
                to = ((it.get("to") or {}).get("hash") or "").lower()
                val = int((it.get("total") or {}).get("value") or 0) / 1e18
                if to == WALLET.lower() and sym == "VIRTUAL":
                    dust_v += val
                elif to == WALLET.lower() and sym == "WETH":
                    dust_w += val

        # 3) closed cycles
        cycles = []
        for h, ts in sorted(nft_txs.items(), key=lambda x: x[1]):
            for tid, c in _parse_tx_closes(h).items():
                if "principal" in c and "collected" in c:
                    fv = max(c["collected"][0] - c["principal"][0], 0.0)
                    fw = max(c["collected"][1] - c["principal"][1], 0.0)
                    cycles.append({"token_id": tid, "closed_at": ts, "tx": h,
                                   "fees_virtual": fv, "fees_weth": fw})

        # 4) active NFT = highest token id with liquidity
        active = None
        for tid in sorted(token_ids, reverse=True):
            p = _position(tid)
            if p and p["liquidity"] > 0:
                active = p
                break
        if not active:
            return _RESULT_CACHE["data"]

        sa, sb = math.sqrt(active["range_min"]), math.sqrt(active["range_max"])
        L = active["liquidity"]
        if sqrt_p <= sa:
            a0, a1 = L * (sb - sa) / (sa * sb), 0.0
        elif sqrt_p >= sb:
            a0, a1 = 0.0, L * (sb - sa)
        else:
            a0, a1 = L * (sb - sqrt_p) / (sqrt_p * sb), L * (sqrt_p - sa)
        pend_v, pend_w = _pending_fees(active["token_id"])

        last_rebalance = max((c["closed_at"] for c in cycles), default=START_ISO)
        data = {
            "px_weth": px,
            "active_nft": active["token_id"],
            "range_min": active["range_min"],
            "range_max": active["range_max"],
            "liquidity": L,
            "in_range": active["range_min"] <= px <= active["range_max"],
            "pool_virtual": a0 / 1e18,
            "pool_weth": a1 / 1e18,
            "pending_virtual": pend_v,
            "pending_weth": pend_w,
            "dust_virtual": dust_v,
            "dust_weth": dust_w,
            "cycles": cycles,
            "last_rebalance_iso": last_rebalance,
            "audited_at": datetime.now(timezone.utc).isoformat(),
        }
        _reprice(data, eth_usd)
        _RESULT_CACHE.update({"ts": now_ts, "data": dict(data)})
        return data
    except Exception as e:
        print(f"[-] VIRTUAL audit error: {e}")
        cached = _RESULT_CACHE["data"]
        if cached and eth_usd:
            cached = dict(cached)
            _reprice(cached, eth_usd)
        return cached


def _reprice(d: dict, eth_usd: float) -> None:
    """(Re)computes every USD field from token amounts at the given ETH price."""
    px = d["px_weth"]
    v_usd = px * eth_usd
    d["eth_usd"] = eth_usd
    d["virtual_usd"] = v_usd
    d["pool_usd"] = d["pool_virtual"] * v_usd + d["pool_weth"] * eth_usd
    d["pending_usd"] = d["pending_virtual"] * v_usd + d["pending_weth"] * eth_usd
    d["dust_usd"] = d["dust_virtual"] * v_usd + d["dust_weth"] * eth_usd
    for c in d["cycles"]:
        c["fees_usd"] = c["fees_virtual"] * v_usd + c["fees_weth"] * eth_usd
    d["collected_fees_usd"] = sum(c["fees_usd"] for c in d["cycles"])
    d["total_fees_usd"] = d["collected_fees_usd"] + d["pending_usd"]
    d["last_cycle"] = d["cycles"][-1] if d["cycles"] else None

    # Equity: fees already compounded inside pool/dust -> do NOT add collected fees again
    d["initial_usd"] = INITIAL_USD
    d["equity_usd"] = d["pool_usd"] + d["pending_usd"] + d["dust_usd"]
    d["equity_weth"] = d["equity_usd"] / eth_usd
    d["net_usd"] = d["equity_usd"] - INITIAL_USD
    d["net_pct"] = d["net_usd"] / INITIAL_USD * 100.0
    d["net_weth_pct"] = (d["equity_weth"] - INITIAL_WETH) / INITIAL_WETH * 100.0
    d["hodl_usd"] = INITIAL_HODL_VIRTUAL * v_usd + INITIAL_HODL_WETH * eth_usd
    d["vs_hodl_usd"] = d["equity_usd"] - d["hodl_usd"]
    # price effect (IL realised by rebalances + market move) = net result minus fees earned
    d["price_effect_usd"] = d["net_usd"] - d["total_fees_usd"]

    now = datetime.now(timezone.utc)
    start = datetime.fromisoformat(START_ISO)
    hours = max((now - start).total_seconds() / 3600.0, 1e-6)
    d["hours_active"] = hours
    d["fees_per_day_avg"] = d["total_fees_usd"] / hours * 24.0
    try:
        last = datetime.fromisoformat(d["last_rebalance_iso"].replace("Z", "+00:00"))
        h_cur = max((now - last).total_seconds() / 3600.0, 1e-6)
    except Exception:
        h_cur = hours
    d["hours_current_cycle"] = h_cur
    d["fees_per_day_current"] = d["pending_usd"] / h_cur * 24.0
    d["apr_avg_pct"] = d["fees_per_day_avg"] * 365.0 / INITIAL_USD * 100.0


if __name__ == "__main__":
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    a = audit_virtual(force=True)
    if not a:
        print("audit failed")
        sys.exit(1)
    print(f"VIRTUAL {a['px_weth']:.8f} WETH (${a['virtual_usd']:.4f}) | ETH ${a['eth_usd']:.2f}")
    print(f"NFT ativo #{a['active_nft']} faixa {a['range_min']:.8f} <-> {a['range_max']:.8f} in_range={a['in_range']}")
    for c in a["cycles"]:
        print(f"  ciclo NFT #{c['token_id']} fechado {c['closed_at'][:16]}: {c['fees_virtual']:.4f} V + {c['fees_weth']:.6f} W = ${c['fees_usd']:.2f}")
    print(f"Pool: {a['pool_virtual']:.2f} V + {a['pool_weth']:.6f} W = ${a['pool_usd']:.2f}")
    print(f"Taxas pendentes: ${a['pending_usd']:.2f} | coletadas: ${a['collected_fees_usd']:.2f} | total: ${a['total_fees_usd']:.2f}")
    print(f"Trocos carteira: {a['dust_virtual']:.4f} V + {a['dust_weth']:.6f} W = ${a['dust_usd']:.2f}")
    print(f"Patrimônio: ${a['equity_usd']:.2f} | vs aporte ${INITIAL_USD}: {a['net_usd']:+.2f} ({a['net_pct']:+.2f}%) | em WETH {a['net_weth_pct']:+.2f}%")
    print(f"HODL: ${a['hodl_usd']:.2f} | vs HODL {a['vs_hodl_usd']:+.2f} | efeito preço/IL {a['price_effect_usd']:+.2f}")
    print(f"Taxas/dia média {a['fees_per_day_avg']:.2f} | ciclo atual {a['fees_per_day_current']:.2f} | APR médio {a['apr_avg_pct']:.0f}%")
