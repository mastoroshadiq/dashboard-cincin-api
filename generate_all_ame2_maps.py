import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Patch
from pathlib import Path
import os
import json

print("="*70)
print("🔥 GENERATING CINCIN API MAPS FOR ALL AME II BLOCKS")
print("="*70)

# Load NDRE data
input_file = 'data/input/tabelNDREnew.csv'
if not os.path.exists(input_file):
    input_file = 'poac_sim/data/input/tabelNDREnew.csv'

df1 = pd.read_csv(input_file)
df1.columns = [c.upper().strip() for c in df1.columns]

# Output directory
output_dir = Path('data/output')
output_dir.mkdir(parents=True, exist_ok=True)

def generate_tight_square_map(df_ndre, block_name, output_path):
    """Generate TIGHT SQUARE visualization matching D007A style"""
    
    # Filter for target block
    if 'BLOK_B' in df_ndre.columns:
        df_ndre['Blok_Filter'] = df_ndre['BLOK_B']
    elif 'BLOK' in df_ndre.columns:
        df_ndre['Blok_Filter'] = df_ndre['BLOK']
    
    df_ndre['Blok_Filter'] = df_ndre['Blok_Filter'].astype(str).str.strip().str.upper()
    block_data = df_ndre[df_ndre['Blok_Filter'] == block_name].copy()
    
    if len(block_data) == 0:
        return None
    
    # Ensure NDRE125 is numeric
    if 'NDRE125' in block_data.columns:
        block_data['NDRE125'] = pd.to_numeric(
            block_data['NDRE125'].astype(str).str.replace(',', '.'), 
            errors='coerce'
        )
        block_data = block_data.dropna(subset=['NDRE125'])
    else:
        return None
    
    # Ensure coordinates are numeric
    for col in ['N_POKOK', 'N_BARIS']:
        if col in block_data.columns:
            block_data[col] = pd.to_numeric(block_data[col], errors='coerce')
    
    block_data = block_data.dropna(subset=['N_POKOK', 'N_BARIS'])
    
    if len(block_data) < 10: # Skip very small/invalid blocks
        return None
    
    # Calculate z-scores
    mean_v = block_data['NDRE125'].mean()
    std_v = block_data['NDRE125'].std()
    
    if std_v == 0:
        block_data['z'] = 0
    else:
        block_data['z'] = (block_data['NDRE125'] - mean_v) / std_v
    
    # Build tree map
    tree_map = {}
    for _, row in block_data.iterrows():
        x = int(row['N_POKOK'])
        y = int(row['N_BARIS'])
        key = f"{x},{y}"
        tree_map[key] = {
            'x': x,
            'y': y,
            'z': row['z'],
            'status': 'HIJAU'
        }
    
    # V8 Cincin Api Algorithm
    z_core = -1.5
    z_neigh = -1.0
    min_n = 3
    offsets = [[0,1], [0,-1], [1,0], [-1,0], [1,1], [1,-1], [-1,1], [-1,-1]]
    keys = list(tree_map.keys())
    
    # Step 1: Identify Cores (MERAH/RED)
    cores = set()
    for k in keys:
        if tree_map[k]['z'] < z_core:
            x, y = tree_map[k]['x'], tree_map[k]['y']
            count = 0
            for o in offsets:
                nk = f"{x+o[0]},{y+o[1]}"
                if nk in tree_map and tree_map[nk]['z'] < z_neigh:
                    count += 1
            if count >= min_n:
                tree_map[k]['status'] = 'MERAH'
                cores.add(k)
    
    # Step 2: Identify Ring of Fire (ORANYE) - BFS from cores
    queue = list(cores)
    visited = set(cores)
    
    while queue:
        k = queue.pop(0)
        x, y = tree_map[k]['x'], tree_map[k]['y']
        for o in offsets:
            nk = f"{x+o[0]},{y+o[1]}"
            if nk in tree_map and nk not in visited:
                if tree_map[nk]['z'] < z_neigh:
                    if tree_map[nk]['status'] != 'MERAH':
                        tree_map[nk]['status'] = 'ORANYE'
                    visited.add(nk)
                    queue.append(nk)
    
    # Step 3: Identify Suspects (KUNING/YELLOW)
    for k in keys:
        if tree_map[k]['status'] == 'HIJAU' and tree_map[k]['z'] < z_neigh:
            tree_map[k]['status'] = 'KUNING'
    
    # Count statistics
    counts = {
        'MERAH': sum(1 for k in keys if tree_map[k]['status'] == 'MERAH'),
        'ORANYE': sum(1 for k in keys if tree_map[k]['status'] == 'ORANYE'),
        'KUNING': sum(1 for k in keys if tree_map[k]['status'] == 'KUNING'),
        'HIJAU': sum(1 for k in keys if tree_map[k]['status'] == 'HIJAU')
    }
    
    total = len(keys)
    
    # Create figure
    fig, ax = plt.subplots(figsize=(8, 14), facecolor='white')
    
    color_map = {
        'MERAH': '#8B0000',    # Dark Red
        'ORANYE': '#FF6600',   # Bright Orange
        'KUNING': '#FFD700',   # Gold Yellow
        'HIJAU': '#2ecc71'     # Emerald Green
    }
    
    square_size = 0.9
    
    # Draw squares
    for k in keys:
        tree = tree_map[k]
        x, y, status = tree['x'], tree['y'], tree['status']
        rect = Rectangle(
            (x - 0.5, y - 0.5),
            square_size,
            square_size,
            facecolor=color_map[status],
            edgecolor='none',
            linewidth=0
        )
        ax.add_patch(rect)
    
    x_coords = [tree_map[k]['x'] for k in keys]
    y_coords = [tree_map[k]['y'] for k in keys]
    ax.set_xlim(min(x_coords) - 1, max(x_coords) + 1)
    ax.set_ylim(min(y_coords) - 1, max(y_coords) + 1)
    ax.set_xlabel('Nomor Pokok (N_POKOK)', fontsize=11, fontweight='bold')
    ax.set_ylabel('Nomor Baris (N_BARIS)', fontsize=11, fontweight='bold')
    
    title = f'🔥 BLOK {block_name} - PETA KLUSTER GANODERMA (CINCIN API)\\n'
    title += f'Total: {total} | 🔴 MERAH: {counts["MERAH"]} | 🔥 ORANYE: {counts["ORANYE"]} | 🟡 KUNING: {counts["KUNING"]}'
    ax.set_title(title, fontsize=12, fontweight='bold', pad=12)
    
    legend_elements = [
        Patch(facecolor=color_map['MERAH'], label=f'🔴 MERAH - Kluster Aktif ({counts["MERAH"]})'),
        Patch(facecolor=color_map['ORANYE'], label=f'🔥 ORANYE - CINCIN API ({counts["ORANYE"]})'),
        Patch(facecolor=color_map['KUNING'], label=f'🟡 KUNING - Suspect ({counts["KUNING"]})'),
        Patch(facecolor=color_map['HIJAU'], label=f'🟢 HIJAU - Sehat ({counts["HIJAU"]})')
    ]
    ax.legend(handles=legend_elements, loc='upper left', fontsize=9, framealpha=0.95, edgecolor='black', fancybox=False)
    ax.grid(True, alpha=0.1)
    ax.set_aspect('equal')
    ax.invert_yaxis()
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white') # Low DPI for speed/size
    plt.close()
    
    return counts

# Get all blocks in AME II
ame2_blocks = df1[df1['DIVISI'] == 'AME II']['BLOK_B'].unique()
print(f"📌 Found {len(ame2_blocks)} blocks in AME II.")

all_stats = {}
for i, block in enumerate(ame2_blocks):
    print(f"[{i+1}/{len(ame2_blocks)}] Processing {block}...", end=' ', flush=True)
    out_path = output_dir / f"cincin_api_map_{block}.png"
    stats = generate_tight_square_map(df1, block, out_path)
    if stats:
        all_stats[block] = stats
        print("✅ DONE")
    else:
        print("❌ SKIPPED (No data)")

# UPDATE all_blocks_data.json with NEW counts to ensure consistency
json_path = 'data/output/all_blocks_data.json'
if os.path.exists(json_path):
    with open(json_path, 'r') as f:
        master_data = json.load(f)
    
    updated_count = 0
    for block, stats in all_stats.items():
        if block in master_data:
            master_data[block]['merah'] = stats['MERAH']
            master_data[block]['oranye'] = stats['ORANYE']
            master_data[block]['kuning'] = stats['KUNING']
            master_data[block]['has_map'] = True
            updated_count += 1
    
    with open(json_path, 'w') as f:
        json.dump(master_data, f, indent=2)
    
    print(f"\n✅ UPDATED: {updated_count} blocks in all_blocks_data.json with new scientific counts.")

print("\n" + "="*70)
print("🎯 ALL AME II MAPS COMPLETED!")
print("="*70)
