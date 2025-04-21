from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QRect, pyqtSignal
from PyQt5.QtGui import QPainter, QColor

class RangeSlider(QWidget):
    """A custom range slider widget that allows selecting both start and end values"""
    rangeChanged = pyqtSignal(float, float)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(50)
        self._min = 0
        self._max = 1000
        self._start = 0
        self._end = 1000
        self._handle_size = 12  # Slightly larger handles
        self._bar_height = 6    # Slightly thicker bar
        self._dragging_start = False
        self._dragging_end = False
        self._original_start = None
        self._original_end = None
        
        # Modern color scheme
        self._bar_color = QColor(220, 220, 220)  # Light gray for background
        self._original_range_color = QColor(200, 200, 200)  # Slightly darker for original range
        self._selected_range_color = QColor(0, 120, 215)    # Modern blue for selected range
        self._handle_color = QColor(0, 120, 215)           # Same blue for handles
        self._handle_border_color = QColor(255, 255, 255)  # White border for handles
        self._indicator_color = QColor(100, 100, 100)      # Dark gray for indicators

    def resetToOriginal(self):
        """Reset the slider to the original timestamps"""
        if self._original_start is not None and self._original_end is not None:
            self.setValues(self._original_start, self._original_end)
        
    def setRange(self, min_val, max_val):
        self._min = min_val
        self._max = max_val
        self._start = min_val
        self._end = max_val
        self.update()
        
    def setValues(self, start, end):
        self._start = max(self._min, min(self._max, start))
        self._end = max(self._min, min(self._max, end))
        self.update()
        self.rangeChanged.emit(self._start, self._end)
        
    def setOriginalTimes(self, start, end):
        """Set the original subtitle timing for visual reference"""
        self._original_start = start
        self._original_end = end
        self.update()
        
    def getValues(self):
        return self._start, self._end
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw the background bar with rounded corners
        bar_rect = QRect(0, self.height()//2 - self._bar_height//2,
                        self.width(), self._bar_height)
        painter.setPen(Qt.NoPen)
        painter.setBrush(self._bar_color)
        painter.drawRoundedRect(bar_rect, self._bar_height//2, self._bar_height//2)
        
        # Draw the original timing indicators if set
        if self._original_start is not None and self._original_end is not None:
            # Draw original range in a different color
            start_pos = int((self._original_start - self._min) / (self._max - self._min) * self.width())
            end_pos = int((self._original_end - self._min) / (self._max - self._min) * self.width())
            original_rect = QRect(start_pos, self.height()//2 - self._bar_height//2,
                                end_pos - start_pos, self._bar_height)
            painter.setBrush(self._original_range_color)
            painter.drawRoundedRect(original_rect, self._bar_height//2, self._bar_height//2)
            
            # Draw vertical lines for original start and end
            painter.setPen(self._indicator_color)
            painter.drawLine(start_pos, self.height()//2 - 10, start_pos, self.height()//2 + 10)
            painter.drawLine(end_pos, self.height()//2 - 10, end_pos, self.height()//2 + 10)
        
        # Draw the selected range
        start_pos = int((self._start - self._min) / (self._max - self._min) * self.width())
        end_pos = int((self._end - self._min) / (self._max - self._min) * self.width())
        selected_rect = QRect(start_pos, self.height()//2 - self._bar_height//2,
                            end_pos - start_pos, self._bar_height)
        painter.setBrush(self._selected_range_color)
        painter.drawRoundedRect(selected_rect, self._bar_height//2, self._bar_height//2)
        
        # Draw the handles with border and shadow effect
        for pos in [start_pos, end_pos]:
            handle_rect = QRect(pos - self._handle_size//2,
                              self.height()//2 - self._handle_size//2,
                              self._handle_size, self._handle_size)
            
            # Draw handle shadow
            shadow_rect = handle_rect.translated(1, 1)
            painter.setBrush(QColor(0, 0, 0, 30))
            painter.drawEllipse(shadow_rect)
            
            # Draw handle border
            painter.setPen(self._handle_border_color)
            painter.setBrush(self._handle_color)
            painter.drawEllipse(handle_rect)
            
    def mousePressEvent(self, event):
        start_pos = int((self._start - self._min) / (self._max - self._min) * self.width())
        end_pos = int((self._end - self._min) / (self._max - self._min) * self.width())
        
        if abs(event.x() - start_pos) < self._handle_size:
            self._dragging_start = True
        elif abs(event.x() - end_pos) < self._handle_size:
            self._dragging_end = True
            
    def mouseMoveEvent(self, event):
        if self._dragging_start:
            new_start = self._min + (event.x() / self.width()) * (self._max - self._min)
            new_start = max(self._min, min(new_start, self._end))
            self._start = new_start
            self.update()
            self.rangeChanged.emit(self._start, self._end)
        elif self._dragging_end:
            new_end = self._min + (event.x() / self.width()) * (self._max - self._min)
            new_end = max(self._start, min(new_end, self._max))
            self._end = new_end
            self.update()
            self.rangeChanged.emit(self._start, self._end)
            
    def mouseReleaseEvent(self, event):
        self._dragging_start = False
        self._dragging_end = False 