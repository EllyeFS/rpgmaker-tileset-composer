"""
Tile model representing an extracted 48×48 tile from a source image.

All tiles are 48×48 pixels. Larger units (autotiles) are represented
as multiple Tiles grouped by a TileUnit.
"""

from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING

from PySide6.QtGui import QImage, QPixmap

from ..utils.constants import TILE_SIZE

if TYPE_CHECKING:
    from .tile_unit import TileUnit


@dataclass
class Tile:
    """
    Represents a single 48×48 pixel tile extracted from a source image.
    
    All tiles are exactly 48×48 pixels. For larger units (autotiles),
    multiple Tiles are grouped together by a TileUnit.
    """
    # Source information
    source_path: str          # Path to the source image file
    source_index: int         # Index within the source image (0-based)
    
    # Position in source image (pixels)
    x: int
    y: int
    
    # The actual image data (always 48×48)
    image: QImage
    
    # Reference to parent unit (None until grouped)
    unit: Optional["TileUnit"] = field(default=None, repr=False, compare=False)
    
    # Cached pixmap for display (created on demand)
    _pixmap: Optional[QPixmap] = field(default=None, repr=False, compare=False)
    
    @property
    def width(self) -> int:
        """Tile width is always TILE_SIZE (48)."""
        return TILE_SIZE
    
    @property
    def height(self) -> int:
        """Tile height is always TILE_SIZE (48)."""
        return TILE_SIZE
    
    @property
    def pixmap(self) -> QPixmap:
        """Get a QPixmap for display, caching the result."""
        if self._pixmap is None:
            object.__setattr__(self, '_pixmap', QPixmap.fromImage(self.image))
        return self._pixmap
    
    @property
    def source_name(self) -> str:
        """Get just the filename from the source path."""
        from pathlib import Path
        return Path(self.source_path).name
