"""
Generate Final Calibrated Dashboard with All Results
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


def generate_final_dashboard():
    """Generate comprehensive final dashboard."""
    
    output_dir = script_dir / "data" / "output" / "final_dashboard"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load all data
    print("Loading data...")
    
    # Calibration data
    df_cal_ame2 = pd.read_csv(script_dir / "data/output/z_score_calibration/AME002_calibration.csv")
    df_cal_ame4 = pd.read_csv(script_dir / "data/output/z_score_calibration/AME004_calibration.csv")
    
    # Population data
    df_ame2 = load_and_clean_data(script_dir / "data/input/tabelNDREnew.csv")
    df_ame4 = load_ame_iv_data(script_dir / "data/input/AME_IV.csv")
    
    # Ground truth
    df_gt = pd.read_excel(
        script_dir / "data/input/areal_inti_serangan_gano_AMEII_AMEIV.xlsx",
        sheet_name='Sheet1', header=[0, 1]
    )
    df_gt.columns = ['DIVISI', 'BLOK', 'TAHUN_TANAM', 'LUAS_SD_2024', 'PENAMBAHAN', 
                     'LUAS_SD_2025', 'TANAM', 'SISIP', 'SISIP_KENTOSAN', 'TOTAL_PKK',
                     'SPH', 'STADIUM_12', 'STADIUM_34', 'TOTAL_GANO', 'SERANGAN_PCT']
    
    # Generate charts
    print("Generating charts...")
    charts = {}
    plt.style.use('dark_background')
    
    # Chart 1: Calibration curves
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    # AME II
    ax1 = axes[0]
    ax1.plot(df_cal_ame2['z_threshold'], df_cal_ame2['mae'], 'o-', color='#e74c3c', linewidth=2, markersize=8, label='MAE')
    ax1.axvline(x=-1.5, color='#2ecc71', linestyle='--', linewidth=2, label='Optimal (-1.5)')
    ax1.set_xlabel('Z-Score Threshold')
    ax1.set_ylabel('MAE (%)')
    ax1.set_title('AME II Calibration')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # AME IV
    ax2 = axes[1]
    ax2.plot(df_cal_ame4['z_threshold'], df_cal_ame4['mae'], 'o-', color='#e74c3c', linewidth=2, markersize=8, label='MAE')
    ax2.axvline(x=-4.0, color='#2ecc71', linestyle='--', linewidth=2, label='Optimal (-4.0)')
    ax2.set_xlabel('Z-Score Threshold')
    ax2.set_ylabel('MAE (%)')
    ax2.set_title('AME IV Calibration')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=120, bbox_inches='tight', facecolor='#1a1a2e')
    buf.seek(0)
    charts['calibration'] = base64.b64encode(buf.read()).decode('utf-8')
    plt.close()
    
    # Chart 2: Population composition
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    
    categories = ['MATURE', 'YOUNG', 'DEAD', 'EMPTY']
    colors = ['#27ae60', '#f39c12', '#e74c3c', '#7f8c8d']
    
    # AME II
    counts_ame2 = [len(df_ame2[df_ame2['Category'] == c]) for c in categories]
    axes[0].pie(counts_ame2, labels=categories, autopct='%1.1f%%', colors=colors, 
                explode=[0.02]*4, shadow=True)
    axes[0].set_title(f'AME II Population\n({sum(counts_ame2):,} total)')
    
    # AME IV
    counts_ame4 = [len(df_ame4[df_ame4['Category'] == c]) for c in categories]
    axes[1].pie(counts_ame4, labels=categories, autopct='%1.1f%%', colors=colors,
                explode=[0.02]*4, shadow=True)
    axes[1].set_title(f'AME IV Population\n({sum(counts_ame4):,} total)')
    
    plt.tight_layout()
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=120, bbox_inches='tight', facecolor='#1a1a2e')
    buf.seek(0)
    charts['population'] = base64.b64encode(buf.read()).decode('utf-8')
    plt.close()
    
    # Chart 3: Ground truth comparison
    fig, ax = plt.subplots(figsize=(10, 6))
    
    gt_ame2 = df_gt[df_gt['DIVISI'] == 'AME002']
    gt_ame4 = df_gt[df_gt['DIVISI'] == 'AME004']
    
    labels = ['AME II', 'AME IV']
    gt_pct = [
        gt_ame2['TOTAL_GANO'].sum() / gt_ame2['TOTAL_PKK'].sum() * 100,
        gt_ame4['TOTAL_GANO'].sum() / gt_ame4['TOTAL_PKK'].sum() * 100
    ]
    algo_pct = [7.00, 1.79]  # From calibrated results
    
    x = np.arange(len(labels))
    width = 0.35
    
    bars1 = ax.bar(x - width/2, gt_pct, width, label='Ground Truth', color='#f39c12', alpha=0.8)
    bars2 = ax.bar(x + width/2, algo_pct, width, label='Calibrated Algo', color='#27ae60', alpha=0.8)
    
    ax.set_ylabel('Detection Rate (%)')
    ax.set_title('Ground Truth vs Calibrated Algorithm')
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')
    
    # Add value labels
    for bar, val in zip(bars1, gt_pct):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.2, f'{val:.1f}%', 
                ha='center', fontweight='bold')
    for bar, val in zip(bars2, algo_pct):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.2, f'{val:.1f}%', 
                ha='center', fontweight='bold')
    
    plt.tight_layout()
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=120, bbox_inches='tight', facecolor='#1a1a2e')
    buf.seek(0)
    charts['comparison'] = base64.b64encode(buf.read()).decode('utf-8')
    plt.close()
    
    # Generate HTML
    print("Generating HTML dashboard...")
    
    html = f"""<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cincin Api - Calibrated Analysis Dashboard</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: 'Segoe UI', Tahoma, sans-serif; 
            background: linear-gradient(135deg, #0f0f23 0%, #1a1a2e 50%, #16213e 100%);
            color: #e0e0e0; 
            min-height: 100vh;
        }}
        .container {{ max-width: 1600px; margin: 0 auto; padding: 20px; }}
        
        .header {{ 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 40px;
            border-radius: 20px;
            margin-bottom: 30px;
            text-align: center;
            box-shadow: 0 10px 40px rgba(102, 126, 234, 0.3);
        }}
        .header h1 {{ font-size: 2.5em; margin-bottom: 10px; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }}
        .header p {{ font-size: 1.2em; opacity: 0.9; }}
        
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .summary-card {{
            background: rgba(255,255,255,0.05);
            border-radius: 15px;
            padding: 25px;
            border: 1px solid rgba(255,255,255,0.1);
            transition: transform 0.3s, box-shadow 0.3s;
        }}
        .summary-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        }}
        .summary-card h3 {{ 
            color: #667eea; 
            margin-bottom: 15px;
            font-size: 1.3em;
        }}
        .summary-card .value {{
            font-size: 2.5em;
            font-weight: bold;
            margin: 10px 0;
        }}
        .summary-card .label {{ color: #a0a0a0; }}
        
        .threshold-box {{
            background: linear-gradient(135deg, #27ae60 0%, #2ecc71 100%);
            color: white;
            padding: 20px;
            border-radius: 12px;
            margin: 15px 0;
            text-align: center;
        }}
        .threshold-box .threshold-value {{
            font-size: 2em;
            font-weight: bold;
        }}
        
        .section {{
            background: rgba(255,255,255,0.03);
            border-radius: 20px;
            padding: 30px;
            margin-bottom: 30px;
            border: 1px solid rgba(255,255,255,0.05);
        }}
        .section h2 {{
            color: #667eea;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid rgba(102, 126, 234, 0.3);
        }}
        
        .charts-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
            gap: 20px;
        }}
        .chart-card {{
            background: rgba(255,255,255,0.03);
            border-radius: 15px;
            padding: 20px;
        }}
        .chart-card img {{ width: 100%; border-radius: 10px; }}
        .chart-card h4 {{ margin-bottom: 15px; color: #a0a0a0; }}
        
        .findings-list {{
            list-style: none;
            padding: 0;
        }}
        .findings-list li {{
            padding: 15px 20px;
            margin: 10px 0;
            background: rgba(255,255,255,0.05);
            border-radius: 10px;
            border-left: 4px solid #667eea;
        }}
        .findings-list li strong {{ color: #667eea; }}
        
        .comparison-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        .comparison-table th, .comparison-table td {{
            padding: 15px;
            text-align: center;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }}
        .comparison-table th {{ background: rgba(102, 126, 234, 0.2); }}
        .comparison-table tr:hover {{ background: rgba(255,255,255,0.05); }}
        
        .badge {{
            display: inline-block;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: bold;
        }}
        .badge-success {{ background: #27ae60; color: white; }}
        .badge-warning {{ background: #f39c12; color: white; }}
        
        .footer {{
            text-align: center;
            padding: 20px;
            color: #666;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔬 Cincin Api - Calibrated Analysis</h1>
            <p>Z-Score Threshold Calibration Based on Census Ground Truth</p>
            <p style="margin-top: 15px; font-size: 0.9em; opacity: 0.7;">
                Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}
            </p>
        </div>
        
        <!-- Summary Cards -->
        <div class="summary-grid">
            <div class="summary-card">
                <h3>🌴 AME II (AME002)</h3>
                <div class="threshold-box">
                    <div class="threshold-value">Z &lt; -1.5</div>
                    <div>Calibrated Threshold</div>
                </div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-top: 15px;">
                    <div>
                        <div class="value" style="font-size: 1.8em; color: #2ecc71;">2.93%</div>
                        <div class="label">MAE</div>
                    </div>
                    <div>
                        <div class="value" style="font-size: 1.8em; color: #3498db;">0.360</div>
                        <div class="label">Correlation</div>
                    </div>
                </div>
                <p style="margin-top: 15px; color: #a0a0a0; font-size: 0.9em;">
                    Detection: 7.0% vs GT 6.3%
                </p>
            </div>
            
            <div class="summary-card">
                <h3>🌴 AME IV (AME004)</h3>
                <div class="threshold-box">
                    <div class="threshold-value">Z &lt; -4.0</div>
                    <div>Calibrated Threshold</div>
                </div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-top: 15px;">
                    <div>
                        <div class="value" style="font-size: 1.8em; color: #2ecc71;">2.25%</div>
                        <div class="label">MAE</div>
                    </div>
                    <div>
                        <div class="value" style="font-size: 1.8em; color: #3498db;">0.369</div>
                        <div class="label">Correlation</div>
                    </div>
                </div>
                <p style="margin-top: 15px; color: #a0a0a0; font-size: 0.9em;">
                    Detection: 1.8% vs GT 3.8% | <span class="badge badge-success">+11.9% improvement</span>
                </p>
            </div>
            
            <div class="summary-card">
                <h3>📊 Ground Truth</h3>
                <div style="margin-top: 20px;">
                    <div style="display: flex; justify-content: space-between; margin: 10px 0;">
                        <span>AME II Ganoderma:</span>
                        <span style="font-weight: bold; color: #e74c3c;">6.28%</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; margin: 10px 0;">
                        <span>AME IV Ganoderma:</span>
                        <span style="font-weight: bold; color: #e74c3c;">3.84%</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; margin: 10px 0;">
                        <span>Total Blok:</span>
                        <span style="font-weight: bold;">112</span>
                    </div>
                </div>
            </div>
            
            <div class="summary-card">
                <h3>🎯 Key Insight</h3>
                <p style="line-height: 1.8; margin-top: 15px;">
                    <strong>One-size-fits-all tidak bekerja!</strong><br><br>
                    AME II butuh threshold <span style="color: #2ecc71;">lebih sensitif (-1.5)</span> karena tingkat serangan tinggi.<br><br>
                    AME IV butuh threshold <span style="color: #e74c3c;">lebih ketat (-4.0)</span> karena kebun lebih muda dengan tingkat serangan rendah.
                </p>
            </div>
        </div>
        
        <!-- Calibration Charts -->
        <div class="section">
            <h2>📈 Threshold Calibration Curves</h2>
            <div class="chart-card">
                <img src="data:image/png;base64,{charts['calibration']}" alt="Calibration">
            </div>
        </div>
        
        <!-- Population & Comparison -->
        <div class="charts-grid">
            <div class="section">
                <h2>👥 Population Segmentation</h2>
                <div class="chart-card">
                    <img src="data:image/png;base64,{charts['population']}" alt="Population">
                </div>
                <p style="margin-top: 15px; color: #a0a0a0;">
                    Hanya <strong>MATURE</strong> yang digunakan untuk baseline Z-Score.
                    YOUNG (Sisip) dikecualikan karena NDRE rendah.
                </p>
            </div>
            
            <div class="section">
                <h2>🎯 Detection Rate Comparison</h2>
                <div class="chart-card">
                    <img src="data:image/png;base64,{charts['comparison']}" alt="Comparison">
                </div>
            </div>
        </div>
        
        <!-- Threshold Comparison Table -->
        <div class="section">
            <h2>📋 Standard vs Calibrated Threshold</h2>
            <table class="comparison-table">
                <thead>
                    <tr>
                        <th>Divisi</th>
                        <th>Standard (Z &lt; -2.0)</th>
                        <th>Calibrated</th>
                        <th>MAE Improvement</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td><strong>AME II</strong></td>
                        <td>MAE: 3.50%</td>
                        <td>Z &lt; -1.5 → MAE: 2.93%</td>
                        <td style="color: #2ecc71;">+0.57%</td>
                        <td><span class="badge badge-success">✓ Optimal</span></td>
                    </tr>
                    <tr>
                        <td><strong>AME IV</strong></td>
                        <td>MAE: 14.18%</td>
                        <td>Z &lt; -4.0 → MAE: 2.25%</td>
                        <td style="color: #2ecc71;">+11.93%</td>
                        <td><span class="badge badge-success">✓ Significant</span></td>
                    </tr>
                </tbody>
            </table>
        </div>
        
        <!-- Key Findings -->
        <div class="section">
            <h2>💡 Key Findings</h2>
            <ul class="findings-list">
                <li>
                    <strong>AME II (Z &lt; -1.5):</strong> Lebih sensitif karena tingkat serangan tinggi (6.28%). 
                    Detection rate 7.0% mendekati ground truth.
                </li>
                <li>
                    <strong>AME IV (Z &lt; -4.0):</strong> Butuh threshold ketat karena tingkat serangan rendah (3.84%) 
                    dan data lebih homogen. Improvement MAE +11.93%.
                </li>
                <li>
                    <strong>Population Segmentation:</strong> AME IV memiliki 10.8% EMPTY (lokasi tanpa pohon) 
                    yang menunjukkan data quality issue.
                </li>
                <li>
                    <strong>Rekomendasi:</strong> Gunakan threshold terkalibrasi per divisi, bukan threshold tunggal.
                </li>
            </ul>
        </div>
        
        <div class="footer">
            <p>🌴 POAC Simulation Engine | Cincin Api Algorithm | Population Segmentation Analysis</p>
        </div>
    </div>
</body>
</html>
"""
    
    # Save HTML
    html_path = output_dir / "calibrated_dashboard.html"
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"Dashboard saved: {html_path}")
    return html_path


if __name__ == "__main__":
    dashboard_path = generate_final_dashboard()
    print(f"\nOpening dashboard...")
    import os
    os.startfile(dashboard_path)
