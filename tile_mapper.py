import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple


# --- Tile type constants ---

WATER = "water"
GRASS = "grass"
TREES = "trees"
ROCKS = "rocks"


# --- Threshold configuration ---

@dataclass
class TileThresholds:
    """
    Defines the upper noise value boundary for each tile type.

    Tiles are assigned by testing each threshold in order; the first
    threshold whose value is >= the noise sample wins. The final entry
    acts as a catch-all and its threshold value is ignored.

    Default ranges (noise values normalized to [0, 1]):
        water : 0.00 – 0.30
        grass : 0.30 – 0.55
        trees : 0.55 – 0.78
        rocks : 0.78 – 1.00
    """
    thresholds: List[Tuple[float, str]] = field(default_factory=lambda: [
        (0.30, WATER),
        (0.55, GRASS),
        (0.78, TREES),
        (1.00, ROCKS),
    ])

    def __post_init__(self):
        if not self.thresholds:
            raise ValueError("thresholds must contain at least one entry.")


# --- Core mapping function ---

def map_tiles(
    noise_map: np.ndarray,
    thresholds: TileThresholds | None = None,
) -> np.ndarray:
    """
    Convert a normalized 2D noise array into a 2D grid of tile type strings.

    Args:
        noise_map:   A (height x width) float array with values in [0, 1],
                     as produced by generate_noise_map().
        thresholds:  A TileThresholds instance defining tile boundaries.
                     Defaults to TileThresholds() if not provided.

    Returns:
        A (height x width) NumPy array of dtype object containing tile
        type strings (e.g. "water", "grass", "trees", "rocks").
    """
    if thresholds is None:
        thresholds = TileThresholds()

    height, width = noise_map.shape
    tile_grid = np.full((height, width), fill_value="", dtype=object)

    sorted_thresholds = sorted(thresholds.thresholds, key=lambda t: t[0])

    for y in range(height):
        for x in range(width):
            value = noise_map[y, x]
            tile_grid[y, x] = _classify(value, sorted_thresholds)

    return tile_grid


def _classify(value: float, sorted_thresholds: List[Tuple[float, str]]) -> str:
    """Return the tile type for a single noise value."""
    for threshold, tile_type in sorted_thresholds:
        if value <= threshold:
            return tile_type
    # Fallback: return the last tile type if value exceeds all thresholds
    return sorted_thresholds[-1][1]
