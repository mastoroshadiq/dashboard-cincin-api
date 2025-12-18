# Kesimpulan Sementara: Perbandingan 3 Preset dengan dan tanpa Elbow Method

**Tanggal:** 18 Desember 2024  
**Data:** AME II (tabelNDREnew.csv) - 95,030 pohon  
**Versi:** POAC v3.3

---

## 📊 Executive Summary

| Aspek | Temuan |
|-------|--------|
| **Elbow Method Status** | ✅ Sudah terintegrasi ke 3 preset |
| **Masalah Teridentifikasi** | Elbow cenderung memilih threshold di BATAS ATAS |
| **Dampak** | Over-detection signifikan, terutama pada preset Agresif |
| **Gap Terbesar** | Agresif: +21,639 pohon (+115%) |

---

## 🔬 Metodologi Perbandingan

### Skenario yang Diuji:

1. **WITH Elbow** - Threshold dipilih otomatis via Elbow Method (efficiency-based)
2. **WITHOUT Elbow** - Threshold fixed di MIDPOINT range setiap preset

### Formula Elbow yang Digunakan:

```
Rasio_Efisiensi = (Kluster_Valid / Total_Suspect) × 100%

Dimana:
- Kluster_Valid = Pohon suspect dengan ≥min_sick_neighbors tetangga sakit
- Total_Suspect = Pohon dengan Ranking_Persentil ≤ threshold
```

---

## 📈 Hasil Perbandingan Detail

### Tabel Perbandingan Utama

| Preset | Range | Elbow Thresh | Fixed Thresh | MERAH (Elbow) | MERAH (Fixed) | GAP | GAP % |
|--------|-------|--------------|--------------|---------------|---------------|-----|-------|
| **Konservatif** | 3-15% | 15% | 9% | 861 | ~350 | +511 | +146% |
| **Standar** | 5-30% | 30% | 17.5% | 11,291 | ~5,500 | +5,791 | +105% |
| **Agresif** | 10-50% | 50% | 30% | 40,455 | 18,816 | +21,639 | +115% |

### Visualisasi Perbandingan

```
MERAH Detection Count (thousands)
│
40 ┤                              ████ Elbow (40.5k)
   │                              ████
35 ┤                              ████
   │                              ████
30 ┤                              ████
   │                              ████
25 ┤                              ████
   │                              ████
20 ┤                         ▓▓▓▓ Fixed (18.8k)
   │                         ████
15 ┤                         ████
   │      ████ Elbow(11.3k)  ████
10 ┤      ████               ████
   │      ▓▓▓▓ Fixed(5.5k)   ████
 5 ┤      ████               ████
   │ ██▓▓ ████               ████
 0 ┼──────────────────────────────────
     Konservatif  Standar    Agresif
```

---

## 🔍 Analisis Root Cause

### Mengapa Elbow Memilih Batas Atas?

**Penyebab:** Metode "efficiency" memiliki BIAS ke threshold tinggi.

```
Saat threshold NAIK:
├── Lebih BANYAK pohon menjadi "suspect"
├── Lebih BANYAK pohon memiliki "tetangga suspect"
├── Lebih MUDAH memenuhi syarat ≥3 tetangga sakit
├── Kluster_Valid naik LEBIH CEPAT dari Total_Suspect
└── → Rasio Efisiensi MENINGKAT!
```

**Ilustrasi:**

| Threshold | Total Suspect | Kluster Valid | Efisiensi |
|-----------|---------------|---------------|-----------|
| 10% | 9,500 | 3,000 | 31.6% |
| 30% | 28,500 | 13,000 | 45.6% |
| 50% | 47,500 | 23,000 | **48.4%** ← Tertinggi |

**Kesimpulan:** Elbow dengan metode "efficiency" akan SELALU cenderung memilih threshold tertinggi dalam range yang diberikan.

---

## ⚠️ Implikasi Praktis

### Dampak Over-Detection:

| Aspek | Konsekuensi |
|-------|-------------|
| **Survey Lapangan** | Beban survey meningkat 2-3x lipat |
| **False Positive** | Banyak pohon sehat di-flag sebagai MERAH |
| **Budget Logistik** | Kebutuhan Asap Cair/Trichoderma meningkat tidak proporsional |
| **Credibility** | Tingkat kepercayaan mandor terhadap sistem menurun |

### Perbandingan Beban Survey:

```
Preset Agresif:
├── WITH Elbow:    40,455 MERAH × estimasi 5 menit/pohon = 3,371 jam
├── WITHOUT Elbow: 18,816 MERAH × estimasi 5 menit/pohon = 1,568 jam
└── SAVING:        1,803 jam = 225 man-days!
```

---

## 💡 Rekomendasi

### Opsi 1: Turunkan Batas Atas Threshold

```python
# SEBELUM (over-detect)
"agresif": {
    "threshold_max": 0.50,  # 50%
}

# SETELAH (lebih ketat)
"agresif": {
    "threshold_max": 0.30,  # 30%
}
```

### Opsi 2: Ganti Metode Elbow ke "gradient"

```python
CINCIN_API_CONFIG = {
    "elbow_method": "gradient",  # Bukan "efficiency"
}
```

**Metode Gradient:** Mencari titik perubahan terbesar (true elbow point), bukan efisiensi tertinggi.

### Opsi 3: Gunakan Fixed Threshold (Tanpa Elbow)

Jika over-detection tidak dapat diterima, gunakan threshold fixed:
- **Konservatif:** 10%
- **Standar:** 20%
- **Agresif:** 30%

### Opsi 4: Consensus Voting (Post-Processing)

Jalankan semua 3 preset, lalu hanya flag pohon yang MERAH di ≥2 preset:
- Dari 40,455 → 11,291 MERAH (reduksi 72%)

---

## 📋 Langkah Selanjutnya

1. [ ] Validasi lapangan untuk menentukan opsi terbaik
2. [ ] Pilih metode tuning yang sesuai dengan kebutuhan operasional
3. [ ] Implementasi perubahan ke config.py
4. [ ] Re-run analisis untuk verifikasi
5. [ ] Update dokumentasi algoritma

---

## 📁 File Terkait

| File | Deskripsi |
|------|-----------|
| `poac_sim/config.py` | Konfigurasi preset dan Elbow parameters |
| `poac_sim/src/clustering.py` | Implementasi algoritma Cincin Api |
| `poac_sim/elbow_comparison.py` | Script perbandingan dengan/tanpa Elbow |
| `data/output/elbow_comparison_*/` | Hasil analisis dan dashboard |

---

**Dokumen ini adalah DRAFT dan memerlukan validasi lebih lanjut dengan data ground truth.**
