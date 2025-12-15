"""Display calibration analysis results"""
import pandas as pd

df = pd.read_csv('data/output/calibrated_analysis/summary.csv')

print("="*80)
print("CALIBRATED ANALYSIS RESULTS")
print("="*80)

print("\n" + "-"*80)
print(f"{'Divisi':<10} {'Std Thresh':<12} {'Cal Thresh':<12} {'MAE Std':>10} {'MAE Cal':>10} {'Corr Std':>10} {'Corr Cal':>10}")
print("-"*80)

for _, row in df.iterrows():
    print(f"{row['divisi']:<10} {row['threshold_std']:<12} {row['threshold_cal']:<12} {row['mae_std']:>9.2f}% {row['mae_cal']:>9.2f}% {row['corr_std']:>10.3f} {row['corr_cal']:>10.3f}")

print("-"*80)

print("\n" + "="*80)
print("IMPROVEMENT ANALYSIS")
print("="*80)

for _, row in df.iterrows():
    imp_mae = row['improvement_mae']
    imp_corr = row['improvement_corr']
    
    print(f"\n{row['divisi']}:")
    print(f"  Threshold: {row['threshold_std']} -> {row['threshold_cal']}")
    print(f"  MAE Improvement:  {imp_mae:+.2f}% {'✅ BETTER' if imp_mae > 0 else '❌ WORSE'}")
    print(f"  Corr Improvement: {imp_corr:+.3f} {'✅ BETTER' if imp_corr > 0 else '❌ WORSE'}")
