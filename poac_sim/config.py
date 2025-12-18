"""
POAC v3.3 - Simulation Engine Configuration
Definisi Skenario dan Parameter Tunable

Referensi: BACKEND_TUNABLE_PARAMS_V3.3.md
"""

# =============================================================================
# SCENARIO DEFINITIONS (TUNABLE VARIABLES)
# =============================================================================
# Z_Threshold_G3: Ambang batas Z-Score untuk klasifikasi G3 (Terinfeksi Berat)
# Z_Threshold_G2: Ambang batas Z-Score untuk klasifikasi G2 (Terinfeksi Sedang)
# Semakin rendah threshold (lebih negatif) = semakin ketat deteksi (hanya outlier ekstrem)
# Semakin tinggi threshold (mendekati 0) = semakin sensitif (lebih banyak terdeteksi)

SCENARIOS = [
    {
        "name": "Skenario 1 - Hemat",
        "description": "Hanya deteksi outlier ekstrem. Cocok untuk budget terbatas.",
        "Z_Threshold_G3": -2.5,
        "Z_Threshold_G2": -1.5
    },
    {
        "name": "Skenario 2 - Seimbang",
        "description": "Rekomendasi Baseline. Sesuai standar statistik (2.5% tail).",
        "Z_Threshold_G3": -2.0,
        "Z_Threshold_G2": -1.0
    },
    {
        "name": "Skenario 3 - Perang",
        "description": "Sangat sensitif. Proteksi maksimum terhadap Ganoderma.",
        "Z_Threshold_G3": -1.5,
        "Z_Threshold_G2": -0.5
    }
]

# =============================================================================
# CALIBRATED THRESHOLDS (Based on Census Ground Truth)
# =============================================================================
# Threshold terkalibrasi berdasarkan data sensus Ganoderma.
# Kalibrasi dilakukan untuk meminimalkan MAE antara deteksi algoritma
# dan ground truth % serangan.
#
# AME II (AME002): Z < -1.5 -> Lebih sensitif karena:
#   - Tingkat serangan lebih tinggi (6.28%)
#   - Tanaman lebih tua (2008-2009)
#
# AME IV (AME004): Z < -4.0 -> Lebih ketat karena:
#   - Tingkat serangan lebih rendah (3.84%)
#   - Data lebih homogen (std dev lebih kecil)
#   - Tanaman lebih muda dan bervariasi (2010-2025)

CALIBRATED_THRESHOLDS = {
    "AME002": {
        "Z_Threshold_G3": -1.5,  # Calibrated - best MAE 2.93%
        "Z_Threshold_G2": -0.75,
        "description": "Calibrated for AME II - MAE: 2.93%, Algo: 7.0% vs GT: 6.3%"
    },
    "AME004": {
        "Z_Threshold_G3": -4.0,  # Calibrated - significant improvement
        "Z_Threshold_G2": -2.5,
        "description": "Calibrated for AME IV - MAE improved from 14.18% to 2.25%"
    },
    # Alias untuk nama alternatif
    "AME II": {
        "Z_Threshold_G3": -1.5,
        "Z_Threshold_G2": -0.75,
        "description": "Alias untuk AME002"
    },
    "AME IV": {
        "Z_Threshold_G3": -4.0,
        "Z_Threshold_G2": -2.5,
        "description": "Alias untuk AME004"
    }
}

def get_calibrated_threshold(divisi: str) -> dict:
    """
    Get calibrated threshold for a specific divisi.
    Falls back to standard threshold if divisi not found.
    """
    # Normalize divisi name
    divisi_norm = divisi.upper().replace(" ", "")
    if divisi_norm in ["AMEII", "AME2"]:
        divisi_norm = "AME002"
    elif divisi_norm in ["AMEIV", "AME4"]:
        divisi_norm = "AME004"
    
    if divisi_norm in CALIBRATED_THRESHOLDS:
        return CALIBRATED_THRESHOLDS[divisi_norm]
    else:
        # Fallback to standard scenario
        return {
            "Z_Threshold_G3": -2.0,
            "Z_Threshold_G2": -1.0,
            "description": "Default (not calibrated)"
        }

# =============================================================================
# DATA CONFIGURATION
# =============================================================================
# Kolom wajib yang harus ada dalam file CSV input (case-insensitive mapping)
REQUIRED_COLUMNS = ["blok", "n_baris", "n_pokok", "ndre125"]

# Column name mapping (CSV column -> internal name)
COLUMN_MAPPING = {
    "blok": "Blok",
    "n_baris": "N_BARIS", 
    "n_pokok": "N_POKOK",
    "ndre125": "NDRE125",
    "divisi": "Divisi",
    "blok_b": "Blok_B",
    "t_tanam": "T_Tanam",
    "objectid": "ObjectID",
    "klassndre12025": "Klass_NDRE",
    "ket": "Keterangan"
}

# Nama kolom yang akan dihasilkan
OUTPUT_COLUMNS = {
    "z_score": "Z_Score",
    "status": "Status_Ganoderma",
    "ring_candidate": "Ring_Candidate"
}

# =============================================================================
# STATUS CLASSIFICATION
# =============================================================================
STATUS_G3 = "G3"  # Terinfeksi Berat - Target Sanitasi
STATUS_G2 = "G2"  # Terinfeksi Sedang - Monitoring Ketat
STATUS_HEALTHY = "Sehat"  # Pohon Sehat

# =============================================================================
# ALGORITMA CINCIN API CONFIGURATION (Tunable Parameters)
# =============================================================================
# Konfigurasi untuk algoritma deteksi kluster Ganoderma berbasis Cincin Api
# Sesuaikan parameter ini berdasarkan kondisi kebun dan tingkat infeksi

CINCIN_API_CONFIG = {
    # --------------------------------------------------------------------------
    # THRESHOLD SIMULATION (Rentang Simulasi untuk Elbow Method)
    # --------------------------------------------------------------------------
    # Persentil minimum untuk simulasi (0.0 - 1.0)
    # Nilai lebih rendah = hanya outlier ekstrem yang dideteksi
    "threshold_min": 0.05,  # 5%
    
    # Persentil maksimum untuk simulasi (0.0 - 1.0)
    # Nilai lebih tinggi = lebih banyak pohon terdeteksi sebagai suspect
    "threshold_max": 0.30,  # 30%
    
    # Increment per step simulasi (0.01 = 1%)
    # Nilai lebih kecil = presisi tinggi tapi lebih lambat
    "threshold_step": 0.05,  # 5%
    
    # --------------------------------------------------------------------------
    # CLUSTERING PARAMETERS
    # --------------------------------------------------------------------------
    # Minimum tetangga sakit untuk dianggap kluster aktif (MERAH)
    # Rentang valid: 1-6 (hexagonal grid punya maksimal 6 tetangga)
    # Nilai 3 = 50% dari tetangga harus sakit
    "min_sick_neighbors": 3,
    
    # Minimum kluster valid untuk threshold dianggap layak
    # Digunakan dalam Elbow Method selection
    "min_clusters_for_valid": 10,
    
    # --------------------------------------------------------------------------
    # ELBOW METHOD TUNING
    # --------------------------------------------------------------------------
    # Metode pemilihan threshold optimal:
    # "efficiency" = Pilih berdasarkan rasio efisiensi tertinggi (OLD - prone to over-detect)
    # "gradient" = Pilih berdasarkan Kneedle algorithm (NEW - recommended)
    "elbow_method": "gradient",  # CHANGED: from efficiency to gradient
    
    # Sensitivitas gradient (deprecated, kept for backward compatibility)
    "gradient_sensitivity": 0.1,
    
    # --------------------------------------------------------------------------
    # CONSENSUS VOTING (Multi-Preset Filter)
    # --------------------------------------------------------------------------
    # Gunakan consensus voting untuk filter hasil dari multiple preset
    "use_consensus": True,
    
    # Minimum preset yang harus setuju untuk pohon dianggap target
    # v3.5: Union voting (1) terbukti efektif: 5,773 deteksi (-3% vs GT)
    "min_votes": 1,  # CHANGED: from 2 to 1 (Union voting)
    
    # --------------------------------------------------------------------------
    # OUTPUT & VISUALIZATION OPTIONS
    # --------------------------------------------------------------------------
    # Jumlah blok terparah untuk visualisasi Top-N
    "top_n_blocks": 10,
    
    # Jumlah target prioritas untuk laporan Mandor
    "top_n_priority_targets": 100,
    
    # Ukuran figure untuk visualisasi (width, height) dalam inches
    "figure_size_main": (24, 16),
    "figure_size_block": (28, 16),
    
    # DPI untuk export gambar
    "figure_dpi": 150,
}

# =============================================================================
# PRESET CONFIGURATIONS
# =============================================================================
# Preset untuk berbagai kondisi kebun

CINCIN_API_PRESETS = {
    "konservatif": {
        # v3.5: RAISE THE FLOOR - Paksa Kneedle mulai dari 8%
        # Target: Menangkap core infection yang lebih luas
        "threshold_min": 0.08,  # 8% (raised from 5%)
        "threshold_max": 0.20,  # 20%
        "threshold_step": 0.01,
        "min_sick_neighbors": 4,
        "description": "v3.5: Raised floor 8%. Deteksi ketat."
    },
    "standar": {
        # v3.5: RAISE THE FLOOR - Ini adalah "Sweet Spot" kita
        # Target: 12-15% threshold untuk ~5,500-7,000 deteksi
        "threshold_min": 0.12,  # 12% (raised from 10%)
        "threshold_max": 0.30,  # 30%
        "threshold_step": 0.01,
        "min_sick_neighbors": 3,
        "description": "v3.5: Raised floor 12%. Sweet spot target."
    },
    "agresif": {
        # v3.5: RAISE THE FLOOR - Upper bound limit
        # Target: 18-20% threshold
        "threshold_min": 0.15,  # 15% (raised from 20%)
        "threshold_max": 0.40,  # 40%
        "threshold_step": 0.01,
        "min_sick_neighbors": 2,
        "description": "v3.5: Raised floor 15%. Upper bound."
    }
}

# =============================================================================
# FILE PATHS
# =============================================================================
DEFAULT_INPUT_PATH = "data/input/tabelNDREnew.csv"
DEFAULT_OUTPUT_PATH = "data/output/"
