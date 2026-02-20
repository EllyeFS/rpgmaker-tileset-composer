"""Canvas widget for composing tilesets."""

from typing import Dict, Tuple, Optional

from PySide6.QtWidgets import QWidget, QScrollArea, QVBoxLayout, QApplication
from PySide6.QtCore import Qt, Signal, QPoint, QMimeData
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QPixmap, QDrag

from ..models.tileset_types import TilesetType, TILESET_TYPES, get_unit_positions
from ..models.tile_unit import TileUnit
from ..utils.constants import TILE_SIZE, TILE_UNIT_MIME_TYPE


def _get_drag_unit() -> Optional[TileUnit]:
    """Get the currently dragged unit from the palette module."""
    from .tile_palette import get_current_drag_unit
    return get_current_drag_unit()


def _set_drag_unit(unit: Optional[TileUnit]):
    """Set the currently dragged unit in the palette module."""
    from .tile_palette import set_current_drag_unit
    set_current_drag_unit(unit)


class TileCanvasWidget(QWidget):
    """
    The actual canvas surface where tiles are painted.
    
    This widget has a fixed size matching the tileset dimensions
    and draws the grid overlay. Accepts tile unit drops from the palette.
    """
    
    # Signal emitted when a grid cell is clicked: (grid_x, grid_y)
    cell_clicked = Signal(int, int)
    
    # Signal emitted when a unit is placed: (unit, grid_x, grid_y)
    unit_placed = Signal(TileUnit, int, int)
    
    # Checkerboard pattern for transparency indication
    CHECKER_LIGHT = QColor(255, 255, 255)
    CHECKER_DARK = QColor(204, 204, 204)
    CHECKER_SIZE = 8
    
    DEFAULT_GRID_COLOR = QColor("#646464")
    DEFAULT_UNIT_GRID_COLOR = QColor("#000000")
    
    DROP_HIGHLIGHT_COLOR = QColor(52, 152, 219, 100)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._tileset_type: TilesetType = TILESET_TYPES["A5"]
        self._checker_pattern: QPixmap = self._create_checker_pattern()
        
        # Grid colors (instance variables for customization)
        self._grid_color: QColor = QColor(self.DEFAULT_GRID_COLOR)
        self._unit_grid_color: QColor = QColor(self.DEFAULT_UNIT_GRID_COLOR)
        
        # Cached unit positions for current tileset type
        self._unit_positions: list = []
        self._update_unit_positions()
        
        # Placed units: maps (grid_x, grid_y) -> TileUnit
        # Only stores the top-left position of each placed unit
        self._placed_units: Dict[Tuple[int, int], TileUnit] = {}
        
        # Current drop hover position (for visual feedback)
        self._drop_hover_pos: Optional[Tuple[int, int]] = None
        self._drop_hover_unit: Optional[TileUnit] = None
        self._drop_hover_valid: bool = False
        
        # Drag tracking for moving placed units
        self._drag_start_pos: Optional[QPoint] = None
        self._dragging_from_canvas: bool = False
        
        # Enable drop acceptance
        self.setAcceptDrops(True)
        
        self._update_size()
        
    def _create_checker_pattern(self) -> QPixmap:
        """Create a checkerboard pattern pixmap for the background."""
        size = self.CHECKER_SIZE * 2
        pixmap = QPixmap(size, size)
        painter = QPainter(pixmap)
        
        # Light squares
        painter.fillRect(0, 0, self.CHECKER_SIZE, self.CHECKER_SIZE, self.CHECKER_LIGHT)
        painter.fillRect(self.CHECKER_SIZE, self.CHECKER_SIZE, self.CHECKER_SIZE, self.CHECKER_SIZE, self.CHECKER_LIGHT)
        
        # Dark squares
        painter.fillRect(self.CHECKER_SIZE, 0, self.CHECKER_SIZE, self.CHECKER_SIZE, self.CHECKER_DARK)
        painter.fillRect(0, self.CHECKER_SIZE, self.CHECKER_SIZE, self.CHECKER_SIZE, self.CHECKER_DARK)
        
        painter.end()
        return pixmap
    
    def set_tileset_type(self, tileset_type: TilesetType):
        """Set the tileset type and resize the canvas accordingly."""
        self._tileset_type = tileset_type
        self._placed_units.clear()  # Clear placed tiles when changing type
        self._update_unit_positions()
        self._update_size()
        self.update()
    
    def set_grid_color(self, color: QColor):
        """Set the color for the regular grid lines."""
        self._grid_color = QColor(color)
        self.update()
    
    def set_unit_grid_color(self, color: QColor):
        """Set the color for the unit boundary grid lines."""
        self._unit_grid_color = QColor(color)
        self.update()
    
    @property
    def grid_color(self) -> QColor:
        """Get the current grid color."""
        return self._grid_color
    
    @property
    def unit_grid_color(self) -> QColor:
        """Get the current unit boundary grid color."""
        return self._unit_grid_color
    
    def _update_unit_positions(self):
        """Update cached unit positions for current tileset type."""
        self._unit_positions = get_unit_positions(self._tileset_type)
    
    def _is_valid_drop_position(self, grid_x: int, grid_y: int, unit: TileUnit) -> bool:
        """
        Check if a unit can be dropped at the given grid position.
        
        The unit must align with an expected unit position and match the expected size.
        """
        px = grid_x * TILE_SIZE
        py = grid_y * TILE_SIZE
        pw = unit.grid_width * TILE_SIZE
        ph = unit.grid_height * TILE_SIZE
        
        # Check if this matches any expected unit position
        for (ux, uy, uw, uh) in self._unit_positions:
            if px == ux and py == uy and pw == uw and ph == uh:
                return True
        return False
    
    def _snap_to_valid_position(self, grid_x: int, grid_y: int, unit: TileUnit) -> Optional[Tuple[int, int]]:
        """
        Find the nearest valid drop position for the unit, if any.
        
        Returns (grid_x, grid_y) of a valid position, or None if no valid position.
        """
        pw = unit.grid_width * TILE_SIZE
        ph = unit.grid_height * TILE_SIZE
        
        # Find unit positions that match the unit's size
        matching_positions = [
            (ux // TILE_SIZE, uy // TILE_SIZE)
            for (ux, uy, uw, uh) in self._unit_positions
            if uw == pw and uh == ph
        ]
        
        if not matching_positions:
            return None
        
        # Find the closest matching position
        def distance(pos):
            return abs(pos[0] - grid_x) + abs(pos[1] - grid_y)
        
        return min(matching_positions, key=distance)
    
    def _update_size(self):
        """Update the widget size based on the tileset type."""
        width = self._tileset_type.width
        height = self._tileset_type.height
        self.setFixedSize(width, height)
    
    @property
    def grid_width(self) -> int:
        """Number of columns in the grid."""
        return self._tileset_type.width // TILE_SIZE
    
    @property
    def grid_height(self) -> int:
        """Number of rows in the grid."""
        return self._tileset_type.height // TILE_SIZE
    
    def paintEvent(self, event):
        """Draw the canvas with checkerboard background, placed tiles, and grid."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        
        rect = self.rect()
        
        # Draw checkerboard background
        painter.drawTiledPixmap(rect, self._checker_pattern)
        
        # Draw placed tiles
        for (grid_x, grid_y), unit in self._placed_units.items():
            self._draw_unit(painter, unit, grid_x, grid_y)
        
        # Draw drop hover preview (only if valid)
        if self._drop_hover_pos and self._drop_hover_unit and self._drop_hover_valid:
            gx, gy = self._drop_hover_pos
            # Draw semi-transparent preview
            painter.setOpacity(0.6)
            self._draw_unit(painter, self._drop_hover_unit, gx, gy)
            painter.setOpacity(1.0)
            
            # Draw highlight rectangle
            px = gx * TILE_SIZE
            py = gy * TILE_SIZE
            pw = self._drop_hover_unit.grid_width * TILE_SIZE
            ph = self._drop_hover_unit.grid_height * TILE_SIZE
            painter.fillRect(px, py, pw, ph, self.DROP_HIGHLIGHT_COLOR)
        
        # Draw grid lines
        pen = QPen(self._grid_color)
        pen.setWidth(1)
        painter.setPen(pen)
        
        # Vertical lines
        for x in range(0, rect.width() + 1, TILE_SIZE):
            painter.drawLine(x, 0, x, rect.height())
        
        # Horizontal lines
        for y in range(0, rect.height() + 1, TILE_SIZE):
            painter.drawLine(0, y, rect.width(), y)
        
        # Draw stronger unit boundary lines
        unit_pen = QPen(self._unit_grid_color)
        unit_pen.setWidth(2)
        painter.setPen(unit_pen)
        
        # Collect unique x and y boundaries from unit positions
        x_boundaries = set([0, rect.width()])
        y_boundaries = set([0, rect.height()])
        for (ux, uy, uw, uh) in self._unit_positions:
            x_boundaries.add(ux)
            x_boundaries.add(ux + uw)
            y_boundaries.add(uy)
            y_boundaries.add(uy + uh)
        
        # Draw vertical unit boundary lines
        for x in sorted(x_boundaries):
            if 0 <= x <= rect.width():
                painter.drawLine(x, 0, x, rect.height())
        
        # Draw horizontal unit boundary lines
        for y in sorted(y_boundaries):
            if 0 <= y <= rect.height():
                painter.drawLine(0, y, rect.width(), y)
        
        painter.end()
    
    def _draw_unit(self, painter: QPainter, unit: TileUnit, grid_x: int, grid_y: int):
        """Draw a tile unit at the specified grid position."""
        if not unit.tiles:
            return
        
        # Find min position in source for relative offsets
        min_x = min(t.x for t in unit.tiles)
        min_y = min(t.y for t in unit.tiles)
        
        # Draw each tile
        for tile in unit.tiles:
            rel_x = (tile.x - min_x) // TILE_SIZE
            rel_y = (tile.y - min_y) // TILE_SIZE
            px = (grid_x + rel_x) * TILE_SIZE
            py = (grid_y + rel_y) * TILE_SIZE
            painter.drawPixmap(px, py, tile.pixmap)
    
    def mousePressEvent(self, event):
        """Handle mouse click to select a grid cell or start drag."""
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position().toPoint()
            grid_x = pos.x() // TILE_SIZE
            grid_y = pos.y() // TILE_SIZE
            
            # Ensure within bounds
            if 0 <= grid_x < self.grid_width and 0 <= grid_y < self.grid_height:
                # Check if there's a unit at this position
                unit_info = self._find_unit_at_cell(grid_x, grid_y)
                if unit_info:
                    # Start tracking for potential drag
                    self._drag_start_pos = pos
                else:
                    self._drag_start_pos = None
                    self.cell_clicked.emit(grid_x, grid_y)
    
    def mouseMoveEvent(self, event):
        """Handle mouse move to start dragging placed units."""
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return
        if self._drag_start_pos is None:
            return
        
        # Check if we've moved far enough to start a drag
        distance = (event.position().toPoint() - self._drag_start_pos).manhattanLength()
        if distance < QApplication.startDragDistance():
            return
        
        # Find the unit at the drag start position
        start_grid_x = self._drag_start_pos.x() // TILE_SIZE
        start_grid_y = self._drag_start_pos.y() // TILE_SIZE
        unit_info = self._find_unit_at_cell(start_grid_x, start_grid_y)
        
        if not unit_info:
            self._drag_start_pos = None
            return
        
        unit_pos, unit = unit_info
        
        # Remove the unit from canvas before starting drag
        del self._placed_units[unit_pos]
        self.update()
        
        # Create drag pixmap
        drag_pixmap = unit.to_pixmap()
        
        # Create drag object
        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setData(TILE_UNIT_MIME_TYPE, b"")
        drag.setMimeData(mime_data)
        drag.setPixmap(drag_pixmap)
        drag.setHotSpot(QPoint(TILE_SIZE // 2, TILE_SIZE // 2))
        
        # Store unit in module-level variable
        self._dragging_from_canvas = True
        _set_drag_unit(unit)
        
        # Execute drag
        result = drag.exec(Qt.DropAction.MoveAction | Qt.DropAction.CopyAction)
        
        # If drag was not accepted (dropped outside), unit is discarded
        # If dropped on canvas, dropEvent will have placed it
        _set_drag_unit(None)
        self._dragging_from_canvas = False
        self._drag_start_pos = None
    
    def _find_unit_at_cell(self, grid_x: int, grid_y: int) -> Optional[Tuple[Tuple[int, int], TileUnit]]:
        """Find the unit (if any) that covers the given grid cell.
        
        Returns:
            Tuple of ((unit_x, unit_y), unit) or None if no unit at cell.
        """
        for (ux, uy), unit in self._placed_units.items():
            if (ux <= grid_x < ux + unit.grid_width and
                uy <= grid_y < uy + unit.grid_height):
                return ((ux, uy), unit)
        return None
    
    def dragEnterEvent(self, event):
        """Accept drag if it contains a tile unit."""
        if event.mimeData().hasFormat(TILE_UNIT_MIME_TYPE):
            event.acceptProposedAction()
            # Get unit from module-level storage
            unit = _get_drag_unit()
            if unit:
                self._drop_hover_unit = unit
    
    def dragMoveEvent(self, event):
        """Update hover position as drag moves."""
        if event.mimeData().hasFormat(TILE_UNIT_MIME_TYPE):
            pos = event.position().toPoint()
            grid_x = pos.x() // TILE_SIZE
            grid_y = pos.y() // TILE_SIZE
            
            if self._drop_hover_unit:
                # Try to snap to a valid position for this unit
                valid_pos = self._snap_to_valid_position(grid_x, grid_y, self._drop_hover_unit)
                if valid_pos:
                    grid_x, grid_y = valid_pos
                    self._drop_hover_valid = True
                else:
                    # No valid position for this unit size
                    self._drop_hover_valid = False
            else:
                self._drop_hover_valid = False
            
            new_pos = (grid_x, grid_y)
            if new_pos != self._drop_hover_pos or not self._drop_hover_valid:
                self._drop_hover_pos = new_pos
                self.update()
            
            event.acceptProposedAction()
    
    def dragLeaveEvent(self, event):
        """Clear hover when drag leaves."""
        self._drop_hover_pos = None
        self._drop_hover_unit = None
        self._drop_hover_valid = False
        self.update()
    
    def dropEvent(self, event):
        """Handle drop of a tile unit."""
        if not event.mimeData().hasFormat(TILE_UNIT_MIME_TYPE):
            return
        
        unit = _get_drag_unit()
        if not unit:
            return
        
        # Calculate grid position
        pos = event.position().toPoint()
        grid_x = pos.x() // TILE_SIZE
        grid_y = pos.y() // TILE_SIZE
        
        # Snap to valid position
        valid_pos = self._snap_to_valid_position(grid_x, grid_y, unit)
        if not valid_pos:
            # Invalid drop - unit size doesn't match any position
            self._drop_hover_pos = None
            self._drop_hover_unit = None
            self._drop_hover_valid = False
            self.update()
            return
        
        grid_x, grid_y = valid_pos
        
        # Place the unit
        self.place_unit(unit, grid_x, grid_y)
        
        # Clear hover state
        self._drop_hover_pos = None
        self._drop_hover_unit = None
        self._drop_hover_valid = False
        
        event.acceptProposedAction()
    
    def place_unit(self, unit: TileUnit, grid_x: int, grid_y: int):
        """Place a tile unit at the specified grid position."""
        # Remove any existing tiles that would be overwritten
        for dy in range(unit.grid_height):
            for dx in range(unit.grid_width):
                key = (grid_x + dx, grid_y + dy)
                # Find and remove any unit that occupies this cell
                self._remove_unit_at_cell(key)
        
        # Store the unit at its top-left position
        self._placed_units[(grid_x, grid_y)] = unit
        
        # Emit signal
        self.unit_placed.emit(unit, grid_x, grid_y)
        
        self.update()
    
    def _remove_unit_at_cell(self, cell: Tuple[int, int]):
        """Remove any unit that occupies the given cell."""
        to_remove = []
        for (ux, uy), unit in self._placed_units.items():
            # Check if this unit covers the cell
            if (ux <= cell[0] < ux + unit.grid_width and
                uy <= cell[1] < uy + unit.grid_height):
                to_remove.append((ux, uy))
        
        for key in to_remove:
            del self._placed_units[key]
    
    def clear(self):
        """Remove all placed units from the canvas."""
        self._placed_units.clear()
        self.update()
    
    def render_to_image(self) -> QPixmap:
        """
        Render the canvas content to a QPixmap.
        
        Creates a transparent image with all placed tiles drawn.
        This is used for PNG export.
        
        Returns:
            QPixmap with the rendered tileset (transparent background).
        """
        width = self._tileset_type.width
        height = self._tileset_type.height
        
        pixmap = QPixmap(width, height)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        
        # Draw all placed units
        for (grid_x, grid_y), unit in self._placed_units.items():
            self._draw_unit(painter, unit, grid_x, grid_y)
        
        painter.end()
        return pixmap
    
    def is_empty(self) -> bool:
        """Check if the canvas has no placed units."""
        return len(self._placed_units) == 0
    
    @property
    def placed_unit_count(self) -> int:
        """Get the number of placed units."""
        return len(self._placed_units)
    
    def get_placed_units(self) -> Dict[Tuple[int, int], TileUnit]:
        """Get a copy of the placed units dictionary."""
        return dict(self._placed_units)
    
    def set_placed_units(self, placed_units: Dict[Tuple[int, int], TileUnit]):
        """Set the placed units dictionary."""
        self._placed_units = dict(placed_units)
        self.update()


class TileCanvas(QScrollArea):
    """
    Scrollable container for the tile canvas.
    
    This widget handles scrolling and contains the actual canvas surface.
    """
    
    # Forward signals from inner canvas
    cell_clicked = Signal(int, int)
    unit_placed = Signal(TileUnit, int, int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Create the canvas widget
        self._canvas = TileCanvasWidget()
        self._canvas.cell_clicked.connect(self.cell_clicked)
        self._canvas.unit_placed.connect(self.unit_placed)
        
        # Configure scroll area
        self.setWidget(self._canvas)
        self.setWidgetResizable(False)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Style the scroll area
        self.setStyleSheet("""
            QScrollArea {
                background-color: #2d2d2d;
                border: 1px solid #555;
            }
        """)
    
    def set_tileset_type(self, tileset_type: TilesetType):
        """Set the tileset type for the canvas."""
        self._canvas.set_tileset_type(tileset_type)
    
    def set_tileset_type_by_name(self, type_name: str):
        """Set the tileset type by name (e.g., 'A5', 'B')."""
        if type_name in TILESET_TYPES:
            self.set_tileset_type(TILESET_TYPES[type_name])
    
    @property
    def canvas(self) -> TileCanvasWidget:
        """Access the underlying canvas widget."""
        return self._canvas
    
    @property
    def tileset_type(self) -> TilesetType:
        """Get the current tileset type."""
        return self._canvas._tileset_type
    
    def render_to_image(self) -> QPixmap:
        """Render the canvas to a QPixmap for export."""
        return self._canvas.render_to_image()
    
    def is_empty(self) -> bool:
        """Check if the canvas has no placed units."""
        return self._canvas.is_empty()
    
    def clear(self):
        """Clear all placed units from the canvas."""
        self._canvas.clear()
    
    def get_placed_units(self) -> Dict[Tuple[int, int], TileUnit]:
        """Get a copy of the placed units dictionary."""
        return self._canvas.get_placed_units()
    
    def set_placed_units(self, placed_units: Dict[Tuple[int, int], TileUnit]):
        """Set the placed units dictionary."""
        self._canvas.set_placed_units(placed_units)
    
    def set_grid_color(self, color: QColor):
        """Set the color for the regular grid lines."""
        self._canvas.set_grid_color(color)
    
    def set_unit_grid_color(self, color: QColor):
        """Set the color for the unit boundary grid lines."""
        self._canvas.set_unit_grid_color(color)
    
    @property
    def grid_color(self) -> QColor:
        """Get the current grid color."""
        return self._canvas.grid_color
    
    @property
    def unit_grid_color(self) -> QColor:
        """Get the current unit boundary grid color."""
        return self._canvas.unit_grid_color
