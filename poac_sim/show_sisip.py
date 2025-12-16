"""Show sisip comparison results"""
import pandas as pd
from pathlib import Path
import sys

script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

import logging
logging.disable(logging.CRITICAL)

from src.ingestion import load_and_clean_data, load_ame_iv_data
from src.cost_control_loader import normalize_block

# Load drone data
df_ame2 = load_and_clean_data(script_dir / "data/input/tabelNDREnew.csv")
df_ame4 = load_ame_iv_data(script_dir / "data/input/AME_IV.csv")

# Load ground truth
df_gt = pd.read_excel(
    script_dir / "data/input/areal_inti_serangan_gano_AMEII_AMEIV.xlsx",
    sheet_name='Sheet1', header=[0, 1]
)
df_gt.columns = ['DIVISI', 'BLOK', 'TAHUN_TANAM', 'LUAS_SD_2024', 'PENAMBAHAN', 
                 'LUAS_SD_2025', 'TANAM', 'SISIP', 'SISIP_KENTOSAN', 'TOTAL_PKK',
                 'SPH', 'STADIUM_12', 'STADIUM_34', 'TOTAL_GANO', 'SERANGAN_PCT']

# AME II
sisip_drone_ame2 = len(df_ame2[df_ame2['Category'] == 'YOUNG'])
df_gt_ame2 = df_gt[df_gt['DIVISI'] == 'AME002']
gt_sisip_ame2 = int(df_gt_ame2['SISIP'].fillna(0).sum() + df_gt_ame2['SISIP_KENTOSAN'].fillna(0).sum())

# AME IV
sisip_drone_ame4 = len(df_ame4[df_ame4['Category'] == 'YOUNG'])
df_gt_ame4 = df_gt[df_gt['DIVISI'] == 'AME004']
gt_sisip_ame4 = int(df_gt_ame4['SISIP'].fillna(0).sum() + df_gt_ame4['SISIP_KENTOSAN'].fillna(0).sum())

print("="*70)
print("PERBANDINGAN JUMLAH SISIP: Drone vs Ground Truth")
print("="*70)

print()
print(f"{'Divisi':<10} {'Drone SISIP':>15} {'GT SISIP':>15} {'Difference':>15}")
print("-"*55)
print(f"{'AME II':<10} {sisip_drone_ame2:>15,} {gt_sisip_ame2:>15,} {sisip_drone_ame2 - gt_sisip_ame2:>+15,}")
print(f"{'AME IV':<10} {sisip_drone_ame4:>15,} {gt_sisip_ame4:>15,} {sisip_drone_ame4 - gt_sisip_ame4:>+15,}")

# Blok breakdown AME II
print()
print("="*70)
print("AME II - Blok dengan SISIP")
print("="*70)

sisip_blok_ame2 = df_ame2[df_ame2['Category'] == 'YOUNG'].groupby('Blok').size().sort_values(ascending=False)
print(f"\nDrone Data - Top 10 blok dengan SISIP:")
for blok, count in sisip_blok_ame2.head(10).items():
    print(f"  {blok}: {count}")

print(f"\nSemua blok dengan SISIP di Drone: {list(sisip_blok_ame2.index)}")

# GT sisip per blok AME II
print(f"\nGround Truth - Blok dengan SISIP > 0:")
for _, row in df_gt_ame2[df_gt_ame2['SISIP'] > 0].iterrows():
    print(f"  {row['BLOK']}: SISIP={int(row['SISIP'])}, KENTOSAN={int(row['SISIP_KENTOSAN']) if pd.notna(row['SISIP_KENTOSAN']) else 0}")

# Blok breakdown AME IV  
print()
print("="*70)
print("AME IV - Blok dengan SISIP")
print("="*70)

sisip_blok_ame4 = df_ame4[df_ame4['Category'] == 'YOUNG'].groupby('Blok').size().sort_values(ascending=False)
print(f"\nDrone Data - Top 10 blok dengan SISIP:")
for blok, count in sisip_blok_ame4.head(10).items():
    print(f"  {blok}: {count}")

print(f"\nGround Truth top 10 SISIP:")
for _, row in df_gt_ame4.sort_values('SISIP', ascending=False).head(10).iterrows():
    print(f"  {row['BLOK']}: SISIP={int(row['SISIP']) if pd.notna(row['SISIP']) else 0}, KENTOSAN={int(row['SISIP_KENTOSAN']) if pd.notna(row['SISIP_KENTOSAN']) else 0}")
