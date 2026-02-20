"""Tests for the MainWindow UI behavior."""

import pytest
import tempfile
import os
from unittest.mock import patch, MagicMock

from PySide6.QtWidgets import QMessageBox
from PySide6.QtGui import QImage

from src.ui.main_window import MainWindow


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
        """Create a folder with 15 images (above threshold)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            for i in range(15):
                image = QImage(48, 48, QImage.Format.Format_ARGB32)
                image.fill(0xFFFF0000)
                image.save(os.path.join(tmpdir, f"tile_{i}.png"), "PNG")
            yield tmpdir
    
    def test_small_folder_loads_without_warning(self, main_window, small_folder):
        """Folders with <= 10 files should load without showing a warning."""
        with patch.object(QMessageBox, 'warning') as mock_warning:
            main_window._load_tiles_from_folder(small_folder)
            
            # Warning should not be called
            mock_warning.assert_not_called()
            
            # Tiles should be loaded
            assert len(main_window.tile_palette._tiles) == 5
    
    def test_large_folder_shows_warning(self, main_window, large_folder):
        """Folders with > 10 files should show a warning dialog."""
        with patch.object(QMessageBox, 'warning', return_value=QMessageBox.StandardButton.Yes) as mock_warning:
            main_window._load_tiles_from_folder(large_folder)
            
            # Warning should be called once
            mock_warning.assert_called_once()
            
            # Check the warning message contains file count
            call_args = mock_warning.call_args
            message = call_args[0][2]  # Third positional arg is the message
            assert "15" in message
            assert "freeze" in message.lower() or "crash" in message.lower()
    
    def test_large_folder_cancelled_does_not_load(self, main_window, large_folder):
        """Clicking No on the warning should cancel loading."""
        with patch.object(QMessageBox, 'warning', return_value=QMessageBox.StandardButton.No):
            main_window._load_tiles_from_folder(large_folder)
            
            # Tiles should NOT be loaded
            assert len(main_window.tile_palette._tiles) == 0
    
    def test_large_folder_confirmed_loads_tiles(self, main_window, large_folder):
        """Clicking Yes on the warning should proceed with loading."""
        with patch.object(QMessageBox, 'warning', return_value=QMessageBox.StandardButton.Yes):
            main_window._load_tiles_from_folder(large_folder)
            
            # Tiles should be loaded
            assert len(main_window.tile_palette._tiles) == 15
    
    def test_exactly_10_files_no_warning(self, main_window, qapp):
        """Exactly 10 files should not trigger the warning."""
        with tempfile.TemporaryDirectory() as tmpdir:
            for i in range(10):
                image = QImage(48, 48, QImage.Format.Format_ARGB32)
                image.fill(0xFF0000FF)
                image.save(os.path.join(tmpdir, f"tile_{i}.png"), "PNG")
            
            with patch.object(QMessageBox, 'warning') as mock_warning:
                main_window._load_tiles_from_folder(tmpdir)
                
                mock_warning.assert_not_called()
                assert len(main_window.tile_palette._tiles) == 10
    
    def test_exactly_11_files_shows_warning(self, main_window, qapp):
        """11 files should trigger the warning."""
        with tempfile.TemporaryDirectory() as tmpdir:
            for i in range(11):
                image = QImage(48, 48, QImage.Format.Format_ARGB32)
                image.fill(0xFF0000FF)
                image.save(os.path.join(tmpdir, f"tile_{i}.png"), "PNG")
            
            with patch.object(QMessageBox, 'warning', return_value=QMessageBox.StandardButton.Yes) as mock_warning:
                main_window._load_tiles_from_folder(tmpdir)
                
                mock_warning.assert_called_once()
