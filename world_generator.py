"""
world_generator.py — Procedural world generation pipeline.

Responsibilities:
  - Combine noise generation and tile classification into a single,
    easy-to-call function: generate_world().
  - Return a plain 2D list of integers so callers have no dependency on
    NumPy or any internal data structure.
  - Contain no UI or rendering logic.

Tile integer encoding:
    0 = water   (low elevation — noise value ≤ 0.30)
    1 = grass   (mid elevation — noise value ≤ 0.55)
    2 = trees   (high elevation — noise value ≤ 0.78)
    3 = rocks   (peaks         — noise value > 0.78)

How Perlin noise drives terrain distribution
--------------------------------------------
Perlin noise produces smooth, continuous values in [0, 1] after
normalization.  Low values cluster around simulated "valleys" and
water bodies; high values represent elevated terrain.  By slicing
that continuous range at fixed thresholds we convert a smooth
gradient into discrete biome tiles.  The scale parameter controls
how gradually values transition: a large scale produces wide biomes
with gentle borders; a small scale produces fragmented, chaotic
patches.  Octaves add layered detail on top of the base shape —
coarse octaves define mountains and plains, fine octaves add
surface roughness.
"""

from __future__ import annotations

from typing import List

from noise_generator import generate_noise_map
from tile_mapper import TileThresholds, map_tiles


# Map the string tile types produced by tile_mapper to the integer
# encoding expected by the rest of the application.
_TILE_TO_INT: dict[str, int] = {
    "water": 0,
    "grass": 1,
    "trees": 2,
    "rocks": 3,
}

# Default noise scale.  Tweak upward for broader biomes, downward for
# more fragmented terrain.
_DEFAULT_SCALE: float = 200.0


def generate_world(
    width: int,
    height: int,
    seed: int,
    scale: float = _DEFAULT_SCALE,
    thresholds: TileThresholds | None = None,
) -> List[List[int]]:
    """
    Generate a deterministic procedural world grid.

    Pipeline
    --------
    1. generate_noise_map  — produce a (height × width) Perlin noise array
                             normalized to [0, 1].  The seed ensures the
                             same inputs always yield the same output.
    2. map_tiles           — classify each noise value into a tile type
                             string using configurable thresholds.
    3. Integer encoding    — convert tile strings to integers for a
                             simple, dependency-free output format.

    Parameters
    ----------
    width  : Number of tile columns.
    height : Number of tile rows.
    seed   : Integer seed — identical seeds produce identical worlds.
    scale  : Perlin noise zoom level (default 200).  Higher = smoother
             terrain with larger biomes; lower = noisier, more fragmented.
    thresholds : Optional custom TileThresholds.  Pass one to override the
                 default water/grass/trees/rocks boundaries.

    Returns
    -------
    A (height × width) 2D list of ints:
        0 = water, 1 = grass, 2 = trees, 3 = rocks
    """
    # Step 1 — continuous noise field driven by seed for reproducibility.
    noise_map = generate_noise_map(width, height, scale=scale, seed=seed)

    # Step 2 — threshold the noise field into discrete tile types.
    # Low noise values → water; mid values → grass/trees; high → rocks.
    tile_grid = map_tiles(noise_map, thresholds=thresholds)

    # Step 3 — convert string tiles to the integer encoding.
    return [
        [_TILE_TO_INT.get(str(tile_grid[y, x]), 0) for x in range(width)]
        for y in range(height)
    ]
