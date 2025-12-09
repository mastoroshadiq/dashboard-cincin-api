"""
POAC v3.3 - Interactive Dashboard
Dashboard interaktif untuk visualisasi hasil Algoritma Cincin Api

Fitur:
1. Peta Panas (Heatmap) per Blok
2. Elbow Chart (Auto-Tuning Visualization)
3. Peta Grid Hexagonal dengan status warna
4. Daftar Target Prioritas untuk Mandor
5. Statistik ringkasan
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec
from matplotlib.colors import LinearSegmentedColormap
from pathlib import Path
import logging
import sys

# Setup logging
logger = logging.getLogger(__name__)

# Add parent to path
_parent_dir = Path(__file__).parent.parent
if str(_parent_dir) not in sys.path:
    sys.path.insert(0, str(_parent_dir))

from config import CINCIN_API_CONFIG

# Status colors
STATUS_COLORS = {
    "MERAH (KLUSTER AKTIF)": "#e74c3c",
    "KUNING (RISIKO TINGGI)": "#f1c40f", 
    "ORANYE (NOISE/KENTOSAN)": "#e67e22",
    "HIJAU (SEHAT)": "#27ae60"
}

STATUS_SHORT = {
    "MERAH (KLUSTER AKTIF)": "MERAH",
    "KUNING (RISIKO TINGGI)": "KUNING",
    "ORANYE (NOISE/KENTOSAN)": "ORANYE",
    "HIJAU (SEHAT)": "HIJAU"
}


def create_dashboard(
    df_classified: pd.DataFrame, 
    metadata: dict,
    output_dir: str = None,
    show_plots: bool = True
):
    """
    Membuat dashboard lengkap untuk hasil Algoritma Cincin Api.
    
    Args:
        df_classified: DataFrame hasil klasifikasi dari run_cincin_api_algorithm
        metadata: Metadata dari algoritma (threshold, counts, dll)
        output_dir: Direktori untuk menyimpan output
        show_plots: Apakah menampilkan plot
    """
    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
    
    print("\n" + "=" * 70)
    print("📊 DASHBOARD ALGORITMA CINCIN API")
    print("=" * 70)
    
    # 1. Summary Statistics
    _print_summary(df_classified, metadata)
    
    # 2. Create main dashboard figure
    fig = _create_main_dashboard(df_classified, metadata)
    if output_dir:
        fig.savefig(output_dir / "dashboard_main.png", dpi=150, bbox_inches='tight')
        logger.info(f"Dashboard saved to: {output_dir / 'dashboard_main.png'}")
    if show_plots:
        plt.show()
    plt.close(fig)
    
    # 3. Block Heatmap
    fig2 = _create_block_heatmap(df_classified)
    if output_dir:
        fig2.savefig(output_dir / "dashboard_block_heatmap.png", dpi=150, bbox_inches='tight')
    if show_plots:
        plt.show()
    plt.close(fig2)
    
    # 4. Elbow Chart (if available)
    if metadata.get('simulation_data') is not None:
        fig3 = _create_elbow_chart(metadata['simulation_data'], metadata['optimal_threshold'])
        if output_dir:
            fig3.savefig(output_dir / "dashboard_elbow.png", dpi=150, bbox_inches='tight')
        if show_plots:
            plt.show()
        plt.close(fig3)
    
    # 5. Top 10 affected blocks detail
    print("\n[Generating Top 10 Block Details...]")
    _create_top10_block_details(df_classified, output_dir, show_plots)
    
    # 6. Export priority list
    if output_dir:
        from src.clustering import get_priority_targets
        priority_df = get_priority_targets(df_classified, top_n=500)
        priority_path = output_dir / "target_prioritas_mandor.csv"
        priority_df.to_csv(priority_path, index=False)
        logger.info(f"Priority targets exported to: {priority_path}")
    
    print("\n" + "=" * 70)
    print("✅ DASHBOARD COMPLETE!")
    if output_dir:
        print(f"📁 Files saved to: {output_dir}")
    print("=" * 70)


def _print_summary(df: pd.DataFrame, metadata: dict):
    """Print summary statistics."""
    print(f"""
┌─────────────────────────────────────────────────────────────────────┐
│                    RINGKASAN ALGORITMA CINCIN API                    │
├─────────────────────────────────────────────────────────────────────┤
│  Threshold Optimal (Auto-Tuning): {metadata['optimal_threshold_pct']:>10}                        │
│  Total Pohon Dianalisis:          {metadata['total_trees']:>10,}                        │
├─────────────────────────────────────────────────────────────────────┤
│  🔴 MERAH (Kluster Aktif):        {metadata['merah_count']:>10,}  → TARGET SANITASI     │
│  🟡 KUNING (Risiko Tinggi):       {metadata['kuning_count']:>10,}  → MONITORING KETAT   │
│  🟠 ORANYE (Noise/Kentosan):      {metadata['oranye_count']:>10,}  → INVESTIGASI        │
│  🟢 HIJAU (Sehat):                {metadata['hijau_count']:>10,}  → NORMAL             │
├─────────────────────────────────────────────────────────────────────┤
│  Total Target Intervensi (MERAH+KUNING): {metadata['merah_count'] + metadata['kuning_count']:>10,}                   │
└─────────────────────────────────────────────────────────────────────┘
""")


def _create_main_dashboard(df: pd.DataFrame, metadata: dict):
    """Create main dashboard with 4 panels."""
    fig = plt.figure(figsize=(16, 12))
    gs = GridSpec(2, 2, figure=fig, hspace=0.3, wspace=0.25)
    
    fig.suptitle('POAC v3.3 - Dashboard Algoritma Cincin Api\nDeteksi Kluster Ganoderma', 
                 fontsize=16, fontweight='bold', y=0.98)
    
    # Panel 1: Status Distribution Pie Chart
    ax1 = fig.add_subplot(gs[0, 0])
    status_counts = df['Status_Risiko'].value_counts()
    colors = [STATUS_COLORS.get(s, '#cccccc') for s in status_counts.index]
    labels = [STATUS_SHORT.get(s, s) for s in status_counts.index]
    
    wedges, texts, autotexts = ax1.pie(
        status_counts.values, 
        labels=labels,
        colors=colors,
        autopct=lambda pct: f'{pct:.1f}%\n({int(pct/100*sum(status_counts.values)):,})',
        startangle=90,
        explode=[0.05 if 'MERAH' in s else 0 for s in status_counts.index]
    )
    ax1.set_title(f'Distribusi Status Risiko\n(Threshold: {metadata["optimal_threshold_pct"]})', 
                  fontweight='bold', fontsize=12)
    
    # Panel 2: Top 15 Blocks with Most MERAH
    ax2 = fig.add_subplot(gs[0, 1])
    block_merah = df[df['Status_Risiko'] == 'MERAH (KLUSTER AKTIF)'].groupby('Blok').size()
    block_merah = block_merah.sort_values(ascending=True).tail(15)
    
    bars = ax2.barh(range(len(block_merah)), block_merah.values, color='#e74c3c')
    ax2.set_yticks(range(len(block_merah)))
    ax2.set_yticklabels(block_merah.index)
    ax2.set_xlabel('Jumlah Pohon MERAH (Kluster Aktif)')
    ax2.set_title('Top 15 Blok dengan Kluster Terbanyak', fontweight='bold', fontsize=12)
    
    for i, (bar, val) in enumerate(zip(bars, block_merah.values)):
        ax2.text(val + 1, i, str(val), va='center', fontweight='bold')
    
    # Panel 3: Density Score Distribution
    ax3 = fig.add_subplot(gs[1, 0])
    suspect_df = df[df['Status_Risiko'] != 'HIJAU (SEHAT)']
    if not suspect_df.empty:
        density_counts = suspect_df['Skor_Kepadatan_Kluster'].value_counts().sort_index()
        colors_density = ['#e67e22' if d == 0 else '#f1c40f' if d < 3 else '#e74c3c' 
                         for d in density_counts.index]
        ax3.bar(density_counts.index, density_counts.values, color=colors_density, edgecolor='black')
        ax3.set_xlabel('Jumlah Tetangga Sakit')
        ax3.set_ylabel('Jumlah Pohon')
        ax3.set_title('Distribusi Skor Kepadatan Kluster\n(Suspect Trees Only)', 
                      fontweight='bold', fontsize=12)
        ax3.set_xticks(range(0, 7))
        
        # Add threshold line
        ax3.axvline(x=2.5, color='red', linestyle='--', linewidth=2, 
                   label=f'Threshold Kluster (≥3)')
        ax3.legend()
    
    # Panel 4: Statistics Table
    ax4 = fig.add_subplot(gs[1, 1])
    ax4.axis('off')
    
    # Calculate additional stats
    total_intervensi = metadata['merah_count'] + metadata['kuning_count']
    pct_merah = (metadata['merah_count'] / metadata['total_trees']) * 100
    pct_intervensi = (total_intervensi / metadata['total_trees']) * 100
    
    table_data = [
        ['Metrik', 'Nilai'],
        ['Total Pohon', f"{metadata['total_trees']:,}"],
        ['Threshold Optimal', metadata['optimal_threshold_pct']],
        ['', ''],
        ['MERAH (Kluster)', f"{metadata['merah_count']:,} ({pct_merah:.2f}%)"],
        ['KUNING (Risiko)', f"{metadata['kuning_count']:,}"],
        ['ORANYE (Noise)', f"{metadata['oranye_count']:,}"],
        ['HIJAU (Sehat)', f"{metadata['hijau_count']:,}"],
        ['', ''],
        ['Total Intervensi', f"{total_intervensi:,} ({pct_intervensi:.2f}%)"],
        ['Blok Terparah', df[df['Status_Risiko']=='MERAH (KLUSTER AKTIF)'].groupby('Blok').size().idxmax() if metadata['merah_count'] > 0 else '-'],
    ]
    
    table = ax4.table(
        cellText=table_data,
        cellLoc='left',
        loc='center',
        colWidths=[0.5, 0.5]
    )
    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1.2, 1.8)
    
    # Style header
    table[(0, 0)].set_facecolor('#3498db')
    table[(0, 1)].set_facecolor('#3498db')
    table[(0, 0)].set_text_props(color='white', fontweight='bold')
    table[(0, 1)].set_text_props(color='white', fontweight='bold')
    
    ax4.set_title('Statistik Ringkasan', fontweight='bold', fontsize=12, pad=20)
    
    # Add legend footer
    _add_legend_footer(fig, metadata)
    
    return fig


def _add_legend_footer(fig, metadata: dict):
    """Add informative legend footer to figure."""
    legend_text = (
        "PANDUAN: 🔴 MERAH = Kluster Aktif (→ Sanitasi) │ "
        "🟡 KUNING = Risiko Tinggi (→ Monitoring) │ "
        "🟠 ORANYE = Noise (→ Investigasi) │ "
        "🟢 HIJAU = Sehat"
    )
    
    stats_text = (
        f"Threshold: {metadata.get('optimal_threshold_pct', 'N/A')} │ "
        f"Total: {metadata.get('total_trees', 0):,} pohon │ "
        f"Target Intervensi: {metadata.get('merah_count', 0) + metadata.get('kuning_count', 0):,} pohon"
    )
    
    fig.text(0.5, 0.02, legend_text, ha='center', va='bottom', 
            fontsize=9, fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='#ecf0f1', edgecolor='#bdc3c7', alpha=0.9))
    
    fig.text(0.5, -0.01, stats_text, ha='center', va='bottom', 
            fontsize=8, style='italic', color='#7f8c8d')
    
    # Adjust layout to make room for footer
    fig.subplots_adjust(bottom=0.08)


def _create_block_heatmap(df: pd.DataFrame):
    """Create heatmap of MERAH counts per block."""
    fig, ax = plt.subplots(figsize=(14, 8))
    
    # Aggregate by block
    block_stats = df.groupby('Blok').agg({
        'Status_Risiko': [
            lambda x: (x == 'MERAH (KLUSTER AKTIF)').sum(),
            lambda x: (x == 'KUNING (RISIKO TINGGI)').sum(),
            lambda x: (x == 'ORANYE (NOISE/KENTOSAN)').sum(),
            'count'
        ]
    }).reset_index()
    block_stats.columns = ['Blok', 'MERAH', 'KUNING', 'ORANYE', 'TOTAL']
    block_stats = block_stats.sort_values('MERAH', ascending=False)
    
    x = np.arange(len(block_stats))
    width = 0.25
    
    bars1 = ax.bar(x - width, block_stats['MERAH'], width, label='MERAH (Kluster)', color='#e74c3c')
    bars2 = ax.bar(x, block_stats['KUNING'], width, label='KUNING (Risiko)', color='#f1c40f')
    bars3 = ax.bar(x + width, block_stats['ORANYE'], width, label='ORANYE (Noise)', color='#e67e22')
    
    ax.set_xlabel('Blok', fontsize=12)
    ax.set_ylabel('Jumlah Pohon', fontsize=12)
    ax.set_title('Distribusi Status Risiko per Blok', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(block_stats['Blok'], rotation=45, ha='right')
    ax.legend()
    ax.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    return fig


def _create_elbow_chart(simulation_df: pd.DataFrame, optimal_threshold: float):
    """Create Elbow Method visualization."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    
    fig.suptitle('Elbow Method - Auto-Tuning Threshold', fontsize=14, fontweight='bold')
    
    # Chart 1: Clusters and Suspects vs Threshold
    ax1.plot(simulation_df['Batas_Ambang'] * 100, simulation_df['Total_Suspect'], 
             'b-o', label='Total Suspect', linewidth=2)
    ax1.plot(simulation_df['Batas_Ambang'] * 100, simulation_df['Kluster_Valid'], 
             'r-s', label='Kluster Valid (≥3 tetangga)', linewidth=2)
    ax1.axvline(x=optimal_threshold * 100, color='green', linestyle='--', 
                linewidth=2, label=f'Threshold Optimal ({optimal_threshold*100:.0f}%)')
    ax1.set_xlabel('Threshold (%)', fontsize=11)
    ax1.set_ylabel('Jumlah Pohon', fontsize=11)
    ax1.set_title('Jumlah Suspect vs Kluster Valid', fontweight='bold')
    ax1.legend()
    ax1.grid(alpha=0.3)
    
    # Chart 2: Efficiency Ratio
    ax2.plot(simulation_df['Batas_Ambang'] * 100, simulation_df['Rasio_Efisiensi'], 
             'g-^', linewidth=2, markersize=8)
    ax2.axvline(x=optimal_threshold * 100, color='red', linestyle='--', 
                linewidth=2, label=f'Threshold Optimal ({optimal_threshold*100:.0f}%)')
    
    # Mark optimal point
    optimal_row = simulation_df[simulation_df['Batas_Ambang'] == optimal_threshold]
    if not optimal_row.empty:
        ax2.scatter([optimal_threshold * 100], [optimal_row['Rasio_Efisiensi'].values[0]], 
                   color='red', s=200, zorder=5, marker='*')
    
    ax2.set_xlabel('Threshold (%)', fontsize=11)
    ax2.set_ylabel('Rasio Efisiensi (%)', fontsize=11)
    ax2.set_title('Rasio Efisiensi Kluster (Elbow Point)', fontweight='bold')
    ax2.legend()
    ax2.grid(alpha=0.3)
    
    plt.tight_layout()
    return fig


def _create_block_detail(df: pd.DataFrame):
    """Create detailed hexagonal map for the most affected block."""
    # Find block with most MERAH
    block_merah = df[df['Status_Risiko'] == 'MERAH (KLUSTER AKTIF)'].groupby('Blok').size()
    if block_merah.empty:
        # Fallback to block with most non-green
        block_merah = df[df['Status_Risiko'] != 'HIJAU (SEHAT)'].groupby('Blok').size()
    
    if block_merah.empty:
        logger.warning("No affected blocks found")
        fig, ax = plt.subplots(figsize=(10, 8))
        ax.text(0.5, 0.5, "No affected blocks", ha='center', va='center', fontsize=16)
        return fig
    
    top_block = block_merah.idxmax()
    df_block = df[df['Blok'] == top_block].copy()
    
    # Calculate optimal figure size based on data range
    baris_range = df_block['N_BARIS'].max() - df_block['N_BARIS'].min() + 1
    pokok_range = df_block['N_POKOK'].max() - df_block['N_POKOK'].min() + 1
    
    # Make figure wider and taller for better visibility
    # Minimum 24 inches wide, scale based on data
    fig_width = max(28, pokok_range * 0.3)
    fig_height = max(16, baris_range * 0.15)
    
    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    
    # Get colors and sizes for each tree (bigger for clusters)
    colors = []
    sizes = []
    edge_colors = []
    edge_widths = []
    
    for _, row in df_block.iterrows():
        status = row['Status_Risiko']
        colors.append(STATUS_COLORS.get(status, '#cccccc'))
        
        # Make MERAH (cluster) points larger and with thicker border
        if status == 'MERAH (KLUSTER AKTIF)':
            sizes.append(200)
            edge_colors.append('darkred')
            edge_widths.append(2)
        elif status == 'KUNING (RISIKO TINGGI)':
            sizes.append(150)
            edge_colors.append('darkorange')
            edge_widths.append(1.5)
        elif status == 'ORANYE (NOISE/KENTOSAN)':
            sizes.append(120)
            edge_colors.append('black')
            edge_widths.append(1)
        else:  # HIJAU
            sizes.append(60)
            edge_colors.append('darkgreen')
            edge_widths.append(0.5)
    
    # Apply hexagonal offset
    x_coords = []
    y_coords = []
    for _, row in df_block.iterrows():
        baris = row['N_BARIS']
        pokok = row['N_POKOK']
        x_offset = 0.5 if baris % 2 == 0 else 0
        x_coords.append(pokok + x_offset)
        y_coords.append(baris)
    
    # Plot in layers: HIJAU first, then ORANYE, KUNING, MERAH on top
    status_order = ['HIJAU (SEHAT)', 'ORANYE (NOISE/KENTOSAN)', 'KUNING (RISIKO TINGGI)', 'MERAH (KLUSTER AKTIF)']
    
    for status in status_order:
        mask = df_block['Status_Risiko'] == status
        if mask.any():
            indices = df_block[mask].index
            x_plot = [x_coords[list(df_block.index).index(i)] for i in indices]
            y_plot = [y_coords[list(df_block.index).index(i)] for i in indices]
            s_plot = [sizes[list(df_block.index).index(i)] for i in indices]
            c_plot = [colors[list(df_block.index).index(i)] for i in indices]
            ec_plot = [edge_colors[list(df_block.index).index(i)] for i in indices]
            ew_plot = [edge_widths[list(df_block.index).index(i)] for i in indices]
            
            ax.scatter(x_plot, y_plot, c=c_plot, s=s_plot, alpha=0.85, 
                      edgecolors=ec_plot, linewidths=ew_plot, zorder=status_order.index(status)+1)
    
    # Count statistics
    merah_count = len(df_block[df_block["Status_Risiko"]=="MERAH (KLUSTER AKTIF)"])
    kuning_count = len(df_block[df_block["Status_Risiko"]=="KUNING (RISIKO TINGGI)"])
    oranye_count = len(df_block[df_block["Status_Risiko"]=="ORANYE (NOISE/KENTOSAN)"])
    hijau_count = len(df_block[df_block["Status_Risiko"]=="HIJAU (SEHAT)"])
    
    # Create legend with larger markers
    legend_elements = [
        mpatches.Patch(color='#e74c3c', label=f'MERAH - Kluster Aktif ({merah_count})', linewidth=2, edgecolor='darkred'),
        mpatches.Patch(color='#f1c40f', label=f'KUNING - Risiko Tinggi ({kuning_count})'),
        mpatches.Patch(color='#e67e22', label=f'ORANYE - Noise ({oranye_count})'),
        mpatches.Patch(color='#27ae60', label=f'HIJAU - Sehat ({hijau_count})')
    ]
    ax.legend(handles=legend_elements, loc='upper right', fontsize=12, 
              framealpha=0.9, fancybox=True, shadow=True)
    
    ax.set_xlabel('Nomor Pokok (N_POKOK)', fontsize=14)
    ax.set_ylabel('Nomor Baris (N_BARIS)', fontsize=14)
    ax.set_title(f'Peta Detail Blok {top_block} - KLUSTER GANODERMA\n'
                f'(Total: {len(df_block)} pohon | MERAH: {merah_count} | KUNING: {kuning_count})', 
                fontsize=16, fontweight='bold')
    ax.invert_yaxis()
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.set_aspect('equal')
    
    # Add tick labels for better navigation
    ax.tick_params(axis='both', which='major', labelsize=10)
    
    plt.tight_layout()
    return fig


def _create_top10_block_details(df: pd.DataFrame, output_dir: Path = None, show_plots: bool = True):
    """
    Create detailed hexagonal maps for Top 10 most affected blocks.
    Each block saved as separate file with numbered naming.
    """
    # Get top 10 blocks by MERAH count
    block_merah = df[df['Status_Risiko'] == 'MERAH (KLUSTER AKTIF)'].groupby('Blok').size()
    block_merah = block_merah.sort_values(ascending=False).head(10)
    
    if block_merah.empty:
        logger.warning("No affected blocks found for Top 10 visualization")
        return
    
    print(f"\n📊 Generating Top 10 Block Visualizations:")
    print("-" * 50)
    
    for rank, (block_name, merah_count) in enumerate(block_merah.items(), 1):
        print(f"   [{rank:02d}] Blok {block_name}: {merah_count} kluster MERAH")
        
        fig = _create_single_block_detail(df, block_name, rank, merah_count)
        
        if output_dir:
            filename = f"top10_{rank:02d}_blok_{block_name}.png"
            filepath = output_dir / filename
            fig.savefig(filepath, dpi=150, bbox_inches='tight')
            logger.info(f"Saved: {filepath}")
        
        if show_plots:
            plt.show()
        plt.close(fig)
    
    print("-" * 50)
    print(f"✅ Top 10 block visualizations complete!")


def _create_single_block_detail(df: pd.DataFrame, block_name: str, rank: int, merah_total: int):
    """
    Create detailed hexagonal map for a single block with rank number.
    """
    df_block = df[df['Blok'] == block_name].copy()
    
    if df_block.empty:
        fig, ax = plt.subplots(figsize=(10, 8))
        ax.text(0.5, 0.5, f"No data for block {block_name}", ha='center', va='center', fontsize=16)
        return fig
    
    # Calculate optimal figure size based on data range
    baris_range = df_block['N_BARIS'].max() - df_block['N_BARIS'].min() + 1
    pokok_range = df_block['N_POKOK'].max() - df_block['N_POKOK'].min() + 1
    
    # Make figure wider and taller for better visibility
    fig_width = max(28, pokok_range * 0.3)
    fig_height = max(16, baris_range * 0.15)
    
    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    
    # Get colors and sizes for each tree
    colors = []
    sizes = []
    edge_colors = []
    edge_widths = []
    
    for _, row in df_block.iterrows():
        status = row['Status_Risiko']
        colors.append(STATUS_COLORS.get(status, '#cccccc'))
        
        if status == 'MERAH (KLUSTER AKTIF)':
            sizes.append(200)
            edge_colors.append('darkred')
            edge_widths.append(2)
        elif status == 'KUNING (RISIKO TINGGI)':
            sizes.append(150)
            edge_colors.append('darkorange')
            edge_widths.append(1.5)
        elif status == 'ORANYE (NOISE/KENTOSAN)':
            sizes.append(120)
            edge_colors.append('black')
            edge_widths.append(1)
        else:
            sizes.append(60)
            edge_colors.append('darkgreen')
            edge_widths.append(0.5)
    
    # Apply hexagonal offset
    x_coords = []
    y_coords = []
    for _, row in df_block.iterrows():
        baris = row['N_BARIS']
        pokok = row['N_POKOK']
        x_offset = 0.5 if baris % 2 == 0 else 0
        x_coords.append(pokok + x_offset)
        y_coords.append(baris)
    
    # Plot in layers
    status_order = ['HIJAU (SEHAT)', 'ORANYE (NOISE/KENTOSAN)', 'KUNING (RISIKO TINGGI)', 'MERAH (KLUSTER AKTIF)']
    
    for status in status_order:
        mask = df_block['Status_Risiko'] == status
        if mask.any():
            indices = df_block[mask].index
            x_plot = [x_coords[list(df_block.index).index(i)] for i in indices]
            y_plot = [y_coords[list(df_block.index).index(i)] for i in indices]
            s_plot = [sizes[list(df_block.index).index(i)] for i in indices]
            c_plot = [colors[list(df_block.index).index(i)] for i in indices]
            ec_plot = [edge_colors[list(df_block.index).index(i)] for i in indices]
            ew_plot = [edge_widths[list(df_block.index).index(i)] for i in indices]
            
            ax.scatter(x_plot, y_plot, c=c_plot, s=s_plot, alpha=0.85, 
                      edgecolors=ec_plot, linewidths=ew_plot, zorder=status_order.index(status)+1)
    
    # Count statistics
    merah_count = len(df_block[df_block["Status_Risiko"]=="MERAH (KLUSTER AKTIF)"])
    kuning_count = len(df_block[df_block["Status_Risiko"]=="KUNING (RISIKO TINGGI)"])
    oranye_count = len(df_block[df_block["Status_Risiko"]=="ORANYE (NOISE/KENTOSAN)"])
    hijau_count = len(df_block[df_block["Status_Risiko"]=="HIJAU (SEHAT)"])
    total_count = len(df_block)
    
    # Create legend
    legend_elements = [
        mpatches.Patch(color='#e74c3c', label=f'MERAH - Kluster Aktif ({merah_count})'),
        mpatches.Patch(color='#f1c40f', label=f'KUNING - Risiko Tinggi ({kuning_count})'),
        mpatches.Patch(color='#e67e22', label=f'ORANYE - Noise ({oranye_count})'),
        mpatches.Patch(color='#27ae60', label=f'HIJAU - Sehat ({hijau_count})')
    ]
    ax.legend(handles=legend_elements, loc='upper right', fontsize=12, 
              framealpha=0.9, fancybox=True, shadow=True)
    
    ax.set_xlabel('Nomor Pokok (N_POKOK)', fontsize=14)
    ax.set_ylabel('Nomor Baris (N_BARIS)', fontsize=14)
    
    # Title with rank number
    ax.set_title(f'#{rank:02d} - BLOK {block_name} - PETA KLUSTER GANODERMA\n'
                f'Total Pohon: {total_count} | MERAH: {merah_count} | KUNING: {kuning_count} | ORANYE: {oranye_count}', 
                fontsize=16, fontweight='bold', color='darkred' if rank <= 3 else 'black')
    
    ax.invert_yaxis()
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.set_aspect('equal')
    ax.tick_params(axis='both', which='major', labelsize=10)
    
    # Add rank badge in corner
    ax.text(0.02, 0.98, f'RANK #{rank}', transform=ax.transAxes, fontsize=20, 
            fontweight='bold', color='white', 
            bbox=dict(boxstyle='round,pad=0.3', facecolor='#e74c3c' if rank <= 3 else '#f39c12', 
                     edgecolor='black', linewidth=2),
            verticalalignment='top')
    
    plt.tight_layout()
    return fig


def create_mandor_report(df: pd.DataFrame, metadata: dict, output_path: str = None) -> str:
    """
    Generate laporan untuk Mandor dalam format text.
    """
    from src.clustering import get_priority_targets
    
    priority_df = get_priority_targets(df, top_n=50)
    
    report = f"""
================================================================================
                    LAPORAN TARGET INTERVENSI MANDOR
                    ALGORITMA CINCIN API - POAC v3.3
================================================================================

THRESHOLD DETEKSI: {metadata['optimal_threshold_pct']}
TANGGAL GENERATE: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}

--------------------------------------------------------------------------------
RINGKASAN STATUS:
--------------------------------------------------------------------------------
🔴 MERAH (TARGET UTAMA - SANITASI):     {metadata['merah_count']:>8,} pohon
🟡 KUNING (MONITORING KETAT):           {metadata['kuning_count']:>8,} pohon
🟠 ORANYE (INVESTIGASI):                {metadata['oranye_count']:>8,} pohon
🟢 HIJAU (NORMAL):                      {metadata['hijau_count']:>8,} pohon
                                        ─────────────
   TOTAL:                               {metadata['total_trees']:>8,} pohon

--------------------------------------------------------------------------------
TOP 50 TARGET PRIORITAS (Urutkan berdasarkan Kepadatan Kluster):
--------------------------------------------------------------------------------
"""
    
    if not priority_df.empty:
        for i, (_, row) in enumerate(priority_df.head(50).iterrows(), 1):
            status_icon = "🔴" if "MERAH" in row['Status_Risiko'] else "🟡"
            report += f"{i:3}. {status_icon} Blok {row['Blok']:>5} | Baris {row['N_BARIS']:>3} | Pokok {row['N_POKOK']:>3} | "
            report += f"Tetangga Sakit: {row['Skor_Kepadatan_Kluster']} | NDRE: {row['NDRE125']:.4f}\n"
    
    report += """
--------------------------------------------------------------------------------
INSTRUKSI UNTUK MANDOR:
--------------------------------------------------------------------------------
1. PRIORITAS UTAMA: Fokus pada pohon 🔴 MERAH (Kluster Aktif)
2. Lakukan validasi lapangan untuk konfirmasi serangan Ganoderma
3. Jika terkonfirmasi, lakukan sanitasi sesuai SOP
4. Pohon 🟡 KUNING perlu monitoring berkala
5. Abaikan 🟠 ORANYE kecuali ada indikasi lain di lapangan

================================================================================
"""
    
    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report)
        logger.info(f"Mandor report saved to: {output_path}")
    
    return report
