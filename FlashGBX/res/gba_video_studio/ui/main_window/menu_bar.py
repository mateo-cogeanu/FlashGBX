# ui/main_window/menu_bar.py
from ui.qt_compat import QMenu, QAction
from ui.dialogs import show_about_dialog, show_contribute_dialog

_LANGUAGES = {
    "english":             "English",
    "spanish":             "Español",
    "br_portuguese":       "Português (Brasil)",
    "french":              "Français",
    "german":              "Deutsch",
    "italian":             "Italiano",
    "portuguese":          "Português",
    "dutch":               "Nederlands",
    "polish":              "Polski",
    "turkish":             "Türkçe",
    "vietnamese":          "Tiếng Việt",
    "indonesian":          "Bahasa Indonesia",
    "hindi":               "हिन्दी",
    "russian":             "Русский",
    "japanese":            "日本語",
    "chinese_simplified":  "简体中文",
    "chinese_traditional": "繁體中文",
    "korean":              "한국어",
}


def _setup_menu_bar(main_window):
    menubar = main_window.menuBar()

    main_window._menu_file = menubar.addMenu(main_window.tr("file_menu"))
    main_window.action_open_video = QAction(main_window.tr("open_video"), main_window)
    main_window.action_open_video.setShortcut("Ctrl+O")
    main_window.action_open_video.triggered.connect(lambda checked=False: main_window.open_video_dialog())
    main_window._menu_file.addAction(main_window.action_open_video)

    main_window.action_build_rom = QAction(main_window.tr("menu_build_rom"), main_window)
    main_window.action_build_rom.setShortcut("Ctrl+B")
    main_window.action_build_rom.setEnabled(False)
    main_window.action_build_rom.triggered.connect(lambda checked=False: main_window.export_video())
    main_window._menu_file.addAction(main_window.action_build_rom)

    main_window._menu_file.addSeparator()
    main_window.action_exit = QAction(main_window.tr("exit_app"), main_window)
    main_window.action_exit.setShortcut("Ctrl+Q")
    main_window.action_exit.triggered.connect(main_window.close)
    main_window._menu_file.addAction(main_window.action_exit)

    main_window._menu_presets = menubar.addMenu(main_window.tr("presets_menu"))
    main_window.presets_submenu = QMenu(main_window.tr("presets_submenu"), main_window)
    main_window._update_presets_submenu()
    main_window._menu_presets.addMenu(main_window.presets_submenu)
    main_window._menu_presets.addSeparator()

    main_window.action_save_preset = QAction(main_window.tr("save_preset"), main_window)
    main_window.action_save_preset.triggered.connect(lambda checked=False: main_window._save_new_preset())
    main_window._menu_presets.addAction(main_window.action_save_preset)

    main_window.action_update_preset = QAction(main_window.tr("update_current_preset"), main_window)
    main_window.action_update_preset.triggered.connect(lambda checked=False: main_window._update_current_preset())
    main_window._menu_presets.addAction(main_window.action_update_preset)

    main_window.action_set_default_preset = QAction(main_window.tr("set_current_as_default"), main_window)
    main_window.action_set_default_preset.triggered.connect(lambda checked=False: main_window._set_current_as_default())
    main_window._menu_presets.addAction(main_window.action_set_default_preset)

    main_window._menu_presets.addSeparator()

    main_window.action_delete_preset = QAction(main_window.tr("delete_preset"), main_window)
    main_window.action_delete_preset.triggered.connect(lambda checked=False: main_window._delete_current_preset())
    main_window._menu_presets.addAction(main_window.action_delete_preset)

    main_window._menu_settings = menubar.addMenu(main_window.tr("settings_menu"))

    main_window.language_menu = QMenu(main_window.tr("language_menu"), main_window)
    _setup_language_menu(main_window)
    main_window._menu_settings.addMenu(main_window.language_menu)

    main_window._menu_settings.addSeparator()

    main_window.remember_paths_action = QAction(main_window.tr("remember_file_paths"), main_window)
    main_window.remember_paths_action.setCheckable(True)
    if main_window.config_manager:
        try:
            main_window.remember_paths_action.setChecked(
                main_window.config_manager.getboolean('SETTINGS', 'remember_file_paths', False))
        except Exception:
            main_window.remember_paths_action.setChecked(False)
    main_window.remember_paths_action.triggered.connect(main_window._on_remember_paths_toggled)
    main_window._menu_settings.addAction(main_window.remember_paths_action)

    main_window._menu_help = menubar.addMenu(main_window.tr("help_menu"))
    main_window.action_about = QAction(main_window.tr("about_menu"), main_window)
    main_window.action_about.triggered.connect(
        lambda checked=False: show_about_dialog(main_window, main_window.VERSION, main_window.translator))
    main_window._menu_help.addAction(main_window.action_about)
    main_window.action_contribute = QAction(main_window.tr("contribute_menu"), main_window)
    main_window.action_contribute.triggered.connect(
        lambda checked=False: show_contribute_dialog(main_window, main_window.translator))
    main_window._menu_help.addAction(main_window.action_contribute)


def _setup_language_menu(main_window):
    main_window.language_menu.clear()
    main_window.language_actions = {}

    current_lang = "english"
    if main_window.config_manager:
        try:
            current_lang = main_window.config_manager.get('SETTINGS', 'language', 'english')
        except Exception:
            pass

    for lang_key, lang_name in _LANGUAGES.items():
        action = main_window.language_menu.addAction(lang_name)
        action.setCheckable(True)
        action.setChecked(lang_key == current_lang)
        action.triggered.connect(lambda checked=False, lk=lang_key: main_window.change_language(lk))
        main_window.language_actions[lang_key] = action


def retranslate_menus(main_window):
    tr = main_window.translator.tr
    menus = main_window.menuBar().actions()
    for action, key in zip(menus, ["file_menu", "presets_menu", "settings_menu", "help_menu"]):
        action.setText(tr(key))
    main_window.language_menu.setTitle(tr("language_menu"))
    main_window.presets_submenu.setTitle(tr("presets_submenu"))
    main_window.action_open_video.setText(tr("open_video"))
    main_window.action_build_rom.setText(tr("menu_build_rom"))
    main_window.action_exit.setText(tr("exit_app"))
    main_window.action_save_preset.setText(tr("save_preset"))
    main_window.action_update_preset.setText(tr("update_current_preset"))
    main_window.action_set_default_preset.setText(tr("set_current_as_default"))
    main_window.action_delete_preset.setText(tr("delete_preset"))
    main_window.remember_paths_action.setText(tr("remember_file_paths"))
    main_window.action_about.setText(tr("about_menu"))
    main_window.action_contribute.setText(tr("contribute_menu"))
