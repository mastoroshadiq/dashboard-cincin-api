"""
Analisis Produktivitas Blok (Yield = Ton/Ha)
============================================
Top 10 blok paling produktif dan tidak produktif
Berdasarkan varietas dan Luas Ha
"""
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

def load_production_data():
    """Load and parse data_gabungan.xlsx"""
    file_path = Path(r'd:\PythonProjects\simulasi_poac\poac_sim\data\input\data_gabungan.xlsx')
    
    # Read raw to understand structure
    df_raw = pd.read_excel(file_path, header=None)
    
    # Based on analysis: headers at rows 0-7, data starts at row 8
    # Col 0: Blok, Col 1: Tahun Tanam, Col 2: Umur, Col 3-5: Divisi/Estate
    
    # Skip header rows and use data
    df = df_raw.iloc[8:].copy().reset_index(drop=True)
    
    # Assign column names for key columns (based on observed structure)
    # We need: Blok, Luas, Varietas, Production
    df.columns = [f'col_{i}' for i in range(df.shape[1])]
    
    # Map identified columns
    df = df.rename(columns={
        'col_0': 'Blok',
        'col_1': 'Tahun_Tanam',
        'col_2': 'Umur',
        'col_3': 'Divisi',
        'col_4': 'Estate',
        'col_5': 'Afdeling'
    })
    
    # Find Luas and Varietas columns by looking for patterns
    # Typically: Luas Ha is numeric around 15-35, Varietas is text like 'TENERA', 'DxP'
    
    return df, df_raw

def find_key_columns(df_raw):
    """Find columns for Luas Ha, Varietas, and Production."""
    
    # Search headers (rows 0-7) for key words
    key_cols = {
        'luas': None,
        'varietas': None,
        'produksi': None,
        'yield': None
    }
    
    for i in range(8):
        for j in range(min(50, df_raw.shape[1])):
            val = df_raw.iloc[i, j]
            if pd.notna(val):
                val_str = str(val).lower()
                if 'luas' in val_str and key_cols['luas'] is None:
                    key_cols['luas'] = j
                if 'varietas' in val_str or 'var' in val_str:
                    key_cols['varietas'] = j
                if 'produksi' in val_str or 'prod' in val_str:
                    key_cols['produksi'] = j
                if 'ton' in val_str or 'yield' in val_str:
                    key_cols['yield'] = j
    
    return key_cols

def analyze_productivity():
    """Main analysis function."""
    print("=" * 70)
    print("ANALISIS PRODUKTIVITAS BLOK")
    print("Top 10 Most & Least Productive (Yield = Ton/Ha)")
    print("=" * 70)
    
    df, df_raw = load_production_data()
    
    print(f"\nTotal blok: {len(df)}")
    
    # Find key columns
    key_cols = find_key_columns(df_raw)
    print(f"\nIdentified columns: {key_cols}")
    
    # If we can't find by header, use column analysis
    # Luas is typically column 6-10 with values 15-35
    # Look for potential Luas column
    potential_luas = None
    for col in ['col_6', 'col_7', 'col_8', 'col_9', 'col_10']:
        if col in df.columns:
            col_vals = pd.to_numeric(df[col], errors='coerce')
            mean_val = col_vals.mean()
            if 10 < mean_val < 50:  # Typical Luas Ha range
                potential_luas = col
                break
    
    if potential_luas:
        df['Luas_Ha'] = pd.to_numeric(df[potential_luas], errors='coerce')
        print(f"Using {potential_luas} as Luas_Ha (mean: {df['Luas_Ha'].mean():.1f})")
    
    # For now, display available data
    print("\n" + "-" * 70)
    print("SAMPLE DATA (First 10 rows, key columns):")
    print("-" * 70)
    
    display_cols = ['Blok', 'Tahun_Tanam', 'Divisi', 'Estate']
    if 'Luas_Ha' in df.columns:
        display_cols.append('Luas_Ha')
    
    print(df[display_cols].head(10).to_string())
    
    # Check for production columns (large numeric values)
    print("\n" + "-" * 70)
    print("LOOKING FOR PRODUCTION DATA (High-value numeric columns):")
    print("-" * 70)
    
    for i in range(15, min(50, df.shape[1])):
        col = f'col_{i}'
        if col in df.columns:
            col_vals = pd.to_numeric(df[col], errors='coerce')
            total = col_vals.sum()
            if total > 100000:  # Likely production data
                print(f"  {col}: total = {total:,.0f}")
    
    return df

if __name__ == '__main__':
    df = analyze_productivity()
