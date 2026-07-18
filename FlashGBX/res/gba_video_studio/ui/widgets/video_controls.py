# ui/widgets/video_controls.py
from ui.qt_compat import QWidget, QHBoxLayout, QPushButton, QSlider, QSpinBox, QLabel


class VideoControls(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setup_ui()
    
    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.btn_play = self._create_button("▶", "Play/Pause (Space)")
        self.btn_prev_frame = self._create_button("◀◀", "Previous Frame (←)")
        self.btn_next_frame = self._create_button("▶▶", "Next Frame (→)")
        self.btn_prev_keyframe = self._create_button("▲", "Previous Keyframe (↑)")
        self.btn_next_keyframe = self._create_button("▼", "Next Keyframe (↓)")
        self.btn_mark_start = self._create_button("[", "Mark Start (Ctrl+PageUp)")
        self.btn_mark_end = self._create_button("]", "Mark End (Ctrl+PageDown)")
        self.btn_goto_start = self._create_button("←[", "Go to Start (Shift+↓)")
        self.btn_goto_end = self._create_button("]→", "Go to End (Shift+↑)")
        self.btn_first_frame = self._create_button("|◀", "First Frame (Home)")
        self.btn_last_frame = self._create_button("▶|", "Last Frame (End)")
        
        for btn in [self.btn_play, self.btn_prev_frame, self.btn_next_frame,
                    self.btn_prev_keyframe, self.btn_next_keyframe,
                    self.btn_mark_start, self.btn_mark_end,
                    self.btn_goto_start, self.btn_goto_end,
                    self.btn_first_frame, self.btn_last_frame]:
            layout.addWidget(btn)
        
        layout.addStretch()
    
    def _create_button(self, text, tooltip):
        btn = QPushButton(text)
        btn.setToolTip(tooltip)
        btn.setFixedSize(50, 35)
        return btn
    
    def get_buttons(self):
        return {
            'play': self.btn_play,
            'prev_frame': self.btn_prev_frame,
            'next_frame': self.btn_next_frame,
            'prev_keyframe': self.btn_prev_keyframe,
            'next_keyframe': self.btn_next_keyframe,
            'mark_start': self.btn_mark_start,
            'mark_end': self.btn_mark_end,
            'goto_start': self.btn_goto_start,
            'goto_end': self.btn_goto_end,
            'first_frame': self.btn_first_frame,
            'last_frame': self.btn_last_frame,
        }
