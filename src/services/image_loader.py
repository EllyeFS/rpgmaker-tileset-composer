"""
Image loading service for extracting tiles and units from source images.

Images are sliced into TILE_SIZE × TILE_SIZE tiles, then grouped into TileUnits
according to the tileset type. Simple grids have 1×1 units, autotiles have
larger units (2×2, 2×3, etc.).
"""

from pathlib import Path
from typing import Callable, List, Optional, Tuple

from PySide6.QtGui import QImage

from ..models.tile import Tile
from ..models.tile_unit import TileUnit
from ..models.tileset_types import TilesetType, get_unit_positions, TILESET_TYPES
from ..utils.constants import TILE_SIZE


# Dimension-based auto-detection mapping: (width, height) -> tileset type name
# Note: A1 and A2 share the same dimensions (768×576). Both are treated as A2 format
# since they use compatible 2×3 unit layouts. A1's animated frames appear as static units.
AUTO_DETECT_DIMENSIONS = {
    (768, 576): "A2",  # A1/A2: Autotiles (2×3 units) - same dimensions
    (768, 384): "A3",  # A3: Building autotiles (2×2 units)
    (768, 720): "A4",  # A4: Wall autotiles (alternating 2×3 and 2×2 units)
}


class ImageLoader:
    """Service for loading images and extracting tiles/units."""
    
    # Use lowercase only - glob is case-insensitive on Windows anyway
    SUPPORTED_EXTENSIONS = {'.png'}
    
    @classmethod
    def load_units_from_image(
        cls,
        image_path: str,
        tileset_type: Optional[TilesetType] = None,
    ) -> List[TileUnit]:
        """
        Load an image and extract tile units from it.
        
        Images are sliced into tiles (TILE_SIZE × TILE_SIZE), then grouped
        into units according to the tileset type.
        
        Args:
            image_path: Path to the source image file.
            tileset_type: If provided, group tiles according to this type's layout.
                         If None, auto-detect from dimensions or use 1×1 units.
        
        Returns:
            List of TileUnit objects, each containing one or more Tiles.
        """
        image = QImage(image_path)
        if image.isNull():
            raise ValueError(f"Failed to load image: {image_path}")
        
        # Convert to ARGB32 for consistent handling
        if image.format() != QImage.Format.Format_ARGB32:
            image = image.convertToFormat(QImage.Format.Format_ARGB32)
        
        # Use provided type, or auto-detect from dimensions
        effective_type = tileset_type
        if effective_type is None:
            dimensions = (image.width(), image.height())
            if dimensions in AUTO_DETECT_DIMENSIONS:
                type_name = AUTO_DETECT_DIMENSIONS[dimensions]
                effective_type = TILESET_TYPES[type_name]
        
        # First, extract all 48×48 tiles into a 2D grid
        tile_grid = cls._extract_tile_grid(image_path, image)
        
        # Then group tiles into units based on tileset type
        if effective_type:
            return cls._group_by_tileset_type(tile_grid, effective_type, image)
        else:
            return cls._group_as_simple_grid(tile_grid, image.width())
    
    @classmethod
    def _extract_tile_grid(
        cls,
        image_path: str,
        image: QImage,
    ) -> List[List[Tile]]:
        """
        Extract all tiles from an image into a 2D grid.
        
        Returns:
            2D list of tiles indexed as tile_grid[row][col]
        """
        cols = image.width() // TILE_SIZE
        rows = image.height() // TILE_SIZE
        
        tile_grid: List[List[Tile]] = []
        index = 0
        
        for row in range(rows):
            tile_row: List[Tile] = []
            for col in range(cols):
                x = col * TILE_SIZE
                y = row * TILE_SIZE
                
                tile_image = image.copy(x, y, TILE_SIZE, TILE_SIZE)
                tile = Tile(
                    source_path=image_path,
                    source_index=index,
                    x=x,
                    y=y,
                    image=tile_image,
                )
                tile_row.append(tile)
                index += 1
            tile_grid.append(tile_row)
        
        return tile_grid
    
    @classmethod
    def _group_as_simple_grid(
        cls,
        tile_grid: List[List[Tile]],
        image_width: int,
    ) -> List[TileUnit]:
        """
        Group tiles as 1×1 units (simple grid).
        
        Tiles are grouped in standard row-by-row order.
        """
        units: List[TileUnit] = []
        
        if not tile_grid:
            return units
        
        cols = len(tile_grid[0])
        rows = len(tile_grid)
        
        # Standard row-by-row order
        for row in range(rows):
            for col in range(cols):
                tile = tile_grid[row][col]
                unit = TileUnit(
                    grid_width=1,
                    grid_height=1,
                    tiles=[tile],
                    grid_x=col,
                    grid_y=row,
                )
                tile.unit = unit
                units.append(unit)
        
        return units
    
    @classmethod
    def _group_by_tileset_type(
        cls,
        tile_grid: List[List[Tile]],
        tileset_type: TilesetType,
        image: QImage,
    ) -> List[TileUnit]:
        """Group tiles into units according to a tileset type's layout."""
        units: List[TileUnit] = []
        positions = get_unit_positions(tileset_type)
        
        for unit_index, (px, py, pw, ph) in enumerate(positions):
            # Convert pixel positions to tile grid positions
            start_col = px // TILE_SIZE
            start_row = py // TILE_SIZE
            unit_cols = pw // TILE_SIZE
            unit_rows = ph // TILE_SIZE
            
            # Make sure we don't go out of bounds
            if start_col + unit_cols > len(tile_grid[0]) if tile_grid else 0:
                continue
            if start_row + unit_rows > len(tile_grid):
                continue
            
            # Collect tiles for this unit in row-major order
            unit_tiles: List[Tile] = []
            for r in range(unit_rows):
                for c in range(unit_cols):
                    tile = tile_grid[start_row + r][start_col + c]
                    unit_tiles.append(tile)
            
            unit = TileUnit(
                grid_width=unit_cols,
                grid_height=unit_rows,
                tiles=unit_tiles,
                grid_x=start_col,
                grid_y=start_row,
            )
            
            # Link tiles back to their unit
            for tile in unit_tiles:
                tile.unit = unit
            
            units.append(unit)
        
        return units
    
    @classmethod
    def load_tiles_from_image(
        cls,
        image_path: str,
        tileset_type: Optional[TilesetType] = None,
    ) -> List[Tile]:
        """
        Load an image and extract individual tiles from it.
        
        Returns a flat list of all tiles. For grouped unit access,
        use load_units_from_image instead.
        """
        units = cls.load_units_from_image(image_path, tileset_type)
        # Return all tiles from all units
        return [tile for unit in units for tile in unit.tiles]
    
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
    def _load_batch(
        cls,
        image_paths: List[str],
        load_func: Callable[[str], List],
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> List:
        """
        Load items from multiple images using a provided load function.
        
        Args:
            image_paths: List of paths to image files.
            load_func: Function to load items from a single image path.
            progress_callback: Optional callback(current, total) for progress updates.
        
        Returns:
            List of all items from all images.
        """
        all_items = []
        total = len(image_paths)
        
        for i, image_path in enumerate(image_paths):
            if progress_callback:
                progress_callback(i, total)
            try:
                items = load_func(image_path)
                all_items.extend(items)
            except ValueError:
                # Skip files that fail to load
                continue
        
        if progress_callback:
            progress_callback(total, total)
        
        return all_items
    
    @classmethod
    def load_units_from_folder(
        cls,
        folder_path: str,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> List[TileUnit]:
        """
        Load all images in a folder as tile units.
        
        Args:
            folder_path: Path to folder containing images.
            progress_callback: Optional callback(current, total) for progress updates.
        
        Returns:
            List of all units from all images in the folder.
        """
        image_paths = cls.find_images_in_folder(folder_path)
        return cls._load_batch(image_paths, cls.load_units_from_image, progress_callback)
    
    @classmethod
    def load_units_from_images(
        cls,
        image_paths: List[str],
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> List[TileUnit]:
        """
        Load specific images as tile units.
        
        Args:
            image_paths: List of paths to image files.
            progress_callback: Optional callback(current, total) for progress updates.
        
        Returns:
            List of all units from the specified images.
        """
        return cls._load_batch(image_paths, cls.load_units_from_image, progress_callback)
