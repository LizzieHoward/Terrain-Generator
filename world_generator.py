"""
world_generator.py — Procedural world generation pipeline.

Responsibilities:
  - Combine noise generation and tile classification into a single,
    easy-to-call function: generate_world().
  - Return a plain 2D list of integers so callers have no dependency on
    NumPy or any internal data structure.
  - Contain no UI or rendering logic.

Tile layer structure per cell:
    {
        "base":    int        # terrain drawn first
        "overlay": int | None  # object drawn on top (or None)
    }

Layer semantics:
    water  → base=water,  overlay=None
    grass  → base=grass,  overlay=None  (rare chance of a tree overlay)
    forest → base=grass,  overlay=tree  (dense tree placement)
    rocks  → base=rock,   overlay=None  (rock IS the terrain, no grass underneath)

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

import random as _random
from typing import Dict, List

from noise_generator import generate_noise_map
from tile_mapper import TileThresholds, map_tiles


# Probability that a plain grass tile spawns a tree overlay.
_GRASS_TREE_CHANCE: float = 0.04

# Probability that a forest tile spawns a tree overlay (dense coverage).
_FOREST_TREE_CHANCE: float = 0.80

# Integer tile type constants used in layer dicts.
_WATER  = 0
_GRASS  = 1
_TREES  = 2  # overlay object only
_ROCKS  = 3  # base terrain

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
    A (height × width) 2D list of layer dicts::

        {"base": int, "overlay": int | None}

    Integer constants: 0=water, 1=grass, 2=trees (overlay), 3=rocks (base)
    """
    # Step 1 — continuous noise field driven by seed for reproducibility.
    noise_map = generate_noise_map(width, height, scale=scale, seed=seed)

    # Step 2 — threshold the noise field into discrete tile type strings.
    tile_grid = map_tiles(noise_map, thresholds=thresholds)

    # Step 3 — convert tile type strings to layered cell dicts.
    #
    # Semantic rules:
    #   water  → water base, no overlay
    #   grass  → grass base, rare chance of a tree overlay
    #   trees  → grass base, high chance of a tree overlay (forest biome)
    #   rocks  → rock base,  no overlay (rock IS the terrain)
    #
    # A dedicated RNG seeded from the world seed drives overlay probability
    # so the same seed always produces the same object layout.
    rng = _random.Random(seed)

    def _cell(tile_type: str) -> Dict:
        if tile_type == "water":
            return {"base": _WATER, "overlay": None}
        if tile_type == "grass":
            overlay = _TREES if rng.random() < _GRASS_TREE_CHANCE else None
            return {"base": _GRASS, "overlay": overlay}
        if tile_type == "trees":
            overlay = _TREES if rng.random() < _FOREST_TREE_CHANCE else None
            return {"base": _GRASS, "overlay": overlay}
        if tile_type == "rocks":
            return {"base": _ROCKS, "overlay": None}
        raise ValueError(
            f"Unknown tile type '{tile_type}'. "
            "Add it to world_generator._cell()."
        )

    return [
        [_cell(str(tile_grid[y, x])) for x in range(width)]
        for y in range(height)
    ]
