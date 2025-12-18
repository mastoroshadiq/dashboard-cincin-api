"""
Analisis Overlap Deteksi Antar Preset
=====================================
Membandingkan hasil deteksi dari 3 preset (Konservatif, Standar, Agresif)
untuk melihat overlap dan potensi Consensus Voting.
"""
import sys
sys.path.insert(0, 'src')

import pandas as pd
import numpy as np
from pathlib import Path
from src.ingestion import load_and_clean_data
from src.clustering import run_cincin_api_algorithm
from config import CINCIN_API_CONFIG, CINCIN_API_PRESETS

# Output directory
output_dir = Path('data/output/preset_overlap_analysis')
output_dir.mkdir(parents=True, exist_ok=True)

def run_preset_comparison(divisi='AME_II'):
    """Run all 3 presets and compare results."""
    
    print('=' * 70)
    print('ANALISIS OVERLAP DETEKSI ANTAR PRESET')
    print('=' * 70)
    
    # Load data
    print('\n[1/4] Loading data...')
    if divisi == 'AME_II':
        df = load_and_clean_data(Path('data/input/tabelNDREnew.csv'))
    else:
        df = load_and_clean_data(Path('data/input/AME_IV.csv'))
    
    print(f'  Total pohon: {len(df):,}')
    
    # Run each preset
    results = {}
    presets = ['konservatif', 'standar', 'agresif']
    
    print('\n[2/4] Running all presets...')
    for preset_name in presets:
        preset_config = CINCIN_API_PRESETS.get(preset_name, {})
        final_config = {**CINCIN_API_CONFIG, **preset_config}
        
        print(f'\n  Running {preset_name.upper()}...')
        print(f'    Threshold: {final_config["threshold_min"]*100:.0f}% - {final_config["threshold_max"]*100:.0f}%')
        
        df_classified, metadata = run_cincin_api_algorithm(
            df.copy(),
            auto_tune=True,
            config_override=final_config
        )
        
        results[preset_name] = {
            'df': df_classified,
            'metadata': metadata,
            'threshold': metadata.get('optimal_threshold', 0)
        }
        
        # Count by status
        merah = len(df_classified[df_classified['Status_Risiko'].str.contains('MERAH', na=False)])
        oranye = len(df_classified[df_classified['Status_Risiko'].str.contains('ORANYE', na=False)])
        kuning = len(df_classified[df_classified['Status_Risiko'].str.contains('KUNING', na=False)])
        hijau = len(df_classified[df_classified['Status_Risiko'].str.contains('HIJAU', na=False)])
        
        print(f'    Optimal Threshold: {results[preset_name]["threshold"]*100:.0f}%')
        print(f'    MERAH: {merah:,}  ORANYE: {oranye:,}  KUNING: {kuning:,}  HIJAU: {hijau:,}')
        
        results[preset_name]['counts'] = {
            'merah': merah,
            'oranye': oranye,
            'kuning': kuning,
            'hijau': hijau
        }
    
    # Analyze overlap
    print('\n[3/4] Analyzing overlap...')
    
    # Create merged DataFrame with all preset results
    df_merged = df[['Blok', 'N_BARIS', 'N_POKOK']].copy()
    
    for preset_name in presets:
        df_preset = results[preset_name]['df']
        # Create unique key
        df_preset['key'] = df_preset['Blok'].astype(str) + '_' + df_preset['N_BARIS'].astype(str) + '_' + df_preset['N_POKOK'].astype(str)
        df_merged['key'] = df_merged['Blok'].astype(str) + '_' + df_merged['N_BARIS'].astype(str) + '_' + df_merged['N_POKOK'].astype(str)
        
        # Map status
        status_map = df_preset.set_index('key')['Status_Risiko'].to_dict()
        df_merged[f'status_{preset_name}'] = df_merged['key'].map(status_map)
        
        # Is MERAH?
        df_merged[f'is_merah_{preset_name}'] = df_merged[f'status_{preset_name}'].str.contains('MERAH', na=False)
    
    # Count overlap
    df_merged['merah_count'] = (
        df_merged['is_merah_konservatif'].astype(int) +
        df_merged['is_merah_standar'].astype(int) +
        df_merged['is_merah_agresif'].astype(int)
    )
    
    # Categorize
    merah_all_3 = len(df_merged[df_merged['merah_count'] == 3])
    merah_2_of_3 = len(df_merged[df_merged['merah_count'] == 2])
    merah_1_only = len(df_merged[df_merged['merah_count'] == 1])
    merah_none = len(df_merged[df_merged['merah_count'] == 0])
    
    print('\n' + '=' * 70)
    print('HASIL ANALISIS OVERLAP')
    print('=' * 70)
    
    print('\n📊 DETEKSI PER PRESET:')
    print('-' * 50)
    for preset_name in presets:
        counts = results[preset_name]['counts']
        thresh = results[preset_name]['threshold'] * 100
        print(f'  {preset_name.upper():12} (Thresh {thresh:.0f}%): MERAH = {counts["merah"]:,}')
    
    print('\n📈 OVERLAP ANALYSIS:')
    print('-' * 50)
    print(f'  MERAH di SEMUA 3 preset:     {merah_all_3:>8,} pohon (HIGH CONFIDENCE)')
    print(f'  MERAH di 2 dari 3 preset:    {merah_2_of_3:>8,} pohon (MEDIUM CONFIDENCE)')
    print(f'  MERAH di 1 preset saja:      {merah_1_only:>8,} pohon (LOW CONFIDENCE)')
    print(f'  Tidak MERAH di preset apapun:{merah_none:>8,} pohon')
    
    print('\n💡 REKOMENDASI:')
    print('-' * 50)
    total_merah_agresif = results['agresif']['counts']['merah']
    reduction_pct = (1 - merah_all_3 / total_merah_agresif) * 100 if total_merah_agresif > 0 else 0
    
    print(f'  Menggunakan Consensus Voting (≥2 preset):')
    print(f'    Dari {total_merah_agresif:,} → {merah_all_3 + merah_2_of_3:,} MERAH')
    print(f'    Reduksi: {total_merah_agresif - (merah_all_3 + merah_2_of_3):,} pohon ({reduction_pct:.1f}%)')
    
    print('\n  Menggunakan Strict Consensus (SEMUA 3 preset):')
    print(f'    Dari {total_merah_agresif:,} → {merah_all_3:,} MERAH')
    strict_reduction = (1 - merah_all_3 / total_merah_agresif) * 100 if total_merah_agresif > 0 else 0
    print(f'    Reduksi: {total_merah_agresif - merah_all_3:,} pohon ({strict_reduction:.1f}%)')
    
    # Save results
    print('\n[4/4] Saving results...')
    df_merged.to_csv(output_dir / f'preset_overlap_{divisi}.csv', index=False)
    print(f'  Saved to: {output_dir / f"preset_overlap_{divisi}.csv"}')
    
    return results, df_merged

if __name__ == '__main__':
    run_preset_comparison('AME_II')
