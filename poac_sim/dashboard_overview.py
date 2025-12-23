"""
Dashboard Overview - All Divisions Production Analysis
Standalone dashboard for divisions without tree-level NDVI data
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import logging

# Import custom modules
from all_divisions_module import generate_all_divisions_tab

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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
        'col_173': 'Potensi_Prod_Ton'
    })
    
    df['Luas_Ha'] = pd.to_numeric(df['Luas_Ha'], errors='coerce')
    df['Tahun_Tanam'] = pd.to_numeric(df['Tahun_Tanam'], errors='coerce')
    df['Produksi_Ton'] = pd.to_numeric(df['Produksi_Ton'], errors='coerce')
    df['Potensi_Prod_Ton'] = pd.to_numeric(df['Potensi_Prod_Ton'], errors='coerce')
    
    # Recalculate yields
    df['Yield_Realisasi'] = df['Produksi_Ton'] / df['Luas_Ha']
    df['Yield_Realisasi'] = df['Yield_Realisasi'].replace([np.inf, -np.inf], np.nan)
    
    df['Potensi_Yield'] = df['Potensi_Prod_Ton'] / df['Luas_Ha']
    df['Potensi_Yield'] = df['Potensi_Yield'].replace([np.inf, -np.inf], np.nan)
    
    df['Gap_Yield'] = df['Potensi_Yield'] - df['Yield_Realisasi']
    df['Yield_TonHa'] = df['Yield_Realisasi']
    
    # Calculate plant age
    current_year = datetime.now().year
    df['Umur_Tahun'] = current_year - df['Tahun_Tanam']
    
    # Filter only productive blocks
    df_clean = df[['Blok_Prod', 'Divisi_Prod', 'Tahun_Tanam', 'Umur_Tahun', 'Luas_Ha',
                   'Produksi_Ton', 'Potensi_Prod_Ton', 'Yield_TonHa', 'Yield_Realisasi', 'Potensi_Yield', 'Gap_Yield']].dropna()
    df_clean = df_clean[(df_clean['Produksi_Ton'] > 0) & (df_clean['Yield_TonHa'] > 0)]
    
    return df_clean

def main():
    """Generate overview dashboard for all divisions."""
    print('='*70)
    print('🌴 DASHBOARD OVERVIEW - ALL DIVISIONS v1.0')
    print('   Production Analysis for All Estates')
    print('='*70)
    
    base_dir = Path(__file__).parent
    timestamp = datetime.now().strftime('%Y%m%d_%H%M')
    output_dir = base_dir / f'data/output/dashboard_overview_{timestamp}'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print('\n[1/3] Loading productivity data...')
    prod_df = load_productivity_data()
    print(f'  ✅ {len(prod_df)} blocks loaded from {prod_df["Divisi_Prod"].nunique()} divisions')
    
    print('\n[2/3] Generating overview analysis...')
    overview_data = generate_all_divisions_tab(prod_df, output_dir)
    print('  ✅ Overview content generated')
    print(f'  ✅ Visualizations: {list(overview_data["charts"].keys())}')
    
    print('\n[3/3] Building HTML dashboard...')
    
    html = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard Overview - All Divisions</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            color: #333;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }}
        
        header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}
        
        header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        }}
        
        header p {{
            font-size: 1.1em;
            opacity: 0.9;
        }}
        
        .content {{
            padding: 40px;
        }}
        
        section {{
            margin-bottom: 40px;
            background: #f8f9fa;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        
        h3 {{
            color: #667eea;
            margin-bottom: 20px;
            font-size: 1.8em;
            border-bottom: 3px solid #667eea;
            padding-bottom: 10px;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            background: white;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        
        thead {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }}
        
        th, td {{
            padding: 15px;
            text-align: left;
            border-bottom: 1px solid #e0e0e0;
        }}
        
        th {{
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.9em;
            letter-spacing: 0.5px;
        }}
        
        tbody tr:hover {{
            background: #f5f5f5;
            transition: background 0.3s ease;
        }}
        
        tbody tr:last-child td {{
            border-bottom: none;
        }}
        
        .pov-section {{
            background: linear-gradient(to right, #ffecd2 0%, #fcb69f 100%);
        }}
        
        footer {{
            background: #333;
            color: white;
            text-align: center;
            padding: 20px;
            font-size: 0.9em;
        }}
        
        .stats-badge {{
            display: inline-block;
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: bold;
            margin: 5px;
        }}
        
        .badge-success {{ background: #27ae60; color: white; }}
        .badge-warning {{ background: #f39c12; color: white; }}
        .badge-danger {{ background: #e74c3c; color: white; }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🌴 DASHBOARD OVERVIEW</h1>
            <p>Analisis Produktivitas Seluruh Divisi PT Sawit Riau</p>
            <p style="font-size: 0.9em; margin-top: 10px;">
                <span class="stats-badge badge-success">{len(prod_df)} Blok</span>
                <span class="stats-badge badge-warning">{prod_df["Divisi_Prod"].nunique()} Divisi</span>
                <span class="stats-badge badge-danger">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</span>
            </p>
        </header>
        
        <div class="content">
            {overview_data['html']}
        </div>
        
        <footer>
            <p>🌴 Dashboard Overview v1.0 | PT Sawit Riau | {datetime.now().year}</p>
            <p style="margin-top: 5px; font-size: 0.85em; opacity: 0.7;">
                Production Analysis Dashboard (without tree-level Ganoderma data)
            </p>
        </footer>
    </div>
</body>
</html>'''
    
    html_path = output_dir / 'dashboard_overview.html'
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f'\n{"="*70}')
    print('✅ DASHBOARD OVERVIEW COMPLETE!')
    print(f'📁 Output: {output_dir}')
    print(f'🌐 Dashboard: file:///{html_path.absolute()}')
    print('='*70)
    
    return html_path

if __name__ == '__main__':
    main()
