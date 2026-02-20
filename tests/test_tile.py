"""Tests for the Tile model."""

import pytest
from PySide6.QtGui import QImage, QPixmap

from src.models.tile import Tile
from src.models.tile_unit import TileUnit


class TestTile:
    """Tests for Tile model."""
    
    @pytest.fixture
    def sample_image(self, qapp):
        """Create a simple 48x48 test image."""
        image = QImage(48, 48, QImage.Format.Format_ARGB32)
        image.fill(0xFFFF0000)  # Red
        return image
    
    @pytest.fixture
    def sample_tile(self, sample_image):
        """Create a sample tile for testing."""
        return Tile(
            source_path="/test/image.png",
            source_index=0,
            x=0,
            y=0,
            image=sample_image,
        )
    
    def test_tile_properties(self, sample_tile):
        """Tile should store all properties correctly."""
        assert sample_tile.source_path == "/test/image.png"
        assert sample_tile.source_index == 0
        assert sample_tile.x == 0
        assert sample_tile.y == 0
        # width and height are now computed properties (always 48)
        assert sample_tile.width == 48
        assert sample_tile.height == 48
    
    def test_source_name_extracts_filename(self, sample_tile):
        """source_name should return just the filename."""
        assert sample_tile.source_name == "image.png"
    
    def test_source_name_with_nested_path(self, sample_image):
        """source_name should work with deeply nested paths."""
        tile = Tile(
            source_path="/path/to/some/folder/tileset.png",
            source_index=0,
            x=0, y=0,
            image=sample_image,
        )
        assert tile.source_name == "tileset.png"
    
    def test_pixmap_returns_qpixmap(self, sample_tile):
        """pixmap property should return a QPixmap."""
        pixmap = sample_tile.pixmap
        assert isinstance(pixmap, QPixmap)
        assert pixmap.width() == 48
        assert pixmap.height() == 48
    
    def test_pixmap_is_cached(self, sample_tile):
        """pixmap should be cached after first access."""
        pixmap1 = sample_tile.pixmap
        pixmap2 = sample_tile.pixmap
        # Should be the exact same object
        assert pixmap1 is pixmap2
    
    def test_tile_unit_reference(self, sample_image):
        """Tile can reference its parent TileUnit."""
        tile = Tile(
            source_path="/test/image.png",
            source_index=0,
            x=0, y=0,
            image=sample_image,
        )
        assert tile.unit is None
        
        unit = TileUnit(grid_width=1, grid_height=1, tiles=[tile])
        tile.unit = unit
        
        assert tile.unit is unit


class TestTileUnit:
    """Tests for TileUnit model."""
    
    @pytest.fixture
    def sample_image(self, qapp):
        """Create a simple 48x48 test image."""
        image = QImage(48, 48, QImage.Format.Format_ARGB32)
        image.fill(0xFF00FF00)  # Green
        return image
    
    def test_single_tile_unit(self, sample_image):
        """A 1×1 unit contains a single tile."""
        tile = Tile(
            source_path="/test/image.png",
            source_index=0,
            x=0, y=0,
            image=sample_image,
        )
        unit = TileUnit(grid_width=1, grid_height=1, tiles=[tile])
        
        assert unit.is_single_tile
        assert len(unit.tiles) == 1
        assert unit.pixel_width == 48
        assert unit.pixel_height == 48
    
    def test_2x2_unit(self, sample_image):
        """A 2×2 unit contains 4 tiles arranged in a grid."""
        tiles = [
            Tile(source_path="/test.png", source_index=i, x=(i % 2) * 48, y=(i // 2) * 48, image=sample_image)
            for i in range(4)
        ]
        unit = TileUnit(grid_width=2, grid_height=2, tiles=tiles)
        
        assert not unit.is_single_tile
        assert len(unit.tiles) == 4
        assert unit.pixel_width == 96
        assert unit.pixel_height == 96
    
    def test_source_path_from_tiles(self, sample_image):
        """Unit source_path comes from its first tile."""
        tile = Tile(
            source_path="/my/tileset.png",
            source_index=0,
            x=0, y=0,
            image=sample_image,
        )
        unit = TileUnit(grid_width=1, grid_height=1, tiles=[tile])
        
        assert unit.source_path == "/my/tileset.png"
        assert unit.source_name == "tileset.png"
