# ui/main_window/setup_ui.py
import os

from ui.qt_compat import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QSlider, QSpinBox, QDoubleSpinBox, QLineEdit, QGroupBox, QCheckBox,
    QScrollArea, QComboBox,
    Qt, get_align_center, get_horizontal, get_vertical,
)
from ui.core.preset_manager import PresetManager
from ui.widgets import VideoLabel, VideoControls


def init_ui(main_window):
    preview_mode = False
    if main_window.config_manager:
        try:
            preview_mode = main_window.config_manager.getboolean('UI', 'preview_mode', False)
        except Exception:
            pass

    main_window.setWindowTitle(main_window.tr("window_title"))
    main_window.setGeometry(100, 100, 1100, 820)

    from .menu_bar import _setup_menu_bar
    _setup_menu_bar(main_window)

    central_widget = QWidget()
    main_window.setCentralWidget(central_widget)
    main_layout = QHBoxLayout(central_widget)

    left_column = QWidget()
    left_layout = QVBoxLayout(left_column)

    _setup_video_area(main_window, left_layout, preview_mode)
    _setup_controls_and_volume(main_window, left_layout)
    _setup_output_filters(main_window, left_layout)
    _setup_output_folder(main_window, left_layout)

    left_layout.addStretch()

    right_scroll_content = QWidget()
    right_layout = QVBoxLayout(right_scroll_content)

    _setup_preset_section(main_window, right_layout)
    _setup_processing(main_window, right_layout)
    _setup_video_parameters(main_window, right_layout)
    _setup_audio_parameters(main_window, right_layout)
    _setup_decompilation(main_window, right_layout)

    right_layout.addStretch()

    scroller = QScrollArea()
    scroller.setWidgetResizable(True)
    scroller.setWidget(right_scroll_content)
    scroller.setFixedWidth(350)
    scroller.setMinimumWidth(350)

    main_layout.addWidget(left_column, stretch=1)
    main_layout.addWidget(scroller)

    from .utils import _setup_shortcuts, disable_mouse_wheel_recursive
    _setup_shortcuts(main_window)
    disable_mouse_wheel_recursive(main_window, central_widget)

    from .presets import _load_default_preset, _apply_preset, _rebuild_preset_combo
    default_preset = _load_default_preset(main_window)
    main_window.preset_combo.blockSignals(True)
    idx = main_window.preset_combo.findData(default_preset)
    if idx >= 0:
        main_window.preset_combo.setCurrentIndex(idx)
    main_window.preset_combo.blockSignals(False)
    _apply_preset(main_window, default_preset)

    if main_window.config_manager and main_window.config_manager.getboolean('SETTINGS', 'remember_file_paths', False):
        try:
            saved_output = main_window.config_manager.get('PATHS', 'output_folder', '')
            if saved_output and os.path.exists(saved_output):
                main_window.output_folder = saved_output
                main_window.output_path_edit.setText(saved_output)
        except Exception:
            pass

    main_window.adjustSize()
    main_window.setMinimumSize(main_window.size())


def _setup_video_area(main_window, layout, preview_mode):
    main_window.video_label = VideoLabel()
    main_window.video_label.setAlignment(get_align_center())
    main_window.video_label.setFixedSize(640, 427)
    main_window.video_label.setStyleSheet("border: 2px solid gray; background: black;")
    layout.addWidget(main_window.video_label)

    view_controls_layout = QHBoxLayout()
    main_window.show_preview_check = QCheckBox(main_window.tr("show_preview"))
    main_window.show_preview_check.setChecked(preview_mode)
    main_window.show_preview_check.setToolTip(main_window.tr("show_preview_tooltip"))
    main_window.show_preview_check.stateChanged.connect(main_window._on_view_mode_changed)
    main_window.show_preview_check.stateChanged.connect(main_window._save_preview_mode)
    view_controls_layout.addWidget(main_window.show_preview_check)
    view_controls_layout.addSpacing(380)

    main_window.video_mode_label = QLabel()
    main_window.video_mode_label.setStyleSheet("font-weight: bold; color: #AAAAAA;")
    if preview_mode:
        main_window.video_mode_label.setText(main_window.tr("view_preview"))
        main_window.video_mode_label.setStyleSheet("font-weight: bold; color: #00AA00;")
        main_window.video_label.setStyleSheet("border: 2px solid #00AA00; background: black;")
    else:
        main_window.video_mode_label.setText(main_window.tr("view_input"))
        main_window.video_mode_label.setStyleSheet("font-weight: bold; color: #AAAAAA;")
        main_window.video_label.setStyleSheet("border: 2px solid gray; background: black;")

    view_controls_layout.addWidget(main_window.video_mode_label)
    view_controls_layout.addStretch()
    layout.addLayout(view_controls_layout)


def _setup_controls_and_volume(main_window, layout):
    row = QHBoxLayout()
    row.setSpacing(6)
    row.setContentsMargins(0, 0, 0, 0)

    left = QWidget()
    left_vbox = QVBoxLayout(left)
    left_vbox.setContentsMargins(0, 0, 0, 0)
    left_vbox.setSpacing(2)
    _setup_controls(main_window, left_vbox)
    _setup_timeline(main_window, left_vbox)
    row.addWidget(left, stretch=1)

    vol_widget = QWidget()
    vol_widget.setFixedWidth(28)
    vol_vbox = QVBoxLayout(vol_widget)
    vol_vbox.setContentsMargins(0, 0, 0, 0)
    vol_vbox.setSpacing(2)

    main_window.btn_mute = QPushButton("🔊")
    main_window.btn_mute.setFixedSize(24, 24)
    main_window.btn_mute.setFlat(True)
    main_window.btn_mute.setToolTip(main_window.tr("mute_toggle", default="Mute / Unmute"))
    main_window.btn_mute.clicked.connect(main_window._on_mute_toggled)
    vol_vbox.addWidget(main_window.btn_mute, alignment=get_align_center())

    main_window.volume_slider = QSlider(get_vertical())
    main_window.volume_slider.setRange(0, 100)
    main_window.volume_slider.setValue(100)
    main_window.volume_slider.setToolTip(main_window.tr("volume_slider_tooltip", default="Preview volume"))
    main_window.volume_slider.valueChanged.connect(main_window._on_volume_changed)
    vol_vbox.addWidget(main_window.volume_slider, stretch=1)

    row.addWidget(vol_widget)
    layout.addLayout(row)


def _setup_controls(main_window, layout):
    main_window._controls_widget = VideoControls(main_window)
    controls_widget = main_window._controls_widget
    main_window.btn_play = controls_widget.btn_play
    main_window.btn_prev_frame = controls_widget.btn_prev_frame
    main_window.btn_next_frame = controls_widget.btn_next_frame
    main_window.btn_prev_keyframe = controls_widget.btn_prev_keyframe
    main_window.btn_next_keyframe = controls_widget.btn_next_keyframe
    main_window.btn_mark_start = controls_widget.btn_mark_start
    main_window.btn_mark_end = controls_widget.btn_mark_end
    main_window.btn_goto_start = controls_widget.btn_goto_start
    main_window.btn_goto_end = controls_widget.btn_goto_end
    main_window.btn_first_frame = controls_widget.btn_first_frame
    main_window.btn_last_frame = controls_widget.btn_last_frame
    main_window.btn_play.setToolTip(main_window.tr("play"))
    main_window.btn_prev_frame.setToolTip(main_window.tr("prev_frame"))
    main_window.btn_next_frame.setToolTip(main_window.tr("next_frame"))
    main_window.btn_prev_keyframe.setToolTip(main_window.tr("prev_keyframe"))
    main_window.btn_next_keyframe.setToolTip(main_window.tr("next_keyframe"))
    main_window.btn_mark_start.setToolTip(main_window.tr("mark_start"))
    main_window.btn_mark_end.setToolTip(main_window.tr("mark_end"))
    main_window.btn_goto_start.setToolTip(main_window.tr("goto_start"))
    main_window.btn_goto_end.setToolTip(main_window.tr("goto_end"))
    main_window.btn_first_frame.setToolTip(main_window.tr("first_frame"))
    main_window.btn_last_frame.setToolTip(main_window.tr("last_frame"))
    main_window.btn_play.clicked.connect(main_window.toggle_play)
    main_window.btn_prev_frame.clicked.connect(main_window.prev_frame)
    main_window.btn_next_frame.clicked.connect(main_window.next_frame)
    main_window.btn_prev_keyframe.clicked.connect(main_window.prev_keyframe)
    main_window.btn_next_keyframe.clicked.connect(main_window.next_keyframe)
    main_window.btn_mark_start.clicked.connect(main_window._set_start_frame)
    main_window.btn_mark_end.clicked.connect(main_window._set_end_frame)
    main_window.btn_goto_start.clicked.connect(main_window._goto_start_marker)
    main_window.btn_goto_end.clicked.connect(main_window._goto_end_marker)
    main_window.btn_first_frame.clicked.connect(main_window.first_frame)
    main_window.btn_last_frame.clicked.connect(main_window.last_frame)
    layout.addWidget(controls_widget)


def _setup_timeline(main_window, layout):
    timeline_layout = QHBoxLayout()
    main_window.timeline = QSlider(get_horizontal())
    main_window.timeline.setEnabled(False)
    main_window.timeline.valueChanged.connect(main_window._seek_frame)
    timeline_layout.addWidget(main_window.timeline)

    main_window.lbl_time = QLabel("00:00:00.00")
    main_window.lbl_time.setStyleSheet("font-family: monospace;")
    timeline_layout.addWidget(main_window.lbl_time)
    main_window._lbl_frame = QLabel(main_window.tr("frame_label"))
    timeline_layout.addWidget(main_window._lbl_frame)
    main_window.frame_spin = QSpinBox()
    main_window.frame_spin.setEnabled(False)
    main_window.frame_spin.valueChanged.connect(main_window._seek_frame)
    timeline_layout.addWidget(main_window.frame_spin)

    layout.addLayout(timeline_layout)

    main_window.lbl_range = QLabel(main_window.tr("range_not_set"))
    layout.addWidget(main_window.lbl_range)

    main_window.lbl_info = QLabel(main_window.tr("no_video_loaded"))
    layout.addWidget(main_window.lbl_info)


def _setup_output_filters(main_window, layout):
    main_window._grp_output_filters = QGroupBox(main_window.tr("output_filters"))
    out_layout = QVBoxLayout(main_window._grp_output_filters)

    filters_row = QHBoxLayout()
    main_window._lbl_crop = QLabel(main_window.tr("crop_label"))
    filters_row.addWidget(main_window._lbl_crop)
    main_window.crop_edit = QLineEdit()
    main_window.crop_edit.setPlaceholderText(main_window.tr("crop_placeholder"))
    main_window.crop_edit.setMaximumWidth(150)
    main_window.crop_edit.setEnabled(False)
    filters_row.addWidget(main_window.crop_edit)

    main_window.letterbox_check = QCheckBox(main_window.tr("letterbox"))
    main_window.letterbox_check.setChecked(True)
    filters_row.addWidget(main_window.letterbox_check)

    main_window._lbl_target = QLabel(main_window.tr("target_label"))
    filters_row.addWidget(main_window._lbl_target)
    lbl_target_val = QLabel("240 x 160")
    lbl_target_val.setStyleSheet("font-weight: bold; color: #00AA00;")
    filters_row.addWidget(lbl_target_val)

    filters_row.addStretch()

    main_window.btn_apply_filters = QPushButton(main_window.tr("apply_filters"))
    main_window.btn_apply_filters.setEnabled(False)
    main_window.btn_apply_filters.setFixedWidth(100)
    main_window.btn_apply_filters.clicked.connect(main_window.update_preview)
    filters_row.addWidget(main_window.btn_apply_filters)

    out_layout.addLayout(filters_row)
    layout.addWidget(main_window._grp_output_filters)


def _setup_output_folder(main_window, layout):
    import sys as _sys
    import platform as _platform
    _os = _sys.platform

    main_window._grp_output_folder = QGroupBox(main_window.tr("output_folder"))
    group_vbox = QVBoxLayout(main_window._grp_output_folder)

    row0 = QHBoxLayout()
    main_window._lbl_rom_name = QLabel(main_window.tr("rom_name_label"))
    row0.addWidget(main_window._lbl_rom_name)
    main_window.rom_name_edit = QLineEdit()
    main_window.rom_name_edit.setText("GBA_Video")
    main_window.rom_name_edit.setPlaceholderText(main_window.tr("rom_name_placeholder"))
    main_window.rom_name_edit.setFixedWidth(200)
    row0.addWidget(main_window.rom_name_edit)
    row0.addStretch()
    group_vbox.addLayout(row0)

    row1 = QHBoxLayout()
    main_window._lbl_save_to = QLabel(main_window.tr("save_to"))
    row1.addWidget(main_window._lbl_save_to)
    main_window.output_path_edit = QLineEdit()
    main_window.output_path_edit.setPlaceholderText(main_window.tr("output_folder_placeholder"))
    main_window.output_path_edit.setReadOnly(True)
    row1.addWidget(main_window.output_path_edit, stretch=1)

    main_window.btn_browse_output = QPushButton(main_window.tr("browse_button"))
    main_window.btn_browse_output.setEnabled(False)
    main_window.btn_browse_output.setFixedWidth(80)
    main_window.btn_browse_output.clicked.connect(main_window._browse_output_folder)
    row1.addWidget(main_window.btn_browse_output)

    main_window.btn_export = QPushButton(main_window.tr("build_rom"))
    main_window.btn_export.setEnabled(False)
    main_window.btn_export.setFixedWidth(120)
    main_window.btn_export.clicked.connect(main_window.export_video)
    row1.addWidget(main_window.btn_export)

    group_vbox.addLayout(row1)

    row2 = QHBoxLayout()
    main_window.lbl_export_status = QLabel(main_window.tr("ready_to_export"))
    main_window.lbl_export_status.setStyleSheet("color: #00AA00; font-weight: bold;")
    row2.addWidget(main_window.lbl_export_status)

    main_window.lbl_export_timer = QLabel("")
    main_window.lbl_export_timer.setStyleSheet("font-family: monospace; color: #000000;")
    main_window.lbl_export_timer.setVisible(False)
    row2.addWidget(main_window.lbl_export_timer)

    row2.addStretch()

    _lbl_on_finish = QLabel(main_window.tr("on_finish_label"))
    row2.addWidget(_lbl_on_finish)
    main_window._lbl_on_finish = _lbl_on_finish

    main_window.combo_post_action = QComboBox()
    main_window.combo_post_action.setFixedWidth(150)
    main_window.combo_post_action.addItem("---", "on_finish_nothing")
    main_window.combo_post_action.addItem(main_window.tr("on_finish_open_folder"), "on_finish_open_folder")
    main_window.combo_post_action.addItem(main_window.tr("on_finish_open_rom"), "on_finish_open_rom")
    main_window.combo_post_action.addItem(main_window.tr("on_finish_quit_app"), "on_finish_quit_app")
    if _os == "win32":
        main_window.combo_post_action.addItem(main_window.tr("on_finish_shutdown"), "on_finish_shutdown")
        main_window.combo_post_action.addItem(main_window.tr("on_finish_sleep"), "on_finish_sleep")
        main_window.combo_post_action.addItem(main_window.tr("on_finish_hibernate"), "on_finish_hibernate")
        main_window.combo_post_action.addItem(main_window.tr("on_finish_lock"), "on_finish_lock")
        main_window.combo_post_action.addItem(main_window.tr("on_finish_logoff"), "on_finish_logoff")
    elif _os == "linux":
        main_window.combo_post_action.addItem(main_window.tr("on_finish_shutdown"), "on_finish_shutdown")
        main_window.combo_post_action.addItem(main_window.tr("on_finish_sleep"), "on_finish_sleep")
        main_window.combo_post_action.addItem(main_window.tr("on_finish_lock"), "on_finish_lock")
    elif _os == "darwin":
        main_window.combo_post_action.addItem(main_window.tr("on_finish_shutdown"), "on_finish_shutdown")
        main_window.combo_post_action.addItem(main_window.tr("on_finish_sleep"), "on_finish_sleep")
        main_window.combo_post_action.addItem(main_window.tr("on_finish_lock"), "on_finish_lock")
    row2.addWidget(main_window.combo_post_action)

    group_vbox.addLayout(row2)

    layout.addWidget(main_window._grp_output_folder)


def _setup_preset_section(main_window, layout):
    main_window._grp_preset = QGroupBox(main_window.tr("preset_section", default="Preset"))
    preset_layout = QGridLayout(main_window._grp_preset)

    main_window._lbl_preset = QLabel(main_window.tr("preset_label"))
    preset_layout.addWidget(main_window._lbl_preset, 0, 0)

    combo_row = QHBoxLayout()
    combo_row.addStretch()

    main_window.preset_combo = QComboBox()
    main_window.preset_combo.setFixedWidth(120)
    from .presets import _rebuild_preset_combo
    _rebuild_preset_combo(main_window)
    main_window.preset_combo.currentTextChanged.connect(main_window._on_preset_changed)
    combo_row.addWidget(main_window.preset_combo)

    main_window.btn_reload_preset = QPushButton(main_window.tr("reload_preset"))
    main_window.btn_reload_preset.setFixedWidth(100)
    main_window.btn_reload_preset.setToolTip(main_window.tr("reload_preset_tooltip"))
    main_window.btn_reload_preset.clicked.connect(main_window._reload_current_preset)
    combo_row.addWidget(main_window.btn_reload_preset)

    preset_layout.addLayout(combo_row, 0, 1)
    layout.addWidget(main_window._grp_preset)


def _setup_processing(main_window, layout):
    main_window._grp_processing = QGroupBox(main_window.tr("processing"))
    proc_layout = QGridLayout(main_window._grp_processing)

    main_window._lbl_max_workers = QLabel(main_window.tr("max_workers"))
    proc_layout.addWidget(main_window._lbl_max_workers, 0, 0)

    max_workers_layout = QHBoxLayout()
    max_workers_layout.addStretch()

    main_window.workers_spin = QSpinBox()
    max_workers = os.cpu_count() or 4
    if main_window.config_manager:
        try:
            max_workers = main_window.config_manager.getint('SETTINGS', 'max_workers', max_workers)
            max_workers = min(max_workers, os.cpu_count() or 4)
        except Exception:
            pass
    main_window.workers_spin.setRange(1, os.cpu_count() or 4)
    main_window.workers_spin.setValue(max_workers)
    main_window.workers_spin.setToolTip(main_window.tr("max_workers_tooltip"))
    main_window.workers_spin.valueChanged.connect(main_window._save_max_workers)
    main_window.workers_spin.setFixedWidth(152)
    max_workers_layout.addWidget(main_window.workers_spin)

    proc_layout.addLayout(max_workers_layout, 0, 1)

    layout.addWidget(main_window._grp_processing)


def _setup_video_parameters(main_window, layout):
    main_window._grp_video = QGroupBox(main_window.tr("video_parameters"))
    video_layout = QGridLayout(main_window._grp_video)

    main_window._lbl_fps = QLabel(main_window.tr("target_fps"))
    video_layout.addWidget(main_window._lbl_fps, 0, 0)
    main_window.fps_combo = QComboBox()
    fps_display = [
        main_window.tr("fps_5_9727"), main_window.tr("fps_6_6364"), main_window.tr("fps_7_4659"),
        main_window.tr("fps_8_5325"), main_window.tr("fps_9_9546"), main_window.tr("fps_11_9455"),
        main_window.tr("fps_14_9319"),
    ]
    for i, display in enumerate(fps_display):
        main_window.fps_combo.addItem(display, PresetManager.FPS_VALUES[i])
    main_window.fps_combo.setCurrentIndex(4)
    video_layout.addWidget(main_window.fps_combo, 0, 1)

    main_window._lbl_iframe_interval = QLabel(main_window.tr("iframe_interval"))
    video_layout.addWidget(main_window._lbl_iframe_interval, 1, 0)
    main_window.iframe_interval = QSpinBox()
    main_window.iframe_interval.setRange(1, 999)
    main_window.iframe_interval.setValue(60)
    main_window.iframe_interval.setToolTip(main_window.tr("iframe_interval_tooltip"))
    video_layout.addWidget(main_window.iframe_interval, 1, 1)

    main_window._lbl_diff_threshold = QLabel(main_window.tr("diff_threshold"))
    video_layout.addWidget(main_window._lbl_diff_threshold, 2, 0)
    main_window.diff_threshold = QDoubleSpinBox()
    main_window.diff_threshold.setRange(0.0, 50.0)
    main_window.diff_threshold.setSingleStep(0.5)
    main_window.diff_threshold.setValue(2.5)
    main_window.diff_threshold.setToolTip(main_window.tr("diff_threshold_tooltip"))
    video_layout.addWidget(main_window.diff_threshold, 2, 1)

    main_window._lbl_variance_threshold = QLabel(main_window.tr("variance_threshold"))
    video_layout.addWidget(main_window._lbl_variance_threshold, 3, 0)
    main_window.variance_threshold = QDoubleSpinBox()
    main_window.variance_threshold.setRange(0.0, 100.0)
    main_window.variance_threshold.setSingleStep(1.0)
    main_window.variance_threshold.setValue(10.0)
    main_window.variance_threshold.setToolTip(main_window.tr("variance_threshold_tooltip"))
    video_layout.addWidget(main_window.variance_threshold, 3, 1)

    main_window._lbl_color_fallback = QLabel(main_window.tr("color_fallback"))
    video_layout.addWidget(main_window._lbl_color_fallback, 4, 0)
    main_window.color_fallback_threshold = QDoubleSpinBox()
    main_window.color_fallback_threshold.setRange(0.0, 100.0)
    main_window.color_fallback_threshold.setSingleStep(1.0)
    main_window.color_fallback_threshold.setValue(10.0)
    main_window.color_fallback_threshold.setToolTip(main_window.tr("color_fallback_tooltip"))
    video_layout.addWidget(main_window.color_fallback_threshold, 4, 1)

    main_window._lbl_force_i = QLabel(main_window.tr("force_i_threshold"))
    video_layout.addWidget(main_window._lbl_force_i, 5, 0)
    main_window.force_i_threshold = QDoubleSpinBox()
    main_window.force_i_threshold.setRange(0.0, 1.0)
    main_window.force_i_threshold.setSingleStep(0.05)
    main_window.force_i_threshold.setValue(0.7)
    main_window.force_i_threshold.setToolTip(main_window.tr("force_i_threshold_tooltip"))
    video_layout.addWidget(main_window.force_i_threshold, 5, 1)

    main_window._lbl_codebook_size = QLabel(main_window.tr("codebook_size"))
    video_layout.addWidget(main_window._lbl_codebook_size, 6, 0)
    main_window.codebook_size = QSpinBox()
    main_window.codebook_size.setRange(2, 256)
    main_window.codebook_size.setValue(256)
    main_window.codebook_size.setToolTip(main_window.tr("codebook_size_tooltip"))
    video_layout.addWidget(main_window.codebook_size, 6, 1)

    main_window._lbl_kmeans = QLabel(main_window.tr("kmeans_iterations"))
    video_layout.addWidget(main_window._lbl_kmeans, 7, 0)
    main_window.kmeans_spin = QSpinBox()
    main_window.kmeans_spin.setRange(1, 2000)
    main_window.kmeans_spin.setValue(200)
    main_window.kmeans_spin.setToolTip(main_window.tr("kmeans_iterations_tooltip"))
    video_layout.addWidget(main_window.kmeans_spin, 7, 1)

    main_window._lbl_iframe_weight = QLabel(main_window.tr("iframe_weight"))
    video_layout.addWidget(main_window._lbl_iframe_weight, 8, 0)
    main_window.iframe_weight = QSpinBox()
    main_window.iframe_weight.setRange(1, 10)
    main_window.iframe_weight.setValue(3)
    main_window.iframe_weight.setToolTip(main_window.tr("iframe_weight_tooltip"))
    video_layout.addWidget(main_window.iframe_weight, 8, 1)

    main_window._lbl_motion_thresh = QLabel(main_window.tr("motion_threshold"))
    video_layout.addWidget(main_window._lbl_motion_thresh, 9, 0)
    main_window.motion_thresh = QSpinBox()
    main_window.motion_thresh.setRange(0, 16)
    main_window.motion_thresh.setValue(6)
    main_window.motion_thresh.setToolTip(main_window.tr("motion_threshold_tooltip"))
    video_layout.addWidget(main_window.motion_thresh, 9, 1)

    main_window.dither_check = QCheckBox(main_window.tr("floyd_steinberg_dithering"))
    main_window.dither_check.setChecked(True)
    main_window.dither_check.setToolTip(main_window.tr("floyd_steinberg_dithering_tooltip"))
    video_layout.addWidget(main_window.dither_check, 10, 0, 1, 2)

    main_window.motion_check = QCheckBox(main_window.tr("motion_compensation"))
    main_window.motion_check.setChecked(True)
    main_window.motion_check.setToolTip(main_window.tr("motion_compensation_tooltip"))
    video_layout.addWidget(main_window.motion_check, 11, 0, 1, 2)

    layout.addWidget(main_window._grp_video)


def _setup_audio_parameters(main_window, layout):
    main_window._grp_audio = QGroupBox(main_window.tr("audio_parameters"))
    audio_layout = QGridLayout(main_window._grp_audio)

    main_window.no_audio_check = QCheckBox(main_window.tr("no_audio"))
    audio_layout.addWidget(main_window.no_audio_check, 0, 0, 1, 2)

    main_window._lbl_audio_format = QLabel(main_window.tr("audio_format"))
    audio_layout.addWidget(main_window._lbl_audio_format, 1, 0)
    main_window.audio_format = QComboBox()
    main_window.audio_format.addItems(["PCM", "ADPCM"])
    main_window.audio_format.setCurrentText("PCM")
    main_window.audio_format.currentTextChanged.connect(main_window._on_audio_format_changed)
    audio_layout.addWidget(main_window.audio_format, 1, 1)

    main_window._lbl_sample_rate = QLabel(main_window.tr("audio_sample_rate"))
    audio_layout.addWidget(main_window._lbl_sample_rate, 2, 0)
    main_window.sample_rate = QSpinBox()
    main_window.sample_rate.setRange(6500, 44100)
    main_window.sample_rate.setValue(18157)
    main_window.sample_rate.setToolTip(main_window.tr("audio_sample_rate_tooltip_pcm"))
    audio_layout.addWidget(main_window.sample_rate, 2, 1)

    main_window._lbl_volume = QLabel(main_window.tr("audio_volume"))
    audio_layout.addWidget(main_window._lbl_volume, 3, 0)
    main_window.volume = QDoubleSpinBox()
    main_window.volume.setRange(0, 200)
    main_window.volume.setSuffix(" %")
    main_window.volume.setValue(100.0)
    audio_layout.addWidget(main_window.volume, 3, 1)

    main_window.adpcm_note_label = QLabel(main_window.tr("adpcm_note"))
    main_window.adpcm_note_label.setStyleSheet("color: gray; font-size: 9px;")
    main_window.adpcm_note_label.setVisible(False)
    audio_layout.addWidget(main_window.adpcm_note_label, 4, 0, 1, 2)

    main_window.no_audio_check.toggled.connect(main_window._on_no_audio_toggled)

    layout.addWidget(main_window._grp_audio)


def _setup_decompilation(main_window, layout):
    main_window._grp_decomp = QGroupBox(main_window.tr("decompilation_settings"))
    decomp_layout = QVBoxLayout(main_window._grp_decomp)

    main_window.skip_video_check = QCheckBox(main_window.tr("enable_skip_button"))
    main_window.skip_video_check.setToolTip(main_window.tr("enable_skip_button_tooltip"))
    main_window.skip_video_check.toggled.connect(main_window._on_skip_video_toggled)
    decomp_layout.addWidget(main_window.skip_video_check)

    main_window._lbl_skip_buttons = QLabel(main_window.tr("skip_buttons_label"))
    main_window._lbl_skip_buttons.setToolTip(main_window.tr("skip_buttons_tooltip"))
    decomp_layout.addWidget(main_window._lbl_skip_buttons)

    buttons_row = QHBoxLayout()
    main_window.button_checkboxes = []
    for button in ["A", "B", "Start", "Select", "R", "L"]:
        cb = QCheckBox(button)
        cb.setEnabled(False)
        cb.toggled.connect(lambda checked, cb=cb: main_window._on_button_toggled(checked, cb))
        main_window.button_checkboxes.append(cb)
        buttons_row.addWidget(cb)
    buttons_row.addStretch()
    decomp_layout.addLayout(buttons_row)

    layout.addWidget(main_window._grp_decomp)
