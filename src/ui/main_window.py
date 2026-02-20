"""Main application window."""

from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QLabel,
    QComboBox,
    QPushButton,
    QFileDialog,
    QStatusBar,
    QMenuBar,
    QMenu,
    QMessageBox,
    QCheckBox,
    QProgressDialog,
    QApplication,
)
from PySide6.QtCore import Qt

from ..models import TILESET_TYPES
from ..models.tile import Tile
from ..models.tile_unit import TileUnit
from ..services.image_loader import ImageLoader
from .tile_palette import TilePalette
from .tile_canvas import TileCanvas
from .new_project_dialog import NewProjectDialog


class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RPG Maker MZ Tileset Composer")
        self.setMinimumSize(1200, 800)
        
        self._setup_menu_bar()
        self._setup_ui()
        self._setup_status_bar()
    
    def _setup_menu_bar(self):
        """Create the menu bar."""
        menu_bar = self.menuBar()
        
        # File menu
        file_menu = menu_bar.addMenu("&File")
        file_menu.addAction("&New Project", self._new_project)
        file_menu.addAction("&Open Project...", self._open_project)
        file_menu.addAction("&Save Project", self._save_project)
        file_menu.addSeparator()
        file_menu.addAction("&Export PNG...", self._export_png)
        file_menu.addSeparator()
        file_menu.addAction("E&xit", self.close)
        
        # Edit menu
        edit_menu = menu_bar.addMenu("&Edit")
        edit_menu.addAction("&Undo", self._undo)
        edit_menu.addAction("&Redo", self._redo)
        edit_menu.addSeparator()
        edit_menu.addAction("&Clear Canvas", self._clear_canvas)
        
        # View menu
        view_menu = menu_bar.addMenu("&View")
        view_menu.addAction("Zoom &In", self._zoom_in)
        view_menu.addAction("Zoom &Out", self._zoom_out)
        view_menu.addAction("&Reset Zoom", self._zoom_reset)
        
        # Help menu
        help_menu = menu_bar.addMenu("&Help")
        help_menu.addAction("&About", self._show_about)
    
    def _setup_ui(self):
        """Setup the main UI layout."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        
        # Toolbar area
        toolbar_layout = QHBoxLayout()
        
        # Individual image selector
        toolbar_layout.addWidget(QLabel("Source:"))
        self.load_images_btn = QPushButton("Load Images...")
        self.load_images_btn.clicked.connect(self._select_images)
        toolbar_layout.addWidget(self.load_images_btn)
        
        # Source folder selector
        self.source_folder_btn = QPushButton("Load Folder...")
        self.source_folder_btn.clicked.connect(self._select_source_folder)
        toolbar_layout.addWidget(self.source_folder_btn)
        
        # Append checkbox
        self.append_checkbox = QCheckBox("Append to palette")
        self.append_checkbox.setToolTip("Keep existing tiles and add new ones to the top")
        toolbar_layout.addWidget(self.append_checkbox)
        
        toolbar_layout.addSpacing(20)
        
        # New project button
        self.new_project_btn = QPushButton("New Project...")
        self.new_project_btn.clicked.connect(self._new_project)
        toolbar_layout.addWidget(self.new_project_btn)
        
        # Target type display (read-only)
        toolbar_layout.addSpacing(10)
        toolbar_layout.addWidget(QLabel("Target:"))
        self.target_type_label = QLabel("A5")
        self.target_type_label.setStyleSheet("font-weight: bold;")
        self._current_type_name = "A5"  # Track current type
        toolbar_layout.addWidget(self.target_type_label)
        
        toolbar_layout.addStretch()
        
        # Export button
        self.export_btn = QPushButton("Export PNG")
        self.export_btn.clicked.connect(self._export_png)
        toolbar_layout.addWidget(self.export_btn)
        
        main_layout.addLayout(toolbar_layout)
        
        # Main content area with splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left panel - Tile palette
        self.tile_palette = TilePalette()
        self.tile_palette.tile_selected.connect(self._on_tile_selected)
        splitter.addWidget(self.tile_palette)
        
        # Right panel - Target canvas
        self.tile_canvas = TileCanvas()
        self.tile_canvas.set_tileset_type_by_name(self._current_type_name)
        self.tile_canvas.cell_clicked.connect(self._on_canvas_cell_clicked)
        self.tile_canvas.unit_placed.connect(self._on_unit_placed)
        splitter.addWidget(self.tile_canvas)
        
        # Set initial splitter sizes (palette needs ~500px for 8 columns)
        splitter.setSizes([500, 700])
        
        main_layout.addWidget(splitter)
    
    def _setup_status_bar(self):
        """Create the status bar."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
    
    # Slot methods (stubs for now)
    
    def _select_source_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Source Tileset Folder")
        if folder:
            self.source_folder_btn.setText(folder)
            self._load_tiles_from_folder(folder)
    
    def _load_tiles_from_folder(self, folder: str):
        """Load all tiles from the selected folder."""
        try:
            # Check file count first
            image_files = ImageLoader.find_images_in_folder(folder)
            file_count = len(image_files)
            
            if file_count > 10:
                reply = QMessageBox.warning(
                    self,
                    "Large Number of Files",
                    f"This folder contains {file_count} image files.\n\n"
                    f"Loading many tileset images at once may cause the application "
                    f"to freeze or crash due to high memory usage.\n\n"
                    f"It's recommended to organize your tiles into smaller folders "
                    f"(10 or fewer files each).\n\n"
                    f"Do you want to continue anyway?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                if reply != QMessageBox.StandardButton.Yes:
                    self.status_bar.showMessage("Folder loading cancelled")
                    return
            
            # Create progress dialog
            progress = QProgressDialog(
                "Loading images...", "Cancel", 0, file_count, self
            )
            progress.setWindowTitle("Loading")
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.setMinimumDuration(0)  # Show immediately
            progress.setValue(0)
            
            cancelled = False
            
            def update_progress(current: int, total: int):
                nonlocal cancelled
                progress.setValue(current)
                progress.setLabelText(f"Loading image {current + 1} of {total}...")
                QApplication.processEvents()
                if progress.wasCanceled():
                    cancelled = True
            
            tiles = ImageLoader.load_folder_as_simple_tiles(
                folder, progress_callback=update_progress
            )
            
            progress.close()
            
            if cancelled:
                self.status_bar.showMessage("Folder loading cancelled")
                return
            
            if self.append_checkbox.isChecked():
                self.tile_palette.prepend_tiles(tiles)
                self.status_bar.showMessage(f"Added {len(tiles)} tiles from {folder}")
            else:
                self.tile_palette.set_tiles(tiles)
                self.status_bar.showMessage(f"Loaded {len(tiles)} tiles from {folder}")
        except Exception as e:
            self.status_bar.showMessage(f"Error loading tiles: {e}")
    
    def _select_images(self):
        """Open file dialog to select individual image files."""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Tileset Images",
            "",
            "PNG Images (*.png);;All Files (*.*)"
        )
        if files:
            self._load_tiles_from_images(files)
    
    def _load_tiles_from_images(self, image_paths: list):
        """Load tiles from selected image files."""
        try:
            file_count = len(image_paths)
            
            if file_count > 10:
                reply = QMessageBox.warning(
                    self,
                    "Large Number of Files",
                    f"You selected {file_count} image files.\n\n"
                    f"Loading many tileset images at once may cause the application "
                    f"to freeze or crash due to high memory usage.\n\n"
                    f"It's recommended to select 10 or fewer files at a time.\n\n"
                    f"Do you want to continue anyway?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                if reply != QMessageBox.StandardButton.Yes:
                    self.status_bar.showMessage("Image loading cancelled")
                    return
            
            # Create progress dialog
            progress = QProgressDialog(
                "Loading images...", "Cancel", 0, file_count, self
            )
            progress.setWindowTitle("Loading")
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.setMinimumDuration(0)  # Show immediately
            progress.setValue(0)
            
            cancelled = False
            
            def update_progress(current: int, total: int):
                nonlocal cancelled
                progress.setValue(current)
                progress.setLabelText(f"Loading image {current + 1} of {total}...")
                QApplication.processEvents()
                if progress.wasCanceled():
                    cancelled = True
            
            tiles = ImageLoader.load_images_as_simple_tiles(
                image_paths, progress_callback=update_progress
            )
            
            progress.close()
            
            if cancelled:
                self.status_bar.showMessage("Image loading cancelled")
                return
            
            if self.append_checkbox.isChecked():
                self.tile_palette.prepend_tiles(tiles)
                self.status_bar.showMessage(f"Added {len(tiles)} tiles from {file_count} image(s)")
            else:
                self.tile_palette.set_tiles(tiles)
                self.status_bar.showMessage(f"Loaded {len(tiles)} tiles from {file_count} image(s)")
        except Exception as e:
            self.status_bar.showMessage(f"Error loading tiles: {e}")
    
    def _on_tile_selected(self, tile: Tile):
        """Handle tile selection from the palette."""
        self.status_bar.showMessage(
            f"Selected: {tile.source_name} [{tile.source_index}] "
            f"({tile.width}×{tile.height}px)"
        )
    
    def _set_target_type(self, type_name: str):
        """Set the target tileset type (internal)."""
        tileset_type = TILESET_TYPES[type_name]
        self._current_type_name = type_name
        self.target_type_label.setText(type_name)
        self.tile_canvas.set_tileset_type(tileset_type)
        self.status_bar.showMessage(
            f"Target: {type_name} ({tileset_type.width}×{tileset_type.height} px)"
        )
    
    def _on_canvas_cell_clicked(self, grid_x: int, grid_y: int):
        """Handle click on a canvas grid cell."""
        self.status_bar.showMessage(f"Canvas cell clicked: ({grid_x}, {grid_y})")
    
    def _on_unit_placed(self, unit, grid_x: int, grid_y: int):
        """Handle unit placement on the canvas."""
        placed_count = len(self.tile_canvas.canvas._placed_units)
        total_cells = self.tile_canvas.canvas.grid_width * self.tile_canvas.canvas.grid_height
        self.status_bar.showMessage(
            f"Placed {unit.source_name} at ({grid_x}, {grid_y}) - "
            f"{placed_count} unit(s) on canvas"
        )
    
    def _new_project(self):
        """Create a new tileset project."""
        # Warn if canvas is not empty
        if not self.tile_canvas.is_empty():
            reply = QMessageBox.question(
                self,
                "New Project",
                "Creating a new project will clear the current canvas.\n\nContinue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        
        # Show new project dialog
        selected_type = NewProjectDialog.get_tileset_type(
            self, self._current_type_name
        )
        
        if selected_type:
            self._set_target_type(selected_type)
            self.status_bar.showMessage(f"New {selected_type} project created")
    
    def _open_project(self):
        self.status_bar.showMessage("Open project...")
    
    def _save_project(self):
        self.status_bar.showMessage("Save project...")
    
    def _export_png(self):
        """Export the current canvas as a PNG file."""
        if self.tile_canvas.is_empty():
            QMessageBox.warning(
                self,
                "Nothing to Export",
                "The canvas is empty. Add some tiles before exporting.",
                QMessageBox.StandardButton.Ok
            )
            return
        
        # Suggest a filename based on target type
        target_type = self._current_type_name
        suggested_name = f"Tileset_{target_type}.png"
        
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Export Tileset",
            suggested_name,
            "PNG Images (*.png)"
        )
        if filepath:
            # Ensure .png extension
            if not filepath.lower().endswith('.png'):
                filepath += '.png'
            
            # Render and save
            pixmap = self.tile_canvas.render_to_image()
            success = pixmap.save(filepath, "PNG")
            
            if success:
                self.status_bar.showMessage(f"Exported to: {filepath}")
            else:
                QMessageBox.critical(
                    self,
                    "Export Failed",
                    f"Failed to save image to:\n{filepath}",
                    QMessageBox.StandardButton.Ok
                )
                self.status_bar.showMessage("Export failed")
    
    def _undo(self):
        self.status_bar.showMessage("Undo")
    
    def _redo(self):
        self.status_bar.showMessage("Redo")
    
    def _clear_canvas(self):
        """Clear all tiles from the canvas."""
        if self.tile_canvas.is_empty():
            self.status_bar.showMessage("Canvas is already empty")
            return
        
        reply = QMessageBox.question(
            self,
            "Clear Canvas",
            "Are you sure you want to clear all tiles from the canvas?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.tile_canvas.clear()
            self.status_bar.showMessage("Canvas cleared")
    
    def _zoom_in(self):
        self.status_bar.showMessage("Zoom in")
    
    def _zoom_out(self):
        self.status_bar.showMessage("Zoom out")
    
    def _zoom_reset(self):
        self.status_bar.showMessage("Zoom reset")
    
    def _show_about(self):
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.about(
            self,
            "About Tileset Composer",
            "RPG Maker MZ Tileset Composer\n\n"
            "A visual tool for creating and composing tilesets."
        )
