"""
POAC v3.3 - Visualization Module
Modul untuk visualisasi hasil simulasi Ring of Fire & Adaptive NDRE

Fitur:
1. Heatmap Z-Score per Blok
2. Peta Hexagonal Grid dengan Ring of Fire
3. Perbandingan Skenario (Bar Chart)
4. Distribusi Z-Score (Histogram)
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.colors import LinearSegmentedColormap
from pathlib import Path
import logging
import sys

# Setup logging
logger = logging.getLogger(__name__)

# Add parent to path for config import
_parent_dir = Path(__file__).parent.parent
if str(_parent_dir) not in sys.path:
    sys.path.insert(0, str(_parent_dir))

from config import OUTPUT_COLUMNS, STATUS_G3, STATUS_G2, STATUS_HEALTHY


def plot_scenario_comparison(summary_df: pd.DataFrame, save_path: str = None):
    """
    Plot perbandingan metrik antar skenario menggunakan bar chart.
    
    Args:
        summary_df: DataFrame hasil dari run_multi_scenario
        save_path: Path untuk menyimpan gambar (opsional)
    """
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    fig.suptitle('POAC v3.3 - Perbandingan Skenario Simulasi', fontsize=14, fontweight='bold')
    
    scenarios = summary_df['Skenario'].tolist()
    x = np.arange(len(scenarios))
    width = 0.6
    
    colors = ['#e74c3c', '#f39c12', '#27ae60']  # Red, Orange, Green
    
    # Chart 1: Jumlah G3 (Target Sanitasi)
    ax1 = axes[0]
    bars1 = ax1.bar(x, summary_df['Jumlah_G3'], width, color=colors)
    ax1.set_xlabel('Skenario')
    ax1.set_ylabel('Jumlah Pohon')
    ax1.set_title('🎯 Jumlah G3\n(Target Sanitasi)', fontweight='bold')
    ax1.set_xticks(x)
    ax1.set_xticklabels(['Hemat', 'Seimbang', 'Perang'], rotation=0)
    for bar, val in zip(bars1, summary_df['Jumlah_G3']):
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 50, 
                f'{int(val):,}', ha='center', va='bottom', fontweight='bold')
    
    # Chart 2: Jumlah Cincin Api (Target Proteksi)
    ax2 = axes[1]
    bars2 = ax2.bar(x, summary_df['Cincin_Api'], width, color=colors)
    ax2.set_xlabel('Skenario')
    ax2.set_ylabel('Jumlah Pohon')
    ax2.set_title('🔥 Jumlah Cincin Api\n(Target Proteksi)', fontweight='bold')
    ax2.set_xticks(x)
    ax2.set_xticklabels(['Hemat', 'Seimbang', 'Perang'], rotation=0)
    for bar, val in zip(bars2, summary_df['Cincin_Api']):
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 50, 
                f'{int(val):,}', ha='center', va='bottom', fontweight='bold')
    
    # Chart 3: Total Intervensi (Beban Kerja)
    ax3 = axes[2]
    bars3 = ax3.bar(x, summary_df['Total_Intervensi'], width, color=colors)
    ax3.set_xlabel('Skenario')
    ax3.set_ylabel('Jumlah Pohon')
    ax3.set_title('👷 Total Intervensi\n(Beban Kerja Mandor)', fontweight='bold')
    ax3.set_xticks(x)
    ax3.set_xticklabels(['Hemat', 'Seimbang', 'Perang'], rotation=0)
    for bar, val in zip(bars3, summary_df['Total_Intervensi']):
        ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 50, 
                f'{int(val):,}', ha='center', va='bottom', fontweight='bold')
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        logger.info(f"Chart saved to: {save_path}")
    
    plt.show()
    return fig


def plot_zscore_distribution(df: pd.DataFrame, scenario_name: str = "", save_path: str = None):
    """
    Plot distribusi Z-Score dengan threshold markers.
    
    Args:
        df: DataFrame dengan kolom Z_Score
        scenario_name: Nama skenario untuk judul
        save_path: Path untuk menyimpan gambar (opsional)
    """
    fig, ax = plt.subplots(figsize=(12, 6))
    
    z_col = OUTPUT_COLUMNS['z_score']
    z_scores = df[z_col].dropna()
    
    # Histogram
    n, bins, patches = ax.hist(z_scores, bins=50, edgecolor='black', alpha=0.7, color='steelblue')
    
    # Color bars based on threshold regions
    for i, (patch, left, right) in enumerate(zip(patches, bins[:-1], bins[1:])):
        if right <= -2.0:
            patch.set_facecolor('#e74c3c')  # G3 - Red
        elif right <= -1.0:
            patch.set_facecolor('#f39c12')  # G2 - Orange
        else:
            patch.set_facecolor('#27ae60')  # Healthy - Green
    
    # Add threshold lines
    ax.axvline(x=-2.5, color='darkred', linestyle='--', linewidth=2, label='Threshold G3 (Hemat): -2.5')
    ax.axvline(x=-2.0, color='red', linestyle='--', linewidth=2, label='Threshold G3 (Seimbang): -2.0')
    ax.axvline(x=-1.5, color='orange', linestyle='--', linewidth=2, label='Threshold G3 (Perang): -1.5')
    ax.axvline(x=0, color='gray', linestyle='-', linewidth=1, alpha=0.5)
    
    ax.set_xlabel('Z-Score', fontsize=12)
    ax.set_ylabel('Jumlah Pohon', fontsize=12)
    ax.set_title(f'Distribusi Z-Score NDRE {scenario_name}\n(Merah=G3, Oranye=G2, Hijau=Sehat)', 
                fontsize=14, fontweight='bold')
    ax.legend(loc='upper right')
    ax.grid(axis='y', alpha=0.3)
    
    # Add statistics text
    stats_text = f'Total: {len(z_scores):,}\nMean: {z_scores.mean():.2f}\nStd: {z_scores.std():.2f}'
    ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, fontsize=10,
            verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        logger.info(f"Chart saved to: {save_path}")
    
    plt.show()
    return fig


def plot_block_heatmap(df: pd.DataFrame, block_name: str, scenario_name: str = "", save_path: str = None):
    """
    Plot heatmap untuk satu blok, menampilkan posisi G3 dan Ring of Fire.
    
    Args:
        df: DataFrame dengan koordinat dan status
        block_name: Nama blok untuk divisualisasikan
        scenario_name: Nama skenario
        save_path: Path untuk menyimpan gambar (opsional)
    """
    # Filter data untuk blok tertentu
    df_block = df[df['Blok'] == block_name].copy()
    
    if df_block.empty:
        logger.warning(f"Block '{block_name}' tidak ditemukan dalam data")
        return None
    
    fig, ax = plt.subplots(figsize=(14, 10))
    
    status_col = OUTPUT_COLUMNS['status']
    z_col = OUTPUT_COLUMNS['z_score']
    
    # Define colors based on status
    colors = []
    for _, row in df_block.iterrows():
        if row[status_col] == STATUS_G3:
            colors.append('#e74c3c')  # Red for G3
        elif row.get('Ring_Candidate', False):
            colors.append('#f39c12')  # Orange for Ring
        elif row[status_col] == STATUS_G2:
            colors.append('#f1c40f')  # Yellow for G2
        else:
            colors.append('#27ae60')  # Green for healthy
    
    # Plot scatter with hexagonal offset consideration
    x_coords = []
    y_coords = []
    
    for _, row in df_block.iterrows():
        baris = row['N_BARIS']
        pokok = row['N_POKOK']
        
        # Apply hexagonal offset for even rows
        x_offset = 0.5 if baris % 2 == 0 else 0
        x_coords.append(pokok + x_offset)
        y_coords.append(baris)
    
    scatter = ax.scatter(x_coords, y_coords, c=colors, s=100, alpha=0.8, edgecolors='black', linewidth=0.5)
    
    # Create legend
    legend_elements = [
        mpatches.Patch(color='#e74c3c', label=f'G3 - Target Sanitasi ({len(df_block[df_block[status_col] == STATUS_G3])})'),
        mpatches.Patch(color='#f39c12', label=f'Cincin Api - Target Proteksi ({len(df_block[df_block["Ring_Candidate"] == True]) if "Ring_Candidate" in df_block.columns else 0})'),
        mpatches.Patch(color='#f1c40f', label=f'G2 - Monitoring ({len(df_block[df_block[status_col] == STATUS_G2])})'),
        mpatches.Patch(color='#27ae60', label=f'Sehat ({len(df_block[df_block[status_col] == STATUS_HEALTHY])})')
    ]
    ax.legend(handles=legend_elements, loc='upper right', fontsize=10)
    
    ax.set_xlabel('Nomor Pokok (N_POKOK)', fontsize=12)
    ax.set_ylabel('Nomor Baris (N_BARIS)', fontsize=12)
    ax.set_title(f'Peta Blok {block_name} - {scenario_name}\nPola Hexagonal (Mata Lima)', 
                fontsize=14, fontweight='bold')
    ax.invert_yaxis()  # Baris 1 di atas
    ax.grid(True, alpha=0.3)
    ax.set_aspect('equal')
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        logger.info(f"Chart saved to: {save_path}")
    
    plt.show()
    return fig


def plot_block_summary(df: pd.DataFrame, save_path: str = None):
    """
    Plot ringkasan per blok - jumlah G3 dan Ring per blok.
    
    Args:
        df: DataFrame dengan status dan blok
        save_path: Path untuk menyimpan gambar (opsional)
    """
    status_col = OUTPUT_COLUMNS['status']
    
    # Aggregate per block
    block_summary = df.groupby('Blok').agg({
        status_col: lambda x: (x == STATUS_G3).sum(),
        'Ring_Candidate': 'sum' if 'Ring_Candidate' in df.columns else lambda x: 0
    }).reset_index()
    block_summary.columns = ['Blok', 'G3_Count', 'Ring_Count']
    block_summary = block_summary.sort_values('G3_Count', ascending=False).head(20)
    
    fig, ax = plt.subplots(figsize=(14, 8))
    
    x = np.arange(len(block_summary))
    width = 0.35
    
    bars1 = ax.bar(x - width/2, block_summary['G3_Count'], width, label='G3 (Target Sanitasi)', color='#e74c3c')
    bars2 = ax.bar(x + width/2, block_summary['Ring_Count'], width, label='Cincin Api (Target Proteksi)', color='#f39c12')
    
    ax.set_xlabel('Blok', fontsize=12)
    ax.set_ylabel('Jumlah Pohon', fontsize=12)
    ax.set_title('Top 20 Blok dengan G3 Terbanyak', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(block_summary['Blok'], rotation=45, ha='right')
    ax.legend()
    ax.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        logger.info(f"Chart saved to: {save_path}")
    
    plt.show()
    return fig


def create_full_visualization_report(summary_df: pd.DataFrame, detailed_results: list, output_dir: str = None):
    """
    Generate full visualization report untuk semua skenario.
    
    Args:
        summary_df: DataFrame ringkasan dari run_multi_scenario
        detailed_results: List hasil detail dari setiap skenario
        output_dir: Direktori untuk menyimpan gambar
    """
    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
    
    print("\n" + "=" * 70)
    print("📊 GENERATING VISUALIZATION REPORT")
    print("=" * 70)
    
    # 1. Scenario Comparison
    print("\n[1/4] Generating Scenario Comparison Chart...")
    save_path = str(output_dir / "01_scenario_comparison.png") if output_dir else None
    plot_scenario_comparison(summary_df, save_path)
    
    # 2. Z-Score Distribution (use Skenario Seimbang as reference)
    print("\n[2/4] Generating Z-Score Distribution...")
    if detailed_results:
        seimbang_result = detailed_results[1] if len(detailed_results) > 1 else detailed_results[0]
        save_path = str(output_dir / "02_zscore_distribution.png") if output_dir else None
        plot_zscore_distribution(seimbang_result['dataframe'], seimbang_result['scenario_name'], save_path)
    
    # 3. Block Summary
    print("\n[3/4] Generating Block Summary Chart...")
    if detailed_results:
        save_path = str(output_dir / "03_block_summary.png") if output_dir else None
        plot_block_summary(detailed_results[1]['dataframe'] if len(detailed_results) > 1 else detailed_results[0]['dataframe'], save_path)
    
    # 4. Sample Block Heatmap (blok dengan G3 terbanyak)
    print("\n[4/4] Generating Sample Block Heatmap...")
    if detailed_results:
        df_result = detailed_results[1]['dataframe'] if len(detailed_results) > 1 else detailed_results[0]['dataframe']
        status_col = OUTPUT_COLUMNS['status']
        
        # Find block with most G3
        g3_per_block = df_result[df_result[status_col] == STATUS_G3].groupby('Blok').size()
        if not g3_per_block.empty:
            top_block = g3_per_block.idxmax()
            save_path = str(output_dir / f"04_block_heatmap_{top_block}.png") if output_dir else None
            scenario_name = detailed_results[1]['scenario_name'] if len(detailed_results) > 1 else detailed_results[0]['scenario_name']
            plot_block_heatmap(df_result, top_block, scenario_name, save_path)
    
    print("\n" + "=" * 70)
    print("✅ VISUALIZATION REPORT COMPLETE!")
    if output_dir:
        print(f"📁 Files saved to: {output_dir}")
    print("=" * 70)
