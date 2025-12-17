"""
SPH Gap Analysis - Quick Report
Using pre-calculated data from dashboard
"""
import json

# Load summary data
with open('data/output/comprehensive_dashboard/data/executive_summary.json') as f:
    data = json.load(f)

ame2 = data['AME002']
ame4 = data['AME004']

print('=' * 60)
print('SPH GAP ANALYSIS REPORT')
print('=' * 60)

print('\n📊 AME II (Reference - Low SPH Gap):')
print(f'   SPH Drone:     {ame2["avg_sph_drone"]:.0f}')
print(f'   SPH GT:        {ame2["avg_sph_gt"]:.0f}')
sph_gap_2 = ame2["avg_sph_drone"] - ame2["avg_sph_gt"]
sph_gap_2_pct = sph_gap_2 / ame2["avg_sph_gt"] * 100 if ame2["avg_sph_gt"] > 0 else 0
print(f'   Gap:           {sph_gap_2:+.0f} ({sph_gap_2_pct:+.1f}%)')

print('\n📊 AME IV (High SPH Gap - ANOMALY):')
print(f'   SPH Drone:     {ame4["avg_sph_drone"]:.0f}')
print(f'   SPH GT:        {ame4["avg_sph_gt"]:.0f}')
sph_gap_4 = ame4["avg_sph_drone"] - ame4["avg_sph_gt"]
sph_gap_4_pct = sph_gap_4 / ame4["avg_sph_gt"] * 100 if ame4["avg_sph_gt"] > 0 else 0
print(f'   Gap:           {sph_gap_4:+.0f} ({sph_gap_4_pct:+.1f}%)')

print('\n' + '=' * 60)
print('🔍 ROOT CAUSE ANALYSIS')
print('=' * 60)

print('\n📋 Tree Count Comparison:')
print(f'   AME II: Drone={ame2["drone_total"]:,} GT={ame2["gt_total"]:,} Gap={ame2["drone_total"]-ame2["gt_total"]:+,}')
print(f'   AME IV: Drone={ame4["drone_total"]:,} GT={ame4["gt_total"]:,} Gap={ame4["drone_total"]-ame4["gt_total"]:+,}')

print('\n📐 Ha (Luas) Analysis:')
# Calculate implied Ha
ha_implied_drone_ame4 = ame4["drone_total"] / ame4["avg_sph_drone"] if ame4["avg_sph_drone"] > 0 else 0
ha_implied_gt_ame4 = ame4["gt_total"] / ame4["avg_sph_gt"] if ame4["avg_sph_gt"] > 0 else 0

print(f'   AME IV Implied Ha (Drone): {ha_implied_drone_ame4:.1f} Ha')
print(f'   AME IV Implied Ha (GT):    {ha_implied_gt_ame4:.1f} Ha')
print(f'   Ha Gap:                    {ha_implied_drone_ame4 - ha_implied_gt_ame4:+.1f} Ha')

print('\n' + '=' * 60)
print('⚠️  HYPOTHESIS')
print('=' * 60)

print('''
   SPH = Total Pohon / Luas (Ha)
   
   If SPH Drone >> SPH GT, possible causes:
   
   1. Ha yang digunakan drone LEBIH KECIL dari Ha aktual
      → Ini menyebabkan SPH menjadi INFLATED
      
   2. Definisi luas berbeda:
      - Drone: mungkin menggunakan scanned area
      - GT: menggunakan planted area total
      
   3. Boundary blok yang berbeda antara drone dan GT
''')

print('=' * 60)
print('💡 REKOMENDASI')
print('=' * 60)

print('''
   ❌ JANGAN gunakan SPH Drone AME IV untuk:
      - Pelaporan ke manajemen
      - Keputusan operasional
      - Perbandingan dengan benchmark
      
   ✅ GUNAKAN SPH dari Ground Truth sebagai acuan
   
   🔧 LANGKAH PERBAIKAN:
      1. Audit definisi Ha di data drone AME IV
      2. Verifikasi boundary blok dengan GIS
      3. Sinkronisasi definisi luas planted area
''')
