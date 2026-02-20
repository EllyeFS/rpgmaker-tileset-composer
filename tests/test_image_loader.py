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


class TestImageLoaderBCDEOrdering:
    """Tests for BCDE-style half-column ordering."""
    
    @pytest.fixture
    def temp_dir(self, qapp):
        """Create a temporary directory for test images."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    def _create_test_image(self, path: str, width: int, height: int):
        """Create a test PNG image."""
        image = QImage(width, height, QImage.Format.Format_ARGB32)
        image.fill(0xFF0000FF)  # Blue
        image.save(path, "PNG")
        return path
    
    def test_bcde_16_column_ordering(self, temp_dir):
        """16-column images should extract left half first, then right half."""
        # 16 cols × 2 rows = 32 tiles
        path = self._create_test_image(
            os.path.join(temp_dir, "bcde.png"), 768, 96
        )
        tiles = ImageLoader.load_tiles_from_image(path)
        
        assert len(tiles) == 32
        
        # First 16 tiles should be left half (cols 0-7, both rows)
        # Row 0, cols 0-7
        for i in range(8):
            assert tiles[i].x == i * 48, f"Tile {i} x mismatch"
            assert tiles[i].y == 0, f"Tile {i} y mismatch"
        
        # Row 1, cols 0-7
        for i in range(8):
            assert tiles[8 + i].x == i * 48, f"Tile {8+i} x mismatch"
            assert tiles[8 + i].y == 48, f"Tile {8+i} y mismatch"
        
        # Next 16 tiles should be right half (cols 8-15, both rows)
        # Row 0, cols 8-15
        for i in range(8):
            assert tiles[16 + i].x == (8 + i) * 48, f"Tile {16+i} x mismatch"
            assert tiles[16 + i].y == 0, f"Tile {16+i} y mismatch"
        
        # Row 1, cols 8-15
        for i in range(8):
            assert tiles[24 + i].x == (8 + i) * 48, f"Tile {24+i} x mismatch"
            assert tiles[24 + i].y == 48, f"Tile {24+i} y mismatch"
    
    def test_full_bcde_image_256_tiles(self, temp_dir):
        """Full 768x768 BCDE image should yield 256 tiles in correct order."""
        path = self._create_test_image(
            os.path.join(temp_dir, "full_bcde.png"), 768, 768
        )
        tiles = ImageLoader.load_tiles_from_image(path)
        
        assert len(tiles) == 256
        
        # First 128 tiles are left half, next 128 are right half
        # Verify first tile of each half
        assert tiles[0].x == 0  # First tile of left half
        assert tiles[128].x == 8 * 48  # First tile of right half (col 8)
    
    def test_non_16_column_uses_row_order(self, temp_dir):
        """Images with != 16 columns should use standard row order."""
        # 8 cols × 2 rows = 16 tiles
        path = self._create_test_image(
            os.path.join(temp_dir, "a5_style.png"), 384, 96
        )
        tiles = ImageLoader.load_tiles_from_image(path)
        
        assert len(tiles) == 16
        
        # Should be row-by-row order
        assert (tiles[0].x, tiles[0].y) == (0, 0)
        assert (tiles[7].x, tiles[7].y) == (7 * 48, 0)
        assert (tiles[8].x, tiles[8].y) == (0, 48)


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
    
    def test_extract_with_a3_type(self, temp_dir):
        """Extracting with A3 type should yield 2x2 units."""
        path = self._create_test_image(
            os.path.join(temp_dir, "a3.png"), 768, 384
        )
        tileset_type = TILESET_TYPES["A3"]
        tiles = ImageLoader.load_tiles_from_image(path, tileset_type)
        
        assert len(tiles) == 32
        # All units should be 96x96 (2x2 tiles)
        assert all(t.width == 96 and t.height == 96 for t in tiles)
