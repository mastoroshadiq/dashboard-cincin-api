"""
POAC v3.3 - Cincin Api Runner
Entry point untuk menjalankan Algoritma Cincin Api dengan Dashboard

=================================================================
ALGORITMA CINCIN API (Ring of Fire)
- Ranking Relatif per Blok (Percentile Rank)
- Auto-Tuning dengan Elbow Method
- Klasterisasi berbasis tetangga heksagonal
- Klasifikasi: MERAH, KUNING, ORANYE, HIJAU
=================================================================

Cara Penggunaan:
    python run_cincin_api.py                    # Default dengan auto-tune
    python run_cincin_api.py --threshold 0.15   # Manual threshold 15%
    python run_cincin_api.py --no-dashboard     # Tanpa visualisasi
"""

import sys
import logging
import argparse
from pathlib import Path
from datetime import datetime

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from config import DEFAULT_INPUT_PATH, CINCIN_API_CONFIG, CINCIN_API_PRESETS
from src.ingestion import load_and_clean_data, validate_data_integrity
from src.clustering import run_cincin_api_algorithm, get_priority_targets
from src.dashboard import create_dashboard, create_mandor_report
from src.report_generator import generate_readme, generate_html_report


def generate_output_folder_name(preset: str = None, config_override: dict = None, threshold: float = None) -> str:
    """
    Generate nama folder output dengan format:
    YYYYMMDD_HHMM_{preset/custom}_{key_params}
    
    Contoh:
    - 20251209_1530_standar_t30_n3
    - 20251209_1535_agresif_t50_n2
    - 20251209_1540_custom_t20_n4
    """
    # Timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    
    # Determine preset name
    if preset:
        preset_name = preset
    elif config_override:
        preset_name = "custom"
    else:
        preset_name = "standar"
    
    # Get key parameters for folder name
    config = CINCIN_API_CONFIG.copy()
    if preset and preset in CINCIN_API_PRESETS:
        config.update(CINCIN_API_PRESETS[preset])
    if config_override:
        config.update(config_override)
    
    # Build parameter suffix
    if threshold is not None:
        threshold_pct = int(threshold * 100)
    else:
        threshold_pct = int(config.get('threshold_max', 0.30) * 100)
    
    min_neighbors = config.get('min_sick_neighbors', 3)
    
    # Format: timestamp_preset_tXX_nX
    folder_name = f"{timestamp}_{preset_name}_t{threshold_pct}_n{min_neighbors}"
    
    return folder_name


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def main(
    input_file: str = None, 
    threshold: float = None,
    dashboard: bool = True,
    export: bool = True,
    preset: str = None,
    config_override: dict = None
):
    """
    Main entry point untuk Algoritma Cincin Api.
    
    Args:
        input_file: Path ke file CSV input
        threshold: Manual threshold (0.0-1.0), None untuk auto-tune
        dashboard: Generate dashboard visualisasi
        export: Export hasil ke CSV
        preset: Nama preset konfigurasi ("konservatif", "standar", "agresif")
        config_override: Dictionary untuk override konfigurasi
    """
    print("\n" + "=" * 70)
    print("🔥 POAC v3.3 - ALGORITMA CINCIN API")
    print("Deteksi Kluster Ganoderma dengan Auto-Tuning")
    print("=" * 70 + "\n")
    
    # Build config override from preset if specified
    final_config = None
    if preset:
        if preset in CINCIN_API_PRESETS:
            final_config = CINCIN_API_PRESETS[preset].copy()
            print(f"📋 Using preset: {preset.upper()}")
            print(f"   {final_config.get('description', '')}")
        else:
            print(f"⚠️ Unknown preset: {preset}. Using default config.")
            print(f"   Available presets: {list(CINCIN_API_PRESETS.keys())}")
    
    # Apply additional config override
    if config_override:
        if final_config is None:
            final_config = config_override
        else:
            final_config.update(config_override)
        print(f"📋 Config override: {config_override}")
    
    # Generate output folder with timestamp
    output_folder_name = generate_output_folder_name(preset, config_override, threshold)
    output_dir = Path(__file__).parent / "data" / "output" / "cincin_api" / output_folder_name
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"📁 Output folder: {output_folder_name}")
    
    # Save run configuration
    run_config = {
        "timestamp": datetime.now().isoformat(),
        "preset": preset or "standar",
        "threshold_manual": threshold,
        "config_override": config_override,
        "final_config": final_config
    }
    
    # Determine input file path
    if input_file is None:
        input_file = Path(__file__).parent / DEFAULT_INPUT_PATH
    else:
        input_file = Path(input_file)
    
    # =========================================================================
    # STEP 1: Data Ingestion
    # =========================================================================
    print("📂 STEP 1: Data Ingestion & Cleaning")
    print("-" * 40)
    
    try:
        df = load_and_clean_data(input_file)
    except FileNotFoundError as e:
        logger.error(f"❌ {e}")
        return None
    except ValueError as e:
        logger.error(f"❌ {e}")
        return None
    
    stats = validate_data_integrity(df)
    print(f"\n📊 Data Statistics:")
    print(f"   Total Pohon: {stats['total_rows']:,}")
    print(f"   Total Blok: {stats['total_blocks']}")
    
    # =========================================================================
    # STEP 2: Run Cincin Api Algorithm
    # =========================================================================
    print("\n" + "=" * 70)
    print("🔥 STEP 2: Menjalankan Algoritma Cincin Api")
    print("-" * 40)
    
    auto_tune = threshold is None
    
    df_classified, metadata = run_cincin_api_algorithm(
        df,
        auto_tune=auto_tune,
        manual_threshold=threshold,
        config_override=final_config
    )
    
    # =========================================================================
    # STEP 3: Generate Dashboard
    # =========================================================================
    if dashboard:
        print("\n" + "=" * 70)
        print("📊 STEP 3: Generating Dashboard")
        print("-" * 40)
        
        create_dashboard(df_classified, metadata, output_dir, show_plots=True)
        
        # Generate mandor report
        report_path = output_dir / "laporan_mandor.txt"
        report = create_mandor_report(df_classified, metadata, str(report_path))
        print(report)
    
    # =========================================================================
    # STEP 4: Export Results
    # =========================================================================
    if export:
        print("\n" + "=" * 70)
        print("📁 STEP 4: Exporting Results")
        print("-" * 40)
        
        # Export full classified data
        full_path = output_dir / "hasil_klasifikasi_lengkap.csv"
        df_classified.to_csv(full_path, index=False)
        print(f"📁 Full results: {full_path}")
        
        # Export priority targets
        priority_df = get_priority_targets(df_classified, top_n=1000)
        priority_path = output_dir / "target_prioritas.csv"
        priority_df.to_csv(priority_path, index=False)
        print(f"📁 Priority targets: {priority_path}")
        
        # Export per-block summary
        block_summary = df_classified.groupby('Blok').agg({
            'Status_Risiko': [
                lambda x: (x == 'MERAH (KLUSTER AKTIF)').sum(),
                lambda x: (x == 'KUNING (RISIKO TINGGI)').sum(),
                lambda x: (x == 'ORANYE (NOISE/KENTOSAN)').sum(),
                lambda x: (x == 'HIJAU (SEHAT)').sum(),
                'count'
            ]
        }).reset_index()
        block_summary.columns = ['Blok', 'MERAH', 'KUNING', 'ORANYE', 'HIJAU', 'TOTAL']
        block_summary = block_summary.sort_values('MERAH', ascending=False)
        block_path = output_dir / "ringkasan_per_blok.csv"
        block_summary.to_csv(block_path, index=False)
        print(f"📁 Block summary: {block_path}")
        
        # Export run configuration for reproducibility
        import json
        config_path = output_dir / "run_config.json"
        with open(config_path, 'w') as f:
            json.dump({
                "timestamp": run_config["timestamp"],
                "preset": run_config["preset"],
                "threshold_manual": run_config["threshold_manual"],
                "threshold_optimal": metadata.get("optimal_threshold", None),
                "config_applied": run_config["final_config"],
                "results_summary": {
                    "total_trees": metadata.get("total_trees", 0),
                    "merah": metadata.get("merah_count", 0),
                    "kuning": metadata.get("kuning_count", 0),
                    "oranye": metadata.get("oranye_count", 0),
                    "hijau": metadata.get("hijau_count", 0)
                }
            }, f, indent=2, default=str)
        print(f"📁 Run config: {config_path}")
    
    # =========================================================================
    # STEP 5: Generate Documentation (README.md & HTML Report)
    # =========================================================================
    print("\n" + "=" * 70)
    print("📝 STEP 5: Generating Documentation")
    print("-" * 40)
    
    # Generate README.md
    readme_path = generate_readme(
        output_dir=output_dir,
        metadata=metadata,
        config=final_config,
        preset=preset
    )
    print(f"📄 README.md: {readme_path}")
    
    # Generate HTML Report
    html_path = generate_html_report(
        output_dir=output_dir,
        df_classified=df_classified,
        metadata=metadata,
        config=final_config,
        preset=preset
    )
    print(f"🌐 HTML Report: {html_path}")
    print(f"   → Buka file ini di browser untuk laporan interaktif!")
    
    print("\n" + "=" * 70)
    print("✅ ALGORITMA CINCIN API SELESAI!")
    print(f"📁 Semua file tersimpan di: {output_dir}")
    print("=" * 70 + "\n")
    
    return df_classified, metadata


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='POAC v3.3 - Algoritma Cincin Api (Ring of Fire Detection)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Contoh Penggunaan:
  python run_cincin_api.py                        # Default (auto-tune)
  python run_cincin_api.py --preset agresif       # Gunakan preset agresif
  python run_cincin_api.py --preset konservatif   # Gunakan preset konservatif
  python run_cincin_api.py -t 0.20                # Manual threshold 20%
  python run_cincin_api.py --min-neighbors 4      # Override min tetangga sakit
  python run_cincin_api.py --threshold-max 0.40   # Expand threshold range

Preset Tersedia:
  konservatif - Deteksi ketat, hanya kluster padat (min_neighbors=4)
  standar     - Setting default, seimbang
  agresif     - Deteksi luas, threshold tinggi (min_neighbors=2)
        """
    )
    parser.add_argument(
        'input_file', 
        nargs='?', 
        default=None,
        help='Path to input CSV file'
    )
    parser.add_argument(
        '-t', '--threshold',
        type=float,
        default=None,
        help='Manual threshold (0.0-1.0). Contoh: 0.15 untuk 15%%. Default: Auto-tune'
    )
    parser.add_argument(
        '--preset',
        choices=['konservatif', 'standar', 'agresif'],
        default=None,
        help='Preset konfigurasi (konservatif/standar/agresif)'
    )
    parser.add_argument(
        '--min-neighbors',
        type=int,
        default=None,
        help='Minimum tetangga sakit untuk kluster MERAH (default: 3)'
    )
    parser.add_argument(
        '--threshold-min',
        type=float,
        default=None,
        help='Batas bawah simulasi threshold (default: 0.05 = 5%%)'
    )
    parser.add_argument(
        '--threshold-max',
        type=float,
        default=None,
        help='Batas atas simulasi threshold (default: 0.30 = 30%%)'
    )
    parser.add_argument(
        '--threshold-step',
        type=float,
        default=None,
        help='Step simulasi threshold (default: 0.05 = 5%%)'
    )
    parser.add_argument(
        '--no-dashboard',
        action='store_true',
        help='Skip dashboard visualization'
    )
    parser.add_argument(
        '--no-export',
        action='store_true',
        help='Skip CSV export'
    )
    parser.add_argument(
        '--show-config',
        action='store_true',
        help='Tampilkan konfigurasi saat ini dan keluar'
    )
    
    args = parser.parse_args()
    
    # Handle --show-config
    if args.show_config:
        print("\n📋 KONFIGURASI CINCIN API SAAT INI:")
        print("=" * 50)
        for key, value in CINCIN_API_CONFIG.items():
            print(f"  {key}: {value}")
        print("\n📋 PRESET TERSEDIA:")
        print("=" * 50)
        for name, preset in CINCIN_API_PRESETS.items():
            print(f"\n  [{name.upper()}]")
            for key, value in preset.items():
                print(f"    {key}: {value}")
        sys.exit(0)
    
    # Build config override from CLI arguments
    config_override = {}
    if args.min_neighbors is not None:
        config_override['min_sick_neighbors'] = args.min_neighbors
    if args.threshold_min is not None:
        config_override['threshold_min'] = args.threshold_min
    if args.threshold_max is not None:
        config_override['threshold_max'] = args.threshold_max
    if args.threshold_step is not None:
        config_override['threshold_step'] = args.threshold_step
    
    main(
        args.input_file, 
        args.threshold,
        dashboard=not args.no_dashboard,
        export=not args.no_export,
        preset=args.preset,
        config_override=config_override if config_override else None
    )
