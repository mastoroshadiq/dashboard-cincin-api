import pandas as pd
from pathlib import Path
import sys
sys.path.insert(0, 'src')

from dashboard_v7_fixed import load_productivity_data, convert_prod_to_gano_pattern
from src.ingestion import load_and_clean_data

# Load data
df_ii = load_and_clean_data(Path('data/input/tabelNDREnew.csv'))
prod_df = load_productivity_data()

print(f'Total prod blocks: {len(prod_df)}')
productive = prod_df[prod_df['Umur_Tahun'] > 5]
print(f'Productive (>5y): {len(productive)}')

low_yield = productive.nsmallest(20, 'Yield_TonHa')
print(f'\nLow yield blocks (top 20):')
print(low_yield[['Blok_Prod', 'Yield_TonHa', 'Umur_Tahun']].head(10))

# Check attack % for these blocks
print('\n=== Checking Ganoderma attack % ===')
from dashboard_v7_fixed import analyze_divisi

results_ii, maps_ii = analyze_divisi(df_ii, 'AME II', prod_df, Path('data/output/temp'))
block_stats = results_ii['standar']['block_stats']

print(f'\nBlock stats sample:')
print(block_stats[['Blok', 'Attack_Pct']].head(10))

matched = 0
for _, r in low_yield.head(10).iterrows():
    gano_pattern = convert_prod_to_gano_pattern(r['Blok_Prod'])
    blok_match = block_stats[block_stats['Blok'].str.contains(gano_pattern, na=False, regex=False)]
    attack = blok_match['Attack_Pct'].mean() if not blok_match.empty else 0
    
    marker = "✅" if attack >= 10 else "❌"
    print(f'{marker} {r["Blok_Prod"]:10s} (Gano: {gano_pattern:5s}) -> Attack: {attack:.1f}%, Yield: {r["Yield_TonHa"]:.2f}')
    if attack >= 10:
        matched += 1

print(f'\n📊 Result: {matched}/10 blocks have attack >= 10%')
