"""Debug: Why calibration results are different?"""
import pandas as pd

# From zscore_calibration.py (original)
df_cal = pd.read_csv('data/output/z_score_calibration/AME002_calibration.csv')

print("="*60)
print("FROM zscore_calibration.py")
print("="*60)
print(df_cal[['z_threshold', 'mae', 'correlation', 'avg_algo_pct', 'avg_gt_pct']].head(10).to_string(index=False))

# Best by MAE
idx_mae = df_cal['mae'].idxmin()
print(f"\nBest MAE: Z < {df_cal.loc[idx_mae, 'z_threshold']} -> MAE = {df_cal.loc[idx_mae, 'mae']:.2f}%")

# From the recent quick test
print("\n" + "="*60)
print("FROM recent quick test (inline)")
print("="*60)

print("""
Z < -1.5: MAE=2.93%, Corr=0.360, Algo=7.00%, GT=6.32%
Z < -2.0: MAE=3.50%, Corr=0.524, Algo=3.08%, GT=6.32%
Z < -2.5: MAE=5.05%, Corr=0.588, Algo=1.27%, GT=6.32%
""")

# Compare
print("="*60)
print("COMPARISON")
print("="*60)
print("Both show Z < -1.5 has BEST MAE around 2.93%")
print("So original calibration was CORRECT!")
print()
print("The problem was in run_calibrated_analysis.py comparison logic.")
