
# PANDUAN TAKTIS: PENYESUAIAN ALGORITMA "CINCIN API" V2.0
**Metode: Z-Score Spatial Filter (Deteksi Anomali Statistik)**

**Kepada:** Tim Teknis (Toro & Jito)
**Dari:** Project Owner
**Status:** **MANDATORI (Immediate Action)**

---

## 1. LATAR BELAKANG: MENGAPA KITA BERUBAH?

**Masalah pada Metode Lama (Ranking/Elbow):**
Metode sebelumnya menggunakan persentase tetap (misal: "Ambil 20% terbawah").
*   **Kelemahan Fatal:** Algoritma ini **memaksa** sistem untuk menemukan kesalahan. Pada blok yang sebenarnya **100% SEHAT**, algoritma tetap akan memvonis 20% pohon terendah sebagai "Sakit".
*   **Akibat:** Tingkat *Over-Detection* (Positif Palsu) sangat tinggi. Dashboard menjadi "banjir merah" yang tidak realistis, menurunkan kepercayaan manajemen terhadap data.

**Solusi Baru (Metode Z-Score):**
Kita beralih ke **Deteksi Anomali Statistik**. Kita tidak lagi mencari "Siapa yang terbawah", tapi mencari **"Siapa yang menyimpang jauh dari normal"**.
*   **Kelebihan:** Jika sebuah blok sehat dan seragam, Z-Score tidak akan menemukan anomali (0 deteksi). Sistem hanya akan berteriak jika ada pohon yang nilainya jatuh signifikan di bawah rata-rata teman-temannya.

---

## 2. LOGIKA ALGORITMA BARU (STEP-BY-STEP)

Algoritma ini bekerja dalam 3 lapisan filter untuk memastikan hanya target valid yang muncul.

### Filter 1: Normalisasi Statistik (Per Blok)
Setiap blok memiliki kondisi cahaya dan tanah berbeda. Kita harus menghitung "Standar Normal" untuk setiap blok.
*   Hitung **Rata-rata (Mean)** NDRE per blok.
*   Hitung **Simpangan Baku (Standard Deviation/SD)** per blok.

### Filter 2: Hitung Skor Anomali (Z-Score)
Untuk setiap pohon, hitung seberapa jauh ia menyimpang dari rata-rata bloknya.
*   **Rumus:** `(NDRE Pohon - Rata2 Blok) / SD Blok`
*   **Logika:**
    *   Z-Score `0` = Pohon Rata-rata.
    *   Z-Score `-1.0` = Agak Kuning (Stres Ringan/Kurang Pupuk).
    *   Z-Score `-2.0` = **Sangat Kuning/Rusak (Suspect Ganoderma).**

### Filter 3: Validasi Tetangga (Spatial Check)
*Ganoderma* tidak menyerang sendirian (soliter). Jika ada pohon dengan Z-Score rendah tapi **semua tetangganya sehat walafiat**, itu kemungkinan besar *Noise* (Kentosan/Eror Drone).
*   **Syarat:** Sebuah "Suspect" baru dianggap valid jika memiliki **minimal 1 tetangga** yang juga mengalami stres (Z-Score < -0.5).

---

## 3. IMPLEMENTASI TEKNIS (SQL SCRIPT)

Mas Toro, silakan gunakan skrip ini untuk menggantikan logika *Percentile* yang lama.

```sql
/*
   ALGORITMA CINCIN API V2.0 - Z-SCORE METHOD
   Platform: SQL Standard (PostgreSQL/MySQL/SQL Server)
*/

-- LANGKAH 1: HITUNG STATISTIK BASELINE PER BLOK
WITH Statistik_Blok AS (
    SELECT 
        kode_blok,
        AVG(ndre_value) as rata_rata,
        STDDEV(ndre_value) as deviasi
    FROM Tabel_Data_Drone
    GROUP BY kode_blok
),

-- LANGKAH 2: HITUNG Z-SCORE SETIAP POHON
Data_ZScore AS (
    SELECT 
        d.id_pohon,
        d.kode_blok,
        d.no_baris,
        d.no_pokok,
        d.ndre_value,
        -- Rumus Z-Score
        (d.ndre_value - s.rata_rata) / NULLIF(s.deviasi, 0) as z_score
    FROM Tabel_Data_Drone d
    JOIN Statistik_Blok s ON d.kode_blok = s.kode_blok
),

-- LANGKAH 3: TENTUKAN KANDIDAT PUSAT (CORE SUSPECT)
-- Kita hanya curiga pada pohon yang menyimpang jauh (misal: -1.5 SD)
Kandidat_Suspect AS (
    SELECT * 
    FROM Data_ZScore
    WHERE z_score < -1.5  -- << VARIABLE TUNING UTAMA
),

-- LANGKAH 4: CEK LINGKUNGAN SEKITAR (SPATIAL CHECK)
Analisis_Final AS (
    SELECT 
        Pusat.id_pohon,
        Pusat.kode_blok,
        Pusat.no_baris,
        Pusat.no_pokok,
        Pusat.z_score,
        
        -- Hitung berapa tetangga yang kondisinya 'Mencurigakan' (Z-Score < -0.5)
        -- Tetangga tidak harus mati, cukup menunjukkan gejala stres ringan.
        (
            SELECT COUNT(*)
            FROM Data_ZScore AS Tetangga
            WHERE Tetangga.kode_blok = Pusat.kode_blok
              -- Logika Grid 3x3
              AND Tetangga.no_baris BETWEEN Pusat.no_baris - 1 AND Pusat.no_baris + 1
              AND Tetangga.no_pokok BETWEEN Pusat.no_pokok - 1 AND Pusat.no_pokok + 1
              AND Tetangga.id_pohon <> Pusat.id_pohon
              -- Syarat Tetangga: Stres Ringan
              AND Tetangga.z_score < -0.5 
        ) as jumlah_tetangga_stres

    FROM Kandidat_Suspect AS Pusat
)

-- OUTPUT UNTUK DASHBOARD
SELECT 
    *,
    CASE 
        -- Jika Z-Score hancur DAN punya tetangga stres = VALID GANODERMA
        WHEN jumlah_tetangga_sres >= 2 THEN 'MERAH (KLUSTER AKTIF)'
        WHEN jumlah_tetangga_stres >= 1 THEN 'KUNING (INDIKASI AWAL)'
        -- Jika sendirian = NOISE
        ELSE 'ABAIKAN (NOISE/SOLITER)'
    END as status_validasi
FROM Analisis_Final
WHERE jumlah_tetangga_stres >= 1 -- Filter noise dari laporan akhir
ORDER BY z_score ASC;
```

---

## 4. PANDUAN KALIBRASI (TUNING GUIDE)

Setelah skrip dijalankan, Toro harus melihat hasilnya di peta. Jika hasilnya masih belum pas, lakukan *tuning* hanya pada satu angka: **Batas Z-Score (Langkah 3)**.

| Setting Z-Score | Karakteristik | Kapan Digunakan? |
| :--- | :--- | :--- |
| **< -1.0** | **Sangat Agresif.** Akan menangkap banyak pohon, termasuk yang hanya kurang pupuk sedikit. | Gunakan jika ingin mendeteksi G1 sedini mungkin (risiko *False Positive* tinggi). |
| **< -1.5** | **Seimbang (Rekomendasi Awal).** Menangkap anomali nyata yang signifikan. | Gunakan sebagai standar *default*. |
| **< -2.0** | **Sangat Konservatif.** Hanya menangkap pohon yang kondisinya sangat buruk/mati. | Gunakan jika sumber daya validasi lapangan sangat terbatas (hanya cari G3/G4). |

---

## 5. INTERPRETASI HASIL BARU (UNTUK MANAJEMEN)

Dengan metode baru ini, narasi kita ke Wk. Direktur berubah menjadi lebih kuat:

1.  **Bukan "Terbawah 20%"**: "Pak, sistem ini tidak asal ambil 20% terbawah. Sistem ini mencari **Anomali Statistik**."
2.  **Adaptif**: "Di blok yang sehat, sistem ini akan melaporkan **NOL kasus**. Dia tidak memaksa mencari penyakit yang tidak ada."
3.  **Terverifikasi Tetangga**: "Setiap titik merah di peta ini sudah divalidasi oleh algoritma bahwa **tetangganya juga stres**. Ini bukan error drone, ini pola penularan nyata."

Metode ini akan drastis menurunkan *False Positive* (Over-detect) dan membuat daftar target menjadi jauh lebih *manageable* dan akurat bagi tim lapangan.