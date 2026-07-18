# ui/main_window/config.py
from ui.qt_compat import Qt
from ui.core.preset_manager import PresetManager


def change_language(main_window, lang_key):
    if main_window.config_manager:
        main_window.config_manager.set('SETTINGS', 'language', lang_key)
    main_window.translator.load_language(lang_key)
    main_window._tr = main_window.translator.tr
    for lk, action in main_window.language_actions.items():
        action.setChecked(lk == lang_key)
    retranslate_ui(main_window)


def retranslate_ui(main_window):
    tr = main_window.translator.tr

    main_window.setWindowTitle(tr("window_title"))

    from .menu_bar import retranslate_menus
    retranslate_menus(main_window)

    main_window.show_preview_check.setText(tr("show_preview"))
    main_window.show_preview_check.setToolTip(tr("show_preview_tooltip"))
    if main_window.show_preview_check.isChecked():
        main_window.video_mode_label.setText(tr("view_preview"))
    else:
        main_window.video_mode_label.setText(tr("view_input"))

    main_window.btn_play.setToolTip(tr("play"))
    main_window.btn_prev_frame.setToolTip(tr("prev_frame"))
    main_window.btn_next_frame.setToolTip(tr("next_frame"))
    main_window.btn_prev_keyframe.setToolTip(tr("prev_keyframe"))
    main_window.btn_next_keyframe.setToolTip(tr("next_keyframe"))
    main_window.btn_mark_start.setToolTip(tr("mark_start"))
    main_window.btn_mark_end.setToolTip(tr("mark_end"))
    main_window.btn_goto_start.setToolTip(tr("goto_start"))
    main_window.btn_goto_end.setToolTip(tr("goto_end"))
    main_window.btn_first_frame.setToolTip(tr("first_frame"))
    main_window.btn_last_frame.setToolTip(tr("last_frame"))
    main_window.btn_mute.setToolTip(tr("mute_toggle"))
    main_window.volume_slider.setToolTip(tr("volume_slider_tooltip"))

    main_window._lbl_frame.setText(tr("frame_label"))
    main_window.lbl_range.setText(tr("range_not_set"))
    if not main_window.video_controller.cap:
        main_window.lbl_info.setText(tr("no_video_loaded"))
    else:
        from pathlib import Path as _Path
        from .utils import _format_time
        duration_str = _format_time(main_window, main_window.video_controller.total_frames - 1)
        main_window.lbl_info.setText(
            tr("video_info",
               name=_Path(main_window.video_path).name,
               width=main_window.video_controller.width,
               height=main_window.video_controller.height,
               frames=main_window.video_controller.total_frames,
               fps=main_window.video_controller.fps,
               duration=duration_str)
        )

    main_window._grp_output_filters.setTitle(tr("output_filters"))
    main_window._lbl_crop.setText(tr("crop_label"))
    main_window.crop_edit.setPlaceholderText(tr("crop_placeholder"))
    main_window.letterbox_check.setText(tr("letterbox"))
    main_window._lbl_target.setText(tr("target_label"))
    main_window.btn_apply_filters.setText(tr("apply_filters"))

    main_window._grp_output_folder.setTitle(tr("output_folder"))
    main_window._lbl_rom_name.setText(tr("rom_name_label"))
    main_window.rom_name_edit.setPlaceholderText(tr("rom_name_placeholder"))
    main_window._lbl_save_to.setText(tr("save_to"))
    main_window.output_path_edit.setPlaceholderText(tr("output_folder_placeholder"))
    main_window.btn_browse_output.setText(tr("browse_button"))
    main_window.btn_export.setText(tr("build_rom"))
    main_window.lbl_export_status.setText(tr("ready_to_export"))
    if hasattr(main_window, '_lbl_on_finish'):
        main_window._lbl_on_finish.setText(tr("on_finish_label"))
    for i in range(main_window.combo_post_action.count()):
        key = main_window.combo_post_action.itemData(i)
        if key and key != "on_finish_nothing":
            main_window.combo_post_action.setItemText(i, tr(key))

    main_window._grp_preset.setTitle(tr("preset_section", default="Preset"))
    main_window._lbl_preset.setText(tr("preset_label"))
    main_window.btn_reload_preset.setText(tr("reload_preset"))
    main_window.btn_reload_preset.setToolTip(tr("reload_preset_tooltip"))

    from .presets import _rebuild_preset_combo, _update_presets_submenu
    current_key = main_window.preset_combo.currentData()
    _rebuild_preset_combo(main_window, select_key=current_key)
    _update_presets_submenu(main_window)

    main_window._grp_processing.setTitle(tr("processing"))
    main_window._lbl_max_workers.setText(tr("max_workers"))
    main_window.workers_spin.setToolTip(tr("max_workers_tooltip"))

    main_window._grp_video.setTitle(tr("video_parameters"))
    main_window._lbl_fps.setText(tr("target_fps"))
    current_fps_data = main_window.fps_combo.currentData()
    main_window.fps_combo.blockSignals(True)
    main_window.fps_combo.clear()
    fps_keys = ["fps_5_9727", "fps_6_6364", "fps_7_4659", "fps_8_5325",
                "fps_9_9546", "fps_11_9455", "fps_14_9319"]
    for i, key in enumerate(fps_keys):
        main_window.fps_combo.addItem(tr(key), PresetManager.FPS_VALUES[i])
    idx = PresetManager.FPS_VALUES.index(current_fps_data) if current_fps_data in PresetManager.FPS_VALUES else 4
    main_window.fps_combo.setCurrentIndex(idx)
    main_window.fps_combo.blockSignals(False)
    main_window._lbl_iframe_interval.setText(tr("iframe_interval"))
    main_window.iframe_interval.setToolTip(tr("iframe_interval_tooltip"))
    main_window._lbl_diff_threshold.setText(tr("diff_threshold"))
    main_window.diff_threshold.setToolTip(tr("diff_threshold_tooltip"))
    main_window._lbl_variance_threshold.setText(tr("variance_threshold"))
    main_window.variance_threshold.setToolTip(tr("variance_threshold_tooltip"))
    main_window._lbl_color_fallback.setText(tr("color_fallback"))
    main_window.color_fallback_threshold.setToolTip(tr("color_fallback_tooltip"))
    main_window._lbl_force_i.setText(tr("force_i_threshold"))
    main_window.force_i_threshold.setToolTip(tr("force_i_threshold_tooltip"))
    main_window._lbl_codebook_size.setText(tr("codebook_size"))
    main_window.codebook_size.setToolTip(tr("codebook_size_tooltip"))
    main_window._lbl_kmeans.setText(tr("kmeans_iterations"))
    main_window.kmeans_spin.setToolTip(tr("kmeans_iterations_tooltip"))
    main_window._lbl_iframe_weight.setText(tr("iframe_weight"))
    main_window.iframe_weight.setToolTip(tr("iframe_weight_tooltip"))
    main_window._lbl_motion_thresh.setText(tr("motion_threshold"))
    main_window.motion_thresh.setToolTip(tr("motion_threshold_tooltip"))
    main_window.dither_check.setText(tr("floyd_steinberg_dithering"))
    main_window.dither_check.setToolTip(tr("floyd_steinberg_dithering_tooltip"))
    main_window.motion_check.setText(tr("motion_compensation"))
    main_window.motion_check.setToolTip(tr("motion_compensation_tooltip"))

    main_window._grp_audio.setTitle(tr("audio_parameters"))
    main_window._lbl_audio_format.setText(tr("audio_format"))
    main_window._lbl_sample_rate.setText(tr("audio_sample_rate"))
    fmt = main_window.audio_format.currentText()
    if fmt == "ADPCM":
        main_window.sample_rate.setToolTip(tr("audio_sample_rate_tooltip_adpcm"))
    else:
        main_window.sample_rate.setToolTip(tr("audio_sample_rate_tooltip_pcm"))
    main_window._lbl_volume.setText(tr("audio_volume"))
    main_window.no_audio_check.setText(tr("no_audio"))
    main_window.adpcm_note_label.setText(tr("adpcm_note"))

    main_window._grp_decomp.setTitle(tr("decompilation_settings"))
    main_window.skip_video_check.setText(tr("enable_skip_button"))
    main_window.skip_video_check.setToolTip(tr("enable_skip_button_tooltip"))
    main_window._lbl_skip_buttons.setText(tr("skip_buttons_label"))
    main_window._lbl_skip_buttons.setToolTip(tr("skip_buttons_tooltip"))


def _on_remember_paths_toggled(main_window, checked):
    if main_window.config_manager:
        main_window.config_manager.set('SETTINGS', 'remember_file_paths', str(checked))


def _save_preview_mode(main_window, state):
    if main_window.config_manager:
        try:
            main_window.config_manager.set('UI', 'preview_mode', str(state == Qt.Checked))
        except Exception:
            pass


def _save_max_workers(main_window, value):
    if main_window.config_manager:
        try:
            main_window.config_manager.set('SETTINGS', 'max_workers', str(value))
        except Exception:
            pass


def _save_output_folder(main_window, folder):
    if main_window.config_manager:
        try:
            main_window.config_manager.set('PATHS', 'output_folder', folder)
        except Exception:
            pass


def _save_last_video(main_window, path):
    if main_window.config_manager:
        try:
            main_window.config_manager.set('PATHS', 'last_video_path', path)
        except Exception:
            pass
