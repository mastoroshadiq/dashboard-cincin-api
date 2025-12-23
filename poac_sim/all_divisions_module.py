"""
Add "All Divisions" overview tab to dashboard_v7_fixed.py
This provides production analysis for divisions without tree-level NDVI data
"""

import pandas as pd
import numpy as np
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
import base64

def generate_all_divisions_tab(prod_df, output_dir):
    """
    Generate overview tab for all divisions with production analysis
    
    Args:
        prod_df: DataFrame with all productivity data
        output_dir: Path to output directory
        
    Returns:
        dict with HTML content and charts
    """
    
    # Group by division
    div_summary = prod_df.groupby('Divisi_Prod').agg({
        'Blok_Prod': 'count',
        'Luas_Ha': 'sum',
        'Produksi_Ton': 'sum',
        'Potensi_Prod_Ton': 'sum',
        'Yield_TonHa': 'mean',
        'Potensi_Yield': 'mean',
        'Umur_Tahun': 'mean'
    }).round(2)
    
    div_summary.columns = ['Jumlah_Blok', 'Total_Luas', 'Total_Produksi', 
                           'Total_Potensi', 'Avg_Yield', 'Avg_Potensi_Yield', 'Avg_Umur']
    
    div_summary['Gap_Produksi'] = div_summary['Total_Potensi'] - div_summary['Total_Produksi']
    div_summary['Gap_Yield'] = div_summary['Avg_Potensi_Yield'] - div_summary['Avg_Yield']
    div_summary['Efficiency_%'] = (div_summary['Total_Produksi'] / div_summary['Total_Potensi'] * 100).round(1)
    
    # Sort by total production
    div_summary = div_summary.sort_values('Total_Produksi', ascending=False)
    
    # Create visualizations
    charts = {}
    
    # 1. Bar Chart - Yield Comparison per Division
    fig, ax = plt.subplots(figsize=(12, 6))
    divisions = div_summary.index[:10]  # Top 10
    x = np.arange(len(divisions))
    width = 0.35
    
    bars1 = ax.bar(x - width/2, div_summary.loc[divisions, 'Avg_Yield'], 
                   width, label='Realisasi', color='#3498db', alpha=0.8)
    bars2 = ax.bar(x + width/2, div_summary.loc[divisions, 'Avg_Potensi_Yield'], 
                   width, label='Potensi', color='#2ecc71', alpha=0.8)
    
    ax.set_xlabel('Divisi', fontsize=12, weight='bold')
    ax.set_ylabel('Yield (Ton/Ha)', fontsize=12, weight='bold')
    ax.set_title('Perbandingan Yield Realisasi vs Potensi (Top 10 Divisi)', 
                 fontsize=14, weight='bold', pad=20)
    ax.set_xticks(x)
    ax.set_xticklabels(divisions, rotation=45, ha='right')
    ax.legend()
    ax.grid(axis='y', alpha=0.3)
    
    # Add value labels
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height:.1f}', ha='center', va='bottom', fontsize=9)
    
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    buf.seek(0)
    charts['yield_comparison'] = base64.b64encode(buf.read()).decode()
    plt.close()
    
    # 2. Scatter Plot - Production vs Potential
    fig, ax = plt.subplots(figsize=(10, 8))
    
    scatter = ax.scatter(div_summary['Total_Produksi'], 
                        div_summary['Total_Potensi'],
                        s=div_summary['Jumlah_Blok']*10,  # Size by block count
                        c=div_summary['Efficiency_%'], 
                        cmap='RdYlGn', 
                        alpha=0.6,
                        edgecolors='black',
                        linewidth=1)
    
    # Add diagonal line (perfect efficiency)
    max_val = max(div_summary['Total_Potensi'].max(), div_summary['Total_Produksi'].max())
    ax.plot([0, max_val], [0, max_val], 'k--', alpha=0.3, label='100% Efficiency')
    
    # Label points
    for idx, row in div_summary.iterrows():
        if row['Jumlah_Blok'] > 10:  # Only label major divisions
            ax.annotate(idx, 
                       (row['Total_Produksi'], row['Total_Potensi']),
                       fontsize=8, alpha=0.7)
    
    ax.set_xlabel('Produksi Realisasi (Ton)', fontsize=12, weight='bold')
    ax.set_ylabel('Produksi Potensi (Ton)', fontsize=12, weight='bold')
    ax.set_title('Analisis Gap Produksi per Divisi\\n(Ukuran lingkaran = Jumlah blok)', 
                 fontsize=14, weight='bold', pad=20)
    
    cbar = plt.colorbar(scatter, ax=ax)
    cbar.set_label('Efficiency (%)', rotation=270, labelpad=20)
    ax.legend()
    ax.grid(alpha=0.3)
    
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    buf.seek(0)
    charts['production_scatter'] = base64.b64encode(buf.read()).decode()
    plt.close()
    
    # 3. Generate summary table HTML
    summary_rows = ""
    for i, (div, row) in enumerate(div_summary.iterrows(), 1):
        eff_color = "#27ae60" if row['Efficiency_%'] >= 90 else "#f39c12" if row['Efficiency_%'] >= 80 else "#e74c3c"
        summary_rows += f'''
        <tr>
            <td>{i}</td>
            <td><b>{div}</b></td>
            <td>{row['Jumlah_Blok']}</td>
            <td>{row['Total_Luas']:.1f}</td>
            <td>{row['Total_Produksi']:.2f}</td>
            <td>{row['Total_Potensi']:.2f}</td>
            <td style="color:#e74c3c"><b>{row['Gap_Produksi']:.2f}</b></td>
            <td>{row['Avg_Yield']:.2f}</td>
            <td>{row['Avg_Potensi_Yield']:.2f}</td>
            <td>{row['Gap_Yield']:.2f}</td>
            <td style="color:{eff_color}"><b>{row['Efficiency_%']:.1f}%</b></td>
            <td>{row['Avg_Umur']:.0f} th</td>
        </tr>
        '''
    
    # 4. Top/Bottom performers
    top_5 = prod_df.nlargest(10, 'Yield_TonHa')[['Blok_Prod', 'Divisi_Prod', 'Yield_TonHa', 'Potensi_Yield', 'Gap_Yield', 'Umur_Tahun']]
    bottom_5 = prod_df.nsmallest(10, 'Yield_TonHa')[['Blok_Prod', 'Divisi_Prod', 'Yield_TonHa', 'Potensi_Yield', 'Gap_Yield', 'Umur_Tahun']]
    
    top_rows = ""
    for i, (_, row) in enumerate(top_5.iterrows(), 1):
        top_rows += f'''
        <tr>
            <td>{i}</td>
            <td><b>{row['Blok_Prod']}</b></td>
            <td>{row['Divisi_Prod']}</td>
            <td style="color:#27ae60"><b>{row['Yield_TonHa']:.2f}</b></td>
            <td>{row['Potensi_Yield']:.2f}</td>
            <td>{row['Gap_Yield']:.2f}</td>
            <td>{row['Umur_Tahun']:.0f} th</td>
        </tr>
        '''
    
    bottom_rows = ""
    for i, (_, row) in enumerate(bottom_5.iterrows(), 1):
        bottom_rows += f'''
        <tr>
            <td>{i}</td>
            <td><b>{row['Blok_Prod']}</b></td>
            <td>{row['Divisi_Prod']}</td>
            <td style="color:#e74c3c"><b>{row['Yield_TonHa']:.2f}</b></td>
            <td>{row['Potensi_Yield']:.2f}</td>
            <td>{row['Gap_Yield']:.2f}</td>
            <td>{row['Umur_Tahun']:.0f} th</td>
        </tr>
        '''
    
    html_content = f'''
    <section>
        <h3>📊 Overview Semua Divisi</h3>
        <p>Analisis produktivitas seluruh divisi tanpa data detil Ganoderma</p>
        
        <table>
            <thead>
                <tr>
                    <th>#</th><th>Divisi</th><th>Blok</th><th>Luas (Ha)</th>
                    <th>Produksi Real (Ton)</th><th>Produksi Pot (Ton)</th><th>Gap Prod</th>
                    <th>Yield Real</th><th>Yield Pot</th><th>Gap Yield</th>
                    <th>Efficiency</th><th>Avg Umur</th>
                </tr>
            </thead>
            <tbody>{summary_rows}</tbody>
        </table>
    </section>
    
    <section>
        <h3>📈 Visualisasi Perbandingan Divisi</h3>
        <div style="margin: 20px 0;">
            <img src="data:image/png;base64,{charts['yield_comparison']}" style="max-width:100%; height:auto;">
        </div>
        
        <div style="margin: 20px 0;">
            <img src="data:image/png;base64,{charts['production_scatter']}" style="max-width:100%; height:auto;">
        </div>
    </section>
    
    <section>
        <h3>🏆 Top 10 Best Performers</h3>
        <table>
            <thead>
                <tr><th>#</th><th>Blok</th><th>Divisi</th><th>Yield Real</th><th>Yield Pot</th><th>Gap</th><th>Umur</th></tr>
            </thead>
            <tbody>{top_rows}</tbody>
        </table>
    </section>
    
    <section>
        <h3>⚠️ Top 10 Lowest Performers</h3>
        <table>
            <thead>
                <tr><th>#</th><th>Blok</th><th>Divisi</th><th>Yield Real</th><th>Yield Pot</th><th>Gap</th><th>Umur</th></tr>
            </thead>
            <tbody>{bottom_rows}</tbody>
        </table>
    </section>
    '''
    
    return {
        'html': html_content,
        'charts': charts
    }

# Test
if __name__ == '__main__':
    import sys
    sys.path.insert(0, '.')
    from dashboard_v7_fixed import load_productivity_data
    
    prod_df = load_productivity_data()
    result = generate_all_divisions_tab(prod_df, Path('data/output/test'))
    print('✅ All Divisions tab generated successfully')
    print(f'Charts created: {list(result["charts"].keys())}')
