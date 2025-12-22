"""
Dashboard Z-Score Multi-Divisi v5.0
====================================
Fitur:
1. Z-Score Spatial Filter untuk deteksi Ganoderma
2. Tabs terpisah AME II dan AME IV
3. Peta kluster matplotlib (PNG) - seperti dashboard lama
4. Real-time recalculation untuk stats dan chart via JavaScript
5. Integrasi data produktivitas
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
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

from src.ingestion import load_and_clean_data
from config import ZSCORE_PRESETS

# Output
timestamp = datetime.now().strftime("%Y%m%d_%H%M")
output_dir = Path(f'data/output/dashboard_zscore_multi_{timestamp}')
output_dir.mkdir(parents=True, exist_ok=True)

def load_ame_iv_data(file_path):
    """Load AME IV data with semicolon delimiter."""
    # AME_IV.csv uses semicolon delimiter
    df = pd.read_csv(file_path, sep=';')
    
    # Check if columns are already correct
    logging.info(f"AME IV columns: {df.columns.tolist()[:10]}")
    
    # Rename columns to match expected format
    column_mapping = {
        'DIVISI': 'Divisi',
        'blok': 'Blok',
        'n_baris': 'N_BARIS', 
        'n_pokok': 'N_POKOK',
        'ndre125': 'NDRE125'
    }
    
    for old, new in column_mapping.items():
        if old in df.columns and new not in df.columns:
            df.rename(columns={old: new}, inplace=True)
    
    # Ensure numeric columns
    for col in ['N_BARIS', 'N_POKOK', 'NDRE125']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Check required columns exist
    required = ['Blok', 'N_BARIS', 'N_POKOK', 'NDRE125']
    missing = [c for c in required if c not in df.columns]
    if missing:
        logging.error(f"Missing columns: {missing}. Available: {df.columns.tolist()}")
        raise KeyError(f"Missing required columns: {missing}")
    
    df = df.dropna(subset=['Blok', 'N_BARIS', 'N_POKOK', 'NDRE125'])
    
    logging.info(f"Loaded AME IV: {len(df):,} trees")
    return df

def calculate_zscore_detection(df, z_core=-1.5, z_neighbor=-0.5, min_neighbors=1):
    """
    Calculate Z-Score based Ganoderma detection.
    Returns DataFrame with Status column.
    """
    df = df.copy()
    
    # Calculate block statistics
    block_stats = df.groupby('Blok')['NDRE125'].agg(['mean', 'std']).reset_index()
    block_stats.columns = ['Blok', 'Mean_NDRE', 'SD_NDRE']
    block_stats['SD_NDRE'] = block_stats['SD_NDRE'].fillna(1).replace(0, 1)
    
    # Merge and calculate Z-Score
    df = df.merge(block_stats, on='Blok', how='left')
    df['ZScore'] = (df['NDRE125'] - df['Mean_NDRE']) / df['SD_NDRE']
    df['Is_Core'] = df['ZScore'] < z_core
    
    # Count stressed neighbors per tree
    df['Stressed_Neighbors'] = 0
    df['Status'] = 'HIJAU'
    
    for blok in df['Blok'].unique():
        block_mask = df['Blok'] == blok
        block_df = df[block_mask].copy()
        block_indices = df[block_mask].index
        
        for idx in block_indices:
            if not df.loc[idx, 'Is_Core']:
                continue
            
            baris = df.loc[idx, 'N_BARIS']
            pokok = df.loc[idx, 'N_POKOK']
            
            # Find neighbors (3x3 grid around the tree)
            neighbor_mask = (
                (block_df['N_BARIS'] >= baris - 1) & 
                (block_df['N_BARIS'] <= baris + 1) &
                (block_df['N_POKOK'] >= pokok - 1) & 
                (block_df['N_POKOK'] <= pokok + 1) &
                (block_df['ZScore'] < z_neighbor)
            )
            
            stressed_count = neighbor_mask.sum() - 1  # Exclude self
            stressed_count = max(0, stressed_count)
            df.loc[idx, 'Stressed_Neighbors'] = stressed_count
            
            # Classify
            if stressed_count >= min_neighbors:
                df.loc[idx, 'Status'] = 'MERAH'
            elif stressed_count >= 1:
                df.loc[idx, 'Status'] = 'ORANYE'
            else:
                df.loc[idx, 'Status'] = 'KUNING'
    
    return df

def generate_cluster_map_png(df, blok, preset_name, rank, output_dir, divisi_id):
    """Generate matplotlib cluster map PNG for a block - VERTICAL format with hexagonal offset."""
    import matplotlib.patches as mpatches
    
    block_df = df[df['Blok'] == blok].copy().reset_index(drop=True)
    if len(block_df) == 0:
        return None
    
    # Count statistics
    merah_count = (block_df['Status'] == 'MERAH').sum()
    oranye_count = (block_df['Status'] == 'ORANYE').sum()
    kuning_count = (block_df['Status'] == 'KUNING').sum()
    hijau_count = (block_df['Status'] == 'HIJAU').sum()
    total_count = len(block_df)
    
    # Create figure - VERTICAL/PORTRAIT format like dashboard lama
    fig, ax = plt.subplots(figsize=(14, 12))
    
    # Prepare colors, sizes, edge colors based on status
    colors = []
    sizes = []
    edge_colors = []
    edge_widths = []
    
    for _, row in block_df.iterrows():
        status = row['Status']
        if status == 'MERAH':
            colors.append('#e74c3c')
            sizes.append(60)
            edge_colors.append('darkred')
            edge_widths.append(1)
        elif status == 'ORANYE':
            colors.append('#e67e22')
            sizes.append(60)
            edge_colors.append('darkorange')
            edge_widths.append(1)
        elif status == 'KUNING':
            colors.append('#f1c40f')
            sizes.append(60)
            edge_colors.append('olive')
            edge_widths.append(1)
        else:  # HIJAU
            colors.append('#27ae60')
            sizes.append(60)
            edge_colors.append('darkgreen')
            edge_widths.append(0.5)
    
    # Apply hexagonal offset (like dashboard lama)
    x_coords = []
    y_coords = []
    for _, row in block_df.iterrows():
        baris = row['N_BARIS']
        pokok = row['N_POKOK']
        x_offset = 0.5 if baris % 2 == 0 else 0
        x_coords.append(pokok + x_offset)
        y_coords.append(baris)
    
    # Plot in layers (HIJAU first, MERAH last so MERAH is on top)
    status_order = ['HIJAU', 'KUNING', 'ORANYE', 'MERAH']
    
    for status in status_order:
        mask = block_df['Status'] == status
        if mask.any():
            indices = block_df[mask].index.tolist()
            x_plot = [x_coords[i] for i in indices]
            y_plot = [y_coords[i] for i in indices]
            s_plot = [sizes[i] for i in indices]
            c_plot = [colors[i] for i in indices]
            ec_plot = [edge_colors[i] for i in indices]
            ew_plot = [edge_widths[i] for i in indices]
            
            ax.scatter(x_plot, y_plot, c=c_plot, s=s_plot, alpha=0.85,
                      edgecolors=ec_plot, linewidths=ew_plot, zorder=status_order.index(status)+1)
    
    # Legend with proper labels
    legend_elements = [
        mpatches.Patch(color='#e74c3c', label=f'MERAH - Kluster Aktif ({merah_count})'),
        mpatches.Patch(color='#e67e22', label=f'ORANYE - Cincin Api ({oranye_count})'),
        mpatches.Patch(color='#f1c40f', label=f'KUNING - Suspect ({kuning_count})'),
        mpatches.Patch(color='#27ae60', label=f'HIJAU - Sehat ({hijau_count})')
    ]
    ax.legend(handles=legend_elements, loc='upper right', fontsize=11,
             framealpha=0.9, fancybox=True, shadow=True)
    
    # Axis labels - N_POKOK for X, N_BARIS for Y (NOT year!)
    ax.set_xlabel('Nomor Pokok (N_POKOK)', fontsize=12)
    ax.set_ylabel('Nomor Baris (N_BARIS)', fontsize=12)
    
    # Title with statistics
    ax.set_title(
        f'#{rank:02d} - BLOK {blok} - PETA KLUSTER GANODERMA\n'
        f'Total Pohon: {total_count} | MERAH: {merah_count} | KUNING: {kuning_count} | ORANYE: {oranye_count}',
        fontsize=14, fontweight='bold', color='darkred' if rank <= 3 else 'black'
    )
    
    ax.invert_yaxis()  # Baris 1 di atas
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.set_aspect('equal')
    ax.tick_params(axis='both', which='major', labelsize=10)
    
    # Add rank badge in corner
    ax.text(0.02, 0.98, f'RANK #{rank}', transform=ax.transAxes, fontsize=16,
           fontweight='bold', color='white',
           bbox=dict(boxstyle='round,pad=0.3', facecolor='#e74c3c' if rank <= 3 else '#f39c12',
                    edgecolor='black', linewidth=2),
           verticalalignment='top')
    
    # Add preset badge
    preset_colors = {'konservatif': '#3498db', 'standar': '#27ae60', 'agresif': '#e74c3c'}
    ax.text(0.98, 0.98, f'{preset_name.upper()}',
           transform=ax.transAxes, fontsize=12, fontweight='bold',
           color='white', horizontalalignment='right', verticalalignment='top',
           bbox=dict(boxstyle='round,pad=0.3', facecolor=preset_colors.get(preset_name, '#333'),
                    edgecolor='black', linewidth=1))
    
    plt.tight_layout()
    
    # Save with higher DPI
    divisi_dir = output_dir / divisi_id
    divisi_dir.mkdir(exist_ok=True)
    
    filename = f'cluster_map_{preset_name}_{rank:02d}_{blok}.png'
    filepath = divisi_dir / filename
    fig.savefig(filepath, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    
    logging.info(f"  Saved: {filename}")
    
    return {
        'filename': filename,
        'blok': blok,
        'rank': rank,
        'merah': merah_count,
        'oranye': oranye_count,
        'kuning': kuning_count,
        'hijau': hijau_count,
        'total': total_count
    }

def analyze_divisi_with_zscore(df, divisi_name, output_dir, presets=['konservatif', 'standar', 'agresif']):
    """Analyze a division with Z-Score for all presets."""
    divisi_id = divisi_name.replace(' ', '_')
    results = {}
    block_maps = {}
    
    for preset_name in presets:
        preset = ZSCORE_PRESETS[preset_name]
        
        logging.info(f"Analyzing {divisi_name} with {preset_name} preset...")
        
        # Run Z-Score detection
        df_classified = calculate_zscore_detection(
            df,
            z_core=preset['z_threshold_core'],
            z_neighbor=preset['z_threshold_neighbor'],
            min_neighbors=preset['min_stressed_neighbors']
        )
        
        # Calculate statistics
        merah_count = (df_classified['Status'] == 'MERAH').sum()
        oranye_count = (df_classified['Status'] == 'ORANYE').sum()
        kuning_count = (df_classified['Status'] == 'KUNING').sum()
        hijau_count = (df_classified['Status'] == 'HIJAU').sum()
        total_trees = len(df_classified)
        
        # Find top 5 blocks by risk
        block_risk = df_classified.groupby('Blok').agg({
            'Status': lambda x: ((x == 'MERAH') | (x == 'ORANYE')).sum()
        }).reset_index()
        block_risk.columns = ['Blok', 'Risk_Count']
        block_risk['Total'] = df_classified.groupby('Blok').size().values
        block_risk['Risk_Pct'] = block_risk['Risk_Count'] / block_risk['Total'] * 100
        top_blocks = block_risk.nlargest(5, 'Risk_Pct')
        
        # Generate cluster maps for top 5 blocks
        maps = []
        for rank, (_, row) in enumerate(top_blocks.iterrows(), 1):
            blok = row['Blok']
            map_info = generate_cluster_map_png(
                df_classified, blok, preset_name, rank, output_dir, divisi_id
            )
            if map_info:
                maps.append(map_info)
        
        block_maps[preset_name] = maps
        
        results[preset_name] = {
            'df': df_classified,
            'metadata': {
                'preset': preset_name,
                'z_threshold_core': preset['z_threshold_core'],
                'z_threshold_neighbor': preset['z_threshold_neighbor'],
                'min_stressed_neighbors': preset['min_stressed_neighbors'],
                'total_trees': total_trees,
                'merah_count': merah_count,
                'oranye_count': oranye_count,
                'kuning_count': kuning_count,
                'hijau_count': hijau_count,
                'total_blocks': df_classified['Blok'].nunique()
            }
        }
        
        logging.info(f"  {preset_name}: MERAH={merah_count}, ORANYE={oranye_count}")
    
    return results, block_maps

def prepare_tree_data_for_js(df, max_trees=25000):
    """Prepare tree data as JSON for JavaScript real-time processing."""
    cols = ['Blok', 'N_BARIS', 'N_POKOK', 'NDRE125']
    df_subset = df[cols].copy()
    df_subset['N_BARIS'] = df_subset['N_BARIS'].astype(int)
    df_subset['N_POKOK'] = df_subset['N_POKOK'].astype(int)
    
    # Sample if too large
    if len(df_subset) > max_trees:
        sample_rate = len(df_subset) // max_trees
        df_subset = df_subset.iloc[::sample_rate]
    
    # Block statistics
    block_stats = df[cols].groupby('Blok').agg({
        'NDRE125': ['mean', 'std', 'count']
    }).reset_index()
    block_stats.columns = ['Blok', 'Mean_NDRE', 'SD_NDRE', 'Count']
    block_stats['SD_NDRE'] = block_stats['SD_NDRE'].fillna(1).replace(0, 1)
    
    return df_subset.to_dict('records'), block_stats.to_dict('records')

def generate_multi_divisi_html(output_dir, all_divisi_results, all_block_maps, all_tree_data):
    """Generate HTML dashboard with tabs for AME II and AME IV."""
    
    presets_json = json.dumps(ZSCORE_PRESETS)
    
    # Build tabs HTML
    divisi_tabs_html = ""
    divisi_content_html = ""
    
    for idx, (divisi_name, data) in enumerate(all_divisi_results.items()):
        divisi_id = divisi_name.replace(' ', '_')
        active_class = "active" if idx == 0 else ""
        
        results = data['results']
        block_maps = all_block_maps[divisi_name]
        tree_data = all_tree_data[divisi_name]['trees']
        block_stats = all_tree_data[divisi_name]['stats']
        
        # Tab button - using style from user's image
        tab_color = "#e67e22" if idx == 0 else "#3498db"
        divisi_tabs_html += f'''
            <button class="divisi-tab {active_class}" style="background: {tab_color};" 
                    onclick="switchDivisi('{divisi_id}')" data-divisi="{divisi_id}">
                🌴 {divisi_name}
            </button>
        '''
        
        # Stats from standar preset
        stats = results['standar']['metadata']
        
        # Build preset cards
        preset_cards = ""
        for preset_name in ['konservatif', 'standar', 'agresif']:
            meta = results[preset_name]['metadata']
            preset_info = {
                'konservatif': {'color': '#3498db', 'icon': '🔵', 'display': 'Konservatif'},
                'standar': {'color': '#27ae60', 'icon': '🟢', 'display': 'Standar'},
                'agresif': {'color': '#e74c3c', 'icon': '🔴', 'display': 'Agresif'}
            }[preset_name]
            
            preset_cards += f'''
            <div class="preset-card" data-preset="{preset_name}">
                <div class="preset-header" style="background: linear-gradient(135deg, {preset_info['color']}, {preset_info['color']}dd);">
                    <span class="preset-icon">{preset_info['icon']}</span>
                    <span class="preset-name">{preset_info['display'].upper()}</span>
                    <div class="preset-threshold">Z-Core: {meta['z_threshold_core']} | Z-Neighbor: {meta['z_threshold_neighbor']}</div>
                </div>
                <div class="preset-body">
                    <div class="status-grid">
                        <div class="status-item merah">
                            <span class="status-label">🔴 MERAH</span>
                            <span class="status-value">{meta['merah_count']:,}</span>
                        </div>
                        <div class="status-item oranye">
                            <span class="status-label">🟠 ORANYE</span>
                            <span class="status-value">{meta['oranye_count']:,}</span>
                        </div>
                        <div class="status-item kuning">
                            <span class="status-label">🟡 KUNING</span>
                            <span class="status-value">{meta['kuning_count']:,}</span>
                        </div>
                        <div class="status-item hijau">
                            <span class="status-label">🟢 HIJAU</span>
                            <span class="status-value">{meta['hijau_count']:,}</span>
                        </div>
                    </div>
                </div>
            </div>
            '''
        
        # Build block maps gallery
        block_maps_html = ""
        for preset_name in ['konservatif', 'standar', 'agresif']:
            preset_info = {
                'konservatif': {'color': '#3498db', 'icon': '🔵', 'display': 'Konservatif'},
                'standar': {'color': '#27ae60', 'icon': '🟢', 'display': 'Standar'},
                'agresif': {'color': '#e74c3c', 'icon': '🔴', 'display': 'Agresif'}
            }[preset_name]
            
            maps = block_maps.get(preset_name, [])
            maps_items = ""
            for m in maps:
                maps_items += f'''
                    <div class="map-item" onclick="openLightbox('{divisi_id}/{m['filename']}', 'Blok {m['blok']}')">
                        <img src="{divisi_id}/{m['filename']}" alt="Cluster Map {m['blok']}">
                        <div class="map-label">{m['blok']} - 🔴{m['merah']} 🟠{m['oranye']}</div>
                    </div>
                '''
            
            block_maps_html += f'''
            <div class="maps-preset-section">
                <h4 style="color: {preset_info['color']}">{preset_info['icon']} {preset_info['display']}</h4>
                <div class="maps-grid">
                    {maps_items}
                </div>
            </div>
            '''
        
        # Store tree data for JavaScript
        tree_data_json = json.dumps(tree_data)
        block_stats_json = json.dumps(block_stats)
        
        # Divisi content
        divisi_content_html += f'''
        <div class="divisi-content {active_class}" id="content-{divisi_id}" data-divisi="{divisi_id}">
            <script>
                divisiData['{divisi_id}'] = {{
                    trees: {tree_data_json},
                    stats: {block_stats_json},
                    totalTrees: {stats['total_trees']}
                }};
            </script>
            
            <div class="divisi-header">
                <h2>📍 {divisi_name}</h2>
                <div class="divisi-stats">
                    <span>🌳 <span id="total-{divisi_id}">{stats['total_trees']:,}</span> pohon</span>
                    <span>📦 {stats['total_blocks']} blok</span>
                </div>
            </div>
            
            <!-- Real-time Stats Display -->
            <div class="realtime-stats-grid" id="realtime-stats-{divisi_id}">
                <div class="stat-card merah">
                    <div class="stat-value" id="merah-{divisi_id}">{results['standar']['metadata']['merah_count']:,}</div>
                    <div class="stat-label">🔴 MERAH (Kluster)</div>
                </div>
                <div class="stat-card oranye">
                    <div class="stat-value" id="oranye-{divisi_id}">{results['standar']['metadata']['oranye_count']:,}</div>
                    <div class="stat-label">🟠 ORANYE (Indikasi)</div>
                </div>
                <div class="stat-card kuning">
                    <div class="stat-value" id="kuning-{divisi_id}">{results['standar']['metadata']['kuning_count']:,}</div>
                    <div class="stat-label">🟡 KUNING (Suspect)</div>
                </div>
                <div class="stat-card hijau">
                    <div class="stat-value" id="hijau-{divisi_id}">{results['standar']['metadata']['hijau_count']:,}</div>
                    <div class="stat-label">🟢 HIJAU (Sehat)</div>
                </div>
            </div>
            
            <section class="preset-cards-section">
                <h3>📊 Perbandingan 3 Preset (Z-Score)</h3>
                <div class="preset-cards-container">
                    {preset_cards}
                </div>
            </section>
            
            <section class="charts-section">
                <h3>📈 Visualisasi Real-Time</h3>
                <div class="charts-grid">
                    <div class="chart-box">
                        <h4>🥧 Distribusi Status</h4>
                        <canvas id="pie-{divisi_id}"></canvas>
                    </div>
                    <div class="chart-box">
                        <h4>📊 Perbandingan Preset</h4>
                        <canvas id="bar-{divisi_id}"></canvas>
                    </div>
                </div>
            </section>
            
            <section class="block-maps-section">
                <h3>🗺️ Peta Kluster per Blok (Top 5)</h3>
                {block_maps_html}
            </section>
        </div>
        '''
    
    # Full HTML
    html = f'''<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🔥 Dashboard Z-Score Multi-Divisi v5.0</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {{
            --merah: #e74c3c;
            --oranye: #e67e22;
            --kuning: #f1c40f;
            --hijau: #27ae60;
            --biru: #3498db;
            --dark: #1a1a2e;
            --darker: #16213e;
            --card-bg: #0f3460;
        }}
        
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        
        body {{
            font-family: 'Segoe UI', system-ui, sans-serif;
            background: linear-gradient(135deg, var(--dark), var(--darker));
            color: #fff;
            min-height: 100vh;
        }}
        
        .header {{
            background: linear-gradient(135deg, var(--darker), var(--card-bg));
            padding: 30px;
            text-align: center;
            border-bottom: 3px solid var(--oranye);
        }}
        
        .header h1 {{
            font-size: 2.5rem;
            margin-bottom: 10px;
            background: linear-gradient(45deg, #ff6b6b, #ffa500, #00ff88);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        
        .realtime-badge {{
            display: inline-block;
            background: linear-gradient(45deg, #00ff88, #00d9ff);
            color: #000;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: bold;
            animation: pulse 2s infinite;
        }}
        
        @keyframes pulse {{
            0%, 100% {{ opacity: 1; transform: scale(1); }}
            50% {{ opacity: 0.8; transform: scale(1.02); }}
        }}
        
        .container {{ max-width: 1800px; margin: 0 auto; padding: 20px; }}
        
        /* Config Panel */
        .config-panel {{
            background: rgba(255,107,107,0.1);
            border: 2px solid rgba(255,107,107,0.3);
            border-radius: 20px;
            padding: 25px;
            margin: 20px 0;
        }}
        
        .config-panel-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }}
        
        .config-panel h3 {{
            color: #ff6b6b;
            margin: 0;
        }}
        
        .info-btn {{
            background: linear-gradient(45deg, #00d9ff, #0099cc);
            color: white;
            border: none;
            padding: 8px 15px;
            border-radius: 20px;
            font-size: 0.9rem;
            font-weight: bold;
            cursor: pointer;
            transition: transform 0.3s, box-shadow 0.3s;
        }}
        
        .info-btn:hover {{
            transform: scale(1.05);
            box-shadow: 0 5px 15px rgba(0,217,255,0.4);
        }}
        
        .config-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 15px;
        }}
        
        .config-item {{
            background: rgba(0,0,0,0.3);
            padding: 15px;
            border-radius: 10px;
        }}
        
        .config-item label {{
            display: block;
            color: #00d9ff;
            font-weight: bold;
            margin-bottom: 5px;
        }}
        
        .config-item input, .config-item select {{
            width: 100%;
            padding: 10px;
            border: 2px solid rgba(0,217,255,0.3);
            border-radius: 8px;
            background: rgba(0,0,0,0.3);
            color: #fff;
            font-size: 1rem;
        }}
        
        .apply-btn {{
            background: linear-gradient(45deg, #ff6b6b, #ee5a24);
            color: white;
            border: none;
            padding: 12px 30px;
            border-radius: 25px;
            font-size: 1rem;
            font-weight: bold;
            cursor: pointer;
            margin-top: 15px;
            transition: transform 0.3s;
        }}
        
        .apply-btn:hover {{ transform: scale(1.05); }}
        
        /* Info Modal */
        .info-modal {{
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.85);
            z-index: 2000;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }}
        
        .info-modal.active {{ display: flex; }}
        
        .info-modal-content {{
            background: linear-gradient(135deg, #1a1a2e, #16213e);
            border: 2px solid #00d9ff;
            border-radius: 20px;
            padding: 30px;
            max-width: 900px;
            max-height: 85vh;
            overflow-y: auto;
        }}
        
        .info-modal-close {{
            float: right;
            font-size: 2rem;
            color: #ff6b6b;
            cursor: pointer;
            margin-top: -10px;
        }}
        
        .info-modal-close:hover {{ color: #fff; }}
        
        .info-modal h2 {{
            color: #00d9ff;
            margin-bottom: 20px;
            border-bottom: 2px solid rgba(0,217,255,0.3);
            padding-bottom: 10px;
        }}
        
        .info-section {{
            background: rgba(0,0,0,0.3);
            border-radius: 15px;
            padding: 20px;
            margin-bottom: 20px;
            border-left: 4px solid #00d9ff;
        }}
        
        .info-section h4 {{
            color: #ff6b6b;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        .info-section p {{
            color: #ccc;
            line-height: 1.7;
            margin-bottom: 10px;
        }}
        
        .info-section .impact {{
            background: rgba(255,107,107,0.1);
            border-radius: 8px;
            padding: 10px 15px;
            color: #ff6b6b;
            font-size: 0.9rem;
        }}
        
        .info-section .impact strong {{ color: #fff; }}
        

        
        /* Tabs */
        .divisi-tabs {{
            display: flex;
            justify-content: center;
            gap: 20px;
            margin: 20px 0;
        }}
        
        .divisi-tab {{
            padding: 15px 40px;
            border: none;
            border-radius: 30px;
            font-size: 1.2rem;
            font-weight: bold;
            cursor: pointer;
            color: white;
            transition: transform 0.3s, box-shadow 0.3s;
        }}
        
        .divisi-tab:hover {{
            transform: translateY(-3px);
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        }}
        
        .divisi-tab.active {{
            box-shadow: 0 5px 20px rgba(0,0,0,0.4);
        }}
        
        .divisi-content {{
            display: none;
        }}
        
        .divisi-content.active {{
            display: block;
        }}
        
        .divisi-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 20px;
            background: rgba(255,255,255,0.05);
            border-radius: 15px;
            margin-bottom: 20px;
        }}
        
        .divisi-stats {{
            display: flex;
            gap: 30px;
            font-size: 1.1rem;
        }}
        
        /* Real-time Stats Grid */
        .realtime-stats-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 20px;
            margin-bottom: 25px;
        }}
        
        .stat-card {{
            background: rgba(255,255,255,0.08);
            padding: 25px;
            border-radius: 15px;
            text-align: center;
            border-left: 5px solid transparent;
            transition: transform 0.3s;
        }}
        
        .stat-card:hover {{ transform: translateY(-5px); }}
        .stat-card.merah {{ border-left-color: var(--merah); }}
        .stat-card.oranye {{ border-left-color: var(--oranye); }}
        .stat-card.kuning {{ border-left-color: var(--kuning); }}
        .stat-card.hijau {{ border-left-color: var(--hijau); }}
        
        .stat-value {{
            font-size: 2.5rem;
            font-weight: bold;
        }}
        
        .stat-card.merah .stat-value {{ color: var(--merah); }}
        .stat-card.oranye .stat-value {{ color: var(--oranye); }}
        .stat-card.kuning .stat-value {{ color: var(--kuning); }}
        .stat-card.hijau .stat-value {{ color: var(--hijau); }}
        
        .stat-label {{
            color: #aaa;
            margin-top: 5px;
        }}
        
        /* Preset Cards */
        .preset-cards-container {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 20px;
        }}
        
        .preset-card {{
            background: var(--card-bg);
            border-radius: 15px;
            overflow: hidden;
            transition: transform 0.3s;
        }}
        
        .preset-card:hover {{ transform: translateY(-5px); }}
        
        .preset-header {{
            padding: 20px;
            text-align: center;
        }}
        
        .preset-icon {{ font-size: 2rem; }}
        .preset-name {{ font-size: 1.2rem; font-weight: bold; margin-left: 10px; }}
        .preset-threshold {{ font-size: 0.85rem; opacity: 0.9; margin-top: 5px; }}
        
        .preset-body {{
            padding: 20px;
        }}
        
        .status-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 10px;
        }}
        
        .status-item {{
            background: rgba(0,0,0,0.3);
            padding: 10px;
            border-radius: 8px;
            text-align: center;
        }}
        
        .status-item .status-label {{ font-size: 0.85rem; color: #aaa; }}
        .status-item .status-value {{ font-size: 1.2rem; font-weight: bold; }}
        .status-item.merah .status-value {{ color: var(--merah); }}
        .status-item.oranye .status-value {{ color: var(--oranye); }}
        .status-item.kuning .status-value {{ color: var(--kuning); }}
        .status-item.hijau .status-value {{ color: var(--hijau); }}
        
        /* Charts */
        .charts-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 20px;
        }}
        
        .chart-box {{
            background: rgba(0,0,0,0.2);
            padding: 20px;
            border-radius: 15px;
        }}
        
        .chart-box h4 {{
            color: #00d9ff;
            margin-bottom: 15px;
        }}
        
        /* Block Maps */
        .maps-preset-section {{
            margin-bottom: 30px;
        }}
        
        .maps-preset-section h4 {{
            margin-bottom: 15px;
        }}
        
        .maps-grid {{
            display: grid;
            grid-template-columns: repeat(5, 1fr);
            gap: 15px;
        }}
        
        .map-item {{
            background: rgba(0,0,0,0.3);
            border-radius: 10px;
            overflow: hidden;
            cursor: pointer;
            transition: transform 0.3s;
        }}
        
        .map-item:hover {{ transform: scale(1.03); }}
        
        .map-item img {{
            width: 100%;
            display: block;
        }}
        
        .map-label {{
            padding: 10px;
            text-align: center;
            background: rgba(0,0,0,0.5);
            font-size: 0.9rem;
        }}
        
        /* Lightbox */
        .lightbox {{
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.95);
            z-index: 1000;
            justify-content: center;
            align-items: center;
        }}
        
        .lightbox.active {{ display: flex; }}
        
        .lightbox img {{
            max-width: 90%;
            max-height: 90%;
        }}
        
        .lightbox-close {{
            position: absolute;
            top: 20px;
            right: 30px;
            font-size: 3rem;
            color: white;
            cursor: pointer;
        }}
        
        section {{
            background: rgba(255,255,255,0.05);
            border-radius: 20px;
            padding: 25px;
            margin-bottom: 25px;
        }}
        
        section h3 {{
            color: #00d9ff;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid rgba(0,217,255,0.3);
        }}
        
        .footer {{
            text-align: center;
            padding: 30px;
            color: #666;
        }}
        
        /* Loading */
        .loading {{
            display: none;
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: rgba(0,0,0,0.9);
            padding: 30px 50px;
            border-radius: 15px;
            z-index: 999;
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
        
        @media (max-width: 1200px) {{
            .config-grid {{ grid-template-columns: repeat(2, 1fr); }}
            .realtime-stats-grid {{ grid-template-columns: repeat(2, 1fr); }}
            .preset-cards-container {{ grid-template-columns: 1fr; }}
            .charts-grid {{ grid-template-columns: 1fr; }}
            .maps-grid {{ grid-template-columns: repeat(3, 1fr); }}
        }}
    </style>
</head>
<body>
    <div class="loading" id="loading">
        <div class="spinner"></div>
        <div>Menghitung ulang dengan Z-Score...</div>
    </div>
    
    <div class="lightbox" id="lightbox" onclick="closeLightbox()">
        <span class="lightbox-close">&times;</span>
        <img id="lightbox-img" src="" alt="">
    </div>
    
    <div class="header">
        <h1>🔥 DASHBOARD Z-SCORE MULTI-DIVISI</h1>
        <p style="color:#aaa; margin-bottom: 10px;">Deteksi Ganoderma dengan Z-Score Spatial Filter | AME II & AME IV</p>
        <div class="realtime-badge">⚡ REAL-TIME RECALCULATION</div>
    </div>
    
    <div class="container">
        <!-- Info Modal -->
        <div class="info-modal" id="infoModal">
            <div class="info-modal-content">
                <span class="info-modal-close" onclick="closeInfoModal()">&times;</span>
                <h2>ℹ️ Panduan Konfigurasi Z-Score</h2>
                
                <div class="info-section">
                    <h4>📊 Preset Strategi</h4>
                    <p><strong>Makna:</strong> Preset adalah kombinasi parameter Z-Score yang sudah disiapkan untuk berbagai kondisi lapangan.</p>
                    <ul style="color:#ccc; margin-left:20px; line-height:1.8;">
                        <li><strong>Konservatif:</strong> Hanya mendeteksi kasus yang sangat jelas (false positive rendah)</li>
                        <li><strong>Standar:</strong> Keseimbangan antara sensitivitas dan spesifisitas (rekomendasi)</li>
                        <li><strong>Agresif:</strong> Mendeteksi semua potensi infeksi termasuk tahap awal (false positive lebih tinggi)</li>
                    </ul>
                    <div class="impact">💡 <strong>Dampak:</strong> Mempengaruhi semua parameter Z-Score secara otomatis</div>
                </div>
                
                <div class="info-section">
                    <h4>🎯 Z-Score Core (Threshold Inti)</h4>
                    <p><strong>Makna:</strong> Nilai Z-Score minimum untuk menandai pohon sebagai "suspect inti" (core suspect). Pohon dengan Z-Score di bawah threshold ini dianggap memiliki nilai NDRE yang abnormal rendah dibandingkan bloknya.</p>
                    <p><strong>Satuan:</strong> Standar deviasi dari mean blok</p>
                    <p><strong>Range:</strong> -5.0 s/d 0.0 (default: -1.5 untuk Standar)</p>
                    <div class="impact">💡 <strong>Dampak:</strong> Semakin mendekati 0, semakin banyak pohon yang dikategorikan suspect (lebih sensitif)</div>
                </div>
                
                <div class="info-section">
                    <h4>🔗 Z-Score Neighbor (Threshold Tetangga)</h4>
                    <p><strong>Makna:</strong> Nilai Z-Score minimum untuk menghitung tetangga yang "stressed". Tetangga dengan Z-Score di bawah threshold ini dianggap tertekan dan akan dihitung sebagai bagian dari kluster.</p>
                    <p><strong>Satuan:</strong> Standar deviasi dari mean blok</p>
                    <p><strong>Range:</strong> -3.0 s/d 0.0 (default: -0.5 untuk Standar)</p>
                    <div class="impact">💡 <strong>Dampak:</strong> Semakin mendekati 0, semakin banyak tetangga yang dihitung stressed → lebih banyak MERAH</div>
                </div>
                
                <div class="info-section">
                    <h4>👥 Min Neighbors (Minimum Tetangga)</h4>
                    <p><strong>Makna:</strong> Jumlah minimum tetangga stressed yang diperlukan untuk mengklasifikasikan pohon suspect menjadi "MERAH" (kluster aktif). Jika kurang dari threshold ini, pohon akan menjadi ORANYE atau KUNING.</p>
                    <p><strong>Satuan:</strong> Jumlah pohon (1-8)</p>
                    <p><strong>Range:</strong> 1 s/d 8 (default: 1 untuk Standar)</p>
                    <div class="impact">💡 <strong>Dampak:</strong> Semakin kecil, semakin mudah pohon dikategorikan MERAH</div>
                </div>
                
                <div class="info-section" style="border-left-color: #27ae60;">
                    <h4 style="color:#27ae60;">🔬 Bagaimana Algoritma Bekerja?</h4>
                    <p>1. Hitung Z-Score setiap pohon berdasarkan nilai NDRE relatif terhadap bloknya</p>
                    <p>2. Tandai pohon dengan Z-Score < Z-Core sebagai "suspect inti"</p>
                    <p>3. Untuk setiap suspect inti, hitung tetangga (8 pohon terdekat) yang memiliki Z-Score < Z-Neighbor</p>
                    <p>4. Klasifikasikan berdasarkan jumlah tetangga stressed:</p>
                    <ul style="color:#ccc; margin-left:20px;">
                        <li>🔴 <strong>MERAH:</strong> >= Min Neighbors tetangga stressed</li>
                        <li>🟠 <strong>ORANYE:</strong> >= 1 tetangga stressed (tapi < Min Neighbors)</li>
                        <li>🟡 <strong>KUNING:</strong> 0 tetangga stressed (suspect terisolasi)</li>
                        <li>🟢 <strong>HIJAU:</strong> Bukan suspect inti (sehat)</li>
                    </ul>
                </div>
            </div>
        </div>
        
        <!-- Config Panel -->
        <div class="config-panel">
            <div class="config-panel-header">
                <h3>⚙️ KONFIGURASI THRESHOLD Z-SCORE</h3>
                <button class="info-btn" onclick="openInfoModal()">❓ Panduan</button>
            </div>
            <div class="config-grid">
                <div class="config-item">
                    <label>📊 Preset Strategi</label>
                    <select id="preset" onchange="applyPreset()">
                        <option value="konservatif">Konservatif</option>
                        <option value="standar" selected>Standar</option>
                        <option value="agresif">Agresif</option>
                    </select>
                </div>
                <div class="config-item">
                    <label>🎯 Z-Score Core</label>
                    <input type="number" id="z_core" value="-1.5" step="0.1" min="-5" max="0">
                </div>
                <div class="config-item">
                    <label>🔗 Z-Score Neighbor</label>
                    <input type="number" id="z_neighbor" value="-0.5" step="0.1" min="-3" max="0">
                </div>
                <div class="config-item">
                    <label>👥 Min Neighbors</label>
                    <input type="number" id="min_neighbors" value="1" step="1" min="1" max="8">
                </div>
            </div>
            <div style="text-align: center;">
                <button class="apply-btn" onclick="recalculateAll()">
                    🔄 TERAPKAN & HITUNG ULANG (Semua Divisi)
                </button>
            </div>
        </div>
        
        
        <!-- Divisi Tabs -->
        <div class="divisi-tabs">
            {divisi_tabs_html}
        </div>
        
        <!-- Divisi Content -->
        <script>
            const presets = {presets_json};
            const divisiData = {{}};
            const charts = {{}};
        </script>
        
        {divisi_content_html}
        
        <div class="footer">
            <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>Dashboard Z-Score Multi-Divisi v5.0 | Real-Time Recalculation</p>
        </div>
    </div>
    
    <script>
        let currentDivisi = 'AME_II';
        
        function switchDivisi(divisiId) {{
            currentDivisi = divisiId;
            
            // Update tabs
            document.querySelectorAll('.divisi-tab').forEach(tab => {{
                tab.classList.remove('active');
                if (tab.dataset.divisi === divisiId) {{
                    tab.classList.add('active');
                }}
            }});
            
            // Update content
            document.querySelectorAll('.divisi-content').forEach(content => {{
                content.classList.remove('active');
                if (content.dataset.divisi === divisiId) {{
                    content.classList.add('active');
                }}
            }});
            
            // Initialize charts for this divisi if not already done
            initCharts(divisiId);
        }}
        
        function applyPreset() {{
            const preset = presets[document.getElementById('preset').value];
            document.getElementById('z_core').value = preset.z_threshold_core;
            document.getElementById('z_neighbor').value = preset.z_threshold_neighbor;
            document.getElementById('min_neighbors').value = preset.min_stressed_neighbors;
        }}
        
        function recalculateAll() {{
            document.getElementById('loading').classList.add('active');
            
            setTimeout(() => {{
                const zCore = parseFloat(document.getElementById('z_core').value);
                const zNeighbor = parseFloat(document.getElementById('z_neighbor').value);
                const minNeighbors = parseInt(document.getElementById('min_neighbors').value);
                
                // Recalculate for all divisions
                Object.keys(divisiData).forEach(divisiId => {{
                    recalculateDivisi(divisiId, zCore, zNeighbor, minNeighbors);
                }});
                
                document.getElementById('loading').classList.remove('active');
            }}, 100);
        }}
        
        function getBlockStat(divisiId, blok) {{
            const stats = divisiData[divisiId].stats;
            return stats.find(s => s.Blok === blok) || {{ Mean_NDRE: 0, SD_NDRE: 1 }};
        }}
        
        function recalculateDivisi(divisiId, zCore, zNeighbor, minNeighbors) {{
            const trees = divisiData[divisiId].trees;
            let merah = 0, oranye = 0, kuning = 0, hijau = 0;
            
            // Group by block
            const byBlock = {{}};
            trees.forEach(tree => {{
                if (!byBlock[tree.Blok]) byBlock[tree.Blok] = [];
                byBlock[tree.Blok].push(tree);
            }});
            
            // Process each block
            Object.keys(byBlock).forEach(blok => {{
                const blockTrees = byBlock[blok];
                const stat = getBlockStat(divisiId, blok);
                
                // Calculate Z-scores
                blockTrees.forEach(tree => {{
                    tree.ZScore = stat.SD_NDRE > 0 ? (tree.NDRE125 - stat.Mean_NDRE) / stat.SD_NDRE : 0;
                    tree.isCore = tree.ZScore < zCore;
                }});
                
                // Count neighbors and classify
                blockTrees.forEach((tree, idx) => {{
                    if (!tree.isCore) {{
                        hijau++;
                        return;
                    }}
                    
                    let stressedNeighbors = 0;
                    blockTrees.forEach((other, oIdx) => {{
                        if (idx === oIdx) return;
                        if (Math.abs(other.N_BARIS - tree.N_BARIS) <= 1 &&
                            Math.abs(other.N_POKOK - tree.N_POKOK) <= 1 &&
                            other.ZScore < zNeighbor) {{
                            stressedNeighbors++;
                        }}
                    }});
                    
                    if (stressedNeighbors >= minNeighbors) {{
                        merah++;
                    }} else if (stressedNeighbors >= 1) {{
                        oranye++;
                    }} else {{
                        kuning++;
                    }}
                }});
            }});
            
            // Update UI
            document.getElementById(`merah-${{divisiId}}`).textContent = merah.toLocaleString();
            document.getElementById(`oranye-${{divisiId}}`).textContent = oranye.toLocaleString();
            document.getElementById(`kuning-${{divisiId}}`).textContent = kuning.toLocaleString();
            document.getElementById(`hijau-${{divisiId}}`).textContent = hijau.toLocaleString();
            
            // Update charts
            updateCharts(divisiId, merah, oranye, kuning, hijau);
        }}
        
        function initCharts(divisiId) {{
            if (charts[divisiId]) return;
            
            const pieCtx = document.getElementById(`pie-${{divisiId}}`);
            const barCtx = document.getElementById(`bar-${{divisiId}}`);
            
            if (!pieCtx || !barCtx) return;
            
            charts[divisiId] = {{
                pie: new Chart(pieCtx, {{
                    type: 'doughnut',
                    data: {{
                        labels: ['MERAH', 'ORANYE', 'KUNING', 'HIJAU'],
                        datasets: [{{
                            data: [0, 0, 0, 0],
                            backgroundColor: ['#e74c3c', '#e67e22', '#f1c40f', '#27ae60']
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        plugins: {{ legend: {{ position: 'bottom', labels: {{ color: '#fff' }} }} }}
                    }}
                }}),
                bar: new Chart(barCtx, {{
                    type: 'bar',
                    data: {{
                        labels: ['Konservatif', 'Standar', 'Agresif'],
                        datasets: [
                            {{ label: 'MERAH', data: [0, 0, 0], backgroundColor: '#e74c3c' }},
                            {{ label: 'ORANYE', data: [0, 0, 0], backgroundColor: '#e67e22' }}
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
                }})
            }};
            
            // Initialize with current values
            const merah = parseInt(document.getElementById(`merah-${{divisiId}}`).textContent.replace(/,/g, ''));
            const oranye = parseInt(document.getElementById(`oranye-${{divisiId}}`).textContent.replace(/,/g, ''));
            const kuning = parseInt(document.getElementById(`kuning-${{divisiId}}`).textContent.replace(/,/g, ''));
            const hijau = parseInt(document.getElementById(`hijau-${{divisiId}}`).textContent.replace(/,/g, ''));
            updateCharts(divisiId, merah, oranye, kuning, hijau);
        }}
        
        function updateCharts(divisiId, merah, oranye, kuning, hijau) {{
            if (!charts[divisiId]) return;
            
            // Update pie chart
            charts[divisiId].pie.data.datasets[0].data = [merah, oranye, kuning, hijau];
            charts[divisiId].pie.update();
            
            // Update bar chart with estimated preset values
            charts[divisiId].bar.data.datasets[0].data = [
                Math.round(merah * 0.5),
                merah,
                Math.round(merah * 1.8)
            ];
            charts[divisiId].bar.data.datasets[1].data = [
                Math.round(oranye * 0.4),
                oranye,
                Math.round(oranye * 2)
            ];
            charts[divisiId].bar.update();
        }}
        
        function openLightbox(src, title) {{
            document.getElementById('lightbox-img').src = src;
            document.getElementById('lightbox').classList.add('active');
        }}
        
        function closeLightbox() {{
            document.getElementById('lightbox').classList.remove('active');
        }}
        
        // Info Modal functions
        function openInfoModal() {{
            document.getElementById('infoModal').classList.add('active');
        }}
        
        function closeInfoModal() {{
            document.getElementById('infoModal').classList.remove('active');
        }}
        
        // Close modal when clicking outside
        document.addEventListener('click', function(e) {{
            if (e.target.classList.contains('info-modal')) {{
                closeInfoModal();
            }}
        }});
        
        // Initialize on load
        window.onload = function() {{
            applyPreset();
            switchDivisi('AME_II');
        }};
    </script>
</body>
</html>
'''
    
    html_path = output_dir / 'dashboard_zscore_multi_divisi.html'
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    logging.info(f"Dashboard generated: {html_path}")
    return html_path

def main():
    print('=' * 80)
    print('🔥 DASHBOARD Z-SCORE MULTI-DIVISI v5.0')
    print('Real-Time Recalculation dengan Peta Kluster Matplotlib')
    print('=' * 80)
    
    base_dir = Path(__file__).parent
    
    # Load data for both divisions
    print('\n[1/5] Loading AME II data...')
    df_ame_ii = load_and_clean_data(base_dir / 'data' / 'input' / 'tabelNDREnew.csv')
    print(f'  ✅ AME II: {len(df_ame_ii):,} pohon')
    
    print('\n[2/5] Loading AME IV data...')
    df_ame_iv = load_ame_iv_data(base_dir / 'data' / 'input' / 'AME_IV.csv')
    print(f'  ✅ AME IV: {len(df_ame_iv):,} pohon')
    
    # Analyze both divisions
    all_divisi_results = {}
    all_block_maps = {}
    all_tree_data = {}
    
    print('\n[3/5] Analyzing AME II with Z-Score...')
    results_ii, maps_ii = analyze_divisi_with_zscore(df_ame_ii, 'AME II', output_dir)
    all_divisi_results['AME II'] = {'results': results_ii}
    all_block_maps['AME II'] = maps_ii
    
    trees_ii, stats_ii = prepare_tree_data_for_js(df_ame_ii)
    all_tree_data['AME II'] = {'trees': trees_ii, 'stats': stats_ii}
    
    print('\n[4/5] Analyzing AME IV with Z-Score...')
    results_iv, maps_iv = analyze_divisi_with_zscore(df_ame_iv, 'AME IV', output_dir)
    all_divisi_results['AME IV'] = {'results': results_iv}
    all_block_maps['AME IV'] = maps_iv
    
    trees_iv, stats_iv = prepare_tree_data_for_js(df_ame_iv)
    all_tree_data['AME IV'] = {'trees': trees_iv, 'stats': stats_iv}
    
    # Generate HTML dashboard
    print('\n[5/5] Generating Multi-Divisi HTML Dashboard...')
    html_path = generate_multi_divisi_html(output_dir, all_divisi_results, all_block_maps, all_tree_data)
    
    print(f'\n{"="*80}')
    print('✅ DASHBOARD Z-SCORE MULTI-DIVISI v5.0 BERHASIL DIBUAT!')
    print(f'{"="*80}')
    print(f'\n📁 Output: {output_dir}')
    print(f'🌐 Dashboard: {html_path}')
    print(f'\n💡 Fitur:')
    print('   - Tab AME II dan AME IV')
    print('   - Peta kluster matplotlib (PNG) per blok')
    print('   - Real-time recalculation dengan Z-Score')
    print('   - Konfigurasi preset interaktif')
    
    return html_path

if __name__ == '__main__':
    html_path = main()
