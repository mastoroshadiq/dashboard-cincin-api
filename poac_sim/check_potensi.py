import pandas as pd

df = pd.read_excel('data/input/data_gabungan.xlsx', header=None)
headers = df.iloc[6]

print('=== Headers around Produksi (col_170) ===')
for i in range(165, 177):
    if pd.notna(headers[i]):
        print(f'col_{i}: {headers[i]}')

print('\n=== Searching for Potensi/Realisasi columns ===')
for i, h in enumerate(headers):
    if pd.notna(h):
        h_str = str(h).lower()
        if 'potensi' in h_str or 'realisasi' in h_str or 'gap' in h_str:
            print(f'col_{i}: {headers[i]}')

print('\n=== Sample data (first 3 rows) ===')
df_data = df.iloc[8:11].copy()
df_data.columns = [f'col_{i}' for i in range(df_data.shape[1])]
print(df_data[['col_0', 'col_170', 'col_171', 'col_172']].to_string())
