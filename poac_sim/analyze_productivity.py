"""
Analisis Produktivitas Blok - HTML Dashboard
=============================================
Top 10 blok produktif dan tidak produktif dengan visualisasi interaktif
"""
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

# Output
timestamp = datetime.now().strftime("%Y%m%d_%H%M")
output_dir = Path(f'data/output/productivity_dashboard_{timestamp}')
output_dir.mkdir(parents=True, exist_ok=True)

def load_production_data():
    """Load and parse data_gabungan.xlsx"""
    file_path = Path(r'd:\PythonProjects\simulasi_poac\poac_sim\data\input\data_gabungan.xlsx')
    df_raw = pd.read_excel(file_path, header=None)
    
    df = df_raw.iloc[8:].copy().reset_index(drop=True)
    df.columns = [f'col_{i}' for i in range(df.shape[1])]
    
    df = df.rename(columns={
        'col_0': 'Blok',
        'col_1': 'Tahun_Tanam',
        'col_3': 'Divisi',
        'col_5': 'Afdeling',
        'col_6': 'Estate',
        'col_10': 'Varietas',
        'col_11': 'Luas_Ha'
    })
    
    df['Tahun_Tanam'] = pd.to_numeric(df['Tahun_Tanam'], errors='coerce')
    df['Luas_Ha'] = pd.to_numeric(df['Luas_Ha'], errors='coerce')
    
    # Use col_170 as production in TON (verified with E026B = 6.48 Ton)
    df['Produksi_Ton'] = pd.to_numeric(df['col_170'], errors='coerce')
    
    # Calculate Yield (Ton/Ha)
    df['Yield_TonHa'] = df['Produksi_Ton'] / df['Luas_Ha']
    df['Yield_TonHa'] = df['Yield_TonHa'].replace([np.inf, -np.inf], np.nan)
    
    return df

def generate_html_dashboard(df, output_dir):
    """Generate interactive HTML dashboard."""
    
    # Filter valid data
    df_valid = df[df['Yield_TonHa'].notna() & (df['Yield_TonHa'] > 0)].copy()
    
    # Top/Bottom 10
    top_10 = df_valid.nlargest(10, 'Yield_TonHa')
    bottom_10 = df_valid.nsmallest(10, 'Yield_TonHa')
    
    # Stats
    total_blok = len(df_valid)
    total_luas = df_valid['Luas_Ha'].sum()
    total_produksi = df_valid['Produksi_Ton'].sum()
    avg_yield = df_valid['Yield_TonHa'].mean()
    max_yield = df_valid['Yield_TonHa'].max()
    min_yield = df_valid['Yield_TonHa'].min()
    
    # Generate table rows
    def make_table_rows(data, color_class):
        rows = ""
        for i, (_, row) in enumerate(data.iterrows()):
            rows += f"""
            <tr class="{color_class}">
                <td>{i+1}</td>
                <td><strong>{row['Blok']}</strong></td>
                <td>{row['Estate']}</td>
                <td>{row['Varietas'] if pd.notna(row['Varietas']) else '-'}</td>
                <td>{row['Luas_Ha']:.1f}</td>
                <td>{row['Produksi_Ton']:.2f}</td>
                <td><strong>{row['Yield_TonHa']:.3f}</strong></td>
            </tr>
            """
        return rows
    
    top_rows = make_table_rows(top_10, "top-row")
    bottom_rows = make_table_rows(bottom_10, "bottom-row")
    
    # JSON data for charts
    yield_data = df_valid['Yield_TonHa'].dropna()
    hist_data = np.histogram(yield_data[yield_data < yield_data.quantile(0.95)], bins=20)
    
    html = f"""
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard Produktivitas Blok</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', Tahoma, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            color: #fff;
            padding: 20px;
        }}
        .header {{
            text-align: center;
            padding: 30px;
            background: rgba(255,255,255,0.05);
            border-radius: 15px;
            margin-bottom: 30px;
            backdrop-filter: blur(10px);
        }}
        .header h1 {{
            font-size: 2.5rem;
            margin-bottom: 10px;
            background: linear-gradient(45deg, #00d9ff, #00ff88);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .header p {{ color: #aaa; font-size: 1.1rem; }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .stat-card {{
            background: rgba(255,255,255,0.08);
            padding: 25px;
            border-radius: 15px;
            text-align: center;
            transition: transform 0.3s;
        }}
        .stat-card:hover {{ transform: translateY(-5px); }}
        .stat-card .value {{
            font-size: 2rem;
            font-weight: bold;
            color: #00d9ff;
        }}
        .stat-card .label {{ color: #aaa; margin-top: 5px; }}
        .section {{
            background: rgba(255,255,255,0.05);
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 30px;
        }}
        .section h2 {{
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .top-section h2 {{ color: #00ff88; }}
        .bottom-section h2 {{ color: #ff6b6b; }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }}
        th, td {{
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }}
        th {{ background: rgba(0,0,0,0.3); color: #00d9ff; }}
        .top-row:hover {{ background: rgba(0,255,136,0.1); }}
        .bottom-row:hover {{ background: rgba(255,107,107,0.1); }}
        .chart-container {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
            margin-bottom: 30px;
        }}
        .chart-box {{
            background: rgba(255,255,255,0.05);
            border-radius: 15px;
            padding: 25px;
        }}
        .chart-box h3 {{ margin-bottom: 20px; color: #00d9ff; }}
        @media (max-width: 768px) {{
            .chart-container {{ grid-template-columns: 1fr; }}
        }}
        .timestamp {{ text-align: center; color: #666; margin-top: 30px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🌴 DASHBOARD PRODUKTIVITAS BLOK</h1>
        <p>Analisis Top 10 Blok Paling Produktif & Tidak Produktif (Yield = Ton/Ha)</p>
    </div>
    
    <div class="stats-grid">
        <div class="stat-card">
            <div class="value">{total_blok:,}</div>
            <div class="label">Total Blok</div>
        </div>
        <div class="stat-card">
            <div class="value">{total_luas:,.0f}</div>
            <div class="label">Total Luas (Ha)</div>
        </div>
        <div class="stat-card">
            <div class="value">{total_produksi:,.0f}</div>
            <div class="label">Total Produksi (Ton)</div>
        </div>
        <div class="stat-card">
            <div class="value">{avg_yield:.3f}</div>
            <div class="label">Rata-rata Yield (T/Ha)</div>
        </div>
        <div class="stat-card">
            <div class="value" style="color: #00ff88;">{max_yield:.3f}</div>
            <div class="label">🏆 Yield Tertinggi</div>
        </div>
        <div class="stat-card">
            <div class="value" style="color: #ff6b6b;">{min_yield:.3f}</div>
            <div class="label">⚠️ Yield Terendah</div>
        </div>
    </div>
    
    <div class="chart-container">
        <div class="chart-box">
            <h3>📊 Top 10 Most Productive</h3>
            <canvas id="topChart"></canvas>
        </div>
        <div class="chart-box">
            <h3>📉 Top 10 Least Productive</h3>
            <canvas id="bottomChart"></canvas>
        </div>
    </div>
    
    <div class="section top-section">
        <h2>🏆 TOP 10 BLOK PALING PRODUKTIF</h2>
        <table>
            <thead>
                <tr>
                    <th>#</th>
                    <th>Blok</th>
                    <th>Estate</th>
                    <th>Varietas</th>
                    <th>Luas (Ha)</th>
                    <th>Produksi (Ton)</th>
                    <th>Yield (T/Ha)</th>
                </tr>
            </thead>
            <tbody>
                {top_rows}
            </tbody>
        </table>
    </div>
    
    <div class="section bottom-section">
        <h2>⚠️ TOP 10 BLOK PALING TIDAK PRODUKTIF</h2>
        <table>
            <thead>
                <tr>
                    <th>#</th>
                    <th>Blok</th>
                    <th>Estate</th>
                    <th>Varietas</th>
                    <th>Luas (Ha)</th>
                    <th>Produksi (Ton)</th>
                    <th>Yield (T/Ha)</th>
                </tr>
            </thead>
            <tbody>
                {bottom_rows}
            </tbody>
        </table>
    </div>
    
    <div class="timestamp">
        Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    </div>
    
    <script>
        // Top 10 Chart
        new Chart(document.getElementById('topChart'), {{
            type: 'bar',
            data: {{
                labels: {top_10['Blok'].tolist()},
                datasets: [{{
                    label: 'Yield (Ton/Ha)',
                    data: {[round(x, 3) for x in top_10['Yield_TonHa'].tolist()]},
                    backgroundColor: 'rgba(0, 255, 136, 0.7)',
                    borderColor: 'rgba(0, 255, 136, 1)',
                    borderWidth: 1
                }}]
            }},
            options: {{
                indexAxis: 'y',
                responsive: true,
                plugins: {{ legend: {{ display: false }} }},
                scales: {{
                    x: {{ grid: {{ color: 'rgba(255,255,255,0.1)' }} }},
                    y: {{ grid: {{ display: false }} }}
                }}
            }}
        }});
        
        // Bottom 10 Chart
        new Chart(document.getElementById('bottomChart'), {{
            type: 'bar',
            data: {{
                labels: {bottom_10['Blok'].tolist()},
                datasets: [{{
                    label: 'Yield (Ton/Ha)',
                    data: {[round(x, 3) for x in bottom_10['Yield_TonHa'].tolist()]},
                    backgroundColor: 'rgba(255, 107, 107, 0.7)',
                    borderColor: 'rgba(255, 107, 107, 1)',
                    borderWidth: 1
                }}]
            }},
            options: {{
                indexAxis: 'y',
                responsive: true,
                plugins: {{ legend: {{ display: false }} }},
                scales: {{
                    x: {{ grid: {{ color: 'rgba(255,255,255,0.1)' }} }},
                    y: {{ grid: {{ display: false }} }}
                }}
            }}
        }});
    </script>
</body>
</html>
    """
    
    html_path = output_dir / 'productivity_dashboard.html'
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f'Dashboard HTML saved: {html_path}')
    return html_path

def main():
    print('=' * 70)
    print('ANALISIS PRODUKTIVITAS BLOK - HTML DASHBOARD')
    print('=' * 70)
    
    print('\n[1/2] Loading data...')
    df = load_production_data()
    print(f'  Total blok: {len(df)}')
    
    print('\n[2/2] Generating HTML dashboard...')
    html_path = generate_html_dashboard(df, output_dir)
    
    print(f'\n✅ Dashboard ready: {html_path}')
    return html_path

if __name__ == '__main__':
    html_path = main()
