"""
Dashboard Cincin Api Z-Score v2.0 dengan Config UI
===================================================
HTML Dashboard dengan:
- Z-Score Spatial Filter detection
- 3 Status: MERAH (Kluster), ORANYE (Indikasi), HIJAU (Sehat)
- UI Input untuk konfigurasi threshold
"""
import sys
sys.path.insert(0, 'src')

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import json
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

from src.ingestion import load_and_clean_data
from src.zscore_detection import run_zscore_detection, calculate_block_statistics, calculate_zscore
from config import ZSCORE_PRESETS, ZSCORE_STATUS_LABELS

# Output
timestamp = datetime.now().strftime("%Y%m%d_%H%M")
output_dir = Path(f'data/output/cincin_api_zscore_{timestamp}')
output_dir.mkdir(parents=True, exist_ok=True)

def run_zscore_with_config(df, z_threshold_core=-1.5, z_threshold_neighbor=-0.5, min_neighbors=1):
    """Run Z-Score detection with custom config."""
    
    # Step 1: Block statistics
    block_stats = calculate_block_statistics(df, 'NDRE125')
    
    # Step 2: Calculate Z-Score
    df = df.merge(block_stats[['Blok', 'Mean_NDRE', 'SD_NDRE']], on='Blok', how='left')
    df['Z_Score'] = (df['NDRE125'] - df['Mean_NDRE']) / df['SD_NDRE']
    df['Z_Score'] = df['Z_Score'].fillna(0)
    
    # Step 3: Identify core suspects
    df['is_core_suspect'] = df['Z_Score'] < z_threshold_core
    
    # Step 4: Count stressed neighbors
    stressed_neighbors = []
    for idx, row in df.iterrows():
        if not row['is_core_suspect']:
            stressed_neighbors.append(0)
            continue
        
        blok = row['Blok']
        baris = int(row['N_BARIS'])
        pokok = int(row['N_POKOK'])
        
        neighbors = df[
            (df['Blok'] == blok) &
            (df['N_BARIS'].between(baris - 1, baris + 1)) &
            (df['N_POKOK'].between(pokok - 1, pokok + 1)) &
            (df.index != idx)
        ]
        
        stressed = len(neighbors[neighbors['Z_Score'] < z_threshold_neighbor])
        stressed_neighbors.append(stressed)
    
    df['Tetangga_Stres'] = stressed_neighbors
    
    # Step 5: Classify - MERAH/ORANYE/HIJAU
    def classify(row):
        if not row['is_core_suspect']:
            return 'HIJAU'
        if row['Tetangga_Stres'] >= min_neighbors:
            return 'MERAH'
        elif row['Tetangga_Stres'] >= 1:
            return 'ORANYE'
        else:
            return 'HIJAU'
    
    df['Status_Risiko'] = df.apply(classify, axis=1)
    
    return df

def generate_zscore_dashboard(df, config, output_dir):
    """Generate HTML dashboard with Z-Score detection and config UI."""
    
    # Stats
    total = len(df)
    merah = len(df[df['Status_Risiko'] == 'MERAH'])
    oranye = len(df[df['Status_Risiko'] == 'ORANYE'])
    hijau = len(df[df['Status_Risiko'] == 'HIJAU'])
    
    # Block summary
    block_summary = df.groupby('Blok')['Status_Risiko'].apply(
        lambda x: pd.Series({
            'MERAH': (x == 'MERAH').sum(),
            'ORANYE': (x == 'ORANYE').sum(),
            'HIJAU': (x == 'HIJAU').sum(),
            'Total': len(x)
        })
    ).unstack()
    block_summary['Pct_Risiko'] = ((block_summary['MERAH'] + block_summary['ORANYE']) / block_summary['Total'] * 100).round(1)
    block_summary = block_summary.sort_values('Pct_Risiko', ascending=False)
    
    # Top 10 blocks
    top_10_blocks = block_summary.head(10)
    
    # Generate table rows
    rows_html = ""
    for i, (blok, row) in enumerate(top_10_blocks.iterrows()):
        rows_html += f"""
        <tr>
            <td>{i+1}</td>
            <td><strong>{blok}</strong></td>
            <td class="merah">{int(row['MERAH'])}</td>
            <td class="oranye">{int(row['ORANYE'])}</td>
            <td class="hijau">{int(row['HIJAU'])}</td>
            <td><strong>{row['Pct_Risiko']:.1f}%</strong></td>
        </tr>
        """
    
    # Preset options
    preset_options = ""
    for name, preset in ZSCORE_PRESETS.items():
        preset_options += f'<option value="{name}">{name.capitalize()} (Z={preset["z_threshold_core"]})</option>\n'
    
    html = f"""
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🔥 Dashboard Cincin Api - Z-Score v2.0</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', Tahoma, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            color: #fff;
            padding: 20px;
        }}
        .header {{
            text-align: center;
            padding: 30px;
            background: rgba(255,255,255,0.05);
            border-radius: 15px;
            margin-bottom: 30px;
        }}
        .header h1 {{
            font-size: 2.5rem;
            margin-bottom: 10px;
            background: linear-gradient(45deg, #ff6b6b, #ffa500, #00ff88);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .config-panel {{
            background: rgba(255,255,255,0.08);
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 30px;
            border: 2px solid rgba(255,107,107,0.3);
        }}
        .config-panel h3 {{
            color: #ff6b6b;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .config-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
        }}
        .config-item {{
            background: rgba(0,0,0,0.2);
            padding: 15px;
            border-radius: 10px;
        }}
        .config-item label {{
            display: block;
            color: #aaa;
            margin-bottom: 8px;
            font-size: 0.9rem;
        }}
        .config-item input, .config-item select {{
            width: 100%;
            padding: 10px;
            border: none;
            border-radius: 8px;
            background: rgba(255,255,255,0.1);
            color: #fff;
            font-size: 1rem;
        }}
        .config-item input:focus, .config-item select:focus {{
            outline: 2px solid #ff6b6b;
        }}
        .btn-apply {{
            background: linear-gradient(45deg, #ff6b6b, #ee5a24);
            color: white;
            border: none;
            padding: 15px 30px;
            border-radius: 10px;
            font-size: 1rem;
            cursor: pointer;
            margin-top: 20px;
            transition: transform 0.2s;
        }}
        .btn-apply:hover {{ transform: scale(1.05); }}
        .current-config {{
            background: rgba(255,107,107,0.1);
            padding: 15px;
            border-radius: 10px;
            margin-top: 15px;
            font-family: monospace;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 20px;
            margin-bottom: 30px;
        }}
        .stat-card {{
            background: rgba(255,255,255,0.08);
            padding: 25px;
            border-radius: 15px;
            text-align: center;
        }}
        .stat-card.merah {{ border-left: 4px solid #ff6b6b; }}
        .stat-card.oranye {{ border-left: 4px solid #ffa500; }}
        .stat-card.hijau {{ border-left: 4px solid #00ff88; }}
        .stat-card .value {{ font-size: 2.5rem; font-weight: bold; }}
        .stat-card .label {{ color: #aaa; margin-top: 5px; }}
        .merah {{ color: #ff6b6b; }}
        .oranye {{ color: #ffa500; }}
        .hijau {{ color: #00ff88; }}
        .section {{
            background: rgba(255,255,255,0.05);
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 30px;
        }}
        .section h2 {{ margin-bottom: 20px; color: #00d9ff; }}
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        th, td {{
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }}
        th {{ background: rgba(0,0,0,0.3); color: #00d9ff; }}
        tr:hover {{ background: rgba(255,255,255,0.05); }}
        .chart-container {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
        }}
        .chart-box {{
            background: rgba(255,255,255,0.05);
            border-radius: 15px;
            padding: 25px;
        }}
        .legend {{
            display: flex;
            gap: 30px;
            justify-content: center;
            margin-top: 20px;
        }}
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .legend-color {{
            width: 20px;
            height: 20px;
            border-radius: 50%;
        }}
        @media (max-width: 768px) {{
            .stats-grid {{ grid-template-columns: repeat(2, 1fr); }}
            .chart-container {{ grid-template-columns: 1fr; }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🔥 DASHBOARD CINCIN API - Z-SCORE v2.0</h1>
        <p>Deteksi Ganoderma dengan Metode Anomali Statistik | 3 Status: MERAH • ORANYE • HIJAU</p>
    </div>
    
    <div class="config-panel">
        <h3>⚙️ KONFIGURASI THRESHOLD</h3>
        <div class="config-grid">
            <div class="config-item">
                <label>Preset</label>
                <select id="preset" onchange="updateFromPreset()">
                    {preset_options}
                </select>
            </div>
            <div class="config-item">
                <label>Z-Score Core Threshold</label>
                <input type="number" id="z_core" value="{config['z_threshold_core']}" step="0.1" min="-5" max="0">
            </div>
            <div class="config-item">
                <label>Z-Score Neighbor Threshold</label>
                <input type="number" id="z_neighbor" value="{config['z_threshold_neighbor']}" step="0.1" min="-3" max="0">
            </div>
            <div class="config-item">
                <label>Min Stressed Neighbors</label>
                <input type="number" id="min_neighbors" value="{config['min_stressed_neighbors']}" step="1" min="1" max="5">
            </div>
        </div>
        <div class="current-config">
            <strong>Konfigurasi Aktif:</strong> 
            Z-Core = <span class="merah">{config['z_threshold_core']}</span> | 
            Z-Neighbor = <span class="oranye">{config['z_threshold_neighbor']}</span> | 
            Min Neighbors = <span class="hijau">{config['min_stressed_neighbors']}</span>
        </div>
        <p style="margin-top: 15px; color: #888; font-size: 0.9rem;">
            💡 <strong>Interpretasi:</strong> Z-Score &lt; -1.5 = Anomali signifikan (1.5 SD di bawah rata-rata blok)
        </p>
    </div>
    
    <div class="stats-grid">
        <div class="stat-card">
            <div class="value">{total:,}</div>
            <div class="label">Total Pohon</div>
        </div>
        <div class="stat-card merah">
            <div class="value merah">{merah:,}</div>
            <div class="label">🔴 MERAH (Kluster)</div>
        </div>
        <div class="stat-card oranye">
            <div class="value oranye">{oranye:,}</div>
            <div class="label">🟠 ORANYE (Indikasi)</div>
        </div>
        <div class="stat-card hijau">
            <div class="value hijau">{hijau:,}</div>
            <div class="label">🟢 HIJAU (Sehat)</div>
        </div>
    </div>
    
    <div class="chart-container">
        <div class="chart-box">
            <h3 style="color: #00d9ff; margin-bottom: 20px;">📊 Distribusi Status Risiko</h3>
            <canvas id="pieChart"></canvas>
        </div>
        <div class="chart-box">
            <h3 style="color: #00d9ff; margin-bottom: 20px;">📈 Top 10 Blok Paling Berisiko</h3>
            <canvas id="barChart"></canvas>
        </div>
    </div>
    
    <div class="legend">
        <div class="legend-item">
            <div class="legend-color" style="background: #ff6b6b;"></div>
            <span>MERAH: Z &lt; {config['z_threshold_core']} + ≥{config['min_stressed_neighbors']} tetangga stres</span>
        </div>
        <div class="legend-item">
            <div class="legend-color" style="background: #ffa500;"></div>
            <span>ORANYE: Z &lt; {config['z_threshold_core']} + ≥1 tetangga stres</span>
        </div>
        <div class="legend-item">
            <div class="legend-color" style="background: #00ff88;"></div>
            <span>HIJAU: Normal (tidak ada anomali)</span>
        </div>
    </div>
    
    <div class="section" style="margin-top: 30px;">
        <h2>📋 TOP 10 BLOK PALING BERISIKO</h2>
        <table>
            <thead>
                <tr>
                    <th>#</th>
                    <th>Blok</th>
                    <th>🔴 MERAH</th>
                    <th>🟠 ORANYE</th>
                    <th>🟢 HIJAU</th>
                    <th>% Risiko</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>
    </div>
    
    <div style="text-align: center; color: #666; margin-top: 30px;">
        Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Method: Z-Score Spatial Filter v2.0
    </div>
    
    <script>
        // Presets data
        const presets = {json.dumps(ZSCORE_PRESETS)};
        
        function updateFromPreset() {{
            const preset = document.getElementById('preset').value;
            if (presets[preset]) {{
                document.getElementById('z_core').value = presets[preset].z_threshold_core;
                document.getElementById('z_neighbor').value = presets[preset].z_threshold_neighbor;
                document.getElementById('min_neighbors').value = presets[preset].min_stressed_neighbors;
            }}
        }}
        
        // Pie Chart
        new Chart(document.getElementById('pieChart'), {{
            type: 'doughnut',
            data: {{
                labels: ['MERAH (Kluster)', 'ORANYE (Indikasi)', 'HIJAU (Sehat)'],
                datasets: [{{
                    data: [{merah}, {oranye}, {hijau}],
                    backgroundColor: ['#ff6b6b', '#ffa500', '#00ff88'],
                    borderWidth: 0
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    legend: {{ position: 'bottom', labels: {{ color: '#fff' }} }}
                }}
            }}
        }});
        
        // Bar Chart
        new Chart(document.getElementById('barChart'), {{
            type: 'bar',
            data: {{
                labels: {top_10_blocks.index.tolist()},
                datasets: [
                    {{
                        label: 'MERAH',
                        data: {[int(x) for x in top_10_blocks['MERAH'].tolist()]},
                        backgroundColor: '#ff6b6b'
                    }},
                    {{
                        label: 'ORANYE',
                        data: {[int(x) for x in top_10_blocks['ORANYE'].tolist()]},
                        backgroundColor: '#ffa500'
                    }}
                ]
            }},
            options: {{
                responsive: true,
                scales: {{
                    x: {{ stacked: true, grid: {{ color: 'rgba(255,255,255,0.1)' }} }},
                    y: {{ stacked: true, grid: {{ color: 'rgba(255,255,255,0.1)' }} }}
                }},
                plugins: {{
                    legend: {{ position: 'top', labels: {{ color: '#fff' }} }}
                }}
            }}
        }});
    </script>
</body>
</html>
    """
    
    html_path = output_dir / 'cincin_api_zscore_dashboard.html'
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f'Dashboard saved: {html_path}')
    return html_path

def main():
    print('=' * 70)
    print('DASHBOARD CINCIN API - Z-SCORE v2.0')
    print('=' * 70)
    
    # Load data
    print('\n[1/3] Loading data...')
    df = load_and_clean_data(Path('data/input/tabelNDREnew.csv'))
    print(f'  Total: {len(df):,} pohon')
    
    # Use standar preset
    config = ZSCORE_PRESETS['standar']
    print(f'\n[2/3] Running Z-Score detection...')
    print(f'  Config: {config}')
    
    df = run_zscore_with_config(
        df,
        z_threshold_core=config['z_threshold_core'],
        z_threshold_neighbor=config['z_threshold_neighbor'],
        min_neighbors=config['min_stressed_neighbors']
    )
    
    # Stats
    merah = len(df[df['Status_Risiko'] == 'MERAH'])
    oranye = len(df[df['Status_Risiko'] == 'ORANYE'])
    hijau = len(df[df['Status_Risiko'] == 'HIJAU'])
    
    print(f'\n  Results:')
    print(f'    MERAH (Kluster): {merah:,}')
    print(f'    ORANYE (Indikasi): {oranye:,}')
    print(f'    HIJAU (Sehat): {hijau:,}')
    
    # Generate dashboard
    print(f'\n[3/3] Generating HTML dashboard...')
    html_path = generate_zscore_dashboard(df, config, output_dir)
    
    # Save CSV
    df.to_csv(output_dir / 'zscore_results.csv', index=False)
    
    print(f'\n✅ Dashboard ready: {html_path}')
    return html_path

if __name__ == '__main__':
    html_path = main()
