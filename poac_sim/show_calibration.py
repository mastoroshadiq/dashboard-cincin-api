"""Show calibration results"""
import pandas as pd

df1 = pd.read_csv('data/output/z_score_calibration/AME002_calibration.csv')
df2 = pd.read_csv('data/output/z_score_calibration/AME004_calibration.csv')

print("="*70)
print("Z-SCORE CALIBRATION RESULTS")
print("="*70)

print("\nAME002 (AME II):")
print(df1.to_string(index=False))

print("\n\nAME004 (AME IV):")
print(df2.to_string(index=False))

# Find optimal
print("\n" + "="*70)
print("OPTIMAL THRESHOLDS")
print("="*70)

for name, df in [("AME002", df1), ("AME004", df2)]:
    idx_mae = df["mae"].idxmin()
    idx_corr = df["correlation"].idxmax()
    idx_bias = abs(df["bias"]).idxmin()
    
    print(f"\n{name}:")
    print(f"  Min MAE:  Z < {df.loc[idx_mae, 'z_threshold']:.1f} (MAE={df.loc[idx_mae, 'mae']:.2f}%)")
    print(f"  Max Corr: Z < {df.loc[idx_corr, 'z_threshold']:.1f} (r={df.loc[idx_corr, 'correlation']:.3f})")
    print(f"  Min Bias: Z < {df.loc[idx_bias, 'z_threshold']:.1f} (bias={df.loc[idx_bias, 'bias']:+.2f}%)")
