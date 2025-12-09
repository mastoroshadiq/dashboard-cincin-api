"""
POAC v3.3 - Statistical Normalization Module
Implements Logika A: Normalisasi Statistik (Adaptive Thresholding)

Sistem tidak boleh menggunakan nilai mentah NDRE (Absolute Float).
Menggunakan Z-Score untuk normalisasi per blok.

Formula: Z = (NDRE_pohon - μ) / σ
"""

import pandas as pd
import numpy as np
import logging
from pathlib import Path
import sys

# Setup logging
logger = logging.getLogger(__name__)

# Add parent to path for config import
_parent_dir = Path(__file__).parent.parent
if str(_parent_dir) not in sys.path:
    sys.path.insert(0, str(_parent_dir))

from config import OUTPUT_COLUMNS, STATUS_G3, STATUS_G2, STATUS_HEALTHY


def calculate_zscore_by_block(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate Z-Score for each tree, grouped by Block (Blok).
    
    Implements Logika A from SRS:
    1. Grouping data per Blok
    2. Hitung Rata-rata (μ) dan Standar Deviasi (σ) untuk blok tersebut
    3. Hitung Z-Score untuk setiap pohon: Z = (NDRE_pohon - μ) / σ
    
    Args:
        df: DataFrame with NDRE125 and Blok columns
        
    Returns:
        pd.DataFrame: DataFrame with added Z_Score column
    """
    df_result = df.copy()
    
    # Calculate Z-Score per block using groupby transform
    df_result[OUTPUT_COLUMNS['z_score']] = df_result.groupby('Blok')['NDRE125'].transform(
        lambda x: _calculate_zscore(x)
    )
    
    logger.info(f"Z-Score calculated for {len(df_result)} trees across {df_result['Blok'].nunique()} blocks")
    
    return df_result


def _calculate_zscore(series: pd.Series) -> pd.Series:
    """
    Calculate Z-Score for a pandas Series.
    
    Formula: Z = (x - μ) / σ
    
    Handles edge case where σ = 0 (all values identical) by returning 0.
    
    Args:
        series: Pandas Series of NDRE values
        
    Returns:
        pd.Series: Z-Score values
    """
    mean = series.mean()
    std = series.std()
    
    # Handle edge case: if std is 0, all values are the same
    if std == 0 or pd.isna(std):
        logger.warning(f"Standard deviation is 0 or NaN. All Z-Scores set to 0.")
        return pd.Series([0.0] * len(series), index=series.index)
    
    z_scores = (series - mean) / std
    return z_scores


def classify_ganoderma_status(
    df: pd.DataFrame, 
    z_threshold_g3: float, 
    z_threshold_g2: float
) -> pd.DataFrame:
    """
    Classify trees into Ganoderma infection status based on Z-Score thresholds.
    
    Classification Logic:
    - G3 (Terinfeksi Berat): Z_Score <= z_threshold_g3
    - G2 (Terinfeksi Sedang): z_threshold_g3 < Z_Score <= z_threshold_g2
    - Sehat: Z_Score > z_threshold_g2
    
    Note: Lower NDRE means worse condition, so negative Z-Scores indicate
    trees performing below block average.
    
    Args:
        df: DataFrame with Z_Score column
        z_threshold_g3: Threshold for G3 classification (e.g., -2.0)
        z_threshold_g2: Threshold for G2 classification (e.g., -1.0)
        
    Returns:
        pd.DataFrame: DataFrame with added Status_Ganoderma column
    """
    df_result = df.copy()
    z_col = OUTPUT_COLUMNS['z_score']
    
    # Ensure Z_Score column exists
    if z_col not in df_result.columns:
        raise ValueError(f"Column '{z_col}' not found. Run calculate_zscore_by_block first.")
    
    # Classify based on thresholds
    conditions = [
        df_result[z_col] <= z_threshold_g3,  # G3: severe infection
        (df_result[z_col] > z_threshold_g3) & (df_result[z_col] <= z_threshold_g2),  # G2: moderate
    ]
    choices = [STATUS_G3, STATUS_G2]
    
    df_result[OUTPUT_COLUMNS['status']] = np.select(
        conditions, 
        choices, 
        default=STATUS_HEALTHY
    )
    
    # Log classification summary
    status_counts = df_result[OUTPUT_COLUMNS['status']].value_counts()
    logger.info(f"Classification complete with thresholds G3={z_threshold_g3}, G2={z_threshold_g2}")
    logger.info(f"Status distribution: {status_counts.to_dict()}")
    
    return df_result


def get_block_statistics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate statistics for each block.
    
    Useful for analysis and debugging.
    
    Args:
        df: DataFrame with NDRE125 and Blok columns
        
    Returns:
        pd.DataFrame: Block-level statistics
    """
    stats = df.groupby('Blok').agg({
        'NDRE125': ['count', 'mean', 'std', 'min', 'max']
    }).round(4)
    
    stats.columns = ['Count', 'Mean_NDRE', 'Std_NDRE', 'Min_NDRE', 'Max_NDRE']
    stats = stats.reset_index()
    
    return stats
