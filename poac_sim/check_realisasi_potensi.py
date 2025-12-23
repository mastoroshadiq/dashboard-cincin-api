import pandas as pd

print('=== Loading Realisasi vs Potensi Data ===')
df = pd.read_excel('data/input/Realisasi vs Potensi PT SR.xlsx', header=None)

print(f'\nShape: {df.shape}')
print(f'\nFirst 15 rows to find headers:')
print(df.head(15))

print('\n=== Looking for data pattern ===')
# Try to find where actual data starts
for i in range(15):
    print(f'\nRow {i}: {df.iloc[i, 0:5].tolist()}')
