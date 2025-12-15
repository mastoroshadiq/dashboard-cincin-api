"""
Z-Score Threshold Calibration using Census Data
================================================

Objective: Find optimal Z-Score threshold that best matches ground truth Ganoderma detection.

Approach:
1. Test multiple Z-Score thresholds
2. Calculate detection rate for each threshold
3. Compare with ground truth (%SERANGAN)
4. Find threshold that minimizes MAE and maximizes correlation
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys
from datetime import datetime
import base64
from io import BytesIO

# Setup
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from src.ingestion import load_and_clean_data, load_ame_iv_data
from src.cost_control_loader import normalize_block

# =============================================================================
# CALIBRATION FUNCTIONS
# =============================================================================

def calculate_detection_for_threshold(df: pd.DataFrame, z_threshold: float) -> pd.DataFrame:
    """Calculate detection rates per block for a given Z-Score threshold."""
    df_result = df.copy()
    
    # Calculate Z-Score per block
    results = []
    
    for blok in df_result['Blok'].unique():
        mask = df_result['Blok'] == blok
        df_blok = df_result[mask]
        
        # Only use MATURE for baseline
        mask_mature = mask & (df_result['Category'] == 'MATURE')
        ndre_mature = df_result.loc[mask_mature, 'NDRE125']
        
        if len(ndre_mature) > 1:
            mean_val = ndre_mature.mean()
            std_val = ndre_mature.std()
            
            if std_val > 0:
                # Calculate Z-Score for ALL trees in block
                z_scores = (df_blok['NDRE125'] - mean_val) / std_val
                
                # Count detections (trees below threshold)
                detected = (z_scores < z_threshold).sum()
                total = len(df_blok)
                
                results.append({
                    'blok': blok,
                    'total': total,
                    'detected': detected,
                    'detected_pct': detected / total * 100 if total > 0 else 0
                })
    
    return pd.DataFrame(results)


def calibrate_threshold(df_drone: pd.DataFrame, df_gt: pd.DataFrame, divisi: str,
                        thresholds: list) -> pd.DataFrame:
    """Test multiple thresholds and compare with ground truth."""
    
    # Filter ground truth
    df_gt_div = df_gt[df_gt['DIVISI'] == divisi].copy()
    df_gt_div['blok_norm'] = df_gt_div['BLOK'].apply(normalize_block)
    df_gt_div['gt_pct'] = df_gt_div['TOTAL_GANO'] / df_gt_div['TOTAL_PKK'] * 100
    
    results = []
    
    for z_thresh in thresholds:
        # Calculate detection for this threshold
        df_detection = calculate_detection_for_threshold(df_drone, z_thresh)
        df_detection['blok_norm'] = df_detection['blok'].apply(normalize_block)
        
        # Merge with ground truth
        df_merged = df_detection.merge(
            df_gt_div[['blok_norm', 'gt_pct', 'TOTAL_GANO', 'TOTAL_PKK']],
            on='blok_norm',
            how='inner'
        )
        
        if len(df_merged) > 0:
            # Calculate metrics
            correlation = df_merged['detected_pct'].corr(df_merged['gt_pct'])
            mae = abs(df_merged['detected_pct'] - df_merged['gt_pct']).mean()
            rmse = np.sqrt(((df_merged['detected_pct'] - df_merged['gt_pct'])**2).mean())
            
            avg_algo = df_merged['detected_pct'].mean()
            avg_gt = df_merged['gt_pct'].mean()
            
            # Bias (positive = over-detection, negative = under-detection)
            bias = avg_algo - avg_gt
            
            results.append({
                'z_threshold': z_thresh,
                'correlation': correlation,
                'mae': mae,
                'rmse': rmse,
                'avg_algo_pct': avg_algo,
                'avg_gt_pct': avg_gt,
                'bias': bias,
                'n_blocks': len(df_merged)
            })
    
    return pd.DataFrame(results)


def find_optimal_threshold(df_calibration: pd.DataFrame) -> dict:
    """Find optimal threshold based on different criteria."""
    
    optimal = {}
    
    # Best by MAE (minimum)
    idx_mae = df_calibration['mae'].idxmin()
    optimal['min_mae'] = {
        'threshold': df_calibration.loc[idx_mae, 'z_threshold'],
        'mae': df_calibration.loc[idx_mae, 'mae'],
        'corr': df_calibration.loc[idx_mae, 'correlation']
    }
    
    # Best by correlation (maximum)
    idx_corr = df_calibration['correlation'].idxmax()
    optimal['max_corr'] = {
        'threshold': df_calibration.loc[idx_corr, 'z_threshold'],
        'mae': df_calibration.loc[idx_corr, 'mae'],
        'corr': df_calibration.loc[idx_corr, 'correlation']
    }
    
    # Best by minimum absolute bias
    df_calibration['abs_bias'] = abs(df_calibration['bias'])
    idx_bias = df_calibration['abs_bias'].idxmin()
    optimal['min_bias'] = {
        'threshold': df_calibration.loc[idx_bias, 'z_threshold'],
        'bias': df_calibration.loc[idx_bias, 'bias'],
        'corr': df_calibration.loc[idx_bias, 'correlation']
    }
    
    return optimal


def generate_calibration_charts(df_calib: pd.DataFrame, divisi: str) -> dict:
    """Generate calibration analysis charts."""
    charts = {}
    plt.style.use('dark_background')
    
    # Chart 1: MAE vs Threshold
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
    # MAE
    ax1 = axes[0, 0]
    ax1.plot(df_calib['z_threshold'], df_calib['mae'], 'o-', color='#e74c3c', linewidth=2, markersize=8)
    ax1.set_xlabel('Z-Score Threshold')
    ax1.set_ylabel('MAE (%)')
    ax1.set_title('Mean Absolute Error vs Threshold')
    ax1.grid(True, alpha=0.3)
    ax1.axhline(y=df_calib['mae'].min(), color='yellow', linestyle='--', alpha=0.5)
    
    # Correlation
    ax2 = axes[0, 1]
    ax2.plot(df_calib['z_threshold'], df_calib['correlation'], 'o-', color='#3498db', linewidth=2, markersize=8)
    ax2.set_xlabel('Z-Score Threshold')
    ax2.set_ylabel('Correlation (r)')
    ax2.set_title('Correlation vs Threshold')
    ax2.grid(True, alpha=0.3)
    ax2.axhline(y=0, color='white', linestyle='-', alpha=0.3)
    
    # Detection Rate
    ax3 = axes[1, 0]
    ax3.plot(df_calib['z_threshold'], df_calib['avg_algo_pct'], 'o-', color='#2ecc71', linewidth=2, markersize=8, label='Algorithm')
    ax3.axhline(y=df_calib['avg_gt_pct'].mean(), color='#f39c12', linestyle='--', linewidth=2, label='Ground Truth')
    ax3.set_xlabel('Z-Score Threshold')
    ax3.set_ylabel('Avg Detection Rate (%)')
    ax3.set_title('Average Detection Rate vs Threshold')
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # Bias
    ax4 = axes[1, 1]
    colors = ['#e74c3c' if b > 0 else '#2ecc71' for b in df_calib['bias']]
    ax4.bar(df_calib['z_threshold'], df_calib['bias'], color=colors, alpha=0.7, edgecolor='white')
    ax4.set_xlabel('Z-Score Threshold')
    ax4.set_ylabel('Bias (%)')
    ax4.set_title('Detection Bias vs Threshold')
    ax4.axhline(y=0, color='white', linestyle='-', linewidth=1)
    ax4.grid(True, alpha=0.3, axis='y')
    
    plt.suptitle(f'{divisi} - Threshold Calibration Analysis', fontsize=14, fontweight='bold')
    plt.tight_layout()
    
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=120, bbox_inches='tight', facecolor='#1a1a2e')
    buf.seek(0)
    charts['calibration'] = base64.b64encode(buf.read()).decode('utf-8')
    plt.close()
    
    return charts


def generate_calibration_html_report(df_calib: pd.DataFrame, optimal: dict, charts: dict,
                                     divisi: str, output_path: Path) -> None:
    """Generate HTML report for calibration results."""
    
    html = f"""<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Z-Score Calibration - {divisi}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: 'Segoe UI', Tahoma, sans-serif; 
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #e0e0e0; 
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{ max-width: 1400px; margin: 0 auto; }}
        .header {{ 
            background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%);
            padding: 25px;
            border-radius: 15px;
            margin-bottom: 20px;
            text-align: center;
        }}
        .header h1 {{ font-size: 1.8em; margin-bottom: 10px; }}
        .optimal-box {{
            background: linear-gradient(135deg, #27ae60 0%, #2ecc71 100%);
            padding: 25px;
            border-radius: 15px;
            margin-bottom: 20px;
        }}
        .optimal-box h3 {{ margin-bottom: 15px; }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }}
        .metric-card {{
            background: rgba(255,255,255,0.1);
            padding: 20px;
            border-radius: 12px;
            text-align: center;
        }}
        .metric-value {{ font-size: 2em; font-weight: bold; }}
        .metric-label {{ color: rgba(255,255,255,0.8); margin-top: 5px; }}
        .chart-container {{
            background: rgba(255,255,255,0.05);
            padding: 20px;
            border-radius: 15px;
            margin-bottom: 20px;
        }}
        .chart-container img {{ width: 100%; border-radius: 12px; }}
        table {{
            width: 100%;
            border-collapse: collapse;
            background: rgba(255,255,255,0.05);
            border-radius: 12px;
            overflow: hidden;
            margin-top: 20px;
        }}
        th, td {{
            padding: 12px;
            text-align: center;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }}
        th {{ background: rgba(231,76,60,0.3); }}
        tr:hover {{ background: rgba(255,255,255,0.05); }}
        .highlight {{ background: rgba(46,204,113,0.3) !important; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎛️ Z-Score Threshold Calibration</h1>
            <p>{divisi} - Ground Truth Based Calibration</p>
            <p style="font-size: 0.9em; margin-top: 10px;">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
        </div>
        
        <div class="optimal-box">
            <h3>✅ OPTIMAL THRESHOLD RECOMMENDATIONS</h3>
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-value">{optimal['min_mae']['threshold']:.1f}</div>
                    <div class="metric-label">Minimum MAE</div>
                    <div style="font-size: 0.9em; margin-top: 5px;">MAE: {optimal['min_mae']['mae']:.2f}%</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{optimal['max_corr']['threshold']:.1f}</div>
                    <div class="metric-label">Maximum Correlation</div>
                    <div style="font-size: 0.9em; margin-top: 5px;">r: {optimal['max_corr']['corr']:.3f}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{optimal['min_bias']['threshold']:.1f}</div>
                    <div class="metric-label">Minimum Bias</div>
                    <div style="font-size: 0.9em; margin-top: 5px;">Bias: {optimal['min_bias']['bias']:+.2f}%</div>
                </div>
            </div>
        </div>
        
        <div class="chart-container">
            <h3 style="margin-bottom: 15px;">📊 Calibration Analysis</h3>
            <img src="data:image/png;base64,{charts.get('calibration', '')}" alt="Calibration">
        </div>
        
        <h3>📋 All Threshold Results</h3>
        <table>
            <thead>
                <tr>
                    <th>Z Threshold</th>
                    <th>Correlation (r)</th>
                    <th>MAE (%)</th>
                    <th>RMSE (%)</th>
                    <th>Algo Avg (%)</th>
                    <th>GT Avg (%)</th>
                    <th>Bias (%)</th>
                </tr>
            </thead>
            <tbody>
"""
    
    # Find optimal row
    optimal_thresh = optimal['min_mae']['threshold']
    
    for _, row in df_calib.iterrows():
        highlight = 'highlight' if row['z_threshold'] == optimal_thresh else ''
        html += f"""
                <tr class="{highlight}">
                    <td>{row['z_threshold']:.1f}</td>
                    <td>{row['correlation']:.3f}</td>
                    <td>{row['mae']:.2f}</td>
                    <td>{row['rmse']:.2f}</td>
                    <td>{row['avg_algo_pct']:.2f}</td>
                    <td>{row['avg_gt_pct']:.2f}</td>
                    <td>{row['bias']:+.2f}</td>
                </tr>
"""
    
    html += """
            </tbody>
        </table>
        
        <div style="margin-top: 30px; padding: 20px; background: rgba(255,255,255,0.05); border-radius: 12px;">
            <h4>📝 Interpretasi</h4>
            <ul style="margin-top: 10px; padding-left: 20px;">
                <li><strong>MAE (Mean Absolute Error)</strong>: Semakin rendah semakin baik. Rata-rata selisih absolut antara deteksi algoritma dan ground truth.</li>
                <li><strong>Correlation (r)</strong>: Nilai positif mendekati 1 menunjukkan korelasi kuat. Nilai negatif berarti algoritma berkebalikan dengan ground truth.</li>
                <li><strong>Bias</strong>: Positif = over-detection, Negatif = under-detection.</li>
            </ul>
        </div>
    </div>
</body>
</html>
"""
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"  HTML saved: {output_path}")


# =============================================================================
# MAIN
# =============================================================================

def main():
    print("="*70)
    print("Z-Score Threshold Calibration")
    print("Finding optimal threshold based on census data")
    print("="*70)
    
    # Output directory
    output_dir = script_dir / "data" / "output" / "z_score_calibration"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Thresholds to test
    thresholds = [-0.5, -1.0, -1.5, -2.0, -2.5, -3.0, -3.5, -4.0, -4.5, -5.0]
    
    # Load data
    print("\n[1/4] Loading data...")
    df_ame2 = load_and_clean_data(script_dir / "data/input/tabelNDREnew.csv")
    df_ame4 = load_ame_iv_data(script_dir / "data/input/AME_IV.csv")
    
    # Load ground truth
    df_gt = pd.read_excel(
        script_dir / "data/input/areal_inti_serangan_gano_AMEII_AMEIV.xlsx",
        sheet_name='Sheet1', header=[0, 1]
    )
    df_gt.columns = ['DIVISI', 'BLOK', 'TAHUN_TANAM', 'LUAS_SD_2024', 'PENAMBAHAN', 
                     'LUAS_SD_2025', 'TANAM', 'SISIP', 'SISIP_KENTOSAN', 'TOTAL_PKK',
                     'SPH', 'STADIUM_12', 'STADIUM_34', 'TOTAL_GANO', 'SERANGAN_PCT']
    df_gt = df_gt[df_gt['DIVISI'].isin(['AME002', 'AME004'])]
    
    print(f"  - AME II: {len(df_ame2):,} trees")
    print(f"  - AME IV: {len(df_ame4):,} trees")
    print(f"  - Ground Truth: {len(df_gt)} blocks")
    print(f"  - Testing thresholds: {thresholds}")
    
    all_optimal = {}
    
    # Calibrate for each divisi
    for divisi, df_drone in [('AME002', df_ame2), ('AME004', df_ame4)]:
        print(f"\n[2/4] Calibrating {divisi}...")
        
        # Only use MATURE trees for detection (exclude YOUNG, DEAD, EMPTY)
        df_mature = df_drone[df_drone['Category'] == 'MATURE'].copy()
        print(f"  - Using {len(df_mature):,} MATURE trees")
        
        # Run calibration
        df_calib = calibrate_threshold(df_mature, df_gt, divisi, thresholds)
        
        # Find optimal
        optimal = find_optimal_threshold(df_calib)
        all_optimal[divisi] = optimal
        
        # Save CSV
        csv_path = output_dir / f"{divisi}_calibration.csv"
        df_calib.to_csv(csv_path, index=False)
        print(f"  - CSV saved: {csv_path}")
        
        # Generate charts and HTML
        charts = generate_calibration_charts(df_calib, divisi)
        html_path = output_dir / f"{divisi}_calibration_report.html"
        generate_calibration_html_report(df_calib, optimal, charts, divisi, html_path)
    
    # Print summary
    print("\n" + "="*70)
    print("CALIBRATION RESULTS SUMMARY")
    print("="*70)
    
    for divisi, opt in all_optimal.items():
        print(f"\n{divisi}:")
        print(f"  Optimal by Min MAE:     Z < {opt['min_mae']['threshold']:.1f} (MAE: {opt['min_mae']['mae']:.2f}%)")
        print(f"  Optimal by Max Corr:    Z < {opt['max_corr']['threshold']:.1f} (r: {opt['max_corr']['corr']:.3f})")
        print(f"  Optimal by Min Bias:    Z < {opt['min_bias']['threshold']:.1f} (bias: {opt['min_bias']['bias']:+.2f}%)")
    
    print(f"\n[4/4] Complete! Reports saved to: {output_dir}")
    
    return all_optimal


if __name__ == "__main__":
    main()
