# Z-Score Threshold Calibration Report
## Population Segmentation & Calibrated Detection

**Generated**: 2025-12-15

---

## 1. Executive Summary

Analisis kalibrasi threshold Z-Score berhasil dilakukan untuk meningkatkan akurasi deteksi Ganoderma. Threshold terkalibrasi berbeda antara AME II dan AME IV berdasarkan karakteristik masing-masing kebun.

### Calibrated Thresholds:

| Divisi | Standard | **Calibrated** | MAE Improvement |
|--------|----------|----------------|-----------------|
| **AME II (AME002)** | Z < -2.0 | **Z < -1.5** | Optimal at 2.93% |
| **AME IV (AME004)** | Z < -2.0 | **Z < -4.0** | +11.93% (14.18% → 2.25%) |

---

## 2. Population Segmentation

Sebelum deteksi, data drone dikategorikan berdasarkan kolom `Keterangan`:

| Category | AME II | AME IV | Perlakuan |
|----------|--------|--------|-----------|
| **MATURE** | 94,201 (99%) | 68,372 (83%) | Z-Score Calculation |
| **YOUNG** | 787 (0.8%) | 4,700 (5.7%) | Force G1 (Monitor) |
| **DEAD** | 42 (0.04%) | 65 (0.08%) | Force G4 (Source) |
| **EMPTY** | 0 | 8,825 (10.8%) | Exclude |

**Catatan**: 
- Hanya pohon **MATURE** yang digunakan untuk baseline Z-Score
- YOUNG (Sisip) dikecualikan dari baseline karena NDRE rendah (kanopi kecil)
- EMPTY menunjukkan lokasi tanpa pohon

---

## 3. Calibration Methodology

### 3.1 Approach
1. Test multiple Z-Score thresholds: -0.5 sampai -5.0
2. Calculate detection rate per blok
3. Compare dengan Ground Truth (% Serangan Ganoderma dari sensus)
4. Minimize MAE (Mean Absolute Error)

### 3.2 Ground Truth Source
File: `areal_inti_serangan_gano_AMEII_AMEIV.xlsx`
- TOTAL_PKK: Total pohon per blok
- TOTAL_GANO: Total pohon terinfeksi Ganoderma
- % Serangan: TOTAL_GANO / TOTAL_PKK × 100

---

## 4. Results

### 4.1 AME II (AME002)

| Threshold | MAE | Correlation | Algo % | GT % |
|-----------|-----|-------------|--------|------|
| Z < -1.0 | 8.55% | 0.179 | 15.43% | 6.32% |
| **Z < -1.5** | **2.93%** | 0.360 | **7.00%** | 6.32% |
| Z < -2.0 | 3.50% | 0.524 | 3.08% | 6.32% |
| Z < -2.5 | 5.05% | 0.588 | 1.27% | 6.32% |

**Optimal: Z < -1.5**
- MAE terbaik: 2.93%
- Detection rate (7.00%) mendekati GT (6.32%)
- Sedikit over-detect lebih baik daripada under-detect

### 4.2 AME IV (AME004)

| Threshold | MAE | Correlation | Algo % | GT % |
|-----------|-----|-------------|--------|------|
| Z < -2.0 | 14.18% | -0.07 | 17.99% | 3.84% |
| Z < -3.0 | 5.65% | 0.28 | 5.60% | 3.84% |
| **Z < -4.0** | **2.25%** | 0.37 | **1.79%** | 3.84% |
| Z < -5.0 | 3.05% | 0.02 | 0.79% | 3.84% |

**Optimal: Z < -4.0**
- MAE improvement: 14.18% → 2.25% (+11.93%)
- Correlation: -0.07 → 0.37 (+0.44)
- AME IV butuh threshold ketat karena:
  - Tingkat serangan rendah (3.84%)
  - Data lebih homogen
  - Banyak tanaman muda

---

## 5. Implementation

### 5.1 Config (`config.py`)

```python
CALIBRATED_THRESHOLDS = {
    "AME002": {
        "Z_Threshold_G3": -1.5,
        "Z_Threshold_G2": -0.75,
    },
    "AME004": {
        "Z_Threshold_G3": -4.0,
        "Z_Threshold_G2": -2.5,
    }
}
```

### 5.2 Usage

```python
from config import get_calibrated_threshold

# Get threshold for specific divisi
threshold = get_calibrated_threshold("AME002")
z_g3 = threshold["Z_Threshold_G3"]  # -1.5
```

---

## 6. Key Findings

1. **One-size-fits-all tidak bekerja**: Setiap kebun butuh threshold berbeda
2. **Usia dan tingkat serangan mempengaruhi threshold optimal**
3. **Population segmentation penting**: YOUNG harus dipisah dari baseline
4. **AME IV memiliki 10.8% EMPTY** menunjukkan data quality issue

---

## 7. Output Files

- `data/output/calibrated_analysis/AME002_report.html`
- `data/output/calibrated_analysis/AME004_report.html`
- `data/output/calibrated_analysis/summary.csv`
- `data/output/z_score_calibration/AME002_calibration.csv`
- `data/output/z_score_calibration/AME004_calibration.csv`

---

## 8. Recommendations

1. **Use calibrated thresholds** untuk analisis Cincin Api
2. **Re-calibrate periodically** saat kondisi kebun berubah
3. **Investigate AME IV EMPTY data** untuk perbaikan data quality
4. **Consider separate baselines** untuk kebun multi-generasi
