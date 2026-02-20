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
from ..services.image_loader import ImageLoader
from .tile_palette import TilePalette


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
        
        # Target type selector
        toolbar_layout.addWidget(QLabel("Target Type:"))
        self.target_type_combo = QComboBox()
        self.target_type_combo.addItems(TILESET_TYPES.keys())
        self.target_type_combo.setCurrentText("A5")  # Default to simple grid
        self.target_type_combo.currentTextChanged.connect(self._on_target_type_changed)
        toolbar_layout.addWidget(self.target_type_combo)
        
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
        
        # Right panel - Target canvas (placeholder)
        canvas_placeholder = QWidget()
        canvas_layout = QVBoxLayout(canvas_placeholder)
        canvas_layout.addWidget(QLabel("TARGET CANVAS"))
        canvas_layout.addWidget(QLabel(f"(Ready for {self.target_type_combo.currentText()} tileset)"))
        canvas_layout.addStretch()
        splitter.addWidget(canvas_placeholder)
        
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
    
    def _on_target_type_changed(self, type_name: str):
        tileset_type = TILESET_TYPES[type_name]
        self.status_bar.showMessage(
            f"Target: {type_name} ({tileset_type.width}×{tileset_type.height} px)"
        )
    
    def _new_project(self):
        self.status_bar.showMessage("New project")
    
    def _open_project(self):
        self.status_bar.showMessage("Open project...")
    
    def _save_project(self):
        self.status_bar.showMessage("Save project...")
    
    def _export_png(self):
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Export Tileset", "", "PNG Images (*.png)"
        )
        if filepath:
            self.status_bar.showMessage(f"Exported to: {filepath}")
    
    def _undo(self):
        self.status_bar.showMessage("Undo")
    
    def _redo(self):
        self.status_bar.showMessage("Redo")
    
    def _clear_canvas(self):
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
