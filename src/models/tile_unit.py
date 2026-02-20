"""
TileUnit model representing a group of linked tiles forming a selectable unit.

For simple tiles (A5, B-E): unit contains a single tile.
For autotiles (A2-A4): unit contains multiple tiles that form the unit.
"""

from dataclasses import dataclass, field
from typing import List, Tuple, TYPE_CHECKING

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
    
    def get_tile_at(self, local_x: int, local_y: int) -> "Tile | None":
        """
        Get the tile at a local grid position within this unit.
        
        Args:
            local_x: Column within the unit (0 to grid_width-1)
            local_y: Row within the unit (0 to grid_height-1)
        
        Returns:
            The tile at that position, or None if out of bounds.
        """
        if 0 <= local_x < self.grid_width and 0 <= local_y < self.grid_height:
            index = local_y * self.grid_width + local_x
            if index < len(self.tiles):
                return self.tiles[index]
        return None
    
    def to_pixmap(self) -> "QPixmap":
        """
        Create a QPixmap showing the complete unit.
        
        Returns:
            QPixmap with all tiles composited at their relative positions.
        """
        from PySide6.QtGui import QPixmap, QPainter
        from PySide6.QtCore import Qt
        
        pixmap = QPixmap(self.pixel_width, self.pixel_height)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        if self.tiles:
            painter = QPainter(pixmap)
            min_x = min(t.x for t in self.tiles)
            min_y = min(t.y for t in self.tiles)
            
            for tile in self.tiles:
                rel_x = tile.x - min_x
                rel_y = tile.y - min_y
                painter.drawPixmap(rel_x, rel_y, tile.pixmap)
            
            painter.end()
        
        return pixmap
