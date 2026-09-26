import os, json, time, urllib.request

PK_TOKEN = os.environ.get('PK_TOKEN', '')

pine_path = 'C:/Users/seares/Desktop/botrade/pine/vce_fc_v1.pine'
pine = open(pine_path).read()

symbols = [
    ("ETHUSDT", "30"), ("ETHUSDT", "60"), ("ETHUSDT", "120"), ("ETHUSDT", "240"),
    ("SOLUSDT", "15"), ("SOLUSDT", "30"), ("SOLUSDT", "60"),
    ("XRPUSDT", "15"), ("XRPUSDT", "30")
]

url = f"https://mcp.trader.dev/mcp?key={PK_TOKEN}"
results = []

for sym, tf in symbols:
    print(f"=== {sym} {tf}m ===", flush=True)
    payload = json.dumps({
        "jsonrpc": "2.0",
        "method": "quick_backtest",
        "params": {"pineSource": pine, "symbol": sym, "timeframe": tf},
        "id": f"{sym}_{tf}"
    }).encode()
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())
            result = data.get("result", {}).get("result", {})
            trades = result.get("totalTrades", 0)
            net = result.get("netProfitPct", 0)
            pf = result.get("profitFactor", 0)
            dd = result.get("maxDrawdownPct", 0)
            print(f"  -> trades={trades}, net={net}%, PF={pf}, DD={dd}%", flush=True)
            results.append({"symbol": sym, "tf": tf, "trades": trades, "net": net, "pf": pf, "dd": dd})
    except Exception as e:
        print(f"  -> ERROR: {e}", flush=True)
        results.append({"symbol": sym, "tf": tf, "error": str(e)})
    time.sleep(2)

print()
print("=== SUMMARY ===")
for r in results:
    if "error" in r:
        print(f"{r['symbol']} {r['tf']}m: ERROR")
    else:
        print(f"{r['symbol']} {r['tf']}m: trades={r['trades']}, net={r['net']}%, PF={r['pf']}, DD={r['dd']}%")

out = "C:/Users/seares/Desktop/botrade/data/vce_fc_v1_results.json"
with open(out, "w") as f:
    json.dump(results, f, indent=2)
print(f"\nSaved to {out}")
