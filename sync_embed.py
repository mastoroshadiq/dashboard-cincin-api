import json
import os

json_path = 'data/output/all_blocks_data.json'
js_path = 'data/output/blocks_data_embed.js'

if os.path.exists(json_path):
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    with open(js_path, 'w') as f:
        f.write("const BLOCKS_DATA = " + json.dumps(data, indent=2) + ";")
    
    print(f"✅ Successfully updated {js_path} from {json_path}")
else:
    print(f"❌ Error: {json_path} not found.")
