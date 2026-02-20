"""Canvas widget for composing tilesets."""

from typing import Dict, Tuple, Optional

from PySide6.QtWidgets import QWidget, QScrollArea, QVBoxLayout
from PySide6.QtCore import Qt, Signal, QPoint
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QPixmap, QDrag

from ..models.tileset_types import TilesetType, TILESET_TYPES
from ..models.tile_unit import TileUnit
from ..utils.constants import TILE_SIZE


# Custom MIME type for tile unit drag operations (must match palette)
TILE_UNIT_MIME_TYPE = "application/x-rpgmaker-tileunit"


def _get_drag_unit() -> Optional[TileUnit]:
    """Get the currently dragged unit from the palette module."""
    from .tile_palette import get_current_drag_unit
    return get_current_drag_unit()


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
    
    # Checkerboard colors for transparency indication
    CHECKER_LIGHT = QColor(255, 255, 255)
    CHECKER_DARK = QColor(204, 204, 204)
    CHECKER_SIZE = 8  # Size of each checker square
    
    # Grid line color
    GRID_COLOR = QColor(100, 100, 100, 128)
    
    # Drop hover highlight color
    DROP_HIGHLIGHT_COLOR = QColor(52, 152, 219, 100)  # Semi-transparent blue
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._tileset_type: TilesetType = TILESET_TYPES["A5"]
        self._checker_pattern: QPixmap = self._create_checker_pattern()
        
        # Placed units: maps (grid_x, grid_y) -> TileUnit
        # Only stores the top-left position of each placed unit
        self._placed_units: Dict[Tuple[int, int], TileUnit] = {}
        
        # Current drop hover position (for visual feedback)
        self._drop_hover_pos: Optional[Tuple[int, int]] = None
        self._drop_hover_unit: Optional[TileUnit] = None
        
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
        self._update_size()
        self.update()
    
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
        
        # Draw drop hover preview
        if self._drop_hover_pos and self._drop_hover_unit:
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
        pen = QPen(self.GRID_COLOR)
        pen.setWidth(1)
        painter.setPen(pen)
        
        # Vertical lines
        for x in range(0, rect.width() + 1, TILE_SIZE):
            painter.drawLine(x, 0, x, rect.height())
        
        # Horizontal lines
        for y in range(0, rect.height() + 1, TILE_SIZE):
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
        """Handle mouse click to select a grid cell."""
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position().toPoint()
            grid_x = pos.x() // TILE_SIZE
            grid_y = pos.y() // TILE_SIZE
            
            # Ensure within bounds
            if 0 <= grid_x < self.grid_width and 0 <= grid_y < self.grid_height:
                self.cell_clicked.emit(grid_x, grid_y)
    
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
            
            # Clamp to canvas bounds considering unit size
            if self._drop_hover_unit:
                max_x = self.grid_width - self._drop_hover_unit.grid_width
                max_y = self.grid_height - self._drop_hover_unit.grid_height
                grid_x = max(0, min(grid_x, max_x))
                grid_y = max(0, min(grid_y, max_y))
            
            new_pos = (grid_x, grid_y)
            if new_pos != self._drop_hover_pos:
                self._drop_hover_pos = new_pos
                self.update()
            
            event.acceptProposedAction()
    
    def dragLeaveEvent(self, event):
        """Clear hover when drag leaves."""
        self._drop_hover_pos = None
        self._drop_hover_unit = None
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
        
        # Clamp to canvas bounds considering unit size
        max_x = self.grid_width - unit.grid_width
        max_y = self.grid_height - unit.grid_height
        grid_x = max(0, min(grid_x, max_x))
        grid_y = max(0, min(grid_y, max_y))
        
        # Place the unit
        self.place_unit(unit, grid_x, grid_y)
        
        # Clear hover state
        self._drop_hover_pos = None
        self._drop_hover_unit = None
        
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
