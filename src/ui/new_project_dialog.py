"""Dialog for creating a new tileset project."""

from typing import Optional

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QPushButton,
    QDialogButtonBox,
    QGroupBox,
    QFormLayout,
)
from PySide6.QtCore import Qt

from ..models.tileset_types import TILESET_TYPES


class NewProjectDialog(QDialog):
    """Dialog for creating a new tileset project."""
    
    def __init__(self, parent=None, current_type: str = "A5"):
        super().__init__(parent)
        self.setWindowTitle("New Tileset Project")
        self.setModal(True)
        self.setMinimumWidth(350)
        
        self._selected_type: Optional[str] = None
        
        self._setup_ui(current_type)
    
    def _setup_ui(self, current_type: str):
        layout = QVBoxLayout(self)
        
        # Info group
        info_group = QGroupBox("Tileset Type")
        info_layout = QFormLayout(info_group)
        
        # Type selector
        self.type_combo = QComboBox()
        self.type_combo.addItems(TILESET_TYPES.keys())
        self.type_combo.setCurrentText(current_type)
        self.type_combo.currentTextChanged.connect(self._update_info)
        info_layout.addRow("Type:", self.type_combo)
        
        # Dimension display
        self.dimension_label = QLabel()
        info_layout.addRow("Dimensions:", self.dimension_label)
        
        # Description
        self.description_label = QLabel()
        self.description_label.setWordWrap(True)
        self.description_label.setStyleSheet("color: #666;")
        info_layout.addRow("", self.description_label)
        
        layout.addWidget(info_group)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        # Initialize info display
        self._update_info(current_type)
    
    def _update_info(self, type_name: str):
        """Update the info display for the selected type."""
        tileset_type = TILESET_TYPES.get(type_name)
        if not tileset_type:
            return
        
        self.dimension_label.setText(f"{tileset_type.width} × {tileset_type.height} pixels")
        
        # Type-specific descriptions
        descriptions = {
            "A1": "Animated tiles (water, lava, waterfalls)",
            "A2": "Ground autotiles (grass, dirt, sand)",
            "A3": "Building autotiles (roofs, walls)",
            "A4": "Wall autotiles (cliffs, fences)",
            "A5": "Normal tiles (8×16 grid, no autotile)",
            "B": "Upper layer tiles (16×16 grid)",
            "C": "Upper layer tiles (16×16 grid)",
            "D": "Upper layer tiles (16×16 grid)",
            "E": "Upper layer tiles (16×16 grid)",
        }
        self.description_label.setText(descriptions.get(type_name, ""))
    
    def _on_accept(self):
        """Handle OK button."""
        self._selected_type = self.type_combo.currentText()
        self.accept()
    
    @property
    def selected_type(self) -> Optional[str]:
        """Get the selected tileset type name."""
        return self._selected_type
    
    @classmethod
    def get_tileset_type(cls, parent=None, current_type: str = "A5") -> Optional[str]:
        """
        Show the dialog and return the selected type.
        
        Returns:
            The selected type name, or None if cancelled.
        """
        dialog = cls(parent, current_type)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return dialog.selected_type
        return None
