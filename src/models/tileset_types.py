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
    width: int   # Width in tiles
    height: int  # Height in tiles
    
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
    For complex layouts (A1-A4): row layouts define the pattern per row.
    
    Uses even_row_layout for rows 0, 2, 4... and odd_row_layout for rows 1, 3, 5...
    For most tilesets these are identical; A4 uses different layouts for alternating rows.
    """
    name: str
    width: int   # Image width in pixels
    height: int  # Image height in pixels
    
    # Layout pattern for even unit-rows (0, 2, 4, ...)
    even_row_layout: Tuple[UnitDefinition, ...]
    
    # Layout pattern for odd unit-rows (1, 3, 5, ...)
    # For most tilesets, this equals even_row_layout
    odd_row_layout: Tuple[UnitDefinition, ...]
    
    # Total number of unit rows
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


# Unit size definitions
UNIT_1x1 = UnitDefinition(1, 1)    # Single tile (48×48)
UNIT_2x2 = UnitDefinition(2, 2)    # 96×96 (A3, A4 wall face)
UNIT_2x3 = UnitDefinition(2, 3)    # 96×144 (A2, A4 wall top, A1 static)
UNIT_6x3 = UnitDefinition(6, 3)    # 288×144 (A1 animated)


# Tileset type definitions
TILESET_TYPES = {
    # A1: Animated autotiles - 768×576
    # 4 rows, each: [6×3][2×3][6×3][2×3]
    # Note: A1 shares dimensions with A2, so auto-detection treats both as A2 format.
    # This definition exists for potential future explicit A1 handling.
    "A1": TilesetType(
        name="A1",
        width=768,
        height=576,
        even_row_layout=(UNIT_6x3, UNIT_2x3, UNIT_6x3, UNIT_2x3),
        odd_row_layout=(UNIT_6x3, UNIT_2x3, UNIT_6x3, UNIT_2x3),
        unit_rows=4,
    ),
    
    # A2: Ground autotiles - 768×576
    # 4 rows of 2×3 units, 8 per row
    "A2": TilesetType(
        name="A2",
        width=768,
        height=576,
        even_row_layout=(UNIT_2x3,),
        odd_row_layout=(UNIT_2x3,),
        unit_rows=4,
    ),
    
    # A3: Building autotiles - 768×384
    # 4 rows of 2×2 units, 8 per row
    "A3": TilesetType(
        name="A3",
        width=768,
        height=384,
        even_row_layout=(UNIT_2x2,),
        odd_row_layout=(UNIT_2x2,),
        unit_rows=4,
    ),
    
    # A4: Wall autotiles - 768×720
    # Alternating rows: wall tops (2×3) on even rows, wall faces (2×2) on odd rows
    # 6 unit rows total (3 wall tops + 3 wall faces)
    "A4": TilesetType(
        name="A4",
        width=768,
        height=720,
        even_row_layout=(UNIT_2x3,),   # Wall tops
        odd_row_layout=(UNIT_2x2,),    # Wall faces
        unit_rows=6,
    ),
    
    # A5: Normal tiles - 384×768
    # 8×16 grid of individual tiles
    "A5": TilesetType(
        name="A5",
        width=384,
        height=768,
        even_row_layout=(UNIT_1x1,),
        odd_row_layout=(UNIT_1x1,),
        unit_rows=16,
    ),
    
    # B-E: Upper layer tiles - 768×768
    # 16×16 grid of individual tiles
    # Note: Source images may be smaller than 768×768; we always create at full size
    "B": TilesetType(
        name="B",
        width=768,
        height=768,
        even_row_layout=(UNIT_1x1,),
        odd_row_layout=(UNIT_1x1,),
        unit_rows=16,
    ),
    "C": TilesetType(
        name="C",
        width=768,
        height=768,
        even_row_layout=(UNIT_1x1,),
        odd_row_layout=(UNIT_1x1,),
        unit_rows=16,
    ),
    "D": TilesetType(
        name="D",
        width=768,
        height=768,
        even_row_layout=(UNIT_1x1,),
        odd_row_layout=(UNIT_1x1,),
        unit_rows=16,
    ),
    "E": TilesetType(
        name="E",
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


# Grouped types - types that share the same dimensions and are interchangeable
# These are grouped for UI purposes (New dialog, target label, detection)
TYPE_GROUPS = {
    "A1/A2": ["A1", "A2"],  # 768×576 animated/ground autotiles
    "B-E": ["B", "C", "D", "E"],  # 768×768 upper layer tiles
}

# Reverse mapping: individual type -> group name (if grouped)
TYPE_TO_GROUP = {}
for group_name, types in TYPE_GROUPS.items():
    for t in types:
        TYPE_TO_GROUP[t] = group_name

# Canonical types for each group (used for actual canvas dimensions)
GROUP_CANONICAL_TYPE = {
    "A1/A2": "A2",  # Use A2 format for A1/A2 (simpler layout)
    "B-E": "B",     # Use B for B-E (all identical)
}

# All selectable types for the UI (ungrouped + grouped)
SELECTABLE_TYPES = ["A1/A2", "A3", "A4", "A5", "B-E"]


def get_display_name(type_name: str) -> str:
    """Get the display name for a type (grouped if applicable)."""
    return TYPE_TO_GROUP.get(type_name, type_name)


def get_canonical_type(type_or_group: str) -> str:
    """Get the canonical individual type name for a type or group."""
    if type_or_group in GROUP_CANONICAL_TYPE:
        return GROUP_CANONICAL_TYPE[type_or_group]
    return type_or_group


def get_detection_message(type_name: str) -> str:
    """Get a message describing the detected tileset type."""
    if type_name in TYPE_TO_GROUP:
        group = TYPE_TO_GROUP[type_name]
        types = TYPE_GROUPS[group]
        if len(types) == 2:
            return f"{types[0]} or {types[1]}"
        else:
            return ", ".join(types[:-1]) + f" or {types[-1]}"
    return type_name

