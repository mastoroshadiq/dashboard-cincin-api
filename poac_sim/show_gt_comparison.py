"""Show GT comparison for Option B"""
import pandas as pd

df2 = pd.read_csv('data/output/option_b_dashboard/AME002_gt_comparison.csv')
df4 = pd.read_csv('data/output/option_b_dashboard/AME004_gt_comparison.csv')

print("Option B - Ground Truth Comparison:")
print("="*60)

print("\nAME II:")
mae2 = abs(df2["detected_pct"] - df2["gt_pct"]).mean()
corr2 = df2["detected_pct"].corr(df2["gt_pct"])
print(f"  Blocks: {len(df2)}, MAE: {mae2:.2f}%, Corr: {corr2:.3f}")
print(f"  Algo Avg: {df2['detected_pct'].mean():.2f}%, GT Avg: {df2['gt_pct'].mean():.2f}%")

print("\nAME IV:")
mae4 = abs(df4["detected_pct"] - df4["gt_pct"]).mean()
corr4 = df4["detected_pct"].corr(df4["gt_pct"])
print(f"  Blocks: {len(df4)}, MAE: {mae4:.2f}%, Corr: {corr4:.3f}")
print(f"  Algo Avg: {df4['detected_pct'].mean():.2f}%, GT Avg: {df4['gt_pct'].mean():.2f}%")
