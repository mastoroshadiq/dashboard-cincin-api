import shutil

# Backup original
shutil.copy('dashboard_v7_fixed.py', 'dashboard_v7_fixed.py.backup')

# Read file
with open('dashboard_v7_fixed.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find and replace lines 437-439
# Line 437 (index 436): productive_df = prod_df[(prod_df['Umur_Tahun'] >= 3) & (prod_df['Umur_Tahun'] <= 25)]
# Line 438 (index 437): if not productive_df.empty:
# Line 439 (index 438): low_yield = productive_df.nsmallest(20, 'Yield_TonHa')

new_code = '''            productive_df = prod_df[(prod_df['Umur_Tahun'] >= 3) & (prod_df['Umur_Tahun'] <= 25)]
            
            # CRITICAL FIX: Filter to only blocks in current division's Ganoderma data
            div_blocks_idx = []
            for idx, row in productive_df.iterrows():
                gano_pattern = convert_prod_to_gano_pattern(row['Blok_Prod'])
                if not block_stats[block_stats['Blok'].str.contains(gano_pattern, na=False, regex=False)].empty:
                    div_blocks_idx.append(idx)
            
            if div_blocks_idx:
                productive_df = productive_df.loc[div_blocks_idx]
            else:
                productive_df = pd.DataFrame()  # No blocks in this division
            
            if not productive_df.empty:
                low_yield = productive_df.nsmallest(20, 'Yield_TonHa')  # Get top 20 candidates
'''

# Replace lines 436-438 (0-indexed)
new_lines = lines[:436] + [new_code] + lines[439:]

# Write back
with open('dashboard_v7_fixed.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("✅ File updated successfully!")
print("Backup saved as: dashboard_v7_fixed.py.backup")
print("\nChanges made:")
print("- Added division filter to POV 2 (lines 437-450)")
print("- Now only shows blocks that exist in current division's Ganoderma data")
