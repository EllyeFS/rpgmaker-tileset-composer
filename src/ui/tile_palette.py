"""
Tile palette widget for displaying and selecting source tiles.
"""

from typing import List, Optional

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QScrollArea,
    QLabel,
    QFrame,
    QGridLayout,
    QSizePolicy,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPainter, QPen, QColor

from ..models.tile import Tile
from ..utils.constants import TILE_SIZE


class TileButton(QFrame):
    """
    A clickable tile display widget.
    
    Shows a single tile and emits a signal when clicked.
    """
    
    clicked = Signal(Tile)
    
    def __init__(self, tile: Tile, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.tile = tile
        self._selected = False
        
        # Set fixed size based on tile dimensions
        self.setFixedSize(tile.width + 2, tile.height + 2)  # +2 for border
        
        # Styling
        self.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Plain)
        self.setLineWidth(1)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self._update_style()
    
    @property
    def selected(self) -> bool:
        return self._selected
    
    @selected.setter
    def selected(self, value: bool):
        self._selected = value
        self._update_style()
        self.update()
    
    def _update_style(self):
        if self._selected:
            self.setStyleSheet("TileButton { border: 2px solid #3498db; }")
        else:
            self.setStyleSheet("TileButton { border: 1px solid #888; }")
    
    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        
        # Draw the tile pixmap centered (accounting for border)
        x = (self.width() - self.tile.width) // 2
        y = (self.height() - self.tile.height) // 2
        painter.drawPixmap(x, y, self.tile.pixmap)
        
        # Draw selection highlight
        if self._selected:
            painter.setPen(QPen(QColor("#3498db"), 2))
            painter.drawRect(0, 0, self.width() - 1, self.height() - 1)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.tile)
        super().mousePressEvent(event)


class TilePalette(QWidget):
    """
    A scrollable palette displaying tiles from source images.
    
    Tiles are displayed in a grid, grouped by source file.
    Emits tile_selected signal when a tile is clicked.
    """
    
    tile_selected = Signal(Tile)
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        self._tiles: List[Tile] = []
        self._tile_buttons: List[TileButton] = []
        self._selected_tile: Optional[Tile] = None
        self._columns = 8  # Number of columns in the grid
        
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Header
        self._header_label = QLabel("Tile Palette")
        self._header_label.setStyleSheet("font-weight: bold; padding: 5px;")
        layout.addWidget(self._header_label)
        
        # Scroll area for tiles
        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        layout.addWidget(self._scroll_area)
        
        # Container for tile grid
        self._tile_container = QWidget()
        self._tile_layout = QGridLayout(self._tile_container)
        self._tile_layout.setSpacing(4)
        self._tile_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self._scroll_area.setWidget(self._tile_container)
        
        # Placeholder when no tiles loaded
        self._placeholder = QLabel("Select a source folder\nto load tiles")
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._placeholder.setStyleSheet("color: #888; padding: 20px;")
        self._tile_layout.addWidget(self._placeholder, 0, 0)
    
    def set_tiles(self, tiles: List[Tile]):
        """Set the tiles to display in the palette (replaces existing)."""
        self._tiles = tiles
        self._selected_tile = None
        self._rebuild_grid()
    
    def prepend_tiles(self, tiles: List[Tile]):
        """Add tiles to the top of the palette (keeps existing, skips duplicates).
        
        Tiles from source images already in the palette are not added again.
        """
        # Get set of source paths already in palette
        existing_sources = {t.source_path for t in self._tiles}
        
        # Filter out tiles from sources that are already loaded
        new_tiles = [t for t in tiles if t.source_path not in existing_sources]
        
        if new_tiles:
            self._tiles = new_tiles + self._tiles
            self._selected_tile = None
            self._rebuild_grid()
    
    def clear(self):
        """Clear all tiles from the palette."""
        self._tiles = []
        self._selected_tile = None
        self._rebuild_grid()
    
    def _rebuild_grid(self):
        """Rebuild the tile grid display."""
        # Clear existing buttons
        for btn in self._tile_buttons:
            btn.deleteLater()
        self._tile_buttons.clear()
        
        # Clear layout
        while self._tile_layout.count():
            item = self._tile_layout.takeAt(0)
            if item.widget() and item.widget() != self._placeholder:
                item.widget().deleteLater()
        
        if not self._tiles:
            # Show placeholder
            self._placeholder.setParent(self._tile_container)
            self._tile_layout.addWidget(self._placeholder, 0, 0)
            self._header_label.setText("Tile Palette")
            return
        
        # Hide placeholder
        self._placeholder.setParent(None)
        
        # Group tiles by source file
        tiles_by_source: dict[str, List[Tile]] = {}
        for tile in self._tiles:
            source = tile.source_name
            if source not in tiles_by_source:
                tiles_by_source[source] = []
            tiles_by_source[source].append(tile)
        
        row = 0
        for source_name, source_tiles in tiles_by_source.items():
            # Add source file label
            source_label = QLabel(source_name)
            source_label.setStyleSheet(
                "font-weight: bold; color: #666; padding: 5px 0; "
                "border-bottom: 1px solid #ccc;"
            )
            self._tile_layout.addWidget(source_label, row, 0, 1, self._columns)
            row += 1
            
            # Add tiles in grid
            col = 0
            for tile in source_tiles:
                btn = TileButton(tile)
                btn.clicked.connect(self._on_tile_clicked)
                self._tile_buttons.append(btn)
                self._tile_layout.addWidget(btn, row, col)
                
                col += 1
                if col >= self._columns:
                    col = 0
                    row += 1
            
            # Move to next row after each source group
            if col > 0:
                row += 1
        
        # Add stretch at bottom
        self._tile_layout.setRowStretch(row, 1)
        
        # Update header
        self._header_label.setText(f"Tile Palette ({len(self._tiles)} tiles)")
    
    def _on_tile_clicked(self, tile: Tile):
        """Handle tile button click."""
        # Update selection state
        for btn in self._tile_buttons:
            btn.selected = (btn.tile is tile)
        
        self._selected_tile = tile
        self.tile_selected.emit(tile)
    
    @property
    def selected_tile(self) -> Optional[Tile]:
        """Get the currently selected tile."""
        return self._selected_tile
    
    def set_columns(self, columns: int):
        """Set the number of columns in the tile grid."""
        if columns > 0 and columns != self._columns:
            self._columns = columns
            self._rebuild_grid()
