"""Analisis NDRE per Kategori untuk menentukan threshold yang tepat"""
import pandas as pd
import numpy as np
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent))

import logging
logging.disable(logging.CRITICAL)

from src.ingestion import load_and_clean_data, load_ame_iv_data

# Load data
df_ame2 = load_and_clean_data('data/input/tabelNDREnew.csv')
df_ame4 = load_ame_iv_data('data/input/AME_IV.csv')

print("="*80)
print("ANALISIS NDRE PER KATEGORI")
print("="*80)

for divisi, df in [("AME II", df_ame2), ("AME IV", df_ame4)]:
    print(f"\n{divisi}")
    print("-"*60)
    print(f"{'Category':<12} {'Count':>10} {'Mean NDRE':>12} {'Std NDRE':>12} {'Min':>10} {'Max':>10}")
    print("-"*60)
    
    for cat in ['MATURE', 'YOUNG', 'DEAD', 'EMPTY']:
        df_cat = df[df['Category'] == cat]
        if len(df_cat) > 0:
            mean_v = df_cat['NDRE125'].mean()
            std_v = df_cat['NDRE125'].std()
            min_v = df_cat['NDRE125'].min()
            max_v = df_cat['NDRE125'].max()
            print(f"{cat:<12} {len(df_cat):>10,} {mean_v:>12.4f} {std_v:>12.4f} {min_v:>10.4f} {max_v:>10.4f}")
        else:
            print(f"{cat:<12} {0:>10} {'N/A':>12} {'N/A':>12} {'N/A':>10} {'N/A':>10}")

print("\n" + "="*80)
print("REKOMENDASI")
print("="*80)

# Calculate difference
for divisi, df in [("AME II", df_ame2), ("AME IV", df_ame4)]:
    mature_mean = df[df['Category'] == 'MATURE']['NDRE125'].mean()
    young = df[df['Category'] == 'YOUNG']
    
    if len(young) > 0:
        young_mean = young['NDRE125'].mean()
        diff = mature_mean - young_mean
        print(f"\n{divisi}:")
        print(f"  MATURE Mean: {mature_mean:.4f}")
        print(f"  YOUNG Mean:  {young_mean:.4f}")
        print(f"  Difference:  {diff:.4f}")
        
        if diff > 0.05:
            print(f"  => YOUNG memiliki NDRE signifikan lebih rendah")
            print(f"  => Perlu threshold TERPISAH atau dikecualikan dari baseline")
    else:
        print(f"\n{divisi}: No YOUNG trees")

print("\n" + "="*80)
print("OPSI PENANGANAN")
print("="*80)
print("""
OPSI A: MATURE Only (Current)
  - Hanya MATURE masuk baseline dan deteksi
  - YOUNG, DEAD, EMPTY dikecualikan
  - Paling konservatif, tidak ada false positive

OPSI B: Include YOUNG dengan baseline terpisah
  - MATURE: baseline dari MATURE, threshold -1.5 (AME II) / -4.0 (AME IV)  
  - YOUNG:  baseline dari YOUNG, threshold -2.0 (lebih ketat)
  - DEAD, EMPTY: excluded
  
OPSI C: Include YOUNG tapi force G1 (monitoring)
  - MATURE: deteksi normal dengan Z-Score
  - YOUNG:  selalu G1 (monitoring) tanpa Z-Score
  - DEAD:   selalu G4 (source/trigger Cincin Api)
  - EMPTY:  excluded
""")
