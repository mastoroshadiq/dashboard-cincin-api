"""
Dashboard Z-Score + Cincin Api + Yield v7.0 FIXED
============================================
1. Algoritma Cincin Api dengan threshold Z-Score
2. Hybrid approach (Z-Score init + Cincin Api classification)
3. Dual POV: Ganoderma→Yield dan Yield→Ganoderma
"""
import sys
sys.path.insert(0, 'src')

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import json
import logging
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

from src.ingestion import load_and_clean_data
from config import ZSCORE_PRESETS

timestamp = datetime.now().strftime("%Y%m%d_%H%M")
output_dir = Path(f'data/output/dashboard_v7_fixed_{timestamp}')
output_dir.mkdir(parents=True, exist_ok=True)

def load_ame_iv_data(file_path):
    """Load AME IV data."""
    df = pd.read_csv(file_path, sep=';')
    
    # CRITICAL FIX: Use BLOK_B for actual block names (Blok column only contains 'IV')
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
        'col_11': 'Luas_Ha', 'col_170': 'Produksi_Ton', 
        'col_173': 'Potensi_Prod_Ton'  # col_173 is Potensi 2025 in Ton
    })
    
    df['Luas_Ha'] = pd.to_numeric(df['Luas_Ha'], errors='coerce')
    df['Tahun_Tanam'] = pd.to_numeric(df['Tahun_Tanam'], errors='coerce')
    df['Produksi_Ton'] = pd.to_numeric(df['Produksi_Ton'], errors='coerce')
    df['Potensi_Prod_Ton'] = pd.to_numeric(df['Potensi_Prod_Ton'], errors='coerce')
    
    # RECALCULATE Yield Realisasi = Produksi / Luas (col_11)
    # This ensures transparency and consistency with displayed Luas
    df['Yield_Realisasi'] = df['Produksi_Ton'] / df['Luas_Ha']
    df['Yield_Realisasi'] = df['Yield_Realisasi'].replace([np.inf, -np.inf], np.nan)
    
    # Calculate Potensi Yield = Potensi Prod (Ton) / Luas Ha
    df['Potensi_Yield'] = df['Potensi_Prod_Ton'] / df['Luas_Ha']
    df['Potensi_Yield'] = df['Potensi_Yield'].replace([np.inf, -np.inf], np.nan)
    
    # Calculate Gap = Potensi - Realisasi (in yield)
    df['Gap_Yield'] = df['Potensi_Yield'] - df['Yield_Realisasi']
    
    # Use Yield_Realisasi as main Yield column for compatibility
    df['Yield_TonHa'] = df['Yield_Realisasi']
    
    # Calculate plant age
    from datetime import datetime
    current_year = datetime.now().year
    df['Umur_Tahun'] = current_year - df['Tahun_Tanam']
    
    # Filter only productive blocks
    df_clean = df[['Blok_Prod', 'Divisi_Prod', 'Tahun_Tanam', 'Umur_Tahun', 'Luas_Ha',
                   'Produksi_Ton', 'Potensi_Prod_Ton', 'Yield_TonHa', 'Yield_Realisasi', 'Potensi_Yield', 'Gap_Yield']].dropna()
    df_clean = df_clean[(df_clean['Produksi_Ton'] > 0) & (df_clean['Yield_TonHa'] > 0)]
    
    return df_clean

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
    Hybrid: Z-Score untuk identifikasi suspect + Algoritma Cincin Api untuk klasifikasi.
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
    df['Status'] = 'HIJAU'
    df['Sick_Neighbors'] = 0
    df['Is_Cincin_Api'] = False
    
    suspect_mask = df['ZScore'] < z_core
    suspect_indices = df[suspect_mask].index.tolist()
    
    # Step 4: Count sick neighbors for suspects (TAHAP 1 Cincin Api)
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
        
        df.loc[idx, 'Sick_Neighbors'] = sick_count
        
        if sick_count >= min_neighbors:
            df.loc[idx, 'Status'] = 'MERAH'
        else:
            df.loc[idx, 'Status'] = 'KUNING'
    
    # Step 5: Create Cincin Api (TAHAP 2) - neighbors of MERAH become ORANYE
    merah_indices = df[df['Status'] == 'MERAH'].index.tolist()
    
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
                if df.loc[n_idx, 'Status'] != 'MERAH':
                    df.loc[n_idx, 'Status'] = 'ORANYE'
                    df.loc[n_idx, 'Is_Cincin_Api'] = True
    
    return df

def generate_cluster_map(df, blok, preset_name, rank, output_dir, divisi_id):
    """Generate matplotlib cluster map with proper Cincin Api visualization."""
    block_df = df[df['Blok'] == blok].copy().reset_index(drop=True)
    if len(block_df) == 0:
        return None
    
    merah = (block_df['Status'] == 'MERAH').sum()
    oranye = (block_df['Status'] == 'ORANYE').sum()
    kuning = (block_df['Status'] == 'KUNING').sum()
    hijau = (block_df['Status'] == 'HIJAU').sum()
    total = len(block_df)
    
    fig, ax = plt.subplots(figsize=(14, 12))
    
    colors = {'MERAH': '#e74c3c', 'ORANYE': '#e67e22', 'KUNING': '#f1c40f', 'HIJAU': '#27ae60'}
    sizes = {'MERAH': 80, 'ORANYE': 70, 'KUNING': 60, 'HIJAU': 50}
    
    # Apply hex offset and plot by layer
    for status in ['HIJAU', 'KUNING', 'ORANYE', 'MERAH']:
        mask = block_df['Status'] == status
        if not mask.any():
            continue
        subset = block_df[mask]
        x = subset['N_POKOK'] + np.where(subset['N_BARIS'] % 2 == 0, 0.5, 0)
        y = subset['N_BARIS']
        ax.scatter(x, y, c=colors[status], s=sizes[status], alpha=0.85,
                  edgecolors='black', linewidths=0.5, zorder=['HIJAU','KUNING','ORANYE','MERAH'].index(status)+1)
    
    legend = [mpatches.Patch(color=c, label=f'{s} ({(block_df["Status"]==s).sum()})') 
              for s, c in colors.items()]
    ax.legend(handles=legend, loc='upper right', fontsize=11, framealpha=0.9, shadow=True)
    
    ax.set_xlabel('Nomor Pokok (N_POKOK)', fontsize=12)
    ax.set_ylabel('Nomor Baris (N_BARIS)', fontsize=12)
    ax.set_title(f'#{rank:02d} - BLOK {blok}\nTotal: {total} | 🔴{merah} | 🟠{oranye} | 🟡{kuning}', 
                fontsize=14, fontweight='bold')
    ax.invert_yaxis()
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.set_aspect('equal')
    
    ax.text(0.02, 0.98, f'RANK #{rank}', transform=ax.transAxes, fontsize=16, fontweight='bold',
           color='white', bbox=dict(boxstyle='round', facecolor='#e74c3c' if rank<=3 else '#f39c12'),
           verticalalignment='top')
    
    preset_colors = {'konservatif': '#3498db', 'standar': '#27ae60', 'agresif': '#e74c3c'}
    ax.text(0.98, 0.98, preset_name.upper(), transform=ax.transAxes, fontsize=12, fontweight='bold',
           color='white', ha='right', va='top', 
           bbox=dict(boxstyle='round', facecolor=preset_colors.get(preset_name, '#333')))
    
    plt.tight_layout()
    
    divisi_dir = output_dir / divisi_id
    divisi_dir.mkdir(exist_ok=True)
    filename = f'cluster_{preset_name}_{rank:02d}_{blok}.png'
    fig.savefig(divisi_dir / filename, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    
    return {'filename': filename, 'blok': blok, 'rank': rank, 'merah': merah, 'oranye': oranye}

def analyze_divisi(df, divisi_name, prod_df, output_dir):
    """Analyze division with hybrid algorithm and yield correlation."""
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
        stats = {s: (df_classified['Status'] == s).sum() for s in ['MERAH', 'ORANYE', 'KUNING', 'HIJAU']}
        
        # Block-level stats
        block_stats = df_classified.groupby('Blok').agg({
            'Status': [lambda x: (x=='MERAH').sum(), lambda x: (x=='ORANYE').sum(), 'count']
        }).reset_index()
        block_stats.columns = ['Blok', 'MERAH', 'ORANYE', 'Total']
        block_stats['Attack_Pct'] = (block_stats['MERAH'] + block_stats['ORANYE']) / block_stats['Total'] * 100
        
        top_blocks = block_stats.nlargest(5, 'Attack_Pct')
        
        # Generate maps
        maps = []
        for rank, (_, row) in enumerate(top_blocks.iterrows(), 1):
            m = generate_cluster_map(df_classified, row['Blok'], preset_name, rank, output_dir, divisi_id)
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
    """Convert Ganoderma block (B16) to Productivity pattern (B016)."""
    import re
    match = re.match(r'([A-Z]+)(\d+)([A-Z]*)', str(gano_blok))
    if match:
        prefix, num, suffix = match.groups()
        return f"{prefix}{num.zfill(3)}"
    return str(gano_blok)

def convert_prod_to_gano_pattern(prod_blok):
    """Convert Productivity block (A012A) to Ganoderma pattern (A12)."""
    import re
    match = re.match(r'([A-Z]+)(\d+)([A-Z]*)', str(prod_blok))
    if match:
        prefix, num, suffix = match.groups()
        return f"{prefix}{int(num)}"
    return str(prod_blok)

def generate_html(output_dir, all_results, all_maps, prod_df):
    """Generate HTML with both POVs."""
    presets_json = json.dumps(ZSCORE_PRESETS)
    
    # Prepare data for JavaScript real-time recalculation
    js_divisi_data = {}
    for divisi, data in all_results.items():
        divisi_id = divisi.replace(' ', '_')
        results = data['results']
        df_full = results['standar']['df']
        
        # Extract essential tree data for JS
        tree_data = df_full[['Blok', 'N_BARIS', 'N_POKOK', 'ZScore', 'Mean_NDRE', 'SD_NDRE']].to_dict('records')
        
        js_divisi_data[divisi_id] = {
            'trees': tree_data,
            'total_trees': len(df_full),
            'total_blocks': df_full['Blok'].nunique()
        }
    
    js_data_json = json.dumps(js_divisi_data)
    
    divisi_tabs = ""
    divisi_content = ""
    
    for idx, (divisi, data) in enumerate(all_results.items()):
        divisi_id = divisi.replace(' ', '_')
        active = "active" if idx == 0 else ""
        
        results = data['results']
        block_maps = all_maps[divisi]
        stats = results['standar']['stats']
        
        # Build preset cards
        preset_cards = ""
        for p in ['konservatif', 'standar', 'agresif']:
            s = results[p]['stats']
            colors = {'konservatif': '#3498db', 'standar': '#27ae60', 'agresif': '#e74c3c'}
            preset_cards += f'''
            <div class="preset-card" style="border-top: 4px solid {colors[p]}">
                <h4>{p.upper()}</h4>
                <div class="stats-mini">
                    <span style="color:#e74c3c">🔴 {s['MERAH']:,}</span>
                    <span style="color:#e67e22">🟠 {s['ORANYE']:,}</span>
                    <span style="color:#f1c40f">🟡 {s['KUNING']:,}</span>
                    <span style="color:#27ae60">🟢 {s['HIJAU']:,}</span>
                </div>
            </div>'''
        
        # Build maps HTML
        maps_html = ""
        for p in ['konservatif', 'standar', 'agresif']:
            items = "".join([f'<div class="map-item"><img src="{divisi_id}/{m["filename"]}"><div class="map-label">{m["blok"]}</div></div>' 
                            for m in block_maps.get(p, [])])
            maps_html += f'<div class="maps-section"><h4>{p.upper()}</h4><div class="maps-grid">{items}</div></div>'
        
        # POV Tables
        block_stats = results['standar']['block_stats']
        top_gano = block_stats.nlargest(10, 'Attack_Pct')
        
        gano_rows = ""
        for i, (_, r) in enumerate(top_gano.iterrows(), 1):
            # FIXED: Convert B16 → B016 for matching
            prod_pattern = convert_gano_to_prod_pattern(r['Blok'])
            yield_matches = prod_df[prod_df['Blok_Prod'].str.contains(prod_pattern, na=False, regex=False)]
            
            # Filter only productive age (3-25 years) - exclude TBM (<3y) and old plants (>25y)
            if not yield_matches.empty:
                yield_matches = yield_matches[(yield_matches['Umur_Tahun'] >= 3) & (yield_matches['Umur_Tahun'] <= 25)]
            
            # Skip block if no productive age match
            if yield_matches.empty:
                continue
            
            # Get block names and metrics
            blok_prod_name = yield_matches['Blok_Prod'].iloc[0]
            luas_ha = yield_matches['Luas_Ha'].mean()
            produksi_real = yield_matches['Produksi_Ton'].mean()
            produksi_pot = yield_matches['Potensi_Prod_Ton'].mean()
            yield_val = yield_matches['Yield_TonHa'].mean()
            potensi_yield = yield_matches['Potensi_Yield'].mean()
            gap_yield = yield_matches['Gap_Yield'].mean()
            umur_val = int(yield_matches['Umur_Tahun'].mean())
            
            # Format values
            luas_str = f"{luas_ha:.1f}" if pd.notna(luas_ha) else "N/A"
            real_str = f"{produksi_real:.2f}" if pd.notna(produksi_real) else "N/A"
            pot_str = f"{produksi_pot:.2f}" if pd.notna(produksi_pot) else "N/A"
            gap_prod = (produksi_pot - produksi_real) if (pd.notna(produksi_pot) and pd.notna(produksi_real)) else None
            gap_prod_str = f"{gap_prod:.2f}" if pd.notna(gap_prod) else "N/A"
            umur_str = f"{umur_val} th" if pd.notna(umur_val) else "N/A"
            
            # Color code gap production (red if big gap, green if small)
            if pd.notna(gap_prod):
                if gap_prod > 30:
                    gap_color = "#e74c3c"  # Red - big gap (>30 Ton)
                elif gap_prod > 10:
                    gap_color = "#f39c12"  # Orange - medium gap (10-30 Ton)
                else:
                    gap_color = "#27ae60"  # Green - small gap (<10 Ton)
            else:
                gap_color = "#999"
            
            # Calculate impact/relevance indicator
            attack_pct = r["Attack_Pct"]
            if pd.notna(yield_val):
                # Define impact based on attack severity and yield level
                if attack_pct >= 50 and yield_val < 15:
                    impact = "🔴 TINGGI"
                    impact_color = "#e74c3c"
                elif attack_pct >= 20 and yield_val < 18:
                    impact = "🟠 SEDANG"
                    impact_color = "#e67e22"
                else:
                    impact = "🟡 RENDAH"
                    impact_color = "#f1c40f"
            else:
                impact = "❓ N/A"
                impact_color = "#999"
            
            # Format yield values
            yield_real_str = f"{yield_val:.2f}" if pd.notna(yield_val) else "N/A"
            yield_pot_str = f"{potensi_yield:.2f}" if pd.notna(potensi_yield) else "N/A"
            gap_yield_str = f"{gap_yield:.2f}" if pd.notna(gap_yield) else "N/A"
            
            gano_rows += f'<tr><td>{i}</td><td><b>{blok_prod_name}</b></td><td>{r["Total"]:,} pohon</td><td style="color:#e74c3c">{r["MERAH"]}</td><td style="color:#e67e22">{r["ORANYE"]}</td><td><b>{r["Attack_Pct"]:.1f}%</b></td><td>{luas_str}</td><td>{real_str}</td><td>{pot_str}</td><td style="color:{gap_color}"><b>{gap_prod_str}</b></td><td>{yield_real_str}</td><td>{yield_pot_str}</td><td>{gap_yield_str}</td><td>{umur_str}</td><td style="color:{impact_color}"><b>{impact}</b></td></tr>'
        
        # POV 2: Low yield blocks WITH RELEVANT Ganoderma attack (PRODUCTIVE PLANTS ONLY)
        yield_rows = ""
        if not prod_df.empty:
            # Filter only productive age (3-25 years) - exclude TBM (<3y) and old plants (>25y)
            productive_df = prod_df[(prod_df['Umur_Tahun'] >= 3) & (prod_df['Umur_Tahun'] <= 25)]
            if not productive_df.empty:
                low_yield = productive_df.nsmallest(20, 'Yield_TonHa')  # Get top 20 candidates
                
                # Filter for relevance: only show if attack % > 2% (Ganoderma-related)  
                relevant_blocks = []
                for _, r in low_yield.iterrows():
                    # FIXED: Convert A012A → A12 for matching
                    gano_pattern = convert_prod_to_gano_pattern(r['Blok_Prod'])
                    blok_match = block_stats[block_stats['Blok'].str.contains(gano_pattern, na=False, regex=False)]
                    attack = blok_match['Attack_Pct'].mean() if not blok_match.empty else 0
                    
                    # Only include if attack > 2% (relevant to Ganoderma)
                    # Threshold lowered from 5% to 2% for better coverage
                    if attack >= 2:
                        relevant_blocks.append({
                            'blok': r['Blok_Prod'],
                            'umur': int(r['Umur_Tahun']) if pd.notna(r['Umur_Tahun']) else 0,
                            'yield': r['Yield_TonHa'],
                            'luas': r['Luas_Ha'],
                            'attack': attack
                        })
                
                # Display top 10 relevant blocks
                for i, block in enumerate(relevant_blocks[:10], 1):
                    # Determine relevance strength
                    if block['attack'] >= 40:
                        relevance = "🔴 KUAT"
                        rel_color = "#e74c3c"
                    elif block['attack'] >= 20:
                        relevance = "🟠 SEDANG"
                        rel_color = "#e67e22"
                    else:
                        relevance = "🟡 LEMAH"
                        rel_color = "#f1c40f"
                    
                    yield_rows += f'<tr><td>{i}</td><td><b>{block["blok"]}</b></td><td>{block["umur"]} th</td><td>{block["yield"]:.3f}</td><td>{block["luas"]:.1f}</td><td><b>{block["attack"]:.1f}%</b></td><td style="color:{rel_color}"><b>{relevance}</b></td></tr>'
        
        divisi_tabs += f'<button class="tab {active}" onclick="switchTab(\'{divisi_id}\')" data-div="{divisi_id}">{divisi}</button>'
        
        divisi_content += f'''
        <div class="content {active}" id="{divisi_id}">
            <div class="header-info"><h2>📍 {divisi}</h2><span>🌳 {results["standar"]["total"]:,} pohon | 📦 {results["standar"]["blocks"]} blok</span></div>
            
            <div class="stats-grid">
                <div class="stat-card merah"><div class="val">{stats["MERAH"]:,}</div><div class="lbl">🔴 MERAH</div></div>
                <div class="stat-card oranye"><div class="val">{stats["ORANYE"]:,}</div><div class="lbl">🟠 ORANYE</div></div>
                <div class="stat-card kuning"><div class="val">{stats["KUNING"]:,}</div><div class="lbl">🟡 KUNING</div></div>
                <div class="stat-card hijau"><div class="val">{stats["HIJAU"]:,}</div><div class="lbl">🟢 HIJAU</div></div>
            </div>
            
            <section><h3>📊 Perbandingan Preset</h3><div class="preset-grid">{preset_cards}</div></section>
            
            <section><h3>🗺️ Peta Kluster Cincin Api (Top 5)</h3>{maps_html}</section>
            
            <section class="pov-section">
                <h3>🔥 POV 1: Ganoderma → Produktivitas</h3>
                <p>Top 10 blok dengan serangan tertinggi dan analisis produktivitas lengkap<br><span style="color:#999; font-size:0.9em">📍 <b>Produksi</b> = Total Ton | <b>Yield</b> = Ton/Ha | <b>Filter</b> = Umur 3-25 tahun (produktif)</span></p>
                <table><thead><tr><th>#</th><th>Blok</th><th>Total Pohon</th><th>MERAH</th><th>ORANYE</th><th>% Attack</th><th>Luas (Ha)</th><th>Real Prod (Ton)</th><th>Pot Prod (Ton)</th><th>Gap Prod</th><th>Yield Real</th><th>Yield Pot</th><th>Gap Yield</th><th>Umur</th><th>Dampak</th></tr></thead>
                <tbody>{gano_rows}</tbody></table>
            </section>
            
            <section class="pov-section">
                <h3>📉 POV 2: Produktivitas → Ganoderma</h3>
                <p>Blok yield terendah DENGAN serangan Ganoderma (attack >2%)<br><span style="color:#999; font-size:0.9em">📌 Filter: Umur 3-25 tahun (produktif) + Attack >2% | <b>Relevansi</b> = Kekuatan korelasi serangan dengan yield rendah</span></p>
                <table><thead><tr><th>#</th><th>Blok</th><th>Umur</th><th>Yield</th><th>Luas</th><th>% Attack</th><th>Relevansi</th></tr></thead>
                <tbody>{yield_rows if yield_rows else "<tr><td colspan='7'>Tidak ada blok dengan yield rendah + serangan signifikan</td></tr>"}</tbody></table>
            </section>
        </div>'''
    
    html = f'''<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Dashboard Z-Score + Cincin Api v7.0 FIXED</title>
<style>
:root {{ --merah:#e74c3c; --oranye:#e67e22; --kuning:#f1c40f; --hijau:#27ae60; --dark:#1a1a2e; }}
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family:'Segoe UI',sans-serif; background:linear-gradient(135deg,#1a1a2e,#16213e); color:#fff; min-height:100vh; }}
.header {{ text-align:center; padding:30px; background:rgba(255,255,255,0.05); border-bottom:3px solid var(--oranye); }}
.header h1 {{ font-size:2.5rem; background:linear-gradient(45deg,#ff6b6b,#ffa500,#00ff88); -webkit-background-clip:text; -webkit-text-fill-color:transparent; }}
.container {{ max-width:1800px; margin:auto; padding:20px; }}
.tabs {{ display:flex; gap:15px; justify-content:center; margin:20px 0; }}
.tab {{ padding:15px 40px; border:none; border-radius:30px; font-size:1.1rem; cursor:pointer; color:#fff; background:#3498db; transition:0.3s; }}
.tab.active {{ background:var(--oranye); box-shadow:0 5px 20px rgba(0,0,0,0.3); }}
.content {{ display:none; }}
.content.active {{ display:block; }}
.header-info {{ display:flex; justify-content:space-between; padding:20px; background:rgba(255,255,255,0.05); border-radius:15px; margin-bottom:20px; }}
.stats-grid {{ display:grid; grid-template-columns:repeat(4,1fr); gap:20px; margin-bottom:25px; }}
.stat-card {{ background:rgba(255,255,255,0.08); padding:25px; border-radius:15px; text-align:center; border-left:5px solid; }}
.stat-card.merah {{ border-color:var(--merah); }} .stat-card.oranye {{ border-color:var(--oranye); }}
.stat-card.kuning {{ border-color:var(--kuning); }} .stat-card.hijau {{ border-color:var(--hijau); }}
.stat-card .val {{ font-size:2.5rem; font-weight:bold; }}
.stat-card.merah .val {{ color:var(--merah); }} .stat-card.oranye .val {{ color:var(--oranye); }}
.stat-card.kuning .val {{ color:var(--kuning); }} .stat-card.hijau .val {{ color:var(--hijau); }}
section {{ background:rgba(255,255,255,0.05); border-radius:20px; padding:25px; margin-bottom:25px; }}
section h3 {{ color:#00d9ff; margin-bottom:15px; padding-bottom:10px; border-bottom:2px solid rgba(0,217,255,0.3); }}
.preset-grid {{ display:grid; grid-template-columns:repeat(3,1fr); gap:20px; }}
.preset-card {{ background:rgba(0,0,0,0.2); border-radius:15px; padding:20px; text-align:center; }}
.preset-card h4 {{ margin-bottom:10px; }}
.stats-mini {{ display:flex; gap:15px; justify-content:center; flex-wrap:wrap; }}
.maps-section {{ margin-bottom:20px; }}
.maps-section h4 {{ margin-bottom:10px; }}
.maps-grid {{ display:grid; grid-template-columns:repeat(5,1fr); gap:15px; }}
.map-item {{ background:rgba(0,0,0,0.3); border-radius:10px; overflow:hidden; cursor:pointer; }}
.map-item img {{ width:100%; }}
.map-label {{ padding:10px; text-align:center; background:rgba(0,0,0,0.5); }}
.pov-section p {{ color:#aaa; margin-bottom:15px; }}

/* Config Panel Styles */
.config-panel {{ background:rgba(255,107,107,0.1); border:2px solid rgba(255,107,107,0.3); border-radius:20px; padding:25px; margin:20px 0; }}
.config-header {{ display:flex; justify-content:space-between; align-items:center; margin-bottom:20px; }}
.config-header h3 {{ color:#00d9ff; display:flex; align-items:center; gap:10px; margin:0; }}
.info-btn {{ background:#3498db; color:#fff; border:none; border-radius:50%; width:35px; height:35px; font-size:18px; cursor:pointer; transition:0.3s; box-shadow:0 2px 10px rgba(52,152,219,0.3); }}
.info-btn:hover {{ background:#2980b9; transform:scale(1.1); }}
.config-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(280px,1fr)); gap:20px; }}
.config-item {{ background:rgba(0,0,0,0.3); padding:20px; border-radius:15px; border:1px solid rgba(0,217,255,0.2); }}
.config-item label {{ display:block; color:#00d9ff; margin-bottom:10px; font-weight:600; font-size:0.95rem; }}
.config-item select {{ width:100%; padding:12px; border-radius:8px; border:2px solid rgba(0,217,255,0.3); background:rgba(255,255,255,0.1); color:#fff; font-size:16px; cursor:pointer; }}
.config-item input[type="range"] {{ width:100%; height:8px; border-radius:5px; background:linear-gradient(to right,#e74c3c,#f39c12,#27ae60); outline:none; }}
.config-item input[type="range"]::-webkit-slider-thumb {{ width:20px; height:20px; border-radius:50%; background:#00d9ff; cursor:pointer; box-shadow:0 0 10px rgba(0,217,255,0.5); }}
.value-display {{ display:flex; justify-content:space-between; margin-top:8px; color:#aaa; font-size:14px; }}
.value-display span:last-child {{ color:#00d9ff; font-weight:bold; }}
.impact {{ margin-top:12px; padding:12px; background:rgba(0,0,0,0.4); border-radius:8px; border-left:3px solid #ffd700; font-size:13px; color:#ffd700; line-height:1.5; }}

/* Info Modal Styles */
.modal {{ display:none; position:fixed; z-index:9999; left:0; top:0; width:100%; height:100%; background:rgba(0,0,0,0.85); }}
.modal.active {{ display:flex; justify-content:center; align-items:center; }}
.modal-content {{ background:linear-gradient(135deg,#1e3c72,#2a5298); margin:5% auto; padding:35px; border-radius:20px; max-width:850px; max-height:85vh; overflow-y:auto; box-shadow:0 10px 50px rgba(0,0,0,0.7); border:2px solid #00d9ff; }}
.close {{ color:#fff; float:right; font-size:35px; font-weight:bold; cursor:pointer; line-height:25px; transition:0.3s; }}
.close:hover {{ color:#ff6b6b; transform:rotate(90deg); }}
.modal-content h2 {{ color:#00d9ff; margin-bottom:25px; padding-bottom:15px; border-bottom:2px solid rgba(0,217,255,0.3); }}
.modal-content h3 {{ color:#ffa500; margin-top:25px; margin-bottom:15px; }}
.modal-content p {{ line-height:1.8; margin-bottom:15px; color:#ddd; }}
.modal-content ul {{ margin-left:25px; margin-bottom:20px; }}
.modal-content li {{ margin-bottom:10px; line-height:1.6; }}
.modal-content strong {{ color:#00d9ff; }}

table {{ width:100%; border-collapse:collapse; }}
th,td {{ padding:12px; text-align:left; border-bottom:1px solid rgba(255,255,255,0.1); }}
th {{ background:rgba(0,0,0,0.3); color:#00d9ff; }}
tr:hover {{ background:rgba(255,255,255,0.05); }}
.footer {{ text-align:center; padding:30px; color:#666; }}
@media(max-width:1200px) {{ .stats-grid,.preset-grid {{ grid-template-columns:repeat(2,1fr); }} .maps-grid {{ grid-template-columns:repeat(3,1fr); }} }}
</style></head>
<body>
<div class="header"><h1>🔥 DASHBOARD Z-SCORE + CINCIN API v7.0 FIXED</h1><p>Hybrid Detection • Korelasi Produktivitas DIPERBAIKI</p></div>
<div class="container">
    <!-- Configuration Panel -->
    <div class="config-panel">
        <div class="config-header">
            <h3>⚙️ KONFIGURASI THRESHOLD Z-SCORE</h3>
            <button class="info-btn" onclick="openInfoModal()" title="Bantuan">❓</button>
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
                <div class="impact">💡 Semakin tinggi → Lebih banyak pohon dianggap MERAH</div>
            </div>
            
            <div class="config-item">
                <label>🔗 Z-Score Neighbor (Tetangga Terpengaruh):</label>
                <input type="range" id="z-neighbor" min="-2" max="0" step="0.1" value="-0.5" oninput="updateConfig()">
                <div class="value-display">
                    <span>Z-Score:</span>
                    <span id="z-neighbor-val">-0.5</span>
                </div>
                <div class="impact">💡 Semakin tinggi → ORANYE (Cincin Api) lebih luas</div>
            </div>
            
            <div class="config-item">
                <label>👥 Min Neighbors (Tetangga Minimum):</label>
                <input type="range" id="min-neighbors" min="1" max="6" step="1" value="2" oninput="updateConfig()">
                <div class="value-display">
                    <span>Jumlah:</span>
                    <span id="min-neighbors-val">2</span>
                </div>
                <div class="impact">💡 Semakin rendah → Lebih sensitif deteksi kluster</div>
            </div>
        </div>
    </div>
    
<div class="tabs">{divisi_tabs}</div>
{divisi_content}
<div class="footer">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
</div>

<!-- Info Modal -->
<div id="infoModal" class="modal">
    <div class="modal-content">
        <span class="close" onclick="closeInfoModal()">&times;</span>
        <h2>📖 Panduan Konfigurasi Z-Score + Cincin Api</h2>
        
        <h3>📊 Preset Strategi</h3>
        <p><strong>Konservatif:</strong> Deteksi lebih banyak pohon berisiko (cocok untuk pencegahan dini dan treatment agresif)</p>
        <p><strong>Standar:</strong> Balanced detection (rekomendasi umum untuk monitoring rutin)</p>
        <p><strong>Agresif:</strong> Hanya deteksi kluster yang sangat jelas (hemat biaya sanitasi, fokus pada kasus parah)</p>
        
        <h3>🎯 Z-Score Core (Threshold Kluster Aktif)</h3>
        <p><strong>Makna:</strong> Threshold untuk mengidentifikasi pohon dengan NDVI rendah (stressed/terinfeksi)</p>
        <p><strong>Satuan:</strong> Standar deviasi dari rata-rata blok</p>
        <p><strong>Range:</strong> -3.0 sampai 0.0</p>
        <p><strong>Dampak:</strong> Semakin tinggi (mendekati 0), semakin banyak pohon masuk kategori suspect (MERAH/KUNING)</p>
        
        <h3>🔗 Z-Score Neighbor (Threshold Tetangga)</h3>
        <p><strong>Makna:</strong> Threshold untuk menghitung tetangga yang terpengaruh di sekitar pohon suspect</p>
        <p><strong>Satuan:</strong> Standar deviasi dari rata-rata blok</p>
        <p><strong>Range:</strong> -2.0 sampai 0.0</p>
        <p><strong>Dampak:</strong> Semakin tinggi, semakin luas area Cincin Api (ORANYE)</p>
        
        <h3>👥 Min Neighbors (Tetangga Minimum)</h3>
        <p><strong>Makna:</strong> Jumlah minimum tetangga sakit untuk membentuk kluster MERAH (infected cluster)</p>
        <p><strong>Satuan:</strong> Jumlah pohon (1-6)</p>
        <p><strong>Range:</strong> 1 sampai 6 pohon</p>
        <p><strong>Dampak:</strong> Semakin rendah, semakin sensitif deteksi kluster kecil (isolated cases juga terdeteksi)</p>
        
        <h3>🔬 Bagaimana Algoritma Hybrid Bekerja?</h3>
        <ul>
            <li><strong>Step 1 (Z-Score Detection):</strong> Hitung Z-Score untuk setiap pohon (NDVI vs rata-rata blok)</li>
            <li><strong>Step 2 (Suspect Identification):</strong> Identifikasi pohon suspect (Z-Score &lt; Z-Core)</li>
            <li><strong>Step 3 (Neighbor Count):</strong> Hitung tetangga sakit (Z-Score &lt; Z-Neighbor) di sekitar setiap suspect</li>
            <li><strong>Step 4 (Cluster Classification):</strong> Jika ≥ Min Neighbors → MERAH, jika tidak → KUNING</li>
            <li><strong>Step 5 (Cincin Api):</strong> Semua tetangga pohon MERAH → ORANYE (ring of fire effect)</li>
        </ul>
        
        <p style="margin-top:20px; padding:15px; background:rgba(0,217,255,0.1); border-radius:10px; border-left:4px solid #00d9ff;">
            <strong>💡 Tips:</strong> Mulai dengan preset Standar, lalu adjust berdasarkan kondisi lapangan. 
            Gunakan Konservatif jika ingin deteksi dini maksimal, atau Agresif jika budget treatment terbatas.
        </p>
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
    
    // Auto-detect preset match
    let matchedPreset = null;
    for (const [name, config] of Object.entries(PRESETS)) {{
        if (Math.abs(config.z_threshold_core - zCore) < 0.01 && 
            Math.abs(config.z_threshold_neighbor - zNeighbor) < 0.01 && 
            config.min_stressed_neighbors === minNeighbors) {{
            matchedPreset = name;
            break;
        }}
    }}
    document.getElementById('preset-select').value = matchedPreset || 'custom';
    
    // Recalculate for current divisi
    recalculateStats(currentDivisi, zCore, zNeighbor, minNeighbors);
}}

function recalculateStats(divisiId, zCore, zNeighbor, minNeighbors) {{
    const data = DIVISI_DATA[divisiId];
    if (!data) return;
    
    let merah = 0, oranye = 0, kuning = 0, hijau = 0;
    const statusMap = new Map();
    const coordLookup = new Map();
    
    // Build coordinate lookup
    for (const tree of data.trees) {{
        const key = `${{tree.Blok}}_${{tree.N_BARIS}}_${{tree.N_POKOK}}`;
        coordLookup.set(key, tree);
    }}
    
    // Step 1 & 2: Identify suspects based on Z-Score
    const suspects = [];
    for (const tree of data.trees) {{
        const key = `${{tree.Blok}}_${{tree.N_BARIS}}_${{tree.N_POKOK}}`;
        
        if (tree.ZScore < zCore) {{
            suspects.push(tree);
            statusMap.set(key, 'SUSPECT');
        }} else {{
            statusMap.set(key, 'HIJAU');
            hijau++;
        }}
    }}
    
    // Step 3 & 4: Count neighbors and classify MERAH/KUNING
    for (const tree of suspects) {{
        const key = `${{tree.Blok}}_${{tree.N_BARIS}}_${{tree.N_POKOK}}`;
        const neighbors = getHexNeighbors(tree.N_BARIS, tree.N_POKOK);
        
        let sickCount = 0;
        for (const [nb, np] of neighbors) {{
            const nKey = `${{tree.Blok}}_${{nb}}_${{np}}`;
            const neighbor = coordLookup.get(nKey);
            if (neighbor && neighbor.ZScore < zNeighbor) {{
                sickCount++;
            }}
        }}
        
        if (sickCount >= minNeighbors) {{
            statusMap.set(key, 'MERAH');
            merah++;
        }} else {{
            statusMap.set(key, 'KUNING');
            kuning++;
        }}
    }}
    
    // Step 5: Create Cincin Api (ORANYE)
    const merahTrees = [];
    for (const [key, status] of statusMap.entries()) {{
        if (status === 'MERAH') {{
            const [blok, baris, pokok] = key.split('_');
            merahTrees.push({{ blok, baris: parseInt(baris), pokok: parseInt(pokok) }});
        }}
    }}
    
    for (const tree of merahTrees) {{
        const neighbors = getHexNeighbors(tree.baris, tree.pokok);
        for (const [nb, np] of neighbors) {{
            const nKey = `${{tree.blok}}_${{nb}}_${{np}}`;
            if (statusMap.has(nKey) && statusMap.get(nKey) !== 'MERAH') {{
                const oldStatus = statusMap.get(nKey);
                statusMap.set(nKey, 'ORANYE');
                
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
    document.getElementById('infoModal').classList.add('active');
}}

function closeInfoModal() {{
    document.getElementById('infoModal').classList.remove('active');
}}

window.onclick = function(event) {{
    const modal = document.getElementById('infoModal');
    if (event.target === modal) {{
        modal.classList.remove('active');  
    }}
}}
</script>
</body></html>'''
    
    path = output_dir / 'dashboard_v7_fixed.html'
    with open(path, 'w', encoding='utf-8') as f:
        f.write(html)
    return path

def main():
    print('='*70)
    print('🔥 DASHBOARD Z-SCORE + CINCIN API + YIELD v7.0 FIXED')
    print('='*70)
    
    base_dir = Path(__file__).parent
    
    print('\n[1/5] Loading AME II...')
    df_ii = load_and_clean_data(base_dir / 'data/input/tabelNDREnew.csv')
    print(f'  ✅ {len(df_ii):,} pohon')
    
    print('\n[2/5] Loading AME IV...')
    df_iv = load_ame_iv_data(base_dir / 'data/input/AME_IV.csv')
    print(f'  ✅ {len(df_iv):,} pohon')
    
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
    
    print('\n[5/5] Generating HTML Dashboard...')
    html_path = generate_html(output_dir, all_results, all_maps, prod_df)
    
    print(f'\n{"="*70}')
    print(f'✅ DASHBOARD v6.0 SELESAI!')
    print(f'📁 Output: {output_dir}')
    print(f'🌐 Dashboard: {html_path}')
    print('='*70)
    
    return html_path

if __name__ == '__main__':
    main()
