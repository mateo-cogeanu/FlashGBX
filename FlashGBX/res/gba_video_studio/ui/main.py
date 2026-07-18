# ui/main.py
# Modified for FlashGBX on 2026-07-18: integrated-runtime behavior.
import os
import sys
import importlib
import time
import threading
from pathlib import Path

if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).parent.parent

sys.path.insert(0, str(BASE_DIR))

from ui.qt_compat import QApplication, exec_app, QT_BACKEND, QIcon, QMessageBox, QFileDialog, exec_dialog
from ui.video_editor import VideoEditor


def _register_install_path(version: str):
    # FlashGBX ships and updates this tool as a bundled component. Do not
    # register the writable runtime copy as a separate Windows installation.
    if os.environ.get("FLASHGBX_VIDEO_STUDIO") == "1":
        return
    if sys.platform != "win32":
        return
    try:
        import winreg
        exe_path    = sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(__file__)
        install_dir = os.path.dirname(exe_path)

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\CompuMax\GBAVideoStudio") as k:
                registered, _ = winreg.QueryValueEx(k, "InstallPath")
                if os.path.normcase(registered) == os.path.normcase(install_dir):
                    return
        except OSError:
            pass

        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\CompuMax\GBAVideoStudio")
        winreg.SetValueEx(key, "InstallPath", 0, winreg.REG_SZ, install_dir)
        winreg.SetValueEx(key, "Executable",  0, winreg.REG_SZ, exe_path)
        winreg.SetValueEx(key, "Version",     0, winreg.REG_SZ, version)
        winreg.CloseKey(key)
    except Exception:
        pass


def _install_exception_hook(translator=None):
    import traceback
    _tr = translator.tr if translator else lambda k, **kw: k

    def handle_exception(exc_type, exc_value, exc_tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        tb_str = ''.join(traceback.format_exception(exc_type, exc_value, exc_tb))
        print(tb_str)
        try:
            app = QApplication.instance()
            if app is not None:
                msg = QMessageBox()
                msg.setWindowTitle(_tr('error_dialog_title', default='Error'))
                msg.setIcon(QMessageBox.Critical)
                msg.setText(_tr('error_dialog_text', default='An unexpected error occurred:'))
                msg.setDetailedText(tb_str)
                msg.setStandardButtons(QMessageBox.Ok)
                exec_dialog(msg)
        except Exception:
            pass

    sys.excepthook = handle_exception


def warm_up_system_resources():
    try:
        _ = QFileDialog()
    except:
        pass


def load_icon():
    possible_paths = []
    
    if getattr(sys, 'frozen', False):
        exe_dir = Path(sys.executable).parent
        
        possible_paths.extend([
            exe_dir / "assets" / "icon.png",
            exe_dir / "assets" / "icon.ico",
        ])
        
        if hasattr(sys, '_MEIPASS'):
            possible_paths.append(Path(sys._MEIPASS) / "assets" / "icon.png")
    else:
        base_dir = Path(__file__).parent.parent
        possible_paths.append(base_dir / "assets" / "icon.png")
    
    for icon_path in possible_paths:
        if icon_path.exists():
            try:
                return QIcon(str(icon_path))
            except Exception:
                pass
    return None


def main():
    if os.name == 'nt':
        os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
        os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
        os.environ["QT_SCALE_FACTOR_ROUNDING_POLICY"] = "PassThrough"

    app = QApplication(sys.argv)

    try:
        from ui.qt_compat import QT_BACKEND
        if QT_BACKEND == "PySide6":
            from PySide6.QtCore import qInstallMessageHandler, QtMsgType
        else:
            from PySide2.QtCore import qInstallMessageHandler, QtMsgType

        _QT_SUPPRESSED = {
            "OpenType support missing",
            "encountered a rendering issue",
        }

        def _qt_message_filter(msg_type, context, msg):
            if msg_type == QtMsgType.QtWarningMsg:
                if any(s in msg for s in _QT_SUPPRESSED):
                    return
            import sys as _sys
            if msg_type in (QtMsgType.QtCriticalMsg, QtMsgType.QtFatalMsg):
                print(msg, file=_sys.stderr)
            elif msg_type == QtMsgType.QtWarningMsg:
                print(msg, file=_sys.stderr)

        qInstallMessageHandler(_qt_message_filter)
    except Exception:
        pass

    if os.name == 'nt':
        app.setStyle("windowsvista")
        app.setProperty("darkMode", False)
    
    language = "english"
    try:
        from core.config_manager import ConfigManager
        config_manager = ConfigManager()
        language = config_manager.get('SETTINGS', 'language', 'english')
        valid_languages = ["english", "spanish", "br_portuguese", "french", "german", 
                          "italian", "portuguese", "dutch", "polish", "turkish", 
                          "vietnamese", "indonesian", "hindi", "russian", "japanese", 
                          "chinese_simplified", "chinese_traditional", "korean"]
        if language not in valid_languages:
            language = "english"
    except Exception:
        pass
    
    from utils.translator import Translator
    translator = Translator(lang_dir="lang", default_lang=language)
    
    _install_exception_hook(translator)
    
    from ui.splash_screen import GBASplashScreen
    splash = GBASplashScreen(translator)
    splash.show()
    _tr = translator.tr
    
    libraries_to_preload = [
        "cv2",
        "numpy",
        "PySide6.QtCore" if QT_BACKEND == "PySide6" else "PySide2.QtCore",
        "PySide6.QtGui" if QT_BACKEND == "PySide6" else "PySide2.QtGui",
        "PySide6.QtWidgets" if QT_BACKEND == "PySide6" else "PySide2.QtWidgets",
    ]
    
    total = len(libraries_to_preload)
    for i, module_name in enumerate(libraries_to_preload):
        try:
            progress = int((i / total) * 80)
            module_display = module_name.split('.')[-1]
            splash.set_progress(progress, _tr('splash_loading', default='Loading') + ' ' + module_display + '...')
            importlib.import_module(module_name)
            time.sleep(0.02)
        except Exception:
            continue
    
    splash.set_progress(90, _tr('splash_initializing_interface', default='Initializing interface...'))
    time.sleep(0.2)
    
    app_icon = load_icon()
    if app_icon:
        app.setWindowIcon(app_icon)
    
    editor = VideoEditor(translator=translator)
    if app_icon:
        try:
            editor.setWindowIcon(app_icon)
        except Exception:
            pass

    _register_install_path(editor.VERSION)

    splash.set_progress(100, _tr('splash_ready', default='Ready!'))
    time.sleep(0.2)
    splash.finish(editor)
    
    editor.show()
    
    if len(sys.argv) > 1:
        from ui.qt_compat import QTimer
        QTimer.singleShot(500, lambda: editor.load_video(sys.argv[1]))
    
    threading.Thread(target=warm_up_system_resources, daemon=True).start()
    
    return exec_app(app)


if __name__ == "__main__":
    sys.exit(main())
