"""
TileUnit model representing a group of linked tiles forming a selectable unit.

For simple tiles (A5, B-E): unit contains a single tile.
For autotiles (A2-A4): unit contains multiple tiles that form the unit.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Tuple, TYPE_CHECKING

from PySide6.QtGui import QPixmap, QPainter
from PySide6.QtCore import Qt, QPoint

if TYPE_CHECKING:
    from .tile import Tile


@dataclass
class TileUnit:
    """
    A selectable unit composed of one or more tiles.
    
    The unit represents a logical grouping of tiles that should be
    selected, moved, and placed together. All tiles in a unit share
    the same source file.
    """
    # Grid size of this unit (in tiles, e.g., (2, 2) for 96×96)
    grid_width: int
    grid_height: int
    
    # The tiles that make up this unit, in row-major order
    # For a 2×2 unit: [top-left, top-right, bottom-left, bottom-right]
    tiles: List["Tile"] = field(default_factory=list)
    
    # Position of the top-left tile within the source file's unit grid
    # (Not pixel position - this is unit index position for layout)
    grid_x: int = 0
    grid_y: int = 0
    
    @property
    def is_single_tile(self) -> bool:
        """Check if this unit is a single tile."""
        return self.grid_width == 1 and self.grid_height == 1
    
    @property
    def source_path(self) -> str:
        """Get the source path from the first tile."""
        return self.tiles[0].source_path if self.tiles else ""
    
    @property
    def source_name(self) -> str:
        """Get the source filename from the first tile."""
        return self.tiles[0].source_name if self.tiles else ""
    
    @property
    def pixel_width(self) -> int:
        """Total width of the unit in pixels."""
        from ..utils.constants import TILE_SIZE
        return self.grid_width * TILE_SIZE
    
    @property
    def pixel_height(self) -> int:
        """Total height of the unit in pixels."""
        from ..utils.constants import TILE_SIZE
        return self.grid_height * TILE_SIZE
    
    def get_tile_bounds(self) -> Tuple[int, int, int, int]:
        """
        Get the bounding box of all tiles in this unit.
        
        Returns:
            Tuple of (min_x, min_y, max_x, max_y) in pixels.
            Returns (0, 0, 0, 0) if unit has no tiles.
        """
        if not self.tiles:
            return (0, 0, 0, 0)
        
        min_x = min(t.x for t in self.tiles)
        min_y = min(t.y for t in self.tiles)
        max_x = max(t.x for t in self.tiles)
        max_y = max(t.y for t in self.tiles)
        return (min_x, min_y, max_x, max_y)
    
    def to_pixmap(self) -> QPixmap:
        """
        Create a QPixmap showing the complete unit.
        
        Returns:
            QPixmap with all tiles composited at their relative positions.
        """
        pixmap = QPixmap(self.pixel_width, self.pixel_height)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        if self.tiles:
            painter = QPainter(pixmap)
            min_x, min_y, _, _ = self.get_tile_bounds()
            
            for tile in self.tiles:
                rel_x = tile.x - min_x
                rel_y = tile.y - min_y
                painter.drawPixmap(rel_x, rel_y, tile.pixmap)
            
            painter.end()
        
        return pixmap


def create_composite_drag_pixmap(units: List[TileUnit], clicked_unit: TileUnit) -> Tuple[QPixmap, QPoint]:
    """Create a composite pixmap for dragging multiple units.
    
    Args:
        units: List of TileUnit objects to include in the composite.
        clicked_unit: The unit that was actually clicked (determines hotspot).
        
    Returns:
        Tuple of (composite_pixmap, hotspot_point).
    """
    from ..utils.constants import TILE_SIZE
    
    if not units:
        raise ValueError("Cannot create composite pixmap from empty unit list")
    
    if len(units) == 1:
        # Single unit - simple case
        return units[0].to_pixmap(), QPoint(TILE_SIZE // 2, TILE_SIZE // 2)
    
    # Multiple units - create composite pixmap
    # Find bounding box based on grid positions
    min_x = min(u.grid_x * TILE_SIZE for u in units)
    min_y = min(u.grid_y * TILE_SIZE for u in units)
    max_x = max(u.grid_x * TILE_SIZE for u in units)
    max_y = max(u.grid_y * TILE_SIZE for u in units)
    
    width = max_x - min_x + TILE_SIZE
    height = max_y - min_y + TILE_SIZE
    
    # Create composite pixmap
    pixmap = QPixmap(width, height)
    pixmap.fill(Qt.GlobalColor.transparent)
    
    painter = QPainter(pixmap)
    for unit in units:
        unit_pixmap = unit.to_pixmap()
        x = unit.grid_x * TILE_SIZE - min_x
        y = unit.grid_y * TILE_SIZE - min_y
        painter.drawPixmap(x, y, unit_pixmap)
    painter.end()
    
    # Calculate hotspot at clicked unit's position within the composite
    hotspot = QPoint(
        clicked_unit.grid_x * TILE_SIZE - min_x + TILE_SIZE // 2,
        clicked_unit.grid_y * TILE_SIZE - min_y + TILE_SIZE // 2
    )
    
    return pixmap, hotspot
