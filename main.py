"""
POAC v3.3 - Simulation Engine
Entry Point / Main Script

=================================================================
POAC v3.3 - Simulation Engine (Ring of Fire & Adaptive NDRE)
Decision Support Tool untuk Kalibrasi Parameter Sensitivitas
Deteksi Ganoderma pada Perkebunan Kelapa Sawit
=================================================================

Cara Penggunaan:
    python main.py                          # Gunakan default path
    python main.py path/to/tableNDRE.csv    # Custom input file
    python main.py --visualize              # Dengan visualisasi

Output:
    - Tabel perbandingan skenario di console
    - File CSV hasil simulasi per skenario (opsional)
    - Visualisasi grafik (opsional)
"""

import sys
import logging
import argparse
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from config import SCENARIOS, DEFAULT_INPUT_PATH
from src.ingestion import load_and_clean_data, validate_data_integrity
from src.statistics import get_block_statistics
from src.engine import run_multi_scenario, generate_report

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def main(input_file: str = None, visualize: bool = False, export: bool = False):
    """
    Main entry point for POAC Simulation Engine.
    
    Args:
        input_file: Path to input CSV file. Uses DEFAULT_INPUT_PATH if not provided.
        visualize: Whether to generate visualizations
        export: Whether to export CSV results
    """
    print("\n" + "=" * 70)
    print("🌴 POAC v3.3 - SIMULATION ENGINE")
    print("Ring of Fire & Adaptive NDRE Detection")
    print("=" * 70 + "\n")
    
    # Determine input file path
    if input_file is None:
        input_file = Path(__file__).parent / DEFAULT_INPUT_PATH
    else:
        input_file = Path(input_file)
    
    # =========================================================================
    # STEP 1: Data Ingestion (FR-01)
    # =========================================================================
    print("📂 STEP 1: Data Ingestion & Cleaning")
    print("-" * 40)
    
    try:
        df = load_and_clean_data(input_file)
    except FileNotFoundError as e:
        logger.error(f"❌ {e}")
        logger.info(f"💡 Pastikan file tableNDRE.csv ada di: {input_file}")
        logger.info("💡 Atau berikan path sebagai argument: python main.py <path/to/file.csv>")
        return None
    except ValueError as e:
        logger.error(f"❌ {e}")
        return None
    
    # Validate and show data statistics
    stats = validate_data_integrity(df)
    print(f"\n📊 Data Statistics:")
    print(f"   Total Pohon: {stats['total_rows']:,}")
    print(f"   Total Blok: {stats['total_blocks']}")
    print(f"   NDRE Range: {stats['ndre_min']:.4f} - {stats['ndre_max']:.4f}")
    print(f"   NDRE Mean: {stats['ndre_mean']:.4f}")
    print(f"   NDRE Std: {stats['ndre_std']:.4f}")
    
    # Show block-level statistics (top 10)
    print(f"\n📋 Block Statistics (Top 10 by count):")
    block_stats = get_block_statistics(df)
    print(block_stats.head(10).to_string(index=False))
    
    # =========================================================================
    # STEP 2: Multi-Scenario Simulation (FR-02)
    # =========================================================================
    print("\n" + "=" * 70)
    print("🔬 STEP 2: Multi-Scenario Simulation")
    print("-" * 40)
    
    # Run all scenarios
    summary_df, detailed_results = run_multi_scenario(df, SCENARIOS)
    
    # =========================================================================
    # STEP 3: Generate Report (FR-03)
    # =========================================================================
    print("\n" + "=" * 70)
    print("📈 STEP 3: Final Report")
    print("-" * 40)
    
    report = generate_report(summary_df, detailed_results)
    print(report)
    
    # =========================================================================
    # STEP 4: Visualization (Optional)
    # =========================================================================
    if visualize:
        print("\n" + "=" * 70)
        print("📊 STEP 4: Generating Visualizations")
        print("-" * 40)
        
        try:
            from src.visualization import create_full_visualization_report
            output_dir = Path(__file__).parent / "data" / "output" / "visualizations"
            create_full_visualization_report(summary_df, detailed_results, output_dir)
        except ImportError as e:
            logger.warning(f"⚠️ Visualization module not available: {e}")
            logger.info("💡 Install matplotlib: pip install matplotlib")
    
    # =========================================================================
    # STEP 5: Export Results (Optional)
    # =========================================================================
    if export:
        output_dir = Path(__file__).parent / "data" / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Export summary
        summary_path = output_dir / "simulation_summary.csv"
        summary_df.to_csv(summary_path, index=False)
        print(f"\n📁 Summary exported to: {summary_path}")
        
        # Export detailed results per scenario
        for result in detailed_results:
            scenario_name = result['scenario_name'].replace(" ", "_").replace("-", "_")
            output_path = output_dir / f"hasil_{scenario_name}.csv"
            result['dataframe'].to_csv(output_path, index=False)
            print(f"📁 Detail exported to: {output_path}")
    
    print("\n" + "=" * 70)
    print("✅ Simulasi selesai!")
    print("=" * 70 + "\n")
    
    return summary_df, detailed_results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='POAC v3.3 - Simulation Engine (Ring of Fire & Adaptive NDRE)'
    )
    parser.add_argument(
        'input_file', 
        nargs='?', 
        default=None,
        help='Path to input CSV file (default: data/input/tabelNDREnew.csv)'
    )
    parser.add_argument(
        '-v', '--visualize',
        action='store_true',
        help='Generate visualization charts'
    )
    parser.add_argument(
        '-e', '--export',
        action='store_true',
        help='Export results to CSV files'
    )
    
    args = parser.parse_args()
    main(args.input_file, args.visualize, args.export)
