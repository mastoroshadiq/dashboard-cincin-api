"""
POAC v3.3 - Clustering Module (Algoritma Cincin Api)
Implementasi dari Panduan Teknis Algoritma Cincin Api

Fitur:
1. Ranking Relatif (Percentile Rank per Blok)
2. Elbow Method Auto-Tuning
3. Deteksi Kluster dengan analisis tetangga (min 3 tetangga sakit)
4. Klasifikasi: MERAH (Kluster Aktif), KUNING (Risiko Tinggi), ORANYE (Noise), HIJAU (Sehat)
"""

import pandas as pd
import numpy as np
import logging
from typing import Tuple, Dict, List
from pathlib import Path
import sys

# Setup logging
logger = logging.getLogger(__name__)

# Add parent to path for config import
_parent_dir = Path(__file__).parent.parent
if str(_parent_dir) not in sys.path:
    sys.path.insert(0, str(_parent_dir))

from src.spatial import get_hex_neighbors
from config import CINCIN_API_CONFIG

# Status Labels
STATUS_MERAH = "MERAH (KLUSTER AKTIF)"
STATUS_KUNING = "KUNING (RISIKO TINGGI)"
STATUS_ORANYE = "ORANYE (NOISE/KENTOSAN)"
STATUS_HIJAU = "HIJAU (SEHAT)"

# Load config values (can be overridden at runtime)
DEFAULT_MIN_SICK_NEIGHBORS = CINCIN_API_CONFIG.get("min_sick_neighbors", 3)
DEFAULT_THRESHOLD_MIN = CINCIN_API_CONFIG.get("threshold_min", 0.05)
DEFAULT_THRESHOLD_MAX = CINCIN_API_CONFIG.get("threshold_max", 0.30)
DEFAULT_THRESHOLD_STEP = CINCIN_API_CONFIG.get("threshold_step", 0.05)
DEFAULT_MIN_CLUSTERS = CINCIN_API_CONFIG.get("min_clusters_for_valid", 10)


def calculate_percentile_rank(df: pd.DataFrame) -> pd.DataFrame:
    """
    LANGKAH 1: NORMALISASI DATA (RANKING RELATIF)
    
    Memberikan nilai persentil (0.0 - 1.0) untuk setiap pohon 
    relatif terhadap bloknya.
    
    Pohon NDRE terendah di blok mendapat nilai 0.0, tertinggi 1.0
    """
    df_result = df.copy()
    
    # Calculate percentile rank per block (ascending - lower NDRE = lower percentile)
    df_result['Ranking_Persentil'] = df_result.groupby('Blok')['NDRE125'].transform(
        lambda x: x.rank(pct=True, method='average')
    )
    
    # Invert so that lowest NDRE gets lowest percentile (closer to 0)
    # rank(pct=True) gives 1 to lowest, we want 0 to lowest
    df_result['Ranking_Persentil'] = 1 - df_result['Ranking_Persentil']
    
    logger.info(f"Percentile rank calculated for {len(df_result)} trees")
    
    return df_result


def count_sick_neighbors(
    df: pd.DataFrame, 
    row_idx: int, 
    threshold: float,
    coord_lookup: Dict
) -> int:
    """
    Menghitung jumlah tetangga yang sakit (di bawah threshold)
    menggunakan grid heksagonal.
    
    Args:
        df: DataFrame dengan Ranking_Persentil
        row_idx: Index baris yang sedang dianalisis
        threshold: Batas ambang persentil (misal 0.1 = 10% terbawah)
        coord_lookup: Dictionary lookup koordinat ke index
        
    Returns:
        int: Jumlah tetangga sakit
    """
    row = df.loc[row_idx]
    blok = row['Blok']
    baris = int(row['N_BARIS'])
    pokok = int(row['N_POKOK'])
    
    # Get hexagonal neighbors
    neighbors = get_hex_neighbors(baris, pokok)
    
    sick_count = 0
    for n_baris, n_pokok in neighbors:
        neighbor_key = (blok, n_baris, n_pokok)
        if neighbor_key in coord_lookup:
            neighbor_idx = coord_lookup[neighbor_key]
            neighbor_percentile = df.loc[neighbor_idx, 'Ranking_Persentil']
            # Tetangga dianggap sakit jika persentilnya <= threshold
            if neighbor_percentile <= threshold:
                sick_count += 1
    
    return sick_count


def simulate_thresholds(
    df: pd.DataFrame, 
    min_threshold: float = None,
    max_threshold: float = None,
    step: float = None,
    min_sick_neighbors: int = None
) -> pd.DataFrame:
    """
    LANGKAH 2-4: SIMULASI & ELBOW METHOD
    
    Mensimulasikan berbagai threshold dan menghitung efisiensi kluster
    untuk menemukan threshold optimal (Elbow Point).
    
    Args:
        df: DataFrame dengan Ranking_Persentil
        min_threshold: Batas bawah simulasi (default dari config)
        max_threshold: Batas atas simulasi (default dari config)
        step: Increment per step (default dari config)
        min_sick_neighbors: Minimum tetangga sakit untuk kluster (default dari config)
    """
    # Use defaults from config if not specified
    min_threshold = min_threshold if min_threshold is not None else DEFAULT_THRESHOLD_MIN
    max_threshold = max_threshold if max_threshold is not None else DEFAULT_THRESHOLD_MAX
    step = step if step is not None else DEFAULT_THRESHOLD_STEP
    min_sick_neighbors = min_sick_neighbors if min_sick_neighbors is not None else DEFAULT_MIN_SICK_NEIGHBORS
    
    logger.info(f"Running threshold simulation from {min_threshold*100:.0f}% to {max_threshold*100:.0f}%")
    
    # Build coordinate lookup
    coord_lookup = {}
    for idx, row in df.iterrows():
        key = (row['Blok'], int(row['N_BARIS']), int(row['N_POKOK']))
        coord_lookup[key] = idx
    
    results = []
    thresholds = np.arange(min_threshold, max_threshold + step, step)
    
    for threshold in thresholds:
        # Get suspects (trees below threshold)
        suspects = df[df['Ranking_Persentil'] <= threshold].copy()
        total_suspect = len(suspects)
        
        if total_suspect == 0:
            continue
        
        # Count sick neighbors for each suspect
        cluster_valid = 0
        for idx in suspects.index:
            sick_neighbors = count_sick_neighbors(df, idx, threshold, coord_lookup)
            if sick_neighbors >= min_sick_neighbors:
                cluster_valid += 1
        
        # Calculate efficiency ratio
        rasio_efisiensi = (cluster_valid / total_suspect) * 100 if total_suspect > 0 else 0
        
        results.append({
            'Batas_Ambang': threshold,
            'Persen_Ambang': f"{threshold*100:.0f}%",
            'Total_Suspect': total_suspect,
            'Kluster_Valid': cluster_valid,
            'Rasio_Efisiensi': rasio_efisiensi
        })
        
        logger.debug(f"Threshold {threshold*100:.0f}%: {total_suspect} suspects, {cluster_valid} clusters, {rasio_efisiensi:.2f}% efficiency")
    
    return pd.DataFrame(results)


def find_optimal_threshold(
    simulation_df: pd.DataFrame, 
    min_clusters: int = None,
    method: str = None
) -> float:
    """
    LANGKAH 5: MEMILIH THRESHOLD PEMENANG (AUTO-TUNING)
    
    Memilih threshold dengan rasio efisiensi tertinggi,
    dengan syarat minimal memiliki min_clusters kluster valid.
    
    Args:
        simulation_df: DataFrame hasil simulasi threshold
        min_clusters: Minimum kluster valid (default dari config)
        method: Metode pemilihan - "efficiency" atau "gradient" (default dari config)
    """
    # Use defaults from config if not specified
    min_clusters = min_clusters if min_clusters is not None else DEFAULT_MIN_CLUSTERS
    method = method if method is not None else CINCIN_API_CONFIG.get("elbow_method", "efficiency")
    
    # Filter by minimum clusters
    valid_df = simulation_df[simulation_df['Kluster_Valid'] >= min_clusters]
    
    if valid_df.empty:
        # Fallback: use threshold with most clusters
        logger.warning(f"No threshold with >={min_clusters} clusters. Using threshold with max clusters.")
        optimal_idx = simulation_df['Kluster_Valid'].idxmax()
        optimal_threshold = simulation_df.loc[optimal_idx, 'Batas_Ambang']
    elif method == "gradient":
        # Gradient-based elbow detection
        valid_df = valid_df.copy()
        valid_df['Gradient'] = valid_df['Rasio_Efisiensi'].diff().abs()
        sensitivity = CINCIN_API_CONFIG.get("gradient_sensitivity", 0.1)
        optimal_idx = valid_df['Gradient'].idxmax()
        optimal_threshold = valid_df.loc[optimal_idx, 'Batas_Ambang']
    else:
        # Default: efficiency-based selection
        optimal_idx = valid_df['Rasio_Efisiensi'].idxmax()
        optimal_threshold = valid_df.loc[optimal_idx, 'Batas_Ambang']
    
    logger.info(f"Optimal threshold found: {optimal_threshold*100:.0f}%")
    
    return optimal_threshold


def classify_trees_with_clustering(
    df: pd.DataFrame, 
    threshold: float,
    min_sick_neighbors: int = None
) -> pd.DataFrame:
    """
    LANGKAH 6: KLASIFIKASI AKHIR
    
    Mengklasifikasikan setiap pohon berdasarkan threshold optimal
    dan jumlah tetangga sakit.
    
    Status:
    - HIJAU (SEHAT): Persentil > threshold
    - MERAH (KLUSTER AKTIF): Persentil <= threshold DAN >= min_sick_neighbors tetangga sakit
    - KUNING (RISIKO TINGGI): Persentil <= threshold DAN 1 s/d (min_sick_neighbors-1) tetangga sakit
    - ORANYE (NOISE/KENTOSAN): Persentil <= threshold DAN 0 tetangga sakit
    
    Args:
        df: DataFrame dengan Ranking_Persentil
        threshold: Batas ambang persentil optimal
        min_sick_neighbors: Minimum tetangga sakit untuk MERAH (default dari config)
    """
    # Use default from config if not specified
    min_sick_neighbors = min_sick_neighbors if min_sick_neighbors is not None else DEFAULT_MIN_SICK_NEIGHBORS
    
    df_result = df.copy()
    
    # Build coordinate lookup
    coord_lookup = {}
    for idx, row in df_result.iterrows():
        key = (row['Blok'], int(row['N_BARIS']), int(row['N_POKOK']))
        coord_lookup[key] = idx
    
    # Initialize columns
    df_result['Jumlah_Tetangga_Sakit'] = 0
    df_result['Status_Risiko'] = STATUS_HIJAU
    df_result['Skor_Kepadatan_Kluster'] = 0
    
    # Get suspects
    suspect_mask = df_result['Ranking_Persentil'] <= threshold
    suspect_indices = df_result[suspect_mask].index
    
    logger.info(f"Classifying {len(suspect_indices)} suspect trees with threshold {threshold*100:.0f}%")
    
    # Count sick neighbors for all suspects
    for idx in suspect_indices:
        sick_neighbors = count_sick_neighbors(df_result, idx, threshold, coord_lookup)
        df_result.loc[idx, 'Jumlah_Tetangga_Sakit'] = sick_neighbors
        df_result.loc[idx, 'Skor_Kepadatan_Kluster'] = sick_neighbors
        
        # Classify based on neighbor count (using configurable threshold)
        if sick_neighbors >= min_sick_neighbors:
            df_result.loc[idx, 'Status_Risiko'] = STATUS_MERAH
        elif sick_neighbors >= 1:
            df_result.loc[idx, 'Status_Risiko'] = STATUS_KUNING
        else:
            df_result.loc[idx, 'Status_Risiko'] = STATUS_ORANYE
    
    # Log statistics
    status_counts = df_result['Status_Risiko'].value_counts()
    logger.info(f"Classification complete: {status_counts.to_dict()}")
    
    return df_result


def run_cincin_api_algorithm(
    df: pd.DataFrame,
    auto_tune: bool = True,
    manual_threshold: float = None,
    config_override: Dict = None
) -> Tuple[pd.DataFrame, Dict]:
    """
    Menjalankan algoritma Cincin Api lengkap.
    
    Args:
        df: DataFrame dengan data NDRE
        auto_tune: Gunakan Elbow Method untuk auto-tuning
        manual_threshold: Override threshold manual (0.0-1.0)
        config_override: Override konfigurasi (dict dengan keys dari CINCIN_API_CONFIG)
                        Contoh: {"min_sick_neighbors": 4, "threshold_max": 0.40}
        
    Returns:
        Tuple of (classified_df, metadata)
    """
    # Merge config override
    config = CINCIN_API_CONFIG.copy()
    if config_override:
        config.update(config_override)
        logger.info(f"Config override applied: {config_override}")
    
    # Extract parameters from config
    threshold_min = config.get("threshold_min", DEFAULT_THRESHOLD_MIN)
    threshold_max = config.get("threshold_max", DEFAULT_THRESHOLD_MAX)
    threshold_step = config.get("threshold_step", DEFAULT_THRESHOLD_STEP)
    min_sick_neighbors = config.get("min_sick_neighbors", DEFAULT_MIN_SICK_NEIGHBORS)
    min_clusters = config.get("min_clusters_for_valid", DEFAULT_MIN_CLUSTERS)
    elbow_method = config.get("elbow_method", "efficiency")
    
    logger.info("=" * 60)
    logger.info("ALGORITMA CINCIN API v1.0")
    logger.info("=" * 60)
    logger.info(f"Config: threshold_range=[{threshold_min*100:.0f}%-{threshold_max*100:.0f}%], "
                f"step={threshold_step*100:.0f}%, min_sick_neighbors={min_sick_neighbors}")
    
    # Step 1: Calculate percentile rank
    df_ranked = calculate_percentile_rank(df)
    
    # Step 2-5: Simulate and find optimal threshold
    if auto_tune and manual_threshold is None:
        simulation_df = simulate_thresholds(
            df_ranked,
            min_threshold=threshold_min,
            max_threshold=threshold_max,
            step=threshold_step,
            min_sick_neighbors=min_sick_neighbors
        )
        optimal_threshold = find_optimal_threshold(
            simulation_df,
            min_clusters=min_clusters,
            method=elbow_method
        )
    else:
        optimal_threshold = manual_threshold if manual_threshold else 0.10
        simulation_df = None
    
    # Step 6: Classify trees
    df_classified = classify_trees_with_clustering(
        df_ranked, 
        optimal_threshold,
        min_sick_neighbors=min_sick_neighbors
    )
    
    # Prepare metadata
    status_counts = df_classified['Status_Risiko'].value_counts().to_dict()
    
    metadata = {
        'optimal_threshold': optimal_threshold,
        'optimal_threshold_pct': f"{optimal_threshold*100:.0f}%",
        'total_trees': len(df_classified),
        'status_counts': status_counts,
        'merah_count': status_counts.get(STATUS_MERAH, 0),
        'kuning_count': status_counts.get(STATUS_KUNING, 0),
        'oranye_count': status_counts.get(STATUS_ORANYE, 0),
        'hijau_count': status_counts.get(STATUS_HIJAU, 0),
        'simulation_data': simulation_df
    }
    
    logger.info(f"Threshold Optimal: {metadata['optimal_threshold_pct']}")
    logger.info(f"MERAH (Kluster Aktif): {metadata['merah_count']}")
    logger.info(f"KUNING (Risiko Tinggi): {metadata['kuning_count']}")
    logger.info(f"ORANYE (Noise): {metadata['oranye_count']}")
    logger.info(f"HIJAU (Sehat): {metadata['hijau_count']}")
    
    return df_classified, metadata


def get_priority_targets(df: pd.DataFrame, top_n: int = 100) -> pd.DataFrame:
    """
    Mendapatkan daftar target prioritas untuk Mandor.
    
    Diurutkan berdasarkan:
    1. Status (MERAH lebih prioritas)
    2. Skor Kepadatan Kluster (lebih tinggi = lebih prioritas)
    """
    # Filter MERAH dan KUNING saja
    priority_df = df[df['Status_Risiko'].isin([STATUS_MERAH, STATUS_KUNING])].copy()
    
    # Sort by status (MERAH first) then by density score
    status_order = {STATUS_MERAH: 0, STATUS_KUNING: 1}
    priority_df['_status_order'] = priority_df['Status_Risiko'].map(status_order)
    priority_df = priority_df.sort_values(
        ['_status_order', 'Skor_Kepadatan_Kluster'], 
        ascending=[True, False]
    )
    priority_df = priority_df.drop('_status_order', axis=1)
    
    return priority_df.head(top_n)
