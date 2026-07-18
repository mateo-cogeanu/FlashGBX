# ui/main_window/video_ops.py
# Modified for FlashGBX on 2026-07-18: preflight ROM compiler checks.
import os
import sys
import shutil
import contextlib
from pathlib import Path

import cv2
import numpy as np

from ui.qt_compat import (
    QT_BACKEND, QFileDialog, QMessageBox, QLabel, QPixmap, QImage, QStandardPaths,
    Qt, get_keep_aspect_ratio, get_smooth_transformation,
    setup_media_player,
)

os.environ.setdefault("QT_LOGGING_RULES", "*.debug=false;*.info=false;*.warning=false;qt.multimedia.*=false")
os.environ.setdefault("AV_LOG_LEVEL", "panic")

if os.name == 'nt':
    @contextlib.contextmanager
    def suppress_ffmpeg_console():
        original_stderr_fd = os.dup(2)
        devnull_fd = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull_fd, 2)
        os.close(devnull_fd)
        try:
            yield
        finally:
            os.dup2(original_stderr_fd, 2)
            os.close(original_stderr_fd)
else:
    @contextlib.contextmanager
    def suppress_ffmpeg_console():
        with open(os.devnull, 'w') as f:
            old_stderr = sys.stderr
            sys.stderr = f
            try:
                yield
            finally:
                sys.stderr = old_stderr


def open_video_dialog(main_window):
    remember = (main_window.config_manager and
                main_window.config_manager.getboolean('SETTINGS', 'remember_file_paths', False))

    if main_window._session_last_video_dir and os.path.exists(main_window._session_last_video_dir):
        default_dir = main_window._session_last_video_dir
    elif remember:
        default_dir = main_window.config_manager.get('PATHS', 'last_video_path', '')
        if default_dir:
            default_dir = os.path.dirname(default_dir)
        if not default_dir or not os.path.exists(default_dir):
            default_dir = QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation)
    else:
        default_dir = QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation)

    path, _ = QFileDialog.getOpenFileName(
        main_window, main_window.tr("open_video_title"), default_dir, main_window.tr("video_files_filter")
    )
    if path:
        load_video(main_window, path)


def load_video(main_window, path):
    from .utils import _update_range_label, _update_time_display
    from .config import _save_last_video
    
    if main_window.video_controller.is_playing:
        main_window.video_controller.toggle_playback()
        main_window.btn_play.setText("▶")
        
    try:
        with suppress_ffmpeg_console():
            if not main_window.video_controller.load_video(path):
                raise Exception(main_window.tr("cannot_open_video", default="Cannot open video file:\n{path}", path=path))

            main_window.video_path = path
            main_window._session_last_video_dir = os.path.dirname(path)
            if main_window.config_manager and main_window.config_manager.getboolean('SETTINGS', 'remember_file_paths', False):
                _save_last_video(main_window, path)

            duration_str = _format_time(main_window, main_window.video_controller.total_frames - 1)
            main_window.lbl_info.setText(
                main_window.tr("video_info",
                               name=Path(path).name,
                               width=main_window.video_controller.width,
                               height=main_window.video_controller.height,
                               frames=main_window.video_controller.total_frames,
                               fps=main_window.video_controller.fps,
                               duration=duration_str)
            )

            main_window.timeline.setMaximum(main_window.video_controller.total_frames - 1)
            main_window.frame_spin.setMaximum(main_window.video_controller.total_frames - 1)

            _update_range_label(main_window)
            _update_time_display(main_window)

            setup_media_player(main_window.video_controller.media_player, str(path))
            _show_frame(main_window, 0)

            main_window._set_controls_enabled(True)
            from ui.qt_compat import QCoreApplication
            QCoreApplication.processEvents() 

            main_window._set_controls_enabled(True)
        return True
    except Exception as e:
        QMessageBox.critical(main_window, main_window.tr("load_video_error_title"),
                             main_window.tr("load_video_error_msg", error=str(e)))
        return False


def _get_build_functions(project_root):
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "_gba_main", str(project_root / "main.py"))
    mod = importlib.util.module_from_spec(spec)
    import signal as _signal
    import types
    _orig = _signal.signal
    _signal.signal = lambda *a, **kw: None
    try:
        spec.loader.exec_module(mod)
    finally:
        _signal.signal = _orig
    return mod.encode_video, mod.build_gba, mod.check_devkitpro


def _lock_ui(main_window, locked):
    for menu in (main_window._menu_file, main_window._menu_presets,
                 main_window._menu_settings, main_window._menu_help):
        if menu is not None:
            try:
                menu.setEnabled(not locked)
            except Exception:
                pass

    for sc in getattr(main_window, '_shortcuts', []):
        try:
            sc.setEnabled(not locked)
        except Exception:
            pass

    main_window._is_exporting = locked

    param_widgets = [
        main_window.btn_play, main_window.btn_prev_frame, main_window.btn_next_frame,
        main_window.btn_prev_keyframe, main_window.btn_next_keyframe,
        main_window.btn_mark_start, main_window.btn_mark_end,
        main_window.btn_goto_start, main_window.btn_goto_end,
        main_window.btn_first_frame, main_window.btn_last_frame,
        main_window.timeline, main_window.frame_spin,
        main_window.crop_edit, main_window.letterbox_check,
        main_window.btn_apply_filters, main_window.show_preview_check,
        main_window.rom_name_edit, main_window.btn_browse_output,
        main_window.btn_mute, main_window.volume_slider,
        main_window.fps_combo, main_window.iframe_interval,
        main_window.diff_threshold, main_window.variance_threshold,
        main_window.color_fallback_threshold, main_window.force_i_threshold,
        main_window.codebook_size, main_window.kmeans_spin,
        main_window.iframe_weight, main_window.motion_thresh,
        main_window.dither_check, main_window.motion_check,
        main_window.audio_format, main_window.sample_rate,
        main_window.volume, main_window.no_audio_check,
        main_window.workers_spin, main_window.preset_combo,
        main_window.btn_reload_preset,
        main_window.skip_video_check,
        main_window.remember_paths_action,
    ]
    for w in param_widgets:
        if w is not None:
            try:
                w.setEnabled(not locked)
            except Exception:
                pass
    if hasattr(main_window, 'action_build_rom'):
        main_window.action_build_rom.setEnabled(not locked)
    for cb in main_window.button_checkboxes:
        if cb is not None:
            try:
                cb.setEnabled(not locked and main_window.skip_video_check.isChecked())
            except Exception:
                pass


def _cleanup_conversion_dirs(project_root, include_output=False, scope="all"):
    tmp = project_root / "temp"
    if tmp.exists():
        shutil.rmtree(str(tmp), ignore_errors=True)

    if scope == "all":
        for d in ("video", "build"):
            p = project_root / d
            if p.exists():
                shutil.rmtree(str(p), ignore_errors=True)
        if include_output:
            for p in (project_root / "output", project_root / "GBA_Video.gba"):
                if p.is_dir():
                    shutil.rmtree(str(p), ignore_errors=True)
                elif p.exists():
                    p.unlink(missing_ok=True)

    elif scope == "video_only":
        video_dir = project_root / "video"
        if video_dir.exists():
            for f in video_dir.glob("video_data*"):
                try:
                    f.unlink()
                except Exception:
                    pass
            for f in ("clip_lookup_table.bin", "big_block_offsets.bin",
                      "zone_block_offsets.bin", "zone_motion_offsets.bin"):
                p = video_dir / f
                if p.exists():
                    try:
                        p.unlink()
                    except Exception:
                        pass
        inc = project_root / "include" / "video" / "video_data.h"
        if inc.exists():
            inc.unlink(missing_ok=True)
        build_dir = project_root / "build"
        if build_dir.exists():
            shutil.rmtree(str(build_dir), ignore_errors=True)

    elif scope == "audio_only":
        video_dir = project_root / "video"
        if video_dir.exists():
            for f in video_dir.glob("audio_data*"):
                try:
                    f.unlink()
                except Exception:
                    pass
            for f in ("frame_audio_offsets.bin", "i_frame_audio_offsets.bin"):
                p = video_dir / f
                if p.exists():
                    try:
                        p.unlink()
                    except Exception:
                        pass
        inc = project_root / "include" / "video" / "audio_data.h"
        if inc.exists():
            inc.unlink(missing_ok=True)
        build_dir = project_root / "build"
        if build_dir.exists():
            shutil.rmtree(str(build_dir), ignore_errors=True)


def _snapshot_encode_state(main_window, encode_kwargs):
    vc = main_window.video_controller
    return {
        "video_path":    main_window.video_path,
        "start_frame":   vc.start_frame,
        "end_frame":     vc.end_frame,
        "fps":                      encode_kwargs.get("fps"),
        "letterbox":                encode_kwargs.get("letterbox"),
        "crop":                     encode_kwargs.get("crop"),
        "i_frame_interval":         encode_kwargs.get("i_frame_interval"),
        "diff_threshold":           encode_kwargs.get("diff_threshold"),
        "force_i_threshold":        encode_kwargs.get("force_i_threshold"),
        "variance_threshold":       encode_kwargs.get("variance_threshold"),
        "color_fallback_threshold": encode_kwargs.get("color_fallback_threshold"),
        "codebook_size":            encode_kwargs.get("codebook_size"),
        "kmeans_max_iter":          encode_kwargs.get("kmeans_max_iter"),
        "i_frame_weight":           encode_kwargs.get("i_frame_weight"),
        "dither":                   encode_kwargs.get("dither"),
        "no_motion_compensation":   encode_kwargs.get("no_motion_compensation"),
        "motion_update_threshold":  encode_kwargs.get("motion_update_threshold"),
        "max_workers":              encode_kwargs.get("max_workers"),
        "audio_sample_rate": encode_kwargs.get("audio_sample_rate"),
        "audio_format":      encode_kwargs.get("audio_format"),
        "volume":            encode_kwargs.get("volume"),
        "no_audio":          encode_kwargs.get("no_audio"),
        "skip_key":          encode_kwargs.get("skip_key"),
    }


def _detect_rebuild_scope(main_window, encode_kwargs, project_root):
    from pathlib import Path as _Path

    prev = getattr(main_window, '_last_encode_state', None)

    if prev is None:
        return "all"

    vd_bin   = project_root / "video" / "video_data.bin"
    vd_h     = project_root / "include" / "video" / "video_data.h"
    ad_bin   = project_root / "video" / "audio_data.bin"
    ad_h     = project_root / "include" / "video" / "audio_data.h"
    no_audio = encode_kwargs.get("no_audio", False)

    video_artifacts_ok = vd_bin.exists() and vd_h.exists()
    audio_artifacts_ok = no_audio or (ad_bin.exists() and ad_h.exists())

    cur = _snapshot_encode_state(main_window, encode_kwargs)

    _VIDEO_SOURCE_KEYS = {"video_path", "start_frame", "end_frame"}
    _VIDEO_ENCODE_KEYS = {
        "fps", "letterbox", "crop", "i_frame_interval", "diff_threshold",
        "force_i_threshold", "variance_threshold", "color_fallback_threshold",
        "codebook_size", "kmeans_max_iter", "i_frame_weight", "dither",
        "no_motion_compensation", "motion_update_threshold", "max_workers",
    }
    _AUDIO_KEYS = {"audio_sample_rate", "audio_format", "volume", "no_audio", "skip_key"}

    source_changed = any(cur[k] != prev.get(k) for k in _VIDEO_SOURCE_KEYS)
    video_changed  = any(cur[k] != prev.get(k) for k in _VIDEO_ENCODE_KEYS)
    audio_changed  = any(cur[k] != prev.get(k) for k in _AUDIO_KEYS)

    if source_changed:
        return "all"

    if video_changed and audio_changed:
        return "all"

    if video_changed:
        return "video_only" if audio_artifacts_ok else "all"

    if audio_changed:
        return "audio_only" if video_artifacts_ok else "all"

    if video_artifacts_ok and audio_artifacts_ok:
        return "rom_only"

    return "all"


def _estimate_size_warning(main_window):
    GBA_ROM_LIMIT = 32 * 1024 * 1024
    STATIC_OVERHEAD = 512 * 1024
    USABLE = GBA_ROM_LIMIT - STATIC_OVERHEAD

    vc = main_window.video_controller
    fps_src = vc.fps or 24.0
    start_f = vc.start_frame
    end_f   = vc.end_frame
    total_frames_src = vc.total_frames or 1

    target_fps   = main_window.fps_combo.currentData() or 9.9546
    i_interval   = main_window.iframe_interval.value()
    codebook_sz  = main_window.codebook_size.value()
    no_audio     = main_window.no_audio_check.isChecked()
    sample_rate  = main_window.sample_rate.value()
    audio_fmt    = main_window.audio_format.currentText().lower()

    if end_f > start_f:
        duration_s = (end_f - start_f + 1) / fps_src
    else:
        duration_s = total_frames_src / fps_src

    total_gba_frames = duration_s * target_fps

    INDICES_BYTES   = 120 * 80 * 2
    CODEBOOK_BYTES  = codebook_sz * 12
    i_frame_bytes   = CODEBOOK_BYTES + INDICES_BYTES
    p_frame_bytes   = int(INDICES_BYTES * 0.40)

    i_frame_ratio   = 1.0 / i_interval
    avg_frame_bytes = i_frame_ratio * i_frame_bytes + (1 - i_frame_ratio) * p_frame_bytes
    video_bytes     = int(avg_frame_bytes * total_gba_frames)

    if no_audio:
        audio_bytes = 0
    elif audio_fmt == "adpcm":
        audio_bytes = int(sample_rate * duration_s * 0.5)
    else:
        audio_bytes = int(sample_rate * duration_s)

    total_est = video_bytes + audio_bytes
    est_mb    = total_est / (1024 * 1024)
    limit_mb  = USABLE   / (1024 * 1024)

    if total_est <= USABLE:
        return None

    tr = main_window.tr
    over_mb = est_mb - limit_mb

    return (
        f"<b>{tr('size_warning_title', default='Size Warning')}</b><br><br>"
        + tr(
            "size_warning_msg",
            default=(
                "The estimated output size is <b>{est_mb:.1f} MB</b>, which exceeds "
                "the GBA ROM limit of <b>{limit_mb:.0f} MB</b> by ~{over_mb:.1f} MB.<br><br>"
                "The build will likely fail after a long conversion. Consider reducing "
                "the video duration, FPS, or sample rate."
            ),
            est_mb=est_mb,
            limit_mb=limit_mb,
            over_mb=over_mb,
        )
    )


def export_video(main_window):
    import threading
    import shutil
    from pathlib import Path as _Path

    if not main_window.video_path:
        QMessageBox.warning(main_window, main_window.tr("export_error_title"),
                            main_window.tr("no_video_loaded"))
        return
    if not main_window.output_folder:
        QMessageBox.warning(main_window, main_window.tr("export_error_title"),
                            main_window.tr("output_folder_placeholder"))
        return

    if main_window.video_controller.is_playing:
        main_window.toggle_play()
        main_window.btn_play.setText("▶")

    rom_name = main_window.rom_name_edit.text().strip()
    if not rom_name or any(c in rom_name for c in r'\/:*?"<>|'):
        QMessageBox.warning(
            main_window,
            main_window.tr("rom_name_invalid_title", default="Invalid ROM Name"),
            main_window.tr("rom_name_invalid", default='Invalid filename. Avoid: \\ / : * ? " < > |'),
        )
        return

    # FlashGBX integration: a ROM export cannot finish without devkitPro. Check
    # before spending minutes encoding, and provide the setup link immediately.
    from utils.system_utils import get_base_dir
    project_root = get_base_dir()
    _, _, check_devkitpro = _get_build_functions(project_root)
    if not check_devkitpro(silent=True):
        message = QMessageBox(main_window)
        message.setWindowTitle(main_window.tr("export_error_title"))
        message.setIcon(QMessageBox.Warning)
        message.setTextFormat(Qt.RichText)
        message.setText(
            "devkitPro with the <b>gba-dev</b> tools is required to export a "
            "standalone ROM.<br><br>Install it from "
            "<a href='https://devkitpro.org/wiki/Getting_Started'>"
            "devkitpro.org/wiki/Getting_Started</a>, then restart GBA Video Maker."
        )
        label = message.findChild(QLabel, "qt_msgbox_label")
        if label is not None:
            label.setOpenExternalLinks(True)
            label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        message.exec_()
        return

    _warn = _estimate_size_warning(main_window)
    if _warn:
        from ui.qt_compat import QDialog, QVBoxLayout, QPushButton, QHBoxLayout
        dlg = QDialog(main_window)
        dlg.setWindowTitle(main_window.tr("size_warning_title", default="Size Warning"))
        dlg.setWindowFlags(
            dlg.windowFlags()
            & ~Qt.WindowContextHelpButtonHint
            & ~Qt.WindowMaximizeButtonHint
        )
        dlg.setFixedWidth(460)
        layout = QVBoxLayout(dlg)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)
        lbl = QLabel(_warn)
        lbl.setWordWrap(True)
        lbl.setTextFormat(Qt.RichText)
        layout.addWidget(lbl)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_cancel = QPushButton(main_window.tr("cancel", default="Cancel"))
        btn_cancel.setFixedWidth(90)
        btn_cancel.clicked.connect(dlg.reject)
        btn_row.addWidget(btn_cancel)
        btn_continue = QPushButton(main_window.tr("size_warning_proceed", default="Continue anyway"))
        btn_continue.setFixedWidth(150)
        btn_continue.setDefault(True)
        btn_continue.clicked.connect(dlg.accept)
        btn_row.addWidget(btn_continue)
        layout.addLayout(btn_row)
        if dlg.exec_() != QDialog.Accepted:
            return

    vc  = main_window.video_controller
    fps = vc.fps

    start_f  = vc.start_frame
    end_f    = vc.end_frame
    start_time = start_f / fps if fps > 0 else 0.0
    duration   = (end_f - start_f + 1) / fps if fps > 0 and end_f > start_f else None

    letterbox = main_window.letterbox_check.isChecked()
    crop_text = main_window.crop_edit.text().strip() or None

    if crop_text:
        crop_error = _validate_crop(main_window)
        if crop_error:
            QMessageBox.warning(main_window, main_window.tr("error_dialog_title", default="Error"), crop_error)
            return

    _BUTTON_BITS = {"A": 0x0001, "B": 0x0002, "Select": 0x0004,
                    "Start": 0x0008, "R": 0x0010, "L": 0x0020}
    skip_enabled = main_window.skip_video_check.isChecked()
    if skip_enabled:
        skip_key = 0
        for cb in main_window.button_checkboxes:
            if cb.isChecked():
                skip_key |= _BUTTON_BITS.get(cb.text(), 0)
        if skip_key == 0:
            skip_key = 0x0001
    else:
        skip_key = 0

    encode_kwargs = {
        "fps":                      main_window.fps_combo.currentData(),
        "start_time":               start_time if start_f > 0 else None,
        "duration":                 duration,
        "letterbox":                letterbox,
        "crop":                     crop_text,
        "i_frame_interval":         main_window.iframe_interval.value(),
        "audio_sample_rate":        str(main_window.sample_rate.value()),
        "audio_format":             main_window.audio_format.currentText().lower(),
        "no_audio":                 main_window.no_audio_check.isChecked(),
        "skip_key":                 skip_key,
        "dither":                   main_window.dither_check.isChecked(),
        "max_workers":              main_window.workers_spin.value(),
        "diff_threshold":           main_window.diff_threshold.value(),
        "variance_threshold":       main_window.variance_threshold.value(),
        "no_motion_compensation":   not main_window.motion_check.isChecked(),
        "motion_update_threshold":  int(main_window.motion_thresh.value()),
        "color_fallback_threshold": main_window.color_fallback_threshold.value(),
        "codebook_size":            main_window.codebook_size.value(),
        "kmeans_max_iter":          main_window.kmeans_spin.value(),
        "i_frame_weight":           main_window.iframe_weight.value(),
        "force_i_threshold":        main_window.force_i_threshold.value(),
        "volume":                   main_window.volume.value(),
    }

    output_folder = _Path(main_window.output_folder)
    rebuild_scope = _detect_rebuild_scope(main_window, encode_kwargs, project_root)

    _lock_ui(main_window, locked=True)
    
    main_window.btn_export.setEnabled(True)
    main_window.btn_export.setText(main_window.tr("cancel", default="Cancel"))
    main_window.btn_export.setStyleSheet("background-color: #CC0000; color: white; font-weight: bold; padding: 5px;")
    
    cancel_event = threading.Event()

    def _on_cancel_clicked():
        msg_box = QMessageBox(main_window)
        msg_box.setWindowTitle(main_window.tr("cancel_confirm_title", default="Cancel Conversion"))
        msg_box.setText(main_window.tr("cancel_confirm_msg", default="Are you sure you want to cancel the ongoing conversion?"))
        msg_box.setIcon(QMessageBox.Question)
        
        yes_btn = msg_box.addButton(main_window.tr("yes", default="Yes"), QMessageBox.YesRole)
        no_btn = msg_box.addButton(main_window.tr("no", default="No"), QMessageBox.NoRole)
        msg_box.setDefaultButton(no_btn)
        
        msg_box.exec_()
        
        if msg_box.clickedButton() == yes_btn:
            cancel_event.set()
            main_window.btn_export.setEnabled(False)
            main_window.btn_export.setText(main_window.tr("cancelling", default="Cancelling…"))

    try:
        main_window.btn_export.clicked.disconnect()
    except TypeError:
        pass
    main_window.btn_export.clicked.connect(_on_cancel_clicked)

    def _copy_video_files_to_output(project_root, output_folder):
        output_src = project_root / "output"
        output_dst = output_folder / "output"
        try:
            if output_src.exists():
                if output_dst.exists():
                    shutil.rmtree(str(output_dst))
                shutil.copytree(str(output_src), str(output_dst))
        except Exception:
            pass

    def _run():
        try:
            _, build_gba, check_devkitpro = _get_build_functions(project_root)

            if rebuild_scope == "all":
                _cleanup_conversion_dirs(project_root, scope="all")
                main_window.export_phase_changed.emit(
                    main_window.tr("phase_encoding", default="Encoding video…"))
                encoder_cmd = _build_encoder_cmd(
                    main_window.video_path,
                    str(project_root / "video" / "video_data"),
                    encode_kwargs,
                )
                encode_ok = _run_encoder_with_progress(main_window, encoder_cmd, project_root, cancel_event)

            elif rebuild_scope == "video_only":
                _cleanup_conversion_dirs(project_root, scope="video_only")
                main_window.export_phase_changed.emit(
                    main_window.tr("phase_encoding", default="Encoding video…"))
                video_kwargs = dict(encode_kwargs, no_audio=True)
                encoder_cmd = _build_encoder_cmd(
                    main_window.video_path,
                    str(project_root / "video" / "video_data"),
                    video_kwargs,
                )
                encode_ok = _run_encoder_with_progress(main_window, encoder_cmd, project_root, cancel_event)

            elif rebuild_scope == "audio_only":
                _cleanup_conversion_dirs(project_root, scope="audio_only")
                main_window.export_phase_changed.emit(
                    main_window.tr("phase_encoding_audio", default="Encoding audio…"))
                audio_cmd = _build_encoder_cmd(
                    main_window.video_path,
                    str(project_root / "video" / "video_data"),
                    encode_kwargs,
                )
                audio_cmd.append("--audio-only")
                encode_ok = _run_encoder_with_progress(main_window, audio_cmd, project_root, cancel_event)

            else:
                encode_ok = True
                build_dir = project_root / "build"
                if build_dir.exists():
                    shutil.rmtree(str(build_dir), ignore_errors=True)

            if not encode_ok:
                if cancel_event.is_set():
                    main_window.export_timer_stop.emit()
                    main_window.export_error.emit(main_window.tr("encode_canceled", default="Conversion canceled by user."))
                else:
                    main_window.export_timer_stop.emit()
                    main_window.export_error.emit(main_window.tr("encode_failed", default="Encoding failed."))
                return

            if cancel_event.is_set():
                main_window.export_timer_stop.emit()
                main_window.export_error.emit(main_window.tr("encode_canceled", default="Conversion canceled by user."))
                return

            if not check_devkitpro(silent=True):
                main_window.export_timer_stop.emit()
                _copy_video_files_to_output(project_root, output_folder)
                main_window._last_encode_state = _snapshot_encode_state(main_window, encode_kwargs)
                main_window.export_error.emit(main_window.tr("devkitpro_missing",
                    default="devkitPro not found. ROM build skipped.\nInstall devkitPro to compile."))
                return

            main_window.export_phase_changed.emit(
                main_window.tr("phase_building", default="Building ROM…"))

            build_ok, build_err = build_gba(silent=True)
            if not build_ok:
                main_window.export_timer_stop.emit()
                main_window._last_encode_state = _snapshot_encode_state(main_window, encode_kwargs)
                err_msg = main_window.tr("build_failed", default="ROM build failed.")
                if build_err:
                    err_msg += f"\n\n{build_err}"
                main_window.export_error.emit(err_msg)
                return

            gba_src = project_root / "GBA_Video.gba"
            rom_name = main_window.rom_name_edit.text().strip()
            gba_dst = output_folder / f"{rom_name}.gba"
            try:
                shutil.copy2(str(gba_src), str(gba_dst))
            except Exception as e:
                main_window.export_timer_stop.emit()
                main_window.export_error.emit(str(e))
                return

            output_src = project_root / "output"
            output_dst = output_folder / "output"
            try:
                if output_src.exists():
                    if output_dst.exists():
                        shutil.rmtree(str(output_dst))
                    shutil.copytree(str(output_src), str(output_dst))
            except Exception as e:
                main_window.export_timer_stop.emit()
                main_window.export_error.emit(str(e))
                return

            memuse_path = project_root / "build" / "memuse.txt"
            rom_info = ""
            if memuse_path.exists():
                try:
                    with open(str(memuse_path)) as f:
                        rom_info = f.read().strip()
                except Exception:
                    pass

            main_window._last_encode_state = _snapshot_encode_state(main_window, encode_kwargs)

            main_window.export_timer_stop.emit()
            main_window.export_success_with_info.emit(rom_info)

        except Exception as e:
            main_window.export_timer_stop.emit()
            main_window.export_error.emit(str(e))

        except Exception as e:
            main_window.export_timer_stop.emit()
            main_window.export_error.emit(str(e))

    threading.Thread(target=_run, daemon=True).start()


def _validate_crop(main_window):
    crop_text = main_window.crop_edit.text().strip()
    if not crop_text:
        return None
    try:
        parts = [int(p.strip()) for p in crop_text.split(',')]
        if len(parts) != 4:
            return main_window.tr("crop_invalid_format", default="Crop must be x,y,w,h (4 integers)")
        x, y, cw, ch = parts
        src_w = main_window.video_controller.width
        src_h = main_window.video_controller.height
        if x < 0 or y < 0 or cw <= 0 or ch <= 0:
            return main_window.tr("crop_negative", default="Crop values must be positive")
        if x + cw > src_w or y + ch > src_h:
            return main_window.tr(
                "crop_out_of_range",
                default=f"Crop out of range. Source is {src_w}×{src_h}",
                src_w=src_w, src_h=src_h,
            )
        return None
    except ValueError:
        return main_window.tr("crop_invalid_format", default="Crop must be x,y,w,h (4 integers)")


def update_preview(main_window):
    if not main_window.video_controller.cap or main_window._is_closing:
        return
    crop_error = _validate_crop(main_window)
    if crop_error:
        QMessageBox.warning(main_window, main_window.tr("error_dialog_title", default="Error"), crop_error)
        return
    _show_current_frame(main_window)


def _apply_filters(main_window, qimg):
    try:
        if qimg.format() != QImage.Format_RGB888:
            qimg = qimg.convertToFormat(QImage.Format_RGB888)

        w, h = qimg.width(), qimg.height()
        ptr = qimg.bits()
        data = ptr.tobytes() if hasattr(ptr, 'tobytes') else bytes(ptr)

        bytes_per_pixel = 3
        true_bytes_per_line = w * bytes_per_pixel
        padding = (4 - (true_bytes_per_line % 4)) % 4
        expected_line_size = true_bytes_per_line + padding

        cropped_data = b''
        for y in range(h):
            start = y * expected_line_size
            cropped_data += data[start : start + true_bytes_per_line]

        arr = np.frombuffer(cropped_data, dtype=np.uint8).reshape(h, w, 3).copy()

        crop_text = main_window.crop_edit.text().strip()
        if crop_text:
            try:
                parts = [int(p.strip()) for p in crop_text.split(',')]
                if len(parts) == 4:
                    x, y, cw, ch = parts
                    x, y = max(0, x), max(0, y)
                    cw, ch = min(cw, arr.shape[1] - x), min(ch, arr.shape[0] - y)
                    if cw > 0 and ch > 0:
                        arr = arr[y:y+ch, x:x+cw]
            except ValueError:
                pass

        rw, rh = main_window.GBA_WIDTH, main_window.GBA_HEIGHT
        src_h, src_w = arr.shape[:2]
        src_aspect = src_w / src_h
        dst_aspect = rw / rh

        if main_window.letterbox_check.isChecked():
            if dst_aspect > src_aspect:
                new_h = rh
                new_w = int(rh * src_aspect)
            else:
                new_w = rw
                new_h = int(rw / src_aspect)

            resized = cv2.resize(arr, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
            top = (rh - new_h) // 2
            bottom = rh - new_h - top
            left = (rw - new_w) // 2
            right = rw - new_w - left
            arr = cv2.copyMakeBorder(resized, top, bottom, left, right,
                                     cv2.BORDER_CONSTANT, value=[0, 0, 0])
        else:
            arr = cv2.resize(arr, (rw, rh), interpolation=cv2.INTER_LINEAR)

        h, w, ch = arr.shape
        return QImage(arr.data, w, h, ch * w, QImage.Format_RGB888).copy()
    except Exception as e:
        print(f"[Error] Filter error: {e}")
        return qimg


def _display_frame(main_window, qimg, frame_num):
    transform = _get_transformation_mode(main_window)

    main_window.video_label.set_range(
        main_window.video_controller.start_frame,
        main_window.video_controller.end_frame,
        frame_num,
        main_window.video_controller.total_frames,
    )

    if main_window.show_preview_check.isChecked():
        processed = _apply_filters(main_window, qimg)
        if processed:
            pixmap = QPixmap.fromImage(processed)
            scaled = pixmap.scaled(main_window.video_label.size(), get_keep_aspect_ratio(), transform)
            main_window.video_label.setPixmap(scaled)
        else:
            pixmap = QPixmap.fromImage(qimg)
            scaled = pixmap.scaled(main_window.video_label.size(), get_keep_aspect_ratio(), transform)
            main_window.video_label.setPixmap(scaled)
    else:
        pixmap = QPixmap.fromImage(qimg)
        scaled = pixmap.scaled(main_window.video_label.size(), get_keep_aspect_ratio(), transform)
        main_window.video_label.setPixmap(scaled)


def _frame_to_qimage(main_window, frame):
    frame_rgb = frame
    
    h, w, ch = frame_rgb.shape
    bytes_per_line = ch * w
    
    return QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888).copy()


def _show_frame(main_window, frame_num):
    from .utils import _update_time_display
    if not main_window.video_controller.cap or main_window._is_closing:
        return

    frame = main_window.video_controller.seek(frame_num)
    if frame is not None:
        qimg = _frame_to_qimage(main_window, frame)
        _display_frame(main_window, qimg, frame_num)

    _update_time_display(main_window)
    main_window.timeline.blockSignals(True)
    main_window.timeline.setValue(main_window.video_controller.current_frame)
    main_window.timeline.blockSignals(False)
    main_window.frame_spin.blockSignals(True)
    main_window.frame_spin.setValue(main_window.video_controller.current_frame)
    main_window.frame_spin.blockSignals(False)


def _show_current_frame(main_window):
    if not main_window.video_controller.cap or main_window._is_closing:
        return
    frame = main_window.video_controller.get_frame(main_window.video_controller.current_frame)
    if frame is not None:
        qimg = _frame_to_qimage(main_window, frame)
        _display_frame(main_window, qimg, main_window.video_controller.current_frame)


def _get_transformation_mode(main_window):
    if main_window.video_controller.is_playing:
        if QT_BACKEND == "PySide6":
            return Qt.TransformationMode.FastTransformation
        return Qt.FastTransformation
    return get_smooth_transformation()


def _seek_frame(main_window, frame_num):
    if not main_window.video_controller.cap or main_window._is_closing:
        return
    if main_window.video_controller.is_playing:
        main_window.toggle_play()
    _show_frame(main_window, frame_num)


def _set_start_frame(main_window):
    from .utils import _update_range_label, _format_time
    main_window.video_controller.start_frame = main_window.video_controller.current_frame
    _update_range_label(main_window)
    main_window.video_label.set_range(
        main_window.video_controller.start_frame,
        main_window.video_controller.end_frame,
        main_window.video_controller.current_frame,
        main_window.video_controller.total_frames,
    )
    QMessageBox.information(main_window, main_window.tr("start_set_title"),
                            main_window.tr("start_set_msg",
                                           frame=main_window.video_controller.start_frame,
                                           time=_format_time(main_window, main_window.video_controller.start_frame)))


def _set_end_frame(main_window):
    from .utils import _update_range_label, _format_time
    main_window.video_controller.end_frame = main_window.video_controller.current_frame
    _update_range_label(main_window)
    main_window.video_label.set_range(
        main_window.video_controller.start_frame,
        main_window.video_controller.end_frame,
        main_window.video_controller.current_frame,
        main_window.video_controller.total_frames,
    )
    QMessageBox.information(main_window, main_window.tr("end_set_title"),
                            main_window.tr("end_set_msg",
                                           frame=main_window.video_controller.end_frame,
                                           time=_format_time(main_window, main_window.video_controller.end_frame)))


def _goto_start_marker(main_window):
    _show_frame(main_window, main_window.video_controller.start_frame)


def _goto_end_marker(main_window):
    _show_frame(main_window, main_window.video_controller.end_frame)


def _on_frame_ready(main_window, frame_num, frame):
    from .utils import _update_time_display
    if main_window._is_closing:
        return

    vc = main_window.video_controller
    
    if not vc.is_playing or vc.current_frame != frame_num:
        return

    if frame is not None:
        qimg = _frame_to_qimage(main_window, frame)
        _display_frame(main_window, qimg, frame_num)

    main_window.frame_spin.blockSignals(True)
    main_window.frame_spin.setValue(frame_num)
    main_window.frame_spin.blockSignals(False)

    main_window.timeline.blockSignals(True)
    main_window.timeline.setValue(frame_num)
    main_window.timeline.blockSignals(False)

    _update_time_display(main_window)


def toggle_play(main_window):
    main_window.video_controller.toggle_playback()


def prev_frame(main_window):
    if main_window.video_controller.current_frame > 0:
        _show_frame(main_window, main_window.video_controller.current_frame - 1)


def next_frame(main_window):
    if main_window.video_controller.current_frame < main_window.video_controller.total_frames - 1:
        _show_frame(main_window, main_window.video_controller.current_frame + 1)


def prev_keyframe(main_window):
    _show_frame(main_window, max(0, main_window.video_controller.current_frame - 30))


def next_keyframe(main_window):
    _show_frame(main_window, min(main_window.video_controller.total_frames - 1,
                                  main_window.video_controller.current_frame + 30))


def first_frame(main_window):
    _show_frame(main_window, 0)


def last_frame(main_window):
    _show_frame(main_window, main_window.video_controller.total_frames - 1)


def _on_playback_state_changed(main_window, is_playing):
    main_window.btn_play.setText("⏸" if is_playing else "▶")


def _on_view_mode_changed(main_window, state):
    is_preview = main_window.show_preview_check.isChecked()
    if is_preview:
        main_window.video_mode_label.setText(main_window.tr("view_preview"))
        main_window.video_mode_label.setStyleSheet("font-weight: bold; color: #00AA00;")
        main_window.video_label.setStyleSheet("border: 2px solid #00AA00; background: black;")
    else:
        main_window.video_mode_label.setText(main_window.tr("view_input"))
        main_window.video_mode_label.setStyleSheet("font-weight: bold; color: #AAAAAA;")
        main_window.video_label.setStyleSheet("border: 2px solid gray; background: black;")

    if main_window.video_controller.cap and not main_window.video_controller.is_playing:
        _show_current_frame(main_window)


def _browse_output_folder(main_window):
    from .config import _save_output_folder
    if not main_window.video_path:
        return

    remember = (main_window.config_manager and
                main_window.config_manager.getboolean('SETTINGS', 'remember_file_paths', False))

    if main_window._session_output_folder and os.path.exists(main_window._session_output_folder):
        default_folder = main_window._session_output_folder
    elif remember:
        default_folder = main_window.config_manager.get('PATHS', 'output_folder', '')
        if not default_folder or not os.path.exists(default_folder):
            default_folder = QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation)
    else:
        default_folder = QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation)

    folder = QFileDialog.getExistingDirectory(
        main_window, main_window.tr("select_output_folder", default="Select Output Folder"), default_folder
    )
    if folder:
        main_window.output_folder = folder
        main_window._session_output_folder = folder
        main_window.output_path_edit.setText(folder)
        main_window.btn_export.setEnabled(True)
        main_window.btn_export.setStyleSheet("background-color: #00AA00; color: white; font-weight: bold; padding: 5px;")
        if hasattr(main_window, 'action_build_rom'):
            main_window.action_build_rom.setEnabled(True)
        if remember:
            _save_output_folder(main_window, folder)


def _format_time(main_window, frame_num):
    from .utils import _format_time as _ft
    return _ft(main_window, frame_num)


def _on_export_progress(main_window, phase_key, percent):
    main_window._current_export_phase_key = phase_key
    phase_label = main_window.translator.tr(phase_key, default=phase_key)
    main_window.lbl_export_status.setText(f"{phase_label}  {percent}%")


def _run_encoder_with_progress(main_window, cmd, project_root, cancel_event=None):
    import subprocess as _sp
    import re as _re
    import threading

    _PREFIX_MAP = [
        ("Source:",                "progress_source"),
        ("Target:",                "progress_target"),
        ("Pre-transcod",           "progress_pretranscode"),
        ("Extracting frames",      "progress_extracting"),
        ("Extracting audio",       "progress_audio"),
        ("Encoding GOP",           "progress_encoding_gop"),
        ("Training codebook",      "progress_training"),
        ("Encoding frames",        "progress_encoding_frames"),
        ("Parallel encoding",      "progress_parallel"),
        ("Writing",                "progress_writing"),
        ("Done.",                  "progress_done"),
    ]

    _PROGRESS_KEYS = {
        "progress_extracting",
        "progress_encoding_gop",
        "progress_training",
        "progress_encoding_frames",
    }

    _PROGRESS_PHASE_MAP = [
        ("gop codebooks",      "progress_encoding_gop"),
        ("sorting codebooks",  "progress_training"),
        ("encoding frames",    "progress_encoding_frames"),
        ("",                   "progress_extracting"),
    ]

    from utils.system_utils import no_window_flags
    import os as _os
    _enc_env = _os.environ.copy()
    _enc_env["PYTHONUNBUFFERED"] = "1"

    proc = _sp.Popen(
        cmd,
        stdout=_sp.PIPE,
        stderr=_sp.STDOUT,
        encoding='utf-8',
        errors='replace',
        creationflags=no_window_flags(),
        env=_enc_env,
    )
    main_window._encoder_proc = proc

    def _cancel_watcher():
        if cancel_event:
            cancel_event.wait()
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except _sp.TimeoutExpired:
                    proc.kill()

    watcher_thread = threading.Thread(target=_cancel_watcher, daemon=True)
    watcher_thread.start()

    _buf = []
    while True:
        ch = proc.stdout.read(1)
        if not ch:
            if proc.poll() is not None:
                break
            continue

        if ch in ('\n', '\r'):
            line = ''.join(_buf).strip()
            _buf.clear()
            if not line:
                continue

            pct_match = _re.search(r'([\d.]+)%', line)
            if pct_match and any(c in line for c in ('░', '█')):
                pct = int(float(pct_match.group(1)))
                phase_key = None
                line_lower = line.lower()
                for prefix, key in _PROGRESS_PHASE_MAP:
                    if prefix and prefix in line_lower:
                        phase_key = key
                        break
                if phase_key is None:
                    _, phase_key = _PROGRESS_PHASE_MAP[-1]
                main_window.export_progress.emit(phase_key, pct)
                continue

            for prefix, key in _PREFIX_MAP:
                if line.startswith(prefix):
                    main_window.export_phase_changed.emit(
                        main_window.translator.tr(key, default=line[:80]))
                    if key in _PROGRESS_KEYS:
                        main_window.export_progress.emit(key, 0)
                    break
        else:
            _buf.append(ch)

    if _buf:
        line = ''.join(_buf).strip()
        if line:
            for prefix, key in _PREFIX_MAP:
                if line.startswith(prefix):
                    main_window.export_phase_changed.emit(
                        main_window.translator.tr(key, default=line[:80]))
                    if key in _PROGRESS_KEYS:
                        main_window.export_progress.emit(key, 0)
                    break

    proc.wait()
    main_window._encoder_proc = None
    if cancel_event and cancel_event.is_set():
        return False
    return proc.returncode == 0


def _build_encoder_cmd(input_path, output_base, encode_kwargs):
    import sys as _sys
    from pathlib import Path as _Path
    from utils.system_utils import get_base_dir
    if getattr(_sys, 'frozen', False):
        cmd = [_sys.executable, "--run-encoder", str(input_path)]
    else:
        encoder_path = get_base_dir() / "encoder" / "video_encoder.py"
        cmd = [_sys.executable, str(encoder_path), str(input_path)]
    kw = encode_kwargs
    if kw.get("fps") is not None:
        cmd += ["--fps", str(kw["fps"])]
    if kw.get("start_time") is not None:
        cmd += ["--start-time", str(kw["start_time"])]
    if kw.get("duration") is not None:
        cmd += ["--duration", str(kw["duration"])]
    if not kw.get("letterbox", True):
        cmd.append("--no-letterbox")
    if kw.get("crop"):
        cmd += ["--crop", str(kw["crop"])]
    if kw.get("i_frame_interval"):
        cmd += ["--i-frame-interval", str(kw["i_frame_interval"])]
    if kw.get("audio_sample_rate") is not None:
        cmd += ["--audio-sample-rate", str(kw["audio_sample_rate"])]
    if kw.get("audio_format"):
        cmd += ["--audio-format", str(kw["audio_format"])]
    if kw.get("no_audio"):
        cmd.append("--no-audio")
    if kw.get("dither", True):
        cmd.append("--dither")
    if kw.get("max_workers"):
        cmd += ["--max-workers", str(kw["max_workers"])]
    if kw.get("diff_threshold") is not None:
        cmd += ["--diff-threshold", str(kw["diff_threshold"])]
    if kw.get("variance_threshold") is not None:
        cmd += ["--variance-threshold", str(kw["variance_threshold"])]
    if kw.get("no_motion_compensation"):
        cmd.append("--no-motion-compensation")
    if kw.get("motion_update_threshold") is not None:
        cmd += ["--motion-update-threshold", str(kw["motion_update_threshold"])]
    if kw.get("color_fallback_threshold") is not None:
        cmd += ["--color-fallback-threshold", str(kw["color_fallback_threshold"])]
    if kw.get("codebook_size") is not None:
        cmd += ["--codebook-size", str(kw["codebook_size"])]
    if kw.get("kmeans_max_iter") is not None:
        cmd += ["--kmeans-max-iter", str(kw["kmeans_max_iter"])]
    if kw.get("i_frame_weight") is not None:
        cmd += ["--i-frame-weight", str(kw["i_frame_weight"])]
    if kw.get("force_i_threshold") is not None:
        cmd += ["--force-i-threshold", str(kw["force_i_threshold"])]
    if kw.get("volume") is not None:
        cmd += ["--volume", str(kw["volume"])]
    if "skip_key" in kw:
        cmd += ["--skip-key", str(kw["skip_key"])]
    cmd += ["--out", str(output_base)]
    return cmd


def _start_export_timer(main_window, phase_text):
    import time
    from ui.qt_compat import QTimer

    main_window._current_export_phase_text = phase_text
    main_window._current_export_phase_key = None
    main_window.lbl_export_status.setText(phase_text)
    main_window.lbl_export_timer.setVisible(True)

    if hasattr(main_window, '_export_timer') and main_window._export_timer and main_window._export_timer.isActive():
        return

    main_window._export_start_time = time.time()
    main_window.lbl_export_timer.setText("00:00:00")

    def _tick():
        elapsed = int(time.time() - main_window._export_start_time)
        h = elapsed // 3600
        m = (elapsed % 3600) // 60
        s = elapsed % 60
        main_window.lbl_export_timer.setText(f"{h:02d}:{m:02d}:{s:02d}")

    main_window._export_timer = QTimer(main_window)
    main_window._export_timer.setInterval(500)
    main_window._export_timer.timeout.connect(_tick)
    main_window._export_timer.start()


def _stop_export_timer(main_window):
    if hasattr(main_window, '_export_timer') and main_window._export_timer:
        main_window._export_timer.stop()
        main_window._export_timer = None


def _parse_memuse(raw_text):
    import re
    result = []
    for line in raw_text.splitlines():
        m = re.match(r'\s*(rom|ewram|iwram):\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+([\d.]+)%', line, re.IGNORECASE)
        if m:
            region = m.group(1).upper()
            used = float(m.group(2))
            used_unit = m.group(3)
            total = float(m.group(4))
            total_unit = m.group(5)
            pct = m.group(6)
            result.append(f"{region}: {used:,.0f} {used_unit} / {total:,.0f} {total_unit}  ({pct}%)")
    return "\n".join(result) if result else ""


def _build_memuse_html(raw_text, tr=None):
    import re

    if tr is None:
        tr = lambda k, default=k, **kw: default

    _REGION_META = {
        "ROM":   {"icon": "💿", "color": "#0066CC", "bg": "#E8F0FE", "label": "ROM"},
        "EWRAM": {"icon": "💾", "color": "#008844", "bg": "#E8F8F0", "label": "EWRAM"},
        "IWRAM": {"icon": "⚡", "color": "#CC8800", "bg": "#FFF5E6", "label": "IWRAM"},
    }

    rows = []
    for line in raw_text.splitlines():
        m = re.match(
            r'\s*(rom|ewram|iwram):\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+([\d.]+)%',
            line, re.IGNORECASE,
        )
        if not m:
            continue
        region = m.group(1).upper()
        used   = float(m.group(2))
        u_unit = m.group(3)
        total  = float(m.group(4))
        t_unit = m.group(5)
        pct    = float(m.group(6))
        rows.append((region, used, u_unit, total, t_unit, pct))

    if not rows:
        return ""

    BAR_W = 120

    def _pct_color(p):
        if p >= 90: return "#CC0000"
        if p >= 75: return "#CC6600"
        return "#008844"

    def _bar(pct, color):
        filled = max(1, min(int(BAR_W * pct / 100), BAR_W))
        empty  = BAR_W - filled
        return (
            f'<table border="0" cellspacing="0" cellpadding="0"'
            f' style="border:1px solid #C8C8C8;border-radius:3px;">'
            f'<tr>'
            f'<td width="{filled}" bgcolor="{color}" style="height:8px;"></td>'
            f'<td width="{empty}"  bgcolor="#C8C8C8" style="height:8px;"></td>'
            f'</tr></table>'
        )

    table_rows = ""
    for region, used, u_unit, total, t_unit, pct in rows:
        meta  = _REGION_META.get(region, {"icon": "📦", "color": "#666", "bg": "#F0F0F0", "label": region})
        color = meta["color"]
        bg    = meta["bg"]
        pc    = _pct_color(pct)
        table_rows += (
            f'<tr bgcolor="{bg}">'
            f'<td style="padding:5px 8px;font-weight:bold;color:{color};">'
            f'{meta["icon"]}&nbsp;{meta["label"]}</td>'
            f'<td style="padding:5px 8px;color:#333;">'
            f'{used:,.0f}&nbsp;{u_unit}&nbsp;/&nbsp;{total:,.0f}&nbsp;{t_unit}</td>'
            f'<td style="padding:5px 10px;">{_bar(pct, color)}</td>'
            f'<td style="padding:5px 4px;font-weight:bold;color:{pc};text-align:right;">'
            f'{pct:.1f}%</td>'
            f'</tr>'
        )

    return (
        '<table border="0" cellspacing="0" cellpadding="0"'
        ' width="100%" style="border-collapse:collapse;font-family:monospace;font-size:11px;">'
        '<tr bgcolor="#E0E0E0">'
        f'<th style="padding:4px 8px;text-align:left;color:#444;">{tr("memuse_region", default="Region")}</th>'
        f'<th style="padding:4px 8px;text-align:left;color:#444;">{tr("memuse_used_total", default="Used / Total")}</th>'
        f'<th style="padding:4px 8px;text-align:left;color:#444;">{tr("memuse_usage", default="Usage")}</th>'
        '<th style="padding:4px 4px;text-align:right;color:#444;">%</th>'
        '</tr>'
        f'{table_rows}'
        '</table>'
    )


def _execute_post_action(main_window, action_key):
    import subprocess as _sp
    import sys as _sys
    if action_key == "on_finish_open_folder":
        folder = getattr(main_window, 'output_folder', None)
        if folder and os.path.exists(folder):
            if _sys.platform == "win32":
                _sp.Popen(["explorer", os.path.normpath(folder)])
            elif _sys.platform == "darwin":
                _sp.Popen(["open", folder])
            else:
                _sp.Popen(["xdg-open", folder])
    elif action_key == "on_finish_open_rom":
        folder = getattr(main_window, 'output_folder', None)
        if folder:
            from pathlib import Path as _Path
            rom_name_edit = getattr(main_window, 'rom_name_edit', None)
            rom_name = rom_name_edit.text().strip() if rom_name_edit else "GBA_Video"
            rom = _Path(folder) / f"{rom_name}.gba"
            if rom.exists():
                if _sys.platform == "win32":
                    _sp.Popen(["cmd", "/c", "start", "", os.path.normpath(str(rom))])
                elif _sys.platform == "darwin":
                    _sp.Popen(["open", str(rom)])
                else:
                    _sp.Popen(["xdg-open", str(rom)])
    elif action_key == "on_finish_shutdown":
        if _sys.platform == "win32":
            _sp.run(["shutdown", "/s", "/t", "0"])
        elif _sys.platform == "darwin":
            _sp.run(["osascript", "-e", 'tell app "System Events" to shut down'])
        else:
            _sp.run(["systemctl", "poweroff"])
    elif action_key == "on_finish_sleep":
        if _sys.platform == "win32":
            _sp.run(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"])
        elif _sys.platform == "darwin":
            _sp.run(["osascript", "-e", 'tell app "System Events" to sleep'])
        else:
            _sp.run(["systemctl", "suspend"])
    elif action_key == "on_finish_hibernate":
        _sp.run(["shutdown", "/h"])
    elif action_key == "on_finish_lock":
        if _sys.platform == "win32":
            _sp.run(["rundll32.exe", "user32.dll,LockWorkStation"])
        elif _sys.platform == "darwin":
            _sp.run(["osascript", "-e", 'tell app "System Events" to keystroke "q" using {control down, command down}'])
        else:
            _sp.run(["loginctl", "lock-session"])
    elif action_key == "on_finish_logoff":
        _sp.run(["shutdown", "/l"])
    elif action_key == "on_finish_quit_app":
        main_window.close()
