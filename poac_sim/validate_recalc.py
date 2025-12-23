import sys
sys.path.insert(0, '.')
from dashboard_v7_fixed import load_productivity_data

df = load_productivity_data()
e011a = df[df['Blok_Prod'] == 'E011A']

if not e011a.empty:
    row = e011a.iloc[0]
    print('=== VALIDASI E011A ===')
    print(f'Blok: {row["Blok_Prod"]}')
    print(f'Luas Ha: {row["Luas_Ha"]:.1f}')
    print(f'Produksi Real: {row["Produksi_Ton"]:.2f} Ton')
    print(f'Potensi Prod: {row["Potensi_Prod_Ton"]:.2f} Ton')
    print(f'Gap Prod: {row["Potensi_Prod_Ton"] - row["Produksi_Ton"]:.2f} Ton')
    print()
    print(f'Yield Real (RECALCULATED): {row["Yield_Realisasi"]:.2f} Ton/Ha')
    print(f'  = {row["Produksi_Ton"]:.2f} / {row["Luas_Ha"]:.1f}')
    print(f'  = {row["Produksi_Ton"] / row["Luas_Ha"]:.2f} Ton/Ha ✓')
    print()
    print(f'Yield Potensi (RECALCULATED): {row["Potensi_Yield"]:.2f} Ton/Ha')
    print(f'  = {row["Potensi_Prod_Ton"]:.2f} / {row["Luas_Ha"]:.1f}')
    print(f'  = {row["Potensi_Prod_Ton"] / row["Luas_Ha"]:.2f} Ton/Ha ✓')
    print()
    print(f'Gap Yield: {row["Gap_Yield"]:.2f} Ton/Ha')
    print()
    print('=== USER VALIDATION ===')
    print(f'User calculation: 396.81 / 24.3 = {396.81/24.3:.2f}')
    print(f'Our calculation:  {row["Yield_Realisasi"]:.2f}')
    print(f'Match: {"✓ YES" if abs(row["Yield_Realisasi"] - 396.81/24.3) < 0.01 else "❌ NO"}')
else:
    print('E011A not found!')
