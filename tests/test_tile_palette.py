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


class TestTilePaletteMultiselect:
    """Tests for palette multiselect functionality."""
    
    def _create_mock_unit(self, grid_width: int, grid_height: int, 
                          source_path: str = "/test/mock.png",
                          grid_x: int = 0, grid_y: int = 0) -> TileUnit:
        """Create a mock tile unit with correct tile positions."""
        tiles = []
        index = 0
        for dy in range(grid_height):
            for dx in range(grid_width):
                img = QImage(TILE_SIZE, TILE_SIZE, QImage.Format.Format_ARGB32)
                img.fill(Qt.GlobalColor.blue)
                tile = Tile(
                    source_path=source_path,
                    source_index=index,
                    x=(grid_x + dx) * TILE_SIZE,
                    y=(grid_y + dy) * TILE_SIZE,
                    image=img,
                )
                tiles.append(tile)
                index += 1
        
        unit = TileUnit(
            grid_width=grid_width,
            grid_height=grid_height,
            tiles=tiles,
            grid_x=grid_x,
            grid_y=grid_y,
        )
        for tile in tiles:
            tile.unit = unit
        return unit
    
    def test_single_click_selects_unit(self, qtbot):
        """Single click without modifiers selects one unit."""
        palette = TilePalette()
        qtbot.addWidget(palette)
        
        unit1 = self._create_mock_unit(1, 1)
        unit2 = self._create_mock_unit(1, 1, grid_x=1)
        palette.set_units([unit1, unit2])
        
        # Simulate click on first unit without modifiers
        palette._on_tile_clicked(unit1.tiles[0], Qt.KeyboardModifier.NoModifier)
        
        assert len(palette._selected_units) == 1
        assert palette._selected_units[0] is unit1
    
    def test_ctrl_click_adds_to_selection_same_source(self, qtbot):
        """Ctrl+click adds unit to selection if same source."""
        palette = TilePalette()
        qtbot.addWidget(palette)
        
        unit1 = self._create_mock_unit(1, 1, grid_x=0)
        unit2 = self._create_mock_unit(1, 1, grid_x=1)
        palette.set_units([unit1, unit2])
        
        # First click - select unit1
        palette._on_tile_clicked(unit1.tiles[0], Qt.KeyboardModifier.NoModifier)
        assert len(palette._selected_units) == 1
        
        # Ctrl+click unit2 - should add to selection
        palette._on_tile_clicked(unit2.tiles[0], Qt.KeyboardModifier.ControlModifier)
        assert len(palette._selected_units) == 2
        assert unit1 in palette._selected_units
        assert unit2 in palette._selected_units
    
    def test_ctrl_click_toggles_off(self, qtbot):
        """Ctrl+click on selected unit removes it from selection."""
        palette = TilePalette()
        qtbot.addWidget(palette)
        
        unit1 = self._create_mock_unit(1, 1, grid_x=0)
        unit2 = self._create_mock_unit(1, 1, grid_x=1)
        palette.set_units([unit1, unit2])
        
        # Select both units
        palette._on_tile_clicked(unit1.tiles[0], Qt.KeyboardModifier.NoModifier)
        palette._on_tile_clicked(unit2.tiles[0], Qt.KeyboardModifier.ControlModifier)
        assert len(palette._selected_units) == 2
        
        # Ctrl+click unit1 again - should remove it
        palette._on_tile_clicked(unit1.tiles[0], Qt.KeyboardModifier.ControlModifier)
        assert len(palette._selected_units) == 1
        assert palette._selected_units[0] is unit2
    
    def test_ctrl_click_different_source_replaces_selection(self, qtbot):
        """Ctrl+click on different source replaces selection."""
        palette = TilePalette()
        qtbot.addWidget(palette)
        
        unit1 = self._create_mock_unit(1, 1, source_path="/test/source1.png")
        unit2 = self._create_mock_unit(1, 1, source_path="/test/source2.png")
        palette.set_units([unit1, unit2])
        
        # Select unit1
        palette._on_tile_clicked(unit1.tiles[0], Qt.KeyboardModifier.NoModifier)
        assert len(palette._selected_units) == 1
        
        # Ctrl+click unit2 from different source - should replace
        palette._on_tile_clicked(unit2.tiles[0], Qt.KeyboardModifier.ControlModifier)
        assert len(palette._selected_units) == 1
        assert palette._selected_units[0] is unit2
    
    def test_click_already_selected_keeps_selection(self, qtbot):
        """Clicking an already-selected unit keeps current selection."""
        palette = TilePalette()
        qtbot.addWidget(palette)
        
        unit1 = self._create_mock_unit(1, 1, grid_x=0)
        unit2 = self._create_mock_unit(1, 1, grid_x=1)
        palette.set_units([unit1, unit2])
        
        # Select both units
        palette._on_tile_clicked(unit1.tiles[0], Qt.KeyboardModifier.NoModifier)
        palette._on_tile_clicked(unit2.tiles[0], Qt.KeyboardModifier.ControlModifier)
        assert len(palette._selected_units) == 2
        
        # Click unit1 again (already selected) - should keep both selected
        palette._on_tile_clicked(unit1.tiles[0], Qt.KeyboardModifier.NoModifier)
        assert len(palette._selected_units) == 2
    
    def test_get_draggable_units_includes_all_sizes(self, qtbot):
        """get_draggable_units returns units of any size from same source."""
        palette = TilePalette()
        qtbot.addWidget(palette)
        
        unit_1x1_a = self._create_mock_unit(1, 1, grid_x=0)
        unit_1x1_b = self._create_mock_unit(1, 1, grid_x=1)
        unit_2x2 = self._create_mock_unit(2, 2, grid_x=2)
        palette.set_units([unit_1x1_a, unit_1x1_b, unit_2x2])
        
        # Select all three units
        palette._selected_units = [unit_1x1_a, unit_1x1_b, unit_2x2]
        
        # Get draggable units for a 1x1 unit
        draggable = palette.get_draggable_units(unit_1x1_a)
        
        # Should include all units (no size restriction)
        assert len(draggable) == 3
        assert unit_1x1_a in draggable
        assert unit_1x1_b in draggable
        assert unit_2x2 in draggable
    
    def test_get_draggable_units_returns_all_selected(self, qtbot):
        """get_draggable_units returns all selected units when clicked unit is selected."""
        palette = TilePalette()
        qtbot.addWidget(palette)
        
        unit_1x1 = self._create_mock_unit(1, 1, grid_x=0)
        unit_2x2 = self._create_mock_unit(2, 2, grid_x=1)
        palette.set_units([unit_1x1, unit_2x2])
        
        # Select both units
        palette._selected_units = [unit_1x1, unit_2x2]
        
        # Get draggable units for the 2x2 unit
        draggable = palette.get_draggable_units(unit_2x2)
        
        # Should return both selected units
        assert len(draggable) == 2
        assert unit_1x1 in draggable
        assert unit_2x2 in draggable
    
    def test_get_draggable_units_same_source_only(self, qtbot):
        """get_draggable_units filters to same source."""
        palette = TilePalette()
        qtbot.addWidget(palette)
        
        unit_a1 = self._create_mock_unit(1, 1, source_path="/test/a.png", grid_x=0)
        unit_a2 = self._create_mock_unit(1, 1, source_path="/test/a.png", grid_x=1)
        unit_b1 = self._create_mock_unit(1, 1, source_path="/test/b.png", grid_x=2)
        palette.set_units([unit_a1, unit_a2, unit_b1])
        
        # Select all three units
        palette._selected_units = [unit_a1, unit_a2, unit_b1]
        
        # Get draggable units for first unit from source A
        draggable = palette.get_draggable_units(unit_a1)
        
        # Should only include units from source A
        assert len(draggable) == 2
        assert unit_a1 in draggable
        assert unit_a2 in draggable
        assert unit_b1 not in draggable

