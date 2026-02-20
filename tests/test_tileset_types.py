"""Tests for tileset type definitions and unit position calculations."""

import pytest

from src.models.tileset_types import (
    TILESET_TYPES,
    get_unit_positions,
    UNIT_1x1,
    UNIT_2x2,
    UNIT_2x3,
    UNIT_6x3,
)
from src.utils.constants import TILE_SIZE


class TestTilesetTypeCounts:
    """Verify each tileset type has the correct number of units."""
    
    def test_a1_has_16_units(self):
        """A1: 4 rows × 4 units per row (2 animated + 2 static)."""
        assert TILESET_TYPES["A1"].total_units == 16
    
    def test_a2_has_32_units(self):
        """A2: 4 rows × 8 units per row."""
        assert TILESET_TYPES["A2"].total_units == 32
    
    def test_a3_has_32_units(self):
        """A3: 4 rows × 8 units per row."""
        assert TILESET_TYPES["A3"].total_units == 32
    
    def test_a4_has_48_units(self):
        """A4: 6 unit rows × 8 units per row (3 wall tops + 3 wall faces)."""
        assert TILESET_TYPES["A4"].total_units == 48
    
    def test_a5_has_128_units(self):
        """A5: 16 rows × 8 tiles per row."""
        assert TILESET_TYPES["A5"].total_units == 128
    
    @pytest.mark.parametrize("name", ["B", "C", "D", "E"])
    def test_bcde_have_256_units(self, name):
        """B-E: 16 rows × 16 tiles per row."""
        assert TILESET_TYPES[name].total_units == 256


class TestTilesetTypeDimensions:
    """Verify tileset image dimensions are correct."""
    
    @pytest.mark.parametrize("name,width,height", [
        ("A1", 768, 576),
        ("A2", 768, 576),
        ("A3", 768, 384),
        ("A4", 768, 720),
        ("A5", 384, 768),
        ("B", 768, 768),
        ("C", 768, 768),
        ("D", 768, 768),
        ("E", 768, 768),
    ])
    def test_dimensions(self, name, width, height):
        tileset = TILESET_TYPES[name]
        assert tileset.width == width
        assert tileset.height == height


class TestGetUnitPositions:
    """Verify get_unit_positions returns correct positions."""
    
    def test_positions_count_matches_total_units(self):
        """Position count should equal total_units for all tilesets."""
        for name, tileset in TILESET_TYPES.items():
            positions = get_unit_positions(tileset)
            assert len(positions) == tileset.total_units, f"{name} position count mismatch"
    
    def test_positions_within_bounds(self):
        """All positions should be within tileset dimensions."""
        for name, tileset in TILESET_TYPES.items():
            positions = get_unit_positions(tileset)
            for x, y, w, h in positions:
                assert x >= 0, f"{name}: x={x} is negative"
                assert y >= 0, f"{name}: y={y} is negative"
                assert x + w <= tileset.width, f"{name}: x+w={x+w} exceeds width {tileset.width}"
                assert y + h <= tileset.height, f"{name}: y+h={y+h} exceeds height {tileset.height}"
    
    def test_no_overlapping_positions(self):
        """Units should not overlap (for simple grid tilesets)."""
        for name in ["A5", "B", "C", "D", "E"]:
            tileset = TILESET_TYPES[name]
            positions = get_unit_positions(tileset)
            
            for i, (x1, y1, w1, h1) in enumerate(positions):
                for j, (x2, y2, w2, h2) in enumerate(positions):
                    if i >= j:
                        continue
                    # Check if rectangles overlap
                    x_overlap = x1 < x2 + w2 and x2 < x1 + w1
                    y_overlap = y1 < y2 + h2 and y2 < y1 + h1
                    assert not (x_overlap and y_overlap), f"{name}: units {i} and {j} overlap"


class TestA1Layout:
    """Verify A1's specific alternating layout."""
    
    def test_row_pattern(self):
        """Each row should have: [6×3][2×3][6×3][2×3]."""
        tileset = TILESET_TYPES["A1"]
        positions = get_unit_positions(tileset)
        
        # 4 rows, 4 units each
        assert len(positions) == 16
        
        for row in range(4):
            row_positions = positions[row * 4 : row * 4 + 4]
            
            # Verify widths: 288, 96, 288, 96
            widths = [p[2] for p in row_positions]
            assert widths == [288, 96, 288, 96], f"Row {row} width pattern incorrect"
            
            # All heights should be 144 (3 tiles)
            heights = [p[3] for p in row_positions]
            assert all(h == 144 for h in heights), f"Row {row} heights incorrect"


class TestA4Layout:
    """Verify A4's alternating wall tops / wall faces layout."""
    
    def test_alternating_row_heights(self):
        """Even rows (wall tops) are 144px, odd rows (wall faces) are 96px."""
        tileset = TILESET_TYPES["A4"]
        positions = get_unit_positions(tileset)
        
        # 6 unit rows, 8 units each = 48 positions
        assert len(positions) == 48
        
        for row in range(6):
            row_positions = positions[row * 8 : row * 8 + 8]
            expected_height = 144 if row % 2 == 0 else 96  # Even=wall tops, Odd=wall faces
            
            for pos in row_positions:
                assert pos[3] == expected_height, f"Row {row} has wrong height {pos[3]}, expected {expected_height}"
    
    def test_total_height_matches(self):
        """Sum of row heights should equal tileset height (720px)."""
        # 3 wall top rows (144px each) + 3 wall face rows (96px each)
        expected = 3 * 144 + 3 * 96  # 432 + 288 = 720
        assert expected == 720
        assert TILESET_TYPES["A4"].height == 720
