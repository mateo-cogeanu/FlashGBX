# ui/main_window/main.py
import os
from pathlib import Path

from ui.qt_compat import QMainWindow, QTimer, Signal, Slot
from utils.translator import Translator
from ui.core.preset_manager import PresetManager
from ui.core.video_controller import VideoController


class VideoEditor(QMainWindow):
    export_success_with_info = Signal(str)
    export_error = Signal(str)
    export_phase_changed = Signal(str)
    export_progress = Signal(str, int)
    export_timer_stop = Signal()

    from core.config_manager import ConfigManager as _CM
    VERSION = _CM.APP_VERSION
    del _CM
    GBA_WIDTH = 240
    GBA_HEIGHT = 160

    _LANG_DIR = str(Path(__file__).parent.parent.parent / "lang")

    def __init__(self, video_path=None, translator=None):
        super().__init__()

        self.config_manager = None
        try:
            from core.config_manager import ConfigManager
            self.config_manager = ConfigManager()
        except Exception:
            pass

        if translator is not None:
            self.translator = translator
        else:
            lang = "english"
            if self.config_manager:
                try:
                    lang = self.config_manager.get('SETTINGS', 'language', 'english')
                except Exception:
                    pass
            self.translator = Translator(lang_dir=self._LANG_DIR, default_lang=lang)
        self._tr = self.translator.tr

        self.preset_manager = PresetManager()
        self.video_controller = VideoController()
        self.video_controller.frame_ready.connect(self._on_frame_ready)

        self.video_path = None
        self.output_folder = None
        self.crop_rect = None
        self._is_closing = False
        self._is_exporting = False
        self._preview_muted = False
        self._session_last_video_dir = None
        self._session_output_folder = None
        self._last_encode_state = None

        self.video_controller.playback_state_changed.connect(self._on_playback_state_changed)

        self.export_success_with_info.connect(self._on_export_success_with_info)
        self.export_error.connect(self._on_export_error)
        from ui.main_window.video_ops import _start_export_timer, _stop_export_timer, _on_export_progress
        self.export_phase_changed.connect(lambda text: _start_export_timer(self, text))
        self.export_progress.connect(lambda key, pct: _on_export_progress(self, key, pct))
        self.export_timer_stop.connect(lambda: _stop_export_timer(self))

        self.init_ui()
        self._set_controls_enabled(False)

        if video_path:
            QTimer.singleShot(100, lambda: self.load_video(video_path))

    def tr(self, key, **kwargs):
        return self.translator.tr(key, **kwargs)

    def init_ui(self):
        from .setup_ui import init_ui
        return init_ui(self)

    def change_language(self, lang_key):
        from .config import change_language
        return change_language(self, lang_key)

    def retranslate_ui(self):
        from .config import retranslate_ui
        return retranslate_ui(self)

    def retranslate_menus(self):
        from .menu_bar import retranslate_menus
        return retranslate_menus(self)

    def _on_remember_paths_toggled(self, checked):
        from .config import _on_remember_paths_toggled
        return _on_remember_paths_toggled(self, checked)

    def _save_preview_mode(self, state):
        from .config import _save_preview_mode
        return _save_preview_mode(self, state)

    def _save_max_workers(self, value):
        from .config import _save_max_workers
        return _save_max_workers(self, value)

    def _save_output_folder(self, folder):
        from .config import _save_output_folder
        return _save_output_folder(self, folder)

    def _save_last_video(self, path):
        from .config import _save_last_video
        return _save_last_video(self, path)

    def _update_presets_submenu(self):
        from .presets import _update_presets_submenu
        return _update_presets_submenu(self)

    def _apply_preset(self, preset_name):
        from .presets import _apply_preset
        return _apply_preset(self, preset_name)

    def _get_current_preset_values(self):
        from .presets import _get_current_preset_values
        return _get_current_preset_values(self)

    def _load_default_preset(self):
        from .presets import _load_default_preset
        return _load_default_preset(self)

    def _save_default_preset(self, preset_name):
        from .presets import _save_default_preset
        return _save_default_preset(self, preset_name)

    def _on_preset_changed(self, preset_name):
        from .presets import _on_preset_changed
        return _on_preset_changed(self, preset_name)

    def _reload_current_preset(self):
        from .presets import _reload_current_preset
        return _reload_current_preset(self)

    def _save_new_preset(self):
        from .presets import _save_new_preset
        return _save_new_preset(self)

    def _update_current_preset(self):
        from .presets import _update_current_preset
        return _update_current_preset(self)

    def _set_current_as_default(self):
        from .presets import _set_current_as_default
        return _set_current_as_default(self)

    def _delete_current_preset(self):
        from .presets import _delete_current_preset
        return _delete_current_preset(self)

    def open_video_dialog(self):
        from .video_ops import open_video_dialog
        return open_video_dialog(self)

    def load_video(self, path):
        from .video_ops import load_video
        return load_video(self, path)

    def export_video(self):
        from .video_ops import export_video
        return export_video(self)

    def update_preview(self):
        from .video_ops import update_preview
        return update_preview(self)

    def _apply_filters(self, qimg):
        from .video_ops import _apply_filters
        return _apply_filters(self, qimg)

    def _display_frame(self, qimg, frame_num):
        from .video_ops import _display_frame
        return _display_frame(self, qimg, frame_num)

    def _frame_to_qimage(self, frame):
        from .video_ops import _frame_to_qimage
        return _frame_to_qimage(self, frame)

    def _show_frame(self, frame_num):
        from .video_ops import _show_frame
        return _show_frame(self, frame_num)

    def _show_current_frame(self):
        from .video_ops import _show_current_frame
        return _show_current_frame(self)

    def _get_transformation_mode(self):
        from .video_ops import _get_transformation_mode
        return _get_transformation_mode(self)

    def _seek_frame(self, frame_num):
        from .video_ops import _seek_frame
        return _seek_frame(self, frame_num)

    def _set_start_frame(self):
        from .video_ops import _set_start_frame
        return _set_start_frame(self)

    def _set_end_frame(self):
        from .video_ops import _set_end_frame
        return _set_end_frame(self)

    def _goto_start_marker(self):
        from .video_ops import _goto_start_marker
        return _goto_start_marker(self)

    def _goto_end_marker(self):
        from .video_ops import _goto_end_marker
        return _goto_end_marker(self)

    def _on_frame_ready(self, frame_num, frame):
        from .video_ops import _on_frame_ready
        return _on_frame_ready(self, frame_num, frame)

    def toggle_play(self):
        from .video_ops import toggle_play
        return toggle_play(self)

    def prev_frame(self):
        from .video_ops import prev_frame
        return prev_frame(self)

    def next_frame(self):
        from .video_ops import next_frame
        return next_frame(self)

    def prev_keyframe(self):
        from .video_ops import prev_keyframe
        return prev_keyframe(self)

    def next_keyframe(self):
        from .video_ops import next_keyframe
        return next_keyframe(self)

    def first_frame(self):
        from .video_ops import first_frame
        return first_frame(self)

    def last_frame(self):
        from .video_ops import last_frame
        return last_frame(self)

    def _on_playback_state_changed(self, is_playing):
        from .video_ops import _on_playback_state_changed
        return _on_playback_state_changed(self, is_playing)

    def _on_view_mode_changed(self, state):
        from .video_ops import _on_view_mode_changed
        return _on_view_mode_changed(self, state)

    def _browse_output_folder(self):
        from .video_ops import _browse_output_folder
        return _browse_output_folder(self)

    def _format_time(self, frame_num):
        from .utils import _format_time
        return _format_time(self, frame_num)

    def _update_time_display(self):
        from .utils import _update_time_display
        return _update_time_display(self)

    def _update_range_label(self):
        from .utils import _update_range_label
        return _update_range_label(self)

    def _set_controls_enabled(self, enabled):
        from .utils import _set_controls_enabled
        return _set_controls_enabled(self, enabled)

    def disable_mouse_wheel_recursive(self, widget):
        from .utils import disable_mouse_wheel_recursive
        return disable_mouse_wheel_recursive(self, widget)

    def _setup_shortcuts(self):
        from .utils import _setup_shortcuts
        return _setup_shortcuts(self)

    def _on_audio_format_changed(self, format_str):
        from .utils import _on_audio_format_changed
        return _on_audio_format_changed(self, format_str)

    def _on_no_audio_toggled(self, checked):
        from .utils import _on_no_audio_toggled
        return _on_no_audio_toggled(self, checked)

    def _on_mute_toggled(self):
        from .utils import _on_mute_toggled
        return _on_mute_toggled(self)

    def _on_volume_changed(self, value):
        from .utils import _on_volume_changed
        return _on_volume_changed(self, value)

    def _on_skip_video_toggled(self, checked):
        from .utils import _on_skip_video_toggled
        return _on_skip_video_toggled(self, checked)

    def _on_button_toggled(self, checked, sender_cb):
        from .utils import _on_button_toggled
        return _on_button_toggled(self, checked, sender_cb)

    def _ensure_at_least_one_button_selected(self):
        from .utils import _ensure_at_least_one_button_selected
        return _ensure_at_least_one_button_selected(self)

    def closeEvent(self, event):
        if getattr(self, '_is_exporting', False):
            from ui.qt_compat import QMessageBox
            reply = QMessageBox.warning(
                self,
                self.tr("export_in_progress_title", default="Export in progress"),
                self.tr("export_in_progress_close_msg",
                        default="An export is currently in progress.\n"
                                "Closing the application will cancel it.\n\n"
                                "Are you sure you want to close?"),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                event.ignore()
                return

        if self.config_manager:
            try:
                self.config_manager.set('UI', 'preview_mode', str(self.show_preview_check.isChecked()))
                if self.output_folder:
                    self.config_manager.set('PATHS', 'output_folder', self.output_folder)
                if self.video_path:
                    self.config_manager.set('PATHS', 'last_video_path', self.video_path)
                self.config_manager.set('SETTINGS', 'max_workers', str(self.workers_spin.value()))
            except Exception:
                pass

        self._is_closing = True
        if getattr(self, '_encoder_proc', None) and self._encoder_proc.poll() is None:
            self._encoder_proc.kill()
            self._encoder_proc = None
        self.video_controller.close()
        event.accept()

    @Slot(str)
    def _on_export_error(self, error_msg):
        from ui.qt_compat import QMessageBox
        from ui.main_window.video_ops import _lock_ui, _cleanup_conversion_dirs
        from utils.system_utils import get_base_dir

        p = get_base_dir()
        import shutil as _sh
        for d in ("temp", "build"):
            _d = p / d
            if _d.exists():
                _sh.rmtree(str(_d), ignore_errors=True)
        _lock_ui(self, locked=False)
        
        try:
            self.btn_export.clicked.disconnect()
        except TypeError:
            pass
        self.btn_export.clicked.connect(self.export_video)
        self.btn_export.setStyleSheet("background-color: #00AA00; color: white; font-weight: bold; padding: 5px;")
        self.btn_export.setEnabled(True)
        self.btn_export.setText(self.tr("build_rom"))

        self.lbl_export_status.setText(self.tr("ready_to_export"))
        self.lbl_export_timer.setVisible(False)

        QMessageBox.critical(self, self.tr("export_error_title"), str(error_msg))

    @Slot(str)
    def _on_export_success_with_info(self, rom_info):
        from ui.qt_compat import QMessageBox, Qt
        from ui.main_window.video_ops import _lock_ui, _parse_memuse, _build_memuse_html, _execute_post_action, _cleanup_conversion_dirs
        from utils.system_utils import get_base_dir

        import shutil as _sh
        for d in ("temp", "build"):
            _d = get_base_dir() / d
            if _d.exists():
                _sh.rmtree(str(_d), ignore_errors=True)
        self.lbl_export_status.setText(self.tr("progress_done"))

        msg_plain = self.tr("export_success_msg")
        html_table = _build_memuse_html(rom_info, tr=self.tr) if rom_info else ""

        if html_table:
            from ui.qt_compat import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
            dlg = QDialog(self)
            dlg.setWindowTitle(self.tr("export_success_title"))
            dlg.setWindowFlags(
                dlg.windowFlags()
                & ~Qt.WindowContextHelpButtonHint
                & ~Qt.WindowMaximizeButtonHint
            )
            dlg.setFixedWidth(480)

            layout = QVBoxLayout(dlg)
            layout.setSpacing(12)
            layout.setContentsMargins(16, 16, 16, 16)

            lbl_msg = QLabel(f"<b>{msg_plain}</b>")
            lbl_msg.setAlignment(Qt.AlignCenter)
            layout.addWidget(lbl_msg)

            lbl_mem = QLabel(html_table)
            lbl_mem.setTextFormat(Qt.RichText)
            lbl_mem.setAlignment(Qt.AlignLeft)
            layout.addWidget(lbl_mem)

            btn_row = QHBoxLayout()
            btn_row.addStretch()
            btn_ok = QPushButton("OK")
            btn_ok.setDefault(True)
            btn_ok.setFixedWidth(80)
            btn_ok.clicked.connect(dlg.accept)
            btn_row.addWidget(btn_ok)
            layout.addLayout(btn_row)

            dlg.exec_()
        else:
            QMessageBox.information(self, self.tr("export_success_title"), msg_plain)

        _lock_ui(self, locked=False)
        
        try:
            self.btn_export.clicked.disconnect()
        except TypeError:
            pass
        self.btn_export.clicked.connect(self.export_video)
        self.btn_export.setStyleSheet("background-color: #00AA00; color: white; font-weight: bold; padding: 5px;")
        self.btn_export.setEnabled(True)
        self.btn_export.setText(self.tr("build_rom"))

        self.lbl_export_status.setText(self.tr("ready_to_export"))
        self.lbl_export_timer.setVisible(False)

        action_key = self.combo_post_action.currentData()
        if action_key and action_key != "on_finish_nothing":
            _execute_post_action(self, action_key)
