import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path
import os
import json

print("="*80)
print("🛠️  FIXING COORDINATE BUG & RE-GENERATING SOP MAPS")
print("="*80)

# Load data
input_file = 'data/input/tabelNDREnew.csv'
if not os.path.exists(input_file):
    input_file = 'poac_sim/data/input/tabelNDREnew.csv'

df = pd.read_csv(input_file)
df.columns = [c.upper().strip() for c in df.columns]

output_dir = Path('data/output')
output_dir.mkdir(parents=True, exist_ok=True)

STATUS_COLORS = {
    "MERAH": "#e74c3c",
    "ORANYE": "#e67e22",
    "KUNING": "#f1c40f",
    "HIJAU": "#27ae60"
}

def get_hex_neighbors(r: int, p: int) -> list:
    """Correct Hexagonal Neighbor Logic (Returns List of (Row, Pokok))"""
    if r % 2 != 0:  # Baris GANJIL
        return [(r - 1, p - 1), (r - 1, p), (r, p - 1), (r, p + 1), (r + 1, p - 1), (r + 1, p)]
    else:  # Baris GENAP
        return [(r - 1, p), (r - 1, p + 1), (r, p - 1), (r, p + 1), (r + 1, p), (r + 1, p + 1)]

def generate_sop_style_map_fixed(df_ndre, block_name, output_path, rank=1):
    if 'BLOK_B' in df_ndre.columns:
        df_ndre['Blok_Filter'] = df_ndre['BLOK_B']
    else:
        df_ndre['Blok_Filter'] = df_ndre['BLOK']
    
    df_block = df_ndre[df_ndre['Blok_Filter'].astype(str).str.strip().str.upper() == block_name].copy()
    if len(df_block) < 10: return None

    # Precise NDRE Conversion
    df_block['NDRE125'] = pd.to_numeric(df_block['NDRE125'].astype(str).str.replace(',', '.'), errors='coerce')
    df_block = df_block.dropna(subset=['NDRE125'])
    
    # Z-Score Calculation
    mean_v, std_v = df_block['NDRE125'].mean(), df_block['NDRE125'].std()
    df_block['z'] = (df_block['NDRE125'] - mean_v) / std_v if std_v > 0 else 0

    # Build Map (Key: Pokok,Row)
    tree_map = {}
    for _, row in df_block.iterrows():
        x, y = int(row['N_POKOK']), int(row['N_BARIS'])
        tree_map[f"{x},{y}"] = {'x': x, 'y': y, 'z': row['z'], 'status': 'HIJAU'}

    # V8 Algorithm - RE-CALIBRATED THRESHOLDS
    # Standard: z < -1.2 for suspect, min 3 sick neighbors for core
    z_threshold = -1.2 
    min_neighbors = 3
    
    # Identify MERAH (Cores)
    merah_coords = set()
    for key, tree in tree_map.items():
        if tree['z'] < z_threshold:
            sick_count = 0
            # BUG FIX: Ensure mapping nx -> pokok, ny -> baris
            for ny_neigh, nx_neigh in get_hex_neighbors(tree['y'], tree['x']):
                nk = f"{nx_neigh},{ny_neigh}"
                if nk in tree_map and tree_map[nk]['z'] < z_threshold:
                    sick_count += 1
            
            if sick_count >= min_neighbors:
                tree['status'] = 'MERAH'
                merah_coords.add((tree['y'], tree['x']))

    # Step 2: Identify ORANYE (Cincin Api)
    for ry, rx in merah_coords:
        for ny, nx in get_hex_neighbors(ry, rx):
            nk = f"{nx},{ny}"
            if nk in tree_map and tree_map[nk]['status'] == 'HIJAU':
                tree_map[nk]['status'] = 'ORANYE'

    # Step 3: Identify KUNING (Isolated)
    for key, tree in tree_map.items():
        if tree['status'] == 'HIJAU' and tree['z'] < z_threshold:
            tree['status'] = 'KUNING'

    # Visualization
    baris_range = df_block['N_BARIS'].max() - df_block['N_BARIS'].min() + 1
    pokok_range = df_block['N_POKOK'].max() - df_block['N_POKOK'].min() + 1
    fig_width = max(24, pokok_range * 0.28)
    fig_height = max(14, baris_range * 0.14)
    
    fig, ax = plt.subplots(figsize=(fig_width, fig_height), facecolor='white')
    status_order = ['HIJAU', 'KUNING', 'ORANYE', 'MERAH']
    sizes = {'HIJAU': 60, 'KUNING': 150, 'ORANYE': 200, 'MERAH': 240}
    
    counts = {s: 0 for s in status_order}
    for status in status_order:
        plot_x, plot_y, s_list, ec_list, ew_list = [], [], [], [], []
        for key, tree in tree_map.items():
            if tree['status'] == status:
                counts[status] += 1
                offset = 0.5 if tree['y'] % 2 == 0 else 0
                plot_x.append(tree['x'] + offset)
                plot_y.append(tree['y'])
                s_list.append(sizes[status])
                ec_list.append('black' if status != 'HIJAU' else 'darkgreen')
                ew_list.append(1.5 if status != 'HIJAU' else 0.3)
        
        if plot_x:
            ax.scatter(plot_x, plot_y, c=STATUS_COLORS[status], s=s_list, 
                      edgecolors=ec_list, linewidths=ew_list, zorder=status_order.index(status)+1, alpha=0.9)

    ax.invert_yaxis()
    ax.set_aspect('equal')
    ax.set_title(f'PETA KLUSTER CINCIN API - BLOK {block_name}\nMERAH: {counts["MERAH"]} | ORANYE: {counts["ORANYE"]} | KUNING: {counts["KUNING"]}', 
                 fontsize=22, fontweight='bold', pad=25)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=110)
    plt.close()
    return counts

# MAIN RUN
ame2_blocks = df[df['DIVISI'] == 'AME II']['BLOK_B'].unique()
for block in sorted(ame2_blocks):
    print(f"Fixing {block}...", end=' ', flush=True)
    counts = generate_sop_style_map_fixed(df, block, output_dir / f"cincin_api_map_{block}.png")
    if counts: print(f"✅ (Merah: {counts['MERAH']})")

print("\n🚀 ALL MAPS RE-FIXED!")
