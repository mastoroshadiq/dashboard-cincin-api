"""
Comparison: Option A vs Option B - Cincin Api Analysis
=======================================================

OPSI A: MATURE Only (Current)
- Include: MATURE (Pokok Utama + Tambahan)
- Exclude: YOUNG, DEAD, EMPTY
- Threshold: AME II Z<-1.5, AME IV Z<-4.0

OPSI B: Include YOUNG with Separate Threshold
- Include: MATURE + YOUNG
- Exclude: DEAD, EMPTY
- MATURE Threshold: AME II Z<-1.5, AME IV Z<-4.0
- YOUNG Threshold: Z<-2.0 (lebih ketat untuk mencegah false positive)
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
from matplotlib.patches import RegularPolygon
from matplotlib.collections import PatchCollection

import logging
logging.disable(logging.CRITICAL)

from src.ingestion import load_and_clean_data, load_ame_iv_data
from src.cost_control_loader import normalize_block
from config import get_calibrated_threshold


# =============================================================================
# DETECTION FUNCTIONS
# =============================================================================

def run_option_a(df: pd.DataFrame, divisi: str) -> pd.DataFrame:
    """
    OPSI A: MATURE Only
    - Only MATURE trees included
    - Calibrated threshold per divisi
    """
    # Filter MATURE only
    df_result = df[df['Category'] == 'MATURE'].copy()
    
    thresh = get_calibrated_threshold(divisi)
    z_g3 = thresh['Z_Threshold_G3']
    z_g2 = thresh['Z_Threshold_G2']
    
    df_result['Z_Score'] = 0.0
    df_result['G_Status'] = 'G1'
    df_result['Option'] = 'A'
    
    for blok in df_result['Blok'].unique():
        mask = df_result['Blok'] == blok
        ndre = df_result.loc[mask, 'NDRE125']
        
        if len(ndre) > 1:
            mean_v, std_v = ndre.mean(), ndre.std()
            if std_v > 0:
                z = (ndre - mean_v) / std_v
                df_result.loc[mask, 'Z_Score'] = z
                df_result.loc[mask & (df_result['Z_Score'] < z_g3), 'G_Status'] = 'G3'
                df_result.loc[mask & (df_result['Z_Score'] >= z_g3) & (df_result['Z_Score'] < z_g2), 'G_Status'] = 'G2'
    
    return df_result


def run_option_b(df: pd.DataFrame, divisi: str) -> pd.DataFrame:
    """
    OPSI B: Include YOUNG with Separate Threshold
    - MATURE + YOUNG included
    - MATURE: calibrated threshold
    - YOUNG: stricter threshold Z<-2.0
    """
    # Filter MATURE + YOUNG (exclude DEAD, EMPTY)
    df_result = df[df['Category'].isin(['MATURE', 'YOUNG'])].copy()
    
    thresh = get_calibrated_threshold(divisi)
    z_g3_mature = thresh['Z_Threshold_G3']
    z_g2_mature = thresh['Z_Threshold_G2']
    
    # YOUNG uses stricter threshold
    z_g3_young = -2.0
    z_g2_young = -1.0
    
    df_result['Z_Score'] = 0.0
    df_result['G_Status'] = 'G1'
    df_result['Option'] = 'B'
    
    for blok in df_result['Blok'].unique():
        mask_blok = df_result['Blok'] == blok
        
        # Process MATURE with MATURE baseline
        mask_mature = mask_blok & (df_result['Category'] == 'MATURE')
        if mask_mature.sum() > 1:
            ndre_m = df_result.loc[mask_mature, 'NDRE125']
            mean_m, std_m = ndre_m.mean(), ndre_m.std()
            if std_m > 0:
                z_m = (ndre_m - mean_m) / std_m
                df_result.loc[mask_mature, 'Z_Score'] = z_m
                df_result.loc[mask_mature & (df_result['Z_Score'] < z_g3_mature), 'G_Status'] = 'G3'
                df_result.loc[mask_mature & (df_result['Z_Score'] >= z_g3_mature) & (df_result['Z_Score'] < z_g2_mature), 'G_Status'] = 'G2'
        
        # Process YOUNG with YOUNG baseline (separate)
        mask_young = mask_blok & (df_result['Category'] == 'YOUNG')
        if mask_young.sum() > 1:
            ndre_y = df_result.loc[mask_young, 'NDRE125']
            mean_y, std_y = ndre_y.mean(), ndre_y.std()
            if std_y > 0:
                z_y = (ndre_y - mean_y) / std_y
                df_result.loc[mask_young, 'Z_Score'] = z_y
                df_result.loc[mask_young & (df_result['Z_Score'] < z_g3_young), 'G_Status'] = 'G3'
                df_result.loc[mask_young & (df_result['Z_Score'] >= z_g3_young) & (df_result['Z_Score'] < z_g2_young), 'G_Status'] = 'G2'
    
    return df_result


# =============================================================================
# CINCIN API CLUSTERING
# =============================================================================

def find_cincin_api_clusters(df: pd.DataFrame, blok: str, min_sick_neighbors: int = 2) -> pd.DataFrame:
    """
    Find Cincin Api clusters - G3 trees surrounded by sick neighbors.
    Returns DataFrame with cluster info.
    """
    df_blok = df[df['Blok'] == blok].copy()
    
    if len(df_blok) == 0:
        return pd.DataFrame()
    
    # Create grid lookup
    grid = {}
    for idx, row in df_blok.iterrows():
        key = (row['N_BARIS'], row['N_POKOK'])
        grid[key] = {
            'idx': idx,
            'status': row['G_Status'],
            'category': row.get('Category', 'MATURE')
        }
    
    # Find clusters (G3 with sick neighbors)
    clusters = []
    for (baris, pokok), info in grid.items():
        if info['status'] == 'G3':
            # Check 6 hexagonal neighbors
            neighbors_offsets = [
                (-1, 0), (1, 0),   # same row
                (-1, -1), (0, -1), # row above
                (-1, 1), (0, 1)    # row below
            ]
            
            sick_neighbors = 0
            for db, dp in neighbors_offsets:
                neighbor_key = (baris + db, pokok + dp)
                if neighbor_key in grid and grid[neighbor_key]['status'] in ['G2', 'G3']:
                    sick_neighbors += 1
            
            if sick_neighbors >= min_sick_neighbors:
                clusters.append({
                    'blok': blok,
                    'n_baris': baris,
                    'n_pokok': pokok,
                    'status': 'MERAH',  # Cincin Api trigger
                    'sick_neighbors': sick_neighbors,
                    'category': info['category']
                })
            else:
                clusters.append({
                    'blok': blok,
                    'n_baris': baris,
                    'n_pokok': pokok,
                    'status': 'ORANYE',  # Isolated G3
                    'sick_neighbors': sick_neighbors,
                    'category': info['category']
                })
    
    return pd.DataFrame(clusters)


def generate_block_heatmap(df: pd.DataFrame, blok: str, option: str) -> str:
    """Generate heatmap for a block, return base64 image."""
    df_blok = df[df['Blok'] == blok].copy()
    
    if len(df_blok) == 0:
        return ""
    
    fig, ax = plt.subplots(figsize=(12, 8))
    plt.style.use('dark_background')
    
    # Color mapping
    color_map = {
        'G1': '#27ae60',  # Green - Healthy
        'G2': '#f39c12',  # Orange - Warning
        'G3': '#e74c3c',  # Red - Sick
    }
    
    # Plot each tree
    for _, row in df_blok.iterrows():
        color = color_map.get(row['G_Status'], '#7f8c8d')
        marker = 'o' if row.get('Category', 'MATURE') == 'MATURE' else '^'  # Triangle for YOUNG
        ax.scatter(row['N_POKOK'], row['N_BARIS'], c=color, s=30, marker=marker, alpha=0.7)
    
    ax.set_xlabel('N_POKOK')
    ax.set_ylabel('N_BARIS')
    ax.set_title(f'{blok} - Option {option}\nG1={len(df_blok[df_blok["G_Status"]=="G1"])}, G2={len(df_blok[df_blok["G_Status"]=="G2"])}, G3={len(df_blok[df_blok["G_Status"]=="G3"])}')
    ax.invert_yaxis()
    
    # Legend
    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], marker='o', color='w', markerfacecolor='#27ae60', markersize=10, label='G1 (Sehat)'),
        Line2D([0], [0], marker='o', color='w', markerfacecolor='#f39c12', markersize=10, label='G2 (Warning)'),
        Line2D([0], [0], marker='o', color='w', markerfacecolor='#e74c3c', markersize=10, label='G3 (Sick)'),
    ]
    ax.legend(handles=legend_elements, loc='upper right')
    
    plt.tight_layout()
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight', facecolor='#1a1a2e')
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')
    plt.close()
    
    return img_base64


# =============================================================================
# COMPARISON & REPORTING
# =============================================================================

def calculate_metrics(df: pd.DataFrame, df_gt: pd.DataFrame, divisi: str) -> dict:
    """Calculate detection metrics."""
    df_gt_div = df_gt[df_gt['DIVISI'] == divisi].copy()
    df_gt_div['blok_norm'] = df_gt_div['BLOK'].apply(normalize_block)
    
    results = []
    for blok in df['Blok'].unique():
        df_blok = df[df['Blok'] == blok]
        total = len(df_blok)
        g3 = len(df_blok[df_blok['G_Status'] == 'G3'])
        g2 = len(df_blok[df_blok['G_Status'] == 'G2'])
        
        results.append({
            'blok': blok,
            'blok_norm': normalize_block(blok),
            'total': total,
            'g3': g3,
            'g2': g2,
            'detected_pct': (g3 + g2) / total * 100 if total > 0 else 0
        })
    
    df_res = pd.DataFrame(results)
    df_merged = df_res.merge(
        df_gt_div[['blok_norm', 'TOTAL_GANO', 'TOTAL_PKK']],
        on='blok_norm', how='inner'
    )
    
    if len(df_merged) == 0:
        return {'mae': 0, 'corr': 0, 'total': 0, 'g3_total': 0, 'g2_total': 0}
    
    df_merged['gt_pct'] = df_merged['TOTAL_GANO'] / df_merged['TOTAL_PKK'] * 100
    
    return {
        'mae': abs(df_merged['detected_pct'] - df_merged['gt_pct']).mean(),
        'corr': df_merged['detected_pct'].corr(df_merged['gt_pct']),
        'total': df['Blok'].nunique(),
        'g3_total': df[df['G_Status'] == 'G3'].shape[0],
        'g2_total': df[df['G_Status'] == 'G2'].shape[0],
        'total_trees': len(df)
    }


def generate_comparison_html(results: dict, block_charts: dict, output_path: Path):
    """Generate comprehensive HTML comparison report."""
    
    html = f"""<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Comparison: Option A vs Option B - Cincin Api</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: 'Segoe UI', Tahoma, sans-serif; 
            background: linear-gradient(135deg, #0f0f23 0%, #1a1a2e 100%);
            color: #e0e0e0; 
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{ max-width: 1800px; margin: 0 auto; }}
        .header {{ 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 30px;
            border-radius: 15px;
            margin-bottom: 25px;
            text-align: center;
        }}
        .header h1 {{ font-size: 2em; }}
        .options-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 25px;
        }}
        .option-card {{
            background: rgba(255,255,255,0.05);
            border-radius: 15px;
            padding: 25px;
            border: 2px solid rgba(255,255,255,0.1);
        }}
        .option-card.option-a {{ border-color: #3498db; }}
        .option-card.option-b {{ border-color: #2ecc71; }}
        .option-card h2 {{ margin-bottom: 15px; }}
        .metric-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
            margin-top: 15px;
        }}
        .metric {{
            background: rgba(255,255,255,0.05);
            padding: 15px;
            border-radius: 10px;
            text-align: center;
        }}
        .metric-value {{ font-size: 1.5em; font-weight: bold; }}
        .metric-label {{ color: #a0a0a0; font-size: 0.9em; }}
        .divisi-section {{
            background: rgba(255,255,255,0.03);
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 25px;
        }}
        .divisi-section h3 {{ margin-bottom: 20px; color: #667eea; }}
        .blocks-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 15px;
        }}
        .block-card {{
            background: rgba(255,255,255,0.05);
            padding: 15px;
            border-radius: 10px;
        }}
        .block-card h4 {{ margin-bottom: 10px; }}
        .block-card img {{ width: 100%; border-radius: 8px; }}
        .comparison-row {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
        }}
        .comparison-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }}
        .comparison-table th, .comparison-table td {{
            padding: 12px;
            text-align: center;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }}
        .comparison-table th {{ background: rgba(102,126,234,0.2); }}
        .better {{ color: #2ecc71; font-weight: bold; }}
        .worse {{ color: #e74c3c; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔥 Cincin Api Analysis: Option A vs Option B</h1>
            <p>Calibrated Threshold Comparison with Clustering Visualization</p>
            <p style="margin-top: 10px; opacity: 0.8;">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
        </div>
        
        <div class="options-grid">
            <div class="option-card option-a">
                <h2>🅰️ OPSI A: MATURE Only</h2>
                <p>Include: Pokok Utama + Tambahan</p>
                <p>Exclude: Sisip, Mati, Kosong</p>
                <p style="margin-top: 10px;"><strong>Threshold:</strong></p>
                <p>• AME II: Z &lt; -1.5</p>
                <p>• AME IV: Z &lt; -4.0</p>
            </div>
            
            <div class="option-card option-b">
                <h2>🅱️ OPSI B: Include YOUNG (Sisip)</h2>
                <p>Include: Pokok Utama + Tambahan + Sisip</p>
                <p>Exclude: Mati, Kosong</p>
                <p style="margin-top: 10px;"><strong>Threshold:</strong></p>
                <p>• MATURE: AME II Z&lt;-1.5, AME IV Z&lt;-4.0</p>
                <p>• YOUNG: Z &lt; -2.0 (separate baseline)</p>
            </div>
        </div>
"""
    
    # Add metrics comparison for each divisi
    for divisi in ['AME002', 'AME004']:
        divisi_name = 'AME II' if divisi == 'AME002' else 'AME IV'
        metrics_a = results[divisi]['A']
        metrics_b = results[divisi]['B']
        
        better_mae = 'A' if metrics_a['mae'] < metrics_b['mae'] else 'B'
        
        html += f"""
        <div class="divisi-section">
            <h3>🌴 {divisi_name} ({divisi})</h3>
            
            <table class="comparison-table">
                <thead>
                    <tr>
                        <th>Metric</th>
                        <th>Option A</th>
                        <th>Option B</th>
                        <th>Better</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>Total Trees Analyzed</td>
                        <td>{metrics_a['total_trees']:,}</td>
                        <td>{metrics_b['total_trees']:,}</td>
                        <td>-</td>
                    </tr>
                    <tr>
                        <td>G3 (Sick) Count</td>
                        <td>{metrics_a['g3_total']:,}</td>
                        <td>{metrics_b['g3_total']:,}</td>
                        <td>-</td>
                    </tr>
                    <tr>
                        <td>G2 (Warning) Count</td>
                        <td>{metrics_a['g2_total']:,}</td>
                        <td>{metrics_b['g2_total']:,}</td>
                        <td>-</td>
                    </tr>
                    <tr>
                        <td>MAE vs Ground Truth</td>
                        <td class="{'better' if better_mae == 'A' else ''}">{metrics_a['mae']:.2f}%</td>
                        <td class="{'better' if better_mae == 'B' else ''}">{metrics_b['mae']:.2f}%</td>
                        <td class="better">Option {better_mae}</td>
                    </tr>
                    <tr>
                        <td>Correlation</td>
                        <td>{metrics_a['corr']:.3f}</td>
                        <td>{metrics_b['corr']:.3f}</td>
                        <td>-</td>
                    </tr>
                </tbody>
            </table>
"""
        
        # Add block visualizations
        if divisi in block_charts and len(block_charts[divisi]) > 0:
            html += """
            <h4 style="margin-top: 25px;">📊 Block Visualizations (Top 5 by G3 count)</h4>
            <div class="blocks-grid">
"""
            for blok_data in block_charts[divisi][:5]:
                html += f"""
                <div class="block-card">
                    <h4>{blok_data['blok']}</h4>
                    <div class="comparison-row">
                        <div>
                            <p style="text-align:center; font-size:0.9em;">Option A</p>
                            <img src="data:image/png;base64,{blok_data['chart_a']}" alt="Option A">
                        </div>
                        <div>
                            <p style="text-align:center; font-size:0.9em;">Option B</p>
                            <img src="data:image/png;base64,{blok_data['chart_b']}" alt="Option B">
                        </div>
                    </div>
                </div>
"""
            html += "</div>"
        
        html += "</div>"  # Close divisi section
    
    html += """
    </div>
</body>
</html>
"""
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"Report saved: {output_path}")


# =============================================================================
# MAIN
# =============================================================================

def main():
    print("="*70)
    print("COMPARISON: Option A vs Option B - Cincin Api Analysis")
    print("="*70)
    
    output_dir = script_dir / "data" / "output" / "option_comparison"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load data
    print("\n[1/5] Loading data...")
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
    
    results = {}
    block_charts = {}
    
    # Process each divisi
    for divisi_code, divisi_name, df_drone in [('AME002', 'AME II', df_ame2), ('AME004', 'AME IV', df_ame4)]:
        print(f"\n[2/5] Processing {divisi_name}...")
        results[divisi_code] = {}
        block_charts[divisi_code] = []
        
        # Run Option A
        print(f"  Running Option A (MATURE only)...")
        df_a = run_option_a(df_drone.copy(), divisi_code)
        results[divisi_code]['A'] = calculate_metrics(df_a, df_gt, divisi_code)
        
        # Run Option B
        print(f"  Running Option B (Include YOUNG)...")
        df_b = run_option_b(df_drone.copy(), divisi_code)
        results[divisi_code]['B'] = calculate_metrics(df_b, df_gt, divisi_code)
        
        # Find top blocks by G3 count for visualization
        print(f"  Generating block visualizations...")
        g3_per_block_a = df_a[df_a['G_Status'] == 'G3'].groupby('Blok').size().sort_values(ascending=False)
        top_blocks = g3_per_block_a.head(5).index.tolist()
        
        for blok in top_blocks:
            chart_a = generate_block_heatmap(df_a, blok, 'A')
            chart_b = generate_block_heatmap(df_b, blok, 'B')
            
            if chart_a and chart_b:
                block_charts[divisi_code].append({
                    'blok': blok,
                    'chart_a': chart_a,
                    'chart_b': chart_b
                })
        
        # Save CSVs
        df_a.to_csv(output_dir / f"{divisi_code}_option_a.csv", index=False)
        df_b.to_csv(output_dir / f"{divisi_code}_option_b.csv", index=False)
    
    # Generate comparison HTML
    print("\n[4/5] Generating comparison report...")
    generate_comparison_html(results, block_charts, output_dir / "comparison_report.html")
    
    # Print summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    
    for divisi in ['AME002', 'AME004']:
        divisi_name = 'AME II' if divisi == 'AME002' else 'AME IV'
        print(f"\n{divisi_name}:")
        print(f"  Option A: Trees={results[divisi]['A']['total_trees']:,}, G3={results[divisi]['A']['g3_total']:,}, MAE={results[divisi]['A']['mae']:.2f}%")
        print(f"  Option B: Trees={results[divisi]['B']['total_trees']:,}, G3={results[divisi]['B']['g3_total']:,}, MAE={results[divisi]['B']['mae']:.2f}%")
    
    print(f"\n[5/5] Complete! Report saved to: {output_dir}")
    
    # Open report
    import os
    os.startfile(output_dir / "comparison_report.html")


if __name__ == "__main__":
    main()
