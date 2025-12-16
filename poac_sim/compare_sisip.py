"""
Perbandingan Jumlah SISIP antara Drone Data dan Ground Truth
============================================================
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys

script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

import logging
logging.disable(logging.CRITICAL)

from src.ingestion import load_and_clean_data, load_ame_iv_data
from src.cost_control_loader import normalize_block

print("="*80)
print("PERBANDINGAN SISIP: Drone Data vs Ground Truth")
print("="*80)

# Load drone data
print("\nLoading drone data...")
df_ame2 = load_and_clean_data(script_dir / "data/input/tabelNDREnew.csv")
df_ame4 = load_ame_iv_data(script_dir / "data/input/AME_IV.csv")

# Load ground truth
print("Loading ground truth...")
df_gt = pd.read_excel(
    script_dir / "data/input/areal_inti_serangan_gano_AMEII_AMEIV.xlsx",
    sheet_name='Sheet1', header=[0, 1]
)
df_gt.columns = ['DIVISI', 'BLOK', 'TAHUN_TANAM', 'LUAS_SD_2024', 'PENAMBAHAN', 
                 'LUAS_SD_2025', 'TANAM', 'SISIP', 'SISIP_KENTOSAN', 'TOTAL_PKK',
                 'SPH', 'STADIUM_12', 'STADIUM_34', 'TOTAL_GANO', 'SERANGAN_PCT']

# Process AME II
print("\n" + "="*80)
print("AME II (AME002)")
print("="*80)

sisip_drone_ame2 = df_ame2[df_ame2['Category'] == 'YOUNG']
sisip_per_blok_drone = sisip_drone_ame2.groupby('Blok').size().reset_index(name='Drone_Sisip')
sisip_per_blok_drone['blok_norm'] = sisip_per_blok_drone['Blok'].apply(normalize_block)

df_gt_ame2 = df_gt[df_gt['DIVISI'] == 'AME002'].copy()
df_gt_ame2['blok_norm'] = df_gt_ame2['BLOK'].apply(normalize_block)
df_gt_ame2['GT_Sisip'] = df_gt_ame2['SISIP'].fillna(0) + df_gt_ame2['SISIP_KENTOSAN'].fillna(0)

# Merge
comparison_ame2 = sisip_per_blok_drone.merge(
    df_gt_ame2[['BLOK', 'blok_norm', 'SISIP', 'SISIP_KENTOSAN', 'GT_Sisip', 'TANAM', 'TOTAL_PKK']],
    on='blok_norm', how='outer'
).fillna(0)

print(f"\nTotal SISIP dari Drone: {sisip_drone_ame2.shape[0]:,}")
print(f"Total SISIP dari Ground Truth: {int(df_gt_ame2['GT_Sisip'].sum()):,}")
print(f"Difference: {sisip_drone_ame2.shape[0] - int(df_gt_ame2['GT_Sisip'].sum()):+,}")

print(f"\nBlok dengan SISIP di Drone: {len(sisip_per_blok_drone)}")
print(f"Blok dengan SISIP di GT: {len(df_gt_ame2[df_gt_ame2['GT_Sisip'] > 0])}")

print("\n" + "-"*80)
print("Detail per Blok (Top 20 by GT Sisip):")
print("-"*80)
print(f"{'Blok':<15} {'Drone Sisip':>12} {'GT Sisip':>12} {'Diff':>12} {'GT TANAM':>12}")
print("-"*80)

comparison_ame2 = comparison_ame2.sort_values('GT_Sisip', ascending=False)
for _, row in comparison_ame2.head(20).iterrows():
    blok = row['BLOK'] if row['BLOK'] else row['Blok']
    drone = int(row['Drone_Sisip'])
    gt = int(row['GT_Sisip'])
    diff = drone - gt
    tanam = int(row['TANAM'])
    print(f"{blok:<15} {drone:>12,} {gt:>12,} {diff:>+12,} {tanam:>12,}")

# Process AME IV
print("\n\n" + "="*80)
print("AME IV (AME004)")
print("="*80)

sisip_drone_ame4 = df_ame4[df_ame4['Category'] == 'YOUNG']
sisip_per_blok_drone4 = sisip_drone_ame4.groupby('Blok').size().reset_index(name='Drone_Sisip')
sisip_per_blok_drone4['blok_norm'] = sisip_per_blok_drone4['Blok'].apply(normalize_block)

df_gt_ame4 = df_gt[df_gt['DIVISI'] == 'AME004'].copy()
df_gt_ame4['blok_norm'] = df_gt_ame4['BLOK'].apply(normalize_block)
df_gt_ame4['GT_Sisip'] = df_gt_ame4['SISIP'].fillna(0) + df_gt_ame4['SISIP_KENTOSAN'].fillna(0)

# Merge
comparison_ame4 = sisip_per_blok_drone4.merge(
    df_gt_ame4[['BLOK', 'blok_norm', 'SISIP', 'SISIP_KENTOSAN', 'GT_Sisip', 'TANAM', 'TOTAL_PKK']],
    on='blok_norm', how='outer'
).fillna(0)

print(f"\nTotal SISIP dari Drone: {sisip_drone_ame4.shape[0]:,}")
print(f"Total SISIP dari Ground Truth: {int(df_gt_ame4['GT_Sisip'].sum()):,}")
print(f"Difference: {sisip_drone_ame4.shape[0] - int(df_gt_ame4['GT_Sisip'].sum()):+,}")

print(f"\nBlok dengan SISIP di Drone: {len(sisip_per_blok_drone4)}")
print(f"Blok dengan SISIP di GT: {len(df_gt_ame4[df_gt_ame4['GT_Sisip'] > 0])}")

print("\n" + "-"*80)
print("Detail per Blok (Top 20 by GT Sisip):")
print("-"*80)
print(f"{'Blok':<15} {'Drone Sisip':>12} {'GT Sisip':>12} {'Diff':>12} {'GT TANAM':>12}")
print("-"*80)

comparison_ame4 = comparison_ame4.sort_values('GT_Sisip', ascending=False)
for _, row in comparison_ame4.head(20).iterrows():
    blok = row['BLOK'] if row['BLOK'] else row['Blok']
    drone = int(row['Drone_Sisip'])
    gt = int(row['GT_Sisip'])
    diff = drone - gt
    tanam = int(row['TANAM'])
    print(f"{blok:<15} {drone:>12,} {gt:>12,} {diff:>+12,} {tanam:>12,}")

# Summary
print("\n\n" + "="*80)
print("RINGKASAN")
print("="*80)
print(f"\n{'Divisi':<12} {'Drone Sisip':>15} {'GT Sisip':>15} {'Difference':>15}")
print("-"*60)
print(f"{'AME II':<12} {sisip_drone_ame2.shape[0]:>15,} {int(df_gt_ame2['GT_Sisip'].sum()):>15,} {sisip_drone_ame2.shape[0] - int(df_gt_ame2['GT_Sisip'].sum()):>+15,}")
print(f"{'AME IV':<12} {sisip_drone_ame4.shape[0]:>15,} {int(df_gt_ame4['GT_Sisip'].sum()):>15,} {sisip_drone_ame4.shape[0] - int(df_gt_ame4['GT_Sisip'].sum()):>+15,}")

# Check blok yang ada di drone tapi tidak di GT
print("\n\nBlok dengan SISIP di Drone tapi tidak ada di GT:")
drone_only_ame2 = set(sisip_per_blok_drone['blok_norm']) - set(df_gt_ame2['blok_norm'])
drone_only_ame4 = set(sisip_per_blok_drone4['blok_norm']) - set(df_gt_ame4['blok_norm'])
print(f"  AME II: {len(drone_only_ame2)} blok")
print(f"  AME IV: {len(drone_only_ame4)} blok")

# Save to CSV
comparison_ame2.to_csv(script_dir / "data/output/sisip_comparison_ame2.csv", index=False)
comparison_ame4.to_csv(script_dir / "data/output/sisip_comparison_ame4.csv", index=False)
print("\nCSV saved to data/output/sisip_comparison_ame2.csv and sisip_comparison_ame4.csv")
