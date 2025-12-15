"""
Cincin Api Analysis with Calibrated Thresholds
===============================================

Run analysis using calibrated Z-Score thresholds:
- AME II: Z < -1.5 (more sensitive)
- AME IV: Z < -4.0 (stricter)

Compare results with:
1. Standard threshold (Z < -2.0)
2. Ground truth census data
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys
from datetime import datetime
import base64
from io import BytesIO

script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from src.ingestion import load_and_clean_data, load_ame_iv_data
from src.cost_control_loader import normalize_block
from config import CALIBRATED_THRESHOLDS, get_calibrated_threshold

# =============================================================================
# DETECTION FUNCTIONS
# =============================================================================

def run_detection_with_threshold(df: pd.DataFrame, z_threshold_g3: float, 
                                  z_threshold_g2: float = None) -> pd.DataFrame:
    """
    Run Ganoderma detection using specified Z-Score thresholds.
    Uses MATURE baseline only for Z-Score calculation.
    """
    df_result = df.copy()
    df_result['Z_Score'] = 0.0
    df_result['G_Status'] = 'G1'
    
    if z_threshold_g2 is None:
        z_threshold_g2 = z_threshold_g3 + 1.0  # Default G2 = G3 + 1
    
    for blok in df_result['Blok'].unique():
        mask_blok = df_result['Blok'] == blok
        
        # Calculate baseline from MATURE only
        mask_mature = mask_blok & (df_result['Category'] == 'MATURE')
        ndre_mature = df_result.loc[mask_mature, 'NDRE125']
        
        if len(ndre_mature) > 1:
            mean_val = ndre_mature.mean()
            std_val = ndre_mature.std()
            
            if std_val > 0:
                # Apply to all trees in block
                all_ndre = df_result.loc[mask_blok, 'NDRE125']
                z_scores = (all_ndre - mean_val) / std_val
                df_result.loc[mask_blok, 'Z_Score'] = z_scores
                
                # Classify
                df_result.loc[mask_blok & (df_result['Z_Score'] < z_threshold_g3), 'G_Status'] = 'G3'
                df_result.loc[mask_blok & (df_result['Z_Score'] >= z_threshold_g3) & 
                             (df_result['Z_Score'] < z_threshold_g2), 'G_Status'] = 'G2'
    
    return df_result


def calculate_metrics_per_block(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate detection metrics per block."""
    results = []
    
    for blok in df['Blok'].unique():
        df_blok = df[df['Blok'] == blok]
        total = len(df_blok)
        
        g3 = len(df_blok[df_blok['G_Status'] == 'G3'])
        g2 = len(df_blok[df_blok['G_Status'] == 'G2'])
        g1 = len(df_blok[df_blok['G_Status'] == 'G1'])
        
        results.append({
            'blok': blok,
            'blok_norm': normalize_block(blok),
            'total': total,
            'g3_count': g3,
            'g2_count': g2,
            'g1_count': g1,
            'detected_count': g3 + g2,
            'detected_pct': (g3 + g2) / total * 100 if total > 0 else 0,
            'g3_pct': g3 / total * 100 if total > 0 else 0
        })
    
    return pd.DataFrame(results)


def compare_with_ground_truth(df_detection: pd.DataFrame, df_gt: pd.DataFrame, 
                               divisi: str) -> pd.DataFrame:
    """Compare detection results with ground truth."""
    df_gt_div = df_gt[df_gt['DIVISI'] == divisi].copy()
    df_gt_div['blok_norm'] = df_gt_div['BLOK'].apply(normalize_block)
    df_gt_div['gt_pct'] = df_gt_div['TOTAL_GANO'] / df_gt_div['TOTAL_PKK'] * 100
    
    df_merged = df_detection.merge(
        df_gt_div[['blok_norm', 'TOTAL_PKK', 'TOTAL_GANO', 'gt_pct']],
        on='blok_norm',
        how='inner'
    )
    
    df_merged['diff'] = df_merged['detected_pct'] - df_merged['gt_pct']
    df_merged['abs_diff'] = abs(df_merged['diff'])
    
    return df_merged


def calculate_summary_stats(df_comparison: pd.DataFrame) -> dict:
    """Calculate summary statistics."""
    return {
        'correlation': df_comparison['detected_pct'].corr(df_comparison['gt_pct']),
        'mae': df_comparison['abs_diff'].mean(),
        'rmse': np.sqrt((df_comparison['diff']**2).mean()),
        'avg_algo': df_comparison['detected_pct'].mean(),
        'avg_gt': df_comparison['gt_pct'].mean(),
        'bias': df_comparison['diff'].mean(),
        'n_blocks': len(df_comparison)
    }


# =============================================================================
# REPORT GENERATION
# =============================================================================

def generate_comparison_charts(results_standard: dict, results_calibrated: dict, 
                                df_comparison_std: pd.DataFrame, 
                                df_comparison_cal: pd.DataFrame,
                                divisi: str) -> dict:
    """Generate comparison charts."""
    charts = {}
    plt.style.use('dark_background')
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
    # Chart 1: Scatter - Standard vs Ground Truth
    ax1 = axes[0, 0]
    ax1.scatter(df_comparison_std['gt_pct'], df_comparison_std['detected_pct'], 
                alpha=0.6, s=80, c='#e74c3c', label='Standard (Z<-2.0)')
    max_val = max(df_comparison_std['gt_pct'].max(), df_comparison_std['detected_pct'].max()) + 5
    ax1.plot([0, max_val], [0, max_val], 'w--', linewidth=2, alpha=0.5)
    ax1.set_xlabel('Ground Truth (%)')
    ax1.set_ylabel('Algorithm (%)')
    ax1.set_title(f'Standard Threshold\nMAE: {results_standard["mae"]:.2f}%, r: {results_standard["correlation"]:.3f}')
    ax1.grid(True, alpha=0.3)
    
    # Chart 2: Scatter - Calibrated vs Ground Truth
    ax2 = axes[0, 1]
    ax2.scatter(df_comparison_cal['gt_pct'], df_comparison_cal['detected_pct'], 
                alpha=0.6, s=80, c='#2ecc71', label='Calibrated')
    cal_thresh = get_calibrated_threshold(divisi)
    ax2.plot([0, max_val], [0, max_val], 'w--', linewidth=2, alpha=0.5)
    ax2.set_xlabel('Ground Truth (%)')
    ax2.set_ylabel('Algorithm (%)')
    ax2.set_title(f'Calibrated Threshold (Z<{cal_thresh["Z_Threshold_G3"]})\nMAE: {results_calibrated["mae"]:.2f}%, r: {results_calibrated["correlation"]:.3f}')
    ax2.grid(True, alpha=0.3)
    
    # Chart 3: Bar comparison of metrics
    ax3 = axes[1, 0]
    metrics = ['MAE', 'Correlation', 'Bias']
    std_vals = [results_standard['mae'], results_standard['correlation'], abs(results_standard['bias'])]
    cal_vals = [results_calibrated['mae'], results_calibrated['correlation'], abs(results_calibrated['bias'])]
    
    x = np.arange(len(metrics))
    width = 0.35
    
    ax3.bar(x - width/2, std_vals, width, label='Standard', color='#e74c3c', alpha=0.7)
    ax3.bar(x + width/2, cal_vals, width, label='Calibrated', color='#2ecc71', alpha=0.7)
    ax3.set_xticks(x)
    ax3.set_xticklabels(metrics)
    ax3.set_title('Metrics Comparison')
    ax3.legend()
    ax3.grid(True, alpha=0.3, axis='y')
    
    # Chart 4: Detection rate comparison
    ax4 = axes[1, 1]
    labels = ['GT Avg', 'Standard', 'Calibrated']
    values = [results_standard['avg_gt'], results_standard['avg_algo'], results_calibrated['avg_algo']]
    colors = ['#f39c12', '#e74c3c', '#2ecc71']
    
    ax4.bar(labels, values, color=colors, alpha=0.7, edgecolor='white', linewidth=2)
    ax4.set_ylabel('Average Detection Rate (%)')
    ax4.set_title('Detection Rate Comparison')
    ax4.grid(True, alpha=0.3, axis='y')
    
    # Add value labels
    for i, v in enumerate(values):
        ax4.text(i, v + 0.3, f'{v:.2f}%', ha='center', fontweight='bold')
    
    plt.suptitle(f'{divisi} - Standard vs Calibrated Threshold', fontsize=14, fontweight='bold')
    plt.tight_layout()
    
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=120, bbox_inches='tight', facecolor='#1a1a2e')
    buf.seek(0)
    charts['comparison'] = base64.b64encode(buf.read()).decode('utf-8')
    plt.close()
    
    return charts


def generate_html_report(divisi: str, results_std: dict, results_cal: dict,
                          df_comp_std: pd.DataFrame, df_comp_cal: pd.DataFrame,
                          charts: dict, output_path: Path) -> None:
    """Generate comprehensive HTML report."""
    
    cal_thresh = get_calibrated_threshold(divisi)
    improvement_mae = results_std['mae'] - results_cal['mae']
    improvement_corr = results_cal['correlation'] - results_std['correlation']
    
    html = f"""<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Calibrated Analysis - {divisi}</title>
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
            background: linear-gradient(135deg, #27ae60 0%, #2ecc71 100%);
            padding: 25px;
            border-radius: 15px;
            margin-bottom: 20px;
            text-align: center;
        }}
        .header h1 {{ font-size: 1.8em; margin-bottom: 10px; }}
        .improvement-box {{
            background: linear-gradient(135deg, #f39c12 0%, #e67e22 100%);
            padding: 20px;
            border-radius: 12px;
            margin-bottom: 20px;
            text-align: center;
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }}
        .metric-card {{
            background: rgba(255,255,255,0.08);
            padding: 20px;
            border-radius: 12px;
        }}
        .metric-card h4 {{ color: #a0a0a0; margin-bottom: 10px; }}
        .metric-row {{
            display: flex;
            justify-content: space-between;
            margin: 8px 0;
        }}
        .metric-label {{ color: #a0a0a0; }}
        .metric-value {{ font-weight: bold; }}
        .better {{ color: #2ecc71; }}
        .worse {{ color: #e74c3c; }}
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
            margin-top: 15px;
        }}
        th, td {{
            padding: 10px;
            text-align: center;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }}
        th {{ background: rgba(39,174,96,0.3); }}
        tr:hover {{ background: rgba(255,255,255,0.05); }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>✅ {divisi} - Calibrated Threshold Analysis</h1>
            <p>Threshold terkalibrasi berdasarkan data sensus Ganoderma</p>
            <p style="font-size: 0.9em; margin-top: 10px;">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
        </div>
        
        <div class="improvement-box">
            <h3>🎯 IMPROVEMENT SUMMARY</h3>
            <p style="font-size: 1.2em; margin-top: 10px;">
                MAE: <span class="{'better' if improvement_mae > 0 else 'worse'}">{improvement_mae:+.2f}%</span> | 
                Correlation: <span class="{'better' if improvement_corr > 0 else 'worse'}">{improvement_corr:+.3f}</span>
            </p>
            <p style="margin-top: 5px;">Calibrated Threshold: <strong>Z < {cal_thresh['Z_Threshold_G3']}</strong></p>
        </div>
        
        <div class="metrics-grid">
            <div class="metric-card">
                <h4>📊 Standard Threshold (Z < -2.0)</h4>
                <div class="metric-row">
                    <span class="metric-label">MAE:</span>
                    <span class="metric-value">{results_std['mae']:.2f}%</span>
                </div>
                <div class="metric-row">
                    <span class="metric-label">Correlation:</span>
                    <span class="metric-value">{results_std['correlation']:.3f}</span>
                </div>
                <div class="metric-row">
                    <span class="metric-label">Avg Detection:</span>
                    <span class="metric-value">{results_std['avg_algo']:.2f}%</span>
                </div>
                <div class="metric-row">
                    <span class="metric-label">Bias:</span>
                    <span class="metric-value">{results_std['bias']:+.2f}%</span>
                </div>
            </div>
            
            <div class="metric-card" style="border: 2px solid #2ecc71;">
                <h4>✅ Calibrated Threshold (Z < {cal_thresh['Z_Threshold_G3']})</h4>
                <div class="metric-row">
                    <span class="metric-label">MAE:</span>
                    <span class="metric-value better">{results_cal['mae']:.2f}%</span>
                </div>
                <div class="metric-row">
                    <span class="metric-label">Correlation:</span>
                    <span class="metric-value better">{results_cal['correlation']:.3f}</span>
                </div>
                <div class="metric-row">
                    <span class="metric-label">Avg Detection:</span>
                    <span class="metric-value">{results_cal['avg_algo']:.2f}%</span>
                </div>
                <div class="metric-row">
                    <span class="metric-label">Bias:</span>
                    <span class="metric-value">{results_cal['bias']:+.2f}%</span>
                </div>
            </div>
            
            <div class="metric-card">
                <h4>🎯 Ground Truth</h4>
                <div class="metric-row">
                    <span class="metric-label">Avg % Serangan:</span>
                    <span class="metric-value">{results_std['avg_gt']:.2f}%</span>
                </div>
                <div class="metric-row">
                    <span class="metric-label">Blocks Analyzed:</span>
                    <span class="metric-value">{results_std['n_blocks']}</span>
                </div>
            </div>
        </div>
        
        <div class="chart-container">
            <h3 style="margin-bottom: 15px;">📈 Visual Comparison</h3>
            <img src="data:image/png;base64,{charts.get('comparison', '')}" alt="Comparison">
        </div>
        
        <h3>📋 Calibrated Detection - Top 20 Blocks by Detection Rate</h3>
        <table>
            <thead>
                <tr>
                    <th>Blok</th>
                    <th>Total</th>
                    <th>G3</th>
                    <th>G2</th>
                    <th>Algo (%)</th>
                    <th>GT (%)</th>
                    <th>Diff</th>
                </tr>
            </thead>
            <tbody>
"""
    
    # Add top 20 rows
    df_sorted = df_comp_cal.sort_values('detected_pct', ascending=False).head(20)
    for _, row in df_sorted.iterrows():
        diff_class = 'worse' if row['diff'] > 2 else ('better' if row['diff'] < -2 else '')
        html += f"""
                <tr>
                    <td>{row['blok']}</td>
                    <td>{row['total']:,}</td>
                    <td>{row['g3_count']:,}</td>
                    <td>{row['g2_count']:,}</td>
                    <td>{row['detected_pct']:.2f}%</td>
                    <td>{row['gt_pct']:.2f}%</td>
                    <td class="{diff_class}">{row['diff']:+.2f}%</td>
                </tr>
"""
    
    html += """
            </tbody>
        </table>
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
    print("CINCIN API ANALYSIS - CALIBRATED THRESHOLDS")
    print("="*70)
    
    output_dir = script_dir / "data" / "output" / "calibrated_analysis"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load data
    print("\n[1/4] Loading data...")
    df_ame2 = load_and_clean_data(script_dir / "data/input/tabelNDREnew.csv")
    df_ame4 = load_ame_iv_data(script_dir / "data/input/AME_IV.csv")
    
    # Only MATURE for analysis
    df_ame2 = df_ame2[df_ame2['Category'] == 'MATURE'].copy()
    df_ame4 = df_ame4[df_ame4['Category'] == 'MATURE'].copy()
    
    print(f"  - AME II (MATURE): {len(df_ame2):,}")
    print(f"  - AME IV (MATURE): {len(df_ame4):,}")
    
    # Load ground truth
    df_gt = pd.read_excel(
        script_dir / "data/input/areal_inti_serangan_gano_AMEII_AMEIV.xlsx",
        sheet_name='Sheet1', header=[0, 1]
    )
    df_gt.columns = ['DIVISI', 'BLOK', 'TAHUN_TANAM', 'LUAS_SD_2024', 'PENAMBAHAN', 
                     'LUAS_SD_2025', 'TANAM', 'SISIP', 'SISIP_KENTOSAN', 'TOTAL_PKK',
                     'SPH', 'STADIUM_12', 'STADIUM_34', 'TOTAL_GANO', 'SERANGAN_PCT']
    df_gt = df_gt[df_gt['DIVISI'].isin(['AME002', 'AME004'])]
    
    all_results = []
    
    # Process each divisi
    for divisi, df_drone in [('AME002', df_ame2), ('AME004', df_ame4)]:
        print(f"\n[2/4] Processing {divisi}...")
        
        cal_thresh = get_calibrated_threshold(divisi)
        print(f"  - Calibrated threshold: Z < {cal_thresh['Z_Threshold_G3']}")
        
        # Run with STANDARD threshold
        print("  - Running standard threshold (Z < -2.0)...")
        df_std = run_detection_with_threshold(df_drone.copy(), -2.0, -1.0)
        metrics_std = calculate_metrics_per_block(df_std)
        comp_std = compare_with_ground_truth(metrics_std, df_gt, divisi)
        results_std = calculate_summary_stats(comp_std)
        
        # Run with CALIBRATED threshold
        print(f"  - Running calibrated threshold (Z < {cal_thresh['Z_Threshold_G3']})...")
        df_cal = run_detection_with_threshold(
            df_drone.copy(), 
            cal_thresh['Z_Threshold_G3'],
            cal_thresh['Z_Threshold_G2']
        )
        metrics_cal = calculate_metrics_per_block(df_cal)
        comp_cal = compare_with_ground_truth(metrics_cal, df_gt, divisi)
        results_cal = calculate_summary_stats(comp_cal)
        
        # Save CSVs
        comp_std.to_csv(output_dir / f"{divisi}_standard.csv", index=False)
        comp_cal.to_csv(output_dir / f"{divisi}_calibrated.csv", index=False)
        
        # Generate charts and HTML
        print("  - Generating reports...")
        charts = generate_comparison_charts(results_std, results_cal, comp_std, comp_cal, divisi)
        generate_html_report(divisi, results_std, results_cal, comp_std, comp_cal, 
                            charts, output_dir / f"{divisi}_report.html")
        
        # Store results
        all_results.append({
            'divisi': divisi,
            'threshold_std': -2.0,
            'threshold_cal': cal_thresh['Z_Threshold_G3'],
            'mae_std': results_std['mae'],
            'mae_cal': results_cal['mae'],
            'corr_std': results_std['correlation'],
            'corr_cal': results_cal['correlation'],
            'improvement_mae': results_std['mae'] - results_cal['mae'],
            'improvement_corr': results_cal['correlation'] - results_std['correlation']
        })
    
    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    
    df_summary = pd.DataFrame(all_results)
    print(df_summary.to_string(index=False))
    
    df_summary.to_csv(output_dir / "summary.csv", index=False)
    
    print(f"\n[4/4] Complete! Reports saved to: {output_dir}")
    
    return df_summary


if __name__ == "__main__":
    main()
