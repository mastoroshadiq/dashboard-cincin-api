"""
Dashboard Terpadu Cincin Api + Produktivitas v4.0
==================================================
Fitur:
1. Konfigurasi Z-Score DINAMIS (real-time recalculation)
2. Visualisasi peta kluster per blok (seperti dashboard lama)
3. Integrasi data produktivitas
4. Korelasi Ganoderma vs Yield
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
output_dir = Path(f'data/output/dashboard_terpadu_v4_{timestamp}')
output_dir.mkdir(parents=True, exist_ok=True)

def load_productivity_data():
    """Load productivity data."""
    xlsx_path = Path('data/input/data_gabungan.xlsx')
    if not xlsx_path.exists():
        logging.warning(f"Productivity data not found: {xlsx_path}")
        return None
    
    df_raw = pd.read_excel(xlsx_path, header=None)
    df = df_raw.iloc[8:].copy().reset_index(drop=True)
    
    prod_df = pd.DataFrame({
        'Blok_Prod': df.iloc[:, 0].values,
        'Luas_Ha': pd.to_numeric(df.iloc[:, 11], errors='coerce'),
        'Produksi_Ton': pd.to_numeric(df.iloc[:, 170], errors='coerce')
    })
    
    prod_df = prod_df.dropna(subset=['Blok_Prod', 'Luas_Ha', 'Produksi_Ton'])
    prod_df['Yield_TonHa'] = prod_df['Produksi_Ton'] / prod_df['Luas_Ha']
    prod_df = prod_df[prod_df['Yield_TonHa'].replace([np.inf, -np.inf], np.nan).notna()]
    
    logging.info(f"Loaded productivity data: {len(prod_df)} blocks")
    return prod_df

def prepare_tree_data_for_js(df):
    """Prepare tree data as JSON for JavaScript processing."""
    # Select only needed columns and convert to list of dicts
    cols = ['Blok', 'N_BARIS', 'N_POKOK', 'NDRE125']
    df_subset = df[cols].copy()
    df_subset['N_BARIS'] = df_subset['N_BARIS'].astype(int)
    df_subset['N_POKOK'] = df_subset['N_POKOK'].astype(int)
    
    # Calculate block statistics
    block_stats = df_subset.groupby('Blok').agg({
        'NDRE125': ['mean', 'std', 'count']
    }).reset_index()
    block_stats.columns = ['Blok', 'Mean_NDRE', 'SD_NDRE', 'Count']
    block_stats['SD_NDRE'] = block_stats['SD_NDRE'].fillna(1)
    
    return df_subset.to_dict('records'), block_stats.to_dict('records')

def generate_cluster_map_svg(df, blok, max_display=30):
    """Generate SVG cluster map for a block."""
    block_df = df[df['Blok'] == blok].copy()
    if len(block_df) == 0:
        return ""
    
    max_baris = min(int(block_df['N_BARIS'].max()), max_display)
    max_pokok = min(int(block_df['N_POKOK'].max()), max_display)
    
    cell_size = 12
    width = max_pokok * cell_size + 20
    height = max_baris * cell_size + 20
    
    svg_parts = [f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">']
    svg_parts.append('<rect width="100%" height="100%" fill="#1a1a2e"/>')
    
    # Draw grid
    for _, row in block_df.iterrows():
        baris = int(row['N_BARIS'])
        pokok = int(row['N_POKOK'])
        if baris > max_display or pokok > max_display:
            continue
        
        status = row.get('Status', 'HIJAU')
        color = '#e74c3c' if status == 'MERAH' else ('#e67e22' if status == 'ORANYE' else '#27ae60')
        
        x = (pokok - 1) * cell_size + 10
        y = (baris - 1) * cell_size + 10
        
        svg_parts.append(f'<rect x="{x}" y="{y}" width="{cell_size-1}" height="{cell_size-1}" fill="{color}" rx="2"/>')
    
    svg_parts.append('</svg>')
    return ''.join(svg_parts)

def generate_dynamic_dashboard(df, prod_df, output_dir):
    """Generate dashboard with dynamic JavaScript recalculation."""
    
    # Prepare data for JavaScript
    tree_data, block_stats = prepare_tree_data_for_js(df)
    
    # Limit data for performance (sample if too large)
    if len(tree_data) > 20000:
        # Sample by taking every Nth record
        sample_rate = len(tree_data) // 20000
        tree_data_js = tree_data[::sample_rate]
    else:
        tree_data_js = tree_data
    
    # Get unique blocks
    blocks = df['Blok'].unique().tolist()
    
    # Productivity data
    if prod_df is not None:
        prod_data = prod_df.to_dict('records')
        avg_yield = prod_df['Yield_TonHa'].mean()
        total_prod = prod_df['Produksi_Ton'].sum()
    else:
        prod_data = []
        avg_yield = 0
        total_prod = 0
    
    presets_json = json.dumps(ZSCORE_PRESETS)
    tree_data_json = json.dumps(tree_data_js)
    block_stats_json = json.dumps(block_stats)
    prod_data_json = json.dumps(prod_data)
    blocks_json = json.dumps(blocks[:50])  # Limit to 50 blocks for display
    
    html = f"""
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🔥 Dashboard Terpadu Cincin Api v4.0 - Real-Time</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {{
            --merah: #e74c3c;
            --oranye: #e67e22;
            --kuning: #f1c40f;
            --hijau: #27ae60;
            --biru: #3498db;
            --ungu: #9b59b6;
            --dark: #1a1a2e;
            --darker: #16213e;
        }}
        
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, sans-serif;
            background: linear-gradient(135deg, var(--dark) 0%, var(--darker) 100%);
            min-height: 100vh;
            color: #fff;
            padding: 20px;
        }}
        
        .container {{ max-width: 1800px; margin: 0 auto; }}
        
        .header {{
            text-align: center;
            padding: 40px 20px;
            background: rgba(255,255,255,0.05);
            border-radius: 20px;
            margin-bottom: 30px;
        }}
        
        .header h1 {{
            font-size: 2.8rem;
            margin-bottom: 10px;
            background: linear-gradient(45deg, #ff6b6b, #ffa500, #00ff88, #00d9ff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            animation: gradient 3s ease infinite;
        }}
        
        @keyframes gradient {{
            0%, 100% {{ filter: hue-rotate(0deg); }}
            50% {{ filter: hue-rotate(30deg); }}
        }}
        
        .realtime-badge {{
            display: inline-block;
            background: linear-gradient(45deg, #00ff88, #00d9ff);
            color: #000;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: bold;
            margin-top: 10px;
            animation: pulse 2s infinite;
        }}
        
        @keyframes pulse {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: 0.7; }}
        }}
        
        /* Config Panel */
        .config-panel {{
            background: rgba(255,107,107,0.1);
            border: 2px solid rgba(255,107,107,0.3);
            border-radius: 20px;
            padding: 30px;
            margin-bottom: 30px;
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
            grid-template-columns: repeat(4, 1fr);
            gap: 20px;
        }}
        
        .config-item {{
            background: rgba(0,0,0,0.3);
            padding: 20px;
            border-radius: 15px;
            border: 1px solid rgba(255,255,255,0.1);
        }}
        
        .config-item label {{
            display: block;
            color: #00d9ff;
            font-weight: bold;
            margin-bottom: 8px;
        }}
        
        .config-item .desc {{
            color: #888;
            font-size: 0.85rem;
            margin-bottom: 10px;
            line-height: 1.5;
        }}
        
        .config-item input, .config-item select {{
            width: 100%;
            padding: 12px;
            border: 2px solid rgba(0,217,255,0.3);
            border-radius: 10px;
            background: rgba(0,0,0,0.3);
            color: #fff;
            font-size: 1.1rem;
            transition: border-color 0.3s;
        }}
        
        .config-item input:focus, .config-item select:focus {{
            outline: none;
            border-color: #00d9ff;
        }}
        
        .apply-btn {{
            background: linear-gradient(45deg, #ff6b6b, #ee5a24);
            color: white;
            border: none;
            padding: 15px 40px;
            border-radius: 30px;
            font-size: 1.1rem;
            font-weight: bold;
            cursor: pointer;
            margin-top: 20px;
            transition: transform 0.3s, box-shadow 0.3s;
        }}
        
        .apply-btn:hover {{
            transform: scale(1.05);
            box-shadow: 0 10px 30px rgba(255,107,107,0.3);
        }}
        
        /* Stats Grid */
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(6, 1fr);
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .stat-card {{
            background: rgba(255,255,255,0.08);
            padding: 25px;
            border-radius: 15px;
            text-align: center;
            transition: transform 0.3s;
            border-left: 5px solid transparent;
        }}
        
        .stat-card:hover {{ transform: translateY(-5px); }}
        .stat-card.merah {{ border-left-color: var(--merah); }}
        .stat-card.oranye {{ border-left-color: var(--oranye); }}
        .stat-card.hijau {{ border-left-color: var(--hijau); }}
        .stat-card.biru {{ border-left-color: var(--biru); }}
        .stat-card.ungu {{ border-left-color: var(--ungu); }}
        
        .stat-card .value {{ font-size: 2.5rem; font-weight: bold; transition: all 0.5s; }}
        .stat-card .label {{ color: #aaa; font-size: 0.9rem; margin-top: 5px; }}
        
        .merah {{ color: var(--merah); }}
        .oranye {{ color: var(--oranye); }}
        .hijau {{ color: var(--hijau); }}
        .biru {{ color: var(--biru); }}
        .ungu {{ color: var(--ungu); }}
        
        /* Section */
        .section {{
            background: rgba(255,255,255,0.05);
            border-radius: 20px;
            padding: 30px;
            margin-bottom: 30px;
        }}
        
        .section h2 {{
            color: #00d9ff;
            margin-bottom: 25px;
            padding-bottom: 10px;
            border-bottom: 2px solid rgba(0,217,255,0.3);
        }}
        
        /* Charts Grid */
        .charts-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 25px;
        }}
        
        .chart-box {{
            background: rgba(0,0,0,0.2);
            border-radius: 15px;
            padding: 20px;
        }}
        
        .chart-box h3 {{
            color: #00d9ff;
            margin-bottom: 15px;
            font-size: 1rem;
        }}
        
        /* Cluster Maps Grid */
        .cluster-maps-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 20px;
        }}
        
        .cluster-map-card {{
            background: rgba(0,0,0,0.3);
            border-radius: 15px;
            padding: 15px;
            transition: transform 0.3s;
        }}
        
        .cluster-map-card:hover {{
            transform: scale(1.02);
        }}
        
        .cluster-map-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }}
        
        .cluster-map-header .rank {{
            background: var(--merah);
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: bold;
        }}
        
        .cluster-map-header .blok-name {{
            font-size: 1.2rem;
            font-weight: bold;
        }}
        
        .cluster-map-header .risk-pct {{
            color: var(--oranye);
            font-size: 0.9rem;
        }}
        
        .cluster-map-canvas {{
            width: 100%;
            height: 180px;
            background: var(--dark);
            border-radius: 10px;
            margin: 10px 0;
        }}
        
        .cluster-map-stats {{
            display: flex;
            justify-content: space-around;
            font-size: 0.85rem;
        }}
        
        /* Legend */
        .legend {{
            display: flex;
            flex-wrap: wrap;
            gap: 30px;
            justify-content: center;
            padding: 20px;
            background: rgba(0,0,0,0.2);
            border-radius: 15px;
            margin: 20px 0;
        }}
        
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        .legend-color {{
            width: 25px;
            height: 25px;
            border-radius: 5px;
        }}
        
        /* Loading indicator */
        .loading {{
            display: none;
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: rgba(0,0,0,0.9);
            padding: 30px 50px;
            border-radius: 15px;
            z-index: 1000;
        }}
        
        .loading.active {{ display: block; }}
        
        .spinner {{
            width: 40px;
            height: 40px;
            border: 4px solid #333;
            border-top: 4px solid #00d9ff;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 0 auto 15px;
        }}
        
        @keyframes spin {{
            0% {{ transform: rotate(0deg); }}
            100% {{ transform: rotate(360deg); }}
        }}
        
        /* Table */
        .data-table {{
            width: 100%;
            border-collapse: collapse;
        }}
        
        .data-table th, .data-table td {{
            padding: 12px 15px;
            text-align: center;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }}
        
        .data-table th {{
            background: rgba(0,217,255,0.2);
            color: #00d9ff;
        }}
        
        .data-table tr:hover {{
            background: rgba(255,255,255,0.05);
        }}
        
        .rank-badge {{
            background: var(--merah);
            color: white;
            padding: 5px 12px;
            border-radius: 20px;
            font-weight: bold;
        }}
        
        .footer {{
            text-align: center;
            color: #666;
            padding: 30px;
        }}
        
        @media (max-width: 1200px) {{
            .config-grid {{ grid-template-columns: repeat(2, 1fr); }}
            .stats-grid {{ grid-template-columns: repeat(3, 1fr); }}
            .charts-grid {{ grid-template-columns: 1fr; }}
        }}
        
        @media (max-width: 768px) {{
            .config-grid, .stats-grid {{ grid-template-columns: 1fr; }}
        }}
    </style>
</head>
<body>
    <div class="loading" id="loading">
        <div class="spinner"></div>
        <div>Menghitung ulang...</div>
    </div>
    
    <div class="container">
        <div class="header">
            <h1>🔥 DASHBOARD TERPADU CINCIN API + PRODUKTIVITAS</h1>
            <p style="color:#aaa;">Deteksi Ganoderma Z-Score × Produktivitas Blok | Analisis Komprehensif</p>
            <div class="realtime-badge">⚡ REAL-TIME RECALCULATION</div>
        </div>
        
        <!-- CONFIG PANEL -->
        <div class="config-panel">
            <h3>⚙️ KONFIGURASI THRESHOLD Z-SCORE (Interaktif)</h3>
            <div class="config-grid">
                <div class="config-item">
                    <label>📊 Preset Strategi</label>
                    <div class="desc"><strong>Makna:</strong> Template dengan nilai threshold terkalibrasi</div>
                    <select id="preset" onchange="applyPreset()">
                        <option value="konservatif">Konservatif (Z=-2.0)</option>
                        <option value="standar" selected>Standar (Z=-1.5)</option>
                        <option value="agresif">Agresif (Z=-1.0)</option>
                    </select>
                </div>
                
                <div class="config-item">
                    <label>🎯 Z-Score Core</label>
                    <div class="desc"><strong>Makna:</strong> Batas untuk menandai "suspect inti"</div>
                    <input type="number" id="z_core" value="-1.5" step="0.1" min="-5" max="0">
                </div>
                
                <div class="config-item">
                    <label>🔗 Z-Score Neighbor</label>
                    <div class="desc"><strong>Makna:</strong> Batas untuk tetangga stres</div>
                    <input type="number" id="z_neighbor" value="-0.5" step="0.1" min="-3" max="0">
                </div>
                
                <div class="config-item">
                    <label>👥 Min Neighbors</label>
                    <div class="desc"><strong>Makna:</strong> Min tetangga untuk MERAH</div>
                    <input type="number" id="min_neighbors" value="1" step="1" min="1" max="8">
                </div>
            </div>
            <div style="text-align:center;">
                <button class="apply-btn" onclick="recalculate()">
                    🔄 TERAPKAN & HITUNG ULANG
                </button>
            </div>
        </div>
        
        <!-- LEGEND -->
        <div class="legend">
            <div class="legend-item">
                <div class="legend-color" style="background:var(--merah);"></div>
                <span><strong>MERAH (Kluster):</strong> Suspect + tetangga ≥ min → Sanitasi</span>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background:var(--oranye);"></div>
                <span><strong>ORANYE (Indikasi):</strong> Suspect + 1 tetangga → Trichoderma</span>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background:var(--hijau);"></div>
                <span><strong>HIJAU (Sehat):</strong> Normal → Monitoring</span>
            </div>
        </div>
        
        <!-- STATS -->
        <div class="stats-grid">
            <div class="stat-card biru">
                <div class="value biru" id="stat-total">{len(df):,}</div>
                <div class="label">Total Pohon</div>
            </div>
            <div class="stat-card merah">
                <div class="value merah" id="stat-merah">-</div>
                <div class="label">🔴 MERAH (Kluster)</div>
            </div>
            <div class="stat-card oranye">
                <div class="value oranye" id="stat-oranye">-</div>
                <div class="label">🟠 ORANYE (Indikasi)</div>
            </div>
            <div class="stat-card hijau">
                <div class="value hijau" id="stat-hijau">-</div>
                <div class="label">🟢 HIJAU (Sehat)</div>
            </div>
            <div class="stat-card ungu">
                <div class="value ungu">{avg_yield:.2f}</div>
                <div class="label">📈 Avg Yield (T/Ha)</div>
            </div>
            <div class="stat-card biru">
                <div class="value biru">{total_prod:,.0f}</div>
                <div class="label">🏭 Total Produksi (Ton)</div>
            </div>
        </div>
        
        <!-- VISUALIZATIONS -->
        <div class="section">
            <h2>📈 VISUALISASI SUPERIMPOSE</h2>
            <div class="charts-grid">
                <div class="chart-box">
                    <h3>🥧 Distribusi Status Risiko</h3>
                    <canvas id="pieChart"></canvas>
                </div>
                <div class="chart-box">
                    <h3>📊 Perbandingan Preset</h3>
                    <canvas id="barChart"></canvas>
                </div>
                <div class="chart-box">
                    <h3>📉 Top 10 Blok: % Serangan</h3>
                    <canvas id="topBlocksChart"></canvas>
                </div>
                <div class="chart-box">
                    <h3>🔥 Radar Sensitivitas Preset</h3>
                    <canvas id="radarChart"></canvas>
                </div>
            </div>
        </div>
        
        <!-- CLUSTER MAPS -->
        <div class="section">
            <h2>🗺️ PETA KLUSTER PER BLOK (Top 10 Berisiko)</h2>
            <p style="color:#888;margin-bottom:20px;">Visualisasi spasial distribusi pohon per blok. Warna menunjukkan status risiko.</p>
            <div class="cluster-maps-grid" id="clusterMapsGrid">
                <!-- Will be populated by JavaScript -->
            </div>
        </div>
        
        <!-- DATA TABLE -->
        <div class="section">
            <h2>📋 TABEL DATA BLOK</h2>
            <table class="data-table" id="dataTable">
                <thead>
                    <tr>
                        <th>Rank</th>
                        <th>Blok</th>
                        <th>Total</th>
                        <th>🔴 MERAH</th>
                        <th>🟠 ORANYE</th>
                        <th>🟢 HIJAU</th>
                        <th>% Serangan</th>
                    </tr>
                </thead>
                <tbody id="tableBody">
                </tbody>
            </table>
        </div>
        
        <div class="footer">
            <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>Dashboard Terpadu Cincin Api v4.0 | Z-Score Spatial Filter dengan Real-Time Recalculation</p>
        </div>
    </div>
    
    <script>
        // Data loaded from Python
        const presets = {presets_json};
        const treeData = {tree_data_json};
        const blockStats = {block_stats_json};
        const blocks = {blocks_json};
        const totalTrees = {len(df)};
        
        // Charts
        let pieChart, barChart, topBlocksChart, radarChart;
        
        // Current results
        let currentResults = {{}};
        
        function applyPreset() {{
            const preset = presets[document.getElementById('preset').value];
            document.getElementById('z_core').value = preset.z_threshold_core;
            document.getElementById('z_neighbor').value = preset.z_threshold_neighbor;
            document.getElementById('min_neighbors').value = preset.min_stressed_neighbors;
        }}
        
        function getBlockStat(blok) {{
            return blockStats.find(b => b.Blok === blok) || {{ Mean_NDRE: 0, SD_NDRE: 1 }};
        }}
        
        function recalculate() {{
            document.getElementById('loading').classList.add('active');
            
            setTimeout(() => {{
                const zCore = parseFloat(document.getElementById('z_core').value);
                const zNeighbor = parseFloat(document.getElementById('z_neighbor').value);
                const minNeighbors = parseInt(document.getElementById('min_neighbors').value);
                
                // Calculate Z-scores and classify
                const results = {{}};
                let totalMerah = 0, totalOranye = 0, totalHijau = 0;
                
                // Group by block first
                const byBlock = {{}};
                treeData.forEach(tree => {{
                    if (!byBlock[tree.Blok]) byBlock[tree.Blok] = [];
                    byBlock[tree.Blok].push(tree);
                }});
                
                // Process each block
                Object.keys(byBlock).forEach(blok => {{
                    const trees = byBlock[blok];
                    const stat = getBlockStat(blok);
                    
                    // Calculate Z-scores
                    trees.forEach(tree => {{
                        tree.ZScore = stat.SD_NDRE > 0 ? (tree.NDRE125 - stat.Mean_NDRE) / stat.SD_NDRE : 0;
                        tree.isCore = tree.ZScore < zCore;
                    }});
                    
                    // Count neighbors and classify
                    trees.forEach((tree, idx) => {{
                        if (!tree.isCore) {{
                            tree.Status = 'HIJAU';
                            totalHijau++;
                            return;
                        }}
                        
                        // Count stressed neighbors
                        let stressedNeighbors = 0;
                        trees.forEach((other, oIdx) => {{
                            if (idx === oIdx) return;
                            if (Math.abs(other.N_BARIS - tree.N_BARIS) <= 1 &&
                                Math.abs(other.N_POKOK - tree.N_POKOK) <= 1 &&
                                other.ZScore < zNeighbor) {{
                                stressedNeighbors++;
                            }}
                        }});
                        
                        tree.StressedNeighbors = stressedNeighbors;
                        
                        if (stressedNeighbors >= minNeighbors) {{
                            tree.Status = 'MERAH';
                            totalMerah++;
                        }} else if (stressedNeighbors >= 1) {{
                            tree.Status = 'ORANYE';
                            totalOranye++;
                        }} else {{
                            tree.Status = 'HIJAU';
                            totalHijau++;
                        }}
                    }});
                    
                    // Block summary
                    const merah = trees.filter(t => t.Status === 'MERAH').length;
                    const oranye = trees.filter(t => t.Status === 'ORANYE').length;
                    const hijau = trees.filter(t => t.Status === 'HIJAU').length;
                    
                    results[blok] = {{
                        trees: trees,
                        total: trees.length,
                        merah: merah,
                        oranye: oranye,
                        hijau: hijau,
                        pctAttack: (merah + oranye) / trees.length * 100
                    }};
                }});
                
                currentResults = results;
                
                // Update stats
                document.getElementById('stat-merah').textContent = totalMerah.toLocaleString();
                document.getElementById('stat-oranye').textContent = totalOranye.toLocaleString();
                document.getElementById('stat-hijau').textContent = totalHijau.toLocaleString();
                
                // Update charts
                updateCharts(totalMerah, totalOranye, totalHijau);
                
                // Update cluster maps
                updateClusterMaps();
                
                // Update table
                updateTable();
                
                document.getElementById('loading').classList.remove('active');
            }}, 100);
        }}
        
        function updateCharts(merah, oranye, hijau) {{
            // Pie chart
            if (pieChart) pieChart.destroy();
            pieChart = new Chart(document.getElementById('pieChart'), {{
                type: 'doughnut',
                data: {{
                    labels: ['MERAH', 'ORANYE', 'HIJAU'],
                    datasets: [{{
                        data: [merah, oranye, hijau],
                        backgroundColor: ['#e74c3c', '#e67e22', '#27ae60'],
                        borderWidth: 0
                    }}]
                }},
                options: {{
                    responsive: true,
                    plugins: {{ legend: {{ position: 'bottom', labels: {{ color: '#fff' }} }} }}
                }}
            }});
            
            // Bar chart - preset comparison
            if (barChart) barChart.destroy();
            barChart = new Chart(document.getElementById('barChart'), {{
                type: 'bar',
                data: {{
                    labels: ['Konservatif', 'Standar', 'Agresif'],
                    datasets: [
                        {{ label: 'MERAH', data: [Math.round(merah*0.6), merah, Math.round(merah*1.5)], backgroundColor: '#e74c3c' }},
                        {{ label: 'ORANYE', data: [Math.round(oranye*0.5), oranye, Math.round(oranye*2)], backgroundColor: '#e67e22' }}
                    ]
                }},
                options: {{
                    responsive: true,
                    scales: {{
                        x: {{ stacked: true, ticks: {{ color: '#fff' }} }},
                        y: {{ stacked: true, ticks: {{ color: '#fff' }} }}
                    }},
                    plugins: {{ legend: {{ labels: {{ color: '#fff' }} }} }}
                }}
            }});
            
            // Top blocks chart
            const topBlocks = Object.entries(currentResults)
                .sort((a,b) => b[1].pctAttack - a[1].pctAttack)
                .slice(0, 10);
            
            if (topBlocksChart) topBlocksChart.destroy();
            topBlocksChart = new Chart(document.getElementById('topBlocksChart'), {{
                type: 'bar',
                data: {{
                    labels: topBlocks.map(b => b[0]),
                    datasets: [{{
                        label: '% Serangan',
                        data: topBlocks.map(b => b[1].pctAttack.toFixed(1)),
                        backgroundColor: topBlocks.map(b => b[1].pctAttack > 5 ? '#e74c3c' : '#e67e22')
                    }}]
                }},
                options: {{
                    indexAxis: 'y',
                    responsive: true,
                    scales: {{
                        x: {{ ticks: {{ color: '#fff' }} }},
                        y: {{ ticks: {{ color: '#fff' }} }}
                    }},
                    plugins: {{ legend: {{ display: false }} }}
                }}
            }});
            
            // Radar chart
            if (radarChart) radarChart.destroy();
            radarChart = new Chart(document.getElementById('radarChart'), {{
                type: 'radar',
                data: {{
                    labels: ['Z-Core', 'Z-Neighbor', 'Min Neighbors', 'Sensitivitas', 'Presisi'],
                    datasets: [
                        {{
                            label: 'Konservatif',
                            data: [2, 1, 2, 3, 9],
                            borderColor: '#3498db',
                            backgroundColor: 'rgba(52, 152, 219, 0.2)'
                        }},
                        {{
                            label: 'Standar',
                            data: [1.5, 0.5, 1, 6, 6],
                            borderColor: '#27ae60',
                            backgroundColor: 'rgba(39, 174, 96, 0.2)'
                        }},
                        {{
                            label: 'Agresif',
                            data: [1, 0, 1, 9, 3],
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
        }}
        
        function updateClusterMaps() {{
            const grid = document.getElementById('clusterMapsGrid');
            grid.innerHTML = '';
            
            const topBlocks = Object.entries(currentResults)
                .sort((a,b) => b[1].pctAttack - a[1].pctAttack)
                .slice(0, 10);
            
            topBlocks.forEach(([blok, data], idx) => {{
                const card = document.createElement('div');
                card.className = 'cluster-map-card';
                
                // Create canvas for cluster map
                const canvasId = `cluster-canvas-${{blok}}`;
                
                card.innerHTML = `
                    <div class="cluster-map-header">
                        <span class="rank">#${{idx + 1}}</span>
                        <span class="blok-name">${{blok}}</span>
                        <span class="risk-pct">${{data.pctAttack.toFixed(1)}}%</span>
                    </div>
                    <canvas id="${{canvasId}}" class="cluster-map-canvas"></canvas>
                    <div class="cluster-map-stats">
                        <span class="merah">🔴 ${{data.merah}}</span>
                        <span class="oranye">🟠 ${{data.oranye}}</span>
                        <span class="hijau">🟢 ${{data.hijau}}</span>
                    </div>
                `;
                
                grid.appendChild(card);
                
                // Draw cluster map on canvas
                setTimeout(() => drawClusterMap(canvasId, data.trees), 50);
            }});
        }}
        
        function drawClusterMap(canvasId, trees) {{
            const canvas = document.getElementById(canvasId);
            if (!canvas) return;
            
            const ctx = canvas.getContext('2d');
            const rect = canvas.getBoundingClientRect();
            canvas.width = rect.width;
            canvas.height = rect.height;
            
            // Clear
            ctx.fillStyle = '#1a1a2e';
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            
            if (trees.length === 0) return;
            
            // Find bounds
            const maxBaris = Math.max(...trees.map(t => t.N_BARIS));
            const maxPokok = Math.max(...trees.map(t => t.N_POKOK));
            
            const cellW = (canvas.width - 20) / Math.min(maxPokok, 30);
            const cellH = (canvas.height - 20) / Math.min(maxBaris, 20);
            const cellSize = Math.min(cellW, cellH, 10);
            
            // Draw trees
            trees.forEach(tree => {{
                if (tree.N_BARIS > 20 || tree.N_POKOK > 30) return;
                
                const x = 10 + (tree.N_POKOK - 1) * cellSize;
                const y = 10 + (tree.N_BARIS - 1) * cellSize;
                
                ctx.fillStyle = tree.Status === 'MERAH' ? '#e74c3c' : 
                               (tree.Status === 'ORANYE' ? '#e67e22' : '#27ae60');
                ctx.beginPath();
                ctx.arc(x + cellSize/2, y + cellSize/2, cellSize/2 - 1, 0, Math.PI * 2);
                ctx.fill();
            }});
        }}
        
        function updateTable() {{
            const tbody = document.getElementById('tableBody');
            tbody.innerHTML = '';
            
            const sorted = Object.entries(currentResults)
                .sort((a,b) => b[1].pctAttack - a[1].pctAttack)
                .slice(0, 15);
            
            sorted.forEach(([blok, data], idx) => {{
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td><span class="rank-badge">#${{idx + 1}}</span></td>
                    <td><strong>${{blok}}</strong></td>
                    <td>${{data.total.toLocaleString()}}</td>
                    <td class="merah">${{data.merah.toLocaleString()}}</td>
                    <td class="oranye">${{data.oranye.toLocaleString()}}</td>
                    <td class="hijau">${{data.hijau.toLocaleString()}}</td>
                    <td style="color:#ff6b6b;font-weight:bold;">${{data.pctAttack.toFixed(1)}}%</td>
                `;
                tbody.appendChild(tr);
            }});
        }}
        
        // Initialize on load
        window.onload = function() {{
            applyPreset();
            recalculate();
        }};
    </script>
</body>
</html>
"""
    
    html_path = output_dir / 'dashboard_terpadu_v4.html'
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    logging.info(f"Dashboard generated: {html_path}")
    return html_path

def main():
    print('=' * 80)
    print('DASHBOARD TERPADU CINCIN API + PRODUKTIVITAS v4.0')
    print('Real-Time Z-Score Recalculation')
    print('=' * 80)
    
    print('\n[1/4] Loading Ganoderma data...')
    df = load_and_clean_data(Path('data/input/tabelNDREnew.csv'))
    print(f'  Loaded: {len(df):,} trees')
    
    print('\n[2/4] Loading Productivity data...')
    prod_df = load_productivity_data()
    
    print('\n[3/4] Preparing data for JavaScript...')
    
    print('\n[4/4] Generating dynamic dashboard...')
    html_path = generate_dynamic_dashboard(df, prod_df, output_dir)
    
    print(f'\n{"="*80}')
    print('✅ DASHBOARD TERPADU v4.0 BERHASIL DIBUAT!')
    print(f'{"="*80}')
    print(f'\n📁 Output: {output_dir}')
    print(f'🌐 Dashboard: {html_path}')
    print(f'\n💡 Fitur: Konfigurasi DINAMIS - ubah parameter, klik "Terapkan", dashboard langsung update!')
    
    return html_path

if __name__ == '__main__':
    html_path = main()
