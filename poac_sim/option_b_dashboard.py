"""
Option B Dashboard - Cincin Api Analysis
=========================================

Dashboard khusus untuk Option B (Include YOUNG dengan threshold terpisah)
Menampilkan:
1. Summary per divisi
2. Cincin Api clustering visualization
3. Top blocks with clusters
4. YOUNG vs MATURE comparison
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

import logging
logging.disable(logging.CRITICAL)

from src.ingestion import load_and_clean_data, load_ame_iv_data
from config import get_calibrated_threshold


def run_option_b(df: pd.DataFrame, divisi: str) -> pd.DataFrame:
    """Option B: Include YOUNG with separate threshold."""
    df_result = df[df['Category'].isin(['MATURE', 'YOUNG'])].copy()
    
    thresh = get_calibrated_threshold(divisi)
    z_g3_mature = thresh['Z_Threshold_G3']
    z_g2_mature = thresh['Z_Threshold_G2']
    z_g3_young = -2.0
    z_g2_young = -1.0
    
    df_result['Z_Score'] = 0.0
    df_result['G_Status'] = 'G1'
    df_result['Cincin_Status'] = 'NORMAL'
    
    for blok in df_result['Blok'].unique():
        mask_blok = df_result['Blok'] == blok
        
        # MATURE
        mask_mature = mask_blok & (df_result['Category'] == 'MATURE')
        if mask_mature.sum() > 1:
            ndre_m = df_result.loc[mask_mature, 'NDRE125']
            mean_m, std_m = ndre_m.mean(), ndre_m.std()
            if std_m > 0:
                z_m = (ndre_m - mean_m) / std_m
                df_result.loc[mask_mature, 'Z_Score'] = z_m
                df_result.loc[mask_mature & (df_result['Z_Score'] < z_g3_mature), 'G_Status'] = 'G3'
                df_result.loc[mask_mature & (df_result['Z_Score'] >= z_g3_mature) & (df_result['Z_Score'] < z_g2_mature), 'G_Status'] = 'G2'
        
        # YOUNG
        mask_young = mask_blok & (df_result['Category'] == 'YOUNG')
        if mask_young.sum() > 1:
            ndre_y = df_result.loc[mask_young, 'NDRE125']
            mean_y, std_y = ndre_y.mean(), ndre_y.std()
            if std_y > 0:
                z_y = (ndre_y - mean_y) / std_y
                df_result.loc[mask_young, 'Z_Score'] = z_y
                df_result.loc[mask_young & (df_result['Z_Score'] < z_g3_young), 'G_Status'] = 'G3'
                df_result.loc[mask_young & (df_result['Z_Score'] >= z_g3_young) & (df_result['Z_Score'] < z_g2_young), 'G_Status'] = 'G2'
    
    # Find Cincin Api clusters
    for blok in df_result['Blok'].unique():
        df_blok = df_result[df_result['Blok'] == blok]
        
        grid = {}
        for idx, row in df_blok.iterrows():
            grid[(row['N_BARIS'], row['N_POKOK'])] = {'idx': idx, 'status': row['G_Status']}
        
        for (baris, pokok), info in grid.items():
            if info['status'] == 'G3':
                neighbors = [(-1,0), (1,0), (-1,-1), (0,-1), (-1,1), (0,1)]
                sick = sum(1 for db, dp in neighbors if (baris+db, pokok+dp) in grid and grid[(baris+db, pokok+dp)]['status'] in ['G2','G3'])
                
                if sick >= 2:
                    df_result.loc[info['idx'], 'Cincin_Status'] = 'MERAH'
                else:
                    df_result.loc[info['idx'], 'Cincin_Status'] = 'ORANYE'
    
    return df_result


def generate_block_chart(df: pd.DataFrame, blok: str) -> str:
    """Generate block heatmap chart."""
    df_blok = df[df['Blok'] == blok]
    if len(df_blok) == 0:
        return ""
    
    fig, ax = plt.subplots(figsize=(14, 10))
    plt.style.use('dark_background')
    
    colors = {'G1': '#27ae60', 'G2': '#f39c12', 'G3': '#e74c3c'}
    markers = {'MATURE': 'o', 'YOUNG': '^'}
    sizes = {'G1': 30, 'G2': 50, 'G3': 80}
    
    for cat in ['MATURE', 'YOUNG']:
        for status in ['G1', 'G2', 'G3']:
            mask = (df_blok['Category'] == cat) & (df_blok['G_Status'] == status)
            data = df_blok[mask]
            if len(data) > 0:
                ax.scatter(data['N_POKOK'], data['N_BARIS'], 
                          c=colors[status], marker=markers[cat], s=sizes[status],
                          alpha=0.7, label=f'{cat} {status}' if len(data) > 0 else None)
    
    # Highlight MERAH clusters
    merah = df_blok[df_blok['Cincin_Status'] == 'MERAH']
    if len(merah) > 0:
        ax.scatter(merah['N_POKOK'], merah['N_BARIS'], 
                  facecolors='none', edgecolors='white', s=150, linewidths=2,
                  label=f'CINCIN API ({len(merah)})')
    
    ax.set_xlabel('N_POKOK', fontsize=12)
    ax.set_ylabel('N_BARIS', fontsize=12)
    ax.invert_yaxis()
    
    g1 = len(df_blok[df_blok['G_Status']=='G1'])
    g2 = len(df_blok[df_blok['G_Status']=='G2'])
    g3 = len(df_blok[df_blok['G_Status']=='G3'])
    merah_count = len(merah)
    
    ax.set_title(f'{blok}\nTotal: {len(df_blok):,} | G1: {g1:,} | G2: {g2:,} | G3: {g3:,} | Cincin Api: {merah_count}', 
                fontsize=14, fontweight='bold')
    
    ax.legend(loc='upper right', fontsize=9)
    ax.grid(True, alpha=0.2)
    
    plt.tight_layout()
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight', facecolor='#1a1a2e')
    buf.seek(0)
    img = base64.b64encode(buf.read()).decode('utf-8')
    plt.close()
    return img


def main():
    print("="*70)
    print("OPTION B DASHBOARD - Cincin Api Analysis")
    print("="*70)
    
    output_dir = script_dir / "data" / "output" / "option_b_dashboard"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load data
    print("\n[1/5] Loading data...")
    df_ame2 = load_and_clean_data(script_dir / "data/input/tabelNDREnew.csv")
    df_ame4 = load_ame_iv_data(script_dir / "data/input/AME_IV.csv")
    
    # Load ground truth
    print("[2/5] Loading ground truth...")
    from src.cost_control_loader import normalize_block
    
    df_gt = pd.read_excel(
        script_dir / "data/input/areal_inti_serangan_gano_AMEII_AMEIV.xlsx",
        sheet_name='Sheet1', header=[0, 1]
    )
    df_gt.columns = ['DIVISI', 'BLOK', 'TAHUN_TANAM', 'LUAS_SD_2024', 'PENAMBAHAN', 
                     'LUAS_SD_2025', 'TANAM', 'SISIP', 'SISIP_KENTOSAN', 'TOTAL_PKK',
                     'SPH', 'STADIUM_12', 'STADIUM_34', 'TOTAL_GANO', 'SERANGAN_PCT']
    
    results = {}
    block_charts = {}
    gt_comparison = {}
    
    for divisi_code, divisi_name, df_drone in [('AME002', 'AME II', df_ame2), ('AME004', 'AME IV', df_ame4)]:
        print(f"\n[3/5] Processing {divisi_name}...")
        
        df_result = run_option_b(df_drone.copy(), divisi_code)
        
        # Stats
        total = len(df_result)
        mature_count = len(df_result[df_result['Category']=='MATURE'])
        young_count = len(df_result[df_result['Category']=='YOUNG'])
        g3 = len(df_result[df_result['G_Status']=='G3'])
        g2 = len(df_result[df_result['G_Status']=='G2'])
        g1 = len(df_result[df_result['G_Status']=='G1'])
        merah = len(df_result[df_result['Cincin_Status']=='MERAH'])
        oranye = len(df_result[df_result['Cincin_Status']=='ORANYE'])
        
        # YOUNG breakdown
        young_df = df_result[df_result['Category']=='YOUNG']
        young_g3 = len(young_df[young_df['G_Status']=='G3'])
        young_g2 = len(young_df[young_df['G_Status']=='G2'])
        
        results[divisi_code] = {
            'total': total, 'mature': mature_count, 'young': young_count,
            'g3': g3, 'g2': g2, 'g1': g1, 'merah': merah, 'oranye': oranye,
            'young_g3': young_g3, 'young_g2': young_g2
        }
        
        # Ground Truth Comparison
        print(f"  Comparing with ground truth...")
        df_gt_div = df_gt[df_gt['DIVISI'] == divisi_code].copy()
        df_gt_div['blok_norm'] = df_gt_div['BLOK'].apply(normalize_block)
        df_gt_div['gt_pct'] = df_gt_div['TOTAL_GANO'] / df_gt_div['TOTAL_PKK'] * 100
        
        block_metrics = []
        for blok in df_result['Blok'].unique():
            df_blok = df_result[df_result['Blok'] == blok]
            total_blok = len(df_blok)
            g3_blok = len(df_blok[df_blok['G_Status'] == 'G3'])
            g2_blok = len(df_blok[df_blok['G_Status'] == 'G2'])
            detected_pct = (g3_blok + g2_blok) / total_blok * 100 if total_blok > 0 else 0
            
            block_metrics.append({
                'blok': blok,
                'blok_norm': normalize_block(blok),
                'total': total_blok,
                'g3': g3_blok,
                'g2': g2_blok,
                'detected_pct': detected_pct
            })
        
        df_metrics = pd.DataFrame(block_metrics)
        df_merged = df_metrics.merge(df_gt_div[['blok_norm', 'gt_pct', 'TOTAL_GANO', 'TOTAL_PKK']], on='blok_norm', how='inner')
        
        if len(df_merged) > 0:
            mae = abs(df_merged['detected_pct'] - df_merged['gt_pct']).mean()
            corr = df_merged['detected_pct'].corr(df_merged['gt_pct'])
            avg_algo = df_merged['detected_pct'].mean()
            avg_gt = df_merged['gt_pct'].mean()
            bias = avg_algo - avg_gt
        else:
            mae, corr, avg_algo, avg_gt, bias = 0, 0, 0, 0, 0
        
        gt_comparison[divisi_code] = {
            'mae': mae, 'corr': corr, 'avg_algo': avg_algo, 'avg_gt': avg_gt, 'bias': bias,
            'n_blocks': len(df_merged),
            'df_merged': df_merged
        }
        
        results[divisi_code]['mae'] = mae
        results[divisi_code]['corr'] = corr
        results[divisi_code]['avg_algo'] = avg_algo
        results[divisi_code]['avg_gt'] = avg_gt
        
        # Generate top block charts
        print(f"  Generating block visualizations...")
        g3_per_block = df_result[df_result['G_Status']=='G3'].groupby('Blok').size().sort_values(ascending=False)
        top_blocks = g3_per_block.head(8).index.tolist()
        
        block_charts[divisi_code] = []
        for blok in top_blocks:
            chart = generate_block_chart(df_result, blok)
            if chart:
                block_charts[divisi_code].append({'blok': blok, 'chart': chart})
        
        # Save CSV
        df_result.to_csv(output_dir / f"{divisi_code}_option_b.csv", index=False)
        df_merged.to_csv(output_dir / f"{divisi_code}_gt_comparison.csv", index=False)
    
    # Generate HTML Dashboard
    print("\n[3/4] Generating dashboard...")
    
    thresh_ame2 = get_calibrated_threshold('AME002')
    thresh_ame4 = get_calibrated_threshold('AME004')
    
    html = f"""<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Option B Dashboard - Cincin Api</title>
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
            background: linear-gradient(135deg, #2ecc71 0%, #27ae60 100%);
            padding: 35px;
            border-radius: 20px;
            margin-bottom: 25px;
            text-align: center;
        }}
        .header h1 {{ font-size: 2.2em; margin-bottom: 10px; }}
        .header p {{ font-size: 1.1em; opacity: 0.9; }}
        .config-box {{
            background: rgba(255,255,255,0.08);
            padding: 20px;
            border-radius: 12px;
            margin-bottom: 25px;
            border-left: 4px solid #2ecc71;
        }}
        .config-box h3 {{ margin-bottom: 15px; color: #2ecc71; }}
        .config-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 15px; }}
        .config-item {{ background: rgba(255,255,255,0.05); padding: 15px; border-radius: 8px; }}
        .divisi-section {{
            background: rgba(255,255,255,0.03);
            border-radius: 20px;
            padding: 30px;
            margin-bottom: 25px;
        }}
        .divisi-section h2 {{ color: #667eea; margin-bottom: 20px; }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-bottom: 25px;
        }}
        .stat-card {{
            background: rgba(255,255,255,0.08);
            padding: 20px;
            border-radius: 12px;
            text-align: center;
        }}
        .stat-value {{ font-size: 2em; font-weight: bold; }}
        .stat-label {{ color: #a0a0a0; font-size: 0.9em; margin-top: 5px; }}
        .stat-card.highlight {{ border: 2px solid #e74c3c; }}
        .blocks-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(450px, 1fr));
            gap: 20px;
        }}
        .block-card {{
            background: rgba(255,255,255,0.05);
            padding: 15px;
            border-radius: 12px;
        }}
        .block-card img {{ width: 100%; border-radius: 8px; }}
        .legend {{
            background: rgba(255,255,255,0.05);
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 20px;
        }}
        .legend span {{
            display: inline-block;
            margin-right: 20px;
            padding: 5px 10px;
            border-radius: 5px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🅱️ Option B Dashboard - Cincin Api Analysis</h1>
            <p>Include YOUNG (Sisip) dengan Threshold Terpisah</p>
            <p style="margin-top: 10px; opacity: 0.7;">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
        </div>
        
        <div class="config-box">
            <h3>⚙️ Configuration</h3>
            <div class="config-grid">
                <div class="config-item">
                    <strong>Population:</strong><br>
                    Include: MATURE + YOUNG<br>
                    Exclude: DEAD, EMPTY
                </div>
                <div class="config-item">
                    <strong>AME II Threshold:</strong><br>
                    MATURE: Z &lt; {thresh_ame2['Z_Threshold_G3']}<br>
                    YOUNG: Z &lt; -2.0
                </div>
                <div class="config-item">
                    <strong>AME IV Threshold:</strong><br>
                    MATURE: Z &lt; {thresh_ame4['Z_Threshold_G3']}<br>
                    YOUNG: Z &lt; -2.0
                </div>
                <div class="config-item">
                    <strong>Cincin Api Trigger:</strong><br>
                    MERAH: G3 + ≥2 sick neighbors<br>
                    ORANYE: G3 isolated
                </div>
            </div>
        </div>
"""
    
    for divisi_code in ['AME002', 'AME004']:
        r = results[divisi_code]
        divisi_name = 'AME II' if divisi_code == 'AME002' else 'AME IV'
        
        html += f"""
        <div class="divisi-section">
            <h2>🌴 {divisi_name} ({divisi_code})</h2>
            
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-value">{r['total']:,}</div>
                    <div class="stat-label">Total Trees</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{r['mature']:,}</div>
                    <div class="stat-label">MATURE</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" style="color: #f39c12;">{r['young']:,}</div>
                    <div class="stat-label">YOUNG (Sisip)</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" style="color: #27ae60;">{r['g1']:,}</div>
                    <div class="stat-label">G1 (Sehat)</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" style="color: #f39c12;">{r['g2']:,}</div>
                    <div class="stat-label">G2 (Warning)</div>
                </div>
                <div class="stat-card highlight">
                    <div class="stat-value" style="color: #e74c3c;">{r['g3']:,}</div>
                    <div class="stat-label">G3 (Sick)</div>
                </div>
                <div class="stat-card highlight">
                    <div class="stat-value" style="color: #e74c3c;">{r['merah']:,}</div>
                    <div class="stat-label">🔥 CINCIN API</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" style="color: #f39c12;">{r['oranye']:,}</div>
                    <div class="stat-label">Isolated G3</div>
                </div>
            </div>
            
            <div class="config-box" style="border-color: #f39c12;">
                <h3 style="color: #f39c12;">📊 YOUNG (Sisip) Breakdown</h3>
                <p>Total YOUNG: <strong>{r['young']:,}</strong> | 
                   G3: <strong>{r['young_g3']}</strong> ({r['young_g3']/r['young']*100 if r['young'] > 0 else 0:.1f}%) | 
                   G2: <strong>{r['young_g2']}</strong> ({r['young_g2']/r['young']*100 if r['young'] > 0 else 0:.1f}%)
                </p>
            </div>
            
            <div class="config-box" style="border-color: #3498db;">
                <h3 style="color: #3498db;">🎯 Ground Truth Comparison</h3>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 15px; margin-top: 15px;">
                    <div class="stat-card">
                        <div class="stat-value" style="color: #e74c3c;">{r['mae']:.2f}%</div>
                        <div class="stat-label">MAE</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value" style="color: #3498db;">{r['corr']:.3f}</div>
                        <div class="stat-label">Correlation</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{r['avg_algo']:.2f}%</div>
                        <div class="stat-label">Algo Avg</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{r['avg_gt']:.2f}%</div>
                        <div class="stat-label">GT Avg</div>
                    </div>
                </div>
            </div>
            
            <h3 style="margin: 20px 0 15px;">🗺️ Top Blocks - Cincin Api Clustering</h3>
            <div class="legend">
                <span style="background: #27ae60; color: white;">● G1 Sehat</span>
                <span style="background: #f39c12; color: white;">● G2 Warning</span>
                <span style="background: #e74c3c; color: white;">● G3 Sick</span>
                <span style="border: 2px solid white;">○ Cincin Api</span>
                <span>● MATURE | ▲ YOUNG</span>
            </div>
            <div class="blocks-grid">
"""
        
        for bc in block_charts[divisi_code]:
            html += f"""
                <div class="block-card">
                    <img src="data:image/png;base64,{bc['chart']}" alt="{bc['blok']}">
                </div>
"""
        
        html += """
            </div>
        </div>
"""
    
    html += """
    </div>
</body>
</html>
"""
    
    html_path = output_dir / "option_b_dashboard.html"
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"\n[4/4] Dashboard saved: {html_path}")
    
    # Open dashboard
    import os
    os.startfile(html_path)
    
    return results


if __name__ == "__main__":
    main()
