import json
from pathlib import Path

data_path = Path("C:/Users/seares/Desktop/botrade/dashboard/data.json")
js_path = Path("C:/Users/seares/Desktop/botrade/dashboard/data.js")

with open(data_path) as f:
    data = json.load(f)

# Generate JS content
js_content = f"window.MISSION_DATA = {json.dumps(data, separators=(',', ':'))};\n"

with open(js_path, "w") as f:
    f.write(js_content)

print(f"Regenerated data.js: {len(js_content)} bytes")
print(f"Strategies: {len(data['strategies'])}")
print(f"Stats: total={data['stats']['total']}, detail_rows={data['stats']['detail_rows']}")
