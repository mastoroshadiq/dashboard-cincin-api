import pandas as pd

# Check data_gabungan.xlsx for Ganoderma attack columns
df = pd.read_excel('data/input/data_gabungan.xlsx', header=None)

print('=== Checking Headers for Ganoderma Columns ===')
headers = df.iloc[6]

# Search for Ganoderma-related columns
gano_cols = []
for i, h in enumerate(headers):
    if pd.notna(h):
        h_lower = str(h).lower()
        if any(word in h_lower for word in ['gano', 'attack', 'stadium', 'serangan', 'infeksi', 'stad']):
            gano_cols.append((i, h))

if gano_cols:
    print(f'\n✅ Found {len(gano_cols)} Ganoderma-related columns:')
    for col_idx, col_name in gano_cols:
        print(f'  col_{col_idx}: {col_name}')
else:
    print('\n❌ No Ganoderma columns found with keywords')

# Sample data
if gano_cols:
    df_data = df.iloc[8:11].copy()
    df_data.columns = [f'col_{i}' for i in range(df_data.shape[1])]
    
    print('\n=== Sample Data (first 3 blocks) ===')
    cols_to_show = ['col_0'] + [f'col_{idx}' for idx, _ in gano_cols[:5]]
    print(df_data[cols_to_show].to_string())

print('\n=== CRITICAL ANALYSIS ===')
print('For Z-Score + Cincin Api, we need:')
print('1. TREE-LEVEL data (not block-level aggregates)')
print('2. NDVI values per tree')
print('3. Spatial coordinates (Baris/Pokok)')
print('')
print('If data_gabungan only has:')
print('- % Attack per block → AGGREGATE data')
print('- Stadium 1-4 counts → AGGREGATE data')
print('')
print('Then:')
print('❌ Z-Score: NO (needs individual tree NDVI)')
print('❌ Cincin Api: NO (needs spatial tree arrangement)')
print('✅ POV 1 & 2: YES (can use aggregate % attack)')
