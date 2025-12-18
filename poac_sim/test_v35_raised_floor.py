"""
POAC v3.5 Test - Raise the Floor Strategy
==========================================
Testing with raised floor values and Intersection voting (min_votes=2)
Target: 4,500 - 8,000 pohon
"""
import sys
sys.path.insert(0, 'src')

import pandas as pd
from pathlib import Path
from datetime import datetime
from src.ingestion import load_and_clean_data
from src.clustering import (
    calculate_percentile_rank,
    simulate_thresholds,
    find_optimal_threshold,
    classify_trees_with_clustering,
    apply_consensus_voting
)
from config import CINCIN_API_CONFIG, CINCIN_API_PRESETS

# Constants
GT_TOTAL_GANO = 5969
TARGET_LOW = 4500
TARGET_HIGH = 8000

# Output
timestamp = datetime.now().strftime("%Y%m%d_%H%M")
output_dir = Path(f'data/output/v35_raised_floor_{timestamp}')
output_dir.mkdir(parents=True, exist_ok=True)

def main():
    print('=' * 70)
    print('POAC v3.5 - RAISE THE FLOOR STRATEGY')
    print('=' * 70)
    
    print('\n[CONFIG v3.5 - RAISED FLOOR]')
    for preset in ['konservatif', 'standar', 'agresif']:
        p = CINCIN_API_PRESETS[preset]
        print(f'  {preset}: {p["threshold_min"]*100:.0f}% - {p["threshold_max"]*100:.0f}%')
    
    # Load data
    print('\n[1/3] Loading data...')
    df = load_and_clean_data(Path('data/input/tabelNDREnew.csv'))
    print(f'  Total: {len(df):,} pohon')
    
    # Run all presets
    print('\n[2/3] Running presets with GRADIENT (Kneedle)...')
    results = {}
    
    for preset_name in ['konservatif', 'standar', 'agresif']:
        preset_config = CINCIN_API_PRESETS.get(preset_name, {})
        final_config = {**CINCIN_API_CONFIG, **preset_config}
        
        print(f'\n  {preset_name.upper()}:')
        print(f'    Range: {final_config["threshold_min"]*100:.0f}% - {final_config["threshold_max"]*100:.0f}%')
        
        df_ranked = calculate_percentile_rank(df.copy())
        
        sim_df = simulate_thresholds(
            df_ranked,
            min_threshold=final_config['threshold_min'],
            max_threshold=final_config['threshold_max'],
            step=final_config['threshold_step'],
            min_sick_neighbors=final_config['min_sick_neighbors']
        )
        
        optimal_threshold = find_optimal_threshold(sim_df, method='gradient')
        print(f'    Kneedle Threshold: {optimal_threshold*100:.0f}%')
        
        df_classified = classify_trees_with_clustering(
            df_ranked,
            optimal_threshold,
            final_config['min_sick_neighbors']
        )
        
        merah = len(df_classified[df_classified['Status_Risiko'].str.contains('MERAH', na=False)])
        print(f'    MERAH: {merah:,}')
        
        results[preset_name] = df_classified
    
    # Consensus Voting (min_votes=2)
    print('\n[3/3] Applying Consensus Voting (min_votes=2)...')
    df_consensus = apply_consensus_voting(results, min_votes=2)
    approved = len(df_consensus[df_consensus['consensus_status'] == 'APPROVED'])
    
    # Results
    print('\n' + '=' * 70)
    print('v3.5 RESULTS')
    print('=' * 70)
    
    print(f'\nGround Truth: {GT_TOTAL_GANO:,}')
    print(f'Target Range: {TARGET_LOW:,} - {TARGET_HIGH:,}')
    
    pct = (approved - GT_TOTAL_GANO) / GT_TOTAL_GANO * 100
    
    print(f'\n>>> RESULT: {approved:,} APPROVED ({pct:+.0f}% vs GT)')
    
    if TARGET_LOW <= approved <= TARGET_HIGH:
        print('\n✅ SUCCESS! Result within target range!')
        print('>>> LOCK & DEPLOY')
    elif approved < TARGET_LOW:
        print('\n❌ Still under-detect. Need more tuning.')
    else:
        print('\n⚠️ Over-detect. Need adjustment.')
    
    # Vote distribution
    print('\nVote Distribution:')
    for v in [3, 2, 1, 0]:
        count = len(df_consensus[df_consensus['vote_count'] == v])
        print(f'  {v} votes: {count:,}')
    
    # Save
    df_consensus.to_csv(output_dir / 'v35_results.csv', index=False)
    print(f'\nResults saved to: {output_dir}')
    
    return approved

if __name__ == '__main__':
    main()
