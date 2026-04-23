"""
tile_loader.py — Spritesheet tile extractor.

Responsibilities:
  - Load a spritesheet image once.
  - Extract individual tile QPixmaps by (column, row) coordinate.
  - Return a dict mapping integer tile type → QPixmap.
  - No UI logic; purely an asset utility.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Tuple

from PyQt6.QtCore import Qt, QRect
from PyQt6.QtGui import QPixmap


# ---------------------------------------------------------------------------
# Spritesheet configuration
# ---------------------------------------------------------------------------

# Build an absolute path relative to this file's directory so it resolves
# correctly regardless of the working directory, and handles special
# characters (like &) in the filename safely.
_HERE = Path(__file__).parent
SPRITESHEET_PATH = str(
    _HERE / "Tiles" / "color_tileset_16x16_Jerom;Eiyeron_CC-BY-SA-3.0_8.png"
)

TILE_SIZE = 16  # source tile dimensions in pixels (square)

# Tile type integer → (column, row) position inside the spritesheet.
#   0 = water   → column 8, row 1
#   1 = grass   → column 8, row 2
#   2 = forest  → column 8, row 6
#   3 = rock    → column 8, row 7
TILE_COORDS: Dict[int, Tuple[int, int]] = {
    0: (0, 7),  # water
    1: (2, 5),  # grass / field
    2: (5, 5),  # forest
    3: (6, 5),  # rock
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_tile_variants(
    tile_variants: Dict[int, List[Tuple[int, int]]],
    display_size: int | None = None,
    spritesheet_path: str = SPRITESHEET_PATH,
) -> Dict[int, List[QPixmap]]:
    """
    Extract multiple sprite variants per tile type from the spritesheet.

    Parameters
    ----------
    tile_variants :
        Maps each tile type integer to a list of (col, row) coordinates
        on the spritesheet.  Every list must be non-empty — a ValueError
        is raised otherwise.
    display_size :
        If provided, each variant is scaled to this size using
        FastTransformation (no smoothing).
    spritesheet_path :
        Path to the spritesheet PNG.

    Returns
    -------
    Dict mapping tile type integer → list of QPixmap variants.
    """
    for tile_type, coords in tile_variants.items():
        if not coords:
            raise ValueError(
                f"tile_variants[{tile_type}] is empty — "
                "every tile type must have at least one variant."
            )

    spritesheet = _load_spritesheet(spritesheet_path)
    result: Dict[int, List[QPixmap]] = {}

    for tile_type, coords in tile_variants.items():
        pixmaps: List[QPixmap] = []
        for col, row in coords:
            x = col * TILE_SIZE
            y = row * TILE_SIZE
            pixmap = spritesheet.copy(QRect(x, y, TILE_SIZE, TILE_SIZE))
            if display_size is not None and display_size != TILE_SIZE:
                pixmap = pixmap.scaled(
                    display_size,
                    display_size,
                    Qt.AspectRatioMode.IgnoreAspectRatio,
                    Qt.TransformationMode.FastTransformation,
                )
            pixmaps.append(pixmap)
        result[tile_type] = pixmaps

    return result


def load_tiles(
    display_size: int | None = None,
    spritesheet_path: str = SPRITESHEET_PATH,
) -> Dict[int, QPixmap]:
    """
    Load all tile QPixmaps from the spritesheet.

    Parameters
    ----------
    display_size :
        If provided, each extracted tile is scaled to this pixel size
        using FastTransformation (no smoothing) before being returned.
        Defaults to the source TILE_SIZE (16 px) — no scaling.
    spritesheet_path :
        Path to the spritesheet PNG.  Override for testing or alternate
        asset packs.

    Returns
    -------
    Dict mapping tile type integer (0–3) → QPixmap.
    """
    spritesheet = _load_spritesheet(spritesheet_path)
    tiles: Dict[int, QPixmap] = {}

    for tile_type, (col, row) in TILE_COORDS.items():
        x = col * TILE_SIZE
        y = row * TILE_SIZE
        tile_pixmap = spritesheet.copy(QRect(x, y, TILE_SIZE, TILE_SIZE))

        if display_size is not None and display_size != TILE_SIZE:
            tile_pixmap = tile_pixmap.scaled(
                display_size,
                display_size,
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.FastTransformation,  # preserve pixel-art sharpness
            )

        tiles[tile_type] = tile_pixmap

    return tiles


def debug_tiles(
    display_size: int | None = None,
    spritesheet_path: str = SPRITESHEET_PATH,
) -> None:
    """
    Print a diagnostic summary of every extracted tile.

    Verifies that:
      - The spritesheet loaded successfully (non-null, expected dimensions).
      - Each tile QPixmap is non-null and has the expected pixel size.

    Intended for development use only; not called during normal runtime.
    """
    spritesheet = _load_spritesheet(spritesheet_path)
    ss_w, ss_h = spritesheet.width(), spritesheet.height()
    print(f"Spritesheet: {spritesheet_path!r}")
    print(f"  Size : {ss_w} x {ss_h} px  (null={spritesheet.isNull()})")
    print(f"  Expected columns: {ss_w // TILE_SIZE}, rows: {ss_h // TILE_SIZE}")
    print()

    tiles = load_tiles(display_size=display_size, spritesheet_path=spritesheet_path)
    names = {0: "water", 1: "grass", 2: "forest", 3: "rock"}

    for tile_type, pixmap in tiles.items():
        col, row = TILE_COORDS[tile_type]
        status = "OK" if not pixmap.isNull() else "NULL (extraction failed)"
        print(
            f"  Tile {tile_type} ({names.get(tile_type, '?'):>6})  "
            f"sheet[col={col}, row={row}]  "
            f"src_px=({col * TILE_SIZE}, {row * TILE_SIZE})  "
            f"size={pixmap.width()}x{pixmap.height()}  [{status}]"
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _load_spritesheet(path: str) -> QPixmap:
    """Load and validate the spritesheet, raising on failure."""
    pixmap = QPixmap(path)
    if pixmap.isNull():
        raise FileNotFoundError(
            f"Could not load spritesheet: {path!r}\n"
            "Check that the file exists relative to the working directory."
        )
    return pixmap
