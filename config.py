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
    # "efficiency" = Pilih berdasarkan rasio efisiensi tertinggi (default)
    # "gradient" = Pilih berdasarkan perubahan gradient terbesar
    "elbow_method": "efficiency",
    
    # Sensitivitas gradient (hanya untuk elbow_method="gradient")
    # Nilai lebih tinggi = lebih sensitif terhadap perubahan
    "gradient_sensitivity": 0.1,
    
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
        # Untuk kebun dengan infeksi rendah - deteksi ketat
        "threshold_min": 0.03,
        "threshold_max": 0.15,
        "threshold_step": 0.02,
        "min_sick_neighbors": 4,  # Lebih ketat
        "description": "Deteksi ketat untuk kebun sehat. Hanya kluster padat terdeteksi."
    },
    "standar": {
        # Setting default - seimbang
        "threshold_min": 0.05,
        "threshold_max": 0.30,
        "threshold_step": 0.05,
        "min_sick_neighbors": 3,
        "description": "Setting standar untuk kebun dengan infeksi sedang."
    },
    "agresif": {
        # Untuk kebun dengan infeksi tinggi - deteksi luas
        "threshold_min": 0.10,
        "threshold_max": 0.50,
        "threshold_step": 0.05,
        "min_sick_neighbors": 2,  # Lebih longgar
        "description": "Deteksi luas untuk kebun dengan infeksi tinggi."
    }
}

# =============================================================================
# FILE PATHS
# =============================================================================
DEFAULT_INPUT_PATH = "data/input/tabelNDREnew.csv"
DEFAULT_OUTPUT_PATH = "data/output/"
