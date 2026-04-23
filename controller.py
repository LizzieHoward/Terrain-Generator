"""
controller.py — Application controller.

Responsibilities:
  - Contain all business logic (world generation, configuration).
  - Act as the bridge between the procedural generation pipeline and the UI.
  - Never import or manipulate Qt widgets directly; communicate with the
    view only through its public API.
"""

from __future__ import annotations
import random
from world_generator import generate_world
import numpy as np


class AppController:
    """
    Coordinates world generation and delegates rendering to the view.

    Parameters
    ----------
    window :
        The MainWindow instance.  Stored as a reference so the controller
        can push updates to the UI without the UI pulling state.
    """

    def __init__(self, window) -> None:
        # Avoid a hard import of MainWindow here to keep the dependency
        # direction clear: controller → window interface, not the class.
        self._window = window

    # ------------------------------------------------------------------
    # Public actions (called by the view in response to user input)
    # ------------------------------------------------------------------

    def generate_world(self) -> None:
        seed = random.randint(0, 1_000_000)
        layered = generate_world(width=40, height=30, seed=seed)
        # Convert list-of-list-of-dicts to a numpy object array so the
        # renderer can index it with tile_grid[y, x].
        height, width = len(layered), len(layered[0])
        grid = np.empty((height, width), dtype=object)
        for y, row in enumerate(layered):
            for x, cell in enumerate(row):
                grid[y, x] = cell
        self._window.display_grid(grid, seed=seed)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _placeholder_grid(self, width: int, height: int) -> np.ndarray:
        """
        Return a (height x width) array of random integers in [0, 3].

        Each integer loosely represents a tile category:
            0 → water  1 → grass  2 → trees  3 → rocks
        """
        rng = np.random.default_rng()
        return rng.integers(0, 4, size=(height, width))
