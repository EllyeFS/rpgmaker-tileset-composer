"""
Image loading service for extracting tiles from source images.
"""

from pathlib import Path
from typing import List, Optional

from PySide6.QtGui import QImage

from ..models.tile import Tile
from ..models.tileset_types import TilesetType, get_unit_positions
from ..utils.constants import TILE_SIZE


class ImageLoader:
    """Service for loading images and extracting tiles/units."""
    
    # Use lowercase only - glob is case-insensitive on Windows anyway
    SUPPORTED_EXTENSIONS = {'.png'}
    
    @classmethod
    def load_tiles_from_image(
        cls,
        image_path: str,
        tileset_type: Optional[TilesetType] = None,
    ) -> List[Tile]:
        """
        Load an image and extract tiles/units from it.
        
        Args:
            image_path: Path to the source image file.
            tileset_type: If provided, extract units according to this type's layout.
                         If None, extract as simple 48×48 grid.
        
        Returns:
            List of Tile objects extracted from the image.
        """
        image = QImage(image_path)
        if image.isNull():
            raise ValueError(f"Failed to load image: {image_path}")
        
        # Convert to ARGB32 for consistent handling
        if image.format() != QImage.Format.Format_ARGB32:
            image = image.convertToFormat(QImage.Format.Format_ARGB32)
        
        if tileset_type:
            return cls._extract_by_tileset_type(image_path, image, tileset_type)
        else:
            return cls._extract_simple_grid(image_path, image)
    
    @classmethod
    def _extract_simple_grid(cls, image_path: str, image: QImage) -> List[Tile]:
        """
        Extract tiles as a simple 48×48 grid.
        
        For 16-column images (BCDE pattern), tiles are extracted in two halves:
        first the left 8 columns (all rows), then the right 8 columns (all rows).
        This matches how RPG Maker displays them.
        """
        tiles = []
        
        cols = image.width() // TILE_SIZE
        rows = image.height() // TILE_SIZE
        
        # For BCDE-style images (16 columns), read in two 8-column halves
        if cols == 16:
            index = 0
            # Left half (columns 0-7)
            for row in range(rows):
                for col in range(8):
                    x = col * TILE_SIZE
                    y = row * TILE_SIZE
                    tile_image = image.copy(x, y, TILE_SIZE, TILE_SIZE)
                    tile = Tile(
                        source_path=image_path,
                        source_index=index,
                        x=x,
                        y=y,
                        width=TILE_SIZE,
                        height=TILE_SIZE,
                        image=tile_image,
                    )
                    tiles.append(tile)
                    index += 1
            # Right half (columns 8-15)
            for row in range(rows):
                for col in range(8, 16):
                    x = col * TILE_SIZE
                    y = row * TILE_SIZE
                    tile_image = image.copy(x, y, TILE_SIZE, TILE_SIZE)
                    tile = Tile(
                        source_path=image_path,
                        source_index=index,
                        x=x,
                        y=y,
                        width=TILE_SIZE,
                        height=TILE_SIZE,
                        image=tile_image,
                    )
                    tiles.append(tile)
                    index += 1
            return tiles
        
        # Standard row-by-row extraction for other sizes
        index = 0
        for row in range(rows):
            for col in range(cols):
                x = col * TILE_SIZE
                y = row * TILE_SIZE
                
                # Extract the tile region
                tile_image = image.copy(x, y, TILE_SIZE, TILE_SIZE)
                
                tile = Tile(
                    source_path=image_path,
                    source_index=index,
                    x=x,
                    y=y,
                    width=TILE_SIZE,
                    height=TILE_SIZE,
                    image=tile_image,
                )
                tiles.append(tile)
                index += 1
        
        return tiles
    
    @classmethod
    def _extract_by_tileset_type(
        cls,
        image_path: str,
        image: QImage,
        tileset_type: TilesetType,
    ) -> List[Tile]:
        """Extract units according to a tileset type's layout."""
        tiles = []
        positions = get_unit_positions(tileset_type)
        
        for index, (x, y, width, height) in enumerate(positions):
            # Make sure we don't go out of bounds
            if x + width > image.width() or y + height > image.height():
                continue
            
            unit_image = image.copy(x, y, width, height)
            
            tile = Tile(
                source_path=image_path,
                source_index=index,
                x=x,
                y=y,
                width=width,
                height=height,
                image=unit_image,
            )
            tiles.append(tile)
        
        return tiles
    
    @classmethod
    def find_images_in_folder(cls, folder_path: str) -> List[str]:
        """
        Find all supported image files in a folder.
        
        Returns:
            List of absolute paths to image files.
        """
        folder = Path(folder_path)
        if not folder.is_dir():
            return []
        
        # Use a set to avoid duplicates (case-insensitive filesystems)
        images = set()
        for ext in cls.SUPPORTED_EXTENSIONS:
            images.update(str(p) for p in folder.glob(f'*{ext}'))
        
        return sorted(images)
    
    @classmethod
    def load_folder_as_simple_tiles(cls, folder_path: str) -> List[Tile]:
        """
        Load all images in a folder as simple 48×48 tile grids.
        
        Returns:
            List of all tiles from all images in the folder.
        """
        all_tiles = []
        
        for image_path in cls.find_images_in_folder(folder_path):
            try:
                tiles = cls.load_tiles_from_image(image_path)
                all_tiles.extend(tiles)
            except ValueError:
                # Skip files that fail to load
                continue
        
        return all_tiles
