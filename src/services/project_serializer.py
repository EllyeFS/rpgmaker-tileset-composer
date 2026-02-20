"""
Image loading utilities for opening tileset images onto the canvas.
"""

from typing import Dict, Tuple, Optional

from PySide6.QtGui import QImage

from ..models.tile_unit import TileUnit
from ..utils.constants import TILE_SIZE


def load_image_as_project(
    image_path: str,
    tileset_type_name: Optional[str] = None,
) -> Tuple[str, Dict[Tuple[int, int], TileUnit], str]:
    """
    Load an existing tileset image onto the canvas.
    
    Extracts all tiles from the image and places them on the canvas
    at their original positions.
    
    Args:
        image_path: Path to the tileset image file
        tileset_type_name: If provided, use this type. Otherwise auto-detect.
        
    Returns:
        Tuple of (tileset_type_name, placed_units_dict, detection_message)
        
    Raises:
        ValueError: If the image cannot be loaded or type cannot be determined
    """
    from ..models.tileset_types import TILESET_TYPES, get_detection_message
    from .image_loader import ImageLoader, AUTO_DETECT_DIMENSIONS
    
    image = QImage(image_path)
    if image.isNull():
        raise ValueError(f"Failed to load image: {image_path}")
    
    # Determine tileset type
    if tileset_type_name:
        if tileset_type_name not in TILESET_TYPES:
            raise ValueError(f"Unknown tileset type: {tileset_type_name}")
        detected_type = tileset_type_name
    else:
        # Auto-detect from dimensions
        dimensions = (image.width(), image.height())
        if dimensions in AUTO_DETECT_DIMENSIONS:
            detected_type = AUTO_DETECT_DIMENSIONS[dimensions]
        else:
            # Try to find matching type by dimensions
            for name, ttype in TILESET_TYPES.items():
                if ttype.width == image.width() and ttype.height == image.height():
                    detected_type = name
                    break
            else:
                raise ValueError(
                    f"Cannot determine tileset type for image with dimensions "
                    f"{image.width()}×{image.height()}"
                )
    
    # Get detection message for UI
    detection_message = get_detection_message(detected_type)
    
    tileset_type = TILESET_TYPES[detected_type]
    
    # Load units using ImageLoader (which handles autotile grouping)
    units = ImageLoader.load_units_from_image(image_path, tileset_type)
    
    # Place each unit at its original grid position
    placed_units: Dict[Tuple[int, int], TileUnit] = {}
    for unit in units:
        # The unit's first tile has x, y in pixels - convert to grid position
        if unit.tiles:
            grid_x = unit.tiles[0].x // TILE_SIZE
            grid_y = unit.tiles[0].y // TILE_SIZE
            placed_units[(grid_x, grid_y)] = unit
    
    return detected_type, placed_units, detection_message
