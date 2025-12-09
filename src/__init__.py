"""
POAC v3.3 - Source Package Initialization
"""

# Lazy imports to avoid circular dependency issues
__all__ = [
    "load_and_clean_data",
    "calculate_zscore_by_block",
    "get_hex_neighbors",
    "find_ring_candidates",
    "run_simulation",
    "run_multi_scenario"
]

def __getattr__(name):
    if name == "load_and_clean_data":
        from .ingestion import load_and_clean_data
        return load_and_clean_data
    elif name == "calculate_zscore_by_block":
        from .statistics import calculate_zscore_by_block
        return calculate_zscore_by_block
    elif name == "get_hex_neighbors":
        from .spatial import get_hex_neighbors
        return get_hex_neighbors
    elif name == "find_ring_candidates":
        from .spatial import find_ring_candidates
        return find_ring_candidates
    elif name == "run_simulation":
        from .engine import run_simulation
        return run_simulation
    elif name == "run_multi_scenario":
        from .engine import run_multi_scenario
        return run_multi_scenario
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
