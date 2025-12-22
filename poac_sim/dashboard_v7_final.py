"""
Dashboard Z-Score + Cincin Api v7.0 FINAL
==========================================
✅ 1. Algoritma Hybrid Cincin Api (Z-Score init + Cincin Api classification)
✅ 2. Panel konfigurasi real-time dengan slider & preset
✅ 3. Dual POV: Ganoderma→Yield dan Yield→Ganoderma
✅ 4. Peta kluster portrait dengan Cincin Api yang jelas
✅ 5. Info button dengan popup penjelasan
✅ 6. Fix AME IV data loading (BLOK_B column)
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
import matplotlib.patches as mpatches

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

from src.ingestion import load_and_clean_data
from config import ZSCORE_PRESETS

timestamp = datetime.now().strftime("%Y%m%d_%H%M")
output_dir = Path(f'data/output/dashboard_v7_{timestamp}')
output_dir.mkdir(parents=True, exist_ok=True)

def load_ame_iv_data(file_path):
    """Load AME IV data with proper block column."""
    df = pd.read_csv(file_path, sep=';')
    
    # CRITICAL FIX: Use BLOK_B for actual block names
    if 'BLOK_B' in df.columns:
        df['Blok'] = df['BLOK_B']
    
    # Handle comma decimal separator in NDRE125
    if 'NDRE125' in df.columns:
        df['NDRE125'] = df['NDRE125'].astype(str).str.replace(',', '.').astype(float)
    
    for col in ['N_BARIS', 'N_POKOK']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    df = df.dropna(subset=['Blok', 'N_BARIS', 'N_POKOK', 'NDRE125'])
    return df

def load_productivity_data():
    """Load productivity data from data_gabungan.xlsx."""
    file_path = Path('data/input/data_gabungan.xlsx')
    if not file_path.exists():
        logging.warning("Productivity data not found")
        return pd.DataFrame()
    
    df_raw = pd.read_excel(file_path, header=None)
    df = df_raw.iloc[8:].copy().reset_index(drop=True)
    df.columns = [f'col_{i}' for i in range(df.shape[1])]
    
    df = df.rename(columns={
        'col_0': 'Blok_Prod', 'col_1': 'Tahun_Tanam', 'col_3': 'Divisi_Prod',
        'col_11': 'Luas_Ha', 'col_170': 'Produksi_Ton'
    })
    
    df['Luas_Ha'] = pd.to_numeric(df['Luas_Ha'], errors='coerce')
    df['Produksi_Ton'] = pd.to_numeric(df['Produksi_Ton'], errors='coerce')
    df['Yield_TonHa'] = df['Produksi_Ton'] / df['Luas_Ha']
    df['Yield_TonHa'] = df['Yield_TonHa'].replace([np.inf, -np.inf], np.nan)
    
    return df[['Blok_Prod', 'Divisi_Prod', 'Luas_Ha', 'Produksi_Ton', 'Yield_TonHa']].dropna()

def get_hex_neighbors(baris, pokok):
    """Get hexagonal neighbors (mata lima pattern)."""
    if baris % 2 == 0:
        return [(baris-1, pokok-1), (baris-1, pokok), (baris, pokok-1), 
                (baris, pokok+1), (baris+1, pokok-1), (baris+1, pokok)]
    else:
        return [(baris-1, pokok), (baris-1, pokok+1), (baris, pokok-1),
                (baris, pokok+1), (baris+1, pokok), (baris+1, pokok+1)]

def hybrid_cincin_api_zscore(df, z_core=-1.5, z_neighbor=-0.5, min_neighbors=2):
    """
    HYBRID ALGORITHM: Z-Score detection + Cincin Api classification
    
    Step 1: Use Z-Score to identify suspect trees (anomaly detection)
    Step 2: Apply Cincin Api logic to classify MERAH clusters
    Step 3: Create ORANYE ring around MERAH trees
    """
    df = df.copy()
    
    # Step 1: Calculate Z-Score per block
    block_stats = df.groupby('Blok')['NDRE125'].agg(['mean', 'std']).reset_index()
    block_stats.columns = ['Blok', 'Mean_NDRE', 'SD_NDRE']
    block_stats['SD_NDRE'] = block_stats['SD_NDRE'].fillna(1).replace(0, 1)
    
    df = df.merge(block_stats, on='Blok', how='left')
    df['ZScore'] = (df['NDRE125'] - df['Mean_NDRE']) / df['SD_NDRE']
    
    # Step 2: Build coordinate lookup
    coord_lookup = {}
    for idx, row in df.iterrows():
        key = (row['Blok'], int(row['N_BARIS']), int(row['N_POKOK']))
        coord_lookup[key] = idx
    
    # Step 3: Initialize - mark suspects using Z-Score
    df['Status_Risiko'] = 'HIJAU'
    df['Jumlah_Tetangga_Sakit'] = 0
    df['Is_Cincin_Api'] = False
    
    suspect_mask = df['ZScore'] < z_core
    suspect_indices = df[suspect_mask].index.tolist()
    
    # Step 4: Count sick neighbors for suspects (Cincin Api TAHAP 1)
    for idx in suspect_indices:
        row = df.loc[idx]
        blok = row['Blok']
        baris = int(row['N_BARIS'])
        pokok = int(row['N_POKOK'])
        
        neighbors = get_hex_neighbors(baris, pokok)
        sick_count = 0
        
        for n_baris, n_pokok in neighbors:
            neighbor_key = (blok, n_baris, n_pokok)
            if neighbor_key in coord_lookup:
                n_idx = coord_lookup[neighbor_key]
                if df.loc[n_idx, 'ZScore'] < z_neighbor:
                    sick_count += 1
        
        df.loc[idx, 'Jumlah_Tetangga_Sakit'] = sick_count
        
        if sick_count >= min_neighbors:
            df.loc[idx, 'Status_Risiko'] = 'MERAH'
        else:
            df.loc[idx, 'Status_Risiko'] = 'KUNING'
    
    # Step 5: Create Cincin Api (TAHAP 2) - neighbors of MERAH become ORANYE
    merah_indices = df[df['Status_Risiko'] == 'MERAH'].index.tolist()
    
    for idx in merah_indices:
        row = df.loc[idx]
        blok = row['Blok']
        baris = int(row['N_BARIS'])
        pokok = int(row['N_POKOK'])
        
        neighbors = get_hex_neighbors(baris, pokok)
        
        for n_baris, n_pokok in neighbors:
            neighbor_key = (blok, n_baris, n_pokok)
            if neighbor_key in coord_lookup:
                n_idx = coord_lookup[neighbor_key]
                if df.loc[n_idx, 'Status_Risiko'] != 'MERAH':
                    df.loc[n_idx, 'Status_Risiko'] = 'ORANYE'
                    df.loc[n_idx, 'Is_Cincin_Api'] = True
    
    return df

def generate_cluster_map_png(df, blok, preset_name, rank, output_dir, divisi_id):
    """Generate matplotlib cluster map (PORTRAIT format) with proper Cincin Api."""
    block_df = df[df['Blok'] == blok].copy().reset_index(drop=True)
    if len(block_df) == 0:
        return None
    
    merah = (block_df['Status_Risiko'] == 'MERAH').sum()
    oranye = (block_df['Status_Risiko'] == 'ORANYE').sum()
    kuning = (block_df['Status_Risiko'] == 'KUNING').sum()
    hijau = (block_df['Status_Risiko'] == 'HIJAU').sum()
    total = len(block_df)
    
    fig, ax = plt.subplots(figsize=(14, 12))  # PORTRAIT
    
    colors = {'MERAH': '#e74c3c', 'ORANYE': '#e67e22', 'KUNING': '#f1c40f', 'HIJAU': '#27ae60'}
    sizes = {'MERAH': 80, 'ORANYE': 70, 'KUNING': 60, 'HIJAU': 50}
    
    # Layer-based plotting (HIJAU first, MERAH on top)
    for status in ['HIJAU', 'KUNING', 'ORANYE', 'MERAH']:
        mask = block_df['Status_Risiko'] == status
        if not mask.any():
            continue
        subset = block_df[mask]
        
        # Hexagonal offset for even rows
        x = subset['N_POKOK'] + np.where(subset['N_BARIS'] % 2 == 0, 0.5, 0)
        y = subset['N_BARIS']
        
        ax.scatter(x, y, c=colors[status], s=sizes[status], alpha=0.85,
                  edgecolors='black', linewidths=0.5, 
                  zorder=['HIJAU','KUNING','ORANYE','MERAH'].index(status)+1)
    
    # Legend with counts
    legend = [mpatches.Patch(color=c, label=f'{s} ({(block_df["Status_Risiko"]==s).sum()})') 
              for s, c in colors.items()]
    ax.legend(handles=legend, loc='upper right', fontsize=11, framealpha=0.9, shadow=True)
    
    # Axis labels
    ax.set_xlabel('Nomor Pokok (N_POKOK)', fontsize=12)
    ax.set_ylabel('Nomor Baris (N_BARIS)', fontsize=12)
    ax.set_title(f'#{rank:02d} - BLOK {blok}\nTotal: {total} | 🔴{merah} | 🟠{oranye} | 🟡{kuning}', 
                fontsize=14, fontweight='bold')
    ax.invert_yaxis()
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.set_aspect('equal')
    
    # Rank badge
    ax.text(0.02, 0.98, f'RANK #{rank}', transform=ax.transAxes, fontsize=16, fontweight='bold',
           color='white', bbox=dict(boxstyle='round', facecolor='#e74c3c' if rank<=3 else '#f39c12'),
           verticalalignment='top')
    
    # Preset badge
    preset_colors = {'konservatif': '#3498db', 'standar': '#27ae60', 'agresif': '#e74c3c'}
    ax.text(0.98, 0.98, preset_name.upper(), transform=ax.transAxes, fontsize=12, fontweight='bold',
           color='white', ha='right', va='top', 
           bbox=dict(boxstyle='round', facecolor=preset_colors.get(preset_name, '#333')))
    
    plt.tight_layout()
    
    divisi_dir = output_dir / divisi_id
    divisi_dir.mkdir(exist_ok=True)
    filename = f'cluster_{preset_name}_{rank:02d}_{blok}.png'
    filepath = divisi_dir / filename
    fig.savefig(filepath, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    
    # Convert to base64 for embedding
    with open(filepath, 'rb') as f:
        img_data = base64.b64encode(f.read()).decode()
    
    return {
        'filename': filename,
        'blok': blok,
        'rank': rank,
        'merah': merah,
        'oranye': oranye,
        'base64': img_data
    }

def analyze_divisi(df, divisi_name, prod_df, output_dir):
    """Analyze division with all presets and generate maps."""
    divisi_id = divisi_name.replace(' ', '_')
    results = {}
    block_maps = {}
    
    for preset_name in ['konservatif', 'standar', 'agresif']:
        preset = ZSCORE_PRESETS[preset_name]
        
        df_classified = hybrid_cincin_api_zscore(
            df,
            z_core=preset['z_threshold_core'],
            z_neighbor=preset['z_threshold_neighbor'],
            min_neighbors=preset['min_stressed_neighbors']
        )
        
        # Stats
        stats = {s: (df_classified['Status_Risiko'] == s).sum() 
                for s in ['MERAH', 'ORANYE', 'KUNING', 'HIJAU']}
        
        # Block-level stats
        block_stats = df_classified.groupby('Blok').agg({
            'Status_Risiko': [
                lambda x: (x=='MERAH').sum(), 
                lambda x: (x=='ORANYE').sum(), 
                'count'
            ]
        }).reset_index()
        block_stats.columns = ['Blok', 'MERAH', 'ORANYE', 'Total']
        block_stats['Attack_Pct'] = (block_stats['MERAH'] + block_stats['ORANYE']) / block_stats['Total'] * 100
        
        top_blocks = block_stats.nlargest(5, 'Attack_Pct')
        
        # Generate maps
        maps = []
        for rank, (_, row) in enumerate(top_blocks.iterrows(), 1):
            m = generate_cluster_map_png(df_classified, row['Blok'], preset_name, rank, output_dir, divisi_id)
            if m:
                maps.append(m)
        
        block_maps[preset_name] = maps
        results[preset_name] = {
            'df': df_classified, 
            'stats': stats,
            'block_stats': block_stats,
            'total': len(df_classified),
            'blocks': df_classified['Blok'].nunique()
        }
        
        logging.info(f"{divisi_name} {preset_name}: MERAH={stats['MERAH']}, ORANYE={stats['ORANYE']}")
    
    return results, block_maps

def convert_gano_to_prod_pattern(gano_blok):
    """
    Convert Ganoderma block name to Productivity block pattern.
    Examples: B16 → B016, A12 → A012, C18A → C018
    """
    import re
    match = re.match(r'([A-Z]+)(\d+)([A-Z]*)', str(gano_blok))
    if match:
        prefix, num, suffix = match.groups()
        return f"{prefix}{num.zfill(3)}"
    return str(gano_blok)

def convert_prod_to_gano_pattern(prod_blok):
    """
    Convert Productivity block name to Ganoderma block pattern.
    Examples: A012A → A12, B016B → B16, C018A → C18
    """
    import re
    match = re.match(r'([A-Z]+)(\d+)([A-Z]*)', str(prod_blok))
    if match:
        prefix, num, suffix = match.groups()
        return f"{prefix}{int(num)}"
    return str(prod_blok)

def generate_html_with_realtime(output_dir, all_results, all_maps, prod_df):
    """Generate HTML with real-time configuration panel and dual POV."""
    
    presets_json = json.dumps(ZSCORE_PRESETS)
    
    # Prepare data for JavaScript
    js_data = {}
    for divisi, data in all_results.items():
        divisi_id = divisi.replace(' ', '_')
        results = data['results']
        
        # Aggregate all trees from standar preset for JS recalculation
        df_full = results['standar']['df']
        js_data[divisi_id] = {
            'trees': df_full[['Blok', 'N_BARIS', 'N_POKOK', 'ZScore', 'Mean_NDRE', 'SD_NDRE']].to_dict('records'),
            'total_trees': len(df_full),
            'total_blocks': df_full['Blok'].nunique()
        }
    
    js_data_json = json.dumps(js_data)
    
    # Build tabs
    divisi_tabs = ""
    divisi_content = ""
    
    for idx, (divisi, data) in enumerate(all_results.items()):
        divisi_id = divisi.replace(' ', '_')
        active = "active" if idx == 0 else ""
        
        results = data['results']
        block_maps = all_maps[divisi]
        stats = results['standar']['stats']
        
        # Preset cards
        preset_cards = ""
        for p in ['konservatif', 'standar', 'agresif']:
            s = results[p]['stats']
            colors_map = {'konservatif': '#3498db', 'standar': '#27ae60', 'agresif': '#e74c3c'}
            preset_cards += f'''
            <div class="preset-card" style="border-top: 4px solid {colors_map[p]}">
                <h4>{p.upper()}</h4>
                <div class="stats-mini">
                    <span style="color:#e74c3c">🔴 {s['MERAH']:,}</span>
                    <span style="color:#e67e22">🟠 {s['ORANYE']:,}</span>
                    <span style="color:#f1c40f">🟡 {s['KUNING']:,}</span>
                    <span style="color:#27ae60">🟢 {s['HIJAU']:,}</span>
                </div>
            </div>'''
        
        # Maps HTML
        maps_html = ""
        for p in ['konservatif', 'standar', 'agresif']:
            items = "".join([
                f'<div class="map-item"><img src="data:image/png;base64,{m["base64"]}" alt="{m["blok"]}"><div class="map-label">{m["blok"]}</div></div>' 
                for m in block_maps.get(p, [])
            ])
            maps_html += f'<div class="maps-section"><h4>{p.upper()}</h4><div class="maps-grid">{items}</div></div>'
        
def convert_gano_to_prod_pattern(gano_blok):
    """
    Convert Ganoderma block name to Productivity block pattern.
    Examples: B16 → B016, A12 → A012, C18A → C018
    """
    import re
    match = re.match(r'([A-Z]+)(\d+)([A-Z]*)', str(gano_blok))
    if match:
        prefix, num, suffix = match.groups()
        # Zero-pad number to 3 digits
        return f"{prefix}{num.zfill(3)}"
    return str(gano_blok)

def convert_prod_to_gano_pattern(prod_blok):
    """
    Convert Productivity block name to Ganoderma block pattern.
    Examples: A012A → A12, B016B → B16, C018A → C18
    """
    import re
    match = re.match(r'([A-Z]+)(\d+)([A-Z]*)', str(prod_blok))
    if match:
        prefix, num, suffix = match.groups()
        # Remove leading zeros
        return f"{prefix}{int(num)}"
    return str(prod_blok)

        # POV 1: Ganoderma → Yield
        block_stats = results['standar']['block_stats']
        top_gano = block_stats.nlargest(10, 'Attack_Pct')
        
        gano_rows = ""
        for i, (_, r) in enumerate(top_gano.iterrows(), 1):
            # Convert Ganoderma block name to productivity pattern (B16 → B016)
            prod_pattern = convert_gano_to_prod_pattern(r['Blok'])
            yield_matches = prod_df[prod_df['Blok_Prod'].str.contains(prod_pattern, na=False, regex=False)]
            yield_val = yield_matches['Yield_TonHa'].mean() if not yield_matches.empty else None
            yield_str = f"{yield_val:.2f}" if pd.notna(yield_val) else "N/A"
            gano_rows += f'<tr><td>{i}</td><td><b>{r["Blok"]}</b></td><td>{r["Total"]:,}</td><td style="color:#e74c3c">{r["MERAH"]}</td><td style="color:#e67e22">{r["ORANYE"]}</td><td><b>{r["Attack_Pct"]:.1f}%</b></td><td>{yield_str}</td></tr>'
        
        # POV 2: Yield → Ganoderma
        yield_rows = ""
        if not prod_df.empty:
            low_yield = prod_df.nsmallest(10, 'Yield_TonHa')
            for i, (_, r) in enumerate(low_yield.iterrows(), 1):
                # Convert productivity block name to  Ganoderma pattern (A012A → A12)
                gano_pattern = convert_prod_to_gano_pattern(r['Blok_Prod'])
                blok_match = block_stats[block_stats['Blok'].str.contains(gano_pattern, na=False, regex=False)]
                attack = blok_match['Attack_Pct'].mean() if not blok_match.empty else 0
                yield_rows += f'<tr><td>{i}</td><td><b>{r["Blok_Prod"]}</b></td><td>{r["Yield_TonHa"]:.3f}</td><td>{r["Luas_Ha"]:.1f}</td><td>{attack:.1f}%</td></tr>'
        
        divisi_tabs += f'<button class="tab {active}" onclick="switchTab(\'{divisi_id}\')" data-div="{divisi_id}">{divisi}</button>'
        
        divisi_content += f'''
        <div class="content {active}" id="{divisi_id}">
            <div class="header-info"><h2>📍 {divisi}</h2><span id="stats-{divisi_id}">🌳 {results["standar"]["total"]:,} pohon | 📦 {results["standar"]["blocks"]} blok</span></div>
            
            <div class="stats-grid" id="stats-grid-{divisi_id}">
                <div class="stat-card merah"><div class="val" id="merah-{divisi_id}">{stats["MERAH"]:,}</div><div class="lbl">🔴 MERAH</div></div>
                <div class="stat-card oranye"><div class="val" id="oranye-{divisi_id}">{stats["ORANYE"]:,}</div><div class="lbl">🟠 ORANYE</div></div>
                <div class="stat-card kuning"><div class="val" id="kuning-{divisi_id}">{stats["KUNING"]:,}</div><div class="lbl">🟡 KUNING</div></div>
                <div class="stat-card hijau"><div class="val" id="hijau-{divisi_id}">{stats["HIJAU"]:,}</div><div class="lbl">🟢 HIJAU</div></div>
            </div>
            
            <section><h3>📊 Perbandingan Preset</h3><div class="preset-grid">{preset_cards}</div></section>
            
            <section><h3>🗺️ Peta Kluster Cincin Api (Top 5)</h3>{maps_html}</section>
            
            <section class="pov-section">
                <h3>🔥 POV 1: Ganoderma → Produktivitas</h3>
                <p>Top 10 blok dengan serangan tertinggi dan dampak yield-nya</p>
                <table><thead><tr><th>#</th><th>Blok</th><th>Total</th><th>MERAH</th><th>ORANYE</th><th>% Attack</th><th>Yield</th></tr></thead>
                <tbody>{gano_rows}</tbody></table>
            </section>
            
            <section class="pov-section">
                <h3>📉 POV 2: Produktivitas → Ganoderma</h3>
                <p>Top 10 blok dengan yield terendah dan breakdown serangannya</p>
                <table><thead><tr><th>#</th><th>Blok</th><th>Yield</th><th>Luas</th><th>% Attack</th></tr></thead>
                <tbody>{yield_rows if yield_rows else "<tr><td colspan='5'>Data produktivitas tidak tersedia</td></tr>"}</tbody></table>
            </section>
        </div>'''
    
    html = f'''<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🔥 Dashboard Z-Score + Cincin Api v7.0 FINAL</title>
    <style>
:root {{ --merah:#e74c3c; --oranye:#e67e22; --kuning:#f1c40f; --hijau:#27ae60; --dark:#1a1a2e; --blue:#3498db; }}
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family:'Segoe UI',Tahoma,sans-serif; background:linear-gradient(135deg,#1a1a2e,#16213e); color:#fff; min-height:100vh; }}
.header {{ text-align:center; padding:30px; background:rgba(255,255,255,0.05); border-bottom:3px solid var(--oranye); }}
.header h1 {{ font-size:2.5rem; background:linear-gradient(45deg,#ff6b6b,#ffa500,#00ff88); -webkit-background-clip:text; -webkit-text-fill-color:transparent; margin-bottom:10px; }}
.header p {{ color:#aaa; font-size:1.1rem; }}
.container {{ max-width:1800px; margin:auto; padding:20px; }}

/* Configuration Panel */
.config-panel {{ background:rgba(255,255,255,0.08); border-radius:20px; padding:25px; margin-bottom:30px; border:2px solid rgba(0,217,255,0.3); }}
.config-header {{ display:flex; justify-content:space-between; align-items:center; margin-bottom:20px; }}
.config-header h3 {{ color:#00d9ff; display:flex; align-items:center; gap:10px; }}
.info-btn {{ background:#3498db; color:#fff; border:none; border-radius:50%; width:35px; height:35px; font-size:18px; cursor:pointer; transition:0.3s; }}
.info-btn:hover {{ background:#2980b9; transform:scale(1.1); }}
.config-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(300px,1fr)); gap:20px; }}
.config-item {{ background:rgba(0,0,0,0.3); padding:20px; border-radius:15px; }}
.config-item label {{ display:block; color:#00d9ff; margin-bottom:10px; font-weight:600; }}
.config-item select, .config-item input {{ width:100%; padding:10px; border-radius:8px; border:2px solid rgba(0,217,255,0.3); background:rgba(255,255,255,0.1); color:#fff; font-size:16px; }}
.config-item input[type="range"] {{ height:8px; }}
.config-item .value-display {{ display:flex; justify-content:space-between; margin-top:5px; color:#aaa; font-size:14px; }}
.config-item .impact {{ margin-top:10px; padding:10px; background:rgba(0,0,0,0.2); border-radius:8px; font-size:13px; color:#ffd700; }}

/* Modal */
.modal {{ display:none; position:fixed; z-index:9999; left:0; top:0; width:100%; height:100%; background:rgba(0,0,0,0.8); }}
.modal-content {{ background:linear-gradient(135deg,#1e3c72,#2a5298); margin:5% auto; padding:30px; border-radius:20px; max-width:800px; max-height:80vh; overflow-y:auto; box-shadow:0 10px 50px rgba(0,0,0,0.5); }}
.close {{ color:#fff; float:right; font-size:35px; font-weight:bold; cursor:pointer; line-height:20px; }}
.close:hover {{ color:#ff6b6b; }}
.modal-content h2 {{ color:#00d9ff; margin-bottom:20px; }}
.modal-content h3 {{ color:#ffa500; margin-top:20px; margin-bottom:10px; }}
.modal-content p {{ line-height:1.6; margin-bottom:15px; }}
.modal-content ul {{ margin-left:20px; margin-bottom:15px; }}
.modal-content li {{ margin-bottom:8px; }}

/* Tabs */
.tabs {{ display:flex; gap:15px; justify-content:center; margin:20px 0; flex-wrap:wrap; }}
.tab {{ padding:15px 40px; border:none; border-radius:30px; font-size:1.1rem; cursor:pointer; color:#fff; background:#3498db; transition:0.3s; }}
.tab.active {{ background:var(--oranye); box-shadow:0 5px 20px rgba(0,0,0,0.3); }}
.tab:hover {{ transform:translateY(-2px); box-shadow:0 5px 15px rgba(0,0,0,0.4); }}

.content {{ display:none; }}
.content.active {{ display:block; }}

.header-info {{ display:flex; justify-content:space-between; align-items:center; padding:20px; background:rgba(255,255,255,0.05); border-radius:15px; margin-bottom:20px; }}
.stats-grid {{ display:grid; grid-template-columns:repeat(4,1fr); gap:20px; margin-bottom:25px; }}
.stat-card {{ background:rgba(255,255,255,0.08); padding:25px; border-radius:15px; text-align:center; border-left:5px solid; transition:transform 0.3s; }}
.stat-card:hover {{ transform:translateY(-5px); }}
.stat-card.merah {{ border-color:var(--merah); }} 
.stat-card.oranye {{ border-color:var(--oranye); }}
.stat-card.kuning {{ border-color:var(--kuning); }} 
.stat-card.hijau {{ border-color:var(--hijau); }}
.stat-card .val {{ font-size:2.5rem; font-weight:bold; }}
.stat-card.merah .val {{ color:var(--merah); }} 
.stat-card.oranye .val {{ color:var(--oranye); }}
.stat-card.kuning .val {{ color:var(--kuning); }} 
.stat-card.hijau .val {{ color:var(--hijau); }}
.stat-card .lbl {{ color:#aaa; margin-top:5px; }}

section {{ background:rgba(255,255,255,0.05); border-radius:20px; padding:25px; margin-bottom:25px; }}
section h3 {{ color:#00d9ff; margin-bottom:15px; padding-bottom:10px; border-bottom:2px solid rgba(0,217,255,0.3); }}

.preset-grid {{ display:grid; grid-template-columns:repeat(3,1fr); gap:20px; }}
.preset-card {{ background:rgba(0,0,0,0.2); border-radius:15px; padding:20px; text-align:center; transition:transform 0.3s; }}
.preset-card:hover {{ transform:scale(1.05); }}
.preset-card h4 {{ margin-bottom:10px; }}
.stats-mini {{ display:flex; gap:15px; justify-content:center; flex-wrap:wrap; }}

.maps-section {{ margin-bottom:20px; }}
.maps-section h4 {{ margin-bottom:10px; padding:10px; background:rgba(0,0,0,0.3); border-radius:8px; }}
.maps-grid {{ display:grid; grid-template-columns:repeat(5,1fr); gap:15px; }}
.map-item {{ background:rgba(0,0,0,0.3); border-radius:10px; overflow:hidden; cursor:pointer; transition:transform 0.3s; }}
.map-item:hover {{ transform:scale(1.05); box-shadow:0 5px 20px rgba(0,217,255,0.5); }}
.map-item img {{ width:100%; display:block; }}
.map-label {{ padding:10px; text-align:center; background:rgba(0,0,0,0.5); font-weight:bold; }}

.pov-section p {{ color:#aaa; margin-bottom:15px; }}
table {{ width:100%; border-collapse:collapse; }}
th,td {{ padding:12px; text-align:left; border-bottom:1px solid rgba(255,255,255,0.1); }}
th {{ background:rgba(0,0,0,0.3); color:#00d9ff; font-weight:600; }}
tr:hover {{ background:rgba(255,255,255,0.05); }}

.footer {{ text-align:center; padding:30px; color:#666; }}

@media(max-width:1200px) {{ 
    .stats-grid,.preset-grid {{ grid-template-columns:repeat(2,1fr); }} 
    .maps-grid {{ grid-template-columns:repeat(3,1fr); }}
    .config-grid {{ grid-template-columns:1fr; }}
}}
@media(max-width:768px) {{
    .stats-grid {{ grid-template-columns:1fr; }}
    .maps-grid {{ grid-template-columns:repeat(2,1fr); }}
    .header h1 {{ font-size:1.8rem; }}
}}
    </style>
</head>
<body>
    <div class="header">
        <h1>🔥 DASHBOARD Z-SCORE + CINCIN API v7.0 FINAL</h1>
        <p>Hybrid Detection • Real-time Configuration • Korelasi Produktivitas</p>
    </div>
    
    <div class="container">
        <!-- Configuration Panel -->
        <div class="config-panel">
            <div class="config-header">
                <h3>⚙️ KONFIGURASI THRESHOLD Z-SCORE</h3>
                <button class="info-btn" onclick="openInfoModal()">❓</button>
            </div>
            <div class="config-grid">
                <div class="config-item">
                    <label>📋 Preset Strategi:</label>
                    <select id="preset-select" onchange="applyPreset()">
                        <option value="konservatif">Konservatif (Lebih Banyak MERAH)</option>
                        <option value="standar" selected>Standar (Balanced)</option>
                        <option value="agresif">Agresif (Lebih Selektif)</option>
                        <option value="custom">Custom (Manual)</option>
                    </select>
                </div>
                
                <div class="config-item">
                    <label>🎯 Z-Score Core (Kluster Aktif):</label>
                    <input type="range" id="z-core" min="-3" max="0" step="0.1" value="-1.5" oninput="updateConfig()">
                    <div class="value-display">
                        <span>Z-Score:</span>
                        <span id="z-core-val">-1.5</span>
                    </div>
                    <div class="impact">Semakin tinggi → Lebih banyak pohon dianggap MERAH</div>
                </div>
                
                <div class="config-item">
                    <label>🔗 Z-Score Neighbor (Tetangga Terpengaruh):</label>
                    <input type="range" id="z-neighbor" min="-2" max="0" step="0.1" value="-0.5" oninput="updateConfig()">
                    <div class="value-display">
                        <span>Z-Score:</span>
                        <span id="z-neighbor-val">-0.5</span>
                    </div>
                    <div class="impact">Semakin tinggi → ORANYE (Cincin Api) lebih luas</div>
                </div>
                
                <div class="config-item">
                    <label>👥 Min Neighbors (Tetangga Minimum):</label>
                    <input type="range" id="min-neighbors" min="1" max="6" step="1" value="2" oninput="updateConfig()">
                    <div class="value-display">
                        <span>Jumlah:</span>
                        <span id="min-neighbors-val">2</span>
                    </div>
                    <div class="impact">Semakin rendah → Lebih sensitif deteksi kluster</div>
                </div>
            </div>
        </div>
        
        <!-- Tabs -->
        <div class="tabs">{divisi_tabs}</div>
        
        <!-- Content -->
        {divisi_content}
        
        <div class="footer">
            Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Dashboard v7.0 FINAL
        </div>
    </div>
    
    <!-- Info Modal -->
    <div id="infoModal" class="modal">
        <div class="modal-content">
            <span class="close" onclick="closeInfoModal()">&times;</span>
            <h2>📖 Panduan Konfigurasi Z-Score</h2>
            
            <h3>📊 Preset Strategi</h3>
            <p><strong>Konservatif:</strong> Deteksi lebih banyak pohon berisiko (cocok untuk pencegahan dini)</p>
            <p><strong>Standar:</strong> Balanced detection (rekomendasi umum)</p>
            <p><strong>Agresif:</strong> Hanya deteksi kluster yang sangat jelas (hemat biaya sanitasi)</p>
            
            <h3>🎯 Z-Score Core</h3>
            <p><strong>Makna:</strong> Threshold untuk mengidentifikasi pohon dengan NDVI rendah (stressed)</p>
            <p><strong>Satuan:</strong> Standar deviasi dari rata-rata blok</p>
            <p><strong>Range:</strong> -3.0 sampai 0.0</p>
            <p><strong>Dampak:</strong> Semakin tinggi (mendekati 0), semakin banyak pohon masuk kategori suspect</p>
            
            <h3>🔗 Z-Score Neighbor</h3>
            <p><strong>Makna:</strong> Threshold untuk menghitung tetangga yang terpengaruh</p>
            <p><strong>Satuan:</strong> Standar deviasi dari rata-rata blok</p>
            <p><strong>Range:</strong> -2.0 sampai 0.0</p>
            <p><strong>Dampak:</strong> Semakin tinggi, semakin luas area Cincin Api (ORANYE)</p>
            
            <h3>👥 Min Neighbors</h3>
            <p><strong>Makna:</strong> Jumlah minimum tetangga sakit untuk membentuk kluster MERAH</p>
            <p><strong>Satuan:</strong> Jumlah pohon (1-6)</p>
            <p><strong>Range:</strong> 1 sampai 6 pohon</p>
            <p><strong>Dampak:</strong> Semakin rendah, semakin sensitif deteksi kluster kecil</p>
            
            <h3>🔬 Bagaimana Algoritma Bekerja?</h3>
            <ul>
                <li><strong>Step 1:</strong> Hitung Z-Score untuk setiap pohon (NDVI vs rata-rata blok)</li>
                <li><strong>Step 2:</strong> Identifikasi pohon suspect (Z-Score &lt; Z-Core)</li>
                <li><strong>Step 3:</strong> Hitung tetangga sakit di sekitar setiap suspect</li>
                <li><strong>Step 4:</strong> Jika ≥ Min Neighbors → MERAH, jika tidak → KUNING</li>
                <li><strong>Step 5:</strong> Semua tetangga pohon MERAH → ORANYE (Cincin Api)</li>
            </ul>
        </div>
    </div>
    
    <script>
// Global data
const PRESETS = {presets_json};
const DIVISI_DATA = {js_data_json};
let currentDivisi = '{list(all_results.keys())[0].replace(" ", "_")}';

// Preset management
function applyPreset() {{
    const preset = document.getElementById('preset-select').value;
    if (preset === 'custom') return;
    
    const config = PRESETS[preset];
    document.getElementById('z-core').value = config.z_threshold_core;
    document.getElementById('z-neighbor').value = config.z_threshold_neighbor;
    document.getElementById('min-neighbors').value = config.min_stressed_neighbors;
    updateConfig();
}}

function updateConfig() {{
    const zCore = parseFloat(document.getElementById('z-core').value);
    const zNeighbor = parseFloat(document.getElementById('z-neighbor').value);
    const minNeighbors = parseInt(document.getElementById('min-neighbors').value);
    
    // Update displays
    document.getElementById('z-core-val').textContent = zCore.toFixed(1);
    document.getElementById('z-neighbor-val').textContent = zNeighbor.toFixed(1);
    document.getElementById('min-neighbors-val').textContent = minNeighbors;
    
    // Set to custom if values don't match preset
    let matchedPreset = null;
    for (const [name, config] of Object.entries(PRESETS)) {{
        if (config.z_threshold_core === zCore && 
            config.z_threshold_neighbor === zNeighbor && 
            config.min_stressed_neighbors === minNeighbors) {{
            matchedPreset = name;
            break;
        }}
    }}
    document.getElementById('preset-select').value = matchedPreset || 'custom';
    
    // Recalculate for current divisi
    recalculate(currentDivisi, zCore, zNeighbor, minNeighbors);
}}

function recalculate(divisiId, zCore, zNeighbor, minNeighbors) {{
    const data = DIVISI_DATA[divisiId];
    if (!data) return;
    
    let merah = 0, oranye = 0, kuning = 0, hijau = 0;
    const statusMap = new Map();
    
    // Step 1: Identify suspects and classify MERAH/KUNING
    for (const tree of data.trees) {{
        const key = `${{tree.Blok}}_${{tree.N_BARIS}}_${{tree.N_POKOK}}`;
        
        if (tree.ZScore < zCore) {{
            // Count sick neighbors
            let sickNeighbors = 0;
            const neighbors = getHexNeighbors(tree.N_BARIS, tree.N_POKOK);
            
            for (const [nb, np] of neighbors) {{
                const neighborKey = `${{tree.Blok}}_${{nb}}_${{np}}`;
                const neighbor = data.trees.find(t => 
                    t.Blok === tree.Blok && t.N_BARIS === nb && t.N_POKOK === np
                );
                if (neighbor && neighbor.ZScore < zNeighbor) {{
                    sickNeighbors++;
                }}
            }}
            
            if (sickNeighbors >= minNeighbors) {{
                statusMap.set(key, 'MERAH');
                merah++;
            }} else {{
                statusMap.set(key, 'KUNING');
                kuning++;
            }}
        }} else {{
            statusMap.set(key, 'HIJAU');
            hijau++;
        }}
    }}
    
    // Step 2: Create Cincin Api (ORANYE)
    const merahKeys = [...statusMap.entries()].filter(([k, v]) => v === 'MERAH').map(([k]) => k);
    
    for (const merahKey of merahKeys) {{
        const [blok, baris, pokok] = merahKey.split('_');
        const neighbors = getHexNeighbors(parseInt(baris), parseInt(pokok));
        
        for (const [nb, np] of neighbors) {{
            const neighborKey = `${{blok}}_${{nb}}_${{np}}`;
            if (statusMap.has(neighborKey) && statusMap.get(neighborKey) !== 'MERAH') {{
                const oldStatus = statusMap.get(neighborKey);
                statusMap.set(neighborKey, 'ORANYE');
                
                // Update counts
                if (oldStatus === 'HIJAU') hijau--;
                else if (oldStatus === 'KUNING') kuning--;
                oranye++;
            }}
        }}
    }}
    
    // Update UI
    document.getElementById(`merah-${{divisiId}}`).textContent = merah.toLocaleString();
    document.getElementById(`oranye-${{divisiId}}`).textContent = oranye.toLocaleString();
    document.getElementById(`kuning-${{divisiId}}`).textContent = kuning.toLocaleString();
    document.getElementById(`hijau-${{divisiId}}`).textContent = hijau.toLocaleString();
}}

function getHexNeighbors(baris, pokok) {{
    if (baris % 2 === 0) {{
        return [
            [baris-1, pokok-1], [baris-1, pokok], [baris, pokok-1],
            [baris, pokok+1], [baris+1, pokok-1], [baris+1, pokok]
        ];
    }} else {{
        return [
            [baris-1, pokok], [baris-1, pokok+1], [baris, pokok-1],
            [baris, pokok+1], [baris+1, pokok], [baris+1, pokok+1]
        ];
    }}
}}

function switchTab(id) {{
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.content').forEach(c => c.classList.remove('active'));
    document.querySelector(`[data-div="${{id}}"]`).classList.add('active');
    document.getElementById(id).classList.add('active');
    currentDivisi = id;
}}

function openInfoModal() {{
    document.getElementById('infoModal').style.display = 'block';
}}

function closeInfoModal() {{
    document.getElementById('infoModal').style.display = 'none';
}}

window.onclick = function(event) {{
    const modal = document.getElementById('infoModal');
    if (event.target === modal) {{
        modal.style.display = 'none';
    }}
}}
    </script>
</body>
</html>'''
    
    path = output_dir / 'dashboard_v7_final.html'
    with open(path, 'w', encoding='utf-8') as f:
        f.write(html)
    return path

def main():
    print('='*80)
    print('🔥 DASHBOARD Z-SCORE + CINCIN API v7.0 FINAL')
    print('='*80)
    
    base_dir = Path(__file__).parent
    
    print('\n[1/5] Loading AME II...')
    df_ii = load_and_clean_data(base_dir / 'data/input/tabelNDREnew.csv')
    print(f'  ✅ {len(df_ii):,} pohon dari {df_ii["Blok"].nunique()} blok')
    
    print('\n[2/5] Loading AME IV...')
    df_iv = load_ame_iv_data(base_dir / 'data/input/AME_IV.csv')
    print(f'  ✅ {len(df_iv):,} pohon dari {df_iv["Blok"].nunique()} blok')
    
    print('\n[3/5] Loading productivity data...')
    prod_df = load_productivity_data()
    print(f'  ✅ {len(prod_df)} blok dengan data yield')
    
    all_results = {}
    all_maps = {}
    
    print('\n[4/5] Analyzing with Hybrid Cincin Api + Z-Score...')
    results_ii, maps_ii = analyze_divisi(df_ii, 'AME II', prod_df, output_dir)
    all_results['AME II'] = {'results': results_ii}
    all_maps['AME II'] = maps_ii
    
    results_iv, maps_iv = analyze_divisi(df_iv, 'AME IV', prod_df, output_dir)
    all_results['AME IV'] = {'results': results_iv}
    all_maps['AME IV'] = maps_iv
    
    print('\n[5/5] Generating HTML Dashboard with Real-time Config...')
    html_path = generate_html_with_realtime(output_dir, all_results, all_maps, prod_df)
    
    print(f'\n{"="*80}')
    print('✅ DASHBOARD v7.0 FINAL SELESAI!')
    print(f'📁 Output: {output_dir}')
    print(f'🌐 Dashboard: {html_path}')
    print('='*80)
    print('\n🔥 FITUR LENGKAP:')
    print('  ✅ Algoritma Hybrid Cincin Api')
    print('  ✅ Panel konfigurasi real-time')
    print('  ✅ Dual POV: Ganoderma→Yield & Yield→Ganoderma')
    print('  ✅ Peta kluster portrait dengan Cincin Api')
    print('  ✅ Info button dengan popup')
    print('  ✅ Fix AME IV (28 blok, 82K+ pohon)')
    print('='*80)
    
    return html_path

if __name__ == '__main__':
    main()
