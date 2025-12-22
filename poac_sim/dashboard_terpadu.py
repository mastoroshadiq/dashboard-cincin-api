"""
Dashboard Terpadu Cincin Api + Produktivitas v3.0
==================================================
Integrasi lengkap:
1. Visualisasi Cincin Api dari dashboard lama
2. Konfigurasi Z-Score dinamis  
3. Data Produktivitas (Yield per blok)
4. Korelasi Ganoderma vs Produktivitas
"""
import sys
sys.path.insert(0, 'src')

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import json
import base64
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

from src.ingestion import load_and_clean_data
from src.zscore_detection import calculate_block_statistics
from config import ZSCORE_PRESETS

# Output
timestamp = datetime.now().strftime("%Y%m%d_%H%M")
output_dir = Path(f'data/output/dashboard_terpadu_{timestamp}')
output_dir.mkdir(parents=True, exist_ok=True)

def load_productivity_data():
    """Load productivity data from data_gabungan.xlsx."""
    xlsx_path = Path('data/input/data_gabungan.xlsx')
    if not xlsx_path.exists():
        logging.warning(f"Productivity data not found: {xlsx_path}")
        return None
    
    df = pd.read_excel(xlsx_path, header=None)
    
    # Based on previous analysis:
    # col_0 = Blok, col_11 = Luas_Ha, col_170 = Produksi_Ton
    prod_df = pd.DataFrame({
        'Blok': df.iloc[2:, 0].values,
        'Luas_Ha': pd.to_numeric(df.iloc[2:, 11], errors='coerce'),
        'Produksi_Ton': pd.to_numeric(df.iloc[2:, 170], errors='coerce')
    })
    
    prod_df = prod_df.dropna(subset=['Blok', 'Luas_Ha', 'Produksi_Ton'])
    prod_df['Yield_TonHa'] = prod_df['Produksi_Ton'] / prod_df['Luas_Ha']
    prod_df = prod_df[prod_df['Yield_TonHa'].replace([np.inf, -np.inf], np.nan).notna()]
    
    logging.info(f"Loaded productivity data: {len(prod_df)} blocks")
    return prod_df

def run_zscore_analysis(df, preset_name='standar'):
    """Run Z-Score detection with preset."""
    preset = ZSCORE_PRESETS[preset_name]
    z_core = preset['z_threshold_core']
    z_neighbor = preset['z_threshold_neighbor']
    min_neighbors = preset['min_stressed_neighbors']
    
    block_stats = calculate_block_statistics(df, 'NDRE125')
    df = df.merge(block_stats[['Blok', 'Mean_NDRE', 'SD_NDRE']], on='Blok', how='left')
    df['Z_Score'] = (df['NDRE125'] - df['Mean_NDRE']) / df['SD_NDRE']
    df['Z_Score'] = df['Z_Score'].fillna(0)
    df['is_core'] = df['Z_Score'] < z_core
    
    # Count neighbors (simplified)
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

def calculate_block_stats(df_gano):
    """Calculate Ganoderma statistics per block."""
    block_stats = df_gano.groupby('Blok').agg({
        'Status': lambda x: pd.Series({
            'Total': len(x),
            'Merah': (x=='MERAH').sum(),
            'Oranye': (x=='ORANYE').sum(),
            'Hijau': (x=='HIJAU').sum()
        })
    }).reset_index()
    
    # Flatten
    stats = df_gano.groupby('Blok')['Status'].value_counts().unstack(fill_value=0)
    for col in ['MERAH', 'ORANYE', 'HIJAU']:
        if col not in stats.columns:
            stats[col] = 0
    stats['Total'] = stats.sum(axis=1)
    stats['Pct_Attack'] = (stats['MERAH'] + stats['ORANYE']) / stats['Total'] * 100
    
    return stats.reset_index()

def integrate_data(gano_stats, prod_df):
    """Integrate Ganoderma and Productivity data."""
    if prod_df is None:
        return gano_stats
    
    # Merge on Blok
    merged = gano_stats.merge(prod_df, on='Blok', how='left')
    merged['Yield_TonHa'] = merged['Yield_TonHa'].fillna(0)
    
    return merged

def copy_existing_visualizations(source_dir, dest_dir):
    """Copy existing visualizations from old dashboard."""
    source = Path(source_dir)
    if not source.exists():
        return []
    
    copied = []
    for png in source.glob('**/*.png'):
        dest = dest_dir / png.name
        import shutil
        shutil.copy(png, dest)
        copied.append(dest)
    
    return copied

def generate_integrated_dashboard(df_gano, prod_df, preset_name, output_dir):
    """Generate comprehensive integrated dashboard."""
    
    # Calculate stats
    gano_stats = calculate_block_stats(df_gano)
    integrated = integrate_data(gano_stats, prod_df)
    
    # Overall stats
    total_trees = len(df_gano)
    merah_count = len(df_gano[df_gano['Status']=='MERAH'])
    oranye_count = len(df_gano[df_gano['Status']=='ORANYE'])
    hijau_count = len(df_gano[df_gano['Status']=='HIJAU'])
    
    # Top riskiest blocks
    top_risk = integrated.nlargest(10, 'Pct_Attack')
    
    # Productivity stats
    if prod_df is not None:
        avg_yield = prod_df['Yield_TonHa'].mean()
        total_prod = prod_df['Produksi_Ton'].sum()
    else:
        avg_yield = 0
        total_prod = 0
    
    # Generate correlation analysis
    if prod_df is not None and 'Yield_TonHa' in integrated.columns:
        corr_data = integrated[['Pct_Attack', 'Yield_TonHa']].dropna()
        if len(corr_data) > 5:
            correlation = corr_data['Pct_Attack'].corr(corr_data['Yield_TonHa'])
        else:
            correlation = None
    else:
        correlation = None
    
    # Config presets JSON
    presets_json = json.dumps(ZSCORE_PRESETS)
    current_preset = ZSCORE_PRESETS[preset_name]
    
    # Top blocks data for charts
    top_blocks_labels = json.dumps(top_risk['Blok'].tolist())
    top_blocks_attack = json.dumps(top_risk['Pct_Attack'].round(1).tolist())
    top_blocks_yield = json.dumps(top_risk['Yield_TonHa'].round(2).tolist() if 'Yield_TonHa' in top_risk.columns else [])
    
    html = f"""
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🔥 Dashboard Terpadu Cincin Api + Produktivitas v3.0</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {{
            --merah: #e74c3c;
            --oranye: #e67e22;
            --kuning: #f1c40f;
            --hijau: #27ae60;
            --biru: #3498db;
            --ungu: #9b59b6;
            --dark: #2c3e50;
            --light: #ecf0f1;
        }}
        
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
            min-height: 100vh;
            color: #fff;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1600px;
            margin: 0 auto;
        }}
        
        .header {{
            text-align: center;
            padding: 40px 20px;
            background: rgba(255,255,255,0.05);
            border-radius: 20px;
            margin-bottom: 30px;
            backdrop-filter: blur(10px);
        }}
        
        .header h1 {{
            font-size: 2.8rem;
            margin-bottom: 10px;
            background: linear-gradient(45deg, #ff6b6b, #ffa500, #00ff88, #00d9ff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        
        .header .subtitle {{
            color: #aaa;
            font-size: 1.1rem;
        }}
        
        /* Section styling */
        .section {{
            background: rgba(255,255,255,0.05);
            border-radius: 20px;
            padding: 30px;
            margin-bottom: 30px;
            backdrop-filter: blur(5px);
        }}
        
        .section h2 {{
            color: #00d9ff;
            margin-bottom: 25px;
            padding-bottom: 10px;
            border-bottom: 2px solid rgba(0,217,255,0.3);
        }}
        
        /* Config Panel */
        .config-panel {{
            background: rgba(255,107,107,0.1);
            border: 2px solid rgba(255,107,107,0.3);
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 30px;
        }}
        
        .config-panel h3 {{
            color: #ff6b6b;
            margin-bottom: 20px;
        }}
        
        .config-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
        }}
        
        .config-item {{
            background: rgba(0,0,0,0.3);
            padding: 20px;
            border-radius: 12px;
        }}
        
        .config-item label {{
            display: block;
            color: #00d9ff;
            font-weight: bold;
            margin-bottom: 8px;
            font-size: 1rem;
        }}
        
        .config-item .desc {{
            color: #888;
            font-size: 0.85rem;
            margin-bottom: 10px;
            line-height: 1.5;
        }}
        
        .config-item .impact {{
            color: #ffa500;
            font-size: 0.8rem;
            font-style: italic;
            margin-bottom: 10px;
        }}
        
        .config-item input, .config-item select {{
            width: 100%;
            padding: 12px;
            border: none;
            border-radius: 8px;
            background: rgba(255,255,255,0.1);
            color: #fff;
            font-size: 1rem;
        }}
        
        /* Stats Grid */
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .stat-card {{
            background: rgba(255,255,255,0.08);
            padding: 25px;
            border-radius: 15px;
            text-align: center;
            transition: transform 0.3s ease;
        }}
        
        .stat-card:hover {{
            transform: translateY(-5px);
        }}
        
        .stat-card .value {{
            font-size: 2.5rem;
            font-weight: bold;
        }}
        
        .stat-card .label {{
            color: #aaa;
            font-size: 0.9rem;
            margin-top: 5px;
        }}
        
        .stat-card.merah {{ border-left: 5px solid var(--merah); }}
        .stat-card.oranye {{ border-left: 5px solid var(--oranye); }}
        .stat-card.hijau {{ border-left: 5px solid var(--hijau); }}
        .stat-card.biru {{ border-left: 5px solid var(--biru); }}
        .stat-card.ungu {{ border-left: 5px solid var(--ungu); }}
        
        .merah {{ color: var(--merah); }}
        .oranye {{ color: var(--oranye); }}
        .hijau {{ color: var(--hijau); }}
        .biru {{ color: var(--biru); }}
        .ungu {{ color: var(--ungu); }}
        
        /* Charts Grid */
        .charts-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 25px;
            margin-bottom: 30px;
        }}
        
        .chart-box {{
            background: rgba(255,255,255,0.05);
            border-radius: 15px;
            padding: 20px;
        }}
        
        .chart-box h3 {{
            color: #00d9ff;
            margin-bottom: 15px;
            font-size: 1rem;
        }}
        
        /* Integrated Table */
        .integrated-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        
        .integrated-table th, .integrated-table td {{
            padding: 12px 15px;
            text-align: center;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }}
        
        .integrated-table th {{
            background: rgba(0,217,255,0.2);
            color: #00d9ff;
            font-weight: bold;
        }}
        
        .integrated-table tr:hover {{
            background: rgba(255,255,255,0.05);
        }}
        
        .integrated-table .rank {{
            background: var(--merah);
            color: white;
            padding: 5px 10px;
            border-radius: 20px;
            font-weight: bold;
        }}
        
        /* Correlation Box */
        .correlation-box {{
            background: linear-gradient(135deg, rgba(155,89,182,0.3) 0%, rgba(52,152,219,0.3) 100%);
            border-radius: 15px;
            padding: 25px;
            text-align: center;
            margin-top: 20px;
        }}
        
        .correlation-value {{
            font-size: 3rem;
            font-weight: bold;
            margin: 15px 0;
        }}
        
        /* Legend */
        .legend {{
            display: flex;
            flex-wrap: wrap;
            gap: 20px;
            justify-content: center;
            margin: 20px 0;
            padding: 15px;
            background: rgba(0,0,0,0.2);
            border-radius: 10px;
        }}
        
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        
        .legend-color {{
            width: 20px;
            height: 20px;
            border-radius: 4px;
        }}
        
        /* Footer */
        .footer {{
            text-align: center;
            color: #666;
            padding: 30px;
            font-size: 0.9rem;
        }}
        
        @media (max-width: 1024px) {{
            .charts-grid {{ grid-template-columns: 1fr; }}
            .stats-grid {{ grid-template-columns: repeat(2, 1fr); }}
        }}
        
        @media (max-width: 600px) {{
            .stats-grid {{ grid-template-columns: 1fr; }}
            .config-grid {{ grid-template-columns: 1fr; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔥 DASHBOARD TERPADU CINCIN API + PRODUKTIVITAS</h1>
            <p class="subtitle">Analisis Komprehensif: Deteksi Ganoderma × Data Produktivitas Blok | v3.0</p>
        </div>
        
        <!-- CONFIG PANEL -->
        <div class="config-panel">
            <h3>⚙️ KONFIGURASI THRESHOLD Z-SCORE</h3>
            <div class="config-grid">
                <div class="config-item">
                    <label>📊 Preset Strategi</label>
                    <div class="desc">
                        <strong>Makna:</strong> Template konfigurasi dengan nilai threshold yang sudah dikalibrasi untuk skenario berbeda.
                    </div>
                    <div class="impact">
                        💡 <strong>Dampak:</strong> Konservatif = fokus kasus berat, Agresif = deteksi dini maksimal
                    </div>
                    <select id="preset" onchange="updateFromPreset()">
                        <option value="konservatif" {"selected" if preset_name=="konservatif" else ""}>Konservatif (Z=-2.0) - Fokus anomali berat</option>
                        <option value="standar" {"selected" if preset_name=="standar" else ""}>Standar (Z=-1.5) - Seimbang [Rekomendasi]</option>
                        <option value="agresif" {"selected" if preset_name=="agresif" else ""}>Agresif (Z=-1.0) - Deteksi dini maksimal</option>
                    </select>
                </div>
                
                <div class="config-item">
                    <label>🎯 Z-Score Core Threshold</label>
                    <div class="desc">
                        <strong>Makna:</strong> Batas deviasi dari rata-rata blok untuk menandai pohon sebagai "suspect inti". 
                        Nilai -1.5 = pohon dengan NDRE 1.5σ di bawah mean blok.
                    </div>
                    <div class="impact">
                        💡 <strong>Dampak:</strong> Lebih negatif → lebih sedikit terdeteksi (ketat), lebih mendekati 0 → lebih banyak (sensitif)
                    </div>
                    <input type="number" id="z_core" value="{current_preset['z_threshold_core']}" step="0.1">
                </div>
                
                <div class="config-item">
                    <label>🔗 Z-Score Neighbor Threshold</label>
                    <div class="desc">
                        <strong>Makna:</strong> Batas untuk menghitung tetangga yang juga "stres". Digunakan validasi spasial 
                        bahwa pohon sakit berkelompok (karakteristik Ganoderma).
                    </div>
                    <div class="impact">
                        💡 <strong>Dampak:</strong> Membantu filter false positive dari pohon yang sakit secara individual
                    </div>
                    <input type="number" id="z_neighbor" value="{current_preset['z_threshold_neighbor']}" step="0.1">
                </div>
                
                <div class="config-item">
                    <label>👥 Min Stressed Neighbors</label>
                    <div class="desc">
                        <strong>Makna:</strong> Jumlah minimal tetangga stres yang diperlukan untuk klasifikasi MERAH (Kluster).
                        Ganoderma menyebar → pohon sakit cenderung berkelompok.
                    </div>
                    <div class="impact">
                        💡 <strong>Dampak:</strong> 
                        • Nilai 1 → lebih banyak MERAH (sensitif)
                        • Nilai 2+ → MERAH hanya jika benar-benar kluster
                    </div>
                    <input type="number" id="min_neighbors" value="{current_preset['min_stressed_neighbors']}" step="1" min="1">
                </div>
            </div>
        </div>
        
        <!-- LEGEND -->
        <div class="legend">
            <div class="legend-item">
                <div class="legend-color" style="background:#e74c3c;"></div>
                <span><strong>MERAH (Kluster):</strong> Core suspect + ≥{current_preset['min_stressed_neighbors']} tetangga stres → Sanitasi</span>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background:#e67e22;"></div>
                <span><strong>ORANYE (Indikasi):</strong> Core suspect + 1 tetangga → Trichoderma</span>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background:#27ae60;"></div>
                <span><strong>HIJAU (Sehat):</strong> Tidak ada anomali → Monitoring</span>
            </div>
        </div>
        
        <!-- SUMMARY STATS -->
        <div class="section">
            <h2>📊 RINGKASAN GANODERMA + PRODUKTIVITAS</h2>
            <div class="stats-grid">
                <div class="stat-card biru">
                    <div class="value biru">{total_trees:,}</div>
                    <div class="label">Total Pohon Dianalisis</div>
                </div>
                <div class="stat-card merah">
                    <div class="value merah">{merah_count:,}</div>
                    <div class="label">🔴 MERAH (Kluster)<br>{merah_count/total_trees*100:.1f}%</div>
                </div>
                <div class="stat-card oranye">
                    <div class="value oranye">{oranye_count:,}</div>
                    <div class="label">🟠 ORANYE (Indikasi)<br>{oranye_count/total_trees*100:.1f}%</div>
                </div>
                <div class="stat-card hijau">
                    <div class="value hijau">{hijau_count:,}</div>
                    <div class="label">🟢 HIJAU (Sehat)<br>{hijau_count/total_trees*100:.1f}%</div>
                </div>
                <div class="stat-card ungu">
                    <div class="value ungu">{avg_yield:.2f}</div>
                    <div class="label">📈 Avg Yield (Ton/Ha)</div>
                </div>
                <div class="stat-card biru">
                    <div class="value biru">{total_prod:,.0f}</div>
                    <div class="label">🏭 Total Produksi (Ton)</div>
                </div>
            </div>
        </div>
        
        <!-- CHARTS -->
        <div class="section">
            <h2>📈 VISUALISASI SUPERIMPOSE</h2>
            <div class="charts-grid">
                <div class="chart-box">
                    <h3>🥧 Distribusi Status Risiko</h3>
                    <canvas id="pieChart"></canvas>
                </div>
                <div class="chart-box">
                    <h3>📊 Top 10 Blok: % Serangan vs Yield</h3>
                    <canvas id="barChart"></canvas>
                </div>
                <div class="chart-box">
                    <h3>📉 Korelasi Serangan Ganoderma vs Produktivitas</h3>
                    <canvas id="scatterChart"></canvas>
                </div>
                <div class="chart-box">
                    <h3>🔥 Radar Perbandingan Preset</h3>
                    <canvas id="radarChart"></canvas>
                </div>
            </div>
            
            <!-- Correlation Box -->
            <div class="correlation-box">
                <h3>🔬 ANALISIS KORELASI</h3>
                <div class="correlation-value" style="color: {'#e74c3c' if correlation and correlation < 0 else '#27ae60'};">
                    {f'r = {correlation:.3f}' if correlation else 'Data tidak mencukupi'}
                </div>
                <p>
                    {'Korelasi NEGATIF: Semakin tinggi % serangan Ganoderma, semakin RENDAH produktivitas blok' if correlation and correlation < 0 else 
                     ('Korelasi POSITIF: Tidak sesuai ekspektasi, perlu investigasi lanjut' if correlation and correlation > 0 else
                      'Perlu lebih banyak data untuk analisis korelasi yang valid')}
                </p>
            </div>
        </div>
        
        <!-- INTEGRATED TABLE -->
        <div class="section">
            <h2>🏆 TOP 10 BLOK BERISIKO + DAMPAK PRODUKTIVITAS</h2>
            <p style="color:#888;margin-bottom:20px;">
                Blok diurutkan berdasarkan persentase serangan Ganoderma. Kolom Yield menunjukkan produktivitas aktual.
            </p>
            <table class="integrated-table">
                <thead>
                    <tr>
                        <th>Rank</th>
                        <th>Blok</th>
                        <th>Total Pohon</th>
                        <th>🔴 MERAH</th>
                        <th>🟠 ORANYE</th>
                        <th>% Serangan</th>
                        <th>Yield (Ton/Ha)</th>
                        <th>Status Produktivitas</th>
                    </tr>
                </thead>
                <tbody>
"""
    
    # Add table rows
    for i, (_, row) in enumerate(top_risk.iterrows()):
        yield_val = row.get('Yield_TonHa', 0) or 0
        yield_status = "🟢 Tinggi" if yield_val > avg_yield else ("🟡 Sedang" if yield_val > avg_yield * 0.7 else "🔴 Rendah")
        
        html += f"""
                    <tr>
                        <td><span class="rank">#{i+1}</span></td>
                        <td><strong>{row['Blok']}</strong></td>
                        <td>{int(row['Total']):,}</td>
                        <td style="color:#e74c3c;">{int(row.get('MERAH', 0)):,}</td>
                        <td style="color:#e67e22;">{int(row.get('ORANYE', 0)):,}</td>
                        <td style="color:#ff6b6b;font-weight:bold;">{row['Pct_Attack']:.1f}%</td>
                        <td>{yield_val:.2f}</td>
                        <td>{yield_status}</td>
                    </tr>
"""
    
    html += f"""
                </tbody>
            </table>
        </div>
        
        <div class="footer">
            <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>Dashboard Terpadu Cincin Api + Produktivitas v3.0 | Method: Z-Score Spatial Filter</p>
            <p>Preset: {preset_name.upper()} | Z-Core: {current_preset['z_threshold_core']} | Z-Neighbor: {current_preset['z_threshold_neighbor']} | Min Neighbors: {current_preset['min_stressed_neighbors']}</p>
        </div>
    </div>
    
    <script>
        const presets = {presets_json};
        
        function updateFromPreset() {{
            const p = presets[document.getElementById('preset').value];
            document.getElementById('z_core').value = p.z_threshold_core;
            document.getElementById('z_neighbor').value = p.z_threshold_neighbor;
            document.getElementById('min_neighbors').value = p.min_stressed_neighbors;
        }}
        
        // Pie Chart
        new Chart(document.getElementById('pieChart'), {{
            type: 'doughnut',
            data: {{
                labels: ['MERAH (Kluster)', 'ORANYE (Indikasi)', 'HIJAU (Sehat)'],
                datasets: [{{
                    data: [{merah_count}, {oranye_count}, {hijau_count}],
                    backgroundColor: ['#e74c3c', '#e67e22', '#27ae60'],
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
        
        // Bar Chart - Attack vs Yield
        new Chart(document.getElementById('barChart'), {{
            type: 'bar',
            data: {{
                labels: {top_blocks_labels},
                datasets: [
                    {{
                        label: '% Serangan',
                        data: {top_blocks_attack},
                        backgroundColor: 'rgba(231, 76, 60, 0.8)',
                        yAxisID: 'y'
                    }},
                    {{
                        label: 'Yield (Ton/Ha)',
                        data: {top_blocks_yield},
                        backgroundColor: 'rgba(39, 174, 96, 0.8)',
                        yAxisID: 'y1'
                    }}
                ]
            }},
            options: {{
                responsive: true,
                scales: {{
                    y: {{
                        type: 'linear',
                        position: 'left',
                        title: {{ display: true, text: '% Serangan', color: '#fff' }},
                        ticks: {{ color: '#fff' }}
                    }},
                    y1: {{
                        type: 'linear',
                        position: 'right',
                        title: {{ display: true, text: 'Yield (Ton/Ha)', color: '#fff' }},
                        ticks: {{ color: '#fff' }},
                        grid: {{ drawOnChartArea: false }}
                    }},
                    x: {{ ticks: {{ color: '#fff' }} }}
                }},
                plugins: {{ legend: {{ labels: {{ color: '#fff' }} }} }}
            }}
        }});
        
        // Scatter Chart - Correlation
        const scatterData = {json.dumps([{'x': row['Pct_Attack'], 'y': row.get('Yield_TonHa', 0) or 0} for _, row in integrated.iterrows() if row.get('Yield_TonHa', 0)])};
        new Chart(document.getElementById('scatterChart'), {{
            type: 'scatter',
            data: {{
                datasets: [{{
                    label: 'Blok',
                    data: scatterData,
                    backgroundColor: 'rgba(155, 89, 182, 0.6)',
                    borderColor: 'rgba(155, 89, 182, 1)',
                    pointRadius: 8
                }}]
            }},
            options: {{
                responsive: true,
                scales: {{
                    x: {{
                        title: {{ display: true, text: '% Serangan Ganoderma', color: '#fff' }},
                        ticks: {{ color: '#fff' }}
                    }},
                    y: {{
                        title: {{ display: true, text: 'Yield (Ton/Ha)', color: '#fff' }},
                        ticks: {{ color: '#fff' }}
                    }}
                }},
                plugins: {{ legend: {{ labels: {{ color: '#fff' }} }} }}
            }}
        }});
        
        // Radar Chart - Preset Comparison
        new Chart(document.getElementById('radarChart'), {{
            type: 'radar',
            data: {{
                labels: ['Z-Core', 'Z-Neighbor', 'Min Neighbors', 'Sensitivitas', 'Presisi'],
                datasets: [
                    {{
                        label: 'Konservatif',
                        data: [Math.abs(presets.konservatif.z_threshold_core), Math.abs(presets.konservatif.z_threshold_neighbor), presets.konservatif.min_stressed_neighbors, 3, 9],
                        borderColor: '#3498db',
                        backgroundColor: 'rgba(52, 152, 219, 0.2)'
                    }},
                    {{
                        label: 'Standar',
                        data: [Math.abs(presets.standar.z_threshold_core), Math.abs(presets.standar.z_threshold_neighbor), presets.standar.min_stressed_neighbors, 6, 6],
                        borderColor: '#27ae60',
                        backgroundColor: 'rgba(39, 174, 96, 0.2)'
                    }},
                    {{
                        label: 'Agresif',
                        data: [Math.abs(presets.agresif.z_threshold_core), Math.abs(presets.agresif.z_threshold_neighbor), presets.agresif.min_stressed_neighbors, 9, 3],
                        borderColor: '#e74c3c',
                        backgroundColor: 'rgba(231, 76, 60, 0.2)'
                    }}
                ]
            }},
            options: {{
                responsive: true,
                scales: {{
                    r: {{
                        ticks: {{ color: '#fff' }},
                        grid: {{ color: 'rgba(255,255,255,0.2)' }},
                        pointLabels: {{ color: '#fff' }}
                    }}
                }},
                plugins: {{ legend: {{ labels: {{ color: '#fff' }} }} }}
            }}
        }});
    </script>
</body>
</html>
"""
    
    html_path = output_dir / 'dashboard_terpadu.html'
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    logging.info(f"Dashboard generated: {html_path}")
    return html_path

def main():
    print('=' * 80)
    print('DASHBOARD TERPADU CINCIN API + PRODUKTIVITAS v3.0')
    print('=' * 80)
    
    print('\n[1/5] Loading Ganoderma data...')
    df = load_and_clean_data(Path('data/input/tabelNDREnew.csv'))
    print(f'  Loaded: {len(df):,} trees')
    
    print('\n[2/5] Loading Productivity data...')
    prod_df = load_productivity_data()
    
    print('\n[3/5] Running Z-Score analysis (Standar preset)...')
    df = run_zscore_analysis(df, 'standar')
    
    merah = len(df[df['Status']=='MERAH'])
    oranye = len(df[df['Status']=='ORANYE'])
    hijau = len(df[df['Status']=='HIJAU'])
    print(f'  MERAH: {merah:,} | ORANYE: {oranye:,} | HIJAU: {hijau:,}')
    
    print('\n[4/5] Generating integrated dashboard...')
    html_path = generate_integrated_dashboard(df, prod_df, 'standar', output_dir)
    
    print('\n[5/5] Saving results...')
    df.to_csv(output_dir / 'hasil_zscore.csv', index=False)
    
    print(f'\n{"="*80}')
    print('✅ DASHBOARD TERPADU BERHASIL DIBUAT!')
    print(f'{"="*80}')
    print(f'\n📁 Output: {output_dir}')
    print(f'🌐 Dashboard: {html_path}')
    
    return html_path

if __name__ == '__main__':
    html_path = main()
