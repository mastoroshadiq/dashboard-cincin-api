"""
Z-Score Spatial Filter v2.0 - Cincin Api Algorithm
===================================================
Metode baru untuk deteksi Ganoderma berdasarkan anomali statistik.

Kelebihan:
- Tidak memaksa menemukan "sakit" pada blok sehat
- Normalisasi per blok
- Validasi tetangga (spatial check)
- Threshold tunable
"""
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def calculate_block_statistics(df: pd.DataFrame, ndre_column: str = 'NDRE125') -> pd.DataFrame:
    """
    Filter 1: Normalisasi Statistik Per Blok
    
    Hitung Mean dan Standard Deviation NDRE per blok.
    """
    stats = df.groupby('Blok').agg({
        ndre_column: ['mean', 'std', 'count']
    }).round(6)
    
    stats.columns = ['Mean_NDRE', 'SD_NDRE', 'Jumlah_Pohon']
    stats = stats.reset_index()
    
    # Handle blocks with SD = 0 (all same value)
    stats['SD_NDRE'] = stats['SD_NDRE'].replace(0, np.nan)
    
    logger.info(f"Calculated statistics for {len(stats)} blocks")
    return stats


def calculate_zscore(df: pd.DataFrame, block_stats: pd.DataFrame, 
                     ndre_column: str = 'NDRE125') -> pd.DataFrame:
    """
    Filter 2: Hitung Z-Score setiap pohon.
    
    Z-Score = (NDRE_Pohon - Mean_Blok) / SD_Blok
    """
    df = df.merge(block_stats[['Blok', 'Mean_NDRE', 'SD_NDRE']], on='Blok', how='left')
    
    # Calculate Z-Score
    df['Z_Score'] = (df[ndre_column] - df['Mean_NDRE']) / df['SD_NDRE']
    
    # Fill NaN Z-Score with 0 (normal)
    df['Z_Score'] = df['Z_Score'].fillna(0)
    
    logger.info(f"Calculated Z-Score for {len(df)} trees")
    logger.info(f"Z-Score range: {df['Z_Score'].min():.2f} to {df['Z_Score'].max():.2f}")
    
    return df


def spatial_validation(df: pd.DataFrame, z_threshold_core: float = -1.5,
                       z_threshold_neighbor: float = -0.5,
                       min_stressed_neighbors: int = 1) -> pd.DataFrame:
    """
    Filter 3: Validasi Tetangga (Spatial Check)
    
    Ganoderma tidak menyerang sendirian. Check tetangga.
    
    Args:
        z_threshold_core: Threshold untuk suspect inti (default -1.5)
        z_threshold_neighbor: Threshold untuk tetangga stres (default -0.5)
        min_stressed_neighbors: Minimum tetangga stres untuk valid (default 1)
    """
    df = df.copy()
    df['is_core_suspect'] = df['Z_Score'] < z_threshold_core
    
    # Build coordinate lookup per block
    stressed_neighbors_count = []
    
    for idx, row in df.iterrows():
        if not row['is_core_suspect']:
            stressed_neighbors_count.append(0)
            continue
        
        blok = row['Blok']
        baris = int(row['N_BARIS'])
        pokok = int(row['N_POKOK'])
        
        # Get neighbors in same block (3x3 grid)
        neighbors = df[
            (df['Blok'] == blok) &
            (df['N_BARIS'].between(baris - 1, baris + 1)) &
            (df['N_POKOK'].between(pokok - 1, pokok + 1)) &
            (df.index != idx)
        ]
        
        # Count stressed neighbors
        stressed = len(neighbors[neighbors['Z_Score'] < z_threshold_neighbor])
        stressed_neighbors_count.append(stressed)
    
    df['Tetangga_Stres'] = stressed_neighbors_count
    
    # Classify based on spatial validation with new labels
    # MERAH (KLUSTER) = Core suspect + >= min_stressed_neighbors
    # ORANYE (INDIKASI) = Core suspect + >= 1 neighbor
    # HIJAU (SEHAT) = Normal
    def classify_zscore(row):
        if not row['is_core_suspect']:
            return 'HIJAU (SEHAT)'
        
        if row['Tetangga_Stres'] >= min_stressed_neighbors:
            return 'MERAH (KLUSTER)'
        elif row['Tetangga_Stres'] >= 1:
            return 'ORANYE (INDIKASI)'
        else:
            return 'HIJAU (SEHAT)'  # Noise treated as healthy
    
    df['Status_ZScore'] = df.apply(classify_zscore, axis=1)
    
    logger.info(f"Spatial validation complete")
    logger.info(f"  MERAH: {len(df[df['Status_ZScore'] == 'MERAH (KLUSTER)'])}")
    logger.info(f"  ORANYE: {len(df[df['Status_ZScore'] == 'ORANYE (INDIKASI)'])}")
    logger.info(f"  HIJAU: {len(df[df['Status_ZScore'] == 'HIJAU (SEHAT)'])}")
    
    return df


def run_zscore_detection(df: pd.DataFrame, 
                         z_threshold: float = -1.5,
                         ndre_column: str = 'NDRE125') -> tuple:
    """
    Main function: Run complete Z-Score Spatial Filter detection.
    
    Args:
        df: Input DataFrame with NDRE values
        z_threshold: Z-Score threshold for core suspect
        ndre_column: Column name for NDRE values
    
    Returns:
        (df_classified, metadata)
    """
    logger.info(f"Running Z-Score Spatial Filter with threshold={z_threshold}")
    
    # Step 1: Block statistics
    block_stats = calculate_block_statistics(df, ndre_column)
    
    # Step 2: Calculate Z-Score
    df_zscore = calculate_zscore(df, block_stats, ndre_column)
    
    # Step 3: Spatial validation
    df_classified = spatial_validation(df_zscore, z_threshold_core=z_threshold)
    
    # Generate metadata
    metadata = {
        'method': 'Z-Score Spatial Filter v2.0',
        'threshold': z_threshold,
        'total_trees': len(df_classified),
        'merah': len(df_classified[df_classified['Status_ZScore'] == 'MERAH (KLUSTER)']),
        'oranye': len(df_classified[df_classified['Status_ZScore'] == 'ORANYE (INDIKASI)']),
        'hijau': len(df_classified[df_classified['Status_ZScore'] == 'HIJAU (SEHAT)']),
        'timestamp': datetime.now().isoformat()
    }
    
    return df_classified, metadata


def run_zscore_comparison(df: pd.DataFrame) -> pd.DataFrame:
    """
    Run comparison across different Z-Score thresholds.
    """
    thresholds = [-1.0, -1.5, -2.0]
    results = []
    
    for thresh in thresholds:
        df_result, meta = run_zscore_detection(df.copy(), z_threshold=thresh)
        results.append({
            'Threshold': thresh,
            'Label': 'Agresif' if thresh == -1.0 else ('Seimbang' if thresh == -1.5 else 'Konservatif'),
            'MERAH': meta['merah'],
            'ORANYE': meta['oranye'],
            'HIJAU': meta['hijau'],
            'Total_Deteksi': meta['merah'] + meta['oranye']
        })
    
    return pd.DataFrame(results)
