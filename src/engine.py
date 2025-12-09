"""
POAC v3.3 - Main Simulation Engine
Implements FR-02: Scenario Runner (Multi-Scenario Simulation)

Core engine that combines all modules to run complete simulation workflow.
"""

import pandas as pd
import logging
from typing import List, Dict, Any
from pathlib import Path
import sys

# Setup logging
logger = logging.getLogger(__name__)

# Add parent directories to path for imports
_current_dir = Path(__file__).parent
_parent_dir = _current_dir.parent
if str(_parent_dir) not in sys.path:
    sys.path.insert(0, str(_parent_dir))
if str(_current_dir) not in sys.path:
    sys.path.insert(0, str(_current_dir))

from src.ingestion import load_and_clean_data, validate_data_integrity
from src.statistics import calculate_zscore_by_block, classify_ganoderma_status, get_block_statistics
from src.spatial import find_ring_candidates, mark_ring_candidates
from config import OUTPUT_COLUMNS, STATUS_G3, STATUS_G2, STATUS_HEALTHY


def run_simulation(
    df: pd.DataFrame,
    scenario_name: str,
    z_threshold_g3: float,
    z_threshold_g2: float
) -> Dict[str, Any]:
    """
    Run single simulation scenario.
    
    Complete workflow:
    1. Calculate Z-Score per block (Logika A)
    2. Classify Ganoderma status based on thresholds
    3. Detect Ring of Fire candidates (Logika B & C)
    4. Generate metrics
    
    Args:
        df: Cleaned DataFrame from ingestion
        scenario_name: Name of the scenario
        z_threshold_g3: Z-Score threshold for G3 classification
        z_threshold_g2: Z-Score threshold for G2 classification
        
    Returns:
        Dict containing:
        - scenario_name: Name of scenario
        - parameters: Threshold values used
        - metrics: Simulation results
        - dataframe: Processed DataFrame
    """
    logger.info(f"=" * 60)
    logger.info(f"Running scenario: {scenario_name}")
    logger.info(f"Parameters: G3_threshold={z_threshold_g3}, G2_threshold={z_threshold_g2}")
    logger.info(f"=" * 60)
    
    # Step 1: Calculate Z-Score per block (Logika A)
    df_zscore = calculate_zscore_by_block(df)
    
    # Step 2: Classify Ganoderma status
    df_classified = classify_ganoderma_status(df_zscore, z_threshold_g3, z_threshold_g2)
    
    # Step 3: Identify G3 trees for Ring Detection
    status_col = OUTPUT_COLUMNS['status']
    g3_trees = df_classified[df_classified[status_col] == STATUS_G3]
    g2_trees = df_classified[df_classified[status_col] == STATUS_G2]
    healthy_trees = df_classified[df_classified[status_col] == STATUS_HEALTHY]
    
    # Step 4: Find Ring of Fire candidates (Logika B & C)
    ring_candidates = find_ring_candidates(df_classified, g3_trees)
    
    # Step 5: Mark ring candidates in DataFrame
    df_final = mark_ring_candidates(df_classified, ring_candidates)
    
    # Calculate metrics
    metrics = {
        "total_trees": len(df_final),
        "g3_count": len(g3_trees),
        "g2_count": len(g2_trees),
        "healthy_count": len(healthy_trees),
        "ring_candidates": len(ring_candidates),
        "total_intervention": len(g3_trees) + len(ring_candidates),  # Beban kerja mandor
        "g3_percentage": round(len(g3_trees) / len(df_final) * 100, 2) if len(df_final) > 0 else 0,
        "ring_percentage": round(len(ring_candidates) / len(df_final) * 100, 2) if len(df_final) > 0 else 0,
    }
    
    logger.info(f"Metrics: G3={metrics['g3_count']}, Ring={metrics['ring_candidates']}, Total Intervensi={metrics['total_intervention']}")
    
    return {
        "scenario_name": scenario_name,
        "parameters": {
            "Z_Threshold_G3": z_threshold_g3,
            "Z_Threshold_G2": z_threshold_g2
        },
        "metrics": metrics,
        "dataframe": df_final,
        "g3_trees": g3_trees,
        "ring_candidates": ring_candidates
    }


def run_multi_scenario(
    df: pd.DataFrame,
    scenarios: List[Dict[str, Any]]
) -> pd.DataFrame:
    """
    Run multiple simulation scenarios and compare results.
    
    Implements FR-02: Scenario Runner
    
    Args:
        df: Cleaned DataFrame from ingestion
        scenarios: List of scenario configurations, each containing:
            - name: Scenario name
            - Z_Threshold_G3: G3 threshold
            - Z_Threshold_G2: G2 threshold
            
    Returns:
        pd.DataFrame: Summary table comparing all scenarios (FR-03.1)
    """
    logger.info("=" * 70)
    logger.info("POAC v3.3 - MULTI-SCENARIO SIMULATION")
    logger.info("=" * 70)
    
    results = []
    detailed_results = []
    
    for scenario in scenarios:
        result = run_simulation(
            df=df,
            scenario_name=scenario['name'],
            z_threshold_g3=scenario['Z_Threshold_G3'],
            z_threshold_g2=scenario['Z_Threshold_G2']
        )
        
        # Collect summary row
        summary_row = {
            "Skenario": result['scenario_name'],
            "Z_Threshold_G3": result['parameters']['Z_Threshold_G3'],
            "Z_Threshold_G2": result['parameters']['Z_Threshold_G2'],
            "Jumlah_G3": result['metrics']['g3_count'],
            "Jumlah_G2": result['metrics']['g2_count'],
            "Jumlah_Sehat": result['metrics']['healthy_count'],
            "Cincin_Api": result['metrics']['ring_candidates'],
            "Total_Intervensi": result['metrics']['total_intervention'],
            "Persen_G3": result['metrics']['g3_percentage'],
            "Persen_Cincin": result['metrics']['ring_percentage']
        }
        results.append(summary_row)
        detailed_results.append(result)
    
    # Create summary DataFrame (FR-03.1)
    summary_df = pd.DataFrame(results)
    
    logger.info("\n" + "=" * 70)
    logger.info("RINGKASAN PERBANDINGAN SKENARIO")
    logger.info("=" * 70)
    print(summary_df.to_string(index=False))
    
    return summary_df, detailed_results


def generate_report(summary_df: pd.DataFrame, detailed_results: List[Dict]) -> str:
    """
    Generate formatted text report comparing scenarios.
    
    Implements FR-03.2: Metrik wajib dalam laporan
    
    Args:
        summary_df: Summary DataFrame from run_multi_scenario
        detailed_results: List of detailed results from each scenario
        
    Returns:
        str: Formatted report string
    """
    report_lines = [
        "=" * 70,
        "LAPORAN SIMULASI POAC v3.3",
        "Decision Support Tool - Ring of Fire & Adaptive NDRE",
        "=" * 70,
        "",
        "METRIK WAJIB (FR-03.2):",
        "-" * 40,
    ]
    
    for idx, row in summary_df.iterrows():
        report_lines.extend([
            f"\n📊 {row['Skenario']}",
            f"   Threshold: G3 ≤ {row['Z_Threshold_G3']}, G2 ≤ {row['Z_Threshold_G2']}",
            f"   ├─ Jumlah G3 (Target Sanitasi): {row['Jumlah_G3']} ({row['Persen_G3']}%)",
            f"   ├─ Jumlah Cincin Api (Target Proteksi): {row['Cincin_Api']} ({row['Persen_Cincin']}%)",
            f"   └─ Total Intervensi (Beban Kerja Mandor): {row['Total_Intervensi']}",
        ])
    
    report_lines.extend([
        "",
        "-" * 40,
        "ANALISIS:",
        f"  • Skenario dengan G3 terbanyak: {summary_df.loc[summary_df['Jumlah_G3'].idxmax(), 'Skenario']}",
        f"  • Skenario dengan Cincin Api terbanyak: {summary_df.loc[summary_df['Cincin_Api'].idxmax(), 'Skenario']}",
        f"  • Skenario dengan Intervensi terendah: {summary_df.loc[summary_df['Total_Intervensi'].idxmin(), 'Skenario']}",
        "",
        "=" * 70,
        "Catatan: Makin rendah threshold (lebih negatif), makin sedikit deteksi.",
        "Makin tinggi threshold (mendekati 0), makin sensitif/agresif deteksi.",
        "=" * 70,
    ])
    
    report = "\n".join(report_lines)
    return report
