import sys
sys.path.insert(0, '.')
from all_divisions_module import load_ganoderma_block_stats
from dashboard_v7_fixed import load_productivity_data

# Load both datasets
print('=== Loading Ganoderma Stats ===')
gano_stats = load_ganoderma_block_stats()
print(f'Loaded {len(gano_stats)} blocks with Ganoderma data')
print(f'\nSample gano_stats:')
print(gano_stats.head(10))

print('\n=== Loading Productivity Data ===')
prod_df = load_productivity_data()
print(f'Loaded {len(prod_df)} blocks with productivity data')

# Get top/bottom performers
top_10 = prod_df.nlargest(10, 'Yield_TonHa')
bottom_10 = prod_df.nsmallest(10, 'Yield_TonHa')

print('\n=== Checking Top 10 Best Performers ===')
for i, (_, row) in enumerate(top_10.iterrows(), 1):
    blok = row['Blok_Prod']
    in_gano = blok in gano_stats.index
    attack = gano_stats.loc[blok, 'Attack_Pct'] if in_gano else None
    print(f'{i}. {blok:15s} | In gano_stats: {in_gano} | Attack: {attack}')

print('\n=== Checking Bottom 10 Lowest Performers ===')
for i, (_, row) in enumerate(bottom_10.iterrows(), 1):
    blok = row['Blok_Prod']
    in_gano = blok in gano_stats.index
    attack = gano_stats.loc[blok, 'Attack_Pct'] if in_gano else None
    print(f'{i}. {blok:15s} | In gano_stats: {in_gano} | Attack: {attack}')

print('\n=== Checking if issue is Attack_Pct = 0 ===')
zero_attack = gano_stats[gano_stats['Attack_Pct'] == 0]
print(f'Blocks with 0% attack (filtered out): {len(zero_attack)}')

print('\n=== Sample block names comparison ===')
print('From productivity data (first 5):')
print(prod_df['Blok_Prod'].head().tolist())
print('\nFrom gano_stats (first 5):')
print(gano_stats.head().index.tolist())
