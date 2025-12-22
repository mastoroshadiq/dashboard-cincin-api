"""
Generate Dashboard Summary CSV/Excel
=====================================
Creates a summary report of all dashboards in the output folder.
"""
import pandas as pd
from pathlib import Path
from datetime import datetime

def create_dashboard_summary():
    """Create comprehensive summary of all dashboards."""
    
    output_dir = Path(r'D:\PythonProjects\simulasi_poac\poac_sim\data\output')
    
    # Define dashboards and their functions
    dashboards = [
        {
            'Dashboard': 'DASHBOARD CINCIN API',
            'Fungsi': [
                '1. Deteksi kluster Ganoderma dengan Hexagonal Neighbor Analysis',
                '2. Klasifikasi pohon: MERAH (kluster aktif), ORANYE (cincin api), KUNING (terisolasi), HIJAU (sehat)',
                '3. Elbow Method untuk auto-tuning threshold optimal',
                '4. 3 Preset: Konservatif, Standar, Agresif',
                '5. Consensus Voting untuk filter multi-preset',
                '6. Visualisasi cluster map per blok',
                '7. Target prioritas untuk mandor (Asap Cair & Trichoderma)'
            ],
            'Output_Folder': 'cincin_api, v35_raised_floor_*',
            'Format_Output': 'HTML Report, PNG Cluster Maps, CSV'
        },
        {
            'Dashboard': 'DASHBOARD GHOST-TREE',
            'Fungsi': [
                '1. Deteksi pohon "hantu" (tercatat tapi tidak ada di lapangan)',
                '2. Analisis discrepancy Drone vs Ground Truth',
                '3. Identifikasi pohon SISIP dan TAMB',
                '4. Audit akurasi data sensus',
                '5. Visualisasi ghost tree distribution',
                '6. Rekomendasi update database'
            ],
            'Output_Folder': 'ghost_tree_audit',
            'Format_Output': 'CSV Audit Report, PNG Maps'
        },
        {
            'Dashboard': 'DASHBOARD SPH ANALYSIS',
            'Fungsi': [
                '1. Perbandingan SPH Drone vs Ground Truth',
                '2. Gap analysis per divisi (AME II, AME IV)',
                '3. Identifikasi root cause perbedaan',
                '4. Visualisasi SPH comparison chart',
                '5. Rekomendasi kalibrasi'
            ],
            'Output_Folder': 'sph_detail, comprehensive_dashboard',
            'Format_Output': 'HTML Dashboard, PNG Charts'
        },
        {
            'Dashboard': 'DASHBOARD COMPREHENSIVE',
            'Fungsi': [
                '1. Executive Summary semua analisis',
                '2. WIWSNS Panel (What, If, Why, So, Next Steps)',
                '3. Multi-divisi comparison',
                '4. Integrated visualization',
                '5. Action recommendations'
            ],
            'Output_Folder': 'comprehensive_dashboard, final_dashboard',
            'Format_Output': 'HTML Interactive Dashboard'
        },
        {
            'Dashboard': 'DASHBOARD EARLY DETECTION',
            'Fungsi': [
                '1. Early warning system Ganoderma',
                '2. Trend analysis per blok',
                '3. Risk scoring dan prioritization',
                '4. Predictive alerting'
            ],
            'Output_Folder': 'early_detection',
            'Format_Output': 'CSV, PNG Reports'
        },
        {
            'Dashboard': 'DASHBOARD ELBOW COMPARISON',
            'Fungsi': [
                '1. Perbandingan metode Efficiency vs Gradient',
                '2. Threshold selection analysis',
                '3. Visualisasi Elbow curve',
                '4. Impact assessment'
            ],
            'Output_Folder': 'elbow_comparison_*',
            'Format_Output': 'HTML Report, PNG Charts'
        },
        {
            'Dashboard': 'DASHBOARD CALIBRATION',
            'Fungsi': [
                '1. Z-Score threshold calibration',
                '2. MAE optimization',
                '3. Ground Truth validation',
                '4. Per-divisi calibration'
            ],
            'Output_Folder': 'calibrated_analysis, z_score_calibration',
            'Format_Output': 'CSV, JSON Metadata'
        }
    ]
    
    # Create flattened data for CSV
    rows = []
    for dash in dashboards:
        for i, func in enumerate(dash['Fungsi']):
            rows.append({
                'Dashboard': dash['Dashboard'] if i == 0 else '',
                'No': i + 1,
                'Fungsi': func.split('. ', 1)[1] if '. ' in func else func,
                'Output_Folder': dash['Output_Folder'] if i == 0 else '',
                'Format_Output': dash['Format_Output'] if i == 0 else ''
            })
        # Add empty row after each dashboard
        rows.append({
            'Dashboard': '',
            'No': '',
            'Fungsi': '',
            'Output_Folder': '',
            'Format_Output': ''
        })
    
    df = pd.DataFrame(rows)
    
    # Save as CSV
    csv_path = output_dir / 'DASHBOARD_SUMMARY.csv'
    df.to_csv(csv_path, index=False, encoding='utf-8-sig')
    print(f'Saved: {csv_path}')
    
    # Save as Excel
    excel_path = output_dir / 'DASHBOARD_SUMMARY.xlsx'
    with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Dashboard Summary', index=False)
    print(f'Saved: {excel_path}')
    
    # Also create a simpler format matching the user's image
    simple_rows = []
    for dash in dashboards:
        simple_rows.append({'Item': dash['Dashboard']})
        for i, func in enumerate(dash['Fungsi'][:4]):  # Max 4 functions per dashboard
            simple_rows.append({'Item': func})
        # Pad to 4 items
        for _ in range(4 - min(4, len(dash['Fungsi']))):
            simple_rows.append({'Item': ''})
    
    df_simple = pd.DataFrame(simple_rows)
    simple_csv = output_dir / 'DASHBOARD_SUMMARY_SIMPLE.csv'
    df_simple.to_csv(simple_csv, index=False, encoding='utf-8-sig')
    print(f'Saved: {simple_csv}')
    
    return df

if __name__ == '__main__':
    df = create_dashboard_summary()
    print('\nDashboard Summary created successfully!')
    print(df.head(20).to_string())
