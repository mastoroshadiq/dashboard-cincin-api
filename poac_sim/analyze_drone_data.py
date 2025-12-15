"""Comprehensive Drone Data Analysis for Cleansing"""
import pandas as pd
from pathlib import Path

output_file = 'drone_cleansing_analysis.txt'

with open(output_file, 'w', encoding='utf-8') as f:
    f.write("="*80 + "\n")
    f.write("ANALISIS DATA DRONE UNTUK CLEANSING\n")
    f.write("="*80 + "\n")
    
    # ===== 1. tabelNDREnew.csv (AME II) =====
    f.write("\n" + "="*80 + "\n")
    f.write("1. tabelNDREnew.csv (AME II)\n")
    f.write("="*80 + "\n")
    
    df1 = pd.read_csv('data/input/tabelNDREnew.csv')
    f.write(f"\nTotal rows: {len(df1):,}\n")
    f.write(f"Columns: {df1.columns.tolist()}\n")
    
    # Analyze 'ket' column
    f.write("\n--- Distribusi Kolom 'ket' ---\n")
    vc1 = df1['ket'].value_counts()
    
    # Categorize
    categories = {
        'Pokok Utama': [],
        'Sisip': [],
        'Tambahan': [],
        'Kosong': [],
        'Mati': [],
        'Lainnya': []
    }
    
    for val, count in vc1.items():
        val_str = str(val).lower()
        if 'pokok utama' in val_str:
            categories['Pokok Utama'].append((val, count))
        elif 'sisip' in val_str:
            categories['Sisip'].append((val, count))
        elif 'tamb' in val_str:
            categories['Tambahan'].append((val, count))
        elif 'kosong' in val_str:
            categories['Kosong'].append((val, count))
        elif 'mati' in val_str:
            categories['Mati'].append((val, count))
        else:
            categories['Lainnya'].append((val, count))
    
    f.write(f"\n{'Kategori':<20} {'Jumlah':>12} {'Persen':>10}\n")
    f.write("-"*45 + "\n")
    
    total = len(df1)
    for cat, items in categories.items():
        cat_total = sum(c for _, c in items)
        if cat_total > 0:
            pct = cat_total / total * 100
            f.write(f"{cat:<20} {cat_total:>12,} {pct:>9.1f}%\n")
            for val, count in items:
                f.write(f"  - {val:<16} {count:>8,}\n")
    
    # ===== 2. AME_IV.csv =====
    f.write("\n\n" + "="*80 + "\n")
    f.write("2. AME_IV.csv (AME IV)\n")
    f.write("="*80 + "\n")
    
    # Read with current ingestion function
    from src.ingestion import load_ame_iv_data
    df2 = load_ame_iv_data(Path('data/input/AME_IV.csv'))
    
    f.write(f"\nTotal rows (setelah clean): {len(df2):,}\n")
    f.write(f"Columns: {df2.columns.tolist()}\n")
    
    # Check Keterangan column
    if 'Keterangan' in df2.columns:
        f.write("\n--- Distribusi Kolom 'Keterangan' ---\n")
        vc2 = df2['Keterangan'].value_counts()
        
        f.write(f"\n{'Nilai':<25} {'Jumlah':>12} {'Persen':>10}\n")
        f.write("-"*50 + "\n")
        
        for val, count in vc2.head(20).items():
            if pd.notna(val) and str(val).strip():
                pct = count / len(df2) * 100
                f.write(f"{str(val):<25} {count:>12,} {pct:>9.1f}%\n")
    
    # ===== Summary =====
    f.write("\n\n" + "="*80 + "\n")
    f.write("RINGKASAN & REKOMENDASI\n")
    f.write("="*80 + "\n")
    
    f.write("\n1. Kategori Pohon yang Teridentifikasi:\n")
    f.write("-"*50 + "\n")
    f.write("   a. POKOK UTAMA  - Pohon asli/pertama ditanam\n")
    f.write("   b. SISIP        - Pohon pengganti/replanting\n")
    f.write("   c. TAMBAHAN     - Pohon tambahan\n")
    f.write("   d. KOSONG       - Lokasi tidak ada pohon\n")
    f.write("   e. MATI         - Pohon sudah mati\n")
    
    f.write("\n2. Dampak pada Analisis:\n")
    f.write("-"*50 + "\n")
    f.write("   - Ghost Tree Audit: \n")
    f.write("     * Perbandingan Buku vs Drone harus hanya 'Pokok Utama'\n")
    f.write("     * 'Sisip' tidak termasuk dalam hitungan 'Pokok Utama' buku\n")
    f.write("     * 'Kosong' dan 'Mati' harus di-exclude\n")
    f.write("\n   - Early Detection:\n")
    f.write("     * Analisis risiko Ganoderma tetap semua pohon hidup\n")
    f.write("     * 'Kosong' dan 'Mati' exclude dari deteksi\n")
    
    f.write("\n3. Rekomendasi Implementasi:\n")
    f.write("-"*50 + "\n")
    f.write("   a. Tambah kolom 'tree_category' dengan nilai:\n")
    f.write("      - 'POKOK_UTAMA', 'SISIP', 'TAMBAHAN', 'KOSONG', 'MATI'\n")
    f.write("   b. Modifikasi Ghost Tree untuk filter 'POKOK_UTAMA' only\n")
    f.write("   c. Modifikasi Early Detection untuk exclude 'KOSONG'/'MATI'\n")

print(f"Results written to {output_file}")
