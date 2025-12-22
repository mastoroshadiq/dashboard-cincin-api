import pandas as pd
from pathlib import Path

# Load productivity data
df_raw = pd.read_excel(Path('data/input/data_gabungan.xlsx'), header=None)
df = df_raw.iloc[8:].copy().reset_index(drop=True)
df.columns = [f'col_{i}' for i in range(df.shape[1])]

df['Blok_Prod'] = df['col_0']
df['Divisi'] = df['col_3']
df['Luas_Ha'] = pd.to_numeric(df['col_11'], errors='coerce')
df['Produksi_Ton'] = pd.to_numeric(df['col_170'], errors='coerce')
df['Yield_TonHa'] = df['Produksi_Ton'] / df['Luas_Ha']
prod_df = df[['Blok_Prod', 'Divisi', 'Luas_Ha', 'Produksi_Ton', 'Yield_TonHa']].dropna()

print("=== PRODUCTIVITY DATA BY DIVISI ===")
print(prod_df.groupby('Divisi')['Blok_Prod'].count())

print("\n=== AME BLOCKS ===")
ame_blocks = prod_df[prod_df['Divisi'] == 'AME']
print(f"Total AME blocks: {len(ame_blocks)}")
print("\nFirst 30 AME blocks:")
for i, blok in enumerate(ame_blocks['Blok_Prod'].head(30)):
    print(f"  {blok}")

print("\n=== CHECKING IF THERE'S A PATTERN ===")
# Maybe the number part matches?
# e.g., B16 → B016A or similar?
for gano in ['B16', 'B15', 'A12', 'C18A']:
    # Extract prefix and number
    import re
    match = re.match(r'([A-Z]+)(\d+)([A-Z]*)', gano)
    if match:
        prefix, num, suffix = match.groups()
        # Try with zero-padded number
        pattern1 = f"{prefix}{num.zfill(3)}"
        pattern2 = f"{prefix}{num.zfill(2)}"
        
        matches1 = ame_blocks[ame_blocks['Blok_Prod'].str.contains(pattern1, na=False, regex=False)]
        matches2 = ame_blocks[ame_blocks['Blok_Prod'].str.contains(pattern2, na=False, regex=False)]
        
        print(f"\nGanoderma: {gano}")
        print(f"  Pattern '{pattern1}': {len(matches1)} matches - {matches1['Blok_Prod'].tolist()[:3]}")
        print(f"  Pattern '{pattern2}': {len(matches2)} matches - {matches2['Blok_Prod'].tolist()[:3]}")
