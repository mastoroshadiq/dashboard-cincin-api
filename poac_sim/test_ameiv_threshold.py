"""Display AME IV threshold analysis - Save to file"""
import pandas as pd
import numpy as np
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent))

import logging
logging.disable(logging.CRITICAL)

from src.ingestion import load_ame_iv_data
from src.cost_control_loader import normalize_block

df = load_ame_iv_data('data/input/AME_IV.csv')
df = df[df['Category'] == 'MATURE'].copy()

df_gt = pd.read_excel('data/input/areal_inti_serangan_gano_AMEII_AMEIV.xlsx', sheet_name='Sheet1', header=[0, 1])
df_gt.columns = ['DIVISI', 'BLOK', 'TAHUN_TANAM', 'LUAS_SD_2024', 'PENAMBAHAN', 'LUAS_SD_2025', 'TANAM', 'SISIP', 'SISIP_KENTOSAN', 'TOTAL_PKK', 'SPH', 'STADIUM_12', 'STADIUM_34', 'TOTAL_GANO', 'SERANGAN_PCT']
df_gt = df_gt[df_gt['DIVISI'] == 'AME004']
df_gt['blok_norm'] = df_gt['BLOK'].apply(normalize_block)
df_gt['gt_pct'] = df_gt['TOTAL_GANO'] / df_gt['TOTAL_PKK'] * 100

thresholds = [-2.5, -3.0, -3.25, -3.5, -3.75, -4.0, -4.25, -4.5, -4.75, -5.0]
results_all = []

for thresh in thresholds:
    results = []
    for blok in df['Blok'].unique():
        mask = df['Blok'] == blok
        ndre = df.loc[mask, 'NDRE125']
        if len(ndre) > 1:
            mean_v, std_v = ndre.mean(), ndre.std()
            if std_v > 0:
                z = (ndre - mean_v) / std_v
                detected = (z < thresh).sum()
                total = len(ndre)
                results.append({'blok_norm': normalize_block(blok), 'pct': detected/total*100})
    
    df_res = pd.DataFrame(results)
    df_merged = df_res.merge(df_gt[['blok_norm', 'gt_pct']], on='blok_norm', how='inner')
    
    mae = abs(df_merged['pct'] - df_merged['gt_pct']).mean()
    corr = df_merged['pct'].corr(df_merged['gt_pct'])
    algo = df_merged['pct'].mean()
    gt = df_merged['gt_pct'].mean()
    
    results_all.append({'Threshold': thresh, 'MAE': mae, 'Corr': corr, 'Algo': algo, 'GT': gt, 'Bias': algo-gt})

df_results = pd.DataFrame(results_all)

# Print directly
for _, row in df_results.iterrows():
    best = " ** BEST" if row['MAE'] == df_results['MAE'].min() else ""
    print(f"Z<{row['Threshold']:.2f}: MAE={row['MAE']:.2f}% r={row['Corr']:.3f} Algo={row['Algo']:.1f}% GT={row['GT']:.1f}% Bias={row['Bias']:+.1f}%{best}")

print()
print(f"Best: Z < {df_results.loc[df_results['MAE'].idxmin(), 'Threshold']} (MAE={df_results['MAE'].min():.2f}%)")
