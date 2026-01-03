import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path
import os
import json

print("="*80)
print("🔥 GENERATING 90% SIMILAR CINCIN API MAPS (SOP STYLE)")
print("="*80)

# Load NDRE data
input_file = 'data/input/tabelNDREnew.csv'
if not os.path.exists(input_file):
    input_file = 'poac_sim/data/input/tabelNDREnew.csv'

df = pd.read_csv(input_file)
df.columns = [c.upper().strip() for c in df.columns]

# Output directory
output_dir = Path('data/output')
output_dir.mkdir(parents=True, exist_ok=True)

# Status colors matching poac_sim/src/dashboard.py
STATUS_COLORS = {
    "MERAH": "#e74c3c",       # Merah - Target Sanitasi
    "ORANYE": "#e67e22",      # Oranye - Target APH (Trichoderma)
    "KUNING": "#f1c40f",      # Kuning - Investigasi
    "HIJAU": "#27ae60"        # Hijau - Normal
}

def get_hex_neighbors(r: int, p: int) -> list:
    """Hexagonal neighbor logic mapping to Logika B - Spatial Hexagonal"""
    neighbors = []
    if r % 2 != 0:  # Baris GANJIL
        neighbors = [(r - 1, p - 1), (r - 1, p), (r, p - 1), (r, p + 1), (r + 1, p - 1), (r + 1, p)]
    else:  # Baris GENAP
        neighbors = [(r - 1, p), (r - 1, p + 1), (r, p - 1), (r, p + 1), (r + 1, p), (r + 1, p + 1)]
    return neighbors

def generate_sop_style_map(df_ndre, block_name, output_path, rank=1):
    """Generate map mimicking _create_single_block_detail from poac_sim/src/dashboard.py"""
    
    # Filter for target block
    if 'BLOK_B' in df_ndre.columns:
        df_ndre['Blok_Filter'] = df_ndre['BLOK_B']
    elif 'BLOK' in df_ndre.columns:
        df_ndre['Blok_Filter'] = df_ndre['BLOK']
    
    df_ndre['Blok_Filter'] = df_ndre['Blok_Filter'].astype(str).str.strip().str.upper()
    df_block = df_ndre[df_ndre['Blok_Filter'] == block_name].copy()
    
    if len(df_block) < 10:
        return None

    # Calculate Z-scores (Percentile fallback for V8)
    if 'NDRE125' in df_block.columns:
        df_block['NDRE125'] = pd.to_numeric(df_block['NDRE125'].astype(str).str.replace(',', '.'), errors='coerce')
        df_block = df_block.dropna(subset=['NDRE125'])
    
    mean_v = df_block['NDRE125'].mean()
    std_v = df_block['NDRE125'].std()
    
    if std_v == 0:
        df_block['z'] = 0
    else:
        df_block['z'] = (df_block['NDRE125'] - mean_v) / std_v

    # Build coordinate lookup
    tree_map = {}
    for _, row in df_block.iterrows():
        x, y = int(row['N_POKOK']), int(row['N_BARIS'])
        tree_map[f"{x},{y}"] = {'x': x, 'y': y, 'z': row['z'], 'status': 'HIJAU'}

    # V8 Algorithm
    z_core, z_neighbor, min_neighbors = -1.5, -1.0, 3
    
    # Identify MERAH
    merah_coords = set()
    for key, tree in tree_map.items():
        if tree['z'] < z_core:
            sick_count = 0
            for nx, ny in get_hex_neighbors(tree['y'], tree['x']):
                nk = f"{nx},{ny}"
                if nk in tree_map and tree_map[nk]['z'] < z_neighbor:
                    sick_count += 1
            if sick_count >= min_neighbors:
                tree['status'] = 'MERAH'
                merah_coords.add((tree['y'], tree['x']))

    # Identify ORANYE (Cincin Api - Neighbors of MERAH)
    for ry, rx in merah_coords:
        for ny, nx in get_hex_neighbors(ry, rx):
            nk = f"{nx},{ny}"
            if nk in tree_map and tree_map[nk]['status'] == 'HIJAU':
                tree_map[nk]['status'] = 'ORANYE'

    # Identify KUNING (Suspect isolated)
    for key, tree in tree_map.items():
        if tree['status'] == 'HIJAU' and tree['z'] < z_core:
            tree['status'] = 'KUNING'

    # Visualization Setup (SOP STYLE)
    baris_range = df_block['N_BARIS'].max() - df_block['N_BARIS'].min() + 1
    pokok_range = df_block['N_POKOK'].max() - df_block['N_POKOK'].min() + 1
    fig_width = max(20, pokok_range * 0.25)
    fig_height = max(12, baris_range * 0.12)
    
    fig, ax = plt.subplots(figsize=(fig_width, fig_height), facecolor='white')
    
    # Layered plotting
    status_order = ['HIJAU', 'KUNING', 'ORANYE', 'MERAH']
    sizes = {'HIJAU': 60, 'KUNING': 140, 'ORANYE': 180, 'MERAH': 200}
    edge_widths = {'HIJAU': 0.5, 'KUNING': 1.5, 'ORANYE': 2.0, 'MERAH': 2.5}
    edge_colors = {'HIJAU': 'darkgreen', 'KUNING': 'olive', 'ORANYE': 'darkorange', 'MERAH': 'darkred'}
    
    counts = {'MERAH': 0, 'ORANYE': 0, 'KUNING': 0, 'HIJAU': 0}
    
    for status in status_order:
        plot_x, plot_y = [], []
        s_list, ec_list, ew_list = [], [], []
        
        for key, tree in tree_map.items():
            if tree['status'] == status:
                counts[status] += 1
                # Hexagonal offset logic
                x_offset = 0.5 if tree['y'] % 2 == 0 else 0
                plot_x.append(tree['x'] + x_offset)
                plot_y.append(tree['y'])
                s_list.append(sizes[status])
                ec_list.append(edge_colors[status])
                ew_list.append(edge_widths[status])
        
        if plot_x:
            ax.scatter(plot_x, plot_y, c=STATUS_COLORS[status], s=s_list, alpha=0.85,
                      edgecolors=ec_list, linewidths=ew_list, zorder=status_order.index(status)+1)

    # Styling
    ax.invert_yaxis()
    ax.grid(True, alpha=0.2, linestyle='--')
    ax.set_aspect('equal')
    ax.set_xlabel('Nomor Pokok (N_POKOK)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Nomor Baris (N_BARIS)', fontsize=12, fontweight='bold')
    
    # Title
    title_color = 'darkred' if rank <= 5 else 'black'
    ax.set_title(f'#{rank:02d} - BLOK {block_name} - PETA KLUSTER GANODERMA (CINCIN API SOP)\n'
                f'Total: {len(tree_map)} | 🔴 MERAH: {counts["MERAH"]} | 🟠 ORANYE: {counts["ORANYE"]} | 🟡 KUNING: {counts["KUNING"]}',
                fontsize=16, fontweight='bold', color=title_color, pad=20)

    # Legend
    legend_elements = [
        mpatches.Patch(color=STATUS_COLORS['MERAH'], label=f'MERAH - Kluster Aktif ({counts["MERAH"]})'),
        mpatches.Patch(color=STATUS_COLORS['ORANYE'], label=f'ORANYE - Cincin Api ({counts["ORANYE"]})'),
        mpatches.Patch(color=STATUS_COLORS['KUNING'], label=f'KUNING - Suspect ({counts["KUNING"]})'),
        mpatches.Patch(color=STATUS_COLORS['HIJAU'], label=f'HIJAU - Sehat ({counts["HIJAU"]})')
    ]
    ax.legend(handles=legend_elements, loc='upper right', framealpha=0.9, shadow=True)

    # Rank badge
    ax.text(0.01, 0.99, f'AME II - RANK #{rank}', transform=ax.transAxes, fontsize=14, 
            fontweight='bold', color='white', bbox=dict(boxstyle='round', facecolor=title_color, alpha=0.8),
            va='top')

    plt.tight_layout()
    plt.savefig(output_path, dpi=120, bbox_inches='tight')
    plt.close()
    return counts

# Run for all AME II
ame2_blocks = df[df['DIVISI'] == 'AME II']['BLOK_B'].unique()
print(f"📌 Found {len(ame2_blocks)} blocks in AME II.")

all_stats = {}
for i, block in enumerate(sorted(ame2_blocks)):
    print(f"[{i+1}/{len(ame2_blocks)}] Style SOP Rendering: {block}...", end=' ', flush=True)
    out_path = output_dir / f"cincin_api_map_{block}.png"
    stats = generate_sop_style_map(df, block, out_path, rank=i+1)
    if stats:
        all_stats[block] = stats
        print("✅")
    else:
        print("❌")

print("\n🎯 ALL AME II MAPS RE-GENERATED WITH SOP VISUAL STYLE!")
