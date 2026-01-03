import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path
import os

print("="*80)
print("🚀 GENERATING ULTRA HIGH-RESOLUTION CINCIN API MAPS (4K+ READY)")
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
    if r % 2 != 0:
        return [(r - 1, p - 1), (r - 1, p), (r, p - 1), (r, p + 1), (r + 1, p - 1), (r + 1, p)]
    else:
        return [(r - 1, p), (r - 1, p + 1), (r, p - 1), (r, p + 1), (r + 1, p), (r + 1, p + 1)]

def generate_high_res_map(df_ndre, block_name, output_path, rank=1):
    if 'BLOK_B' in df_ndre.columns:
        df_ndre['Blok_Filter'] = df_ndre['BLOK_B']
    else:
        df_ndre['Blok_Filter'] = df_ndre['BLOK']
    
    df_block = df_ndre[df_ndre['Blok_Filter'].astype(str).str.strip().str.upper() == block_name].copy()
    if len(df_block) < 10: return None

    df_block['NDRE125'] = pd.to_numeric(df_block['NDRE125'].astype(str).str.replace(',', '.'), errors='coerce')
    df_block = df_block.dropna(subset=['NDRE125'])
    
    mean_v, std_v = df_block['NDRE125'].mean(), df_block['NDRE125'].std()
    df_block['z'] = (df_block['NDRE125'] - mean_v) / std_v if std_v > 0 else 0

    tree_map = {}
    for _, row in df_block.iterrows():
        x, y = int(row['N_POKOK']), int(row['N_BARIS'])
        tree_map[f"{x},{y}"] = {'x': x, 'y': y, 'z': row['z'], 'status': 'HIJAU'}

    z_threshold = -1.2 
    min_neighbors = 3
    
    merah_coords = set()
    for key, tree in tree_map.items():
        if tree['z'] < z_threshold:
            sick_count = 0
            for ny_neigh, nx_neigh in get_hex_neighbors(tree['y'], tree['x']):
                nk = f"{nx_neigh},{ny_neigh}"
                if nk in tree_map and tree_map[nk]['z'] < z_threshold:
                    sick_count += 1
            if sick_count >= min_neighbors:
                tree['status'] = 'MERAH'
                merah_coords.add((tree['y'], tree['x']))

    for ry, rx in merah_coords:
        for ny, nx in get_hex_neighbors(ry, rx):
            nk = f"{nx},{ny}"
            if nk in tree_map and tree_map[nk]['status'] == 'HIJAU':
                tree_map[nk]['status'] = 'ORANYE'

    for key, tree in tree_map.items():
        if tree['status'] == 'HIJAU' and tree['z'] < z_threshold:
            tree['status'] = 'KUNING'

    # ULTRA HIGH RES SETUP
    baris_range = df_block['N_BARIS'].max() - df_block['N_BARIS'].min() + 1
    pokok_range = df_block['N_POKOK'].max() - df_block['N_POKOK'].min() + 1
    
    # Increase base figsize for better proportion
    fig_width = max(30, pokok_range * 0.35)
    fig_height = max(18, baris_range * 0.18)
    
    fig, ax = plt.subplots(figsize=(fig_width, fig_height), facecolor='white')
    status_order = ['HIJAU', 'KUNING', 'ORANYE', 'MERAH']
    # Scale sizes for high res (slightly smaller as per user request)
    sizes = {'HIJAU': 100, 'KUNING': 200, 'ORANYE': 280, 'MERAH': 360}
    
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
                ec_list.append('black' if status != 'HIJAU' else '#15803d')
                ew_list.append(2.0 if status != 'HIJAU' else 0.5)
        
        if plot_x:
            ax.scatter(plot_x, plot_y, c=STATUS_COLORS[status], s=s_list, 
                      edgecolors=ec_list, linewidths=ew_list, zorder=status_order.index(status)+1, alpha=0.9)

    ax.invert_yaxis()
    ax.set_aspect('equal')
    
    # Grid customization for transparency
    ax.grid(True, which='both', linestyle='--', alpha=0.15, color='#94a3b8')
    
    # Larger fonts for labels and title to match high-res
    ax.set_title(f'PETA KLUSTER CINCIN API - BLOK {block_name}\n(HIGH RESOLUTION ANALYTICS)', 
                 fontsize=32, fontweight='bold', pad=40)
    
    # Stats summary in a box
    stats_text = (f"🔴 MERAH (KLUSTER): {counts['MERAH']}\n"
                 f"🟠 ORANYE (RING): {counts['ORANYE']}\n"
                 f"🟡 KUNING (SUSPECT): {counts['KUNING']}")
    
    props = dict(boxstyle='round,pad=1', facecolor='white', alpha=0.9, edgecolor='#cbd5e1')
    ax.text(0.98, 0.02, stats_text, transform=ax.transAxes, fontsize=24,
            verticalalignment='bottom', horizontalalignment='right', bbox=props, fontweight='bold')

    ax.set_xlabel('Nomor Pokok (X)', fontsize=20, fontweight='bold')
    ax.set_ylabel('Nomor Baris (Y)', fontsize=20, fontweight='bold')
    
    # Increase tick label size
    ax.tick_params(axis='both', which='major', labelsize=16)

    plt.tight_layout()
    # SAVE AS HIGH DPI (300 DPI = ~9000-12000 pixels wide)
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    return counts

# RUN ALL
ame2_blocks = df[df['DIVISI'] == 'AME II']['BLOK_B'].unique()
for i, block in enumerate(sorted(ame2_blocks)):
    print(f"[{i+1}/36] Rendering High-Res: {block}...", end=' ', flush=True)
    generate_high_res_map(df, block, output_dir / f"cincin_api_map_{block}.png")
    print("✅")

print("\n🎯 ALL MAPS UPGRADED TO ULTRA HIGH-RESOLUTION (300 DPI)!")
