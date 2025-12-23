"""
Add "All Divisions" overview tab - UPDATED without charts
Focuses on tables with Ganoderma attack % if available
"""

import pandas as pd
import numpy as np
from pathlib import Path

def load_ganoderma_block_stats():
    """Load Ganoderma attack % from data_gabungan.xlsx - available for ALL divisions."""
    try:
        # Load data_gabungan.xlsx
        file_path = Path('data/input/data_gabungan.xlsx')
        df_raw = pd.read_excel(file_path, header=None)
        df = df_raw.iloc[8:].copy().reset_index(drop=True)
        df.columns = [f'col_{i}' for i in range(df.shape[1])]
        
        # col_55: STADIUM 1&2
        # col_56: STADIUM 3&4  
        # col_58: %SERANGAN (in decimal format 0-1, need to convert to 0-100)
        block_stats = df[['col_0', 'col_55', 'col_56', 'col_58']].copy()
        block_stats.columns = ['Blok', 'Stadium_12', 'Stadium_34', 'Attack_Pct']
        
        # Convert to numeric
        block_stats['Stadium_12'] = pd.to_numeric(block_stats['Stadium_12'], errors='coerce').fillna(0)
        block_stats['Stadium_34'] = pd.to_numeric(block_stats['Stadium_34'], errors='coerce').fillna(0)
        block_stats['Attack_Pct'] = pd.to_numeric(block_stats['Attack_Pct'], errors='coerce').fillna(0)
        
        # Convert from decimal (0-1) to percentage (0-100)
        block_stats['Attack_Pct'] = block_stats['Attack_Pct'] * 100
        
        # Set block as index
        block_stats = block_stats.set_index('Blok')
        
        # Keep ALL blocks (including 0% attack) for complete coverage
        # block_stats = block_stats[block_stats['Attack_Pct'] > 0]  # REMOVED
        
        return block_stats
        
    except Exception as e:
        print(f"  ⚠️ Could not load Ganoderma data: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()


def generate_all_divisions_tab(prod_df, output_dir):
    """
    Generate overview tab for all divisions with production analysis
    
    Args:
        prod_df: DataFrame with all productivity data
        output_dir: Path to output directory
        
    Returns:
        dict with HTML content
    """
    
    # Try to load Ganoderma data
    print('  📊 Loading Ganoderma data (if available)...')
    gano_stats = load_ganoderma_block_stats()
    has_gano = not gano_stats.empty
    print(f'  {"✅" if has_gano else "❌"} Ganoderma data: {len(gano_stats)} blocks')
    
    # Helper function to get attack % for a block
    def get_attack_pct(blok):
        if not has_gano:
            return None
        # Direct match (data_gabungan uses same block names)
        if blok in gano_stats.index:
            return gano_stats.loc[blok, 'Attack_Pct']
        return None
    
    def get_relevance(attack_pct):
        """Get relevance indicator based on attack %"""
        if attack_pct is None or pd.isna(attack_pct):
            return "❓ N/A", "#999"
        if attack_pct >= 40:
            return "🔴 KUAT", "#e74c3c"
        elif attack_pct >= 20:
            return "🟠 SEDANG", "#e67e22"
        elif attack_pct >= 2:
            return "🟡 LEMAH", "#f1c40f"
        else:
            return "⚪ MINIMAL", "#bdc3c7"
    
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
    
    # Generate summary table HTML
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
    
    # Top/Bottom performers WITH Ganoderma data
    top_10 = prod_df.nlargest(10, 'Yield_TonHa')
    bottom_10 = prod_df.nsmallest(10, 'Yield_TonHa')
    
    top_rows = ""
    for i, (_, row) in enumerate(top_10.iterrows(), 1):
        attack = get_attack_pct(row['Blok_Prod'])
        relevance, rel_color = get_relevance(attack)
        attack_str = f"{attack:.1f}%" if attack is not None else "N/A"
        
        top_rows += f'''
        <tr>
            <td>{i}</td>
            <td><b>{row['Blok_Prod']}</b></td>
            <td>{row['Divisi_Prod']}</td>
            <td style="color:#27ae60"><b>{row['Yield_TonHa']:.2f}</b></td>
            <td>{row['Potensi_Yield']:.2f}</td>
            <td>{row['Gap_Yield']:.2f}</td>
            <td>{row['Umur_Tahun']:.0f} th</td>
            <td>{attack_str}</td>
            <td style="color:{rel_color}"><b>{relevance}</b></td>
        </tr>
        '''
    
    bottom_rows = ""
    for i, (_, row) in enumerate(bottom_10.iterrows(), 1):
        attack = get_attack_pct(row['Blok_Prod'])
        relevance, rel_color = get_relevance(attack)
        attack_str = f"{attack:.1f}%" if attack is not None else "N/A"
        
        bottom_rows += f'''
        <tr>
            <td>{i}</td>
            <td><b>{row['Blok_Prod']}</b></td>
            <td>{row['Divisi_Prod']}</td>
            <td style="color:#e74c3c"><b>{row['Yield_TonHa']:.2f}</b></td>
            <td>{row['Potensi_Yield']:.2f}</td>
            <td>{row['Gap_Yield']:.2f}</td>
            <td>{row['Umur_Tahun']:.0f} th</td>
            <td><b>{attack_str}</b></td>
            <td style="color:{rel_color}"><b>{relevance}</b></td>
        </tr>
        '''
    
    html_content = f'''
    <section>
        <h3>📊 Overview Semua Divisi</h3>
        <p>Analisis produktivitas seluruh divisi {f"dengan data Ganoderma untuk AME II/IV" if has_gano else "tanpa data Ganoderma"}</p>
        
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
        <h3>🏆 Top 10 Best Performers</h3>
        <table>
            <thead>
                <tr><th>#</th><th>Blok</th><th>Divisi</th><th>Yield Real</th><th>Yield Pot</th><th>Gap</th><th>Umur</th><th>% Attack</th><th>Relevansi</th></tr>
            </thead>
            <tbody>{top_rows}</tbody>
        </table>
    </section>
    
    <section>
        <h3>⚠️ Top 10 Lowest Performers</h3>
        <table>
            <thead>
                <tr><th>#</th><th>Blok</th><th>Divisi</th><th>Yield Real</th><th>Yield Pot</th><th>Gap</th><th>Umur</th><th>% Attack</th><th>Relevansi</th></tr>
            </thead>
            <tbody>{bottom_rows}</tbody>
        </table>
    </section>
    '''
    
    return {
        'html': html_content,
        'charts': {}  # No charts
    }

# Test
if __name__ == '__main__':
    import sys
    sys.path.insert(0, '.')
    from dashboard_v7_fixed import load_productivity_data
    
    prod_df = load_productivity_data()
    result = generate_all_divisions_tab(prod_df, Path('data/output/test'))
    print('✅ All Divisions tab generated successfully')
    print(f'Has Ganoderma data: {len(result.get("charts", {})) == 0}')
