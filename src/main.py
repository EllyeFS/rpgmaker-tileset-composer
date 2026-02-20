"""
RPG Maker MZ Tileset Composer - Main Entry Point
"""

import sys

from PySide6.QtWidgets import QApplication

from .ui.main_window import MainWindow


def main():
    """Application entry point."""
    app = QApplication(sys.argv)
    app.setApplicationName("RPG Maker Tileset Composer")
    app.setOrganizationName("TilesetComposer")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
