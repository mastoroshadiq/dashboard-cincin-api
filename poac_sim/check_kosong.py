"""Check Kosong entries in tabelNDREnew.csv"""
import pandas as pd

df = pd.read_csv('data/input/tabelNDREnew.csv')

print("=== Sample Rows dengan Keterangan 'Kosong' ===")
print()

# Get rows with 'Kosong' label
kosong1 = df[df['ket'] == 'Kosong']
kosong2 = df[df['ket'] == 'Kosong.']

print(f"Keterangan 'Kosong': {len(kosong1)} rows")
print(kosong1[['blok', 'n_baris', 'n_pokok', 'ndre125', 'ket']].head(10).to_string())
print()

print(f"Keterangan 'Kosong.': {len(kosong2)} rows")
print(kosong2[['blok', 'n_baris', 'n_pokok', 'ndre125', 'ket']].head(10).to_string())
print()

# Convert ndre125 to numeric
df['ndre125_num'] = pd.to_numeric(df['ndre125'], errors='coerce')

# Check NDRE values for these
print("=== Statistik NDRE untuk berbagai kategori ===")
kosong1_ndre = pd.to_numeric(kosong1['ndre125'], errors='coerce')
kosong2_ndre = pd.to_numeric(kosong2['ndre125'], errors='coerce')
utama_ndre = pd.to_numeric(df[df['ket']=='Pokok Utama']['ndre125'], errors='coerce')

print(f"Kosong - NDRE mean: {kosong1_ndre.mean():.4f}")
print(f"Kosong. - NDRE mean: {kosong2_ndre.mean():.4f}")
print(f"Pokok Utama - NDRE mean: {utama_ndre.mean():.4f}")
