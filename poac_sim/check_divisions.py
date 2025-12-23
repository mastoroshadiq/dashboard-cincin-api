import pandas as pd

# Check divisions in data_gabungan.xlsx
df = pd.read_excel('data/input/data_gabungan.xlsx', header=None)
df_data = df.iloc[8:].copy()
df_data.columns = [f'col_{i}' for i in range(df_data.shape[1])]

# col_3 is Divisi_Prod
df_data = df_data.rename(columns={'col_3': 'Divisi_Prod'})

print('=== Divisi/Estate Available in data_gabungan.xlsx ===')
divisi_counts = df_data['Divisi_Prod'].value_counts()
print(divisi_counts)

print(f'\n📊 Total unique divisions: {len(divisi_counts)}')
print(f'Total blocks: {len(df_data)}')

print('\n=== Checking Ganoderma Data Availability ===')
print('AME II: ✓ Has NDVI data (tabelNDREnew.csv)')
print('AME IV: ✓ Has NDVI data (AME_IV.csv)')

other_divisions = [d for d in divisi_counts.index if d not in ['AME II', 'AME IV', 'AME002', 'AME004']]
print(f'\nOther divisions ({len(other_divisions)}):')
for div in other_divisions[:10]:
    count = divisi_counts[div]
    print(f'  - {div}: {count} blocks')

print('\n⚠️ CRITICAL QUESTION:')
print('Do these other divisions have NDVI/Ganoderma tree-level data?')
print('\nPossibilities:')
print('1. If YES → Full dashboard (Z-Score, Cincin Api, POV 1, POV 2)')
print('2. If NO → Limited dashboard (Only POV 2 - yield analysis without Ganoderma)')
