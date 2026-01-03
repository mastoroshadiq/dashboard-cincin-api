"""
Parse data_gabungan.xlsx to extract REAL production data for all 36 AME II blocks
"""
import pandas as pd
import json
import re

print("🔍 PARSING data_gabungan.xlsx FOR ALL 36 BLOCKS")
print("="*70)

# Load the file
df = pd.read_excel('poac_sim/data/input/data_gabungan.xlsx')
print(f"✅ Loaded file: {df.shape}")

# Find where data starts - look for block codes
print("\n🔎 Searching for block codes...")

block_pattern = re.compile(r'^[DEF]\d{3}A$')
data_start_row = None

for i in range(50):
    for j in range(20):
        cell_val = str(df.iloc[i, j])
        if block_pattern.match(cell_val):
            print(f"✅ Found block '{cell_val}' at row {i}, col {j}")
            data_start_row = i
            block_col = j
            break
    if data_start_row:
        break

if not data_start_row:
    print("❌ Could not find block codes in expected format")
    print("\nShowing first 30 rows to inspect:")
    for i in range(30):
        print(f"Row {i}: {df.iloc[i, 0:5].tolist()}")
else:
    print(f"\n✅ Data starts at row {data_start_row}, block codes in column {block_col}")
    
    # Find column headers
    print("\n🔎 Finding column headers...")
    header_row = data_start_row - 1
    
    # Look for columns with "Potensi", "Realisasi", "Gap", "Produksi"
    headers = df.iloc[header_row].tolist()
    print(f"\nHeaders around data columns (cols {max(0, block_col-2)} to {min(len(headers), block_col+20)}):")
    for idx, h in enumerate(headers[max(0, block_col-2):min(len(headers), block_col+20)]):
        col_idx = max(0, block_col-2) + idx
        print(f"  Col {col_idx}: {h}")
    
    # Extract blocks data
    print("\n📊 Extracting block production data...")
    
    blocks_production = {}
    
    # Scan through rows starting from data_start_row
    for i in range(data_start_row, min(data_start_row + 100, len(df))):
        block_code = str(df.iloc[i, block_col]).strip()
        
        if block_pattern.match(block_code):
            print(f"\nProcessing: {block_code}")
            row_data = df.iloc[i].tolist()
            
            # Show all values in this row
            print(f"  Row values (first 30): {row_data[:30]}")
            
            blocks_production[block_code] = {
                'row_index': i,
                'raw_values': row_data[:50]  # Store first 50 values for inspection
            }
    
    print(f"\n✅ Found {len(blocks_production)} blocks")
    print(f"Blocks: {sorted(blocks_production.keys())}")
    
    # Save raw extraction for manual inspection
    with open('data/output/blocks_production_raw.json', 'w') as f:
        # Convert to serializable format
        output = {}
        for block, data in blocks_production.items():
            output[block] = {
                'row_index': data['row_index'],
                'raw_values': [str(v) for v in data['raw_values']]
            }
        json.dump(output, f, indent=2)
    
    print(f"\n✅ Saved raw data to: data/output/blocks_production_raw.json")
    print("\nPlease inspect this file to identify which columns contain:")
    print("  - Potensi (target production)")
    print("  - Realisasi (actual production)")
    print("  - Luas (hectares)")
    print("  - Produksi (total production in tons)")
