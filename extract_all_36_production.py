"""
FINAL COMPREHENSIVE PARSER
Extract Potensi, Realisasi, Gap for ALL 36 AME II blocks
"""
import pandas as pd
import json

print("🚀 EXTRACTING PRODUCTION DATA FOR ALL 36 AME II BLOCKS")
print("="*70)

# Load files
df = pd.read_excel('poac_sim/data/input/data_gabungan.xlsx')
print(f"✅ Loaded data_gabungan.xlsx: {df.shape}")

# Load our 36 blocks
with open('data/output/all_blocks_data.json', 'r') as f:
    blocks_data = json.load(f)

our_blocks = sorted(blocks_data.keys())
print(f"✅ Target: {len(our_blocks)} AME II blocks")

# Find column indices for Potensi, Realisasi, Gap
# These should be in the headers
print("\n🔎 Searching for column headers...")

# Scan first 10 rows for headers
for i in range(10):
    row_vals = [str(v).lower() for v in df.iloc[i].tolist()]
    for j, val in enumerate(row_vals):
        if 'potensi' in val or 'realisasi' in val or 'gap' in val or 'luas' in val or 'produksi' in val:
            print(f"Row {i}, Col {j}: {df.iloc[i, j]}")

# Based on manual inspection, extract data
# For now, save raw data for all blocks so user can see structure
found_data = {}

for block_code in our_blocks:
    for i in range(len(df)):
        for j in range(15):  # Check first 15 columns
            if str(df.iloc[i, j]).strip() == block_code:
                found_data[block_code] = {
                    'row': i,
                    'values': [str(v) if pd.notna(v) else 'nan' for v in df.iloc[i, :100].tolist()]
                }
                print(f"Found: {block_code} at row {i}")
                break
        if block_code in found_data:
            break

print(f"\n✅ Found {len(found_data)}/{len(our_blocks)} blocks")

# Save for inspection
with open('data/output/all_36_blocks_raw_rows.json', 'w') as f:
    json.dump(found_data, f, indent=2)

print(f"✅ Saved to: data/output/all_36_blocks_raw_rows.json")
print("\nNext: Inspect this file to identify column indices for Potensi/Realisasi/Gap")
