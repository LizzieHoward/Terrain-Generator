"""
main.py — Application entry point.

Responsibilities:
  - Bootstrap the PyQt6 application.
  - Instantiate the MainWindow (view) and AppController (logic).
  - Wire the controller to the window so UI events reach business logic.
  - Start the Qt event loop.
"""

import sys

from PyQt6.QtWidgets import QApplication

from main_window import MainWindow
from controller import AppController


def main() -> None:
    app = QApplication(sys.argv)

    window = MainWindow()
    controller = AppController(window)

    # Give the window a reference to the controller so button clicks
    # can call controller methods directly.
    window.set_controller(controller)

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
