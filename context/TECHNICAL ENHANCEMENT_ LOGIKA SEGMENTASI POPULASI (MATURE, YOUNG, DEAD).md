# **TECHNICAL ENHANCEMENT: LOGIKA SEGMENTASI POPULASI (MATURE, YOUNG, DEAD)**

Target: Python Simulation Team  
Component: Data Pre-processing & Statistical Engine  
Priority: CRITICAL (Mencegah Bias Statistik & False Positive)

## **1\. TEMUAN MASALAH (THE DATA TRAP)**

Berdasarkan analisis distribusi NDRE pada tableNDRE.csv, ditemukan pola varians populasi yang dapat merusak akurasi Z-Score:

1. **Pokok Utama & Tambahan (Mature):** Populasi target analisis. NDRE stabil.  
2. **Sisipan (Young):** NDRE rendah karena kanopi kecil. Menurunkan rata-rata blok jika dihitung.  
3. **Mati/Kosong (Dead/Empty):** NDRE mendekati 0 atau Null. **Sangat merusak** standar deviasi jika masuk perhitungan.

Risiko Algoritma Saat Ini:  
Jika semua kategori digabung dalam perhitungan rata-rata blok ($\\mu$):

* Nilai $\\mu$ akan anjlok drastis.  
* Pohon sakit (G3) akan terlihat "normal" (Z-Score membaik) karena rata-rata kelasnya turun.  
* Pohon Mati berisiko tidak terdeteksi sebagai "Sumber" jika data NDRE-nya kosong/null dan sistem tidak menanganinya lewat label.

## **2\. SPESIFIKASI PERUBAHAN LOGIKA**

Ubah logika *Ingestion* dan *Statistics* dengan aturan **"Tri-State Segmentation"** (Split-Apply-Combine) berikut:

### **Rule \#1: Kategorisasi Pohon (Category Tagging)**

Saat membaca kolom Ket (Keterangan) dari CSV, terapkan *tagging* prioritas berikut:

| Keyword di CSV Ket | Kondisi Data Lain | Kategori Baru | Perlakuan Statistik | Perlakuan Status |
| :---- | :---- | :---- | :---- | :---- |
| Mati, Tumbang | \- | **DEAD** | **Exclusion** | Force **G4** (Source) |
| Kosong | OR NDRE is 0/Null | **EMPTY** | **Exclusion** | Force **EMPTY** (Skip) |
| Sisip, sisipan | \- | **YOUNG** | **Exclusion** | Force **G1** (Skip/Monitor) |
| Utama, Tamb | \- | **MATURE** | **Inclusion** | Kalkulasi Z-Score |

### **Rule \#2: Statistik Terisolasi (Statistical Isolation)**

Saat menghitung Rata-rata ($\\mu$) dan Standar Deviasi ($\\sigma$) Blok untuk baseline Z-Score:

* **HANYA** gunakan data populasi **MATURE** (Gabungan Utama & Tambahan).  
* **JANGAN** sertakan populasi **YOUNG**, **DEAD**, atau **EMPTY**.

$$\\mu\_{blok} \= Average(NDRE\_{mature\\\_only})$$

### **Rule \#3: Logika Deteksi Adaptif (Logic Flow)**

Terapkan logika bercabang berdasarkan Kategori:

**A. Jalur MATURE (Utama & Tamb):**

1. Hitung Z-Score menggunakan $\\mu\_{blok}$ Mature.  
2. Terapkan Threshold (misal Z \< \-2.0 \= G3).  
3. **Output:** G1, G2, atau G3.

**B. Jalur YOUNG (Sisipan):**

1. Bypass Z-Score.  
2. **Force Status:** "G1 (Monitoring)".  
3. **Role:** Bisa jadi korban (Ring), tidak bisa jadi sumber.

**C. Jalur DEAD (Mati/Tumbang):**

1. Bypass Z-Score (Nilai NDRE tidak relevan).  
2. **Force Status:** **"G4"**.  
3. **Role:** **SOURCE (Trigger Cincin Api)**.

**D. Jalur EMPTY (Kosong):**

1. Bypass Z-Score.  
2. **Force Status:** "EMPTY".  
3. **Role:** Tidak aktif (Putus Rantai).

## **3\. IMPLEMENTASI KODE (PSEUDO-PYTHON)**

Silakan update modul ingestion.py dan statistics.py:

def classify\_census\_category(row):  
    ket \= str(row\['Ket'\]).lower().strip()  
    ndre \= row\['NDRE125'\]  
      
    \# Prioritas 0: Cek Data Fisik (Safety Net)  
    \# Jika NDRE 0 atau Null, anggap Kosong meski labelnya mungkin salah ketik  
    if ndre \== 0 or pd.isna(ndre):  
        return 'EMPTY'

    \# Prioritas 1: Mati/Kosong (Label Explicit)  
    if 'mati' in ket or 'tumbang' in ket:  
        return 'DEAD'  
    if 'kosong' in ket:  
        return 'EMPTY'  
          
    \# Prioritas 2: Usia Tanam  
    if 'sisip' in ket:  
        return 'YOUNG'  
    elif 'tamb' in ket or 'utama' in ket:  
        return 'MATURE'  
          
    return 'MATURE' \# Default fallback

def calculate\_status(df\_blok):  
    \# 1\. Tagging  
    df\_blok\['Category'\] \= df\_blok.apply(classify\_census\_category, axis=1)  
      
    \# 2\. Hitung Baseline Statistik (Hanya Mature)  
    \# PENTING: Tambahan & Utama digabung jadi satu baseline agar robust  
    mature\_data \= df\_blok\[df\_blok\['Category'\] \== 'MATURE'\]  
      
    if len(mature\_data) \> 0:  
        mean\_base \= mature\_data\['NDRE125'\].mean()  
        std\_base \= mature\_data\['NDRE125'\].std()  
    else:  
        \# Fallback jika blok isinya bibit semua (jarang terjadi)  
        mean\_base \= 0  
        std\_base \= 1 

    def apply\_logic(row):  
        cat \= row\['Category'\]  
          
        \# LOGIC DEAD (G4)  
        if cat \== 'DEAD':  
            return 'G4', 'SOURCE' \# Trigger Ring of Fire  
              
        \# LOGIC EMPTY  
        if cat \== 'EMPTY':  
            return 'EMPTY', 'NONE'  
              
        \# LOGIC YOUNG (Sisipan)  
        if cat \== 'YOUNG':  
            return 'G1', 'MONITOR' \# Jangan vonis sakit via NDRE  
              
        \# LOGIC MATURE (Utama/Tamb)  
        \# Hitung Z-Score  
        if std\_base \== 0: return 'G1', 'MONITOR' \# Prevent div/0  
          
        z \= (row\['NDRE125'\] \- mean\_base) / std\_base  
          
        \# Thresholds (Ambil dari Config)  
        if z \< \-2.0: return 'G3', 'SOURCE'  
        if z \< \-1.0: return 'G2', 'WARNING'  
        return 'G1', 'SAFE'

    \# Apply ke DataFrame  
    \# Note: Gunakan vektorisasi pandas untuk performa di production  
    results \= df\_blok.apply(apply\_logic, axis=1, result\_type='expand')  
    df\_blok\[\['G\_Index', 'Role'\]\] \= results  
      
    return df\_blok

## **4\. DAMPAK YANG DIHARAPKAN**

1. **Integritas Statistik:** Pohon mati (NDRE 0\) tidak lagi menyeret turun rata-rata blok, sehingga deteksi stres pada pohon hidup menjadi lebih tajam.  
2. **Otomasi SOP:** Pohon dengan label "Mati" di CSV otomatis memicu protokol G4 (Sanitasi & Cincin Api) tanpa perlu analisis spektral.

## **5\. RATIONALE (Why Split-Apply-Combine?)**

Kenapa **Pohon Tambahan** disatukan dengan **Pohon Utama**?

1. **Statistical Robustness:** Pohon tambahan biasanya minoritas. Membuat statistik terpisah untuk mereka akan menghasilkan varians yang tinggi (tidak valid).  
2. **Biological Equivalence:** Pohon tambahan (Mature) memiliki profil akar dan kanopi yang setara dengan pohon utama. Risiko penularan Ganoderma adalah sama.  
3. **Prevention of False Negatives:** Jika kita melonggarkan threshold untuk pohon tambahan, kita berisiko membiarkan sumber infeksi (G3) tetap aktif di tengah kebun hanya karena labelnya "Tambahan".