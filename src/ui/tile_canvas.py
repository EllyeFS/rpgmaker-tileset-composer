"""Canvas widget for composing tilesets."""

from typing import Dict, Tuple, Optional, List

from PySide6.QtWidgets import QWidget, QScrollArea, QVBoxLayout, QApplication
from PySide6.QtCore import Qt, Signal, QPoint, QMimeData, QRect
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QPixmap, QDrag

from ..models.tileset_types import TilesetType, TILESET_TYPES, get_unit_positions
from ..models.tile_unit import TileUnit, create_composite_drag_pixmap
from ..utils.constants import TILE_SIZE, TILE_UNIT_MIME_TYPE
from .box_selection_mixin import BoxSelectionMixin


def _get_drag_units() -> List[TileUnit]:
    """Get the currently dragged units from the palette module."""
    from .tile_palette import get_current_drag_units
    return get_current_drag_units()


def _set_drag_units(units: List[TileUnit]):
    """Set the currently dragged units in the palette module."""
    from .tile_palette import set_current_drag_units
    set_current_drag_units(units)


class TileCanvasWidget(QWidget, BoxSelectionMixin):
    """
    The actual canvas surface where tiles are painted.
    
    This widget has a fixed size matching the tileset dimensions
    and draws the grid overlay. Accepts tile unit drops from the palette.
    """
    
    cell_clicked = Signal(int, int)
    unit_placed = Signal(TileUnit, int, int)
    
    CHECKER_LIGHT = QColor(255, 255, 255)
    CHECKER_DARK = QColor(204, 204, 204)
    CHECKER_SIZE = 8
    
    DEFAULT_GRID_COLOR = QColor("#646464")
    DEFAULT_UNIT_GRID_COLOR = QColor("#000000")
    
    DROP_HIGHLIGHT_COLOR = QColor(52, 152, 219, 100)
    SELECTION_BORDER_COLOR = QColor("#3498db")
    SELECTION_BORDER_WIDTH = 3
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._tileset_type: TilesetType = TILESET_TYPES["A5"]
        self._checker_pattern: QPixmap = self._create_checker_pattern()
        
        self._grid_color: QColor = QColor(self.DEFAULT_GRID_COLOR)
        self._unit_grid_color: QColor = QColor(self.DEFAULT_UNIT_GRID_COLOR)
        
        self._unit_positions: list = []
        self._update_unit_positions()
        
        self._placed_units: Dict[Tuple[int, int], TileUnit] = {}
        self._selected_positions: List[Tuple[int, int]] = []
        
        self.initialize_box_selection()
        
        self._drop_hover_pos: Optional[Tuple[int, int]] = None
        self._drop_hover_units: List[TileUnit] = []
        self._drop_hover_valid: bool = False
        
        self._drag_start_pos: Optional[QPoint] = None
        self._dragging_from_canvas: bool = False
        
        self.setAcceptDrops(True)
        
        self._update_size()
        
    def _create_checker_pattern(self) -> QPixmap:
        """Create a checkerboard pattern pixmap for the background."""
        size = self.CHECKER_SIZE * 2
        pixmap = QPixmap(size, size)
        painter = QPainter(pixmap)
        
        painter.fillRect(0, 0, self.CHECKER_SIZE, self.CHECKER_SIZE, self.CHECKER_LIGHT)
        painter.fillRect(self.CHECKER_SIZE, self.CHECKER_SIZE, self.CHECKER_SIZE, self.CHECKER_SIZE, self.CHECKER_LIGHT)
        
        painter.fillRect(self.CHECKER_SIZE, 0, self.CHECKER_SIZE, self.CHECKER_SIZE, self.CHECKER_DARK)
        painter.fillRect(0, self.CHECKER_SIZE, self.CHECKER_SIZE, self.CHECKER_SIZE, self.CHECKER_DARK)
        
        painter.end()
        return pixmap
    
    def set_tileset_type(self, tileset_type: TilesetType):
        """Set the tileset type and resize the canvas accordingly."""
        self._tileset_type = tileset_type
        self._placed_units.clear()
        self._selected_positions.clear()
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
        
        painter.drawTiledPixmap(rect, self._checker_pattern)
        
        for (grid_x, grid_y), unit in self._placed_units.items():
            self._draw_unit(painter, unit, grid_x, grid_y)
        
        if self._selected_positions:
            pen = QPen(self.SELECTION_BORDER_COLOR)
            pen.setWidth(self.SELECTION_BORDER_WIDTH)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            
            for pos in self._selected_positions:
                if pos in self._placed_units:
                    unit = self._placed_units[pos]
                    px = pos[0] * TILE_SIZE
                    py = pos[1] * TILE_SIZE
                    pw = unit.grid_width * TILE_SIZE
                    ph = unit.grid_height * TILE_SIZE
                    painter.drawRect(px + 1, py + 1, pw - 2, ph - 2)
        
        if self._drop_hover_pos and self._drop_hover_units and self._drop_hover_valid:
            base_gx, base_gy = self._drop_hover_pos
            
            first_unit = self._drop_hover_units[0]
            first_unit_grid_x = first_unit.grid_x
            first_unit_grid_y = first_unit.grid_y
            
            painter.setOpacity(0.6)
            for unit in self._drop_hover_units:
                offset_x = unit.grid_x - first_unit_grid_x
                offset_y = unit.grid_y - first_unit_grid_y
                
                target_x = base_gx + offset_x
                target_y = base_gy + offset_y
                
                if self._is_valid_drop_position(target_x, target_y, unit):
                    self._draw_unit(painter, unit, target_x, target_y)
            painter.setOpacity(1.0)
            
            for unit in self._drop_hover_units:
                offset_x = unit.grid_x - first_unit_grid_x
                offset_y = unit.grid_y - first_unit_grid_y
                target_x = base_gx + offset_x
                target_y = base_gy + offset_y
                
                if self._is_valid_drop_position(target_x, target_y, unit):
                    px = target_x * TILE_SIZE
                    py = target_y * TILE_SIZE
                    pw = unit.grid_width * TILE_SIZE
                    ph = unit.grid_height * TILE_SIZE
                    painter.fillRect(px, py, pw, ph, self.DROP_HIGHLIGHT_COLOR)
        
        self.handle_box_selection_paint(painter)
        
        pen = QPen(self._grid_color)
        pen.setWidth(1)
        painter.setPen(pen)
        
        for x in range(0, rect.width() + 1, TILE_SIZE):
            painter.drawLine(x, 0, x, rect.height())
        
        for y in range(0, rect.height() + 1, TILE_SIZE):
            painter.drawLine(0, y, rect.width(), y)
        
        unit_pen = QPen(self._unit_grid_color)
        unit_pen.setWidth(2)
        painter.setPen(unit_pen)
        
        x_boundaries = set([0, rect.width()])
        y_boundaries = set([0, rect.height()])
        for (ux, uy, uw, uh) in self._unit_positions:
            x_boundaries.add(ux)
            x_boundaries.add(ux + uw)
            y_boundaries.add(uy)
            y_boundaries.add(uy + uh)
        
        for x in sorted(x_boundaries):
            if 0 <= x <= rect.width():
                painter.drawLine(x, 0, x, rect.height())
        
        for y in sorted(y_boundaries):
            if 0 <= y <= rect.height():
                painter.drawLine(0, y, rect.width(), y)
        
        painter.end()
    
    def _draw_unit(self, painter: QPainter, unit: TileUnit, grid_x: int, grid_y: int):
        """Draw a tile unit at the specified grid position."""
        if not unit.tiles:
            return
        
        min_x, min_y, _, _ = unit.get_tile_bounds()
        
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
            
            if 0 <= grid_x < self.grid_width and 0 <= grid_y < self.grid_height:
                unit_info = self._find_unit_at_cell(grid_x, grid_y)
                modifiers = event.modifiers()
                
                if unit_info:
                    self._handle_unit_press(unit_info, pos, modifiers)
                else:
                    self._handle_empty_press(grid_x, grid_y, pos, modifiers)
    
    def _handle_unit_press(self, unit_info, pos: QPoint, modifiers):
        """Handle mouse press on a unit."""
        unit_pos, unit = unit_info
        
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            if unit_pos in self._selected_positions:
                self._selected_positions.remove(unit_pos)
            else:
                self._selected_positions.append(unit_pos)
            self.update()
            
            self._box_start = pos
            self._box_current = pos
            self._drag_start_pos = None
        else:
            if unit_pos not in self._selected_positions:
                self._selected_positions = [unit_pos]
                self.update()
            self._drag_start_pos = pos
    
    def _handle_empty_press(self, grid_x: int, grid_y: int, pos: QPoint, modifiers):
        """Handle mouse press on empty space."""
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            self._box_start = pos
            self._box_current = pos
            self._drag_start_pos = None
        else:
            if self._selected_positions:
                self._selected_positions.clear()
                self.update()
            self._drag_start_pos = None
            self.cell_clicked.emit(grid_x, grid_y)
    
    def mouseMoveEvent(self, event):
        """Handle mouse move to start dragging placed units or update box selection."""
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return
        
        pos = event.position().toPoint()
        
        if self._should_activate_box_selection(pos):
            self.update_box_selection(pos)
            self.update()
            return
        
        if self._should_start_drag(pos):
            self._start_unit_drag()
    
    def _should_activate_box_selection(self, pos: QPoint) -> bool:
        """Check if box selection should be activated."""
        if self.is_box_selecting():
            return True
        
        if self._box_start:
            distance = (pos - self._box_start).manhattanLength()
            if distance >= QApplication.startDragDistance():
                self.start_box_selection(self._box_start)
                return True
        
        return False
    
    def _should_start_drag(self, pos: QPoint) -> bool:
        """Check if drag should be started."""
        if self._drag_start_pos is None:
            return False
        
        distance = (pos - self._drag_start_pos).manhattanLength()
        return distance >= QApplication.startDragDistance()
    
    def _start_unit_drag(self):
        """Start dragging units from canvas."""
        start_grid_x = self._drag_start_pos.x() // TILE_SIZE
        start_grid_y = self._drag_start_pos.y() // TILE_SIZE
        unit_info = self._find_unit_at_cell(start_grid_x, start_grid_y)
        
        if not unit_info:
            self._drag_start_pos = None
            return
        
        clicked_pos, clicked_unit = unit_info
        
        drag_positions, drag_units = self._get_drag_units(clicked_pos, clicked_unit)
        
        for pos in drag_positions:
            if pos in self._placed_units:
                del self._placed_units[pos]
        self._selected_positions.clear()
        self.update()
        
        self._execute_drag(drag_units, clicked_unit)
    
    def _get_drag_units(self, clicked_pos, clicked_unit):
        """Get units and positions to drag."""
        if self._selected_positions and clicked_pos in self._selected_positions:
            drag_positions = self._selected_positions.copy()
            drag_units = [self._placed_units[pos] for pos in drag_positions]
        else:
            drag_positions = [clicked_pos]
            drag_units = [clicked_unit]
        return drag_positions, drag_units
    
    def _execute_drag(self, drag_units: List[TileUnit], primary_unit: TileUnit):
        """Execute drag operation."""
        drag_pixmap, hotspot = create_composite_drag_pixmap(drag_units, primary_unit)
        
        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setData(TILE_UNIT_MIME_TYPE, b"")
        drag.setMimeData(mime_data)
        drag.setPixmap(drag_pixmap)
        drag.setHotSpot(hotspot)
        
        self._dragging_from_canvas = True
        _set_drag_units(drag_units)
        
        drag.exec(Qt.DropAction.MoveAction | Qt.DropAction.CopyAction)
        
        _set_drag_units([])
        self._dragging_from_canvas = False
        self._drag_start_pos = None
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release to finish box selection."""
        if event.button() == Qt.MouseButton.LeftButton:
            if self.is_box_selecting():
                self.end_box_selection()
                self.update()
            elif self._box_start:
                self._box_start = None
                self._box_current = None
    
    def _on_box_selection_updated(self):
        """Called when box selection is updated."""
        self._update_box_selection_positions()
    
    def _update_box_selection_positions(self):
        """Update selected positions based on current box selection rectangle."""
        selection_rect = self.get_selection_rect()
        if not selection_rect:
            return
        
        selected_positions = []
        for (ux, uy), unit in self._placed_units.items():
            unit_x = ux * TILE_SIZE
            unit_y = uy * TILE_SIZE
            unit_w = unit.grid_width * TILE_SIZE
            unit_h = unit.grid_height * TILE_SIZE
            unit_rect = QRect(unit_x, unit_y, unit_w, unit_h)
            
            if selection_rect.intersects(unit_rect):
                selected_positions.append((ux, uy))
        
        self._selected_positions = selected_positions
    
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
        """Accept drag if it contains tile units."""
        if event.mimeData().hasFormat(TILE_UNIT_MIME_TYPE):
            event.acceptProposedAction()
            units = _get_drag_units()
            if units:
                self._drop_hover_units = units
    
    def dragMoveEvent(self, event):
        """Update hover position as drag moves."""
        if event.mimeData().hasFormat(TILE_UNIT_MIME_TYPE):
            pos = event.position().toPoint()
            grid_x = pos.x() // TILE_SIZE
            grid_y = pos.y() // TILE_SIZE
            
            if self._drop_hover_units:
                first_unit = self._drop_hover_units[0]
                valid_pos = self._snap_to_valid_position(grid_x, grid_y, first_unit)
                if valid_pos:
                    grid_x, grid_y = valid_pos
                    self._drop_hover_valid = True
                else:
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
        self._drop_hover_units = []
        self._drop_hover_valid = False
        self.update()
    
    def dropEvent(self, event):
        """Handle drop of tile units (supports multiple with relative positioning)."""
        if not event.mimeData().hasFormat(TILE_UNIT_MIME_TYPE):
            return
        
        units = _get_drag_units()
        if not units:
            return
        
        pos = event.position().toPoint()
        grid_x = pos.x() // TILE_SIZE
        grid_y = pos.y() // TILE_SIZE
        
        first_unit = units[0]
        valid_pos = self._snap_to_valid_position(grid_x, grid_y, first_unit)
        if not valid_pos:
            self._drop_hover_pos = None
            self._drop_hover_units = []
            self._drop_hover_valid = False
            self.update()
            return
        
        base_grid_x, base_grid_y = valid_pos
        
        first_unit_grid_x = first_unit.grid_x
        first_unit_grid_y = first_unit.grid_y
        
        for unit in units:
            offset_x = unit.grid_x - first_unit_grid_x
            offset_y = unit.grid_y - first_unit_grid_y
            
            target_x = base_grid_x + offset_x
            target_y = base_grid_y + offset_y
            
            if self._is_valid_drop_position(target_x, target_y, unit):
                self.place_unit(unit, target_x, target_y)
        
        self._drop_hover_pos = None
        self._drop_hover_units = []
        self._drop_hover_valid = False
        
        event.acceptProposedAction()
    
    def place_unit(self, unit: TileUnit, grid_x: int, grid_y: int):
        """Place a tile unit at the specified grid position."""
        for dy in range(unit.grid_height):
            for dx in range(unit.grid_width):
                key = (grid_x + dx, grid_y + dy)
                self._remove_unit_at_cell(key)
        
        self._placed_units[(grid_x, grid_y)] = unit
        
        self.unit_placed.emit(unit, grid_x, grid_y)
        
        self.update()
    
    def _remove_unit_at_cell(self, cell: Tuple[int, int]):
        """Remove any unit that occupies the given cell."""
        to_remove = []
        for (ux, uy), unit in self._placed_units.items():
            if (ux <= cell[0] < ux + unit.grid_width and
                uy <= cell[1] < uy + unit.grid_height):
                to_remove.append((ux, uy))
        
        for key in to_remove:
            del self._placed_units[key]
    
    def clear(self):
        """Remove all placed units from the canvas."""
        self._placed_units.clear()
        self._selected_positions.clear()
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
