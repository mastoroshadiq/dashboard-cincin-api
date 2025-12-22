import pandas as pd
from pathlib import Path

# Load productivity data
df_raw = pd.read_excel(Path('data/input/data_gabungan.xlsx'), header=None)
df = df_raw.iloc[8:].copy().reset_index(drop=True)
df.columns = [f'col_{i}' for i in range(df.shape[1])]

df['Blok_Prod'] = df['col_0']
df['Luas_Ha'] = pd.to_numeric(df['col_11'], errors='coerce')
df['Produksi_Ton'] = pd.to_numeric(df['col_170'], errors='coerce')
df['Yield_TonHa'] = df['Produksi_Ton'] / df['Luas_Ha']
prod_df = df[['Blok_Prod', 'Luas_Ha', 'Produksi_Ton', 'Yield_TonHa']].dropna()

print("=== PRODUCTIVITY DATA BLOCKS ===")
print(f"Total: {len(prod_df)}")
print("\nSample blok names:")
print(prod_df['Blok_Prod'].head(20).tolist())

# Test matching with Ganoderma blocks
gano_blocks = ['B16', 'B15', 'C18A', 'A12', 'B12']

print("\n=== MATCHING TEST ===")
for gano_blok in gano_blocks:
    # Current logic (first 3 chars)
    match1 = prod_df[prod_df['Blok_Prod'].str.contains(gano_blok[:3], na=False, regex=False)]
    
    # Try exact match
    match2 = prod_df[prod_df['Blok_Prod'] == gano_blok]
    
    # Try partial match (blok code in productivity name)
    match3 = prod_df[prod_df['Blok_Prod'].str.contains(gano_blok, na=False, regex=False)]
    
    print(f"\nGanoderma Blok: {gano_blok}")
    print(f"  First 3 chars ('{gano_blok[:3]}'): {len(match1)} matches")
    if len(match1) > 0:
        print(f"    Matched: {match1['Blok_Prod'].tolist()[:5]}")
    print(f"  Exact match: {len(match2)} matches")
    print(f"  Contains '{gano_blok}': {len(match3)} matches")
    if len(match3) > 0:
        print(f"    Matched: {match3['Blok_Prod'].tolist()[:5]}")

# Check if there's any overlap
print("\n=== CHECKING NAMING PATTERN ===")
print("Ganoderma block format examples: B16, B15, C18A, A12")
print("Productivity block format examples:")
for blok in prod_df['Blok_Prod'].head(30):
    print(f"  {blok}")
