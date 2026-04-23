"""
grid_renderer.py

Rendering logic for the tile grid.  This module is intentionally UI-agnostic:
it knows nothing about windows, layouts, or application lifecycle.  It only
populates a QGraphicsScene that a host window can embed inside any QGraphicsView.
"""

import os
from typing import Dict, List

import numpy as np
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPixmap, QPainter
from PyQt6.QtWidgets import QGraphicsScene, QGraphicsPixmapItem

from tile_loader import load_tiles, load_tile_variants

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
        Directory containing tile images named ``<tile_type>.png``.
        Used as a fallback when no spritesheet variants are loaded.
    tile_variants : dict, optional
        Maps each integer tile type to a list of (col, row) spritesheet
        coordinates.  When provided, a random variant is selected per
        tile on each render call.  Every tile type that appears in the
        grid must have an entry — a KeyError is raised at render time
        if one is missing.

        Example::

            tile_variants = {
                0: [(0, 7), (1, 7)],   # water variants
                1: [(2, 5), (3, 5)],   # grass variants
                2: [(5, 5)],           # forest (single sprite)
                3: [(6, 5)],           # rock   (single sprite)
            }
    """

    def __init__(
        self,
        tile_size: int = 32,
        assets_dir: str = "assets",
        tile_variants: Dict[int, List[tuple]] | None = None,
    ) -> None:
        self.tile_size = tile_size
        self.assets_dir = assets_dir
        # _pixmap_cache: single pixmap per tile type (non-variant path)
        self._pixmap_cache: Dict[str, QPixmap] = {}
        # _variant_pixmaps: list of pixmaps per tile type (variant path)
        self._variant_pixmaps: Dict[str, List[QPixmap]] = {}
        self._scene = QGraphicsScene()

        if tile_variants is not None:
            self._load_variant_pixmaps(tile_variants)
        else:
            self._preload_spritesheet_tiles()

    def _load_variant_pixmaps(self, tile_variants: Dict[int, List[tuple]]) -> None:
        """
        Load all sprite variants from the spritesheet and store them keyed
        by tile type string.  Raises ValueError if any list is empty.
        """
        try:
            int_variants = load_tile_variants(tile_variants, display_size=self.tile_size)
            for int_type, pixmaps in int_variants.items():
                tile_type = _INT_TO_TILE.get(int_type, str(int_type))
                self._variant_pixmaps[tile_type] = pixmaps
        except FileNotFoundError as exc:
            raise FileNotFoundError(
                f"[TileRenderer] Cannot load tile variants: {exc}"
            ) from exc

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

    def render(self, tile_grid: np.ndarray, seed: int = 0) -> QGraphicsScene:
        """
        Clear the internal scene and draw *tile_grid* into it.

        Parameters
        ----------
        tile_grid : np.ndarray
            A (height x width) numpy object array where each element is a
            dict with keys ``"base"`` (int) and ``"overlay"`` (int | None),
            as produced by ``world_generator.generate_world()``.
        seed : int
            Seed for variant selection so the same grid always renders
            identically.  Defaults to 0.

        Returns
        -------
        QGraphicsScene
            The populated scene.
        """
        self._scene.clear()

        height, width = tile_grid.shape
        ts = self.tile_size
        use_variants = bool(self._variant_pixmaps)
        rng = np.random.default_rng(seed) if use_variants else None

        for y in range(height):
            for x in range(width):
                cell = tile_grid[y, x]
                # Render terrain base first, then overlay object on top.
                self._render_base_at(cell["base"], x, y, ts, use_variants, rng)
                if cell["overlay"] is not None:
                    self._render_overlay_at(cell["overlay"], x, y, ts, use_variants, rng)

        self._scene.setSceneRect(0, 0, width * ts, height * ts)
        return self._scene

    @property
    def scene(self) -> QGraphicsScene:
        """The underlying QGraphicsScene (contains the last rendered grid)."""
        return self._scene

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _render_base_at(
        self,
        int_type: int,
        x: int,
        y: int,
        ts: int,
        use_variants: bool,
        rng,
    ) -> None:
        """Render a base terrain tile at grid position (x, y)."""
        pixmap = self._resolve_pixmap(int_type, use_variants, rng)
        item = QGraphicsPixmapItem(pixmap)
        item.setTransformationMode(Qt.TransformationMode.FastTransformation)
        item.setPos(x * ts, y * ts)
        self._scene.addItem(item)

    def _render_overlay_at(
        self,
        int_type: int,
        x: int,
        y: int,
        ts: int,
        use_variants: bool,
        rng,
    ) -> None:
        """
        Render an overlay object tile at grid position (x, y), bottom-aligned
        to the base tile.

        Overlay sprites may be taller than one tile (e.g. a tree that occupies
        two tile heights).  The bottom edge of the overlay is pinned to the
        bottom edge of the base tile so objects sit naturally on the terrain
        rather than floating or being clipped at the top.

        Vertical offset formula::

            y_offset = pixmap.height() - ts
            scene_y  = y * ts - y_offset
        """
        pixmap = self._resolve_pixmap(int_type, use_variants, rng)
        y_offset = pixmap.height() - ts
        item = QGraphicsPixmapItem(pixmap)
        item.setTransformationMode(Qt.TransformationMode.FastTransformation)
        item.setPos(x * ts, y * ts - y_offset)
        self._scene.addItem(item)

    def _resolve_pixmap(
        self,
        int_type: int,
        use_variants: bool,
        rng,
    ) -> QPixmap:
        """
        Resolve the pixmap for *int_type*, raising if the type is unknown.

        Raises
        ------
        KeyError
            If *int_type* has no registered tile type string.
        """
        tile_type = _INT_TO_TILE.get(int_type)
        if tile_type is None:
            raise KeyError(
                f"No tile type string registered for int '{int_type}'. "
                "Add it to _INT_TO_TILE in grid_renderer.py."
            )
        return self._pick_variant(tile_type, rng) if use_variants else self._get_pixmap(tile_type)

    def _render_tile_at(
        self,
        int_type: int,
        x: int,
        y: int,
        ts: int,
        use_variants: bool,
        rng,
    ) -> None:
        """Deprecated: use _render_base_at / _render_overlay_at instead."""
        pixmap = self._resolve_pixmap(int_type, use_variants, rng)
        item = QGraphicsPixmapItem(pixmap)
        item.setTransformationMode(Qt.TransformationMode.FastTransformation)
        item.setPos(x * ts, y * ts)
        self._scene.addItem(item)

    def _pick_variant(self, tile_type: str, rng: np.random.Generator) -> QPixmap:
        """
        Randomly select one pixmap from the variant list for *tile_type*.

        Raises
        ------
        KeyError
            If *tile_type* has no entry in the variant map.
        """
        variants = self._variant_pixmaps.get(tile_type)
        if variants is None:
            raise KeyError(
                f"No variants registered for tile type '{tile_type}'. "
                "Add it to the tile_variants dict passed to TileRenderer."
            )
        index = int(rng.integers(0, len(variants)))
        return variants[index]

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
