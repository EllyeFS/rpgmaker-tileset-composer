"""Tests for TilePalette widget and TileButton edge detection."""

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage

from src.ui.tile_palette import TileButton, TilePalette
from src.models.tile import Tile
from src.models.tile_unit import TileUnit
from src.utils.constants import TILE_SIZE


class TestTileButtonEdgeDetection:
    """Tests for TileButton edge flag functionality."""
    
    def _create_mock_tile(self, x: int = 0, y: int = 0) -> Tile:
        """Create a mock tile for testing."""
        img = QImage(TILE_SIZE, TILE_SIZE, QImage.Format.Format_ARGB32)
        img.fill(Qt.GlobalColor.red)
        return Tile(
            source_path="/test/mock.png",
            source_index=0,
            x=x,
            y=y,
            image=img,
        )

    def test_default_all_edges_true(self, qtbot):
        """By default, all edges are unit boundaries."""
        tile = self._create_mock_tile()
        btn = TileButton(tile)
        qtbot.addWidget(btn)
        
        assert btn._edge_top is True
        assert btn._edge_bottom is True
        assert btn._edge_left is True
        assert btn._edge_right is True

    def test_custom_edge_flags(self, qtbot):
        """Edge flags can be set via constructor."""
        tile = self._create_mock_tile()
        btn = TileButton(tile, edge_top=False, edge_bottom=True,
                        edge_left=False, edge_right=True)
        qtbot.addWidget(btn)
        
        assert btn._edge_top is False
        assert btn._edge_bottom is True
        assert btn._edge_left is False
        assert btn._edge_right is True

    def test_corner_tile_all_edges(self, qtbot):
        """A single 1x1 tile has all edges as boundaries."""
        tile = self._create_mock_tile(0, 0)
        btn = TileButton(tile, edge_top=True, edge_bottom=True,
                        edge_left=True, edge_right=True)
        qtbot.addWidget(btn)
        
        # All edges should be strong (2px)
        assert btn._edge_top is True
        assert btn._edge_bottom is True
        assert btn._edge_left is True
        assert btn._edge_right is True

    def test_internal_tile_no_edges(self, qtbot):
        """An internal tile (center of 3x3) has no boundary edges."""
        tile = self._create_mock_tile(TILE_SIZE, TILE_SIZE)  # Center of 3x3
        btn = TileButton(tile, edge_top=False, edge_bottom=False,
                        edge_left=False, edge_right=False)
        qtbot.addWidget(btn)
        
        # No edges should be strong
        assert btn._edge_top is False
        assert btn._edge_bottom is False
        assert btn._edge_left is False
        assert btn._edge_right is False

    def test_border_width_constants(self, qtbot):
        """Border width constants are correctly defined."""
        tile = self._create_mock_tile()
        btn = TileButton(tile)
        qtbot.addWidget(btn)
        
        assert btn.STRONG_BORDER_WIDTH == 2
        assert btn.LIGHT_BORDER_WIDTH == 1


class TestTilePaletteEdgeComputation:
    """Tests for edge computation when building the palette grid."""
    
    def _create_mock_unit(self, grid_width: int, grid_height: int) -> TileUnit:
        """Create a mock tile unit with correct tile positions."""
        tiles = []
        index = 0
        for dy in range(grid_height):
            for dx in range(grid_width):
                img = QImage(TILE_SIZE, TILE_SIZE, QImage.Format.Format_ARGB32)
                img.fill(Qt.GlobalColor.blue)
                tile = Tile(
                    source_path="/test/mock.png",
                    source_index=index,
                    x=dx * TILE_SIZE,
                    y=dy * TILE_SIZE,
                    image=img,
                )
                tiles.append(tile)
                index += 1
        
        unit = TileUnit(
            grid_width=grid_width,
            grid_height=grid_height,
            tiles=tiles,
            grid_x=0,
            grid_y=0,
        )
        for tile in tiles:
            tile.unit = unit
        return unit

    def test_1x1_unit_all_edges(self, qtbot):
        """A 1x1 unit has all edges as boundaries."""
        palette = TilePalette()
        qtbot.addWidget(palette)
        
        unit = self._create_mock_unit(1, 1)
        palette.set_units([unit])
        
        # Should have exactly one button
        assert len(palette._tile_buttons) == 1
        btn = palette._tile_buttons[0]
        
        assert btn._edge_top is True
        assert btn._edge_bottom is True
        assert btn._edge_left is True
        assert btn._edge_right is True

    def test_2x2_unit_corner_edges(self, qtbot):
        """A 2x2 unit has correct edge flags for each corner tile."""
        palette = TilePalette()
        qtbot.addWidget(palette)
        
        unit = self._create_mock_unit(2, 2)
        palette.set_units([unit])
        
        # Should have 4 buttons
        assert len(palette._tile_buttons) == 4
        
        # Find buttons by tile position
        buttons_by_pos = {(btn.tile.x, btn.tile.y): btn for btn in palette._tile_buttons}
        
        # Top-left (0, 0): top, left edges
        tl = buttons_by_pos[(0, 0)]
        assert tl._edge_top is True
        assert tl._edge_left is True
        assert tl._edge_bottom is False
        assert tl._edge_right is False
        
        # Top-right (48, 0): top, right edges
        tr = buttons_by_pos[(TILE_SIZE, 0)]
        assert tr._edge_top is True
        assert tr._edge_right is True
        assert tr._edge_bottom is False
        assert tr._edge_left is False
        
        # Bottom-left (0, 48): bottom, left edges
        bl = buttons_by_pos[(0, TILE_SIZE)]
        assert bl._edge_bottom is True
        assert bl._edge_left is True
        assert bl._edge_top is False
        assert bl._edge_right is False
        
        # Bottom-right (48, 48): bottom, right edges
        br = buttons_by_pos[(TILE_SIZE, TILE_SIZE)]
        assert br._edge_bottom is True
        assert br._edge_right is True
        assert br._edge_top is False
        assert br._edge_left is False

    def test_2x3_unit_edge_flags(self, qtbot):
        """A 2x3 unit has correct edge flags for all tiles."""
        palette = TilePalette()
        qtbot.addWidget(palette)
        
        unit = self._create_mock_unit(2, 3)
        palette.set_units([unit])
        
        # Should have 6 buttons (2 columns × 3 rows)
        assert len(palette._tile_buttons) == 6
        
        buttons_by_pos = {(btn.tile.x, btn.tile.y): btn for btn in palette._tile_buttons}
        
        # Top row: both have top edge
        assert buttons_by_pos[(0, 0)]._edge_top is True
        assert buttons_by_pos[(TILE_SIZE, 0)]._edge_top is True
        
        # Middle row: no top or bottom edge
        assert buttons_by_pos[(0, TILE_SIZE)]._edge_top is False
        assert buttons_by_pos[(0, TILE_SIZE)]._edge_bottom is False
        assert buttons_by_pos[(TILE_SIZE, TILE_SIZE)]._edge_top is False
        assert buttons_by_pos[(TILE_SIZE, TILE_SIZE)]._edge_bottom is False
        
        # Bottom row: both have bottom edge
        assert buttons_by_pos[(0, TILE_SIZE * 2)]._edge_bottom is True
        assert buttons_by_pos[(TILE_SIZE, TILE_SIZE * 2)]._edge_bottom is True
        
        # Left column: all have left edge
        assert buttons_by_pos[(0, 0)]._edge_left is True
        assert buttons_by_pos[(0, TILE_SIZE)]._edge_left is True
        assert buttons_by_pos[(0, TILE_SIZE * 2)]._edge_left is True
        
        # Right column: all have right edge
        assert buttons_by_pos[(TILE_SIZE, 0)]._edge_right is True
        assert buttons_by_pos[(TILE_SIZE, TILE_SIZE)]._edge_right is True
        assert buttons_by_pos[(TILE_SIZE, TILE_SIZE * 2)]._edge_right is True

    def test_multiple_units_independent_edges(self, qtbot):
        """Multiple units each have their own edge boundaries."""
        palette = TilePalette()
        qtbot.addWidget(palette)
        
        unit1 = self._create_mock_unit(1, 1)
        unit2 = self._create_mock_unit(2, 2)
        palette.set_units([unit1, unit2])
        
        # Should have 1 + 4 = 5 buttons
        assert len(palette._tile_buttons) == 5
        
        # The 1x1 unit button should have all edges
        unit1_buttons = [btn for btn in palette._tile_buttons if btn.tile.unit is unit1]
        assert len(unit1_buttons) == 1
        assert unit1_buttons[0]._edge_top is True
        assert unit1_buttons[0]._edge_bottom is True
        assert unit1_buttons[0]._edge_left is True
        assert unit1_buttons[0]._edge_right is True
