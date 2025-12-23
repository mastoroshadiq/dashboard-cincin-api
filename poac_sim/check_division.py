import sys
sys.path.insert(0, '.')
from dashboard_v7_fixed import load_productivity_data
import pandas as pd

# Load productivity data
prod_df = load_productivity_data()

# Filter productive age
productive_df = prod_df[(prod_df['Umur_Tahun'] >= 3) & (prod_df['Umur_Tahun'] <= 25)]

# Get lowest yield
low_yield = productive_df.nsmallest(20, 'Yield_TonHa')

print('=== Top 20 Lowest Yield Blocks by Division ===\n')
for idx, (_, row) in enumerate(low_yield.iterrows(), 1):
    print(f'{idx:2d}. {row["Blok_Prod"]:10s} | Division: {row["Divisi_Prod"]:10s} | Yield: {row["Yield_TonHa"]:6.2f} | Age: {row["Umur_Tahun"]:.0f}y')

print('\n=== Division Distribution in Top 20 ===')
print(low_yield['Divisi_Prod'].value_counts())

print('\n💡 INSIGHT:')
print('POV 2 is generated PER DIVISION (AME II, AME IV separately)')
print('If all low-yield blocks are in one division, other divisions will show "no data"')
