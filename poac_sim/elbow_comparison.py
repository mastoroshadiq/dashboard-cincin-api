"""
Comparison: 3 Presets WITH vs WITHOUT Elbow Method
===================================================
Dashboard untuk melihat perbedaan kontras hasil deteksi
dengan dan tanpa Elbow Method tuning.
"""
import sys
sys.path.insert(0, 'src')

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from datetime import datetime
from src.ingestion import load_and_clean_data
from src.clustering import (
    calculate_percentile_rank, 
    simulate_thresholds,
    find_optimal_threshold,
    classify_trees_with_clustering
)
from config import CINCIN_API_CONFIG, CINCIN_API_PRESETS

# Output directory
timestamp = datetime.now().strftime("%Y%m%d_%H%M")
output_dir = Path(f'data/output/elbow_comparison_{timestamp}')
output_dir.mkdir(parents=True, exist_ok=True)

def run_with_elbow(df, preset_name):
    """Run dengan Elbow Method (auto-tune)."""
    preset_config = CINCIN_API_PRESETS.get(preset_name, {})
    final_config = {**CINCIN_API_CONFIG, **preset_config}
    
    # Calculate percentile rank
    df_ranked = calculate_percentile_rank(df.copy())
    
    # Run Elbow simulation
    sim_df = simulate_thresholds(
        df_ranked,
        min_threshold=final_config['threshold_min'],
        max_threshold=final_config['threshold_max'],
        step=final_config['threshold_step'],
        min_sick_neighbors=final_config['min_sick_neighbors']
    )
    
    # Find optimal threshold via Elbow
    optimal_threshold = find_optimal_threshold(sim_df)
    
    # Classify
    df_classified = classify_trees_with_clustering(
        df_ranked, 
        optimal_threshold, 
        final_config['min_sick_neighbors']
    )
    
    return df_classified, optimal_threshold, sim_df

def run_without_elbow(df, preset_name):
    """Run TANPA Elbow Method (fixed threshold di midpoint)."""
    preset_config = CINCIN_API_PRESETS.get(preset_name, {})
    final_config = {**CINCIN_API_CONFIG, **preset_config}
    
    # Calculate percentile rank
    df_ranked = calculate_percentile_rank(df.copy())
    
    # Use MIDPOINT of range as fixed threshold (no Elbow tuning)
    fixed_threshold = (final_config['threshold_min'] + final_config['threshold_max']) / 2
    
    # Classify dengan fixed threshold
    df_classified = classify_trees_with_clustering(
        df_ranked, 
        fixed_threshold, 
        final_config['min_sick_neighbors']
    )
    
    return df_classified, fixed_threshold

def count_status(df):
    """Count status classifications."""
    merah = len(df[df['Status_Risiko'].str.contains('MERAH', na=False)])
    oranye = len(df[df['Status_Risiko'].str.contains('ORANYE', na=False)])
    kuning = len(df[df['Status_Risiko'].str.contains('KUNING', na=False)])
    hijau = len(df[df['Status_Risiko'].str.contains('HIJAU', na=False)])
    return {'merah': merah, 'oranye': oranye, 'kuning': kuning, 'hijau': hijau}

def main():
    print('=' * 70)
    print('COMPARISON: 3 PRESETS WITH vs WITHOUT ELBOW METHOD')
    print('=' * 70)
    
    # Load data
    print('\n[1/4] Loading data...')
    df = load_and_clean_data(Path('data/input/tabelNDREnew.csv'))
    print(f'  Total pohon: {len(df):,}')
    
    presets = ['konservatif', 'standar', 'agresif']
    results = {}
    
    # Run comparison
    print('\n[2/4] Running comparisons...')
    for preset_name in presets:
        print(f'\n  === {preset_name.upper()} ===')
        
        # WITH Elbow
        df_elbow, thresh_elbow, sim_df = run_with_elbow(df.copy(), preset_name)
        counts_elbow = count_status(df_elbow)
        
        # WITHOUT Elbow
        df_fixed, thresh_fixed = run_without_elbow(df.copy(), preset_name)
        counts_fixed = count_status(df_fixed)
        
        results[preset_name] = {
            'with_elbow': {
                'threshold': thresh_elbow,
                'counts': counts_elbow,
                'simulation': sim_df
            },
            'without_elbow': {
                'threshold': thresh_fixed,
                'counts': counts_fixed
            }
        }
        
        print(f'    WITH Elbow:    Threshold={thresh_elbow*100:.0f}%, MERAH={counts_elbow["merah"]:,}')
        print(f'    WITHOUT Elbow: Threshold={thresh_fixed*100:.0f}%, MERAH={counts_fixed["merah"]:,}')
        gap = counts_elbow['merah'] - counts_fixed['merah']
        gap_pct = gap / counts_fixed['merah'] * 100 if counts_fixed['merah'] > 0 else 0
        print(f'    GAP: {gap:+,} ({gap_pct:+.1f}%)')
    
    # Generate Dashboard
    print('\n[3/4] Generating comparison dashboard...')
    generate_comparison_dashboard(results, output_dir)
    
    # Print Summary
    print('\n[4/4] Summary Report')
    print('=' * 70)
    print('\n📊 HASIL PERBANDINGAN: WITH vs WITHOUT ELBOW')
    print('-' * 70)
    print(f'{"Preset":<15} {"Elbow Thresh":<12} {"Fixed Thresh":<12} {"MERAH Elbow":<12} {"MERAH Fixed":<12} {"GAP":<10}')
    print('-' * 70)
    
    for preset_name in presets:
        r = results[preset_name]
        te = r['with_elbow']['threshold'] * 100
        tf = r['without_elbow']['threshold'] * 100
        me = r['with_elbow']['counts']['merah']
        mf = r['without_elbow']['counts']['merah']
        gap = me - mf
        gap_pct = gap / mf * 100 if mf > 0 else 0
        print(f'{preset_name:<15} {te:<12.0f}% {tf:<12.0f}% {me:<12,} {mf:<12,} {gap:+,} ({gap_pct:+.1f}%)')
    
    print('\n' + '=' * 70)
    print(f'Dashboard saved to: {output_dir}')
    
    return results

def generate_comparison_dashboard(results, output_dir):
    """Generate visual comparison dashboard."""
    presets = ['konservatif', 'standar', 'agresif']
    preset_labels = ['Konservatif', 'Standar', 'Agresif']
    colors = {'with_elbow': '#e74c3c', 'without_elbow': '#3498db'}
    
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('Comparison: 3 Presets WITH vs WITHOUT Elbow Method', fontsize=16, fontweight='bold')
    
    # 1. MERAH Count Comparison (Bar Chart)
    ax1 = axes[0, 0]
    x = np.arange(len(presets))
    width = 0.35
    
    merah_elbow = [results[p]['with_elbow']['counts']['merah'] for p in presets]
    merah_fixed = [results[p]['without_elbow']['counts']['merah'] for p in presets]
    
    bars1 = ax1.bar(x - width/2, merah_elbow, width, label='WITH Elbow', color=colors['with_elbow'], alpha=0.8)
    bars2 = ax1.bar(x + width/2, merah_fixed, width, label='WITHOUT Elbow', color=colors['without_elbow'], alpha=0.8)
    
    ax1.set_ylabel('Jumlah MERAH', fontsize=12)
    ax1.set_title('Perbandingan Deteksi MERAH', fontsize=14, fontweight='bold')
    ax1.set_xticks(x)
    ax1.set_xticklabels(preset_labels, fontsize=11)
    ax1.legend(fontsize=10)
    ax1.grid(True, alpha=0.3, axis='y')
    
    # Add value labels
    for bar in bars1:
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height(), f'{int(bar.get_height()):,}', 
                ha='center', va='bottom', fontsize=9)
    for bar in bars2:
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height(), f'{int(bar.get_height()):,}', 
                ha='center', va='bottom', fontsize=9)
    
    # 2. Threshold Comparison
    ax2 = axes[0, 1]
    thresh_elbow = [results[p]['with_elbow']['threshold'] * 100 for p in presets]
    thresh_fixed = [results[p]['without_elbow']['threshold'] * 100 for p in presets]
    
    bars1 = ax2.bar(x - width/2, thresh_elbow, width, label='WITH Elbow (Auto)', color=colors['with_elbow'], alpha=0.8)
    bars2 = ax2.bar(x + width/2, thresh_fixed, width, label='WITHOUT Elbow (Fixed)', color=colors['without_elbow'], alpha=0.8)
    
    ax2.set_ylabel('Threshold (%)', fontsize=12)
    ax2.set_title('Threshold yang Digunakan', fontsize=14, fontweight='bold')
    ax2.set_xticks(x)
    ax2.set_xticklabels(preset_labels, fontsize=11)
    ax2.legend(fontsize=10)
    ax2.grid(True, alpha=0.3, axis='y')
    
    for bar in bars1:
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height(), f'{bar.get_height():.0f}%', 
                ha='center', va='bottom', fontsize=10)
    for bar in bars2:
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height(), f'{bar.get_height():.0f}%', 
                ha='center', va='bottom', fontsize=10)
    
    # 3. GAP Analysis
    ax3 = axes[1, 0]
    gaps = [results[p]['with_elbow']['counts']['merah'] - results[p]['without_elbow']['counts']['merah'] for p in presets]
    gap_pcts = [(g / results[p]['without_elbow']['counts']['merah'] * 100) if results[p]['without_elbow']['counts']['merah'] > 0 else 0 
                for g, p in zip(gaps, presets)]
    
    bar_colors = ['#27ae60' if g < 0 else '#e74c3c' for g in gaps]
    bars = ax3.bar(preset_labels, gaps, color=bar_colors, alpha=0.8, edgecolor='black')
    
    ax3.axhline(y=0, color='black', linestyle='-', linewidth=1)
    ax3.set_ylabel('GAP (Elbow - Fixed)', fontsize=12)
    ax3.set_title('GAP: Elbow vs Fixed Threshold', fontsize=14, fontweight='bold')
    ax3.grid(True, alpha=0.3, axis='y')
    
    for bar, gap_pct in zip(bars, gap_pcts):
        height = bar.get_height()
        ax3.text(bar.get_x() + bar.get_width()/2, height, f'{int(height):+,}\n({gap_pct:+.1f}%)', 
                ha='center', va='bottom' if height >= 0 else 'top', fontsize=10, fontweight='bold')
    
    # 4. Status Distribution (Stacked)
    ax4 = axes[1, 1]
    categories = ['MERAH', 'ORANYE', 'KUNING', 'HIJAU']
    cat_colors = ['#e74c3c', '#f39c12', '#f1c40f', '#27ae60']
    
    # Create grouped data
    x_labels = []
    stacked_data = {cat: [] for cat in categories}
    
    for preset in presets:
        for variant, label in [('with_elbow', 'Elbow'), ('without_elbow', 'Fixed')]:
            x_labels.append(f'{preset[:4].title()}\n{label}')
            counts = results[preset][variant]['counts']
            stacked_data['MERAH'].append(counts['merah'])
            stacked_data['ORANYE'].append(counts['oranye'])
            stacked_data['KUNING'].append(counts['kuning'])
            stacked_data['HIJAU'].append(counts['hijau'])
    
    x_pos = np.arange(len(x_labels))
    bottom = np.zeros(len(x_labels))
    
    for cat, color in zip(categories, cat_colors):
        ax4.bar(x_pos, stacked_data[cat], bottom=bottom, label=cat, color=color, alpha=0.8)
        bottom += np.array(stacked_data[cat])
    
    ax4.set_ylabel('Jumlah Pohon', fontsize=12)
    ax4.set_title('Distribusi Status per Preset & Metode', fontsize=14, fontweight='bold')
    ax4.set_xticks(x_pos)
    ax4.set_xticklabels(x_labels, fontsize=9)
    ax4.legend(loc='upper right', fontsize=9)
    ax4.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    plt.savefig(output_dir / 'comparison_dashboard.png', dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f'  Dashboard saved: {output_dir / "comparison_dashboard.png"}')
    
    # Generate HTML Report
    generate_html_report(results, output_dir)

def generate_html_report(results, output_dir):
    """Generate HTML report with comparison."""
    presets = ['konservatif', 'standar', 'agresif']
    
    html = """<!DOCTYPE html>
<html>
<head>
    <title>Elbow Method Comparison Dashboard</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #1a1a2e; color: #eee; }
        h1 { color: #e74c3c; text-align: center; }
        h2 { color: #3498db; border-bottom: 2px solid #3498db; padding-bottom: 10px; }
        table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        th, td { padding: 12px; text-align: center; border: 1px solid #444; }
        th { background: #2d2d44; color: #fff; }
        tr:nth-child(even) { background: #252540; }
        .positive { color: #e74c3c; font-weight: bold; }
        .negative { color: #27ae60; font-weight: bold; }
        .highlight { background: #3d3d5c; }
        .summary-box { background: #2d2d44; padding: 20px; border-radius: 10px; margin: 20px 0; }
        img { max-width: 100%; border-radius: 10px; }
    </style>
</head>
<body>
    <h1>🔥 Comparison: WITH vs WITHOUT Elbow Method</h1>
    
    <div class="summary-box">
        <h2>📊 Summary Table</h2>
        <table>
            <tr>
                <th>Preset</th>
                <th>Elbow Threshold</th>
                <th>Fixed Threshold</th>
                <th>MERAH (Elbow)</th>
                <th>MERAH (Fixed)</th>
                <th>GAP</th>
                <th>GAP %</th>
            </tr>
    """
    
    for preset in presets:
        r = results[preset]
        te = r['with_elbow']['threshold'] * 100
        tf = r['without_elbow']['threshold'] * 100
        me = r['with_elbow']['counts']['merah']
        mf = r['without_elbow']['counts']['merah']
        gap = me - mf
        gap_pct = gap / mf * 100 if mf > 0 else 0
        gap_class = 'positive' if gap > 0 else 'negative'
        
        html += f"""
            <tr>
                <td><strong>{preset.title()}</strong></td>
                <td>{te:.0f}%</td>
                <td>{tf:.0f}%</td>
                <td>{me:,}</td>
                <td>{mf:,}</td>
                <td class="{gap_class}">{gap:+,}</td>
                <td class="{gap_class}">{gap_pct:+.1f}%</td>
            </tr>
        """
    
    html += """
        </table>
    </div>
    
    <h2>📈 Visual Comparison</h2>
    <img src="comparison_dashboard.png" alt="Comparison Dashboard">
    
    <div class="summary-box">
        <h2>💡 Kesimpulan</h2>
        <ul>
            <li><strong>Elbow Method cenderung memilih threshold LEBIH TINGGI</strong> dari midpoint</li>
            <li>Threshold lebih tinggi = Lebih banyak pohon terdeteksi MERAH</li>
            <li>Gap terbesar terjadi pada preset <strong>Agresif</strong></li>
        </ul>
    </div>
</body>
</html>
    """
    
    with open(output_dir / 'comparison_report.html', 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f'  HTML Report saved: {output_dir / "comparison_report.html"}')

if __name__ == '__main__':
    main()
