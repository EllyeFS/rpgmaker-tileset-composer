"""Tests for TileCanvas widget."""

import pytest
from PySide6.QtCore import Qt

from src.ui.tile_canvas import TileCanvas, TileCanvasWidget
from src.models.tileset_types import TILESET_TYPES
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
            "A1": (768, 576),
            "A2": (768, 576),
            "A3": (768, 384),
            "A4": (768, 720),
            "A5": (384, 768),
            "B": (768, 768),
            "C": (768, 768),
            "D": (768, 768),
            "E": (768, 768),
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
