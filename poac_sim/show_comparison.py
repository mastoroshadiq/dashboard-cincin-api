"""Show comparison summary"""
import pandas as pd

df_a_ame2 = pd.read_csv('data/output/option_comparison/AME002_option_a.csv')
df_b_ame2 = pd.read_csv('data/output/option_comparison/AME002_option_b.csv')
df_a_ame4 = pd.read_csv('data/output/option_comparison/AME004_option_a.csv')
df_b_ame4 = pd.read_csv('data/output/option_comparison/AME004_option_b.csv')

print("="*70)
print("COMPARISON: Option A vs Option B")
print("="*70)

print("\nAME II:")
a2_g3 = len(df_a_ame2[df_a_ame2["G_Status"]=="G3"])
a2_g2 = len(df_a_ame2[df_a_ame2["G_Status"]=="G2"])
b2_g3 = len(df_b_ame2[df_b_ame2["G_Status"]=="G3"])
b2_g2 = len(df_b_ame2[df_b_ame2["G_Status"]=="G2"])
print(f"  Option A: Total={len(df_a_ame2):,}, G3={a2_g3:,}, G2={a2_g2:,}")
print(f"  Option B: Total={len(df_b_ame2):,}, G3={b2_g3:,}, G2={b2_g2:,}")
print(f"  Difference: +{len(df_b_ame2)-len(df_a_ame2):,} trees, +{b2_g3-a2_g3:,} G3")

print("\nAME IV:")
a4_g3 = len(df_a_ame4[df_a_ame4["G_Status"]=="G3"])
a4_g2 = len(df_a_ame4[df_a_ame4["G_Status"]=="G2"])
b4_g3 = len(df_b_ame4[df_b_ame4["G_Status"]=="G3"])
b4_g2 = len(df_b_ame4[df_b_ame4["G_Status"]=="G2"])
print(f"  Option A: Total={len(df_a_ame4):,}, G3={a4_g3:,}, G2={a4_g2:,}")
print(f"  Option B: Total={len(df_b_ame4):,}, G3={b4_g3:,}, G2={b4_g2:,}")
print(f"  Difference: +{len(df_b_ame4)-len(df_a_ame4):,} trees, +{b4_g3-a4_g3:,} G3")

print("\n" + "-"*70)
print("YOUNG (Sisip) in Option B:")
print("-"*70)

young_ame2 = df_b_ame2[df_b_ame2["Category"]=="YOUNG"]
young_ame4 = df_b_ame4[df_b_ame4["Category"]=="YOUNG"]

print(f"AME II YOUNG: Total={len(young_ame2):,}")
print(f"  G3={len(young_ame2[young_ame2['G_Status']=='G3']):,}")
print(f"  G2={len(young_ame2[young_ame2['G_Status']=='G2']):,}")
print(f"  G1={len(young_ame2[young_ame2['G_Status']=='G1']):,}")

print(f"\nAME IV YOUNG: Total={len(young_ame4):,}")
print(f"  G3={len(young_ame4[young_ame4['G_Status']=='G3']):,}")
print(f"  G2={len(young_ame4[young_ame4['G_Status']=='G2']):,}")
print(f"  G1={len(young_ame4[young_ame4['G_Status']=='G1']):,}")
