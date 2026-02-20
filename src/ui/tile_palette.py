"""
Tile palette widget for displaying and selecting source tiles.

Tiles are always displayed on a 48×48 grid. Larger units (autotiles)
are displayed as multiple cells that select together as a group.
"""

from typing import List, Optional, Dict, Callable

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QScrollArea,
    QLabel,
    QFrame,
    QGridLayout,
    QSizePolicy,
    QApplication,
)
from PySide6.QtCore import Qt, Signal, QMimeData, QPoint
from PySide6.QtGui import QPainter, QPen, QColor, QDrag, QPixmap

from ..models.tile import Tile
from ..models.tile_unit import TileUnit
from ..utils.constants import TILE_SIZE


# Custom MIME type for tile unit drag operations
TILE_UNIT_MIME_TYPE = "application/x-rpgmaker-tileunit"

# Module-level storage for currently dragged unit (Qt drag doesn't preserve Python objects)
_current_drag_unit: Optional[TileUnit] = None


def get_current_drag_unit() -> Optional[TileUnit]:
    """Get the currently dragged tile unit."""
    return _current_drag_unit


def set_current_drag_unit(unit: Optional[TileUnit]):
    """Set the currently dragged tile unit."""
    global _current_drag_unit
    _current_drag_unit = unit


class TileButton(QFrame):
    """
    A clickable tile display widget.
    
    Shows a single 48×48 tile and emits a signal when clicked.
    The signal includes the tile's parent unit for group selection.
    Supports drag operations to move units to the canvas.
    """
    
    clicked = Signal(Tile)
    
    def __init__(self, tile: Tile, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.tile = tile
        self._selected = False
        self._drag_start_pos: Optional[QPoint] = None
        
        # All tiles are 48×48, plus border
        self.setFixedSize(TILE_SIZE + 2, TILE_SIZE + 2)
        
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
        x = (self.width() - TILE_SIZE) // 2
        y = (self.height() - TILE_SIZE) // 2
        painter.drawPixmap(x, y, self.tile.pixmap)
        
        # Draw selection highlight
        if self._selected:
            painter.setPen(QPen(QColor("#3498db"), 2))
            painter.drawRect(0, 0, self.width() - 1, self.height() - 1)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = event.position().toPoint()
            self.clicked.emit(self.tile)
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return
        if self._drag_start_pos is None:
            return
        
        # Check if we've moved far enough to start a drag
        distance = (event.position().toPoint() - self._drag_start_pos).manhattanLength()
        if distance < QApplication.startDragDistance():
            return
        
        # Get the unit to drag
        unit = self.tile.unit
        if unit is None:
            return
        
        # Create drag pixmap showing the full unit
        drag_pixmap = self._create_unit_pixmap(unit)
        
        # Create drag object
        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setData(TILE_UNIT_MIME_TYPE, b"")  # Marker data
        drag.setMimeData(mime_data)
        drag.setPixmap(drag_pixmap)
        
        # Hotspot at center of top-left tile (matches drop behavior)
        drag.setHotSpot(QPoint(TILE_SIZE // 2, TILE_SIZE // 2))
        
        # Store unit in module-level variable (Qt drag doesn't preserve Python objects)
        set_current_drag_unit(unit)
        
        # Execute drag
        drag.exec(Qt.DropAction.CopyAction)
        
        # Clear drag unit reference
        set_current_drag_unit(None)
        self._drag_start_pos = None
    
    def _create_unit_pixmap(self, unit: TileUnit) -> QPixmap:
        """Create a pixmap showing the complete unit."""
        width = unit.grid_width * TILE_SIZE
        height = unit.grid_height * TILE_SIZE
        
        pixmap = QPixmap(width, height)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        
        # Find the top-left position in pixels
        if unit.tiles:
            min_x = min(t.x for t in unit.tiles)
            min_y = min(t.y for t in unit.tiles)
            
            # Draw each tile at its relative position
            for tile in unit.tiles:
                rel_x = tile.x - min_x
                rel_y = tile.y - min_y
                painter.drawPixmap(rel_x, rel_y, tile.pixmap)
        
        painter.end()
        return pixmap


class TilePalette(QWidget):
    """
    A scrollable palette displaying tiles from source images.
    
    Tiles are displayed in a 48×48 grid, preserving their source layout.
    Clicking a tile selects its entire unit (for multi-tile autotiles).
    """
    
    # Emits the selected unit when a tile is clicked
    unit_selected = Signal(TileUnit)
    
    # Legacy signal for backward compatibility
    tile_selected = Signal(Tile)
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        self._units: List[TileUnit] = []
        self._tile_buttons: List[TileButton] = []
        self._selected_unit: Optional[TileUnit] = None
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
        self._scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        layout.addWidget(self._scroll_area)
        
        # Container for tile grid
        self._tile_container = QWidget()
        self._tile_layout = QGridLayout(self._tile_container)
        self._tile_layout.setSpacing(1)
        self._tile_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self._scroll_area.setWidget(self._tile_container)
        
        # Placeholder when no tiles loaded
        self._placeholder = QLabel("Open images or folders to display tile palette")
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._placeholder.setStyleSheet("color: #888; padding: 20px;")
        self._tile_layout.addWidget(self._placeholder, 0, 0)
    
    def set_units(self, units: List[TileUnit], progress_callback: Optional[Callable[[int, int], bool]] = None):
        """Set the units to display in the palette (replaces existing).
        
        Args:
            units: List of TileUnit objects to display
            progress_callback: Optional callback(current, total) that returns True if cancelled
        """
        self._units = units
        self._selected_unit = None
        self._rebuild_grid(progress_callback)
    
    def prepend_units(self, units: List[TileUnit], progress_callback: Optional[Callable[[int, int], bool]] = None):
        """Add units to the top of the palette (keeps existing, skips duplicates).
        
        Units from source images already in the palette are not added again.
        """
        # Get set of source paths already in palette
        existing_sources = {u.source_path for u in self._units}
        
        # Filter out units from sources that are already loaded
        new_units = [u for u in units if u.source_path not in existing_sources]
        
        if new_units:
            self._units = new_units + self._units
            self._selected_unit = None
            self._rebuild_grid(progress_callback)
    
    # Legacy methods for backward compatibility
    def set_tiles(self, tiles: List[Tile], progress_callback: Optional[Callable[[int, int], bool]] = None):
        """Set tiles to display (legacy method - converts to units).
        
        Args:
            tiles: List of Tile objects to display
            progress_callback: Optional callback(current, total) that returns True if cancelled
        """
        # Group tiles into units if they don't have one
        units: List[TileUnit] = []
        seen_units: set = set()
        
        for tile in tiles:
            if tile.unit is not None:
                if id(tile.unit) not in seen_units:
                    units.append(tile.unit)
                    seen_units.add(id(tile.unit))
            else:
                # Create a 1×1 unit for orphan tiles
                unit = TileUnit(
                    grid_width=1,
                    grid_height=1,
                    tiles=[tile],
                    grid_x=tile.x // TILE_SIZE,
                    grid_y=tile.y // TILE_SIZE,
                )
                tile.unit = unit
                units.append(unit)
        
        self.set_units(units, progress_callback)
    
    def prepend_tiles(self, tiles: List[Tile], progress_callback: Optional[Callable[[int, int], bool]] = None):
        """Add tiles to the top of the palette (legacy method).
        
        Args:
            tiles: List of Tile objects to add
            progress_callback: Optional callback(current, total) that returns True if cancelled
        """
        # Group tiles into units
        units: List[TileUnit] = []
        seen_units: set = set()
        
        for tile in tiles:
            if tile.unit is not None:
                if id(tile.unit) not in seen_units:
                    units.append(tile.unit)
                    seen_units.add(id(tile.unit))
            else:
                unit = TileUnit(
                    grid_width=1,
                    grid_height=1,
                    tiles=[tile],
                    grid_x=tile.x // TILE_SIZE,
                    grid_y=tile.y // TILE_SIZE,
                )
                tile.unit = unit
                units.append(unit)
        
        self.prepend_units(units, progress_callback)
    
    @property
    def _tiles(self) -> List[Tile]:
        """Get all tiles from all units (legacy property)."""
        return [tile for unit in self._units for tile in unit.tiles]
    
    def clear(self):
        """Clear all units from the palette."""
        self._units = []
        self._selected_unit = None
        self._rebuild_grid()
    
    def _rebuild_grid(self, progress_callback: Optional[Callable[[int, int], bool]] = None):
        """Rebuild the tile grid display.
        
        Args:
            progress_callback: Optional callback(current, total) that returns True if cancelled
        """
        # Clear existing buttons
        for btn in self._tile_buttons:
            btn.deleteLater()
        self._tile_buttons.clear()
        
        # Clear layout
        while self._tile_layout.count():
            item = self._tile_layout.takeAt(0)
            if item.widget() and item.widget() != self._placeholder:
                item.widget().deleteLater()
        
        if not self._units:
            # Show placeholder
            self._placeholder.setParent(self._tile_container)
            self._tile_layout.addWidget(self._placeholder, 0, 0)
            self._header_label.setText("Tile Palette")
            return
        
        # Hide placeholder
        self._placeholder.setParent(None)
        
        # Count total tiles for progress
        total_tiles = sum(len(unit.tiles) for unit in self._units)
        tiles_processed = 0
        
        # Group units by source file
        units_by_source: Dict[str, List[TileUnit]] = {}
        for unit in self._units:
            source = unit.source_name
            if source not in units_by_source:
                units_by_source[source] = []
            units_by_source[source].append(unit)
        
        cancelled = False
        layout_row = 0
        for source_name, source_units in units_by_source.items():
            if cancelled:
                break
                
            # Add source file label
            source_label = QLabel(source_name)
            source_label.setStyleSheet(
                "font-weight: bold; color: #666; padding: 5px 0; "
                "border-bottom: 1px solid #ccc;"
            )
            self._tile_layout.addWidget(source_label, layout_row, 0, 1, 16)  # Span up to 16 columns
            layout_row += 1
            
            # Calculate grid bounds for this source
            max_col = 0
            max_row = 0
            for unit in source_units:
                for tile in unit.tiles:
                    tile_col = tile.x // TILE_SIZE
                    tile_row = tile.y // TILE_SIZE
                    if tile_col >= max_col:
                        max_col = tile_col + 1
                    if tile_row >= max_row:
                        max_row = tile_row + 1
            
            # Display tiles at their original positions (x, y based)
            for unit in source_units:
                if cancelled:
                    break
                for tile in unit.tiles:
                    display_col = tile.x // TILE_SIZE
                    display_row = tile.y // TILE_SIZE
                    
                    btn = TileButton(tile)
                    btn.clicked.connect(self._on_tile_clicked)
                    self._tile_buttons.append(btn)
                    self._tile_layout.addWidget(btn, layout_row + display_row, display_col)
                    
                    tiles_processed += 1
                    
                    # Report progress and process events periodically
                    if progress_callback and tiles_processed % 10 == 0:
                        if progress_callback(tiles_processed, total_tiles):
                            cancelled = True
                            break
                        QApplication.processEvents()
            
            layout_row += max_row
        
        # Final progress update
        if progress_callback and not cancelled:
            progress_callback(total_tiles, total_tiles)
        
        # Add stretch at bottom
        self._tile_layout.setRowStretch(layout_row, 1)
        
        # Update header with tile count
        self._header_label.setText(f"Tile Palette ({total_tiles} tiles, {len(self._units)} units)")
    
    def _on_tile_clicked(self, tile: Tile):
        """Handle tile button click - selects the entire unit."""
        unit = tile.unit
        if unit is None:
            return
        
        # Update selection state for all tile buttons
        for btn in self._tile_buttons:
            btn.selected = (btn.tile.unit is unit)
        
        self._selected_unit = unit
        self.unit_selected.emit(unit)
        
        # Also emit legacy signal with the clicked tile
        self.tile_selected.emit(tile)
    
    @property
    def selected_unit(self) -> Optional[TileUnit]:
        """Get the currently selected unit."""
        return self._selected_unit
    
    @property
    def selected_tile(self) -> Optional[Tile]:
        """Get a tile from the selected unit (legacy property)."""
        if self._selected_unit and self._selected_unit.tiles:
            return self._selected_unit.tiles[0]
        return None
    
    def set_columns(self, columns: int):
        """Set the number of columns in the tile grid."""
        if columns > 0 and columns != self._columns:
            self._columns = columns
            self._rebuild_grid()

