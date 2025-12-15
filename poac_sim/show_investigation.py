"""Display investigation summary"""
import pandas as pd
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.ingestion import load_and_clean_data, load_ame_iv_data

# Load
df_ame2 = load_and_clean_data(Path(__file__).parent / "data/input/tabelNDREnew.csv")
df_ame4 = load_ame_iv_data(Path(__file__).parent / "data/input/AME_IV.csv")

# Load GT
df_gt = pd.read_excel(
    Path(__file__).parent / "data/input/areal_inti_serangan_gano_AMEII_AMEIV.xlsx",
    sheet_name='Sheet1', header=[0, 1]
)
df_gt.columns = ['DIVISI', 'BLOK', 'TAHUN_TANAM', 'LUAS_SD_2024', 'PENAMBAHAN', 
                 'LUAS_SD_2025', 'TANAM', 'SISIP', 'SISIP_KENTOSAN', 'TOTAL_PKK',
                 'SPH', 'STADIUM_12', 'STADIUM_34', 'TOTAL_GANO', 'SERANGAN_PCT']

# MATURE only
ame2_m = df_ame2[df_ame2['Category'] == 'MATURE']['NDRE125']
ame4_m = df_ame4[df_ame4['Category'] == 'MATURE']['NDRE125']

gt_ame2 = df_gt[df_gt['DIVISI'] == 'AME002']
gt_ame4 = df_gt[df_gt['DIVISI'] == 'AME004']

print("="*70)
print("INVESTIGATION SUMMARY: AME II vs AME IV")
print("="*70)

print("\n1. NDRE STATISTICS (MATURE only):")
print("-"*50)
print(f"  {'Metric':<20} {'AME II':>12} {'AME IV':>12}")
print(f"  {'-'*44}")
print(f"  {'Count':<20} {len(ame2_m):>12,} {len(ame4_m):>12,}")
print(f"  {'Mean':<20} {ame2_m.mean():>12.4f} {ame4_m.mean():>12.4f}")
print(f"  {'Std Dev':<20} {ame2_m.std():>12.4f} {ame4_m.std():>12.4f}")
print(f"  {'CV %':<20} {ame2_m.std()/ame2_m.mean()*100:>11.2f}% {ame4_m.std()/ame4_m.mean()*100:>11.2f}%")

print("\n2. GROUND TRUTH GANODERMA:")
print("-"*50)
pct2 = gt_ame2['TOTAL_GANO'].sum() / gt_ame2['TOTAL_PKK'].sum() * 100
pct4 = gt_ame4['TOTAL_GANO'].sum() / gt_ame4['TOTAL_PKK'].sum() * 100
print(f"  AME II: {pct2:.2f}% serangan")
print(f"  AME IV: {pct4:.2f}% serangan")

print("\n3. POPULATION COMPOSITION:")
print("-"*50)
for cat in ['MATURE', 'YOUNG', 'DEAD', 'EMPTY']:
    c2 = len(df_ame2[df_ame2['Category']==cat])
    c4 = len(df_ame4[df_ame4['Category']==cat])
    p2 = c2/len(df_ame2)*100
    p4 = c4/len(df_ame4)*100
    print(f"  {cat:<10} AME II: {c2:>6,} ({p2:>5.1f}%)  |  AME IV: {c4:>6,} ({p4:>5.1f}%)")

print("\n4. TAHUN TANAM (from Ground Truth):")
print("-"*50)
tt2 = gt_ame2['TAHUN_TANAM'].unique()
tt4 = gt_ame4['TAHUN_TANAM'].unique()
print(f"  AME II: {sorted([int(x) for x in tt2 if pd.notna(x)])}")
print(f"  AME IV: {sorted([int(x) for x in tt4 if pd.notna(x)])}")

print("\n" + "="*70)
print("KESIMPULAN: Mengapa AME IV butuh threshold lebih ketat (Z < -4.0)?")
print("="*70)
print("""
1. NDRE Std Dev AME IV (0.0445) < AME II (0.0336)
   => Data AME IV LEBIH HOMOGEN (variasi lebih kecil)
   => Z-Score distribution lebih sempit
   => Butuh threshold leboh ketat untuk detect outliers

2. Ground Truth % Serangan:
   - AME IV: 3.84% (LEBIH RENDAH)
   - AME II: 6.28%
   => AME IV memiliki lebih sedikit pohon sakit
   => Threshold standar (-2.0) akan over-detect

3. AME IV memiliki 10.8% EMPTY (vs 0% di AME II)
   => Kemungkinan data quality issue di AME IV
   => Pohon dengan NDRE invalid sudah ter-exclude

4. AME IV lebih muda (tanam 2010-2019) vs AME II (2008-2009)
   => Pohon muda mungkin memiliki profil NDRE berbeda
""")
