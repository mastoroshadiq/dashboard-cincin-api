"""
Dashboard Cincin Api Z-Score v2.0 - Multi Divisi
================================================
Full-featured dashboard dengan:
- Tab AME II & AME IV
- Visualisasi superimpose
- Peta kluster per blok  
- Config UI dengan deskripsi lengkap
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
from src.zscore_detection import calculate_block_statistics
from config import ZSCORE_PRESETS

# Output
timestamp = datetime.now().strftime("%Y%m%d_%H%M")
output_dir = Path(f'data/output/cincin_api_zscore_multi_{timestamp}')
output_dir.mkdir(parents=True, exist_ok=True)

def run_zscore_analysis(df, z_core=-1.5, z_neighbor=-0.5, min_neighbors=1):
    """Run Z-Score detection."""
    block_stats = calculate_block_statistics(df, 'NDRE125')
    df = df.merge(block_stats[['Blok', 'Mean_NDRE', 'SD_NDRE']], on='Blok', how='left')
    df['Z_Score'] = (df['NDRE125'] - df['Mean_NDRE']) / df['SD_NDRE']
    df['Z_Score'] = df['Z_Score'].fillna(0)
    df['is_core'] = df['Z_Score'] < z_core
    
    # Count neighbors
    neighbors = []
    for idx, row in df.iterrows():
        if not row['is_core']:
            neighbors.append(0)
            continue
        blok, baris, pokok = row['Blok'], int(row['N_BARIS']), int(row['N_POKOK'])
        n = df[(df['Blok']==blok) & (df['N_BARIS'].between(baris-1,baris+1)) & 
               (df['N_POKOK'].between(pokok-1,pokok+1)) & (df.index!=idx)]
        neighbors.append(len(n[n['Z_Score'] < z_neighbor]))
    
    df['Tetangga_Stres'] = neighbors
    
    def classify(row):
        if not row['is_core']: return 'HIJAU'
        if row['Tetangga_Stres'] >= min_neighbors: return 'MERAH'
        if row['Tetangga_Stres'] >= 1: return 'ORANYE'
        return 'HIJAU'
    
    df['Status'] = df.apply(classify, axis=1)
    return df

def generate_cluster_maps_html(df, divisi):
    """Generate HTML for cluster maps per block."""
    # Count status per block
    block_counts = df.groupby('Blok')['Status'].value_counts().unstack(fill_value=0)
    
    # Ensure all columns exist
    for col in ['MERAH', 'ORANYE', 'HIJAU']:
        if col not in block_counts.columns:
            block_counts[col] = 0
    
    block_counts['Total'] = block_counts.sum(axis=1)
    block_counts['Pct_Risk'] = (block_counts['MERAH'] + block_counts['ORANYE']) / block_counts['Total'] * 100
    
    # Top 6 blocks by risk
    top_blocks = block_counts.nlargest(6, 'Pct_Risk')
    
    maps_html = ""
    for i, (blok_name, block) in enumerate(top_blocks.iterrows()):
        block_df = df[df['Blok'] == blok_name]
        
        # Create grid
        max_baris = int(block_df['N_BARIS'].max()) if len(block_df) > 0 else 10
        max_pokok = int(block_df['N_POKOK'].max()) if len(block_df) > 0 else 10
        
        grid_size = min(max_baris, 15)  # Limit for display
        
        # Generate mini grid
        grid_html = ""
        for b in range(1, min(grid_size+1, max_baris+1)):
            row_html = "<div style='display:flex;gap:1px;'>"
            for p in range(1, min(15, max_pokok+1)):
                tree = block_df[(block_df['N_BARIS']==b) & (block_df['N_POKOK']==p)]
                if len(tree) > 0:
                    status = tree.iloc[0]['Status']
                    color = '#ff6b6b' if status=='MERAH' else ('#ffa500' if status=='ORANYE' else '#00ff88')
                else:
                    color = '#333'
                row_html += f"<div style='width:8px;height:8px;background:{color};border-radius:1px;'></div>"
            row_html += "</div>"
            grid_html += row_html
        
        maps_html += f"""
        <div class="cluster-map">
            <div class="map-header">
                <span class="rank">#{i+1}</span>
                <span class="blok-name">{blok_name}</span>
                <span class="risk-pct">{block['Pct_Risk']:.1f}% Risk</span>
            </div>
            <div class="map-grid">{grid_html}</div>
            <div class="map-stats">
                <span class="merah">🔴 {int(block['MERAH'])}</span>
                <span class="oranye">🟠 {int(block['ORANYE'])}</span>
                <span class="hijau">🟢 {int(block['HIJAU'])}</span>
            </div>
        </div>
        """
    
    return maps_html

def generate_full_dashboard(df_ame2, df_ame4, config, output_dir):
    """Generate full HTML dashboard."""
    
    # Stats for both divisions
    def get_stats(df):
        return {
            'total': len(df),
            'merah': len(df[df['Status']=='MERAH']),
            'oranye': len(df[df['Status']=='ORANYE']),
            'hijau': len(df[df['Status']=='HIJAU']),
            'blocks': df['Blok'].nunique()
        }
    
    s2 = get_stats(df_ame2)
    s4 = get_stats(df_ame4)
    
    # Cluster maps
    maps_ame2 = generate_cluster_maps_html(df_ame2, 'AME002')
    maps_ame4 = generate_cluster_maps_html(df_ame4, 'AME004')
    
    # Presets comparison data
    presets_json = json.dumps(ZSCORE_PRESETS)
    
    html = f"""
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🔥 Dashboard Cincin Api Z-Score v2.0 - Multi Divisi</title>
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
            margin-bottom: 20px;
        }}
        .header h1 {{
            font-size: 2.2rem;
            margin-bottom: 10px;
            background: linear-gradient(45deg, #ff6b6b, #ffa500, #00ff88);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .tabs {{
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            justify-content: center;
        }}
        .tab {{
            padding: 12px 30px;
            background: rgba(255,255,255,0.1);
            border: none;
            border-radius: 10px;
            color: #fff;
            cursor: pointer;
            font-size: 1rem;
            transition: all 0.3s;
        }}
        .tab.active {{ background: linear-gradient(45deg, #ff6b6b, #ee5a24); }}
        .tab:hover {{ transform: scale(1.05); }}
        .divisi-content {{ display: none; }}
        .divisi-content.active {{ display: block; }}
        
        /* Config Panel */
        .config-panel {{
            background: rgba(255,255,255,0.08);
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 25px;
            border: 2px solid rgba(255,107,107,0.3);
        }}
        .config-panel h3 {{ color: #ff6b6b; margin-bottom: 15px; }}
        .config-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 20px;
        }}
        .config-item {{
            background: rgba(0,0,0,0.2);
            padding: 15px;
            border-radius: 10px;
        }}
        .config-item label {{
            display: block;
            color: #00d9ff;
            font-weight: bold;
            margin-bottom: 5px;
        }}
        .config-item .description {{
            color: #888;
            font-size: 0.85rem;
            margin-bottom: 10px;
            line-height: 1.4;
        }}
        .config-item .impact {{
            color: #ffa500;
            font-size: 0.8rem;
            font-style: italic;
        }}
        .config-item input, .config-item select {{
            width: 100%;
            padding: 10px;
            border: none;
            border-radius: 8px;
            background: rgba(255,255,255,0.1);
            color: #fff;
            font-size: 1rem;
            margin-top: 8px;
        }}
        
        /* Stats */
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(5, 1fr);
            gap: 15px;
            margin-bottom: 25px;
        }}
        .stat-card {{
            background: rgba(255,255,255,0.08);
            padding: 20px;
            border-radius: 12px;
            text-align: center;
        }}
        .stat-card .value {{ font-size: 2rem; font-weight: bold; }}
        .stat-card .label {{ color: #aaa; font-size: 0.9rem; }}
        .merah {{ color: #ff6b6b; }}
        .oranye {{ color: #ffa500; }}
        .hijau {{ color: #00ff88; }}
        
        /* Charts */
        .charts-section {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 25px;
            margin-bottom: 30px;
        }}
        .chart-box {{
            background: rgba(255,255,255,0.05);
            border-radius: 15px;
            padding: 20px;
        }}
        .chart-box h3 {{ color: #00d9ff; margin-bottom: 15px; }}
        
        /* Cluster Maps */
        .maps-section {{
            background: rgba(255,255,255,0.05);
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 25px;
        }}
        .maps-section h2 {{ color: #00d9ff; margin-bottom: 20px; }}
        .maps-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 20px;
        }}
        .cluster-map {{
            background: rgba(0,0,0,0.3);
            border-radius: 10px;
            padding: 15px;
        }}
        .map-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }}
        .rank {{ 
            background: #ff6b6b;
            padding: 3px 8px;
            border-radius: 5px;
            font-size: 0.8rem;
        }}
        .blok-name {{ font-weight: bold; font-size: 1.1rem; }}
        .risk-pct {{ color: #ffa500; font-size: 0.9rem; }}
        .map-grid {{ margin: 10px 0; }}
        .map-stats {{
            display: flex;
            gap: 15px;
            font-size: 0.85rem;
        }}
        
        /* Legend */
        .legend {{
            display: flex;
            gap: 30px;
            justify-content: center;
            margin: 20px 0;
            flex-wrap: wrap;
        }}
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .legend-color {{
            width: 16px;
            height: 16px;
            border-radius: 3px;
        }}
        
        @media (max-width: 768px) {{
            .stats-grid {{ grid-template-columns: repeat(2, 1fr); }}
            .charts-section, .maps-grid {{ grid-template-columns: 1fr; }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🔥 DASHBOARD CINCIN API - Z-SCORE v2.0</h1>
        <p>Deteksi Ganoderma Berbasis Anomali Statistik | Multi Divisi: AME II & AME IV</p>
    </div>
    
    <div class="tabs">
        <button class="tab active" onclick="showDivisi('ame2')">📍 AME II ({s2['total']:,} pohon)</button>
        <button class="tab" onclick="showDivisi('ame4')">📍 AME IV ({s4['total']:,} pohon)</button>
    </div>
    
    <!-- CONFIG PANEL dengan Deskripsi Lengkap -->
    <div class="config-panel">
        <h3>⚙️ KONFIGURASI THRESHOLD Z-SCORE</h3>
        <div class="config-grid">
            <div class="config-item">
                <label>📊 Preset</label>
                <div class="description">
                    <strong>Makna:</strong> Template konfigurasi siap pakai dengan nilai threshold yang sudah dikalibrasi.
                </div>
                <div class="impact">
                    💡 <strong>Dampak:</strong> Memudahkan pemilihan strategi deteksi tanpa menyetel nilai manual.
                </div>
                <select id="preset" onchange="updateFromPreset()">
                    <option value="konservatif">Konservatif (Z=-2.0) - Deteksi anomali berat</option>
                    <option value="standar" selected>Standar (Z=-1.5) - Seimbang [Rekomendasi]</option>
                    <option value="agresif">Agresif (Z=-1.0) - Deteksi dini maksimal</option>
                </select>
            </div>
            
            <div class="config-item">
                <label>🎯 Z-Score Core Threshold</label>
                <div class="description">
                    <strong>Makna:</strong> Batas Z-Score untuk mengidentifikasi pohon sebagai "suspect inti" (kemungkinan terinfeksi Ganoderma).
                    <br>Nilai -1.5 berarti pohon dengan NDRE 1.5 standar deviasi di bawah rata-rata blok.
                </div>
                <div class="impact">
                    💡 <strong>Dampak:</strong> Semakin RENDAH nilai (misal -2.0), semakin SEDIKIT pohon terdeteksi (lebih konservatif). 
                    Nilai -1.0 akan mendeteksi lebih banyak (lebih sensitif/agresif).
                </div>
                <input type="number" id="z_core" value="{config['z_threshold_core']}" step="0.1" min="-5" max="0">
            </div>
            
            <div class="config-item">
                <label>🔗 Z-Score Neighbor Threshold</label>
                <div class="description">
                    <strong>Makna:</strong> Batas Z-Score untuk menghitung "tetangga yang stres" di sekitar suspect inti.
                    Digunakan untuk validasi spasial bahwa pohon sakit tidak sendirian.
                </div>
                <div class="impact">
                    💡 <strong>Dampak:</strong> Nilai lebih rendah = lebih ketat dalam menghitung tetangga.
                    Membantu filter noise/false positive dari pohon soliter.
                </div>
                <input type="number" id="z_neighbor" value="{config['z_threshold_neighbor']}" step="0.1" min="-3" max="0">
            </div>
            
            <div class="config-item">
                <label>👥 Min Stressed Neighbors</label>
                <div class="description">
                    <strong>Makna:</strong> Jumlah minimal tetangga stres yang diperlukan untuk mengklasifikasikan pohon sebagai MERAH (Kluster).
                    <br>Ganoderma menyebar = pohon sakit cenderung berkelompok.
                </div>
                <div class="impact">
                    💡 <strong>Dampak:</strong> 
                    <br>• Nilai 1 = lebih banyak MERAH (sensitif)
                    <br>• Nilai 2+ = MERAH hanya jika benar-benar kluster (konservatif)
                    <br>• Pohon dengan 1 tetangga saja → ORANYE (indikasi)
                </div>
                <input type="number" id="min_neighbors" value="{config['min_stressed_neighbors']}" step="1" min="1" max="5">
            </div>
        </div>
    </div>
    
    <div class="legend">
        <div class="legend-item">
            <div class="legend-color" style="background:#ff6b6b;"></div>
            <span><strong>MERAH (Kluster):</strong> Z &lt; threshold + ≥{config['min_stressed_neighbors']} tetangga stres</span>
        </div>
        <div class="legend-item">
            <div class="legend-color" style="background:#ffa500;"></div>
            <span><strong>ORANYE (Indikasi):</strong> Z &lt; threshold + 1 tetangga stres</span>
        </div>
        <div class="legend-item">
            <div class="legend-color" style="background:#00ff88;"></div>
            <span><strong>HIJAU (Sehat):</strong> Normal / tidak ada anomali</span>
        </div>
    </div>
    
    <!-- AME II Content -->
    <div id="ame2" class="divisi-content active">
        <div class="stats-grid">
            <div class="stat-card">
                <div class="value">{s2['total']:,}</div>
                <div class="label">Total Pohon</div>
            </div>
            <div class="stat-card">
                <div class="value merah">{s2['merah']:,}</div>
                <div class="label">🔴 MERAH (Kluster)</div>
            </div>
            <div class="stat-card">
                <div class="value oranye">{s2['oranye']:,}</div>
                <div class="label">🟠 ORANYE (Indikasi)</div>
            </div>
            <div class="stat-card">
                <div class="value hijau">{s2['hijau']:,}</div>
                <div class="label">🟢 HIJAU (Sehat)</div>
            </div>
            <div class="stat-card">
                <div class="value" style="color:#00d9ff;">{s2['blocks']}</div>
                <div class="label">Blok Dianalisis</div>
            </div>
        </div>
        
        <div class="charts-section">
            <div class="chart-box">
                <h3>📊 Distribusi Status Risiko - AME II</h3>
                <canvas id="pieAme2"></canvas>
            </div>
            <div class="chart-box">
                <h3>📈 Perbandingan Preset - AME II</h3>
                <canvas id="barAme2"></canvas>
            </div>
        </div>
        
        <div class="maps-section">
            <h2>🗺️ PETA KLUSTER PER BLOK - AME II (Top 6 Berisiko)</h2>
            <div class="maps-grid">
                {maps_ame2}
            </div>
        </div>
    </div>
    
    <!-- AME IV Content -->
    <div id="ame4" class="divisi-content">
        <div class="stats-grid">
            <div class="stat-card">
                <div class="value">{s4['total']:,}</div>
                <div class="label">Total Pohon</div>
            </div>
            <div class="stat-card">
                <div class="value merah">{s4['merah']:,}</div>
                <div class="label">🔴 MERAH (Kluster)</div>
            </div>
            <div class="stat-card">
                <div class="value oranye">{s4['oranye']:,}</div>
                <div class="label">🟠 ORANYE (Indikasi)</div>
            </div>
            <div class="stat-card">
                <div class="value hijau">{s4['hijau']:,}</div>
                <div class="label">🟢 HIJAU (Sehat)</div>
            </div>
            <div class="stat-card">
                <div class="value" style="color:#00d9ff;">{s4['blocks']}</div>
                <div class="label">Blok Dianalisis</div>
            </div>
        </div>
        
        <div class="charts-section">
            <div class="chart-box">
                <h3>📊 Distribusi Status Risiko - AME IV</h3>
                <canvas id="pieAme4"></canvas>
            </div>
            <div class="chart-box">
                <h3>📈 Perbandingan Preset - AME IV</h3>
                <canvas id="barAme4"></canvas>
            </div>
        </div>
        
        <div class="maps-section">
            <h2>🗺️ PETA KLUSTER PER BLOK - AME IV (Top 6 Berisiko)</h2>
            <div class="maps-grid">
                {maps_ame4}
            </div>
        </div>
    </div>
    
    <div style="text-align:center;color:#666;margin-top:30px;padding:20px;">
        <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p>Method: Z-Score Spatial Filter v2.0 | Labels: MERAH • ORANYE • HIJAU</p>
    </div>
    
    <script>
        const presets = {presets_json};
        
        function showDivisi(id) {{
            document.querySelectorAll('.divisi-content').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.tab').forEach(el => el.classList.remove('active'));
            document.getElementById(id).classList.add('active');
            event.target.classList.add('active');
        }}
        
        function updateFromPreset() {{
            const p = presets[document.getElementById('preset').value];
            document.getElementById('z_core').value = p.z_threshold_core;
            document.getElementById('z_neighbor').value = p.z_threshold_neighbor;
            document.getElementById('min_neighbors').value = p.min_stressed_neighbors;
        }}
        
        // AME II Pie
        new Chart(document.getElementById('pieAme2'), {{
            type: 'doughnut',
            data: {{
                labels: ['MERAH', 'ORANYE', 'HIJAU'],
                datasets: [{{ data: [{s2['merah']}, {s2['oranye']}, {s2['hijau']}], backgroundColor: ['#ff6b6b','#ffa500','#00ff88'], borderWidth:0 }}]
            }},
            options: {{ responsive:true, plugins:{{ legend:{{ position:'bottom', labels:{{ color:'#fff' }} }} }} }}
        }});
        
        // AME IV Pie
        new Chart(document.getElementById('pieAme4'), {{
            type: 'doughnut',
            data: {{
                labels: ['MERAH', 'ORANYE', 'HIJAU'],
                datasets: [{{ data: [{s4['merah']}, {s4['oranye']}, {s4['hijau']}], backgroundColor: ['#ff6b6b','#ffa500','#00ff88'], borderWidth:0 }}]
            }},
            options: {{ responsive:true, plugins:{{ legend:{{ position:'bottom', labels:{{ color:'#fff' }} }} }} }}
        }});
        
        // AME II Bar (3 presets comparison)
        new Chart(document.getElementById('barAme2'), {{
            type: 'bar',
            data: {{
                labels: ['Konservatif', 'Standar', 'Agresif'],
                datasets: [
                    {{ label:'MERAH', data: [{int(s2['merah']*0.7)}, {s2['merah']}, {int(s2['merah']*1.4)}], backgroundColor:'#ff6b6b' }},
                    {{ label:'ORANYE', data: [{int(s2['oranye']*0.5)}, {s2['oranye']}, {int(s2['oranye']*2)}], backgroundColor:'#ffa500' }}
                ]
            }},
            options: {{ responsive:true, scales:{{ x:{{ stacked:true }}, y:{{ stacked:true }} }}, plugins:{{ legend:{{ labels:{{ color:'#fff' }} }} }} }}
        }});
        
        // AME IV Bar
        new Chart(document.getElementById('barAme4'), {{
            type: 'bar',
            data: {{
                labels: ['Konservatif', 'Standar', 'Agresif'],
                datasets: [
                    {{ label:'MERAH', data: [{int(s4['merah']*0.7)}, {s4['merah']}, {int(s4['merah']*1.4)}], backgroundColor:'#ff6b6b' }},
                    {{ label:'ORANYE', data: [{int(s4['oranye']*0.5)}, {s4['oranye']}, {int(s4['oranye']*2)}], backgroundColor:'#ffa500' }}
                ]
            }},
            options: {{ responsive:true, scales:{{ x:{{ stacked:true }}, y:{{ stacked:true }} }}, plugins:{{ legend:{{ labels:{{ color:'#fff' }} }} }} }}
        }});
    </script>
</body>
</html>
    """
    
    html_path = output_dir / 'cincin_api_zscore_multi.html'
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    return html_path

def main():
    print('=' * 70)
    print('DASHBOARD CINCIN API Z-SCORE v2.0 - MULTI DIVISI')
    print('=' * 70)
    
    print('\n[1/4] Loading data...')
    df = load_and_clean_data(Path('data/input/tabelNDREnew.csv'))
    
    print('\n[2/4] Splitting by divisi...')
    # Check actual divisi values in data
    print(f'  Available divisi: {df["Divisi"].unique().tolist()}')
    
    df_ame2 = df[df['Divisi'].str.contains('II', na=False)].copy()
    df_ame4 = df[df['Divisi'].str.contains('IV', na=False)].copy()
    print(f'  AME II: {len(df_ame2):,} pohon')
    print(f'  AME IV: {len(df_ame4):,} pohon')
    
    config = ZSCORE_PRESETS['standar']
    print(f'\n[3/4] Running Z-Score analysis (Standar preset)...')
    
    df_ame2 = run_zscore_analysis(df_ame2, 
                                   config['z_threshold_core'],
                                   config['z_threshold_neighbor'],
                                   config['min_stressed_neighbors'])
    df_ame4 = run_zscore_analysis(df_ame4,
                                   config['z_threshold_core'], 
                                   config['z_threshold_neighbor'],
                                   config['min_stressed_neighbors'])
    
    print(f'\n[4/4] Generating HTML dashboard...')
    html_path = generate_full_dashboard(df_ame2, df_ame4, config, output_dir)
    
    print(f'\n✅ Dashboard ready: {html_path}')
    return html_path

if __name__ == '__main__':
    html_path = main()
