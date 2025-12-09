"""
POAC v3.3 - Spatial Hexagonal Geometry Module
Implements Logika B: Geometri Tetangga Heksagonal

Perkebunan sawit menggunakan pola mata lima (segitiga).
Logika grid kotak (Cartesian) DILARANG digunakan.

Hexagonal Grid dengan Odd-Row Offset:
- Baris Ganjil (R%2 != 0): Tetangga berada di diagonal kiri/kanan normal
- Baris Genap (R%2 == 0): Tetangga bergeser (offset)
"""

import pandas as pd
import logging
from typing import List, Tuple, Set

# Setup logging
logger = logging.getLogger(__name__)


def get_hex_neighbors(r: int, p: int) -> List[Tuple[int, int]]:
    """
    Get 6 hexagonal neighbors for a tree at position (r, p).
    
    Implements Logika B: Hexagonal Grid with Odd-Row Offset
    
    Hexagonal neighbor pattern (odd-row offset):
    
    Baris GANJIL (r % 2 != 0):
        NW=(r-1,p-1)  NE=(r-1,p)
              \\      /
               [r,p]
              /      \\
        SW=(r+1,p-1)  SE=(r+1,p)
        W=(r,p-1)     E=(r,p+1)
    
    Baris GENAP (r % 2 == 0):
        NW=(r-1,p)    NE=(r-1,p+1)
              \\      /
               [r,p]
              /      \\
        SW=(r+1,p)    SE=(r+1,p+1)
        W=(r,p-1)     E=(r,p+1)
    
    Args:
        r: Row number (N_BARIS)
        p: Tree position in row (N_POKOK)
        
    Returns:
        List of 6 neighbor coordinates as (row, pokok) tuples
    """
    neighbors = []
    
    if r % 2 != 0:  # Baris GANJIL
        # 6 tetangga untuk baris ganjil
        neighbors = [
            (r - 1, p - 1),  # NW - Northwest (atas kiri)
            (r - 1, p),      # NE - Northeast (atas kanan)
            (r, p - 1),      # W  - West (kiri)
            (r, p + 1),      # E  - East (kanan)
            (r + 1, p - 1),  # SW - Southwest (bawah kiri)
            (r + 1, p),      # SE - Southeast (bawah kanan)
        ]
    else:  # Baris GENAP (r % 2 == 0)
        # 6 tetangga untuk baris genap (offset ke kanan)
        neighbors = [
            (r - 1, p),      # NW - Northwest (atas kiri)
            (r - 1, p + 1),  # NE - Northeast (atas kanan)
            (r, p - 1),      # W  - West (kiri)
            (r, p + 1),      # E  - East (kanan)
            (r + 1, p),      # SW - Southwest (bawah kiri)
            (r + 1, p + 1),  # SE - Southeast (bawah kanan)
        ]
    
    return neighbors


def find_ring_candidates(
    df: pd.DataFrame, 
    g3_trees: pd.DataFrame
) -> Set[Tuple[int, str, int, int]]:
    """
    Find all healthy trees that form the "Ring of Fire" around G3 trees.
    
    Implements Logika C: Pembentukan Cincin Api (Ring Detection)
    
    Process:
    1. Ambil koordinat (r, p) dari semua G3
    2. Cari 6 tetangga heksagonalnya
    3. Validasi Tetangga:
       - Harus ada di database (bukan lahan kosong)
       - Bukan pohon G3 itu sendiri
    
    Args:
        df: Full DataFrame with all trees
        g3_trees: DataFrame containing only G3 (infected) trees
        
    Returns:
        Set of unique ring candidate tuples: (index, blok, baris, pokok)
    """
    if g3_trees.empty:
        logger.info("No G3 trees found. Ring candidates: 0")
        return set()
    
    # Build coordinate lookup sets per block for fast validation
    # Key: (Blok, N_BARIS, N_POKOK), Value: DataFrame index
    tree_coordinates = {}
    for idx, row in df.iterrows():
        key = (row['Blok'], int(row['N_BARIS']), int(row['N_POKOK']))
        tree_coordinates[key] = idx
    
    # Build set of G3 coordinates to exclude
    g3_coords = set()
    for _, row in g3_trees.iterrows():
        g3_coords.add((row['Blok'], int(row['N_BARIS']), int(row['N_POKOK'])))
    
    # Find ring candidates
    ring_candidates = set()
    
    for _, g3_tree in g3_trees.iterrows():
        blok = g3_tree['Blok']
        r = int(g3_tree['N_BARIS'])
        p = int(g3_tree['N_POKOK'])
        
        # Get hexagonal neighbors
        neighbors = get_hex_neighbors(r, p)
        
        for nr, np in neighbors:
            neighbor_key = (blok, nr, np)
            
            # Validation 1: Must exist in database (not empty land)
            if neighbor_key not in tree_coordinates:
                continue
            
            # Validation 2: Must not be G3 itself
            if neighbor_key in g3_coords:
                continue
            
            # Add to ring candidates
            ring_candidates.add((tree_coordinates[neighbor_key], blok, nr, np))
    
    logger.info(f"Ring candidates found: {len(ring_candidates)} trees around {len(g3_trees)} G3 trees")
    
    return ring_candidates


def mark_ring_candidates(df: pd.DataFrame, ring_candidates: Set[Tuple[int, str, int, int]]) -> pd.DataFrame:
    """
    Mark ring candidate trees in the DataFrame.
    
    Args:
        df: DataFrame with all trees
        ring_candidates: Set of ring candidate tuples from find_ring_candidates
        
    Returns:
        pd.DataFrame: DataFrame with Ring_Candidate column added
    """
    df_result = df.copy()
    
    # Initialize column
    df_result['Ring_Candidate'] = False
    
    # Mark ring candidates
    ring_indices = [candidate[0] for candidate in ring_candidates]
    df_result.loc[ring_indices, 'Ring_Candidate'] = True
    
    return df_result


def visualize_neighbors(r: int, p: int) -> str:
    """
    Generate ASCII visualization of hexagonal neighbors for debugging.
    
    Args:
        r: Row number
        p: Tree position
        
    Returns:
        str: ASCII art representation
    """
    neighbors = get_hex_neighbors(r, p)
    
    is_odd = r % 2 != 0
    row_type = "GANJIL" if is_odd else "GENAP"
    
    viz = f"""
Pohon ({r}, {p}) - Baris {row_type}:

    {neighbors[0]}    {neighbors[1]}
         \\        /
          [{r},{p}]
         /        \\
    {neighbors[4]}    {neighbors[5]}
    
    W={neighbors[2]}      E={neighbors[3]}
    
Semua tetangga: {neighbors}
"""
    return viz
