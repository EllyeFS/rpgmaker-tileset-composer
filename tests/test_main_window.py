"""Tests for the MainWindow UI behavior."""

import pytest
import tempfile
import shutil
import os
from unittest.mock import patch, MagicMock

from PySide6.QtWidgets import QMessageBox
from PySide6.QtGui import QImage

from src.ui.main_window import MainWindow


def _count_tiles(palette):
    """Helper to count total tiles in palette (from all units)."""
    return sum(len(unit.tiles) for unit in palette._units)


def _get_tiles(palette):
    """Helper to get all tiles from palette (from all units)."""
    return [tile for unit in palette._units for tile in unit.tiles]


class TestFolderLoadingWarning:
    """Tests for the large folder warning dialog."""
    
    @pytest.fixture
    def main_window(self, qtbot):
        """Create a MainWindow instance for testing."""
        window = MainWindow()
        qtbot.addWidget(window)
        return window
    
    @pytest.fixture
    def small_folder(self, qapp):
        """Create a folder with 5 images (below threshold)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            for i in range(5):
                image = QImage(48, 48, QImage.Format.Format_ARGB32)
                image.fill(0xFF00FF00)
                image.save(os.path.join(tmpdir, f"tile_{i}.png"), "PNG")
            yield tmpdir
    
    @pytest.fixture
    def large_folder(self, qapp):
        """Create a folder with 16 images (above threshold of 15)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            for i in range(16):
                image = QImage(48, 48, QImage.Format.Format_ARGB32)
                image.fill(0xFFFF0000)
                image.save(os.path.join(tmpdir, f"tile_{i}.png"), "PNG")
            yield tmpdir
    
    def test_small_folder_loads_without_warning(self, main_window, small_folder):
        """Folders with <= 15 files should load without showing a warning."""
        with patch.object(QMessageBox, 'warning') as mock_warning:
            main_window._load_tiles_from_folder(small_folder)
            
            # Warning should not be called
            mock_warning.assert_not_called()
            
            # Tiles should be loaded
            assert _count_tiles(main_window.tile_palette) == 5
    
    def test_large_folder_shows_warning(self, main_window, large_folder):
        """Folders with > 15 files should show a warning dialog."""
        with patch.object(QMessageBox, 'warning', return_value=QMessageBox.StandardButton.Yes) as mock_warning:
            main_window._load_tiles_from_folder(large_folder)
            
            # Warning should be called once
            mock_warning.assert_called_once()
            
            # Check the warning message contains file count
            call_args = mock_warning.call_args
            message = call_args[0][2]  # Third positional arg is the message
            assert "16" in message
            assert "freeze" in message.lower() or "crash" in message.lower()
    
    def test_large_folder_cancelled_does_not_load(self, main_window, large_folder):
        """Clicking No on the warning should cancel loading."""
        with patch.object(QMessageBox, 'warning', return_value=QMessageBox.StandardButton.No):
            main_window._load_tiles_from_folder(large_folder)
            
            # Tiles should NOT be loaded
            assert _count_tiles(main_window.tile_palette) == 0
    
    def test_large_folder_confirmed_loads_tiles(self, main_window, large_folder):
        """Clicking Yes on the warning should proceed with loading."""
        with patch.object(QMessageBox, 'warning', return_value=QMessageBox.StandardButton.Yes):
            main_window._load_tiles_from_folder(large_folder)
            
            # Tiles should be loaded
            assert _count_tiles(main_window.tile_palette) == 16
    
    def test_exactly_15_files_no_warning(self, main_window, qapp):
        """Exactly 15 files should not trigger the warning (threshold is > 15)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            for i in range(15):
                image = QImage(48, 48, QImage.Format.Format_ARGB32)
                image.fill(0xFF0000FF)
                image.save(os.path.join(tmpdir, f"tile_{i}.png"), "PNG")
            
            with patch.object(QMessageBox, 'warning') as mock_warning:
                main_window._load_tiles_from_folder(tmpdir)
                
                mock_warning.assert_not_called()
                assert _count_tiles(main_window.tile_palette) == 15
    
    def test_exactly_16_files_shows_warning(self, main_window, qapp):
        """16 files should trigger the warning (threshold is > 15)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            for i in range(16):
                image = QImage(48, 48, QImage.Format.Format_ARGB32)
                image.fill(0xFF0000FF)
                image.save(os.path.join(tmpdir, f"tile_{i}.png"), "PNG")
            
            with patch.object(QMessageBox, 'warning', return_value=QMessageBox.StandardButton.Yes) as mock_warning:
                main_window._load_tiles_from_folder(tmpdir)
                
                mock_warning.assert_called_once()


class TestLoadMultipleImages:
    """Tests for loading individual image files."""
    
    @pytest.fixture
    def main_window(self, qtbot):
        """Create a MainWindow instance for testing."""
        window = MainWindow()
        qtbot.addWidget(window)
        return window
    
    def test_load_single_image(self, main_window, qapp):
        """Loading a single image should work without warning."""
        with tempfile.TemporaryDirectory() as tmpdir:
            image_path = os.path.join(tmpdir, "tile.png")
            image = QImage(48, 48, QImage.Format.Format_ARGB32)
            image.fill(0xFF00FF00)
            image.save(image_path, "PNG")
            
            with patch.object(QMessageBox, 'warning') as mock_warning:
                main_window._load_tiles_from_images([image_path])
                
                mock_warning.assert_not_called()
                assert _count_tiles(main_window.tile_palette) == 1
    
    def test_load_multiple_images(self, main_window, qapp):
        """Loading multiple images should combine their tiles."""
        with tempfile.TemporaryDirectory() as tmpdir:
            paths = []
            for i in range(3):
                path = os.path.join(tmpdir, f"tile_{i}.png")
                image = QImage(96, 96, QImage.Format.Format_ARGB32)  # 4 tiles each
                image.fill(0xFF00FF00)
                image.save(path, "PNG")
                paths.append(path)
            
            main_window._load_tiles_from_images(paths)
            
            # 3 images × 4 tiles each = 12 tiles
            assert _count_tiles(main_window.tile_palette) == 12
    
    def test_load_more_than_15_images_shows_warning(self, main_window, qapp):
        """Loading more than 15 images should show warning."""
        with tempfile.TemporaryDirectory() as tmpdir:
            paths = []
            for i in range(16):
                path = os.path.join(tmpdir, f"tile_{i}.png")
                image = QImage(48, 48, QImage.Format.Format_ARGB32)
                image.fill(0xFF00FF00)
                image.save(path, "PNG")
                paths.append(path)
            
            with patch.object(QMessageBox, 'warning', return_value=QMessageBox.StandardButton.Yes) as mock_warning:
                main_window._load_tiles_from_images(paths)
                
                mock_warning.assert_called_once()
                assert _count_tiles(main_window.tile_palette) == 16
    
    def test_cancel_large_image_load(self, main_window, qapp):
        """Cancelling large image load should not load tiles."""
        with tempfile.TemporaryDirectory() as tmpdir:
            paths = []
            for i in range(16):
                path = os.path.join(tmpdir, f"tile_{i}.png")
                image = QImage(48, 48, QImage.Format.Format_ARGB32)
                image.fill(0xFF00FF00)
                image.save(path, "PNG")
                paths.append(path)
            
            with patch.object(QMessageBox, 'warning', return_value=QMessageBox.StandardButton.No):
                main_window._load_tiles_from_images(paths)
                
                assert _count_tiles(main_window.tile_palette) == 0


class TestAppendToPalette:
    """Tests for the append to palette checkbox functionality."""
    
    @pytest.fixture
    def main_window(self, qtbot):
        """Create a MainWindow instance for testing."""
        window = MainWindow()
        qtbot.addWidget(window)
        return window
    
    def test_append_unchecked_replaces_tiles(self, main_window, qapp):
        """With append unchecked, loading should replace existing tiles."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Load first batch
            path1 = os.path.join(tmpdir, "tile1.png")
            image = QImage(48, 48, QImage.Format.Format_ARGB32)
            image.fill(0xFF00FF00)
            image.save(path1, "PNG")
            
            main_window.append_checkbox.setChecked(False)
            main_window._load_tiles_from_images([path1])
            assert _count_tiles(main_window.tile_palette) == 1
            
            # Load second batch - should replace
            path2 = os.path.join(tmpdir, "tile2.png")
            image2 = QImage(96, 96, QImage.Format.Format_ARGB32)  # 4 tiles
            image2.fill(0xFFFF0000)
            image2.save(path2, "PNG")
            
            main_window._load_tiles_from_images([path2])
            assert _count_tiles(main_window.tile_palette) == 4
    
    def test_append_checked_adds_to_top(self, main_window, qapp):
        """With append checked, loading should prepend new tiles."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Load first batch
            path1 = os.path.join(tmpdir, "first.png")
            image1 = QImage(48, 48, QImage.Format.Format_ARGB32)
            image1.fill(0xFF00FF00)
            image1.save(path1, "PNG")
            
            main_window.append_checkbox.setChecked(False)
            main_window._load_tiles_from_images([path1])
            assert _count_tiles(main_window.tile_palette) == 1
            tiles = _get_tiles(main_window.tile_palette)
            first_tile_source = tiles[0].source_name
            
            # Load second batch with append checked
            path2 = os.path.join(tmpdir, "second.png")
            image2 = QImage(96, 96, QImage.Format.Format_ARGB32)  # 4 tiles
            image2.fill(0xFFFF0000)
            image2.save(path2, "PNG")
            
            main_window.append_checkbox.setChecked(True)
            main_window._load_tiles_from_images([path2])
            
            # Should have 5 tiles total (1 + 4)
            assert _count_tiles(main_window.tile_palette) == 5
            
            # New tiles should be at the top (prepended)
            tiles = _get_tiles(main_window.tile_palette)
            assert tiles[0].source_name == "second.png"
            # Old tile should still be there at the end
            assert tiles[4].source_name == "first.png"
    
    def test_append_works_with_folder_loading(self, main_window, qapp):
        """Append should also work when loading from folder."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create initial image
            path1 = os.path.join(tmpdir, "initial.png")
            image1 = QImage(48, 48, QImage.Format.Format_ARGB32)
            image1.fill(0xFF00FF00)
            image1.save(path1, "PNG")
            
            # Load it first
            main_window.append_checkbox.setChecked(False)
            main_window._load_tiles_from_folder(tmpdir)
            initial_count = _count_tiles(main_window.tile_palette)
            
            # Create second folder
            tmpdir2 = tempfile.mkdtemp()
            try:
                path2 = os.path.join(tmpdir2, "added.png")
                image2 = QImage(96, 96, QImage.Format.Format_ARGB32)
                image2.fill(0xFFFF0000)
                image2.save(path2, "PNG")
                
                # Load with append
                main_window.append_checkbox.setChecked(True)
                main_window._load_tiles_from_folder(tmpdir2)
                
                # Should have combined tiles
                assert _count_tiles(main_window.tile_palette) == initial_count + 4
            finally:
                shutil.rmtree(tmpdir2)


class TestDuplicateTileBehavior:
    """Tests for loading the same image multiple times."""
    
    @pytest.fixture
    def main_window(self, qtbot):
        window = MainWindow()
        qtbot.addWidget(window)
        return window
    
    def test_same_image_with_append_skips_duplicates(self, main_window, qapp):
        """Loading the same image twice with append should skip duplicates."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "tile.png")
            image = QImage(48, 48, QImage.Format.Format_ARGB32)
            image.fill(0xFF00FF00)
            image.save(path, "PNG")
            
            # Load first time
            main_window.append_checkbox.setChecked(False)
            main_window._load_tiles_from_images([path])
            assert _count_tiles(main_window.tile_palette) == 1
            
            # Load same image again with append
            main_window.append_checkbox.setChecked(True)
            main_window._load_tiles_from_images([path])
            
            # Duplicates should be skipped
            assert _count_tiles(main_window.tile_palette) == 1
    
    def test_different_images_with_append_adds_all(self, main_window, qapp):
        """Loading different images with append should add all of them."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path1 = os.path.join(tmpdir, "tile1.png")
            image1 = QImage(48, 48, QImage.Format.Format_ARGB32)
            image1.fill(0xFF00FF00)
            image1.save(path1, "PNG")
            
            path2 = os.path.join(tmpdir, "tile2.png")
            image2 = QImage(48, 48, QImage.Format.Format_ARGB32)
            image2.fill(0xFFFF0000)
            image2.save(path2, "PNG")
            
            # Load first image
            main_window.append_checkbox.setChecked(False)
            main_window._load_tiles_from_images([path1])
            assert _count_tiles(main_window.tile_palette) == 1
            
            # Load different image with append
            main_window.append_checkbox.setChecked(True)
            main_window._load_tiles_from_images([path2])
            
            # Both should be present
            assert _count_tiles(main_window.tile_palette) == 2
    
    def test_mixed_new_and_existing_images(self, main_window, qapp):
        """Loading a mix of new and existing images should only add new ones."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path1 = os.path.join(tmpdir, "existing.png")
            image1 = QImage(48, 48, QImage.Format.Format_ARGB32)
            image1.fill(0xFF00FF00)
            image1.save(path1, "PNG")
            
            path2 = os.path.join(tmpdir, "new.png")
            image2 = QImage(48, 48, QImage.Format.Format_ARGB32)
            image2.fill(0xFFFF0000)
            image2.save(path2, "PNG")
            
            # Load first image
            main_window.append_checkbox.setChecked(False)
            main_window._load_tiles_from_images([path1])
            assert _count_tiles(main_window.tile_palette) == 1
            
            # Load both (one existing, one new) with append
            main_window.append_checkbox.setChecked(True)
            main_window._load_tiles_from_images([path1, path2])
            
            # Should have 2 tiles (existing + new, no duplicate of existing)
            assert _count_tiles(main_window.tile_palette) == 2
