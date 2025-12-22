"""
Test Z-Score Spatial Filter v2.0
================================
Compare old Ranking/Elbow method vs new Z-Score method.
"""
import sys
sys.path.insert(0, 'src')

import pandas as pd
from pathlib import Path
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

from src.ingestion import load_and_clean_data
from src.zscore_detection import run_zscore_detection, run_zscore_comparison
from src.clustering import (
    calculate_percentile_rank,
    run_cincin_api_algorithm
)
from config import CINCIN_API_CONFIG, CINCIN_API_PRESETS

# Ground Truth
GT_TOTAL_GANO = 5969
TARGET_LOW = 4500
TARGET_HIGH = 8000

# Output
timestamp = datetime.now().strftime("%Y%m%d_%H%M")
output_dir = Path(f'data/output/zscore_v2_{timestamp}')
output_dir.mkdir(parents=True, exist_ok=True)

def run_old_method(df):
    """Run old Ranking/Elbow method (v3.5)."""
    df_classified, metadata = run_cincin_api_algorithm(
        df.copy(),
        auto_tune=True
    )
    merah = len(df_classified[df_classified['Status_Risiko'].str.contains('MERAH', na=False)])
    return merah, df_classified

def run_new_zscore_method(df, threshold=-1.5):
    """Run new Z-Score Spatial Filter method."""
    df_classified, metadata = run_zscore_detection(
        df.copy(),
        z_threshold=threshold
    )
    return metadata, df_classified

def main():
    print('=' * 70)
    print('COMPARISON: OLD METHOD vs NEW Z-SCORE SPATIAL FILTER')
    print('=' * 70)
    
    # Load data
    print('\n[1/3] Loading data...')
    df = load_and_clean_data(Path('data/input/tabelNDREnew.csv'))
    print(f'  Total: {len(df):,} pohon')
    print(f'  Ground Truth: {GT_TOTAL_GANO:,} GANO')
    
    # Run OLD method
    print('\n[2/3] Running OLD method (Ranking + Elbow v3.5)...')
    old_merah, df_old = run_old_method(df.copy())
    old_pct = (old_merah - GT_TOTAL_GANO) / GT_TOTAL_GANO * 100
    print(f'  OLD MERAH: {old_merah:,} ({old_pct:+.0f}% vs GT)')
    
    # Run NEW method with different thresholds
    print('\n[3/3] Running NEW Z-Score method...')
    comparison = run_zscore_comparison(df.copy())
    print(comparison.to_string(index=False))
    
    # Best threshold match
    new_meta, df_new = run_new_zscore_method(df.copy(), threshold=-1.5)
    new_total = new_meta['merah'] + new_meta['kuning']
    new_pct = (new_total - GT_TOTAL_GANO) / GT_TOTAL_GANO * 100
    
    # Results
    print('\n' + '=' * 70)
    print('RESULTS COMPARISON')
    print('=' * 70)
    print(f'\nGround Truth: {GT_TOTAL_GANO:,}')
    print(f'Target Range: {TARGET_LOW:,} - {TARGET_HIGH:,}')
    
    print('\n' + '-' * 70)
    print(f"{'Method':<35} {'Result':>10} {'vs GT':>10} {'Status':>10}")
    print('-' * 70)
    
    # Old method
    old_status = '✅ OK' if TARGET_LOW <= old_merah <= TARGET_HIGH else ('❌ UNDER' if old_merah < TARGET_LOW else '⚠️ OVER')
    print(f"{'OLD: Ranking+Elbow v3.5':<35} {old_merah:>10,} {f'{old_pct:+.0f}%':>10} {old_status:>10}")
    
    # New method thresholds
    for _, row in comparison.iterrows():
        total = row['Total_Deteksi']
        pct = (total - GT_TOTAL_GANO) / GT_TOTAL_GANO * 100
        status = '✅ OK' if TARGET_LOW <= total <= TARGET_HIGH else ('❌ UNDER' if total < TARGET_LOW else '⚠️ OVER')
        print(f"{'NEW: Z-Score ' + row['Label']:<35} {total:>10,} {f'{pct:+.0f}%':>10} {status:>10}")
    
    print('-' * 70)
    
    # Blok Analysis - Zero detection blocks
    print('\n' + '=' * 70)
    print('ANALISIS BLOK SEHAT (Zero Detection)')
    print('=' * 70)
    
    # Check blocks with zero detection in new method
    blok_deteksi = df_new.groupby('Blok')['Status_ZScore'].apply(
        lambda x: (x != 'HIJAU (SEHAT)').sum()
    )
    zero_blok = len(blok_deteksi[blok_deteksi == 0])
    total_blok = len(blok_deteksi)
    
    print(f'  Blok dengan 0 deteksi (SEHAT): {zero_blok} dari {total_blok} ({zero_blok/total_blok*100:.1f}%)')
    print('  >> Ini adalah kelebihan metode baru: tidak memaksa deteksi pada blok sehat!')
    
    # Save results
    df_new.to_csv(output_dir / 'zscore_results.csv', index=False)
    comparison.to_csv(output_dir / 'threshold_comparison.csv', index=False)
    
    # Save summary
    summary = {
        'Timestamp': timestamp,
        'Ground_Truth': GT_TOTAL_GANO,
        'OLD_Ranking_Elbow': old_merah,
        'NEW_ZScore_Agresif': comparison[comparison['Label'] == 'Agresif']['Total_Deteksi'].values[0],
        'NEW_ZScore_Seimbang': comparison[comparison['Label'] == 'Seimbang']['Total_Deteksi'].values[0],
        'NEW_ZScore_Konservatif': comparison[comparison['Label'] == 'Konservatif']['Total_Deteksi'].values[0],
        'Zero_Detection_Blocks': zero_blok
    }
    pd.DataFrame([summary]).to_csv(output_dir / 'summary.csv', index=False)
    
    print(f'\nResults saved to: {output_dir}')
    
    return comparison, df_new

if __name__ == '__main__':
    comparison, df_new = main()
