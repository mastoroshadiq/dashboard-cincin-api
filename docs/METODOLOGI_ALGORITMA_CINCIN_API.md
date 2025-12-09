# 📚 Metodologi Algoritma Cincin Api
## Panduan Lengkap 4 Pendekatan Deteksi Kluster Ganoderma

**Versi:** 1.0  
**Tanggal:** Desember 2025  
**Penulis:** Tim POAC v3.3

---

## 📋 Daftar Isi

1. [Pendahuluan](#1-pendahuluan)
2. [Pendekatan 1: Ranking Relatif (Percentile Rank)](#2-pendekatan-1-ranking-relatif-percentile-rank)
3. [Pendekatan 2: Elbow Method Auto-Tuning](#3-pendekatan-2-elbow-method-auto-tuning)
4. [Pendekatan 3: Analisis Tetangga Hexagonal](#4-pendekatan-3-analisis-tetangga-hexagonal)
5. [Pendekatan 4: Klasifikasi 4-Tier](#5-pendekatan-4-klasifikasi-4-tier)
6. [Alur Kerja Terintegrasi](#6-alur-kerja-terintegrasi)
7. [Kesimpulan](#7-kesimpulan)

---

## 1. Pendahuluan

### 🎯 Tujuan Dokumen

Dokumen ini menjelaskan **mengapa** dan **bagaimana** Algoritma Cincin Api menggunakan 4 pendekatan utama untuk mendeteksi kluster serangan Ganoderma pada perkebunan kelapa sawit.

### 🌴 Konteks Masalah

Ganoderma adalah jamur patogen yang menyerang akar kelapa sawit. Karakteristik penyebarannya:
- **Menyebar melalui kontak akar** → membentuk pola kluster
- **Tidak menyebar acak** → mengikuti pola tanam
- **Deteksi dini krusial** → mencegah penyebaran luas

### 🔥 Mengapa "Cincin Api"?

Nama "Cincin Api" terinspirasi dari strategi memadamkan kebakaran hutan:
> *"Untuk menghentikan api, kita tidak hanya memadamkan titik api, tapi juga membuat garis pembatas (firebreak) di sekitarnya."*

Sama halnya dengan Ganoderma:
- **Titik api** = Pohon yang sudah terinfeksi (MERAH)
- **Cincin api** = Pohon di sekitarnya yang berisiko (KUNING)
- **Firebreak** = Tindakan preventif pada pohon berisiko

---

## 2. Pendekatan 1: Ranking Relatif (Percentile Rank)

### 📖 Apa itu Ranking Relatif?

**Ranking Relatif** adalah metode normalisasi data yang mengubah nilai NDRE setiap pohon menjadi **posisi relatif** terhadap pohon lain **dalam blok yang sama**.

```
Contoh Sederhana:
- Pohon A: NDRE = 0.45 → Peringkat 10 dari 100 → Persentil = 10%
- Pohon B: NDRE = 0.52 → Peringkat 50 dari 100 → Persentil = 50%
- Pohon C: NDRE = 0.58 → Peringkat 90 dari 100 → Persentil = 90%
```

### ❓ Analisis 5W1H

| Aspek | Penjelasan |
|-------|------------|
| **What** (Apa) | Metode untuk mengkonversi nilai NDRE absolut menjadi ranking persentil (0-100%) relatif terhadap blok |
| **Why** (Mengapa) | Karena nilai NDRE absolut **tidak dapat dibandingkan langsung** antar blok yang berbeda |
| **Who** (Siapa) | Diterapkan pada setiap pohon dalam dataset |
| **When** (Kapan) | Langkah pertama sebelum analisis lanjutan |
| **Where** (Dimana) | Perhitungan dilakukan **per blok** secara terpisah |
| **How** (Bagaimana) | `Persentil = (Ranking pohon / Total pohon dalam blok) × 100%` |

### 🤔 Mengapa Tidak Menggunakan Nilai NDRE Langsung?

#### Masalah dengan Nilai Absolut:

```
CONTOH KASUS:
┌─────────────────────────────────────────────────────────────┐
│ Blok A (Tanah Subur)         │ Blok B (Tanah Kurang Subur) │
├─────────────────────────────────────────────────────────────┤
│ Rata-rata NDRE: 0.55         │ Rata-rata NDRE: 0.45        │
│ Pohon Sakit: NDRE = 0.48     │ Pohon Sehat: NDRE = 0.48    │
└─────────────────────────────────────────────────────────────┘

Masalah: Nilai NDRE 0.48 bisa berarti SAKIT di Blok A, 
         tapi SEHAT di Blok B!
```

#### Solusi dengan Ranking Relatif:

```
DENGAN RANKING RELATIF:
┌─────────────────────────────────────────────────────────────┐
│ Blok A                       │ Blok B                       │
├─────────────────────────────────────────────────────────────┤
│ Pohon (NDRE 0.48):           │ Pohon (NDRE 0.48):          │
│ Persentil = 5% (RENDAH)      │ Persentil = 60% (NORMAL)    │
│ → Terdeteksi sebagai SUSPECT │ → Terdeteksi sebagai SEHAT  │
└─────────────────────────────────────────────────────────────┘

Solusi: Sekarang kita membandingkan apel dengan apel!
```

### ✅ Keuntungan Ranking Relatif

1. **Eliminasi Bias Lingkungan** - Perbedaan kondisi tanah, umur tanaman, varietas tidak mempengaruhi
2. **Skala Universal** - Semua blok menggunakan skala 0-100%
3. **Deteksi Anomali Lokal** - Pohon "berbeda" dari tetangganya terdeteksi
4. **Robust terhadap Outlier** - Tidak terpengaruh nilai ekstrem

### 📊 Visualisasi Konsep

```
SEBELUM (Nilai Absolut):          SETELAH (Ranking Relatif):
                                  
Blok A: ████████████ (0.55)       Blok A: 50% ████████████
Blok B: ████████ (0.45)           Blok B: 50% ████████████
                                  
Pohon X di A: ███ (0.48)          Pohon X di A: 5%  █
Pohon Y di B: ███ (0.48)          Pohon Y di B: 60% ██████████
                                  
↑ Terlihat sama                   ↑ Terlihat berbeda!
```

---

## 3. Pendekatan 2: Elbow Method Auto-Tuning

### 📖 Apa itu Elbow Method?

**Elbow Method** adalah teknik untuk menemukan **threshold optimal** secara otomatis dengan mencari titik "siku" pada kurva performa.

```
Analogi Sederhana:
Bayangkan Anda mengatur volume TV:
- Volume 0-20: Hampir tidak terdengar (terlalu rendah)
- Volume 20-50: Perubahan signifikan (sweet spot)
- Volume 50-100: Perbedaan minimal (diminishing returns)

"Siku" ada di sekitar volume 20-50, dimana perubahan paling signifikan.
```

### ❓ Analisis 5W1H

| Aspek | Penjelasan |
|-------|------------|
| **What** (Apa) | Teknik optimasi untuk menemukan threshold persentil terbaik (5%-30%) |
| **Why** (Mengapa) | Karena threshold **tidak bisa ditebak** - setiap dataset/kebun berbeda |
| **Who** (Siapa) | Sistem menjalankan otomatis, tidak perlu input manual |
| **When** (Kapan) | Setelah ranking relatif, sebelum klasifikasi |
| **Where** (Dimana) | Simulasi dilakukan pada keseluruhan dataset |
| **How** (Bagaimana) | Simulasi berbagai threshold → hitung efisiensi → pilih yang optimal |

### 🤔 Mengapa Tidak Menggunakan Threshold Tetap?

#### Masalah dengan Threshold Tetap:

```
CONTOH KASUS:
┌─────────────────────────────────────────────────────────────┐
│ Kebun A (Infeksi Ringan)     │ Kebun B (Infeksi Berat)     │
├─────────────────────────────────────────────────────────────┤
│ Dengan threshold 10%:        │ Dengan threshold 10%:       │
│ Suspect: 500 pohon           │ Suspect: 500 pohon          │
│ Kluster valid: 50 (10%)      │ Kluster valid: 450 (90%)    │
│ → Terlalu banyak false pos.  │ → Threshold terlalu rendah! │
└─────────────────────────────────────────────────────────────┘

Masalah: Threshold yang sama memberikan hasil berbeda drastis!
```

### 📈 Cara Kerja Elbow Method

#### Langkah 1: Simulasi Berbagai Threshold

```
Simulasi threshold 5% sampai 30%:

Threshold │ Total Suspect │ Kluster Valid │ Efisiensi
──────────┼───────────────┼───────────────┼──────────
    5%    │     4,751     │     1,205     │   25.4%
   10%    │     9,503     │     3,890     │   40.9%
   15%    │    14,254     │     6,234     │   43.7%
   20%    │    19,006     │     8,567     │   45.1%
   25%    │    23,757     │    10,234     │   43.1%  ← Mulai turun
   30%    │    28,509     │    11,291     │   39.6%
```

#### Langkah 2: Identifikasi Titik Optimal

```
Grafik Efisiensi:

Efisiensi
   50% │           ╭──────╮
       │         ╭─╯      ╰──╮
   40% │       ╭─╯            ╰───
       │     ╭─╯
   30% │   ╭─╯
       │ ╭─╯
   20% │─╯
       └──────────────────────────
         5%  10%  15%  20%  25%  30%
                      ↑
                 Threshold Optimal (20%)
```

#### Langkah 3: Pilih Threshold dengan Efisiensi Tertinggi

```python
# Pseudo-code
optimal_threshold = threshold_dengan_efisiensi_tertinggi
# dengan syarat: minimal memiliki X kluster valid
```

### ✅ Keuntungan Auto-Tuning

1. **Adaptif** - Menyesuaikan dengan kondisi kebun aktual
2. **Objektif** - Tidak bergantung pada intuisi manusia
3. **Reproducible** - Hasil konsisten untuk data yang sama
4. **Efisien** - Mengoptimalkan rasio deteksi vs false positive

### 🎯 Metrik Efisiensi

```
                    Jumlah Kluster Valid
Efisiensi (%) = ─────────────────────────── × 100
                    Total Suspect Trees

Dimana:
- Kluster Valid = Pohon suspect dengan ≥3 tetangga suspect
- Total Suspect = Semua pohon di bawah threshold
```

---

## 4. Pendekatan 3: Analisis Tetangga Hexagonal

### 📖 Apa itu Analisis Tetangga Hexagonal?

**Analisis Tetangga Hexagonal** adalah metode untuk menentukan apakah sebuah pohon suspect merupakan bagian dari **kluster penyakit** berdasarkan kondisi pohon-pohon tetangganya dalam pola tanam hexagonal.

```
Pola Tanam Mata Lima (Hexagonal):

    🌴     🌴     🌴     🌴
       🌴     🌴     🌴
    🌴     🌴     🌴     🌴
       🌴     🌴     🌴
    🌴     🌴     🌴     🌴

Setiap pohon memiliki 6 tetangga terdekat
```

### ❓ Analisis 5W1H

| Aspek | Penjelasan |
|-------|------------|
| **What** (Apa) | Analisis spasial untuk menghitung jumlah tetangga "sakit" dari setiap pohon |
| **Why** (Mengapa) | Karena Ganoderma **menyebar melalui kontak akar** → membentuk kluster |
| **Who** (Siapa) | Diterapkan pada setiap pohon yang terdeteksi sebagai suspect |
| **When** (Kapan) | Setelah threshold ditentukan, sebelum klasifikasi final |
| **Where** (Dimana) | Menggunakan koordinat Baris (N_BARIS) dan Pokok (N_POKOK) |
| **How** (Bagaimana) | Identifikasi 6 tetangga → hitung yang suspect → tentukan status |

### 🤔 Mengapa Menggunakan Pola Hexagonal?

#### Realitas Pola Tanam Kelapa Sawit:

```
Pola Tanam di Lapangan (Mata Lima / Quincunx):

BARIS GANJIL:    🌴  .  🌴  .  🌴  .  🌴
BARIS GENAP:      .  🌴  .  🌴  .  🌴  .
BARIS GANJIL:    🌴  .  🌴  .  🌴  .  🌴
BARIS GENAP:      .  🌴  .  🌴  .  🌴  .

Jarak antar pohon: ~9 meter
Bentuk: Segitiga sama sisi → membentuk hexagon
```

#### Kenapa Bukan Grid Kotak?

```
GRID KOTAK (4 tetangga):         HEXAGONAL (6 tetangga):
                                 
     🌴                               🌴
   🌴 X 🌴                         🌴   🌴
     🌴                             X
                                  🌴   🌴
                                     🌴

Masalah: Grid kotak tidak         Solusi: Hexagonal sesuai
merepresentasikan pola            dengan realitas lapangan!
tanam sebenarnya
```

### 📐 Cara Menghitung Tetangga Hexagonal

#### Pola Offset Baris (Odd-Row Offset):

```python
# Untuk baris GANJIL (1, 3, 5, ...):
tetangga = [
    (baris-1, pokok-1),  # Kiri Atas
    (baris-1, pokok),    # Kanan Atas
    (baris,   pokok-1),  # Kiri
    (baris,   pokok+1),  # Kanan
    (baris+1, pokok-1),  # Kiri Bawah
    (baris+1, pokok),    # Kanan Bawah
]

# Untuk baris GENAP (2, 4, 6, ...):
tetangga = [
    (baris-1, pokok),    # Kiri Atas
    (baris-1, pokok+1),  # Kanan Atas
    (baris,   pokok-1),  # Kiri
    (baris,   pokok+1),  # Kanan
    (baris+1, pokok),    # Kiri Bawah
    (baris+1, pokok+1),  # Kanan Bawah
]
```

#### Visualisasi Offset:

```
BARIS GANJIL (contoh baris 3):
                    
    [2,2]   [2,3]          ← Tetangga atas
       \     /
  [3,2]—[3,3]—[3,4]        ← Kiri - POHON - Kanan
       /     \
    [4,2]   [4,3]          ← Tetangga bawah

BARIS GENAP (contoh baris 4):
                    
    [3,4]   [3,5]          ← Tetangga atas (GESER)
       \     /
  [4,3]—[4,4]—[4,5]        ← Kiri - POHON - Kanan
       /     \
    [5,4]   [5,5]          ← Tetangga bawah (GESER)
```

### 🎯 Logika Penentuan Kluster

```
Jumlah Tetangga Sakit → Interpretasi:

┌─────────────────────────────────────────────────────────┐
│ 6 tetangga sakit │ ██████ │ Kluster sangat padat       │
│ 5 tetangga sakit │ █████  │ Kluster padat              │
│ 4 tetangga sakit │ ████   │ Kluster sedang             │
│ 3 tetangga sakit │ ███    │ AMBANG BATAS → KLUSTER     │
├─────────────────────────────────────────────────────────┤
│ 2 tetangga sakit │ ██     │ Risiko tinggi, bukan kluster│
│ 1 tetangga sakit │ █      │ Risiko sedang              │
│ 0 tetangga sakit │        │ Terisolasi (noise)         │
└─────────────────────────────────────────────────────────┘

Threshold default: ≥3 tetangga sakit = KLUSTER
(50% dari maksimal 6 tetangga)
```

### ✅ Keuntungan Analisis Hexagonal

1. **Realistis** - Sesuai dengan pola tanam aktual
2. **Spasial** - Mempertimbangkan lokasi, bukan hanya nilai
3. **Mendeteksi Pola** - Kluster vs noise teridentifikasi
4. **Mengurangi False Positive** - Pohon terisolasi tidak dianggap kluster

---

## 5. Pendekatan 4: Klasifikasi 4-Tier

### 📖 Apa itu Klasifikasi 4-Tier?

**Klasifikasi 4-Tier** adalah sistem pengelompokan pohon menjadi 4 kategori berdasarkan kombinasi **ranking persentil** dan **jumlah tetangga sakit**.

```
4 Tier Status:

🔴 MERAH  - Kluster Aktif     → Prioritas Sanitasi
🟡 KUNING - Risiko Tinggi     → Monitoring Ketat
🟠 ORANYE - Noise/Kentosan    → Investigasi
🟢 HIJAU  - Sehat             → Normal
```

### ❓ Analisis 5W1H

| Aspek | Penjelasan |
|-------|------------|
| **What** (Apa) | Sistem kategorisasi 4 level untuk prioritas tindakan |
| **Why** (Mengapa) | Karena **tidak semua pohon sakit sama berbahayanya** - perlu prioritas |
| **Who** (Siapa) | Setiap pohon mendapat satu label klasifikasi |
| **When** (Kapan) | Langkah terakhir setelah semua analisis selesai |
| **Where** (Dimana) | Output final untuk laporan dan visualisasi |
| **How** (Bagaimana) | Decision tree berdasarkan persentil dan jumlah tetangga |

### 🤔 Mengapa 4 Tier, Bukan 2 (Sakit/Sehat)?

#### Masalah dengan Klasifikasi Biner:

```
KLASIFIKASI BINER:
┌─────────────────────────────────────────────────────────┐
│ SAKIT                        │ SEHAT                    │
├─────────────────────────────────────────────────────────┤
│ • Kluster padat 6 tetangga   │ • Pohon normal           │
│ • Kluster kecil 3 tetangga   │                          │
│ • Pohon berisiko 2 tetangga  │                          │
│ • Pohon terisolasi 0 tetangga│                          │
└─────────────────────────────────────────────────────────┘

Masalah: 
- Semua "sakit" dianggap sama → tidak efisien!
- Pohon kluster padat = prioritas utama
- Pohon terisolasi = mungkin false positive
```

#### Solusi dengan 4 Tier:

```
KLASIFIKASI 4-TIER:
┌─────────────────────────────────────────────────────────┐
│ TIER      │ KRITERIA              │ PRIORITAS           │
├─────────────────────────────────────────────────────────┤
│ 🔴 MERAH  │ ≤threshold, ≥3 tetangga│ #1 - SANITASI      │
│ 🟡 KUNING │ ≤threshold, 1-2 tetangga│ #2 - MONITORING   │
│ 🟠 ORANYE │ ≤threshold, 0 tetangga │ #3 - INVESTIGASI  │
│ 🟢 HIJAU  │ >threshold            │ #4 - NORMAL        │
└─────────────────────────────────────────────────────────┘

Solusi: Tindakan yang tepat untuk kondisi yang berbeda!
```

### 🔍 Detail Setiap Tier

#### 🔴 MERAH - Kluster Aktif

```
KRITERIA:
├─ Persentil ≤ threshold (suspect)
└─ Jumlah tetangga sakit ≥ 3

INTERPRETASI:
"Pohon ini berada di tengah kluster penyakit aktif.
Kemungkinan besar sudah terinfeksi dan menyebarkan ke sekitarnya."

TINDAKAN:
✓ PRIORITAS UTAMA
✓ Validasi lapangan segera
✓ Jika terkonfirmasi → Sanitasi sesuai SOP
✓ Periksa pohon tetangga

CONTOH VISUALISASI:
       🟡         🔴 = Pohon ini
    🟡  🔴  🟡    Dikelilingi 4+ pohon sakit
       🟡         → MERAH (Kluster Aktif)
```

#### 🟡 KUNING - Risiko Tinggi

```
KRITERIA:
├─ Persentil ≤ threshold (suspect)
└─ Jumlah tetangga sakit = 1 atau 2

INTERPRETASI:
"Pohon ini menunjukkan gejala DAN berada dekat dengan pohon sakit.
Berpotensi menjadi kluster baru jika tidak ditangani."

TINDAKAN:
✓ Monitoring ketat (setiap 2 minggu)
✓ Catat perkembangan kondisi
✓ Jika memburuk → upgrade ke MERAH
✓ Persiapkan intervensi preventif

CONTOH VISUALISASI:
       🟢         🟡 = Pohon ini
    🔴  🟡  🟢    Hanya 1 tetangga sakit
       🟢         → KUNING (Risiko Tinggi)
```

#### 🟠 ORANYE - Noise/Kentosan

```
KRITERIA:
├─ Persentil ≤ threshold (suspect)
└─ Jumlah tetangga sakit = 0

INTERPRETASI:
"Pohon ini menunjukkan gejala TAPI terisolasi (tidak ada tetangga sakit).
Kemungkinan: kentosan alami, stress lingkungan, atau false positive."

TINDAKAN:
✓ Investigasi penyebab
✓ Bisa diabaikan untuk sementara
✓ Jangan alokasikan resource sanitasi
✓ Monitor jika ada perubahan lingkungan

CONTOH VISUALISASI:
       🟢         🟠 = Pohon ini
    🟢  🟠  🟢    Tidak ada tetangga sakit
       🟢         → ORANYE (Terisolasi)
```

#### 🟢 HIJAU - Sehat

```
KRITERIA:
└─ Persentil > threshold

INTERPRETASI:
"Pohon ini memiliki nilai NDRE normal relatif terhadap bloknya.
Tidak ada indikasi infeksi Ganoderma."

TINDAKAN:
✓ Tidak perlu tindakan khusus
✓ Monitoring rutin standar
✓ Fokus resource ke pohon prioritas

CONTOH:
Semua pohon dengan ranking lebih baik dari threshold
→ HIJAU (Sehat)
```

### 📊 Decision Tree Klasifikasi

```
                    ┌─────────────────┐
                    │  Mulai Analisis │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │ Persentil ≤     │
                    │ Threshold?      │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │ YA           │              │ TIDAK
              ▼              │              ▼
    ┌─────────────────┐      │    ┌─────────────────┐
    │ Hitung tetangga │      │    │    🟢 HIJAU     │
    │ sakit           │      │    │    (Sehat)      │
    └────────┬────────┘      │    └─────────────────┘
             │               │
    ┌────────▼────────┐      │
    │ Jumlah tetangga │      │
    │ sakit = ?       │      │
    └────────┬────────┘      │
             │               │
    ┌────────┼────────┬──────┘
    │        │        │
    ▼        ▼        ▼
  ≥ 3      1-2       0
    │        │        │
    ▼        ▼        ▼
┌───────┐┌───────┐┌───────┐
│🔴MERAH││🟡KUNING││🟠ORANYE│
│Kluster││Risiko ││Noise  │
│Aktif  ││Tinggi ││       │
└───────┘└───────┘└───────┘
```

### ✅ Keuntungan Klasifikasi 4-Tier

1. **Prioritas Jelas** - Mandor tahu harus mulai dari mana
2. **Resource Efisien** - Tidak membuang resource untuk noise
3. **Actionable** - Setiap tier punya rekomendasi tindakan spesifik
4. **Monitoring** - Tier bisa berubah seiring waktu (tracking)

---

## 6. Alur Kerja Terintegrasi

### 📊 Diagram Alur Lengkap

```
┌─────────────────────────────────────────────────────────────────┐
│                    INPUT: Data NDRE Per Pohon                    │
│                    (Blok, Baris, Pokok, NDRE)                   │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  LANGKAH 1: RANKING RELATIF (Percentile Rank)                   │
│  ─────────────────────────────────────────────                  │
│  • Hitung ranking per blok                                       │
│  • Konversi ke persentil 0-100%                                 │
│  • Output: Setiap pohon punya nilai Ranking_Persentil           │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  LANGKAH 2: ELBOW METHOD AUTO-TUNING                            │
│  ─────────────────────────────────────────────                  │
│  • Simulasi threshold 5% - 30%                                  │
│  • Hitung efisiensi setiap threshold                            │
│  • Pilih threshold dengan efisiensi tertinggi                   │
│  • Output: Threshold Optimal (misal: 20%)                       │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  LANGKAH 3: ANALISIS TETANGGA HEXAGONAL                         │
│  ─────────────────────────────────────────────                  │
│  • Identifikasi suspect (persentil ≤ threshold)                 │
│  • Untuk setiap suspect, hitung 6 tetangga hexagonal            │
│  • Hitung berapa tetangga yang juga suspect                     │
│  • Output: Jumlah_Tetangga_Sakit untuk setiap pohon             │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  LANGKAH 4: KLASIFIKASI 4-TIER                                  │
│  ─────────────────────────────────────────────                  │
│  • Persentil > threshold → 🟢 HIJAU                             │
│  • Persentil ≤ threshold:                                       │
│    ├─ ≥3 tetangga sakit → 🔴 MERAH                              │
│    ├─ 1-2 tetangga sakit → 🟡 KUNING                            │
│    └─ 0 tetangga sakit → 🟠 ORANYE                              │
│  • Output: Status_Risiko untuk setiap pohon                     │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    OUTPUT: Laporan & Dashboard                   │
│  • Daftar prioritas untuk Mandor                                │
│  • Visualisasi peta kluster                                     │
│  • Statistik per blok                                           │
│  • HTML Report interaktif                                       │
└─────────────────────────────────────────────────────────────────┘
```

### 🔄 Contoh Kasus End-to-End

```
INPUT:
Pohon ID #12345
├─ Blok: D01
├─ Baris: 15
├─ Pokok: 8
└─ NDRE: 0.4523

LANGKAH 1 - Ranking Relatif:
├─ Blok D01 memiliki 2,500 pohon
├─ Pohon #12345 berada di peringkat 125 dari 2,500
└─ Ranking_Persentil = 125/2500 = 5%

LANGKAH 2 - Threshold (hasil auto-tune):
└─ Threshold Optimal = 20%

LANGKAH 3 - Analisis Tetangga:
├─ Persentil 5% ≤ 20% → SUSPECT ✓
├─ Tetangga hexagonal:
│   ├─ (14, 7): Persentil 8% → Sakit
│   ├─ (14, 8): Persentil 12% → Sakit
│   ├─ (15, 7): Persentil 45% → Sehat
│   ├─ (15, 9): Persentil 6% → Sakit
│   ├─ (16, 7): Persentil 55% → Sehat
│   └─ (16, 8): Persentil 9% → Sakit
└─ Jumlah_Tetangga_Sakit = 4

LANGKAH 4 - Klasifikasi:
├─ Persentil (5%) ≤ Threshold (20%) → Suspect
├─ Tetangga Sakit (4) ≥ 3 → KLUSTER
└─ Status_Risiko = 🔴 MERAH (Kluster Aktif)

OUTPUT:
Pohon #12345 → MERAH → PRIORITAS SANITASI
```

---

## 7. Kesimpulan

### 🎯 Ringkasan 4 Pendekatan

| # | Pendekatan | Fungsi | Mengapa Penting |
|---|------------|--------|-----------------|
| 1 | **Ranking Relatif** | Normalisasi data | Mengeliminasi bias antar blok |
| 2 | **Elbow Method** | Optimasi threshold | Adaptif terhadap kondisi aktual |
| 3 | **Analisis Hexagonal** | Deteksi spasial | Mengidentifikasi kluster vs noise |
| 4 | **Klasifikasi 4-Tier** | Prioritas tindakan | Rekomendasi actionable |

### 🔗 Hubungan Antar Pendekatan

```
Ranking Relatif → membuat data COMPARABLE
         │
         ▼
Elbow Method → membuat threshold OPTIMAL
         │
         ▼
Analisis Hexagonal → membuat deteksi SPATIAL
         │
         ▼
Klasifikasi 4-Tier → membuat output ACTIONABLE
```

### ✅ Validasi Pendekatan

Keempat pendekatan ini telah divalidasi untuk:

1. **Akurasi** - Mendeteksi kluster yang benar-benar ada
2. **Efisiensi** - Meminimalkan false positive
3. **Skalabilitas** - Dapat diterapkan di berbagai ukuran kebun
4. **Interpretabilitas** - Mudah dipahami oleh pengguna lapangan

### 📈 Hasil yang Diharapkan

Dengan kombinasi 4 pendekatan ini, sistem mampu:

- ✅ Mendeteksi kluster Ganoderma aktif dengan akurasi tinggi
- ✅ Membedakan kluster nyata dari noise/kentosan
- ✅ Memberikan prioritas tindakan yang jelas
- ✅ Beradaptasi dengan kondisi kebun yang berbeda-beda
- ✅ Menghemat resource dengan fokus pada target prioritas

---

## 📚 Referensi

1. Panduan Teknis Algoritma Cincin Api v1.0
2. Software Requirements Specification POAC v3.3
3. BACKEND_TUNABLE_PARAMS_V3.3.md

---

*Dokumen ini adalah bagian dari dokumentasi POAC v3.3 - Precision Oil Palm Agriculture Control*

**Terakhir diperbarui:** Desember 2025
