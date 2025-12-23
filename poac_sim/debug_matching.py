import sys
sys.path.insert(0, '.')
from dashboard_v7_fixed import load_productivity_data, convert_prod_to_gano_pattern
import pandas as pd

# Load productivity data
prod_df = load_productivity_data()

# Filter productive age
productive_df = prod_df[(prod_df['Umur_Tahun'] >= 3) & (prod_df['Umur_Tahun'] <= 25)]
print(f'Productive blocks (3-25y): {len(productive_df)}')

# Get lowest yield
low_yield = productive_df.nsmallest(20, 'Yield_TonHa')

print('\n=== Top 20 Lowest Yield Blocks ===')
print('Checking Ganoderma pattern matching...\n')

for idx, (_, row) in enumerate(low_yield.iterrows(), 1):
    gano_pattern = convert_prod_to_gano_pattern(row['Blok_Prod'])
    print(f'{idx:2d}. {row["Blok_Prod"]:10s} -> Gano pattern: "{gano_pattern:6s}" | Yield: {row["Yield_TonHa"]:.2f} | Age: {row["Umur_Tahun"]:.0f}y')

print('\n=== Checking if Ganoderma blocks exist ===')
# Sample check: Load actual Ganoderma data to see block names
from src.ingestion import load_and_clean_data
from pathlib import Path

df_gano = load_and_clean_data(Path('data/input/tabelNDREnew.csv'))
print(f'Total Ganoderma blocks: {df_gano["Blok"].nunique()}')
print(f'\nSample Ganoderma block names:')
print(df_gano['Blok'].unique()[:20])

print('\n=== Testing Pattern Matching ===')
# Test if any prod block matches gano blocks
test_prod = low_yield.iloc[0]['Blok_Prod']
test_pattern = convert_prod_to_gano_pattern(test_prod)
matches = df_gano[df_gano['Blok'].str.contains(test_pattern, na=False, regex=False)]
print(f'Test: {test_prod} -> pattern "{test_pattern}" -> {len(matches)} matches')
if not matches.empty:
    print(f'Matched blocks: {matches["Blok"].unique()[:5]}')
else:
    print('❌ NO MATCHES - This is the problem!')
    print('\nDEBUG: Checking if pattern is in Gano blocks at all...')
    for gano_blok in df_gano['Blok'].unique()[:30]:
        if test_pattern in gano_blok:
            print(f'  Found in: {gano_blok}')
