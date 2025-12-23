import pandas as pd

df = pd.read_excel('data/input/data_gabungan.xlsx', header=None)
df_data = df.iloc[8:].copy()
df_data.columns = [f'col_{i}' for i in range(df_data.shape[1])]

e011a = df_data[df_data['col_0'] == 'E011A'].iloc[0]

print('=== Data E011A dari Excel ===')
print(f'col_11 (Luas Ha): {e011a["col_11"]}')
print(f'col_170 (Produksi Real Ton): {e011a["col_170"]}')
print(f'col_171 (Yield dari Excel): {e011a["col_171"]}')
print(f'col_173 (Potensi Prod Ton): {e011a["col_173"]}')

print('\n=== Perhitungan Manual User ===')
luas_col11 = float(e011a['col_11'])
prod_real = float(e011a['col_170'])
yield_manual = prod_real / luas_col11
print(f'Yield Manual = Produksi / Luas')
print(f'            = {prod_real} / {luas_col11}')
print(f'            = {yield_manual:.2f} Ton/Ha ✓ (BENAR menurut User)')

print('\n=== Yield dari Excel (col_171) ===')
yield_excel = float(e011a['col_171'])
print(f'Yield Excel = {yield_excel:.2f} Ton/Ha')

print('\n=== DISCREPANCY ===')
print(f'User calculation: {yield_manual:.2f} Ton/Ha')
print(f'Excel col_171:    {yield_excel:.2f} Ton/Ha')
print(f'Difference:       {abs(yield_excel - yield_manual):.2f} Ton/Ha')

print('\n=== Hypothesis: Excel uses different Luas ===')
# Reverse calculate what Luas was used in Excel
luas_implied = prod_real / yield_excel
print(f'If Yield = {yield_excel:.2f}, then Luas used = {prod_real} / {yield_excel:.2f}')
print(f'                             = {luas_implied:.2f} Ha')
print(f'\nExcel may use "Effective Area" = {luas_implied:.2f} Ha')
print(f'vs "Legal/Administrative Area" = {luas_col11:.2f} Ha')
print(f'Difference: {abs(luas_col11 - luas_implied):.2f} Ha')

print('\n=== RECOMMENDATION ===')
print('Question: Which Yield should we display?')
print('A) Manual calculation: 396.81 / 24.3 = 16.32 Ton/Ha (using col_11)')
print('B) Excel column: col_171 = 18.19 Ton/Ha (pre-calculated)')
