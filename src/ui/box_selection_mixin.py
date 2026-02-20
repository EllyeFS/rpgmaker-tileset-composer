"""
Box selection mixin for Qt widgets.

Provides reusable box selection functionality with visual feedback.
"""

from typing import Optional

from PySide6.QtCore import QPoint, QRect
from PySide6.QtGui import QPainter, QPen, QColor


class BoxSelectionMixin:
    """
    Mixin providing box selection functionality.
    
    Classes using this mixin should:
    1. Call initialize_box_selection() in __init__
    2. Call handle_box_selection_paint() in paintEvent
    3. Call update() method when box selection changes
    4. Implement _on_box_selection_updated() to handle selection updates
    """
    
    BOX_FILL_COLOR = QColor(135, 206, 250, 60)
    BOX_BORDER_COLOR = QColor(135, 206, 250, 180)
    BOX_BORDER_WIDTH = 2
    
    def initialize_box_selection(self):
        """Initialize box selection state. Call this in __init__."""
        self._box_selecting = False
        self._box_start: Optional[QPoint] = None
        self._box_current: Optional[QPoint] = None
    
    def start_box_selection(self, pos: QPoint):
        """Start box selection at the given position."""
        self._box_selecting = True
        self._box_start = pos
        self._box_current = pos
    
    def update_box_selection(self, pos: QPoint):
        """Update box selection to the given position."""
        if self._box_selecting:
            self._box_current = pos
            self._on_box_selection_updated()
    
    def end_box_selection(self):
        """End box selection."""
        self._box_selecting = False
        self._box_start = None
        self._box_current = None
    
    def is_box_selecting(self) -> bool:
        """Check if currently performing box selection."""
        return self._box_selecting
    
    def get_selection_rect(self) -> Optional[QRect]:
        """Get the current selection rectangle, or None if not selecting."""
        if not self._box_start or not self._box_current:
            return None
        
        x1 = min(self._box_start.x(), self._box_current.x())
        y1 = min(self._box_start.y(), self._box_current.y())
        x2 = max(self._box_start.x(), self._box_current.x())
        y2 = max(self._box_start.y(), self._box_current.y())
        
        return QRect(x1, y1, x2 - x1, y2 - y1)
    
    def handle_box_selection_paint(self, painter: QPainter):
        """Draw box selection overlay. Call this in paintEvent."""
        if not self._box_selecting:
            return
        
        rect = self.get_selection_rect()
        if not rect:
            return
        
        painter.fillRect(rect, self.BOX_FILL_COLOR)
        
        pen = QPen(self.BOX_BORDER_COLOR, self.BOX_BORDER_WIDTH)
        painter.setPen(pen)
        painter.drawRect(rect)
    
    def _on_box_selection_updated(self):
        """
        Called when box selection is updated.
        
        Override this method to implement custom selection logic.
        """
        pass
