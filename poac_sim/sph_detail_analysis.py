"""
SPH Detail Analysis
===================
Analisis SPH (Stand Per Hectare) detail per blok untuk AME II dan AME IV
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
from src.cost_control_loader import normalize_block

print("="*70)
print("SPH DETAIL ANALYSIS - Per Blok")
print("="*70)

output_dir = script_dir / "data" / "output" / "sph_detail"
output_dir.mkdir(parents=True, exist_ok=True)

# Load data
print("\n[1/4] Loading data...")
df_ame2 = load_and_clean_data(script_dir / "data/input/tabelNDREnew.csv")
df_ame4 = load_ame_iv_data(script_dir / "data/input/AME_IV.csv")

print("[2/4] Loading ground truth...")
df_gt = pd.read_excel(
    script_dir / "data/input/areal_inti_serangan_gano_AMEII_AMEIV.xlsx",
    sheet_name='Sheet1', header=[0, 1]
)
df_gt.columns = ['DIVISI', 'BLOK', 'TAHUN_TANAM', 'LUAS_SD_2024', 'PENAMBAHAN', 
                 'LUAS_SD_2025', 'TANAM', 'SISIP', 'SISIP_KENTOSAN', 'TOTAL_PKK',
                 'SPH', 'STADIUM_12', 'STADIUM_34', 'TOTAL_GANO', 'SERANGAN_PCT']

df_gt['blok_norm'] = df_gt['BLOK'].apply(normalize_block)

# Process both divisions
all_sph_data = []

for divisi_code, divisi_name, df_drone in [('AME002', 'AME II', df_ame2), ('AME004', 'AME IV', df_ame4)]:
    print(f"\n[3/4] Processing {divisi_name}...")
    
    df_gt_div = df_gt[df_gt['DIVISI'] == divisi_code]
    
    for blok in df_drone['Blok'].unique():
        df_blok = df_drone[df_drone['Blok'] == blok]
        blok_norm = normalize_block(blok)
        
        drone_total = len(df_blok)
        drone_mature = len(df_blok[df_blok['Category'] == 'MATURE'])
        drone_young = len(df_blok[df_blok['Category'] == 'YOUNG'])
        
        # Get GT data
        gt_row = df_gt_div[df_gt_div['blok_norm'] == blok_norm]
        
        if len(gt_row) > 0:
            gt = gt_row.iloc[0]
            gt_total = int(gt['TOTAL_PKK']) if pd.notna(gt['TOTAL_PKK']) else 0
            gt_sph = float(gt['SPH']) if pd.notna(gt['SPH']) else 0
            gt_luas = float(gt['LUAS_SD_2025']) if pd.notna(gt['LUAS_SD_2025']) else 0
            tahun_tanam = int(gt['TAHUN_TANAM']) if pd.notna(gt['TAHUN_TANAM']) else 0
        else:
            gt_total = 0
            gt_sph = 0
            gt_luas = 0
            tahun_tanam = 0
        
        # Calculate SPH Drone
        sph_drone = drone_total / gt_luas if gt_luas > 0 else 0
        
        # Variance
        sph_variance = sph_drone - gt_sph
        sph_variance_abs = abs(sph_variance)
        sph_variance_pct = sph_variance_abs / gt_sph * 100 if gt_sph > 0 else 0
        
        # Status
        if sph_variance_pct <= 5:
            status = "MATCH"
        elif sph_variance_pct <= 15:
            status = "MODERATE"
        else:
            status = "HIGH_VARIANCE"
        
        # Direction
        if sph_variance > 0:
            direction = "DRONE > GT"
        elif sph_variance < 0:
            direction = "DRONE < GT"
        else:
            direction = "EQUAL"
        
        all_sph_data.append({
            'divisi': divisi_code,
            'divisi_name': divisi_name,
            'blok': blok,
            'tahun_tanam': tahun_tanam,
            'luas_ha': gt_luas,
            'drone_total': drone_total,
            'drone_mature': drone_mature,
            'drone_young': drone_young,
            'gt_total': gt_total,
            'sph_drone': round(sph_drone, 1),
            'sph_gt': round(gt_sph, 1),
            'sph_variance': round(sph_variance, 1),
            'sph_variance_pct': round(sph_variance_pct, 1),
            'status': status,
            'direction': direction
        })

df_sph = pd.DataFrame(all_sph_data)

# Save to CSV
df_sph.to_csv(output_dir / "sph_detail_all.csv", index=False)

# Separate by division
df_sph_ame2 = df_sph[df_sph['divisi'] == 'AME002'].sort_values('sph_variance_pct', ascending=False)
df_sph_ame4 = df_sph[df_sph['divisi'] == 'AME004'].sort_values('sph_variance_pct', ascending=False)

df_sph_ame2.to_csv(output_dir / "sph_detail_ame2.csv", index=False)
df_sph_ame4.to_csv(output_dir / "sph_detail_ame4.csv", index=False)

# Generate bar chart comparison
def generate_sph_bar_chart(df_div: pd.DataFrame, divisi_name: str, n_top: int = 20) -> str:
    """Generate bar chart comparing SPH Drone vs GT."""
    df_top = df_div.head(n_top).copy()
    
    fig, ax = plt.subplots(figsize=(14, 8))
    plt.style.use('dark_background')
    
    x = np.arange(len(df_top))
    width = 0.35
    
    bars1 = ax.bar(x - width/2, df_top['sph_drone'], width, label='SPH Drone', color='#3498db', alpha=0.8)
    bars2 = ax.bar(x + width/2, df_top['sph_gt'], width, label='SPH Ground Truth', color='#e74c3c', alpha=0.8)
    
    ax.set_xlabel('Blok', fontsize=12)
    ax.set_ylabel('SPH (Stand Per Hectare)', fontsize=12)
    ax.set_title(f'{divisi_name} - Top {n_top} Blok dengan SPH Variance Tertinggi', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(df_top['blok'], rotation=45, ha='right', fontsize=9)
    ax.legend()
    ax.grid(True, alpha=0.2, axis='y')
    
    plt.tight_layout()
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight', facecolor='#1a1a2e')
    buf.seek(0)
    img = base64.b64encode(buf.read()).decode('utf-8')
    plt.close()
    return img

print("[4/4] Generating charts and HTML...")

chart_ame2 = generate_sph_bar_chart(df_sph_ame2, 'AME II')
chart_ame4 = generate_sph_bar_chart(df_sph_ame4, 'AME IV')

# Summary stats
def get_summary(df):
    return {
        'total_blocks': len(df),
        'avg_sph_drone': df['sph_drone'].mean(),
        'avg_sph_gt': df['sph_gt'].mean(),
        'avg_variance': df['sph_variance'].mean(),
        'avg_variance_pct': df['sph_variance_pct'].mean(),
        'match_count': len(df[df['status'] == 'MATCH']),
        'moderate_count': len(df[df['status'] == 'MODERATE']),
        'high_count': len(df[df['status'] == 'HIGH_VARIANCE']),
        'drone_higher': len(df[df['direction'] == 'DRONE > GT']),
        'drone_lower': len(df[df['direction'] == 'DRONE < GT'])
    }

summary_ame2 = get_summary(df_sph_ame2)
summary_ame4 = get_summary(df_sph_ame4)

# Generate HTML
html = f"""<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SPH Detail Analysis</title>
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
            background: linear-gradient(135deg, #3498db 0%, #2980b9 100%);
            padding: 30px;
            border-radius: 20px;
            margin-bottom: 25px;
            text-align: center;
        }}
        .header h1 {{ font-size: 2em; margin-bottom: 5px; }}
        
        .section {{
            background: rgba(255,255,255,0.03);
            border-radius: 20px;
            padding: 25px;
            margin-bottom: 25px;
            border: 1px solid rgba(255,255,255,0.05);
        }}
        .section h2 {{ color: #3498db; margin-bottom: 20px; }}
        
        .grid-2 {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; }}
        .grid-4 {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; }}
        
        .kpi-card {{
            background: rgba(255,255,255,0.08);
            padding: 20px;
            border-radius: 12px;
            text-align: center;
        }}
        .kpi-value {{ font-size: 1.8em; font-weight: bold; }}
        .kpi-label {{ color: #a0a0a0; font-size: 0.85em; margin-top: 5px; }}
        
        .chart-card {{ background: rgba(255,255,255,0.05); padding: 15px; border-radius: 12px; margin-bottom: 20px; }}
        .chart-card img {{ width: 100%; border-radius: 8px; }}
        
        table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
        th, td {{ padding: 10px 8px; text-align: center; border-bottom: 1px solid rgba(255,255,255,0.1); font-size: 0.9em; }}
        th {{ background: rgba(52,152,219,0.2); position: sticky; top: 0; }}
        tr:hover {{ background: rgba(255,255,255,0.05); }}
        
        .scrollable {{ max-height: 500px; overflow-y: auto; }}
        
        .status-match {{ color: #27ae60; }}
        .status-moderate {{ color: #f39c12; }}
        .status-high {{ color: #e74c3c; font-weight: bold; }}
        
        .metric-desc {{ font-size: 0.85em; color: #a0a0a0; margin-top: 15px; padding: 15px; background: rgba(255,255,255,0.03); border-radius: 8px; line-height: 1.6; }}
        
        @media (max-width: 1200px) {{
            .grid-2, .grid-4 {{ grid-template-columns: 1fr; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 SPH Detail Analysis</h1>
            <p>Stand Per Hectare - Drone vs Ground Truth | Per Blok</p>
            <p style="margin-top: 10px; opacity: 0.7;">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
        </div>
        
        <div class="metric-desc" style="border-left: 4px solid #3498db; margin-bottom: 25px;">
            <strong>SPH (Stand Per Hectare):</strong> Jumlah pohon per hektar lahan. Metrik ini penting untuk:
            <ul style="margin-left: 20px; margin-top: 10px;">
                <li>Validasi akurasi data drone vs ground truth</li>
                <li>Identifikasi blok dengan data anomali</li>
                <li>Evaluasi kualitas pengambilan data drone</li>
            </ul>
            <br>
            <strong>Kategori Variance:</strong><br>
            <span style="color: #27ae60;">● MATCH</span> - Variance ≤5% (data konsisten)<br>
            <span style="color: #f39c12;">● MODERATE</span> - Variance 5-15% (perlu review)<br>
            <span style="color: #e74c3c;">● HIGH_VARIANCE</span> - Variance >15% (perlu investigasi)
        </div>
"""

# AME II Section
html += f"""
        <div class="section">
            <h2>🌴 AME II (AME002)</h2>
            
            <div class="grid-4">
                <div class="kpi-card">
                    <div class="kpi-value">{summary_ame2['total_blocks']}</div>
                    <div class="kpi-label">Total Blok</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-value">{summary_ame2['avg_sph_drone']:.0f}</div>
                    <div class="kpi-label">Avg SPH Drone</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-value">{summary_ame2['avg_sph_gt']:.0f}</div>
                    <div class="kpi-label">Avg SPH GT</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-value" style="color: {'#27ae60' if summary_ame2['avg_variance_pct'] < 10 else '#f39c12' if summary_ame2['avg_variance_pct'] < 20 else '#e74c3c'};">{summary_ame2['avg_variance_pct']:.1f}%</div>
                    <div class="kpi-label">Avg Variance</div>
                </div>
            </div>
            
            <div class="grid-4" style="margin-top: 15px;">
                <div class="kpi-card">
                    <div class="kpi-value status-match">{summary_ame2['match_count']}</div>
                    <div class="kpi-label">MATCH (≤5%)</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-value status-moderate">{summary_ame2['moderate_count']}</div>
                    <div class="kpi-label">MODERATE (5-15%)</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-value status-high">{summary_ame2['high_count']}</div>
                    <div class="kpi-label">HIGH (>15%)</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-value">{summary_ame2['drone_higher']} / {summary_ame2['drone_lower']}</div>
                    <div class="kpi-label">Drone > GT / < GT</div>
                </div>
            </div>
            
            <div class="chart-card" style="margin-top: 20px;">
                <img src="data:image/png;base64,{chart_ame2}" alt="AME II SPH Chart">
            </div>
            
            <h3 style="margin: 20px 0 15px; color: #a0a0a0;">📋 Detail Per Blok (sorted by variance)</h3>
            <div class="scrollable">
            <table>
                <thead>
                    <tr>
                        <th>Blok</th>
                        <th>Tahun Tanam</th>
                        <th>Luas (Ha)</th>
                        <th>Drone Total</th>
                        <th>GT Total</th>
                        <th>SPH Drone</th>
                        <th>SPH GT</th>
                        <th>Variance</th>
                        <th>Variance %</th>
                        <th>Status</th>
                        <th>Direction</th>
                    </tr>
                </thead>
                <tbody>
"""

for _, row in df_sph_ame2.iterrows():
    status_class = 'status-match' if row['status'] == 'MATCH' else 'status-moderate' if row['status'] == 'MODERATE' else 'status-high'
    html += f"""
                    <tr>
                        <td>{row['blok']}</td>
                        <td>{row['tahun_tanam']}</td>
                        <td>{row['luas_ha']:.2f}</td>
                        <td>{row['drone_total']:,}</td>
                        <td>{row['gt_total']:,}</td>
                        <td>{row['sph_drone']:.0f}</td>
                        <td>{row['sph_gt']:.0f}</td>
                        <td>{row['sph_variance']:+.0f}</td>
                        <td class="{status_class}">{row['sph_variance_pct']:.1f}%</td>
                        <td class="{status_class}">{row['status']}</td>
                        <td>{row['direction']}</td>
                    </tr>
"""

html += """
                </tbody>
            </table>
            </div>
        </div>
"""

# AME IV Section
html += f"""
        <div class="section">
            <h2>🌴 AME IV (AME004)</h2>
            
            <div class="grid-4">
                <div class="kpi-card">
                    <div class="kpi-value">{summary_ame4['total_blocks']}</div>
                    <div class="kpi-label">Total Blok</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-value">{summary_ame4['avg_sph_drone']:.0f}</div>
                    <div class="kpi-label">Avg SPH Drone</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-value">{summary_ame4['avg_sph_gt']:.0f}</div>
                    <div class="kpi-label">Avg SPH GT</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-value" style="color: {'#27ae60' if summary_ame4['avg_variance_pct'] < 10 else '#f39c12' if summary_ame4['avg_variance_pct'] < 20 else '#e74c3c'};">{summary_ame4['avg_variance_pct']:.1f}%</div>
                    <div class="kpi-label">Avg Variance</div>
                </div>
            </div>
            
            <div class="grid-4" style="margin-top: 15px;">
                <div class="kpi-card">
                    <div class="kpi-value status-match">{summary_ame4['match_count']}</div>
                    <div class="kpi-label">MATCH (≤5%)</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-value status-moderate">{summary_ame4['moderate_count']}</div>
                    <div class="kpi-label">MODERATE (5-15%)</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-value status-high">{summary_ame4['high_count']}</div>
                    <div class="kpi-label">HIGH (>15%)</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-value">{summary_ame4['drone_higher']} / {summary_ame4['drone_lower']}</div>
                    <div class="kpi-label">Drone > GT / < GT</div>
                </div>
            </div>
            
            <div class="chart-card" style="margin-top: 20px;">
                <img src="data:image/png;base64,{chart_ame4}" alt="AME IV SPH Chart">
            </div>
            
            <h3 style="margin: 20px 0 15px; color: #a0a0a0;">📋 Detail Per Blok (sorted by variance)</h3>
            <div class="scrollable">
            <table>
                <thead>
                    <tr>
                        <th>Blok</th>
                        <th>Tahun Tanam</th>
                        <th>Luas (Ha)</th>
                        <th>Drone Total</th>
                        <th>GT Total</th>
                        <th>SPH Drone</th>
                        <th>SPH GT</th>
                        <th>Variance</th>
                        <th>Variance %</th>
                        <th>Status</th>
                        <th>Direction</th>
                    </tr>
                </thead>
                <tbody>
"""

for _, row in df_sph_ame4.iterrows():
    status_class = 'status-match' if row['status'] == 'MATCH' else 'status-moderate' if row['status'] == 'MODERATE' else 'status-high'
    html += f"""
                    <tr>
                        <td>{row['blok']}</td>
                        <td>{row['tahun_tanam']}</td>
                        <td>{row['luas_ha']:.2f}</td>
                        <td>{row['drone_total']:,}</td>
                        <td>{row['gt_total']:,}</td>
                        <td>{row['sph_drone']:.0f}</td>
                        <td>{row['sph_gt']:.0f}</td>
                        <td>{row['sph_variance']:+.0f}</td>
                        <td class="{status_class}">{row['sph_variance_pct']:.1f}%</td>
                        <td class="{status_class}">{row['status']}</td>
                        <td>{row['direction']}</td>
                    </tr>
"""

html += """
                </tbody>
            </table>
            </div>
        </div>
        
        <div style="text-align: center; padding: 20px; color: #666; font-size: 0.9em;">
            <p>SPH Detail Analysis | Data Sources: Drone NDRE + Ground Truth Census</p>
        </div>
    </div>
</body>
</html>
"""

html_path = output_dir / "sph_detail_analysis.html"
with open(html_path, 'w', encoding='utf-8') as f:
    f.write(html)

print(f"\n✅ Output saved:")
print(f"   - {html_path}")
print(f"   - {output_dir / 'sph_detail_all.csv'}")
print(f"   - {output_dir / 'sph_detail_ame2.csv'}")
print(f"   - {output_dir / 'sph_detail_ame4.csv'}")

# Print summary
print("\n" + "="*70)
print("SUMMARY")
print("="*70)
print(f"\nAME II:")
print(f"  Avg SPH Drone: {summary_ame2['avg_sph_drone']:.0f}")
print(f"  Avg SPH GT: {summary_ame2['avg_sph_gt']:.0f}")
print(f"  Avg Variance: {summary_ame2['avg_variance_pct']:.1f}%")
print(f"  MATCH: {summary_ame2['match_count']}, MODERATE: {summary_ame2['moderate_count']}, HIGH: {summary_ame2['high_count']}")

print(f"\nAME IV:")
print(f"  Avg SPH Drone: {summary_ame4['avg_sph_drone']:.0f}")
print(f"  Avg SPH GT: {summary_ame4['avg_sph_gt']:.0f}")
print(f"  Avg Variance: {summary_ame4['avg_variance_pct']:.1f}%")
print(f"  MATCH: {summary_ame4['match_count']}, MODERATE: {summary_ame4['moderate_count']}, HIGH: {summary_ame4['high_count']}")

# Open dashboard
import os
os.startfile(html_path)
