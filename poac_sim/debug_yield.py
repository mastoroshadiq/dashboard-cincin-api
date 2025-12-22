import pandas as pd
from pathlib import Path

# Load Excel
df = pd.read_excel(Path('data/input/data_gabungan.xlsx'), header=None)

# Check header row
headers = df.iloc[6]
print('=== IMPORTANT COLUMNS ===')
print(f'col_0 (Blok): {headers[0]}')
print(f'col_1 (Tahun): {headers[1]}')
print(f'col_3 (Divisi): {headers[3]}')
print(f'col_11 (Luas): {headers[11]}')

print('\n=== PRODUCTION COLUMNS (col_160-177) ===')
for i in range(160, 177):
    if pd.notna(headers[i]):
        print(f'col_{i}: {headers[i]}')

# Parse actual data
df_data = df.iloc[8:].copy().reset_index(drop=True)
df_data.columns = [f'col_{i}' for i in range(df_data.shape[1])]

print('\n=== SAMPLE DATA ===')
print(df_data[['col_0', 'col_1', 'col_3', 'col_11', 'col_170']].head(10))

print('\n=== DATA VALIDITY CHECK ===')
df_data['Luas_Ha'] = pd.to_numeric(df_data['col_11'], errors='coerce')
df_data['Produksi_Ton'] = pd.to_numeric(df_data['col_170'], errors='coerce')
df_data['Yield_TonHa'] = df_data['Produksi_Ton'] / df_data['Luas_Ha']
df_data['Yield_TonHa'] = df_data['Yield_TonHa'].replace([float('inf'), float('-inf')], float('nan'))

valid_data = df_data[['col_0', 'Luas_Ha', 'Produksi_Ton', 'Yield_TonHa']].dropna()
print(f'Valid rows with yield: {len(valid_data)}')
print('\nSample valid data:')
print(valid_data.head(10))
