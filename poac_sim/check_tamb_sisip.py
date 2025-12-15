"""Compare Tamb vs Sisip - NDRE Analysis"""
import pandas as pd
import numpy as np

df = pd.read_csv('data/input/tabelNDREnew.csv')

# Convert ndre125 to numeric
df['ndre125_num'] = pd.to_numeric(df['ndre125'], errors='coerce')

# Output to file
with open('tamb_sisip_analysis.txt', 'w', encoding='utf-8') as f:
    f.write("="*70 + "\n")
    f.write("PERBANDINGAN TAMB vs SISIP - Analisis NDRE\n")
    f.write("="*70 + "\n")

    # Define categories
    pokok_mask = df['ket'] == 'Pokok Utama'
    tamb_mask = df['ket'] == 'Tamb'
    sisip_mask = df['ket'].str.contains('Sisip', case=False, na=False)

    # Get data
    pokok = df[pokok_mask]
    tamb = df[tamb_mask]
    sisip = df[sisip_mask]

    f.write(f"\n{'Kategori':<20} {'Count':>10} {'NDRE Mean':>12} {'NDRE Std':>12} {'NDRE Min':>12} {'NDRE Max':>12}\n")
    f.write("-"*80 + "\n")

    for name, data in [('Pokok Utama', pokok), ('Tamb', tamb), ('Sisip (all)', sisip)]:
        ndre = data['ndre125_num']
        f.write(f"{name:<20} {len(data):>10,} {ndre.mean():>12.4f} {ndre.std():>12.4f} {ndre.min():>12.4f} {ndre.max():>12.4f}\n")

    # Detail per Sisip type
    f.write("\n--- Detail per Tipe Sisip ---\n")
    sisip_types = df[sisip_mask]['ket'].unique()
    for stype in sorted(sisip_types):
        data = df[df['ket'] == stype]
        ndre = data['ndre125_num']
        f.write(f"  {stype:<18} {len(data):>6,} NDRE={ndre.mean():.4f}\n")

    # Sample data comparison
    f.write("\n" + "="*70 + "\n")
    f.write("SAMPLE DATA COMPARISON\n")
    f.write("="*70 + "\n")

    f.write("\n--- Sample Tamb (first 10) ---\n")
    f.write(tamb[['blok', 'n_baris', 'n_pokok', 'ndre125', 't_tanam', 'ket']].head(10).to_string() + "\n")

    f.write("\n--- Sample Sisip (first 10) ---\n")
    f.write(sisip[['blok', 'n_baris', 'n_pokok', 'ndre125', 't_tanam', 'ket']].head(10).to_string() + "\n")

    # Distribution by t_tanam (year planted)
    f.write("\n" + "="*70 + "\n")
    f.write("DISTRIBUSI BERDASARKAN TAHUN TANAM\n")
    f.write("="*70 + "\n")

    f.write("\nTamb - Tahun Tanam:\n")
    f.write(str(tamb['t_tanam'].value_counts().sort_index()) + "\n")

    f.write("\nSisip - Tahun Tanam:\n")
    f.write(str(sisip['t_tanam'].value_counts().sort_index()) + "\n")

    f.write("\nPokok Utama - Tahun Tanam (sample):\n")
    f.write(str(pokok['t_tanam'].value_counts().sort_index()) + "\n")

    # Conclusion
    f.write("\n" + "="*70 + "\n")
    f.write("KESIMPULAN\n")
    f.write("="*70 + "\n")

    tamb_ndre = tamb['ndre125_num'].mean()
    sisip_ndre = sisip['ndre125_num'].mean()
    pokok_ndre = pokok['ndre125_num'].mean()

    f.write(f"\nNDRE Mean:\n")
    f.write(f"  Pokok Utama: {pokok_ndre:.4f}\n")
    f.write(f"  Tamb:        {tamb_ndre:.4f}\n")
    f.write(f"  Sisip:       {sisip_ndre:.4f}\n")

    diff_tamb_sisip = abs(tamb_ndre - sisip_ndre)
    diff_tamb_pokok = abs(tamb_ndre - pokok_ndre)

    f.write(f"\nSelisih NDRE:\n")
    f.write(f"  Tamb vs Sisip: {diff_tamb_sisip:.4f}\n")
    f.write(f"  Tamb vs Pokok: {diff_tamb_pokok:.4f}\n")

    if diff_tamb_sisip < diff_tamb_pokok:
        f.write("\n=> Tamb lebih mirip Sisip (nilai NDRE lebih dekat)\n")
    else:
        f.write("\n=> Tamb lebih mirip Pokok Utama (nilai NDRE lebih dekat)\n")

print("Results written to tamb_sisip_analysis.txt")
