"""
POAC v3.3 - Data Ingestion & Cleaning Module
Implements FR-01: Data Ingestion & Cleaning

FR-01.1: Sistem harus mampu membaca file format .csv
FR-01.2: Sistem harus memvalidasi keberadaan kolom wajib
FR-01.3: Data dengan koordinat null atau NDRE non-numerik harus dibuang

Support untuk multiple divisi (AME II, AME IV)
"""

import pandas as pd
import logging
from pathlib import Path
import sys
from typing import List, Dict, Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add parent to path for config import
_parent_dir = Path(__file__).parent.parent
if str(_parent_dir) not in sys.path:
    sys.path.insert(0, str(_parent_dir))

from config import REQUIRED_COLUMNS, COLUMN_MAPPING

# =============================================================================
# TREE CATEGORY CLASSIFICATION (Tri-State Segmentation)
# =============================================================================
# Based on TECHNICAL ENHANCEMENT: LOGIKA SEGMENTASI POPULASI (MATURE, YOUNG, DEAD)
#
# Categories:
# - MATURE: Pokok Utama + Tambahan (Inclusion - Z-Score calculation)
# - YOUNG:  Sisipan (Exclusion - Force G1, NDRE rendah karena kanopi kecil)
# - DEAD:   Mati/Tumbang (Exclusion - Force G4/SOURCE, trigger Cincin Api)
# - EMPTY:  Kosong (Exclusion - Skip, tidak ada pohon)
# =============================================================================

def classify_tree_category(ket_value, ndre_value=None) -> str:
    """
    Klasifikasi kategori pohon berdasarkan kolom Keterangan (Ket).
    
    Mengikuti aturan prioritas dari Technical Enhancement:
    1. Safety Net: NDRE 0/Null -> EMPTY
    2. Label Eksplisit: Mati/Tumbang -> DEAD, Kosong -> EMPTY
    3. Usia Tanam: Sisip -> YOUNG, Utama/Tamb -> MATURE
    4. Default: MATURE
    
    Args:
        ket_value: Nilai dari kolom Ket/Keterangan
        ndre_value: Nilai NDRE (optional, untuk safety net)
        
    Returns:
        str: 'MATURE', 'YOUNG', 'DEAD', atau 'EMPTY'
    """
    # Safety Net: NDRE 0 atau Null -> EMPTY
    if ndre_value is not None:
        import pandas as pd
        if pd.isna(ndre_value) or ndre_value == 0 or str(ndre_value).strip() == '-':
            return 'EMPTY'
    
    # Normalize keterangan
    ket = str(ket_value).lower().strip() if ket_value else ''
    
    # Prioritas 1: Mati/Tumbang -> DEAD
    if 'mati' in ket or 'tumbang' in ket:
        return 'DEAD'
    
    # Prioritas 2: Kosong -> EMPTY  
    if 'kosong' in ket:
        return 'EMPTY'
    
    # Prioritas 3: Sisip -> YOUNG
    if 'sisip' in ket:
        return 'YOUNG'
    
    # Prioritas 4: Utama/Tamb -> MATURE
    if 'utama' in ket or 'tamb' in ket or 'pokok' in ket:
        return 'MATURE'
    
    # Default: MATURE (pohon yang tidak memiliki label spesifik)
    return 'MATURE'


def add_tree_categories(df: pd.DataFrame, ket_column: str = 'ket') -> pd.DataFrame:
    """
    Tambahkan kolom 'Category' ke DataFrame berdasarkan kolom Keterangan.
    
    Args:
        df: DataFrame dengan data pohon
        ket_column: Nama kolom yang berisi keterangan (default: 'ket')
        
    Returns:
        DataFrame dengan kolom 'Category' baru
    """
    df_result = df.copy()
    
    # Find the keterangan column (case-insensitive)
    ket_col = None
    for col in df_result.columns:
        if col.lower() in ['ket', 'keterangan']:
            ket_col = col
            break
    
    if ket_col is None:
        logger.warning("Kolom Keterangan/Ket tidak ditemukan. Semua pohon akan dikategorikan sebagai MATURE.")
        df_result['Category'] = 'MATURE'
        return df_result
    
    # Apply classification
    def classify_row(row):
        ket = row.get(ket_col, '')
        ndre = row.get('NDRE125', None)
        return classify_tree_category(ket, ndre)
    
    df_result['Category'] = df_result.apply(classify_row, axis=1)
    
    # Log distribution
    cat_counts = df_result['Category'].value_counts()
    logger.info(f"Tree category distribution: {cat_counts.to_dict()}")
    
    return df_result


def load_ame_iv_data(filepath: str) -> pd.DataFrame:
    """
    Load dan preprocess data AME IV yang memiliki format berbeda.
    
    AME IV format aktual dari CSV (setelah dibaca dengan sep=';'):
    - DIVISI = "AME"
    - Blok = "IV"  
    - BLOK_B = kode blok singkat (A12, A13, dll)
    - T_TANAM = kode blok lengkap (A012A)
    - N_BARIS = tahun tanam (2016)
    - N_POKOK = nomor baris (1, 2, 3...)
    - OBJECTID = nomor pokok (1.0, 2.0...)
    - NDRE125 = object id (9801, 9802...)
    - KlassNDRE12025 = nilai NDRE dengan koma desimal (0,351342266)
    - Ket = kelas stres (Stres)
    - Unnamed:10 = severity (Berat, Sedang, Ringan)
    - Unnamed:11 = tipe (Pokok, Sisip)
    - Unnamed:12 = status (Utama)
    """
    logger.info(f"Loading AME IV data from: {filepath}")
    
    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"File tidak ditemukan: {filepath}")
    
    # Read with semicolon delimiter
    df = pd.read_csv(filepath, sep=';')
    initial_count = len(df)
    logger.info(f"AME IV data loaded: {initial_count} rows")
    
    # Fix column mapping based on actual AME IV format
    # Data shift: DIVISI=AME, Blok=IV (ini seharusnya digabung)
    # BLOK_B = actual block code (A12)
    # N_BARIS = tahun (2016) -> skip
    # N_POKOK = actual n_baris
    # OBJECTID = actual n_pokok
    # NDRE125 = object id
    # KlassNDRE12025 = actual NDRE value (dengan koma desimal)
    # Unnamed:11 = tipe pohon (Pokok/Sisip)
    # Unnamed:12 = status (Utama)
    
    # Build Keterangan column from Unnamed:11 and Unnamed:12
    # Format: "Pokok Utama" atau "Sisip" 
    def build_keterangan(row):
        tipe = str(row.get('Unnamed: 11', '')).strip() if pd.notna(row.get('Unnamed: 11')) else ''
        status = str(row.get('Unnamed: 12', '')).strip() if pd.notna(row.get('Unnamed: 12')) else ''
        
        if tipe.lower() == 'pokok' and status.lower() == 'utama':
            return 'Pokok Utama'
        elif 'sisip' in tipe.lower():
            return 'Sisip'
        elif 'mati' in tipe.lower() or 'mati' in status.lower():
            return 'Mati'
        elif tipe:
            return f"{tipe} {status}".strip()
        else:
            return ''
    
    df['Keterangan'] = df.apply(build_keterangan, axis=1)
    
    df_fixed = pd.DataFrame({
        'Divisi': 'AME IV',
        'Blok': df['BLOK_B'],  # A12, A13, dll
        'N_BARIS': pd.to_numeric(df['N_POKOK'], errors='coerce'),  # nomor baris
        'N_POKOK': pd.to_numeric(df['OBJECTID'], errors='coerce'),  # nomor pokok
        'NDRE125': df['KlassNDRE12025'].astype(str).str.replace(',', '.'),  # NDRE value
        'Keterangan': df['Keterangan'],  # Tipe pohon (Pokok Utama/Sisip)
    })
    
    # Convert NDRE to numeric
    df_fixed['NDRE125'] = pd.to_numeric(df_fixed['NDRE125'], errors='coerce')
    
    # Drop rows with NaN in essential columns
    before_drop = len(df_fixed)
    df_fixed = df_fixed.dropna(subset=['N_BARIS', 'N_POKOK', 'NDRE125', 'Blok'])
    after_drop = len(df_fixed)
    if before_drop > after_drop:
        logger.warning(f"Dropped {before_drop - after_drop} rows with NaN values")
    
    # Convert to int for N_BARIS and N_POKOK
    df_fixed['N_BARIS'] = df_fixed['N_BARIS'].astype(int)
    df_fixed['N_POKOK'] = df_fixed['N_POKOK'].astype(int)
    
    # Add tree category classification (MATURE, YOUNG, DEAD, EMPTY)
    df_fixed = add_tree_categories(df_fixed)
    
    # Log keterangan distribution
    ket_counts = df_fixed['Keterangan'].value_counts()
    logger.info(f"AME IV Keterangan distribution: {ket_counts.head().to_dict()}")
    
    logger.info(f"AME IV columns mapped: {df_fixed.columns.tolist()}")
    logger.info(f"Sample NDRE125: {df_fixed['NDRE125'].head()}")
    logger.info(f"AME IV data ready: {len(df_fixed)} rows")
    
    return df_fixed


def load_multiple_divisi(file_paths: Dict[str, str]) -> pd.DataFrame:
    """
    Load dan gabungkan data dari multiple divisi.
    
    Args:
        file_paths: Dictionary {divisi_name: file_path}
                   Contoh: {"AME II": "data/input/tabelNDREnew.csv", 
                           "AME IV": "data/input/AME_IV.csv"}
    
    Returns:
        pd.DataFrame: Gabungan data dari semua divisi
    """
    all_data = []
    
    for divisi_name, filepath in file_paths.items():
        logger.info(f"Loading {divisi_name} from {filepath}")
        
        if "AME_IV" in str(filepath) or "ame_iv" in str(filepath).lower():
            # Special handling for AME IV format
            df = load_ame_iv_data(filepath)
        else:
            # Standard format (AME II)
            df = load_and_clean_data(filepath)
        
        all_data.append(df)
        logger.info(f"{divisi_name}: {len(df)} rows loaded")
    
    # Concatenate all data
    df_combined = pd.concat(all_data, ignore_index=True)
    logger.info(f"Total combined: {len(df_combined)} rows from {len(file_paths)} divisi")
    
    return df_combined


def load_and_clean_data(filepath: str) -> pd.DataFrame:
    """
    Load CSV file and perform data cleaning according to FR-01 specifications.
    
    Args:
        filepath: Path to the CSV file (tableNDRE.csv)
        
    Returns:
        pd.DataFrame: Cleaned DataFrame ready for processing
        
    Raises:
        FileNotFoundError: If the CSV file doesn't exist
        ValueError: If required columns are missing
    """
    logger.info(f"Loading data from: {filepath}")
    
    # FR-01.1: Read CSV file
    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"File tidak ditemukan: {filepath}")
    
    df = pd.read_csv(filepath)
    initial_count = len(df)
    logger.info(f"Data loaded: {initial_count} rows")
    
    # Normalize column names to lowercase for matching
    df.columns = df.columns.str.lower()
    
    # FR-01.2: Validate required columns (case-insensitive)
    df_cols_lower = [col.lower() for col in df.columns]
    missing_cols = [col for col in REQUIRED_COLUMNS if col.lower() not in df_cols_lower]
    if missing_cols:
        raise ValueError(
            f"Kolom wajib tidak ditemukan: {missing_cols}\n"
            f"Kolom yang tersedia: {list(df.columns)}"
        )
    logger.info(f"Validasi kolom berhasil: {REQUIRED_COLUMNS}")
    
    # Rename columns to standard names
    rename_map = {k.lower(): v for k, v in COLUMN_MAPPING.items() if k.lower() in df.columns}
    df = df.rename(columns=rename_map)
    
    # FR-01.3: Clean data - drop null coordinates and non-numeric NDRE
    df_clean = _clean_data(df)
    
    final_count = len(df_clean)
    dropped_count = initial_count - final_count
    
    if dropped_count > 0:
        logger.warning(f"Data dibuang (dropped): {dropped_count} rows ({dropped_count/initial_count*100:.2f}%)")
    
    logger.info(f"Data siap diproses: {final_count} rows")
    
    return df_clean


def _clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Internal function to clean data according to FR-01.3.
    
    Removes:
    - Rows with null N_BARIS (koordinat baris)
    - Rows with null N_POKOK (koordinat pokok)
    - Rows with non-numeric NDRE125
    - Rows with Divisi = "AME II Total" or "Grand Total" (summary rows)
    
    Adds:
    - Category column based on Keterangan (MATURE, YOUNG, DEAD, EMPTY)
    """
    df_clean = df.copy()
    
    # Filter out summary rows (AME II Total, Grand Total)
    if 'Divisi' in df_clean.columns:
        summary_rows = df_clean['Divisi'].isin(['AME II Total', 'Grand Total', 'AME IV Total'])
        summary_count = summary_rows.sum()
        if summary_count > 0:
            logger.info(f"Menghapus {summary_count} baris summary (Total rows)")
            df_clean = df_clean[~summary_rows]
    
    # Check for null coordinates
    null_baris = df_clean['N_BARIS'].isnull().sum()
    null_pokok = df_clean['N_POKOK'].isnull().sum()
    
    if null_baris > 0:
        logger.warning(f"Ditemukan {null_baris} baris dengan N_BARIS null")
    if null_pokok > 0:
        logger.warning(f"Ditemukan {null_pokok} baris dengan N_POKOK null")
    
    # Drop null coordinates
    df_clean = df_clean.dropna(subset=['N_BARIS', 'N_POKOK'])
    
    # Convert NDRE125 to numeric, coerce errors to NaN
    df_clean['NDRE125'] = pd.to_numeric(df_clean['NDRE125'], errors='coerce')
    
    # Check for non-numeric NDRE
    null_ndre = df_clean['NDRE125'].isnull().sum()
    if null_ndre > 0:
        logger.warning(f"Ditemukan {null_ndre} baris dengan NDRE125 non-numerik atau null")
    
    # Drop null NDRE
    df_clean = df_clean.dropna(subset=['NDRE125'])
    
    # Ensure coordinate columns are integers
    df_clean['N_BARIS'] = df_clean['N_BARIS'].astype(int)
    df_clean['N_POKOK'] = df_clean['N_POKOK'].astype(int)
    
    # Add tree category classification (MATURE, YOUNG, DEAD, EMPTY)
    df_clean = add_tree_categories(df_clean)
    
    # Reset index
    df_clean = df_clean.reset_index(drop=True)
    
    return df_clean


def validate_data_integrity(df: pd.DataFrame) -> dict:
    """
    Validate data integrity and return statistics.
    
    Args:
        df: Cleaned DataFrame
        
    Returns:
        dict: Data integrity statistics
    """
    stats = {
        "total_rows": len(df),
        "total_blocks": df['Blok'].nunique(),
        "blocks": df['Blok'].unique().tolist(),
        "ndre_min": df['NDRE125'].min(),
        "ndre_max": df['NDRE125'].max(),
        "ndre_mean": df['NDRE125'].mean(),
        "ndre_std": df['NDRE125'].std(),
        "coordinate_range": {
            "baris_min": df['N_BARIS'].min(),
            "baris_max": df['N_BARIS'].max(),
            "pokok_min": df['N_POKOK'].min(),
            "pokok_max": df['N_POKOK'].max()
        }
    }
    
    # Add divisi info if available
    if 'Divisi' in df.columns:
        stats["divisi_list"] = df['Divisi'].dropna().unique().tolist()
        stats["total_divisi"] = len(stats["divisi_list"])
        stats["divisi_counts"] = df['Divisi'].value_counts().to_dict()
    
    # Add tahun tanam info if available
    if 'T_Tanam' in df.columns:
        stats["tahun_tanam"] = df['T_Tanam'].dropna().unique().tolist()
    
    # Add keterangan info if available
    if 'Keterangan' in df.columns:
        stats["keterangan_counts"] = df['Keterangan'].value_counts().to_dict()
    
    logger.info(f"Data integrity validated: {stats['total_rows']} trees in {stats['total_blocks']} blocks")
    if 'divisi_list' in stats:
        logger.info(f"Divisi: {stats['divisi_list']}")
    
    return stats
