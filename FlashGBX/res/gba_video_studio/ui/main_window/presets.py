# ui/main_window/presets.py
import os

from ui.qt_compat import QAction, QMessageBox, QInputDialog
from ui.core.preset_manager import PresetManager


def _display_name(main_window, preset_key):
    if main_window.preset_manager.is_builtin(preset_key):
        return main_window.tr(preset_key, default=preset_key)
    return preset_key


def _update_presets_submenu(main_window):
    main_window.presets_submenu.clear()
    for preset_key in main_window.preset_manager.get_preset_names():
        label = _display_name(main_window, preset_key)
        action = QAction(label, main_window)
        action.triggered.connect(
            lambda checked=False, key=preset_key: _apply_preset_and_sync_combo(main_window, key))
        main_window.presets_submenu.addAction(action)


def _apply_preset_and_sync_combo(main_window, preset_key):
    _rebuild_preset_combo(main_window, select_key=preset_key)
    _apply_preset(main_window, preset_key)


def _rebuild_preset_combo(main_window, select_key=None):
    combo = main_window.preset_combo
    combo.blockSignals(True)
    combo.clear()
    for key in main_window.preset_manager.get_preset_names():
        combo.addItem(_display_name(main_window, key), key)
    if select_key is not None:
        idx = combo.findData(select_key)
        if idx >= 0:
            combo.setCurrentIndex(idx)
    combo.blockSignals(False)


def _apply_preset(main_window, preset_key):
    preset = main_window.preset_manager.get_preset(preset_key)
    if not preset:
        return

    if preset["fps"] in PresetManager.FPS_VALUES:
        idx = PresetManager.FPS_VALUES.index(preset["fps"])
        main_window.fps_combo.setCurrentIndex(idx)

    main_window.iframe_interval.setValue(preset["iframe_interval"])
    main_window.diff_threshold.setValue(preset["diff_threshold"])
    main_window.variance_threshold.setValue(preset["variance_threshold"])
    main_window.color_fallback_threshold.setValue(preset["color_fallback_threshold"])
    main_window.force_i_threshold.setValue(preset["force_i_threshold"])
    main_window.codebook_size.setValue(preset["codebook_size"])
    main_window.kmeans_spin.setValue(preset["kmeans_iter"])
    main_window.iframe_weight.setValue(preset["iframe_weight"])
    main_window.motion_thresh.setValue(preset["motion_thresh"])
    main_window.dither_check.setChecked(preset["dither"])
    main_window.motion_check.setChecked(preset["motion"])
    main_window.audio_format.setCurrentText(preset["audio_format"])
    main_window.sample_rate.setValue(preset["sample_rate"])
    main_window.volume.setValue(preset["volume"])
    main_window.no_audio_check.setChecked(preset["no_audio"])

    workers = preset.get("workers", os.cpu_count() or 4)
    main_window.workers_spin.setValue(workers)

    skip_enabled = preset.get("skip_video_enabled", False)
    main_window.skip_video_check.setChecked(skip_enabled)

    skip_buttons = preset.get("skip_buttons", ["A"])
    for cb in main_window.button_checkboxes:
        cb.setChecked(cb.text() in skip_buttons)

    from .utils import _ensure_at_least_one_button_selected
    _ensure_at_least_one_button_selected(main_window)


def _get_current_preset_values(main_window):
    selected_buttons = [cb.text() for cb in main_window.button_checkboxes if cb.isChecked()]
    if not selected_buttons:
        selected_buttons = ["A"]

    return {
        "fps": main_window.fps_combo.currentData(),
        "iframe_interval": main_window.iframe_interval.value(),
        "diff_threshold": main_window.diff_threshold.value(),
        "variance_threshold": main_window.variance_threshold.value(),
        "color_fallback_threshold": main_window.color_fallback_threshold.value(),
        "force_i_threshold": main_window.force_i_threshold.value(),
        "codebook_size": main_window.codebook_size.value(),
        "kmeans_iter": main_window.kmeans_spin.value(),
        "iframe_weight": main_window.iframe_weight.value(),
        "motion_thresh": main_window.motion_thresh.value(),
        "dither": main_window.dither_check.isChecked(),
        "motion": main_window.motion_check.isChecked(),
        "audio_format": main_window.audio_format.currentText(),
        "sample_rate": main_window.sample_rate.value(),
        "volume": main_window.volume.value(),
        "no_audio": main_window.no_audio_check.isChecked(),
        "workers": main_window.workers_spin.value(),
        "skip_video_enabled": main_window.skip_video_check.isChecked(),
        "skip_buttons": selected_buttons,
    }


def _load_default_preset(main_window):
    if main_window.config_manager:
        preset_key = main_window.config_manager.get('SETTINGS', 'default_preset', 'preset_default')
        if preset_key in main_window.preset_manager.get_preset_names():
            return preset_key
    return "preset_default"


def _save_default_preset(main_window, preset_key):
    if main_window.config_manager:
        main_window.config_manager.set('SETTINGS', 'default_preset', preset_key)
        return True
    return False


def _on_preset_changed(main_window, _display):
    key = main_window.preset_combo.currentData()
    if key:
        _apply_preset(main_window, key)


def _reload_current_preset(main_window):
    key = main_window.preset_combo.currentData()
    if key and key in main_window.preset_manager.get_preset_names():
        _apply_preset(main_window, key)
        label = _display_name(main_window, key)
        QMessageBox.information(main_window, main_window.tr("preset_reloaded"),
                                main_window.tr("preset_reloaded_msg", name=label))


def _save_new_preset(main_window):
    preset_name, ok = QInputDialog.getText(main_window, main_window.tr("save_preset_title"),
                                           main_window.tr("save_preset_prompt"))

    if ok and preset_name.strip():
        preset_name = preset_name.strip()

        if preset_name in main_window.preset_manager.get_preset_names():
            reply = QMessageBox.question(main_window, main_window.tr("preset_exists"),
                                         main_window.tr("preset_exists_msg", name=preset_name),
                                         QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.No:
                return

        main_window.preset_manager.set_preset(preset_name, _get_current_preset_values(main_window))

        _rebuild_preset_combo(main_window, select_key=preset_name)
        _update_presets_submenu(main_window)

        QMessageBox.information(main_window, main_window.tr("preset_saved"),
                                main_window.tr("preset_saved_msg", name=preset_name))


def _update_current_preset(main_window):
    key = main_window.preset_combo.currentData()
    if main_window.preset_manager.is_builtin(key):
        label = _display_name(main_window, key)
        QMessageBox.warning(main_window, main_window.tr("preset_cannot_update"),
                            main_window.tr("preset_cannot_update_msg", name=label))
        return

    if key not in main_window.preset_manager.get_preset_names():
        return

    reply = QMessageBox.question(main_window, main_window.tr("preset_updated"),
                                 main_window.tr("preset_updated_confirm", name=key),
                                 QMessageBox.Yes | QMessageBox.No)
    if reply == QMessageBox.Yes:
        main_window.preset_manager.set_preset(key, _get_current_preset_values(main_window))
        QMessageBox.information(main_window, main_window.tr("preset_updated"),
                                main_window.tr("preset_updated_msg", name=key))


def _set_current_as_default(main_window):
    key = main_window.preset_combo.currentData()
    label = _display_name(main_window, key)
    if _save_default_preset(main_window, key):
        QMessageBox.information(main_window, main_window.tr("default_preset_set"),
                                main_window.tr("default_preset_set_msg", name=label))


def _delete_current_preset(main_window):
    key = main_window.preset_combo.currentData()
    if main_window.preset_manager.is_builtin(key):
        label = _display_name(main_window, key)
        QMessageBox.warning(main_window, main_window.tr("preset_cannot_delete"),
                            main_window.tr("preset_cannot_delete_msg", name=label))
        return

    if key not in main_window.preset_manager.get_preset_names():
        return

    reply = QMessageBox.question(main_window, main_window.tr("delete_preset_confirm"),
                                 main_window.tr("delete_preset_confirm_msg", name=key),
                                 QMessageBox.Yes | QMessageBox.No)
    if reply == QMessageBox.Yes:
        main_window.preset_manager.delete_preset(key)

        if main_window.config_manager:
            default = main_window.config_manager.get('SETTINGS', 'default_preset', 'preset_default')
            if default == key:
                _save_default_preset(main_window, "preset_default")

        _rebuild_preset_combo(main_window, select_key="preset_default")
        _update_presets_submenu(main_window)
        _apply_preset(main_window, "preset_default")

        QMessageBox.information(main_window, main_window.tr("preset_deleted"),
                                main_window.tr("preset_deleted_msg", name=key))
