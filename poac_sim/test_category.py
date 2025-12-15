"""Test tree category classification implementation - Write to file"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.ingestion import load_and_clean_data, load_ame_iv_data

with open('category_test_result.txt', 'w', encoding='utf-8') as f:
    f.write("="*70 + "\n")
    f.write("TEST: Tree Category Classification\n")
    f.write("="*70 + "\n")

    # Test AME II
    f.write("\n1. tabelNDREnew.csv (AME II)\n")
    f.write("-"*50 + "\n")
    df1 = load_and_clean_data('data/input/tabelNDREnew.csv')
    f.write(f"\nTotal: {len(df1):,} rows\n")
    f.write(f"Columns: {df1.columns.tolist()}\n")
    f.write(f"\nCategory distribution:\n")
    cat_counts1 = df1['Category'].value_counts()
    for cat, count in cat_counts1.items():
        pct = count / len(df1) * 100
        f.write(f"  {cat:<10}: {count:>8,} ({pct:>5.1f}%)\n")

    # Test AME IV
    f.write("\n\n2. AME_IV.csv (AME IV)\n")
    f.write("-"*50 + "\n")
    df2 = load_ame_iv_data('data/input/AME_IV.csv')
    f.write(f"\nTotal: {len(df2):,} rows\n")
    f.write(f"Columns: {df2.columns.tolist()}\n")
    f.write(f"\nCategory distribution:\n")
    cat_counts2 = df2['Category'].value_counts()
    for cat, count in cat_counts2.items():
        pct = count / len(df2) * 100
        f.write(f"  {cat:<10}: {count:>8,} ({pct:>5.1f}%)\n")

    # Summary
    f.write("\n" + "="*70 + "\n")
    f.write("SUMMARY: Segmentasi Populasi\n")
    f.write("="*70 + "\n")
    
    f.write("\n" + "-"*50 + "\n")
    f.write("             AME II          AME IV\n")
    f.write("-"*50 + "\n")
    for cat in ['MATURE', 'YOUNG', 'DEAD', 'EMPTY']:
        c1 = cat_counts1.get(cat, 0)
        c2 = cat_counts2.get(cat, 0)
        f.write(f"{cat:<10}: {c1:>10,}      {c2:>10,}\n")
    f.write("-"*50 + "\n")
    f.write(f"{'TOTAL':<10}: {len(df1):>10,}      {len(df2):>10,}\n")

print("Results written to category_test_result.txt")
