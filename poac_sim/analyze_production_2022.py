"""
Analisis Produksi per Blok - Tahun 2022
=======================================
Final version - Estate Level Analysis
"""
import pandas as pd
from pathlib import Path

def load_production_data():
    """Load production data from Real VS Potensi Inti."""
    file_path = Path(r'd:\PythonProjects\simulasi_poac\data\input\Realisasi vs Potensi PT SR.xlsx')
    df = pd.read_excel(file_path, sheet_name='Real VS Potensi Inti', skiprows=5)
    df = df[df.iloc[:, 1].astype(str).str.contains('AME', na=False)].reset_index(drop=True)
    return df

def analyze_production_2022_by_estate():
    """
    Analyze 2022 production by Estate.
    
    Based on column pattern analysis:
    - Cols 0-6: Metadata (No, Estate, Blok, Luas, RPC, SPH, Tahun_Tanam)
    - Production columns: 9, 12, 18, 21, 27, 30, 36, 39, 45, 48, 54, 57
    - Pattern: Every 9 columns = 1 year's data (Real, Potensi, Gap for different metrics)
    - Cols 9, 12 = 2010, Cols 18, 21 = 2011, etc.
    - 2022 = 12 years from 2010 = around Col 9 + (12 * 3) = Col 45
    - Using Col 45 as 2022 Realisasi (5,462,161 Kg total)
    """
    
    print("=" * 70)
    print("ANALISIS PRODUKSI KELAPA SAWIT - TAHUN 2022")
    print("Sheet: Real VS Potensi Inti | Level: Estate")
    print("=" * 70)
    
    df = load_production_data()
    
    # Map column names
    df.columns = [f'col_{i}' for i in range(len(df.columns))]
    df = df.rename(columns={
        'col_0': 'No',
        'col_1': 'Estate', 
        'col_2': 'Blok',
        'col_3': 'Luas_Ha',
        'col_4': 'RPC',
        'col_5': 'SPH',
        'col_6': 'Tahun_Tanam'
    })
    
    # Convert to numeric
    for col in ['Luas_Ha', 'SPH', 'Tahun_Tanam']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Use Col 45 as 2022 Realisasi production (in Kg)
    df['Prod_2022_Kg'] = pd.to_numeric(df['col_45'], errors='coerce')
    
    print(f"\nTotal Blok: {len(df)}")
    print(f"Estate: {df['Estate'].unique().tolist()}")
    
    # Estate Summary
    print("\n" + "=" * 70)
    print("PRODUKSI 2022 PER ESTATE")
    print("=" * 70)
    
    estate_prod = df.groupby('Estate').agg({
        'Blok': 'count',
        'Luas_Ha': 'sum',
        'Prod_2022_Kg': 'sum'
    }).round(0)
    
    estate_prod.columns = ['Jumlah_Blok', 'Luas_Ha', 'Produksi_2022_Kg']
    estate_prod['Produktivitas_Kg_Ha'] = (estate_prod['Produksi_2022_Kg'] / estate_prod['Luas_Ha']).round(0)
    estate_prod['Produksi_2022_Ton'] = (estate_prod['Produksi_2022_Kg'] / 1000).round(0)
    
    print(estate_prod[['Jumlah_Blok', 'Luas_Ha', 'Produksi_2022_Ton', 'Produktivitas_Kg_Ha']].to_string())
    
    # Totals
    print("\n" + "-" * 70)
    total_prod = estate_prod['Produksi_2022_Kg'].sum()
    total_luas = estate_prod['Luas_Ha'].sum()
    total_blok = estate_prod['Jumlah_Blok'].sum()
    avg_prod = total_prod / total_luas if total_luas > 0 else 0
    
    print(f"TOTAL BLOK:       {total_blok:,.0f}")
    print(f"TOTAL LUAS:       {total_luas:,.0f} Ha")
    print(f"TOTAL PRODUKSI:   {total_prod:,.0f} Kg ({total_prod/1000:,.0f} Ton)")
    print(f"AVG PRODUKTIVITAS: {avg_prod:,.0f} Kg/Ha")
    
    # Top 10 Blok by Production
    print("\n" + "=" * 70)
    print("TOP 10 BLOK DENGAN PRODUKSI TERTINGGI 2022")
    print("=" * 70)
    
    top_blok = df.nlargest(10, 'Prod_2022_Kg')[['Estate', 'Blok', 'Luas_Ha', 'Prod_2022_Kg']]
    top_blok['Produksi_Ton'] = (top_blok['Prod_2022_Kg'] / 1000).round(1)
    print(top_blok[['Estate', 'Blok', 'Luas_Ha', 'Produksi_Ton']].to_string(index=False))
    
    return df, estate_prod

if __name__ == '__main__':
    df, summary = analyze_production_2022_by_estate()
