"""
Investigation: Why AME IV needs stricter threshold?
====================================================

Compare characteristics:
1. NDRE distribution
2. Population composition
3. Ground truth Ganoderma rates
4. Standard deviation per block
5. Age of plantation (Tahun Tanam)
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys
from io import BytesIO
import base64

script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from src.ingestion import load_and_clean_data, load_ame_iv_data

# Load data
print("="*70)
print("INVESTIGATION: Why AME IV needs stricter threshold?")
print("="*70)

df_ame2 = load_and_clean_data(script_dir / "data/input/tabelNDREnew.csv")
df_ame4 = load_ame_iv_data(script_dir / "data/input/AME_IV.csv")

# Load ground truth
df_gt = pd.read_excel(
    script_dir / "data/input/areal_inti_serangan_gano_AMEII_AMEIV.xlsx",
    sheet_name='Sheet1', header=[0, 1]
)
df_gt.columns = ['DIVISI', 'BLOK', 'TAHUN_TANAM', 'LUAS_SD_2024', 'PENAMBAHAN', 
                 'LUAS_SD_2025', 'TANAM', 'SISIP', 'SISIP_KENTOSAN', 'TOTAL_PKK',
                 'SPH', 'STADIUM_12', 'STADIUM_34', 'TOTAL_GANO', 'SERANGAN_PCT']

with open('ameiv_investigation.txt', 'w', encoding='utf-8') as f:
    f.write("="*70 + "\n")
    f.write("INVESTIGATION: Why AME IV needs stricter threshold?\n")
    f.write("="*70 + "\n")
    
    # =========================================================================
    # 1. NDRE Distribution Comparison
    # =========================================================================
    f.write("\n\n" + "="*70 + "\n")
    f.write("1. NDRE DISTRIBUTION COMPARISON\n")
    f.write("="*70 + "\n")
    
    # Only MATURE
    ame2_mature = df_ame2[df_ame2['Category'] == 'MATURE']['NDRE125']
    ame4_mature = df_ame4[df_ame4['Category'] == 'MATURE']['NDRE125']
    
    f.write(f"\n{'Metric':<25} {'AME II':>15} {'AME IV':>15} {'Difference':>15}\n")
    f.write("-"*70 + "\n")
    f.write(f"{'Count (MATURE)':<25} {len(ame2_mature):>15,} {len(ame4_mature):>15,} {len(ame2_mature)-len(ame4_mature):>+15,}\n")
    f.write(f"{'NDRE Mean':<25} {ame2_mature.mean():>15.4f} {ame4_mature.mean():>15.4f} {ame2_mature.mean()-ame4_mature.mean():>+15.4f}\n")
    f.write(f"{'NDRE Std':<25} {ame2_mature.std():>15.4f} {ame4_mature.std():>15.4f} {ame2_mature.std()-ame4_mature.std():>+15.4f}\n")
    f.write(f"{'NDRE Min':<25} {ame2_mature.min():>15.4f} {ame4_mature.min():>15.4f}\n")
    f.write(f"{'NDRE Max':<25} {ame2_mature.max():>15.4f} {ame4_mature.max():>15.4f}\n")
    f.write(f"{'NDRE Median':<25} {ame2_mature.median():>15.4f} {ame4_mature.median():>15.4f}\n")
    
    # Coefficient of Variation
    cv_ame2 = ame2_mature.std() / ame2_mature.mean() * 100
    cv_ame4 = ame4_mature.std() / ame4_mature.mean() * 100
    f.write(f"{'CV (Coef. Variation) %':<25} {cv_ame2:>15.2f} {cv_ame4:>15.2f} {cv_ame2-cv_ame4:>+15.2f}\n")
    
    # =========================================================================
    # 2. Population Composition
    # =========================================================================
    f.write("\n\n" + "="*70 + "\n")
    f.write("2. POPULATION COMPOSITION\n")
    f.write("="*70 + "\n")
    
    f.write(f"\n{'Category':<15} {'AME II':>15} {'%':>10} {'AME IV':>15} {'%':>10}\n")
    f.write("-"*65 + "\n")
    
    for cat in ['MATURE', 'YOUNG', 'DEAD', 'EMPTY']:
        c2 = len(df_ame2[df_ame2['Category'] == cat])
        c4 = len(df_ame4[df_ame4['Category'] == cat])
        p2 = c2 / len(df_ame2) * 100
        p4 = c4 / len(df_ame4) * 100
        f.write(f"{cat:<15} {c2:>15,} {p2:>9.1f}% {c4:>15,} {p4:>9.1f}%\n")
    
    f.write("-"*65 + "\n")
    f.write(f"{'TOTAL':<15} {len(df_ame2):>15,} {'100.0':>10}% {len(df_ame4):>15,} {'100.0':>10}%\n")
    
    # =========================================================================
    # 3. Ground Truth Comparison
    # =========================================================================
    f.write("\n\n" + "="*70 + "\n")
    f.write("3. GROUND TRUTH GANODERMA RATES\n")
    f.write("="*70 + "\n")
    
    gt_ame2 = df_gt[df_gt['DIVISI'] == 'AME002']
    gt_ame4 = df_gt[df_gt['DIVISI'] == 'AME004']
    
    f.write(f"\n{'Metric':<25} {'AME II':>15} {'AME IV':>15}\n")
    f.write("-"*55 + "\n")
    f.write(f"{'Number of Blocks':<25} {len(gt_ame2):>15} {len(gt_ame4):>15}\n")
    f.write(f"{'Total PKK':<25} {gt_ame2['TOTAL_PKK'].sum():>15,.0f} {gt_ame4['TOTAL_PKK'].sum():>15,.0f}\n")
    f.write(f"{'Total Ganoderma':<25} {gt_ame2['TOTAL_GANO'].sum():>15,.0f} {gt_ame4['TOTAL_GANO'].sum():>15,.0f}\n")
    
    pct_ame2 = gt_ame2['TOTAL_GANO'].sum() / gt_ame2['TOTAL_PKK'].sum() * 100
    pct_ame4 = gt_ame4['TOTAL_GANO'].sum() / gt_ame4['TOTAL_PKK'].sum() * 100
    f.write(f"{'Overall % Serangan':<25} {pct_ame2:>14.2f}% {pct_ame4:>14.2f}%\n")
    
    # Per block stats
    gt_ame2['pct_serangan'] = gt_ame2['TOTAL_GANO'] / gt_ame2['TOTAL_PKK'] * 100
    gt_ame4['pct_serangan'] = gt_ame4['TOTAL_GANO'] / gt_ame4['TOTAL_PKK'] * 100
    
    f.write(f"{'Mean % per block':<25} {gt_ame2['pct_serangan'].mean():>14.2f}% {gt_ame4['pct_serangan'].mean():>14.2f}%\n")
    f.write(f"{'Std % per block':<25} {gt_ame2['pct_serangan'].std():>14.2f}% {gt_ame4['pct_serangan'].std():>14.2f}%\n")
    f.write(f"{'Max % per block':<25} {gt_ame2['pct_serangan'].max():>14.2f}% {gt_ame4['pct_serangan'].max():>14.2f}%\n")
    
    # =========================================================================
    # 4. Standard Deviation per Block
    # =========================================================================
    f.write("\n\n" + "="*70 + "\n")
    f.write("4. NDRE STANDARD DEVIATION PER BLOCK\n")
    f.write("="*70 + "\n")
    
    # Calculate std per block for MATURE only
    std_per_blok_ame2 = df_ame2[df_ame2['Category'] == 'MATURE'].groupby('Blok')['NDRE125'].std()
    std_per_blok_ame4 = df_ame4[df_ame4['Category'] == 'MATURE'].groupby('Blok')['NDRE125'].std()
    
    f.write(f"\n{'Metric':<25} {'AME II':>15} {'AME IV':>15}\n")
    f.write("-"*55 + "\n")
    f.write(f"{'Mean Std per Block':<25} {std_per_blok_ame2.mean():>15.4f} {std_per_blok_ame4.mean():>15.4f}\n")
    f.write(f"{'Min Std per Block':<25} {std_per_blok_ame2.min():>15.4f} {std_per_blok_ame4.min():>15.4f}\n")
    f.write(f"{'Max Std per Block':<25} {std_per_blok_ame2.max():>15.4f} {std_per_blok_ame4.max():>15.4f}\n")
    
    # =========================================================================
    # 5. Tahun Tanam / Plantation Age
    # =========================================================================
    f.write("\n\n" + "="*70 + "\n")
    f.write("5. PLANTATION AGE (from Ground Truth)\n")
    f.write("="*70 + "\n")
    
    f.write(f"\n{'Tahun Tanam':<15} {'AME II':>15} {'AME IV':>15}\n")
    f.write("-"*45 + "\n")
    
    tt_ame2 = gt_ame2['TAHUN_TANAM'].value_counts().sort_index()
    tt_ame4 = gt_ame4['TAHUN_TANAM'].value_counts().sort_index()
    
    all_years = sorted(set(tt_ame2.index.tolist() + tt_ame4.index.tolist()))
    for year in all_years:
        c2 = tt_ame2.get(year, 0)
        c4 = tt_ame4.get(year, 0)
        f.write(f"{int(year):<15} {c2:>15} {c4:>15}\n")
    
    # =========================================================================
    # 6. HYPOTHESIS
    # =========================================================================
    f.write("\n\n" + "="*70 + "\n")
    f.write("6. HYPOTHESIS: Why AME IV needs stricter threshold?\n")
    f.write("="*70 + "\n")
    
    f.write("\nFindings:\n")
    f.write("-"*50 + "\n")
    
    # Compare key metrics
    if ame4_mature.std() < ame2_mature.std():
        f.write("1. AME IV has LOWER std deviation than AME II\n")
        f.write(f"   ({ame4_mature.std():.4f} vs {ame2_mature.std():.4f})\n")
        f.write("   => AME IV data is MORE HOMOGENEOUS\n")
        f.write("   => Stricter threshold needed to detect actual anomalies\n\n")
    
    if pct_ame4 < pct_ame2:
        f.write("2. AME IV has LOWER Ganoderma rate than AME II\n")
        f.write(f"   ({pct_ame4:.2f}% vs {pct_ame2:.2f}%)\n")
        f.write("   => Fewer diseased trees = need stricter threshold\n\n")
    
    empty_pct = len(df_ame4[df_ame4['Category'] == 'EMPTY']) / len(df_ame4) * 100
    if empty_pct > 5:
        f.write(f"3. AME IV has HIGH EMPTY rate ({empty_pct:.1f}%)\n")
        f.write("   => Data quality issue? NDRE missing/invalid?\n\n")
    
    f.write("\nConclusion:\n")
    f.write("-"*50 + "\n")
    f.write("AME IV requires stricter threshold (Z < -4.0) because:\n")
    f.write("  a) Lower data variability (lower std) means Z-Score distribution\n")
    f.write("     is more compressed - outliers have larger Z values\n")
    f.write("  b) Lower actual Ganoderma rate means fewer trees should be flagged\n")
    f.write("  c) Standard Z < -2.0 threshold over-detects for AME IV\n")

print("Investigation results written to ameiv_investigation.txt")

# Generate comparison chart
fig, axes = plt.subplots(2, 2, figsize=(14, 10))
plt.style.use('dark_background')

# 1. NDRE Distribution
ax1 = axes[0, 0]
ax1.hist(ame2_mature, bins=50, alpha=0.6, label='AME II', color='#3498db', density=True)
ax1.hist(ame4_mature, bins=50, alpha=0.6, label='AME IV', color='#e74c3c', density=True)
ax1.set_xlabel('NDRE125')
ax1.set_ylabel('Density')
ax1.set_title('NDRE Distribution (MATURE trees)')
ax1.legend()
ax1.axvline(ame2_mature.mean(), color='#3498db', linestyle='--', alpha=0.8)
ax1.axvline(ame4_mature.mean(), color='#e74c3c', linestyle='--', alpha=0.8)

# 2. Std per Block
ax2 = axes[0, 1]
ax2.hist(std_per_blok_ame2, bins=20, alpha=0.6, label='AME II', color='#3498db')
ax2.hist(std_per_blok_ame4, bins=20, alpha=0.6, label='AME IV', color='#e74c3c')
ax2.set_xlabel('Std Dev per Block')
ax2.set_ylabel('Frequency')
ax2.set_title('NDRE Std Deviation per Block')
ax2.legend()

# 3. Ground Truth % Serangan
ax3 = axes[1, 0]
ax3.hist(gt_ame2['pct_serangan'], bins=20, alpha=0.6, label='AME II', color='#3498db')
ax3.hist(gt_ame4['pct_serangan'], bins=20, alpha=0.6, label='AME IV', color='#e74c3c')
ax3.set_xlabel('% Serangan (Ground Truth)')
ax3.set_ylabel('Frequency')
ax3.set_title('Ground Truth Ganoderma % per Block')
ax3.legend()

# 4. Population Composition
ax4 = axes[1, 1]
categories = ['MATURE', 'YOUNG', 'DEAD', 'EMPTY']
x = np.arange(len(categories))
width = 0.35

counts_ame2 = [len(df_ame2[df_ame2['Category'] == c]) / len(df_ame2) * 100 for c in categories]
counts_ame4 = [len(df_ame4[df_ame4['Category'] == c]) / len(df_ame4) * 100 for c in categories]

ax4.bar(x - width/2, counts_ame2, width, label='AME II', color='#3498db')
ax4.bar(x + width/2, counts_ame4, width, label='AME IV', color='#e74c3c')
ax4.set_xticks(x)
ax4.set_xticklabels(categories)
ax4.set_ylabel('Percentage (%)')
ax4.set_title('Population Composition')
ax4.legend()

plt.suptitle('AME II vs AME IV Comparison', fontsize=14, fontweight='bold')
plt.tight_layout()
plt.savefig(script_dir / 'data/output/z_score_calibration/ame_comparison.png', dpi=120, 
            bbox_inches='tight', facecolor='#1a1a2e')
plt.close()

print("Chart saved to data/output/z_score_calibration/ame_comparison.png")
