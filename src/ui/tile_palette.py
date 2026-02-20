"""
Tile palette widget for displaying and selecting source tiles.

Tiles are displayed on a grid where each cell is TILE_SIZE × TILE_SIZE.
Larger units (autotiles) span multiple cells and select as a group.
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
from ..utils.constants import TILE_SIZE, PROGRESS_REPORT_INTERVAL, TILE_UNIT_MIME_TYPE


# Module-level storage for currently dragged units (Qt drag doesn't preserve Python objects)
_current_drag_units: List[TileUnit] = []


def get_current_drag_units() -> List[TileUnit]:
    """Get the currently dragged tile units."""
    return _current_drag_units


def set_current_drag_units(units: List[TileUnit]):
    """Set the currently dragged tile units."""
    global _current_drag_units
    _current_drag_units = units if units else []


def tiles_to_units(tiles: List[Tile]) -> List[TileUnit]:
    """
    Convert a list of tiles to a list of unique units.
    
    Tiles that already belong to a unit are grouped by that unit.
    Orphan tiles (no unit) get a new 1x1 unit created for them.
    
    Args:
        tiles: List of Tile objects.
        
    Returns:
        List of unique TileUnit objects.
    """
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
    
    return units

class TileButton(QFrame):
    """
    A clickable tile display widget.
    
    Shows a single tile and emits a signal when clicked.
    The signal includes the tile's parent unit for group selection.
    Supports drag operations to move units to the canvas.
    
    Edge flags indicate which borders are on the unit boundary (strong borders).
    """
    
    clicked = Signal(Tile, object)  # Tile and Qt.KeyboardModifiers
    
    DEFAULT_UNIT_BORDER = QColor("#000000")
    DEFAULT_GRID_BORDER = QColor("#646464")
    SELECTED_BORDER = QColor("#3498db")
    
    STRONG_BORDER_WIDTH = 2
    LIGHT_BORDER_WIDTH = 1
    
    def __init__(self, tile: Tile, edge_top: bool = True, edge_bottom: bool = True,
                 edge_left: bool = True, edge_right: bool = True,
                 unit_border_color: Optional[QColor] = None,
                 grid_border_color: Optional[QColor] = None,
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.tile = tile
        self._selected = False
        self._drag_start_pos: Optional[QPoint] = None
        
        # Which edges are unit boundaries (get strong borders)
        self._edge_top = edge_top
        self._edge_bottom = edge_bottom
        self._edge_left = edge_left
        self._edge_right = edge_right
        
        # Border colors (use defaults if not specified)
        self._unit_border_color = unit_border_color if unit_border_color else QColor(self.DEFAULT_UNIT_BORDER)
        self._grid_border_color = grid_border_color if grid_border_color else QColor(self.DEFAULT_GRID_BORDER)
        
        # All tiles are 48×48, plus border
        self.setFixedSize(TILE_SIZE + 2, TILE_SIZE + 2)
        
        # Styling - no frame, we'll draw borders manually
        self.setFrameStyle(QFrame.Shape.NoFrame)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
    
    @property
    def selected(self) -> bool:
        return self._selected
    
    @selected.setter
    def selected(self, value: bool):
        self._selected = value
        self.update()
    
    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        
        # Draw the tile pixmap centered (accounting for border)
        x = (self.width() - TILE_SIZE) // 2
        y = (self.height() - TILE_SIZE) // 2
        painter.drawPixmap(x, y, self.tile.pixmap)
        
        w = self.width()
        h = self.height()
        
        if self._selected:
            # Draw selection border
            painter.setPen(QPen(self.SELECTED_BORDER, 2))
            painter.drawRect(0, 0, w - 1, h - 1)
        else:
            # Draw borders with different thickness based on edge type
            borders = [
                (self._edge_top, 0, 0, w - 1, 0),        # Top: (x1, y1, x2, y2)
                (self._edge_bottom, 0, h - 1, w - 1, h - 1),  # Bottom
                (self._edge_left, 0, 0, 0, h - 1),        # Left
                (self._edge_right, w - 1, 0, w - 1, h - 1),  # Right
            ]
            
            for is_edge, x1, y1, x2, y2 in borders:
                color = self._unit_border_color if is_edge else self._grid_border_color
                width = self.STRONG_BORDER_WIDTH if is_edge else self.LIGHT_BORDER_WIDTH
                painter.setPen(QPen(color, width))
                painter.drawLine(x1, y1, x2, y2)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = event.position().toPoint()
            self.clicked.emit(self.tile, event.modifiers())
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return
        if self._drag_start_pos is None:
            return
        
        # Don't start drag if modifier keys are held (used for multiselect)
        if event.modifiers() & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier):
            return
        
        # Check if we've moved far enough to start a drag
        distance = (event.position().toPoint() - self._drag_start_pos).manhattanLength()
        if distance < QApplication.startDragDistance():
            return
        
        # Get the unit to drag
        unit = self.tile.unit
        if unit is None:
            return
        
        # Get palette to access selected units
        palette = self.parent()
        while palette and not isinstance(palette, TilePalette):
            palette = palette.parent()
        
        if palette:
            # Get draggable units (filtered to 1×1, same source)
            draggable_units = palette.get_draggable_units(unit)
        else:
            # Fallback if palette not found
            draggable_units = [unit]
        
        # Create composite drag pixmap
        if len(draggable_units) == 1:
            # Single unit - use existing behavior
            drag_pixmap = draggable_units[0].to_pixmap()
            hotspot = QPoint(TILE_SIZE // 2, TILE_SIZE // 2)
        else:
            # Multiple units - create composite pixmap
            # Find bounding box
            min_x = min(u.grid_x * TILE_SIZE for u in draggable_units)
            min_y = min(u.grid_y * TILE_SIZE for u in draggable_units)
            max_x = max(u.grid_x * TILE_SIZE for u in draggable_units)
            max_y = max(u.grid_y * TILE_SIZE for u in draggable_units)
            
            width = max_x - min_x + TILE_SIZE
            height = max_y - min_y + TILE_SIZE
            
            # Create composite pixmap
            drag_pixmap = QPixmap(width, height)
            drag_pixmap.fill(Qt.GlobalColor.transparent)
            
            painter = QPainter(drag_pixmap)
            for u in draggable_units:
                u_pixmap = u.to_pixmap()
                x = u.grid_x * TILE_SIZE - min_x
                y = u.grid_y * TILE_SIZE - min_y
                painter.drawPixmap(x, y, u_pixmap)
            painter.end()
            
            # Hotspot at the clicked unit's position within the composite
            hotspot = QPoint(
                unit.grid_x * TILE_SIZE - min_x + TILE_SIZE // 2,
                unit.grid_y * TILE_SIZE - min_y + TILE_SIZE // 2
            )
        
        # Create drag object
        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setData(TILE_UNIT_MIME_TYPE, b"")  # Marker data
        drag.setMimeData(mime_data)
        drag.setPixmap(drag_pixmap)
        drag.setHotSpot(hotspot)
        
        # Store units in module-level variable (Qt drag doesn't preserve Python objects)
        set_current_drag_units(draggable_units)
        
        # Execute drag
        drag.exec(Qt.DropAction.CopyAction)
        
        # Clear drag units reference
        set_current_drag_units([])
        self._drag_start_pos = None



class TilePalette(QWidget):
    """
    A scrollable palette displaying tiles from source images.
    
    Tiles are displayed in a grid preserving their source layout.
    Clicking a tile selects its entire unit (for multi-tile autotiles).
    """
    
    # Emits the selected unit when a tile is clicked
    unit_selected = Signal(TileUnit)
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        self._units: List[TileUnit] = []
        self._tile_buttons: List[TileButton] = []
        self._selected_units: List[TileUnit] = []  # Multiple selection support
        self._last_clicked_unit: Optional[TileUnit] = None  # For future shift-select
        
        # Grid colors for tile buttons
        self._unit_border_color: QColor = QColor(TileButton.DEFAULT_UNIT_BORDER)
        self._grid_border_color: QColor = QColor(TileButton.DEFAULT_GRID_BORDER)
        
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
        self._tile_layout.setSpacing(0)
        self._tile_layout.setContentsMargins(0, 0, 0, 0)
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
        self._selected_units = []
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
            self._selected_units = []
            self._rebuild_grid(progress_callback)
    
    def clear(self):
        """Clear all units from the palette."""
        self._units = []
        self._selected_units = []
        self._rebuild_grid()
    
    def set_unit_border_color(self, color: QColor):
        """Set the color for unit boundary borders (thicker lines)."""
        self._unit_border_color = QColor(color)
        self._rebuild_grid()
    
    def set_grid_border_color(self, color: QColor):
        """Set the color for internal grid borders (thinner lines)."""
        self._grid_border_color = QColor(color)
        self._rebuild_grid()
    
    @property
    def unit_border_color(self) -> QColor:
        """Get the current unit boundary border color."""
        return self._unit_border_color
    
    @property
    def grid_border_color(self) -> QColor:
        """Get the current internal grid border color."""
        return self._grid_border_color
    
    def _rebuild_grid(self, progress_callback: Optional[Callable[[int, int], bool]] = None):
        """Rebuild the tile grid display.
        
        Args:
            progress_callback: Optional callback(current, total) that returns True if cancelled
        """
        # Disable visual updates during rebuild to prevent UI "shaking"
        self.setUpdatesEnabled(False)
        
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
            self.setUpdatesEnabled(True)
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
                
                # Calculate unit bounds for edge detection
                unit_min_x, unit_min_y, unit_max_x, unit_max_y = unit.get_tile_bounds()
                
                for tile in unit.tiles:
                    display_col = tile.x // TILE_SIZE
                    display_row = tile.y // TILE_SIZE
                    
                    # Determine which edges are unit boundaries
                    edge_top = tile.y == unit_min_y
                    edge_bottom = tile.y == unit_max_y
                    edge_left = tile.x == unit_min_x
                    edge_right = tile.x == unit_max_x
                    
                    btn = TileButton(tile, edge_top, edge_bottom, edge_left, edge_right,
                                     self._unit_border_color, self._grid_border_color)
                    btn.clicked.connect(self._on_tile_clicked)
                    self._tile_buttons.append(btn)
                    self._tile_layout.addWidget(btn, layout_row + display_row, display_col)
                    
                    tiles_processed += 1
                    
                    # Report progress and process events periodically
                    if progress_callback and tiles_processed % PROGRESS_REPORT_INTERVAL == 0:
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
        
        # Re-enable visual updates now that grid is fully built
        self.setUpdatesEnabled(True)
    
    def _on_tile_clicked(self, tile: Tile, modifiers):
        """Handle tile button click - selects the entire unit.
        
        Supports multiselect with Ctrl key (restricted to same source).
        Clicking an already-selected unit keeps the selection (for dragging).
        """
        unit = tile.unit
        if unit is None:
            return
        
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            # Ctrl+Click: toggle selection (restricted to same source)
            if self._selected_units:
                # Check if trying to select from different source
                first_source = self._selected_units[0].source_path
                if unit.source_path != first_source:
                    # Different source - ignore ctrl, replace selection
                    self._selected_units = [unit]
                elif unit in self._selected_units:
                    # Same source - toggle off
                    self._selected_units.remove(unit)
                else:
                    # Same source - add to selection
                    self._selected_units.append(unit)
            else:
                # First selection
                self._selected_units = [unit]
        else:
            # Normal click: if clicking an already-selected unit, keep selection (for dragging)
            # Otherwise, replace selection with just this unit
            if unit not in self._selected_units:
                self._selected_units = [unit]
            # else: keep current selection intact
        
        self._last_clicked_unit = unit
        self._update_selection_visuals()
        
        # Emit signal with first selected unit for compatibility
        if self._selected_units:
            self.unit_selected.emit(self._selected_units[0])
    
    def _update_selection_visuals(self):
        """Update visual selection state for all tile buttons."""
        for btn in self._tile_buttons:
            btn.selected = (btn.tile.unit in self._selected_units)
    
    def get_draggable_units(self, clicked_unit: TileUnit) -> List[TileUnit]:
        """Get units that can be dragged together (only 1×1 units).
        
        Args:
            clicked_unit: The unit that was actually clicked/dragged
            
        Returns:
            List of 1×1 units from the same source, or just the clicked unit if it's not 1×1
        """
        # If clicked unit is not 1×1, just drag it alone
        if clicked_unit.grid_width != 1 or clicked_unit.grid_height != 1:
            return [clicked_unit]
        
        # Filter selected units to only 1×1 from same source
        draggable = []
        for unit in self._selected_units:
            if (unit.grid_width == 1 and unit.grid_height == 1 and 
                unit.source_path == clicked_unit.source_path):
                draggable.append(unit)
        
        return draggable if draggable else [clicked_unit]
    
    @property
    def selected_unit(self) -> Optional[TileUnit]:
        """Get the first selected unit (for compatibility)."""
        return self._selected_units[0] if self._selected_units else None
    
    @property
    def selected_units(self) -> List[TileUnit]:
        """Get all currently selected units."""
        return self._selected_units

