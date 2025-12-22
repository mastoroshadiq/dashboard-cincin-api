"""
Analisis Pohon Tambahan (TAMB) - Drone Data
"""
import pandas as pd

print('=' * 60)
print('ANALISIS POHON TAMBAHAN (TAMB) - DRONE DATA')
print('=' * 60)

# Load AME II
df_ame2 = pd.read_csv('data/input/tabelNDREnew.csv')
tamb_ame2 = len(df_ame2[df_ame2['ket'].str.contains('Tamb', case=False, na=False)])
total_ame2 = len(df_ame2)

print()
print('AME II:')
print('  Total Pohon:    {:,}'.format(total_ame2))
print('  Pohon Tamb:     {:,}'.format(tamb_ame2))
print('  Persentase:     {:.2f}%'.format(tamb_ame2/total_ame2*100))
print()
print('  Breakdown kategori ket:')
for val, cnt in df_ame2['ket'].value_counts().items():
    print('    {}: {:,}'.format(val, cnt))

# Load AME IV  
df_ame4 = pd.read_csv('data/input/AME_IV.csv', sep=';')
print()
print('=' * 60)
print('AME IV:')
print('=' * 60)
print('  Total Pohon:    {:,}'.format(len(df_ame4)))
print('  Kolom tersedia:')
for col in df_ame4.columns:
    print('    - {}'.format(col))

# Check Ket column in AME IV
if 'Ket' in df_ame4.columns:
    print()
    print('  Nilai di kolom Ket:')
    for val, cnt in df_ame4['Ket'].value_counts().items():
        print('    {}: {:,}'.format(val, cnt))
    
    tamb_ame4 = len(df_ame4[df_ame4['Ket'].str.contains('Tamb', case=False, na=False)])
    print()
    print('  Pohon Tamb:     {:,}'.format(tamb_ame4))
else:
    print('  Kolom Ket tidak ditemukan')
    
# Check other columns that might contain classification
print()
print('=' * 60)
print('RINGKASAN')
print('=' * 60)
print()
print('Divisi     | Total      | Tamb       | Persentase')
print('-' * 52)
print('AME II     | {:>10,} | {:>10,} | {:.2f}%'.format(total_ame2, tamb_ame2, tamb_ame2/total_ame2*100))

if 'Ket' in df_ame4.columns:
    tamb_ame4 = len(df_ame4[df_ame4['Ket'].str.contains('Tamb', case=False, na=False)])
    print('AME IV     | {:>10,} | {:>10,} | {:.2f}%'.format(len(df_ame4), tamb_ame4, tamb_ame4/len(df_ame4)*100 if len(df_ame4) > 0 else 0))
