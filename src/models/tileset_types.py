"""
Tileset type definitions for RPG Maker MZ.

Each tileset type defines:
- Image dimensions
- Unit layout (how to slice the image into selectable units)
"""

from dataclasses import dataclass
from typing import List, Tuple

from ..utils.constants import TILE_SIZE


@dataclass(frozen=True)
class UnitDefinition:
    """Defines a unit type within a tileset (size in tiles)."""
    width: int
    height: int
    
    @property
    def pixel_width(self) -> int:
        return self.width * TILE_SIZE
    
    @property
    def pixel_height(self) -> int:
        return self.height * TILE_SIZE


@dataclass(frozen=True)
class TilesetType:
    """
    Defines a tileset format.
    
    For simple grids (A5, B-E): single unit type, uniform grid.
    For complex layouts (A2-A4): row layouts define the pattern per row.
    
    Uses even_row_layout for rows 0, 2, 4... and odd_row_layout for rows 1, 3, 5...
    For most tilesets these are identical; A4 uses different layouts for alternating rows.
    """
    name: str
    width: int
    height: int
    even_row_layout: Tuple[UnitDefinition, ...]
    odd_row_layout: Tuple[UnitDefinition, ...]
    unit_rows: int
    
    @property
    def total_units(self) -> int:
        """Total number of selectable units in this tileset."""
        total = 0
        for row in range(self.unit_rows):
            layout = self.even_row_layout if row % 2 == 0 else self.odd_row_layout
            # Calculate how many times the layout pattern fits in the width
            pattern_width = sum(u.pixel_width for u in layout)
            patterns_per_row = self.width // pattern_width
            total += len(layout) * patterns_per_row
        return total


# Unit size definitions (dimensions in tiles)
UNIT_1x1 = UnitDefinition(1, 1)
UNIT_2x2 = UnitDefinition(2, 2)
UNIT_2x3 = UnitDefinition(2, 3)


# Tileset type definitions
TILESET_TYPES = {
    # A2 also handles A1 images (same dimensions, compatible 2×3 unit layout)
    "A2": TilesetType(
        name="A2",
        width=768,
        height=576,
        even_row_layout=(UNIT_2x3,),
        odd_row_layout=(UNIT_2x3,),
        unit_rows=4,
    ),
    "A3": TilesetType(
        name="A3",
        width=768,
        height=384,
        even_row_layout=(UNIT_2x2,),
        odd_row_layout=(UNIT_2x2,),
        unit_rows=4,
    ),
    # A4 uses alternating row layouts for wall tops (2×3) and faces (2×2)
    "A4": TilesetType(
        name="A4",
        width=768,
        height=720,
        even_row_layout=(UNIT_2x3,),
        odd_row_layout=(UNIT_2x2,),
        unit_rows=6,
    ),
    "A5": TilesetType(
        name="A5",
        width=384,
        height=768,
        even_row_layout=(UNIT_1x1,),
        odd_row_layout=(UNIT_1x1,),
        unit_rows=16,
    ),
    # B represents B/C/D/E (identical format)
    "B": TilesetType(
        name="B",
        width=768,
        height=768,
        even_row_layout=(UNIT_1x1,),
        odd_row_layout=(UNIT_1x1,),
        unit_rows=16,
    ),
}


def get_unit_positions(tileset_type: TilesetType) -> List[Tuple[int, int, int, int]]:
    """
    Get all unit positions (x, y, width, height) in pixels for a tileset type.
    
    Returns list of (x, y, pixel_width, pixel_height) tuples.
    """
    positions = []
    y = 0
    
    for row in range(tileset_type.unit_rows):
        layout = tileset_type.even_row_layout if row % 2 == 0 else tileset_type.odd_row_layout
        
        # Calculate how many times the layout pattern repeats horizontally
        pattern_width = sum(u.pixel_width for u in layout)
        patterns_per_row = tileset_type.width // pattern_width
        
        # Row height is determined by the first unit in the layout
        # (all units in a row should have the same height)
        row_height = layout[0].pixel_height
        
        # Add units for this row
        x = 0
        for _ in range(patterns_per_row):
            for unit in layout:
                positions.append((x, y, unit.pixel_width, unit.pixel_height))
                x += unit.pixel_width
        
        y += row_height
    
    return positions


# Display names for grouped types (used in UI)
# These provide user-friendly names that reflect RPG Maker's naming convention
DISPLAY_NAMES = {
    "A2": "A1/A2",  # A1 and A2 share dimensions
    "B": "B-E",     # B, C, D, E are identical
}

# Reverse mapping: display name -> canonical type
DISPLAY_NAME_TO_TYPE = {v: k for k, v in DISPLAY_NAMES.items()}

# All selectable types for the UI (uses display names for grouped types)
SELECTABLE_TYPES = ["A1/A2", "A3", "A4", "A5", "B-E"]


def get_display_name(type_name: str) -> str:
    """Get the display name for a type (grouped if applicable)."""
    return DISPLAY_NAMES.get(type_name, type_name)


def get_canonical_type(type_or_group: str) -> str:
    """Get the canonical individual type name for a type or group."""
    return DISPLAY_NAME_TO_TYPE.get(type_or_group, type_or_group)


def get_detection_message(type_name: str) -> str:
    """Get a message describing the detected tileset type."""
    return DISPLAY_NAMES.get(type_name, type_name)