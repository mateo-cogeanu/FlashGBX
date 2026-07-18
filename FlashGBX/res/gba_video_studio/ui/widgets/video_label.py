# ui/widgets/video_label.py
from ui.qt_compat import QLabel, QPainter, QPen, QColor, QRect, Qt


class VideoLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.start_frame = 0
        self.end_frame = 0
        self.current_frame = 0
        self.total_frames = 1
        self.selection_color = QColor(0, 255, 0, 100)
    
    def set_range(self, start, end, current, total):
        self.start_frame = start
        self.end_frame = end
        self.current_frame = current
        self.total_frames = total
        self.update()
    
    def paintEvent(self, event):
        super().paintEvent(event)
        if not self.pixmap():
            return
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        rect = self.rect()
        bar_height = 4
        bar_rect = QRect(rect.x(), rect.height() - bar_height, rect.width(), bar_height)
        painter.fillRect(bar_rect, QColor(60, 60, 60))
        
        if self.total_frames > 0:
            start_x = (self.start_frame / self.total_frames) * rect.width()
            end_x = (self.end_frame / self.total_frames) * rect.width()
            selection_rect = QRect(int(start_x), bar_rect.y(), int(end_x - start_x), bar_height)
            painter.fillRect(selection_rect, self.selection_color)
            
            current_x = (self.current_frame / self.total_frames) * rect.width()
            painter.setPen(QPen(QColor(255, 255, 0), 2))
            painter.drawLine(int(current_x), bar_rect.y(), int(current_x), rect.height())
        painter.end()
