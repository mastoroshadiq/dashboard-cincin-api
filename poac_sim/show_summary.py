"""Display summary results"""
import pandas as pd

df = pd.read_csv('data/output/population_analysis/summary_comparison.csv')

print("="*90)
print("SUMMARY: Population Segmentation Analysis - 3 Conditions")
print("="*90)

print("\n" + "-"*90)
print(f"{'Condition':<35} {'Divisi':<8} {'Trees':>10} {'Corr (r)':>10} {'MAE':>10} {'Algo%':>10} {'GT%':>10}")
print("-"*90)

for _, row in df.iterrows():
    cond_short = row['condition_name'].replace('Condition ', 'Cond ').replace(': ', ' - ')[:32]
    print(f"{cond_short:<35} {row['divisi']:<8} {row['total_analyzed']:>10,} {row['correlation']:>10.3f} {row['mae']:>9.2f}% {row['avg_algo_pct']:>9.2f}% {row['avg_gt_pct']:>9.2f}%")

print("-"*90)

print("\n\nINTERPRETASI:")
print("="*90)

# Group by condition
for cond in df['condition'].unique():
    df_cond = df[df['condition'] == cond]
    avg_corr = df_cond['correlation'].mean()
    avg_mae = df_cond['mae'].mean()
    print(f"\n{df_cond['condition_name'].iloc[0]}:")
    print(f"  - Average Correlation: {avg_corr:.3f}")
    print(f"  - Average MAE: {avg_mae:.2f}%")
    
    if avg_corr > 0.5:
        print("  => BAIK: Korelasi positif kuat dengan ground truth")
    elif avg_corr > 0:
        print("  => CUKUP: Korelasi positif lemah")
    else:
        print("  => BURUK: Tidak berkorelasi dengan ground truth")
