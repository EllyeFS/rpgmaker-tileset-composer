"""
Tile model representing an extracted tile/unit from a source image.
"""

from dataclasses import dataclass
from typing import Optional

from PySide6.QtGui import QImage, QPixmap


@dataclass
class Tile:
    """
    Represents a single tile or unit extracted from a source image.
    
    For simple grids (A5, B-E): a 48×48 pixel tile.
    For autotiles (A1-A4): a larger unit (e.g., 96×144 for 2×3).
    """
    # Source information
    source_path: str          # Path to the source image file
    source_index: int         # Index within the source image (0-based)
    
    # Position in source image (pixels)
    x: int
    y: int
    width: int
    height: int
    
    # The actual image data
    image: QImage
    
    # Cached pixmap for display (created on demand)
    _pixmap: Optional[QPixmap] = None
    
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
