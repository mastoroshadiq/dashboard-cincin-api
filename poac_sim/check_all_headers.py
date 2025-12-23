import pandas as pd

df = pd.read_excel('data/input/data_gabungan.xlsx', header=None)
headers = df.iloc[6]

print('=== All column headers (showing col index and header) ===')
print('Looking for any attack/stadium/percentage columns...\n')

# Show all headers to manually identify
for i in range(len(headers)):
    if pd.notna(headers[i]):
        h = str(headers[i])
        # Show columns that might be related
        if any(char.isdigit() for char in h) or '%' in h or len(h) < 10:
            print(f'col_{i}: {h}')

print('\n=== Showing headers around column 50-100 ===')
for i in range(50, min(100, len(headers))):
    if pd.notna(headers[i]):
        print(f'col_{i}: {headers[i]}')
