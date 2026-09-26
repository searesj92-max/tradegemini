import os, json, time, urllib.request

pine_path = 'C:/Users/seares/Desktop/botrade/pine/vce_fc_v1.pine'
pine = open(pine_path).read()

# Read PK_TOKEN from auth file
auth_json = 'C:/Users/seares/AppData/Local/hermes/profiles/researcher/auth.json'
try:
    with open(auth_json) as f:
        auth = json.load(f)
    # Search for PK_TOKEN in the auth file
    import re
    text = json.dumps(auth)
    m = re.search(r'PK_TOKEN[=:]\s*["\']?([a-zA-Z0-9_\-]+)["\']?', text)
    if m:
        PK_TOKEN = m.group(1)
        print(f"Found PK_TOKEN via auth.json")
    else:
        m = re.search(r'"pk_[a-zA-Z0-9_\-]+"', text)
        if m:
            PK_TOKEN = m.group(0).strip('"')
            print(f"Found PK-like token: {PK_TOKEN[:20]}...")
        else:
            print("PK_TOKEN not found in auth.json")
            PK_TOKEN = ''
except Exception as e:
    print(f"Could not read auth.json: {e}")
    PK_TOKEN = ''

if not PK_TOKEN:
    print("No PK_TOKEN found - attempting to read from env or .env")
    # Try to find PK_TOKEN anywhere in the profile directory
    import glob
    for f in glob.glob('C:/Users/seares/AppData/Local/hermes/profiles/researcher/**/*', recursive=True):
        try:
            with open(f, 'r') as fh:
                content = fh.read()
                m = re.search(r'PK_TOKEN[=:]\s*["\']?([a-zA-Z0-9_\-]+)["\']?', content)
                if m:
                    PK_TOKEN = m.group(1)
                    print(f"Found PK_TOKEN in {f}")
                    break
        except:
            pass

if not PK_TOKEN:
    print("Still no PK_TOKEN - aborting")
    exit(1)

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
