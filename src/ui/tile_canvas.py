"""Canvas widget for composing tilesets."""

from PySide6.QtWidgets import QWidget, QScrollArea, QVBoxLayout
from PySide6.QtCore import Qt, Signal, QPoint
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QPixmap

from ..models.tileset_types import TilesetType, TILESET_TYPES
from ..utils.constants import TILE_SIZE


class TileCanvasWidget(QWidget):
    """
    The actual canvas surface where tiles are painted.
    
    This widget has a fixed size matching the tileset dimensions
    and draws the grid overlay.
    """
    
    # Signal emitted when a grid cell is clicked: (grid_x, grid_y)
    cell_clicked = Signal(int, int)
    
    # Checkerboard colors for transparency indication
    CHECKER_LIGHT = QColor(255, 255, 255)
    CHECKER_DARK = QColor(204, 204, 204)
    CHECKER_SIZE = 8  # Size of each checker square
    
    # Grid line color
    GRID_COLOR = QColor(100, 100, 100, 128)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._tileset_type: TilesetType = TILESET_TYPES["A5"]
        self._checker_pattern: QPixmap = self._create_checker_pattern()
        
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
        """Draw the canvas with checkerboard background and grid."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        
        rect = self.rect()
        
        # Draw checkerboard background
        painter.drawTiledPixmap(rect, self._checker_pattern)
        
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
    
    def mousePressEvent(self, event):
        """Handle mouse click to select a grid cell."""
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position().toPoint()
            grid_x = pos.x() // TILE_SIZE
            grid_y = pos.y() // TILE_SIZE
            
            # Ensure within bounds
            if 0 <= grid_x < self.grid_width and 0 <= grid_y < self.grid_height:
                self.cell_clicked.emit(grid_x, grid_y)


class TileCanvas(QScrollArea):
    """
    Scrollable container for the tile canvas.
    
    This widget handles scrolling and contains the actual canvas surface.
    """
    
    # Forward the cell_clicked signal
    cell_clicked = Signal(int, int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Create the canvas widget
        self._canvas = TileCanvasWidget()
        self._canvas.cell_clicked.connect(self.cell_clicked)
        
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
