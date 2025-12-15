"""COMPARE: Drone Data vs Ground Truth Excel - Write to file"""
import pandas as pd
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.ingestion import load_and_clean_data, load_ame_iv_data

# ============================================================
# LOAD GROUND TRUTH DATA
# ============================================================
xlsx_path = 'data/input/areal_inti_serangan_gano_AMEII_AMEIV.xlsx'
df_gt = pd.read_excel(xlsx_path, sheet_name='Sheet1', header=[0, 1])

# Flatten column names
df_gt.columns = ['DIVISI', 'BLOK', 'TAHUN_TANAM', 'LUAS_SD_2024', 'PENAMBAHAN', 
                 'LUAS_SD_2025', 'TANAM', 'SISIP', 'SISIP_KENTOSAN', 'TOTAL_PKK',
                 'SPH', 'STADIUM_12', 'STADIUM_34', 'TOTAL_GANO', 'SERANGAN_PCT']

df_gt = df_gt[df_gt['DIVISI'].isin(['AME002', 'AME004'])]

# ============================================================
# LOAD DRONE DATA
# ============================================================
df_drone_ame2 = load_and_clean_data('data/input/tabelNDREnew.csv')
df_drone_ame4 = load_ame_iv_data('data/input/AME_IV.csv')

# ============================================================
# WRITE COMPARISON TO FILE
# ============================================================
with open('drone_vs_gt_comparison.txt', 'w', encoding='utf-8') as f:
    f.write("="*70 + "\n")
    f.write("PERBANDINGAN: Data Drone vs Ground Truth Excel\n")
    f.write("="*70 + "\n")
    
    for divisi, df_drone in [('AME002', df_drone_ame2), ('AME004', df_drone_ame4)]:
        df_gt_div = df_gt[df_gt['DIVISI'] == divisi]
        
        # Ground Truth
        gt_tanam = df_gt_div['TANAM'].sum()
        gt_sisip = df_gt_div['SISIP'].sum() + df_gt_div['SISIP_KENTOSAN'].sum()
        gt_total = df_gt_div['TOTAL_PKK'].sum()
        
        # Drone
        drone_mature = len(df_drone[df_drone['Category'] == 'MATURE'])
        drone_young = len(df_drone[df_drone['Category'] == 'YOUNG'])
        drone_dead = len(df_drone[df_drone['Category'] == 'DEAD'])
        drone_empty = len(df_drone[df_drone['Category'] == 'EMPTY'])
        drone_total = len(df_drone)
        
        f.write(f"\n{'='*50}\n")
        f.write(f"{divisi}\n")
        f.write("="*50 + "\n")
        f.write(f"\n{'Kategori':<20} {'Ground Truth':>15} {'Drone':>15} {'Selisih':>15}\n")
        f.write("-"*65 + "\n")
        f.write(f"{'TANAM (=MATURE)':<20} {gt_tanam:>15,.0f} {drone_mature:>15,} {drone_mature - gt_tanam:>+15,.0f}\n")
        f.write(f"{'SISIP (=YOUNG)':<20} {gt_sisip:>15,.0f} {drone_young:>15,} {drone_young - gt_sisip:>+15,.0f}\n")
        f.write(f"{'MATI (=DEAD)':<20} {'N/A':>15} {drone_dead:>15,} {'':>15}\n")
        f.write(f"{'KOSONG (=EMPTY)':<20} {'N/A':>15} {drone_empty:>15,} {'':>15}\n")
        f.write("-"*65 + "\n")
        f.write(f"{'TOTAL_PKK':<20} {gt_total:>15,.0f} {drone_total:>15,} {drone_total - gt_total:>+15,.0f}\n")

    f.write("\n\n" + "="*70 + "\n")
    f.write("ANALISIS KESIMPULAN\n")
    f.write("="*70 + "\n")
    
    f.write("\nAME002 (AME II):\n")
    f.write("-"*50 + "\n")
    f.write("  - GT TANAM: 61,005 vs Drone MATURE: 94,201\n")
    f.write("    => Selisih +33,196 menunjukkan Drone mendeteksi lebih banyak\n")
    f.write("    => Kemungkinan: Tamb di drone masuk MATURE, atau ada pohon extra\n")
    f.write("\n")
    f.write("  - GT SISIP: 34,050 vs Drone YOUNG: 787\n")
    f.write("    => Selisih -33,263 menunjukkan banyak sisip TIDAK ter-tag di drone\n")
    f.write("    => Kemungkinan: Sisip sudah dewasa sehingga ter-classify MATURE\n")
    
    f.write("\n\nAME004 (AME IV):\n")
    f.write("-"*50 + "\n")
    f.write("  - GT TANAM: 51,967 vs Drone MATURE: 68,372\n")
    f.write("    => Selisih +16,405 menunjukkan Drone mendeteksi lebih banyak\n")
    f.write("\n")
    f.write("  - GT SISIP: 21,709 vs Drone YOUNG: 4,700\n")
    f.write("    => Selisih -17,009 menunjukkan banyak sisip tidak ter-tag YOUNG\n")

    f.write("\n\n" + "="*70 + "\n")
    f.write("REKOMENDASI\n")
    f.write("="*70 + "\n")
    f.write("\nKategorisasi drone 'MATURE' vs 'YOUNG' TIDAK reliable untuk\n")
    f.write("perbandingan dengan data buku (TANAM vs SISIP) karena:\n")
    f.write("\n")
    f.write("1. Label Keterangan drone tidak selalu akurat/lengkap\n")
    f.write("2. Sisip yang sudah tua (dewasa) akan ter-detect sebagai 'Pokok Utama'\n")
    f.write("3. Data buku (SISIP) adalah akumulatif, sementara drone hanya snapshot\n")
    f.write("\nUntuk Ghost Tree Audit, gunakan TOTAL_PKK dari ground truth Excel\n")
    f.write("untuk perbandingan yang lebih akurat.\n")

print("Results written to drone_vs_gt_comparison.txt")
