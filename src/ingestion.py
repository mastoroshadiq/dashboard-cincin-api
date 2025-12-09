"""
POAC v3.3 - Data Ingestion & Cleaning Module
Implements FR-01: Data Ingestion & Cleaning

FR-01.1: Sistem harus mampu membaca file format .csv
FR-01.2: Sistem harus memvalidasi keberadaan kolom wajib
FR-01.3: Data dengan koordinat null atau NDRE non-numerik harus dibuang
"""

import pandas as pd
import logging
from pathlib import Path
import sys

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
    """
    df_clean = df.copy()
    
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
    
    logger.info(f"Data integrity validated: {stats['total_rows']} trees in {stats['total_blocks']} blocks")
    
    return stats
