"""
grid_renderer.py

Rendering logic for the tile grid.  This module is intentionally UI-agnostic:
it knows nothing about windows, layouts, or application lifecycle.  It only
populates a QGraphicsScene that a host window can embed inside any QGraphicsView.
"""

import os
from typing import Dict

import numpy as np
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPixmap, QPainter
from PyQt6.QtWidgets import QGraphicsScene, QGraphicsPixmapItem

from tile_loader import load_tiles

# Maps the integer keys returned by tile_loader to the string tile types
# used throughout the rest of the pipeline.
_INT_TO_TILE: Dict[int, str] = {
    0: "water",
    1: "grass",
    2: "trees",
    3: "rocks",
}


# Fallback colors used when a tile image is missing from the assets folder.
_FALLBACK_COLORS: Dict[str, str] = {
    "water": "#3a6ea5",
    "grass": "#5a8a3c",
    "trees": "#2d5a1b",
    "rocks": "#7a6a5a",
}
_DEFAULT_FALLBACK_COLOR = "#888888"


class TileRenderer:
    """
    Renders a 2D tile grid into a QGraphicsScene.

    Parameters
    ----------
    tile_size : int
        Width and height of each tile in pixels (assumed square).
    assets_dir : str
        Directory containing tile images named ``<tile_type>.png``
        (e.g. ``assets/water.png``).  Missing images are replaced with
        solid-colour rectangles so the renderer never raises on missing files.
    """

    def __init__(self, tile_size: int = 32, assets_dir: str = "assets") -> None:
        self.tile_size = tile_size
        self.assets_dir = assets_dir
        self._pixmap_cache: Dict[str, QPixmap] = {}
        self._scene = QGraphicsScene()
        self._preload_spritesheet_tiles()

    def _preload_spritesheet_tiles(self) -> None:
        """
        Load all tiles from the spritesheet via tile_loader and populate
        the pixmap cache.  If the spritesheet is missing the fallback
        colour path in _load_or_create_pixmap() is still used.
        """
        try:
            spritesheet_tiles = load_tiles(display_size=self.tile_size)
            for int_type, tile_type in _INT_TO_TILE.items():
                pixmap = spritesheet_tiles.get(int_type)
                if pixmap and not pixmap.isNull():
                    self._pixmap_cache[tile_type] = pixmap
        except FileNotFoundError as exc:
            # Spritesheet not found — renderer will use colour fallbacks.
            print(f"[TileRenderer] Spritesheet not loaded: {exc}")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def render(self, tile_grid: np.ndarray) -> QGraphicsScene:
        """
        Clear the internal scene and draw *tile_grid* into it.

        Parameters
        ----------
        tile_grid : np.ndarray
            A (height x width) array of tile-type strings, as produced by
            ``tile_mapper.map_tiles()``.

        Returns
        -------
        QGraphicsScene
            The populated scene.  Assign it to a QGraphicsView via
            ``view.setScene(renderer.render(grid))``.
        """
        self._scene.clear()

        height, width = tile_grid.shape
        ts = self.tile_size

        for y in range(height):
            for x in range(width):
                tile_type = str(tile_grid[y, x])
                pixmap = self._get_pixmap(tile_type)
                item = QGraphicsPixmapItem(pixmap)
                # Disable Qt's built-in smooth transform for crisp pixel art.
                item.setTransformationMode(Qt.TransformationMode.FastTransformation)
                item.setPos(x * ts, y * ts)
                self._scene.addItem(item)

        self._scene.setSceneRect(0, 0, width * ts, height * ts)
        return self._scene

    @property
    def scene(self) -> QGraphicsScene:
        """The underlying QGraphicsScene (contains the last rendered grid)."""
        return self._scene

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_pixmap(self, tile_type: str) -> QPixmap:
        """Return a cached QPixmap for *tile_type*, loading or creating it."""
        if tile_type not in self._pixmap_cache:
            self._pixmap_cache[tile_type] = self._load_or_create_pixmap(tile_type)
        return self._pixmap_cache[tile_type]

    def _load_or_create_pixmap(self, tile_type: str) -> QPixmap:
        """
        Attempt to load ``<assets_dir>/<tile_type>.png``.
        Fall back to a solid-colour QPixmap if the file is absent.
        """
        path = os.path.join(self.assets_dir, f"{tile_type}.png")
        if os.path.isfile(path):
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                return self._scale_pixmap(pixmap)

        return self._create_fallback_pixmap(tile_type)

    def _scale_pixmap(self, pixmap: QPixmap) -> QPixmap:
        """Scale *pixmap* to tile_size x tile_size without interpolation."""
        if pixmap.width() == self.tile_size and pixmap.height() == self.tile_size:
            return pixmap
        return pixmap.scaled(
            self.tile_size,
            self.tile_size,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.FastTransformation,  # no smoothing
        )

    def _create_fallback_pixmap(self, tile_type: str) -> QPixmap:
        """Create a solid-colour QPixmap for *tile_type*."""
        color_hex = _FALLBACK_COLORS.get(tile_type, _DEFAULT_FALLBACK_COLOR)
        pixmap = QPixmap(self.tile_size, self.tile_size)
        pixmap.fill(QColor(color_hex))
        return pixmap
