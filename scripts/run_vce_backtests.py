"""Run VCE-FC v1 backtests across 5 symbols × 5 TFs using MCP quick_backtest."""
import json
import subprocess
import sys
import time
from pathlib import Path

# MCP endpoint from .env
MCP_URL = "https://mcp.trader.dev/mcp?key="
# We'll read key from env
import os
PK_TOKEN = os.environ.get("PK_TOKEN", "")

# Load pine source
pine_file = Path("/c/Users/seares/Desktop/botrade/pine/vce_fc_v1.pine")
if not pine_file.exists():
    print("Pine file not found, creating...")
    pine_source = """//@version=6
strategy("QM-VCE-FC-v1", overlay=true, pyramiding=1, process_orders_on_close=true,
  commission_type=strategy.commission.percent, commission_value=0.05,
  default_qty_type=strategy.percent_of_equity, default_qty_value=100,
  margin_long=100, margin_short=100, initial_capital=10000)

// === INPUTS ===
compLen      = input.int(20, "Compression lookback (bars)")
atrLen       = input.int(14, "ATR length")
atrCmpLen    = input.int(50, "ATR comparison length")
expMult      = input.float(1.5, "Expansion range multiplier (vs avg compression range)")
maxBars      = input.int(20, "Max bars in trade (time exit)")
rtMult       = input.float(1.5, "Risk-to-reward ratio (TP/SL)")
trendSmaLen  = input.int(200, "Trend filter SMA length")
cooldownBars = input.int(5, "Cooldown after exit (bars)")

// === INDICATORS ===
atr         = ta.atr(atrLen)
sma200      = ta.sma(close, trendSmaLen)
atrLowest   = ta.lowest(atr, compLen)
atrAvgLong  = ta.sma(atr, atrCmpLen)

// === COMPRESSION DETECTION ===
compression = atr <= atrLowest and atr < atrAvgLong * 0.8

// === COMPRESSION ZONE ===
compHigh       = ta.highest(high, compLen)
compLow        = ta.lowest(low, compLen)
avgCompRange  = ta.sma(ta.range, compLen)

// === BREAKOUT + EXPANSION FILTER ===
breakoutLong   = close > compHigh
breakoutShort  = close < compLow
expansionLong  = breakoutLong and (high - low) > avgCompRange * expMult
expansionShort = breakoutShort and (high - low) > avgCompRange * expMult

// === TREND FILTER ===
trendLongOk  = close > sma200
trendShortOk = close < sma200

// === COOLDOWN ===
inPosition    = strategy.position_size != 0
barsSincePos  = ta.barssince(inPosition)
justClosed    = not inPosition and barsSincePos < cooldownBars

// === ENTRY ===
longSignal  = compression and expansionLong  and trendLongOk  and not justClosed
shortSignal = compression and expansionShort and trendShortOk and not justClosed

if longSignal
    strategy.entry("L", strategy.long)
    longRisk  = close - compHigh
    longTP    = close + longRisk * rtMult
    strategy.exit("LT", from_entry="L", limit=longTP)

if shortSignal
    strategy.entry("S", strategy.short)
    shortRisk = compLow - close
    shortTP   = close - shortRisk * rtMult
    strategy.exit("ST", from_entry="S", limit=shortTP)

// === STRUCTURAL EXIT (breakout failure) ===
if strategy.position_size > 0 and close < compHigh
    strategy.close("L")

if strategy.position_size < 0 and close > compLow
    strategy.close("S")

// === TIME EXIT ===
var int barsInTrade = 0
if strategy.position_size != 0
    barsInTrade += 1
else
    barsInTrade := 0

if strategy.position_size != 0 and barsInTrade > maxBars
    strategy.close_all()"""
else:
    pine_source = pine_file.read_text()

symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT"]
timeframes = ["15", "30", "60", "120", "240"]

results = []

for sym in symbols:
    for tf in timeframes:
        print(f"\n=== {sym} {tf}m ===")
        print(f"Running backtest {sym} {tf}m...")
        
        # Call MCP quick_backtest via curl
        payload = {
            "jsonrpc": "2.0",
            "method": "quick_backtest",
            "params": {
                "pineSource": pine_source,
                "symbol": sym,
                "timeframe": tf
            },
            "id": f"{sym}_{tf}"
        }
        
        req_data = json.dumps(payload).encode()
        url = MCP_URL + PK_TOKEN
        
        req = urllib.request.Request(url, data=req_data, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                resp_data = json.loads(resp.read())
                result = resp_data.get("result", {})
                print(f"Result: {json.dumps(result, indent=2)[:500]}")
                results.append({
                    "symbol": sym,
                    "timeframe": tf,
                    "result": result
                })
        except Exception as e:
            print(f"Error: {e}")
            results.append({
                "symbol": sym,
                "timeframe": tf,
                "error": str(e)
            })
        
        # Small delay to avoid rate limiting
        time.sleep(1)

print("\n\n=== SUMMARY ===")
for r in results:
    sym = r.get("symbol")
    tf = r.get("timeframe")
    result = r.get("result", {})
    trades = result.get("totalTrades", 0)
    net = result.get("netProfitPct", 0)
    pf = result.get("profitFactor", 0)
    dd = result.get("maxDrawdownPct", 0)
    wr = result.get("winRatePct", 0)
    print(f"{sym} {tf}m: trades={trades}, net={net}%, PF={pf}, DD={dd}%, WR={wr}%")

# Save results
output_path = Path("/c/Users/seares/Desktop/botrade/data/vce_fc_v1_results.json")
output_path.parent.mkdir(parents=True, exist_ok=True)
with open(output_path, "w") as f:
    json.dump(results, f, indent=2)
print(f"\nResults saved to {output_path}")
