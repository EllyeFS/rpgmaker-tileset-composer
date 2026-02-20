"""
Entry point for PyInstaller builds.
Uses absolute imports to work as a standalone script.
"""

import sys
import os

# Add src to path for absolute imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from src.ui.main_window import MainWindow


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
