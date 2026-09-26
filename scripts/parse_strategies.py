import json, re, sys

with open(sys.argv[1]) as f:
    txt = f.read()

m = re.search(r'^\{"result": (\[.*\]),?\}?$', txt, re.DOTALL)
if not m:
    print("ERRO:Não encontrou JSON array", file=sys.stderr)
    sys.exit(1)

arr = json.loads(m.group(1))
print(f"Total:{len(arr)}")
print("-"*120)
print(f"{'MODE':8} | {'STATUS':8} | {'ID':24} | {'NAME':55} | {'SYM':10} | {'TF':4} | {'TYPE':6} | {'VIS':9} | {'FORK':24}")
print("-"*120)
for s in sorted(arr, key=lambda x: (0 if x['mode']=='deployed' else 1, 0 if x['status']=='active' else 1, x['createdAt'] or '')):
    name = s['name'][:55]
    print(f"{s['mode']:8} | {s['status']:8} | {s['id']:24} | {name:55} | {s['symbol']:10} | {str(s.get('timeframe','?')):>4} | {s.get('strategyType','?'):6} | {s.get('visibility','?'):9} | {str(s.get('forkedFromStrategyId','?')):24}")
