"""
More thorough search for AME II (D, E, F) blocks in data_gabungan.xlsx
"""
import pandas as pd
import re

print("🔍 SEARCHING FOR AME II BLOCKS (D, E, F prefix)")
print("="*70)

df = pd.read_excel('poac_sim/data/input/data_gabungan.xlsx')
print(f"File size: {df.shape}")

# Search for D, E, F blocks in entire dataframe
ame2_pattern = re.compile(r'^[DEF]\d{3}[A-Z]$')
found_blocks = []

print("\n🔎 Scanning entire file for D/E/F blocks...")

for i in range(len(df)):
    for j in range(min(30, len(df.columns))):  # Check first 30 columns
        cell = str(df.iloc[i, j]).strip()
        if ame2_pattern.match(cell):
            found_blocks.append({
                'block': cell,
                'row': i,
                'col': j,
                'row_preview': df.iloc[i,  :min(20, len(df.columns))].tolist()
            })
            print(f"✅ Found {cell} at row {i}, col {j}")

print(f"\n✅ Total AME II blocks found: {len(found_blocks)}")

if len(found_blocks) > 0:
    print(f"\nBlocks found: {sorted(set([b['block'] for b in found_blocks]))}")
    
    # Show structure around first found block
    if found_blocks:
        first = found_blocks[0]
        print(f"\n📋 Example structure for {first['block']}:")
        print(f"Row {first['row']}: {first['row_preview']}")
        
        # Show few rows before (likely headers)
        for offset in range(-5, 0):
            row_idx = first['row'] + offset
            if row_idx >= 0:
                print(f"Row {row_idx} (header?): {df.iloc[row_idx, :20].tolist()}")
                
else:
    print("\n❌ No AME II blocks found!")
    print("\nShowing blocks that WERE found:")
    print("\nFirst 100 unique values in column 0:")
    unique_vals = df.iloc[:, 0].dropna().unique()[:100]
    for val in unique_vals:
        print(f"  - {val}")
