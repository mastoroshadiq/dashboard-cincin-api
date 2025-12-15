"""
Population Segmentation Analysis - 3 Conditions
===============================================

Condition 1: MATURE Only (Pokok Utama saja)
Condition 2: All Living (Include Sisip + Tamb, exclude Mati/Kosong)
Condition 3: Adaptive Threshold (Separate baseline untuk MATURE vs YOUNG)

Output:
- data/output/population_analysis/condition_1_mature_only/
- data/output/population_analysis/condition_2_all_living/
- data/output/population_analysis/condition_3_adaptive/
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys
from datetime import datetime
import base64
from io import BytesIO

# Setup paths
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from src.ingestion import load_and_clean_data, load_ame_iv_data
from src.cost_control_loader import load_ground_truth_excel

# =============================================================================
# ALGORITHM FUNCTIONS
# =============================================================================

def calculate_zscore_standard(df: pd.DataFrame, blok_column: str = 'Blok') -> pd.DataFrame:
    """Calculate Z-Score per block using standard method (all data in block)."""
    df_result = df.copy()
    df_result['Z_Score'] = 0.0
    df_result['G_Status'] = 'G1'
    
    for blok in df_result[blok_column].unique():
        mask = df_result[blok_column] == blok
        ndre_values = df_result.loc[mask, 'NDRE125']
        
        if len(ndre_values) > 1:
            mean_val = ndre_values.mean()
            std_val = ndre_values.std()
            
            if std_val > 0:
                z_scores = (ndre_values - mean_val) / std_val
                df_result.loc[mask, 'Z_Score'] = z_scores
                
                # Classify based on Z-Score
                df_result.loc[mask & (df_result['Z_Score'] < -2.0), 'G_Status'] = 'G3'
                df_result.loc[mask & (df_result['Z_Score'] >= -2.0) & (df_result['Z_Score'] < -1.0), 'G_Status'] = 'G2'
    
    return df_result


def calculate_zscore_adaptive(df: pd.DataFrame, blok_column: str = 'Blok') -> pd.DataFrame:
    """Calculate Z-Score with separate baseline for MATURE vs YOUNG per block."""
    df_result = df.copy()
    df_result['Z_Score'] = 0.0
    df_result['G_Status'] = 'G1'
    
    for blok in df_result[blok_column].unique():
        mask_blok = df_result[blok_column] == blok
        
        # Process MATURE
        mask_mature = mask_blok & (df_result['Category'] == 'MATURE')
        if mask_mature.sum() > 1:
            ndre_mature = df_result.loc[mask_mature, 'NDRE125']
            mean_m = ndre_mature.mean()
            std_m = ndre_mature.std()
            
            if std_m > 0:
                z_scores = (ndre_mature - mean_m) / std_m
                df_result.loc[mask_mature, 'Z_Score'] = z_scores
                df_result.loc[mask_mature & (df_result['Z_Score'] < -2.0), 'G_Status'] = 'G3'
                df_result.loc[mask_mature & (df_result['Z_Score'] >= -2.0) & (df_result['Z_Score'] < -1.0), 'G_Status'] = 'G2'
        
        # Process YOUNG with separate baseline
        mask_young = mask_blok & (df_result['Category'] == 'YOUNG')
        if mask_young.sum() > 1:
            ndre_young = df_result.loc[mask_young, 'NDRE125']
            mean_y = ndre_young.mean()
            std_y = ndre_young.std()
            
            if std_y > 0:
                z_scores = (ndre_young - mean_y) / std_y
                df_result.loc[mask_young, 'Z_Score'] = z_scores
                # Use same thresholds but relative to YOUNG baseline
                df_result.loc[mask_young & (df_result['Z_Score'] < -2.0), 'G_Status'] = 'G3'
                df_result.loc[mask_young & (df_result['Z_Score'] >= -2.0) & (df_result['Z_Score'] < -1.0), 'G_Status'] = 'G2'
    
    return df_result


def run_condition_1(df: pd.DataFrame) -> pd.DataFrame:
    """Condition 1: MATURE Only - Exclude Sisip, Mati, Kosong, Tamb."""
    # Filter only MATURE (Note: our current MATURE includes Tamb, so this is Pokok+Tamb)
    # Actually let's be strict - only 'Pokok Utama' label
    df_filtered = df[df['Category'] == 'MATURE'].copy()
    return calculate_zscore_standard(df_filtered)


def run_condition_2(df: pd.DataFrame) -> pd.DataFrame:
    """Condition 2: All Living - Include Sisip + Tamb, exclude Mati/Kosong."""
    # Exclude DEAD and EMPTY
    df_filtered = df[df['Category'].isin(['MATURE', 'YOUNG'])].copy()
    return calculate_zscore_standard(df_filtered)


def run_condition_3(df: pd.DataFrame) -> pd.DataFrame:
    """Condition 3: Adaptive - Separate baseline for MATURE vs YOUNG."""
    # Exclude DEAD and EMPTY
    df_filtered = df[df['Category'].isin(['MATURE', 'YOUNG'])].copy()
    return calculate_zscore_adaptive(df_filtered)


# =============================================================================
# ANALYSIS FUNCTIONS
# =============================================================================

def calculate_detection_rate(df: pd.DataFrame) -> dict:
    """Calculate detection rates per block."""
    results = []
    
    for blok in df['Blok'].unique():
        df_blok = df[df['Blok'] == blok]
        total = len(df_blok)
        
        g3_count = len(df_blok[df_blok['G_Status'] == 'G3'])
        g2_count = len(df_blok[df_blok['G_Status'] == 'G2'])
        g1_count = len(df_blok[df_blok['G_Status'] == 'G1'])
        
        results.append({
            'blok': blok,
            'total': total,
            'g3_count': g3_count,
            'g2_count': g2_count,
            'g1_count': g1_count,
            'g3_pct': g3_count / total * 100 if total > 0 else 0,
            'g2_pct': g2_count / total * 100 if total > 0 else 0,
            'detected_pct': (g2_count + g3_count) / total * 100 if total > 0 else 0
        })
    
    return pd.DataFrame(results)


def compare_with_ground_truth(df_detection: pd.DataFrame, df_gt: pd.DataFrame, divisi: str) -> pd.DataFrame:
    """Compare algorithm detection with ground truth census data."""
    from src.cost_control_loader import normalize_block
    
    # Filter ground truth for divisi
    df_gt_div = df_gt[df_gt['DIVISI'] == divisi].copy()
    df_gt_div['blok_norm'] = df_gt_div['BLOK'].apply(normalize_block)
    
    # Normalize detection blok
    df_detection['blok_norm'] = df_detection['blok'].apply(normalize_block)
    
    # Merge
    df_merged = df_detection.merge(
        df_gt_div[['blok_norm', 'TOTAL_PKK', 'TOTAL_GANO', 'SERANGAN_PCT']],
        on='blok_norm',
        how='left'
    )
    
    df_merged['gt_serangan_pct'] = df_merged['TOTAL_GANO'] / df_merged['TOTAL_PKK'] * 100
    df_merged['diff_pct'] = df_merged['detected_pct'] - df_merged['gt_serangan_pct']
    
    return df_merged


# =============================================================================
# REPORT GENERATION
# =============================================================================

def generate_charts(df_comparison: pd.DataFrame, condition_name: str) -> dict:
    """Generate charts for the condition."""
    charts = {}
    plt.style.use('dark_background')
    
    # Chart 1: Scatter - Algorithm vs Ground Truth
    fig, ax = plt.subplots(figsize=(10, 8))
    
    ax.scatter(df_comparison['gt_serangan_pct'], df_comparison['detected_pct'], 
               alpha=0.7, s=100, c='#3498db', edgecolors='white')
    
    max_val = max(df_comparison['gt_serangan_pct'].max(), df_comparison['detected_pct'].max()) + 5
    ax.plot([0, max_val], [0, max_val], 'w--', linewidth=2, alpha=0.6, label='Ideal Match')
    
    ax.set_xlabel('Ground Truth (%)', fontsize=12)
    ax.set_ylabel('Algorithm Detection (%)', fontsize=12)
    ax.set_title(f'{condition_name}\nAlgorithm vs Ground Truth per Blok', fontsize=14, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight', facecolor='#1a1a2e')
    buf.seek(0)
    charts['scatter'] = base64.b64encode(buf.read()).decode('utf-8')
    plt.close()
    
    # Chart 2: Distribution of detection rates
    fig, ax = plt.subplots(figsize=(10, 6))
    
    ax.hist(df_comparison['detected_pct'], bins=20, alpha=0.7, color='#3498db', 
            edgecolor='white', label='Algorithm')
    ax.hist(df_comparison['gt_serangan_pct'], bins=20, alpha=0.5, color='#2ecc71',
            edgecolor='white', label='Ground Truth')
    
    ax.set_xlabel('Detection Rate (%)', fontsize=12)
    ax.set_ylabel('Frequency', fontsize=12)
    ax.set_title(f'{condition_name}\nDistribusi Deteksi', fontsize=14, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight', facecolor='#1a1a2e')
    buf.seek(0)
    charts['distribution'] = base64.b64encode(buf.read()).decode('utf-8')
    plt.close()
    
    return charts


def generate_html_report(df_comparison: pd.DataFrame, charts: dict, 
                         condition_name: str, condition_desc: str,
                         summary_stats: dict, output_path: Path) -> None:
    """Generate comprehensive HTML dashboard report."""
    
    # Calculate metrics
    correlation = df_comparison['detected_pct'].corr(df_comparison['gt_serangan_pct'])
    mae = abs(df_comparison['diff_pct']).mean()
    total_algo = df_comparison['detected_pct'].mean()
    total_gt = df_comparison['gt_serangan_pct'].mean()
    
    html = f"""<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{condition_name} - Population Analysis</title>
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
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 25px;
            border-radius: 15px;
            margin-bottom: 20px;
            text-align: center;
        }}
        .header h1 {{ font-size: 1.8em; margin-bottom: 10px; }}
        .header p {{ opacity: 0.9; font-size: 1.1em; }}
        .condition-box {{
            background: rgba(255,255,255,0.08);
            padding: 20px;
            border-radius: 12px;
            margin-bottom: 20px;
            border-left: 4px solid #667eea;
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }}
        .metric-card {{
            background: rgba(255,255,255,0.08);
            padding: 20px;
            border-radius: 12px;
            text-align: center;
        }}
        .metric-value {{ font-size: 2em; font-weight: bold; color: #667eea; }}
        .metric-label {{ color: #a0a0a0; margin-top: 5px; }}
        .charts-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(450px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }}
        .chart-card {{
            background: rgba(255,255,255,0.05);
            padding: 15px;
            border-radius: 12px;
        }}
        .chart-card img {{ width: 100%; border-radius: 8px; }}
        table {{
            width: 100%;
            border-collapse: collapse;
            background: rgba(255,255,255,0.05);
            border-radius: 12px;
            overflow: hidden;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }}
        th {{ background: rgba(102,126,234,0.3); }}
        tr:hover {{ background: rgba(255,255,255,0.05); }}
        .positive {{ color: #e74c3c; }}
        .negative {{ color: #2ecc71; }}
        .summary-section {{
            background: rgba(255,255,255,0.05);
            padding: 20px;
            border-radius: 12px;
            margin-bottom: 20px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🌴 {condition_name}</h1>
            <p>Population Segmentation Analysis - Cincin Api Algorithm</p>
            <p style="font-size: 0.9em; margin-top: 10px;">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
        </div>
        
        <div class="condition-box">
            <h3>📋 Kondisi Analisis</h3>
            <p style="margin-top: 10px;">{condition_desc}</p>
        </div>
        
        <div class="summary-section">
            <h3>📊 Ringkasan Populasi</h3>
            <div class="metrics-grid" style="margin-top: 15px;">
                <div class="metric-card">
                    <div class="metric-value">{summary_stats.get('total_trees', 0):,}</div>
                    <div class="metric-label">Total Pohon Dianalisis</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{summary_stats.get('mature_count', 0):,}</div>
                    <div class="metric-label">MATURE (Pokok+Tamb)</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{summary_stats.get('young_count', 0):,}</div>
                    <div class="metric-label">YOUNG (Sisip)</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{summary_stats.get('excluded_count', 0):,}</div>
                    <div class="metric-label">Excluded (Mati+Kosong)</div>
                </div>
            </div>
        </div>
        
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-value">{correlation:.3f}</div>
                <div class="metric-label">Korelasi (r)</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{mae:.2f}%</div>
                <div class="metric-label">Mean Absolute Error</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{total_algo:.2f}%</div>
                <div class="metric-label">Avg Detection (Algo)</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{total_gt:.2f}%</div>
                <div class="metric-label">Avg Detection (GT)</div>
            </div>
        </div>
        
        <div class="charts-grid">
            <div class="chart-card">
                <h4 style="margin-bottom: 10px;">Algorithm vs Ground Truth</h4>
                <img src="data:image/png;base64,{charts.get('scatter', '')}" alt="Scatter">
            </div>
            <div class="chart-card">
                <h4 style="margin-bottom: 10px;">Distribusi Deteksi</h4>
                <img src="data:image/png;base64,{charts.get('distribution', '')}" alt="Distribution">
            </div>
        </div>
        
        <div class="summary-section">
            <h3>📋 Detail Per Blok (Top 20 by Difference)</h3>
            <table style="margin-top: 15px;">
                <thead>
                    <tr>
                        <th>Blok</th>
                        <th>Total Pohon</th>
                        <th>G3 Count</th>
                        <th>G2 Count</th>
                        <th>Algo (%)</th>
                        <th>GT (%)</th>
                        <th>Selisih</th>
                    </tr>
                </thead>
                <tbody>
"""
    
    # Add top 20 rows by absolute difference
    df_sorted = df_comparison.sort_values('diff_pct', key=abs, ascending=False).head(20)
    for _, row in df_sorted.iterrows():
        diff_class = 'positive' if row['diff_pct'] > 0 else 'negative'
        html += f"""
                    <tr>
                        <td>{row['blok']}</td>
                        <td>{row['total']:,}</td>
                        <td>{row['g3_count']:,}</td>
                        <td>{row['g2_count']:,}</td>
                        <td>{row['detected_pct']:.2f}%</td>
                        <td>{row['gt_serangan_pct']:.2f}%</td>
                        <td class="{diff_class}">{row['diff_pct']:+.2f}%</td>
                    </tr>
"""
    
    html += """
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>
"""
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"HTML report saved: {output_path}")


# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main():
    print("="*70)
    print("POPULATION SEGMENTATION ANALYSIS")
    print("3 Conditions Comparison")
    print("="*70)
    
    # Setup output directories
    base_output = script_dir / "data" / "output" / "population_analysis"
    
    conditions = {
        'condition_1_mature_only': {
            'name': 'Condition 1: MATURE Only',
            'desc': 'Hanya menganalisis pohon MATURE (Pokok Utama + Tambahan). Exclude: Sisip, Mati, Kosong.',
            'func': run_condition_1
        },
        'condition_2_all_living': {
            'name': 'Condition 2: All Living Trees',
            'desc': 'Menganalisis semua pohon hidup (MATURE + YOUNG). Exclude: Mati, Kosong. Menggunakan baseline tunggal.',
            'func': run_condition_2
        },
        'condition_3_adaptive': {
            'name': 'Condition 3: Adaptive Threshold',
            'desc': 'Menganalisis semua pohon hidup dengan baseline TERPISAH untuk MATURE dan YOUNG. Exclude: Mati, Kosong.',
            'func': run_condition_3
        }
    }
    
    # Load data
    print("\n[1/5] Loading drone data...")
    df_ame2 = load_and_clean_data(script_dir / "data/input/tabelNDREnew.csv")
    df_ame4 = load_ame_iv_data(script_dir / "data/input/AME_IV.csv")
    
    print(f"  - AME II: {len(df_ame2):,} rows")
    print(f"  - AME IV: {len(df_ame4):,} rows")
    
    # Load ground truth
    print("\n[2/5] Loading ground truth...")
    df_gt = pd.read_excel(
        script_dir / "data/input/areal_inti_serangan_gano_AMEII_AMEIV.xlsx",
        sheet_name='Sheet1', header=[0, 1]
    )
    df_gt.columns = ['DIVISI', 'BLOK', 'TAHUN_TANAM', 'LUAS_SD_2024', 'PENAMBAHAN', 
                     'LUAS_SD_2025', 'TANAM', 'SISIP', 'SISIP_KENTOSAN', 'TOTAL_PKK',
                     'SPH', 'STADIUM_12', 'STADIUM_34', 'TOTAL_GANO', 'SERANGAN_PCT']
    df_gt = df_gt[df_gt['DIVISI'].isin(['AME002', 'AME004'])]
    
    print(f"  - Ground truth: {len(df_gt)} blok")
    
    # Process each condition
    all_results = []
    
    for cond_key, cond_info in conditions.items():
        print(f"\n[3/5] Processing {cond_info['name']}...")
        
        output_dir = base_output / cond_key
        output_dir.mkdir(parents=True, exist_ok=True)
        
        for divisi_code, divisi_name, df_drone in [
            ('AME002', 'AME II', df_ame2),
            ('AME004', 'AME IV', df_ame4)
        ]:
            print(f"  - {divisi_name}...")
            
            # Get original counts
            total_orig = len(df_drone)
            mature_count = len(df_drone[df_drone['Category'] == 'MATURE'])
            young_count = len(df_drone[df_drone['Category'] == 'YOUNG'])
            excluded = len(df_drone[df_drone['Category'].isin(['DEAD', 'EMPTY'])])
            
            # Run condition
            df_result = cond_info['func'](df_drone.copy())
            
            # Calculate detection rates
            df_detection = calculate_detection_rate(df_result)
            
            # Compare with ground truth
            df_comparison = compare_with_ground_truth(df_detection, df_gt, divisi_code)
            
            # Save CSV
            csv_path = output_dir / f"{divisi_code}_comparison.csv"
            df_comparison.to_csv(csv_path, index=False)
            print(f"    CSV saved: {csv_path}")
            
            # Generate charts
            charts = generate_charts(df_comparison, f"{cond_info['name']} - {divisi_name}")
            
            # Generate HTML report
            summary_stats = {
                'total_trees': len(df_result),
                'mature_count': len(df_result[df_result['Category'] == 'MATURE']) if 'Category' in df_result.columns else mature_count,
                'young_count': len(df_result[df_result['Category'] == 'YOUNG']) if 'Category' in df_result.columns else 0,
                'excluded_count': excluded
            }
            
            html_path = output_dir / f"{divisi_code}_report.html"
            generate_html_report(
                df_comparison, charts,
                f"{cond_info['name']} - {divisi_name}",
                cond_info['desc'],
                summary_stats,
                html_path
            )
            
            # Collect results for summary
            correlation = df_comparison['detected_pct'].corr(df_comparison['gt_serangan_pct'])
            mae = abs(df_comparison['diff_pct']).mean()
            
            all_results.append({
                'condition': cond_key,
                'condition_name': cond_info['name'],
                'divisi': divisi_code,
                'total_analyzed': len(df_result),
                'correlation': correlation,
                'mae': mae,
                'avg_algo_pct': df_comparison['detected_pct'].mean(),
                'avg_gt_pct': df_comparison['gt_serangan_pct'].mean()
            })
    
    # Generate summary comparison
    print("\n[4/5] Generating summary comparison...")
    df_summary = pd.DataFrame(all_results)
    summary_path = base_output / "summary_comparison.csv"
    df_summary.to_csv(summary_path, index=False)
    print(f"  Summary saved: {summary_path}")
    
    # Print summary
    print("\n" + "="*70)
    print("SUMMARY RESULTS")
    print("="*70)
    print(df_summary.to_string(index=False))
    
    print(f"\n[5/5] Complete! Reports saved to: {base_output}")
    
    return df_summary


if __name__ == "__main__":
    main()
