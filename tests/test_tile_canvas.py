"""Tests for TileCanvas widget."""

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage

from src.ui.tile_canvas import TileCanvas, TileCanvasWidget
from src.models.tileset_types import TILESET_TYPES
from src.models.tile import Tile
from src.models.tile_unit import TileUnit
from src.utils.constants import TILE_SIZE


class TestTileCanvasWidget:
    """Tests for the TileCanvasWidget class."""
    
    def test_default_tileset_type(self, qtbot):
        """Canvas defaults to A5 tileset type."""
        canvas = TileCanvasWidget()
        qtbot.addWidget(canvas)
        
        assert canvas._tileset_type.name == "A5"
        assert canvas.width() == 384
        assert canvas.height() == 768
    
    def test_set_tileset_type_resizes(self, qtbot):
        """Setting tileset type resizes the canvas."""
        canvas = TileCanvasWidget()
        qtbot.addWidget(canvas)
        
        # Change to B type (768x768)
        canvas.set_tileset_type(TILESET_TYPES["B"])
        
        assert canvas.width() == 768
        assert canvas.height() == 768
    
    def test_grid_dimensions(self, qtbot):
        """Grid dimensions are calculated correctly."""
        canvas = TileCanvasWidget()
        qtbot.addWidget(canvas)
        
        # A5: 384x768 -> 8x16 grid
        assert canvas.grid_width == 8
        assert canvas.grid_height == 16
        
        # Change to A3: 768x384 -> 16x8 grid
        canvas.set_tileset_type(TILESET_TYPES["A3"])
        assert canvas.grid_width == 16
        assert canvas.grid_height == 8
    
    def test_cell_clicked_signal(self, qtbot):
        """Clicking emits cell_clicked signal with grid coordinates."""
        canvas = TileCanvasWidget()
        qtbot.addWidget(canvas)
        canvas.show()
        
        clicked_cells = []
        canvas.cell_clicked.connect(lambda x, y: clicked_cells.append((x, y)))
        
        # Click at pixel (50, 100) -> grid cell (1, 2)
        qtbot.mouseClick(canvas, Qt.MouseButton.LeftButton, pos=canvas.rect().topLeft() + 
                         type(canvas.rect().topLeft())(50, 100))
        
        assert len(clicked_cells) == 1
        assert clicked_cells[0] == (1, 2)
    
    def test_all_tileset_types(self, qtbot):
        """Canvas can display all tileset types."""
        canvas = TileCanvasWidget()
        qtbot.addWidget(canvas)
        
        expected_sizes = {
            "A2": (768, 576),
            "A3": (768, 384),
            "A4": (768, 720),
            "A5": (384, 768),
            "B": (768, 768),
        }
        
        for type_name, (expected_w, expected_h) in expected_sizes.items():
            canvas.set_tileset_type(TILESET_TYPES[type_name])
            assert canvas.width() == expected_w, f"{type_name} width"
            assert canvas.height() == expected_h, f"{type_name} height"


class TestTileCanvas:
    """Tests for the TileCanvas scroll area wrapper."""
    
    def test_contains_canvas_widget(self, qtbot):
        """TileCanvas contains a TileCanvasWidget."""
        canvas = TileCanvas()
        qtbot.addWidget(canvas)
        
        assert isinstance(canvas.canvas, TileCanvasWidget)
    
    def test_set_type_by_name(self, qtbot):
        """Can set tileset type by name string."""
        canvas = TileCanvas()
        qtbot.addWidget(canvas)
        
        canvas.set_tileset_type_by_name("B")
        
        assert canvas.tileset_type.name == "B"
        assert canvas.canvas.width() == 768
        assert canvas.canvas.height() == 768
    
    def test_cell_clicked_forwarded(self, qtbot):
        """cell_clicked signal is forwarded from inner canvas."""
        canvas = TileCanvas()
        qtbot.addWidget(canvas)
        
        clicked_cells = []
        canvas.cell_clicked.connect(lambda x, y: clicked_cells.append((x, y)))
        
        # Emit from inner canvas
        canvas.canvas.cell_clicked.emit(3, 5)
        
        assert len(clicked_cells) == 1
        assert clicked_cells[0] == (3, 5)


class TestTilePlacement:
    """Tests for tile placement functionality."""
    
    def _create_mock_unit(self, grid_width: int = 1, grid_height: int = 1) -> TileUnit:
        """Create a mock tile unit for testing."""
        tiles = []
        index = 0
        for dy in range(grid_height):
            for dx in range(grid_width):
                # Create a simple colored image
                img = QImage(TILE_SIZE, TILE_SIZE, QImage.Format.Format_ARGB32)
                img.fill(Qt.GlobalColor.red)
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
        # Link tiles to unit
        for tile in tiles:
            tile.unit = unit
        
        return unit
    
    def test_place_single_tile_unit(self, qtbot):
        """Can place a 1x1 unit on the canvas."""
        canvas = TileCanvasWidget()
        qtbot.addWidget(canvas)
        
        unit = self._create_mock_unit(1, 1)
        canvas.place_unit(unit, 0, 0)
        
        assert len(canvas._placed_units) == 1
        assert (0, 0) in canvas._placed_units
        assert canvas._placed_units[(0, 0)] is unit
    
    def test_place_multi_tile_unit(self, qtbot):
        """Can place a 2x2 unit on the canvas."""
        canvas = TileCanvasWidget()
        qtbot.addWidget(canvas)
        
        unit = self._create_mock_unit(2, 2)
        canvas.place_unit(unit, 3, 4)
        
        assert len(canvas._placed_units) == 1
        assert (3, 4) in canvas._placed_units
    
    def test_place_unit_emits_signal(self, qtbot):
        """Placing a unit emits unit_placed signal."""
        canvas = TileCanvasWidget()
        qtbot.addWidget(canvas)
        
        placed = []
        canvas.unit_placed.connect(lambda u, x, y: placed.append((u, x, y)))
        
        unit = self._create_mock_unit(1, 1)
        canvas.place_unit(unit, 2, 3)
        
        assert len(placed) == 1
        assert placed[0][0] is unit
        assert placed[0][1] == 2
        assert placed[0][2] == 3
    
    def test_place_unit_overwrites_existing(self, qtbot):
        """Placing a unit overwrites any existing unit at that position."""
        canvas = TileCanvasWidget()
        qtbot.addWidget(canvas)
        
        unit1 = self._create_mock_unit(1, 1)
        unit2 = self._create_mock_unit(1, 1)
        
        canvas.place_unit(unit1, 0, 0)
        canvas.place_unit(unit2, 0, 0)
        
        assert len(canvas._placed_units) == 1
        assert canvas._placed_units[(0, 0)] is unit2
    
    def test_place_large_unit_removes_overlapped(self, qtbot):
        """Placing a large unit removes smaller units it overlaps."""
        canvas = TileCanvasWidget()
        qtbot.addWidget(canvas)
        
        # Place small units
        small1 = self._create_mock_unit(1, 1)
        small2 = self._create_mock_unit(1, 1)
        canvas.place_unit(small1, 0, 0)
        canvas.place_unit(small2, 1, 1)
        
        assert len(canvas._placed_units) == 2
        
        # Place large 2x2 unit that covers both
        large = self._create_mock_unit(2, 2)
        canvas.place_unit(large, 0, 0)
        
        # Small units should be removed
        assert len(canvas._placed_units) == 1
        assert canvas._placed_units[(0, 0)] is large
    
    def test_clear_removes_all_units(self, qtbot):
        """Clear removes all placed units."""
        canvas = TileCanvasWidget()
        qtbot.addWidget(canvas)
        
        unit1 = self._create_mock_unit(1, 1)
        unit2 = self._create_mock_unit(1, 1)
        canvas.place_unit(unit1, 0, 0)
        canvas.place_unit(unit2, 3, 3)
        
        assert len(canvas._placed_units) == 2
        
        canvas.clear()
        
        assert len(canvas._placed_units) == 0
    
    def test_changing_tileset_type_clears_canvas(self, qtbot):
        """Changing tileset type clears all placed units."""
        canvas = TileCanvasWidget()
        qtbot.addWidget(canvas)
        
        unit = self._create_mock_unit(1, 1)
        canvas.place_unit(unit, 0, 0)
        
        assert len(canvas._placed_units) == 1
        
        canvas.set_tileset_type(TILESET_TYPES["B"])
        
        assert len(canvas._placed_units) == 0
    
    def test_is_empty(self, qtbot):
        """is_empty returns correct state."""
        canvas = TileCanvasWidget()
        qtbot.addWidget(canvas)
        
        assert canvas.is_empty() is True
        
        unit = self._create_mock_unit(1, 1)
        canvas.place_unit(unit, 0, 0)
        
        assert canvas.is_empty() is False
        
        canvas.clear()
        
        assert canvas.is_empty() is True
    
    def test_render_to_image_size(self, qtbot):
        """render_to_image creates pixmap with correct dimensions."""
        canvas = TileCanvasWidget()
        qtbot.addWidget(canvas)
        
        # Default is A5: 384x768
        pixmap = canvas.render_to_image()
        assert pixmap.width() == 384
        assert pixmap.height() == 768
        
        # Change to B: 768x768
        canvas.set_tileset_type(TILESET_TYPES["B"])
        pixmap = canvas.render_to_image()
        assert pixmap.width() == 768
        assert pixmap.height() == 768
    
    def test_render_to_image_transparent_when_empty(self, qtbot):
        """Empty canvas renders as fully transparent."""
        canvas = TileCanvasWidget()
        qtbot.addWidget(canvas)
        
        pixmap = canvas.render_to_image()
        image = pixmap.toImage()
        
        # Check that pixel at (0,0) is transparent
        pixel = image.pixelColor(0, 0)
        assert pixel.alpha() == 0
    
    def test_placed_unit_count(self, qtbot):
        """placed_unit_count returns correct count."""
        canvas = TileCanvasWidget()
        qtbot.addWidget(canvas)
        
        assert canvas.placed_unit_count == 0
        
        unit1 = self._create_mock_unit(1, 1)
        canvas.place_unit(unit1, 0, 0)
        assert canvas.placed_unit_count == 1
        
        unit2 = self._create_mock_unit(1, 1)
        canvas.place_unit(unit2, 1, 0)
        assert canvas.placed_unit_count == 2


class TestDropValidation:
    """Tests for unit drop position validation."""
    
    def _create_mock_unit(self, grid_width: int = 1, grid_height: int = 1) -> TileUnit:
        """Create a mock tile unit for testing."""
        tiles = []
        index = 0
        for dy in range(grid_height):
            for dx in range(grid_width):
                img = QImage(TILE_SIZE, TILE_SIZE, QImage.Format.Format_ARGB32)
                img.fill(Qt.GlobalColor.red)
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

    def test_a5_accepts_1x1_at_any_grid_position(self, qtbot):
        """A5 tileset (1x1 units) accepts drops at any grid position."""
        canvas = TileCanvasWidget()
        qtbot.addWidget(canvas)
        canvas.set_tileset_type(TILESET_TYPES["A5"])
        
        unit = self._create_mock_unit(1, 1)
        
        # A5 is 8x16 grid of 1x1 units
        assert canvas._is_valid_drop_position(0, 0, unit) is True
        assert canvas._is_valid_drop_position(7, 15, unit) is True
        assert canvas._is_valid_drop_position(3, 8, unit) is True

    def test_a5_rejects_2x2_unit(self, qtbot):
        """A5 tileset rejects 2x2 units (wrong size)."""
        canvas = TileCanvasWidget()
        qtbot.addWidget(canvas)
        canvas.set_tileset_type(TILESET_TYPES["A5"])
        
        unit = self._create_mock_unit(2, 2)
        
        # No valid position for 2x2 in A5
        assert canvas._is_valid_drop_position(0, 0, unit) is False
        assert canvas._snap_to_valid_position(0, 0, unit) is None

    def test_a3_accepts_2x2_at_unit_boundaries(self, qtbot):
        """A3 tileset accepts 2x2 units at correct boundaries."""
        canvas = TileCanvasWidget()
        qtbot.addWidget(canvas)
        canvas.set_tileset_type(TILESET_TYPES["A3"])
        
        unit = self._create_mock_unit(2, 2)
        
        # A3: 768x384, 2x2 units -> unit positions at (0,0), (2,0), (4,0), etc.
        assert canvas._is_valid_drop_position(0, 0, unit) is True
        assert canvas._is_valid_drop_position(2, 0, unit) is True
        assert canvas._is_valid_drop_position(0, 2, unit) is True

    def test_a3_rejects_2x2_at_wrong_position(self, qtbot):
        """A3 tileset rejects 2x2 units at non-boundary positions."""
        canvas = TileCanvasWidget()
        qtbot.addWidget(canvas)
        canvas.set_tileset_type(TILESET_TYPES["A3"])
        
        unit = self._create_mock_unit(2, 2)
        
        # (1, 0) is not a valid unit boundary
        assert canvas._is_valid_drop_position(1, 0, unit) is False
        assert canvas._is_valid_drop_position(0, 1, unit) is False

    def test_a3_rejects_1x1_unit(self, qtbot):
        """A3 tileset rejects 1x1 units (wrong size)."""
        canvas = TileCanvasWidget()
        qtbot.addWidget(canvas)
        canvas.set_tileset_type(TILESET_TYPES["A3"])
        
        unit = self._create_mock_unit(1, 1)
        
        assert canvas._is_valid_drop_position(0, 0, unit) is False
        assert canvas._snap_to_valid_position(0, 0, unit) is None

    def test_a2_accepts_2x3_at_unit_boundaries(self, qtbot):
        """A2 tileset accepts 2x3 units at correct boundaries."""
        canvas = TileCanvasWidget()
        qtbot.addWidget(canvas)
        canvas.set_tileset_type(TILESET_TYPES["A2"])
        
        unit = self._create_mock_unit(2, 3)
        
        # A2: 768x576, 2x3 units
        assert canvas._is_valid_drop_position(0, 0, unit) is True
        assert canvas._is_valid_drop_position(2, 0, unit) is True
        assert canvas._is_valid_drop_position(0, 3, unit) is True

    def test_a2_rejects_2x2_unit(self, qtbot):
        """A2 tileset rejects 2x2 units (wrong size)."""
        canvas = TileCanvasWidget()
        qtbot.addWidget(canvas)
        canvas.set_tileset_type(TILESET_TYPES["A2"])
        
        unit = self._create_mock_unit(2, 2)
        
        assert canvas._is_valid_drop_position(0, 0, unit) is False
        assert canvas._snap_to_valid_position(0, 0, unit) is None

    def test_snap_to_valid_finds_nearest(self, qtbot):
        """_snap_to_valid_position finds the nearest valid position."""
        canvas = TileCanvasWidget()
        qtbot.addWidget(canvas)
        canvas.set_tileset_type(TILESET_TYPES["A3"])
        
        unit = self._create_mock_unit(2, 2)
        
        # Hovering at (1, 0) should snap to (0, 0) or (2, 0)
        pos = canvas._snap_to_valid_position(1, 0, unit)
        assert pos in [(0, 0), (2, 0)]
        
        # Hovering at (3, 1) should snap to (2, 0) or (4, 0) or (2, 2) or (4, 2)
        pos = canvas._snap_to_valid_position(3, 1, unit)
        assert pos is not None
        assert canvas._is_valid_drop_position(pos[0], pos[1], unit) is True

    def test_b_type_accepts_1x1_only(self, qtbot):
        """B/C/D/E tilesets accept only 1x1 units."""
        canvas = TileCanvasWidget()
        qtbot.addWidget(canvas)
        canvas.set_tileset_type(TILESET_TYPES["B"])
        
        unit_1x1 = self._create_mock_unit(1, 1)
        unit_2x2 = self._create_mock_unit(2, 2)
        
        assert canvas._is_valid_drop_position(0, 0, unit_1x1) is True
        assert canvas._is_valid_drop_position(0, 0, unit_2x2) is False

    def test_unit_positions_cache_updated(self, qtbot):
        """Unit positions cache is updated when tileset type changes."""
        canvas = TileCanvasWidget()
        qtbot.addWidget(canvas)
        
        # A5 default
        a5_positions = canvas._unit_positions.copy()
        
        # Change to A3
        canvas.set_tileset_type(TILESET_TYPES["A3"])
        a3_positions = canvas._unit_positions
        
        # Positions should differ (A5 has 1x1, A3 has 2x2)
        assert a5_positions != a3_positions
        assert len(a5_positions) > 0
        assert len(a3_positions) > 0
