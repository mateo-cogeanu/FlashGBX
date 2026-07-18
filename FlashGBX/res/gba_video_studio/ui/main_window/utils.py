# ui/main_window/utils.py
import os

from ui.qt_compat import (
    QShortcut, QKeySequence, QSpinBox, QDoubleSpinBox, QComboBox,
    Qt, QObject, QEvent,
)
from ui.widgets import NoWheelEventFilter


def _format_time(main_window, frame_num):
    fps = main_window.video_controller.fps
    if fps <= 0:
        return "00:00:00.00"
    seconds = frame_num / fps
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centiseconds = int((seconds % 1) * 100)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{centiseconds:02d}"


def _update_time_display(main_window):
    main_window.lbl_time.setText(_format_time(main_window, main_window.video_controller.current_frame))


def _update_range_label(main_window):
    fps = main_window.video_controller.fps
    start = main_window.video_controller.start_frame
    end = main_window.video_controller.end_frame
    if fps > 0:
        start_time = _format_time(main_window, start)
        end_time = _format_time(main_window, end)
        duration_frames = end - start + 1
        duration_time = _format_time(main_window, duration_frames - 1)
        main_window.lbl_range.setText(
            main_window.tr("range_format",
                           start=start, end=end,
                           start_time=start_time, end_time=end_time,
                           duration_time=duration_time)
        )
    else:
        main_window.lbl_range.setText(main_window.tr("range_not_set"))


def _set_controls_enabled(main_window, enabled):
    controls = [
        main_window.btn_play, main_window.btn_prev_frame, main_window.btn_next_frame,
        main_window.btn_prev_keyframe, main_window.btn_next_keyframe,
        main_window.btn_mark_start, main_window.btn_mark_end,
        main_window.btn_goto_start, main_window.btn_goto_end,
        main_window.btn_first_frame, main_window.btn_last_frame,
        main_window.timeline, main_window.frame_spin,
        main_window.crop_edit, main_window.letterbox_check,
        main_window.btn_apply_filters, main_window.btn_export, main_window.btn_browse_output,
        main_window.show_preview_check, main_window.rom_name_edit,
        main_window.fps_combo, main_window.diff_threshold, main_window.force_i_threshold,
        main_window.codebook_size, main_window.dither_check, main_window.motion_check,
        main_window.motion_thresh, main_window.variance_threshold, main_window.color_fallback_threshold,
        main_window.audio_format, main_window.volume, main_window.sample_rate, main_window.no_audio_check,
        main_window.workers_spin, main_window.kmeans_spin, main_window.iframe_weight,
        main_window.iframe_interval, main_window.preset_combo, main_window.btn_reload_preset,
        main_window.skip_video_check,
    ]
    for control in controls:
        if control is not None:
            control.setEnabled(enabled)

    skip_enabled = main_window.skip_video_check.isChecked() if hasattr(main_window, 'skip_video_check') else False
    for checkbox in main_window.button_checkboxes:
        if checkbox is not None:
            checkbox.setEnabled(enabled and skip_enabled)

    if enabled and main_window.output_folder:
        main_window.btn_export.setEnabled(True)
        main_window.btn_export.setStyleSheet("background-color: #00AA00; color: white; font-weight: bold; padding: 5px;")
        if hasattr(main_window, 'action_build_rom'):
            main_window.action_build_rom.setEnabled(True)
    elif not enabled:
        main_window.btn_export.setEnabled(False)
        main_window.btn_export.setStyleSheet("")


def disable_mouse_wheel_recursive(main_window, widget):
    for child in widget.findChildren(QSpinBox):
        child.installEventFilter(NoWheelEventFilter(child))
    for child in widget.findChildren(QDoubleSpinBox):
        child.installEventFilter(NoWheelEventFilter(child))
    for child in widget.findChildren(QComboBox):
        child.installEventFilter(NoWheelEventFilter(child))


def _setup_shortcuts(main_window):
    main_window._shortcuts = [
        QShortcut(QKeySequence("Space"),          main_window),
        QShortcut(QKeySequence(Qt.Key_Left),      main_window),
        QShortcut(QKeySequence(Qt.Key_Right),     main_window),
        QShortcut(QKeySequence(Qt.Key_Up),        main_window),
        QShortcut(QKeySequence(Qt.Key_Down),      main_window),
        QShortcut(QKeySequence("Shift+Down"),     main_window),
        QShortcut(QKeySequence("Shift+Up"),       main_window),
        QShortcut(QKeySequence(Qt.Key_Home),      main_window),
        QShortcut(QKeySequence(Qt.Key_End),       main_window),
    ]
    
    for shortcut in main_window._shortcuts:
        shortcut.setContext(Qt.ApplicationShortcut)
    
    sc = main_window._shortcuts
    sc[0].activated.connect(main_window.toggle_play)
    sc[1].activated.connect(main_window.prev_frame)
    sc[2].activated.connect(main_window.next_frame)
    sc[3].activated.connect(main_window.prev_keyframe)
    sc[4].activated.connect(main_window.next_keyframe)
    sc[5].activated.connect(main_window._goto_start_marker)
    sc[6].activated.connect(main_window._goto_end_marker)
    sc[7].activated.connect(main_window.first_frame)
    sc[8].activated.connect(main_window.last_frame)
    
    original_keyPressEvent = main_window.keyPressEvent
    
    def custom_keyPressEvent(event):
        if event.modifiers() == Qt.ControlModifier:
            if event.key() == Qt.Key_PageUp:
                main_window._set_start_frame()
                return
            elif event.key() == Qt.Key_PageDown:
                main_window._set_end_frame()
                return
        original_keyPressEvent(event)
    
    main_window.keyPressEvent = custom_keyPressEvent


def _set_preview_volume(main_window, volume_0_to_1):
    from ui.qt_compat import QT_BACKEND
    vc = main_window.video_controller
    try:
        if QT_BACKEND == "PySide6":
            if vc.audio_output is not None:
                vc.audio_output.setVolume(volume_0_to_1)
        else:
            vc.media_player.setVolume(int(volume_0_to_1 * 100))
    except Exception:
        pass


def _on_mute_toggled(main_window):
    muted = not getattr(main_window, '_preview_muted', False)
    main_window._preview_muted = muted
    main_window.btn_mute.setText("🔈" if muted else "🔊")
    if muted:
        _set_preview_volume(main_window, 0.0)
    else:
        vol = main_window.volume_slider.value() / 100.0
        _set_preview_volume(main_window, vol)


def _on_volume_changed(main_window, value):
    if getattr(main_window, '_preview_muted', False):
        return
    _set_preview_volume(main_window, value / 100.0)


def _on_audio_format_changed(main_window, format_str):
    if main_window.no_audio_check.isChecked():
        return
    main_window.adpcm_note_label.setVisible(format_str == "ADPCM")
    if format_str == "ADPCM":
        main_window.sample_rate.setToolTip(main_window.tr("audio_sample_rate_tooltip_adpcm"))
    else:
        main_window.sample_rate.setToolTip(main_window.tr("audio_sample_rate_tooltip_pcm"))


def _on_no_audio_toggled(main_window, checked):
    for w in (
        main_window._lbl_audio_format,
        main_window.audio_format,
        main_window._lbl_sample_rate,
        main_window.sample_rate,
        main_window._lbl_volume,
        main_window.volume,
        main_window.adpcm_note_label,
    ):
        w.setEnabled(not checked)
    if checked:
        main_window.adpcm_note_label.setVisible(False)


def _on_skip_video_toggled(main_window, checked):
    main_enabled = main_window.btn_play.isEnabled() if hasattr(main_window, 'btn_play') else False
    for checkbox in main_window.button_checkboxes:
        checkbox.setEnabled(main_enabled and checked)
    if checked:
        _ensure_at_least_one_button_selected(main_window)


def _on_button_toggled(main_window, checked, sender_cb):
    if not checked:
        any_other_selected = any(cb.isChecked() for cb in main_window.button_checkboxes if cb != sender_cb)
        if not any_other_selected:
            sender_cb.setChecked(True)


def _ensure_at_least_one_button_selected(main_window):
    any_selected = any(cb.isChecked() for cb in main_window.button_checkboxes)
    if not any_selected:
        for cb in main_window.button_checkboxes:
            if cb.text() == "A":
                cb.setChecked(True)
                break
