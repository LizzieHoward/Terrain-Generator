"""
main_window.py — Main application window.

Responsibilities:
  - Define the visual structure of the application (layout, widgets).
  - Forward user input events (button clicks) to the controller.
  - Expose a clean public API (display_grid) so the controller can push
    content into the view without knowing Qt internals.
  - Contain no business logic.
"""

from __future__ import annotations

import numpy as np
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from grid_renderer import TileRenderer

# Maps the integer encoding used by world_generator back to the tile
# type strings that TileRenderer understands.
_INT_TO_TILE: dict[int, str] = {
    0: "water",
    1: "grass",
    2: "trees",
    3: "rocks",
}


class MainWindow(QMainWindow):
    """
    Top-level application window.

    Layout
    ------
    ┌─────────────────────────────────┐
    │  [Generate]                     │  ← toolbar row
    ├─────────────────────────────────┤
    │                                 │
    │        render area              │  ← QGraphicsView (placeholder)
    │                                 │
    └─────────────────────────────────┘
    """

    def __init__(self) -> None:
        super().__init__()
        self._controller = None  # injected after construction by main.py
        self._renderer = TileRenderer(tile_size=20, assets_dir="assets")
        self._setup_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        self.setWindowTitle("Terrain Generator")
        self.resize(800, 600)

        # --- Toolbar row ---
        self._generate_btn = QPushButton("Generate")
        self._generate_btn.setFixedWidth(100)
        self._generate_btn.clicked.connect(self._on_generate_clicked)

        toolbar_layout = QHBoxLayout()
        toolbar_layout.addWidget(self._generate_btn)
        toolbar_layout.addStretch()

        # --- Render area ---
        # Start with an empty scene; display_grid() will replace it with
        # a fully rendered tile scene when the user clicks Generate.
        placeholder_scene = QGraphicsScene()
        placeholder_scene.addText("Press 'Generate' to create a world.")

        self._view = QGraphicsView(placeholder_scene)
        self._view.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self._view.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        # Disable smooth pixel transforms for crisp tile rendering later.
        self._view.setRenderHint(self._view.renderHints().__class__.SmoothPixmapTransform, False)

        # --- Root layout ---
        root_layout = QVBoxLayout()
        root_layout.addLayout(toolbar_layout)
        root_layout.addWidget(self._view)

        container = QWidget()
        container.setLayout(root_layout)
        self.setCentralWidget(container)

    # ------------------------------------------------------------------
    # Dependency injection
    # ------------------------------------------------------------------

    def set_controller(self, controller) -> None:
        """Inject the controller after construction."""
        self._controller = controller

    # ------------------------------------------------------------------
    # Public view API (called by the controller)
    # ------------------------------------------------------------------

    def display_grid(self, grid: np.ndarray) -> None:
        """
        Display *grid* in the render area.

        Currently renders a plain-text summary of the grid shape as a
        placeholder.  Replace this method body when grid_renderer is
        integrated (pass the QGraphicsScene returned by TileRenderer.render()
        to self._view.setScene(...)).
        """
        # Convert the integer grid to tile-type strings, then delegate
        # all drawing to TileRenderer which returns a populated QGraphicsScene.
        str_grid = np.vectorize(_INT_TO_TILE.get)(grid)
        scene = self._renderer.render(str_grid)
        self._view.setScene(scene)

    # ------------------------------------------------------------------
    # Private slot
    # ------------------------------------------------------------------

    def _on_generate_clicked(self) -> None:
        """Forward the button click to the controller."""
        if self._controller is not None:
            self._controller.generate_world()
