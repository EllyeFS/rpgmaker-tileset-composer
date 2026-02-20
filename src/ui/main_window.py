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
)
from PySide6.QtCore import Qt

from ..models import TILESET_TYPES


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
        
        # Source folder selector
        toolbar_layout.addWidget(QLabel("Source Folder:"))
        self.source_folder_btn = QPushButton("Select Folder...")
        self.source_folder_btn.clicked.connect(self._select_source_folder)
        toolbar_layout.addWidget(self.source_folder_btn)
        
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
        
        # Left panel - Tile palette (placeholder)
        palette_placeholder = QWidget()
        palette_layout = QVBoxLayout(palette_placeholder)
        palette_layout.addWidget(QLabel("TILE PALETTE"))
        palette_layout.addWidget(QLabel("(Select a source folder to load tiles)"))
        palette_layout.addStretch()
        splitter.addWidget(palette_placeholder)
        
        # Right panel - Target canvas (placeholder)
        canvas_placeholder = QWidget()
        canvas_layout = QVBoxLayout(canvas_placeholder)
        canvas_layout.addWidget(QLabel("TARGET CANVAS"))
        canvas_layout.addWidget(QLabel(f"(Ready for {self.target_type_combo.currentText()} tileset)"))
        canvas_layout.addStretch()
        splitter.addWidget(canvas_placeholder)
        
        # Set initial splitter sizes (1:2 ratio)
        splitter.setSizes([400, 800])
        
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
            self.status_bar.showMessage(f"Source folder: {folder}")
    
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
