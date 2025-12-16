"""Quick NDRE stats per category"""
import pandas as pd
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent))

import logging
logging.disable(logging.CRITICAL)

from src.ingestion import load_and_clean_data, load_ame_iv_data

df2 = load_and_clean_data('data/input/tabelNDREnew.csv')
df4 = load_ame_iv_data('data/input/AME_IV.csv')

print("NDRE Mean per Category:")
print()
for name, df in [("AME_II", df2), ("AME_IV", df4)]:
    m = df[df['Category']=='MATURE']['NDRE125'].mean()
    y = df[df['Category']=='YOUNG']['NDRE125'].mean() if len(df[df['Category']=='YOUNG']) > 0 else 0
    print(f"{name}: MATURE={m:.3f}, YOUNG={y:.3f}, Diff={m-y:.3f}")

print()
print("Counts per Category:")
for name, df in [("AME_II", df2), ("AME_IV", df4)]:
    for cat in ['MATURE','YOUNG','DEAD','EMPTY']:
        c = len(df[df['Category']==cat])
        print(f"  {name} {cat}: {c:,}")
    print()
