import pandas as pd

print('=== Checking areal_inti_serangan_gano_AMEII_AMEIV.xlsx ===')
try:
    df_gano = pd.read_excel('data/input/areal_inti_serangan_gano_AMEII_AMEIV.xlsx')
    print(f'Shape: {df_gano.shape}')
    print(f'\nColumns:\n{df_gano.columns.tolist()}')
    print(f'\nFirst 3 rows:')
    print(df_gano.head(3))
    
    if 'Divisi' in df_gano.columns or 'Estate' in df_gano.columns:
        div_col = 'Divisi' if 'Divisi' in df_gano.columns else 'Estate'
        print(f'\nUnique divisions: {df_gano[div_col].unique()}')
except Exception as e:
    print(f'Error: {e}')

print('\n' + '='*70)
print('=== Checking Arael Inti & Serangan Ganoderma.xlsx ===')
try:
    df_arael = pd.read_excel('data/input/Arael Inti & Serangan Ganoderma.xlsx')
    print(f'Shape: {df_arael.shape}')
    print(f'\nColumns:\n{df_arael.columns.tolist()}')
    print(f'\nFirst 3 rows:')
    print(df_arael.head(3))
except Exception as e:
    print(f'Error: {e}')

print('\n' + '='*70)
print('=== CONCLUSION ===')
print('If these files have block-level Ganoderma data for other divisions:')
print('→ Can create POV 1 & POV 2 with visualizations')
print('\nIf NOT:')
print('→ Create production-only dashboard (no Ganoderma charts)')
