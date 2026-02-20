"""Tests for the ImageLoader service."""

import pytest
import tempfile
import os
from pathlib import Path

from PySide6.QtGui import QImage

from src.services.image_loader import ImageLoader
from src.models.tileset_types import TILESET_TYPES
from src.utils.constants import TILE_SIZE


class TestImageLoaderSimpleGrid:
    """Tests for simple grid extraction."""
    
    @pytest.fixture
    def temp_dir(self, qapp):
        """Create a temporary directory for test images."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    def _create_test_image(self, path: str, width: int, height: int):
        """Create a test PNG image with the given dimensions."""
        image = QImage(width, height, QImage.Format.Format_ARGB32)
        image.fill(0xFF00FF00)  # Green
        image.save(path, "PNG")
        return path
    
    def test_load_single_tile_image(self, temp_dir):
        """Loading a 48x48 image should yield 1 tile."""
        path = self._create_test_image(
            os.path.join(temp_dir, "single.png"), 48, 48
        )
        tiles = ImageLoader.load_tiles_from_image(path)
        
        assert len(tiles) == 1
        assert tiles[0].width == 48
        assert tiles[0].height == 48
        assert tiles[0].x == 0
        assert tiles[0].y == 0
    
    def test_load_2x2_grid(self, temp_dir):
        """Loading a 96x96 image should yield 4 tiles in row order."""
        path = self._create_test_image(
            os.path.join(temp_dir, "grid2x2.png"), 96, 96
        )
        tiles = ImageLoader.load_tiles_from_image(path)
        
        assert len(tiles) == 4
        # Check positions (row-by-row order)
        assert (tiles[0].x, tiles[0].y) == (0, 0)
        assert (tiles[1].x, tiles[1].y) == (48, 0)
        assert (tiles[2].x, tiles[2].y) == (0, 48)
        assert (tiles[3].x, tiles[3].y) == (48, 48)
    
    def test_load_a5_dimensions(self, temp_dir):
        """Loading an A5-sized image (384x768) should yield 128 tiles."""
        path = self._create_test_image(
            os.path.join(temp_dir, "a5.png"), 384, 768
        )
        tiles = ImageLoader.load_tiles_from_image(path)
        
        assert len(tiles) == 128  # 8 cols × 16 rows
    
    def test_source_index_increments(self, temp_dir):
        """Each tile should have a unique sequential source_index."""
        path = self._create_test_image(
            os.path.join(temp_dir, "grid.png"), 192, 192
        )
        tiles = ImageLoader.load_tiles_from_image(path)
        
        indices = [t.source_index for t in tiles]
        assert indices == list(range(16))  # 4x4 = 16 tiles

    def test_16_column_image_row_order(self, temp_dir):
        """16-column images should use standard row-by-row order."""
        # 16 cols × 2 rows = 32 tiles
        path = self._create_test_image(
            os.path.join(temp_dir, "wide.png"), 768, 96
        )
        tiles = ImageLoader.load_tiles_from_image(path)
        
        assert len(tiles) == 32
        
        # Should be row-by-row order
        # Row 0: tiles 0-15
        for i in range(16):
            assert tiles[i].x == i * 48, f"Tile {i} x mismatch"
            assert tiles[i].y == 0, f"Tile {i} y mismatch"
        
        # Row 1: tiles 16-31
        for i in range(16):
            assert tiles[16 + i].x == i * 48, f"Tile {16+i} x mismatch"
            assert tiles[16 + i].y == 48, f"Tile {16+i} y mismatch"


class TestImageLoaderFolder:
    """Tests for folder-based image loading."""
    
    @pytest.fixture
    def temp_dir(self, qapp):
        """Create a temporary directory with test images."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a few test images
            for name in ["a.png", "b.png"]:
                image = QImage(96, 96, QImage.Format.Format_ARGB32)
                image.fill(0xFFFF00FF)
                image.save(os.path.join(tmpdir, name), "PNG")
            yield tmpdir
    
    def test_find_images_in_folder(self, temp_dir):
        """Should find all PNG files in folder."""
        images = ImageLoader.find_images_in_folder(temp_dir)
        
        assert len(images) == 2
        assert all(p.endswith('.png') for p in images)
    
    def test_load_folder_as_simple_tiles(self, temp_dir):
        """Should load tiles from all images in folder."""
        tiles = ImageLoader.load_folder_as_simple_tiles(temp_dir)
        
        # Each 96x96 image has 4 tiles, 2 images = 8 tiles
        assert len(tiles) == 8
    
    def test_empty_folder_returns_empty_list(self, temp_dir):
        """Empty folder should return empty list."""
        empty_dir = os.path.join(temp_dir, "empty")
        os.makedirs(empty_dir)
        
        images = ImageLoader.find_images_in_folder(empty_dir)
        assert images == []
        
        tiles = ImageLoader.load_folder_as_simple_tiles(empty_dir)
        assert tiles == []
    
    def test_nonexistent_folder_returns_empty_list(self, qapp):
        """Non-existent folder should return empty list."""
        images = ImageLoader.find_images_in_folder("/nonexistent/path")
        assert images == []


class TestImageLoaderWithTilesetType:
    """Tests for tileset-type-aware extraction."""
    
    @pytest.fixture
    def temp_dir(self, qapp):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    def _create_test_image(self, path: str, width: int, height: int):
        image = QImage(width, height, QImage.Format.Format_ARGB32)
        image.fill(0xFF888888)
        image.save(path, "PNG")
        return path
    
    def test_extract_with_a5_type(self, temp_dir):
        """Extracting with A5 type should use A5 unit positions."""
        path = self._create_test_image(
            os.path.join(temp_dir, "a5.png"), 384, 768
        )
        tileset_type = TILESET_TYPES["A5"]
        tiles = ImageLoader.load_tiles_from_image(path, tileset_type)
        
        assert len(tiles) == 128
        # All tiles should be 48x48
        assert all(t.width == 48 and t.height == 48 for t in tiles)
    
    def test_extract_with_a3_type_returns_tiles(self, temp_dir):
        """Extracting A3 with load_tiles_from_image returns individual 48x48 tiles."""
        path = self._create_test_image(
            os.path.join(temp_dir, "a3.png"), 768, 384
        )
        tileset_type = TILESET_TYPES["A3"]
        tiles = ImageLoader.load_tiles_from_image(path, tileset_type)
        
        # A3 is 16x8 = 128 tiles, grouped into 32 units of 2x2
        assert len(tiles) == 128
        # All tiles should be 48x48
        assert all(t.width == 48 and t.height == 48 for t in tiles)
    
    def test_extract_with_a3_type_returns_units(self, temp_dir):
        """Extracting A3 with load_units_from_image returns 2x2 units."""
        path = self._create_test_image(
            os.path.join(temp_dir, "a3.png"), 768, 384
        )
        tileset_type = TILESET_TYPES["A3"]
        units = ImageLoader.load_units_from_image(path, tileset_type)
        
        # A3 has 32 units (8 cols × 4 rows)
        assert len(units) == 32
        # All units should be 2×2 tiles (96×96 pixels)
        assert all(u.grid_width == 2 and u.grid_height == 2 for u in units)
        assert all(u.pixel_width == 96 and u.pixel_height == 96 for u in units)
        # Each unit should have 4 tiles
        assert all(len(u.tiles) == 4 for u in units)


class TestA3AutoDetection:
    """Tests for automatic A3 format detection based on image dimensions."""
    
    @pytest.fixture
    def temp_dir(self, qapp):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    def _create_test_image(self, path: str, width: int, height: int):
        image = QImage(width, height, QImage.Format.Format_ARGB32)
        image.fill(0xFF00FFFF)  # Cyan
        image.save(path, "PNG")
        return path
    
    def test_768x384_auto_detects_as_a3_units(self, temp_dir):
        """An image with A3 dimensions should auto-detect as A3 format."""
        path = self._create_test_image(
            os.path.join(temp_dir, "auto_a3.png"), 768, 384
        )
        # Load without specifying tileset type - should auto-detect
        units = ImageLoader.load_units_from_image(path)
        
        # Should have 32 units (A3 format: 8 cols × 4 rows of 2×2 units)
        assert len(units) == 32
        
        # All units should be 2×2 tiles (96×96 pixels)
        assert all(u.grid_width == 2 and u.grid_height == 2 for u in units)
    
    def test_768x384_returns_tiles_for_legacy(self, temp_dir):
        """load_tiles_from_image returns individual tiles for A3."""
        path = self._create_test_image(
            os.path.join(temp_dir, "auto_a3.png"), 768, 384
        )
        tiles = ImageLoader.load_tiles_from_image(path)
        
        # Should have 128 tiles (16×8 grid of 48×48)
        assert len(tiles) == 128
        assert all(t.width == 48 and t.height == 48 for t in tiles)
    
    def test_a3_units_have_correct_positions(self, temp_dir):
        """A3 units should have tiles at correct positions."""
        path = self._create_test_image(
            os.path.join(temp_dir, "a3_positions.png"), 768, 384
        )
        units = ImageLoader.load_units_from_image(path)
        
        # First unit at (0, 0) - top-left tile of the unit
        assert units[0].tiles[0].x == 0
        assert units[0].tiles[0].y == 0
        # First unit's top-right tile
        assert units[0].tiles[1].x == 48
        assert units[0].tiles[1].y == 0
        
        # Second unit starts at x=96 (one unit to the right)
        assert units[1].tiles[0].x == 96
        assert units[1].tiles[0].y == 0
        
        # 8th unit (index 7) starts at (7*96, 0) = (672, 0)
        assert units[7].tiles[0].x == 672
        assert units[7].tiles[0].y == 0
        
        # 9th unit (index 8) is first of second row: (0, 96)
        assert units[8].tiles[0].x == 0
        assert units[8].tiles[0].y == 96
    
    def test_similar_but_different_dimensions_uses_simple_grid(self, temp_dir):
        """Images with similar but not exact A3 dimensions should use simple grid."""
        # Close to A3 but not exact
        path = self._create_test_image(
            os.path.join(temp_dir, "not_a3.png"), 768, 380
        )
        tiles = ImageLoader.load_tiles_from_image(path)
        
        # Should use simple grid: 768/48=16 cols, 380/48=7 rows (with remainder ignored)
        # Simple grid extracts 48×48 tiles
        assert all(t.width == 48 and t.height == 48 for t in tiles)
    
    def test_a3_loads_via_load_units_from_images(self, temp_dir):
        """A3 format should work through the load_units_from_images method."""
        path = self._create_test_image(
            os.path.join(temp_dir, "a3_via_method.png"), 768, 384
        )
        units = ImageLoader.load_units_from_images([path])
        
        assert len(units) == 32
        assert all(u.grid_width == 2 and u.grid_height == 2 for u in units)
    
    def test_a3_loads_via_load_units_from_folder(self, temp_dir):
        """A3 format should work through the load_units_from_folder method."""
        self._create_test_image(
            os.path.join(temp_dir, "folder_a3.png"), 768, 384
        )
        units = ImageLoader.load_units_from_folder(temp_dir)
        
        assert len(units) == 32
        assert all(u.grid_width == 2 and u.grid_height == 2 for u in units)


class TestA2AutoDetection:
    """Tests for automatic A2 format detection based on image dimensions."""
    
    @pytest.fixture
    def temp_dir(self, qapp):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    def _create_test_image(self, path: str, width: int, height: int):
        image = QImage(width, height, QImage.Format.Format_ARGB32)
        image.fill(0xFF00FF00)  # Green
        image.save(path, "PNG")
        return path
    
    def test_768x576_auto_detects_as_a2_units(self, temp_dir):
        """An image with A2 dimensions should auto-detect as A2 format."""
        path = self._create_test_image(
            os.path.join(temp_dir, "auto_a2.png"), 768, 576
        )
        # Load without specifying tileset type - should auto-detect
        units = ImageLoader.load_units_from_image(path)
        
        # A2 has 32 units (8 cols × 4 rows of 2×3 units)
        assert len(units) == 32
        
        # All units should be 2×3 tiles (96×144 pixels)
        assert all(u.grid_width == 2 and u.grid_height == 3 for u in units)
        assert all(u.pixel_width == 96 and u.pixel_height == 144 for u in units)
    
    def test_a2_units_have_correct_tile_count(self, temp_dir):
        """Each A2 unit should contain 6 tiles (2×3)."""
        path = self._create_test_image(
            os.path.join(temp_dir, "a2_tiles.png"), 768, 576
        )
        units = ImageLoader.load_units_from_image(path)
        
        # Each 2×3 unit should have 6 tiles
        assert all(len(u.tiles) == 6 for u in units)
    
    def test_a2_units_have_correct_positions(self, temp_dir):
        """A2 units should have tiles at correct positions."""
        path = self._create_test_image(
            os.path.join(temp_dir, "a2_positions.png"), 768, 576
        )
        units = ImageLoader.load_units_from_image(path)
        
        # First unit at (0, 0)
        assert units[0].tiles[0].x == 0
        assert units[0].tiles[0].y == 0
        
        # First unit's tiles in row-major order: (0,0), (48,0), (0,48), (48,48), (0,96), (48,96)
        assert units[0].tiles[1].x == 48
        assert units[0].tiles[1].y == 0
        assert units[0].tiles[2].x == 0
        assert units[0].tiles[2].y == 48
        
        # Second unit starts at x=96 (one unit to the right)
        assert units[1].tiles[0].x == 96
        assert units[1].tiles[0].y == 0
        
        # 8th unit (index 7) starts at (7*96, 0) = (672, 0)
        assert units[7].tiles[0].x == 672
        assert units[7].tiles[0].y == 0
        
        # 9th unit (index 8) is first of second row: (0, 144)
        assert units[8].tiles[0].x == 0
        assert units[8].tiles[0].y == 144
    
    def test_a2_returns_tiles_for_legacy(self, temp_dir):
        """load_tiles_from_image returns individual tiles for A2."""
        path = self._create_test_image(
            os.path.join(temp_dir, "a2_legacy.png"), 768, 576
        )
        tiles = ImageLoader.load_tiles_from_image(path)
        
        # Should have 192 tiles (16×12 grid of 48×48)
        assert len(tiles) == 192
        assert all(t.width == 48 and t.height == 48 for t in tiles)
