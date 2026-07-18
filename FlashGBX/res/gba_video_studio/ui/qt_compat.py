#ui/qt_compat.py
import sys


def _detect_backend():
    if sys.version_info >= (3, 10):
        try:
            import PySide6
            return "PySide6"
        except ImportError:
            pass
    
    try:
        import PySide2
        return "PySide2"
    except ImportError:
        pass
    
    try:
        import PySide6
        return "PySide6"
    except ImportError:
        pass

    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}"
    raise ImportError(
        f"No Qt backend found (Python {py_ver}).\n"
        f"Install PySide6 (Python >= 3.10) or PySide2 (Python 3.8/3.9):\n"
        f"  pip install PySide6    # Python 3.10+\n"
        f"  pip install PySide2==5.15.2  # Python 3.8/3.9"
    )


QT_BACKEND: str = _detect_backend()


if QT_BACKEND == "PySide6":
    from PySide6.QtCore import (
        Qt, Signal, Slot, QTimer, QThread, QObject, QStandardPaths, QUrl, QEvent,
        QSize, QRect, QPoint, QRectF, QPointF,
        QMetaObject, QCoreApplication,
    )
    from PySide6.QtGui import (
        QFont, QColor, QPen, QBrush, QPixmap, QImage,
        QPainter, QIcon, QCursor, QKeySequence,
        QIntValidator, QValidator, QKeyEvent,
        QAction, QMouseEvent, QWheelEvent,
        QShortcut, QActionGroup,
    )
    from PySide6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QDialog,
        QVBoxLayout, QHBoxLayout, QGridLayout, QFormLayout,
        QStackedWidget, QSplitter, QTabWidget, QTabBar,
        QLabel, QPushButton, QToolButton, QCheckBox, QRadioButton,
        QLineEdit, QSpinBox, QComboBox, QSlider, QProgressBar,
        QListWidget, QListWidgetItem,
        QGraphicsView, QGraphicsScene, QGraphicsLineItem,
        QGraphicsRectItem, QGraphicsPixmapItem,
        QFrame, QGroupBox, QSizePolicy,
        QFileDialog, QMessageBox, QColorDialog, QInputDialog,
        QDialogButtonBox, QButtonGroup,
        QSplashScreen, QScrollArea,
        QMenu, QMenuBar, QStatusBar, QDoubleSpinBox,
    )
    from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
    
    QMediaContent = None  

    def exec_dialog(dlg) -> int:
        return dlg.exec()
    
    def exec_app(app) -> int:
        return app.exec()

else:
    from PySide2.QtCore import (
        Qt, Signal, Slot, QTimer, QThread, QObject, QStandardPaths, QUrl, QEvent,
        QSize, QRect, QPoint, QRectF, QPointF,
        QMetaObject, QCoreApplication,
    )
    from PySide2.QtGui import (
        QFont, QColor, QPen, QBrush, QPixmap, QImage,
        QPainter, QIcon, QCursor, QKeySequence,
        QIntValidator, QValidator, QKeyEvent,
        QMouseEvent, QWheelEvent,
    )
    from PySide2.QtWidgets import (
        QApplication, QMainWindow, QWidget, QDialog,
        QVBoxLayout, QHBoxLayout, QGridLayout, QFormLayout,
        QStackedWidget, QSplitter, QTabWidget, QTabBar,
        QLabel, QPushButton, QToolButton, QCheckBox, QRadioButton,
        QLineEdit, QSpinBox, QComboBox, QSlider, QProgressBar,
        QListWidget, QListWidgetItem,
        QGraphicsView, QGraphicsScene, QGraphicsLineItem,
        QGraphicsRectItem, QGraphicsPixmapItem,
        QFrame, QGroupBox, QSizePolicy,
        QFileDialog, QMessageBox, QColorDialog, QInputDialog,
        QDialogButtonBox, QButtonGroup,
        QSplashScreen, QScrollArea,
        QMenu, QMenuBar, QStatusBar, QDoubleSpinBox,
        QAction, QShortcut, QActionGroup,
    )
    from PySide2.QtMultimedia import QMediaPlayer, QMediaContent
    
    QAudioOutput = None  

    def exec_dialog(dlg) -> int:
        return dlg.exec_()
    
    def exec_app(app) -> int:
        return app.exec_()


def get_align_center():
    if QT_BACKEND == "PySide6":
        return Qt.AlignmentFlag.AlignCenter
    return Qt.AlignCenter


def get_keep_aspect_ratio():
    if QT_BACKEND == "PySide6":
        return Qt.AspectRatioMode.KeepAspectRatio
    return Qt.KeepAspectRatio


def get_smooth_transformation():
    if QT_BACKEND == "PySide6":
        return Qt.TransformationMode.SmoothTransformation
    return Qt.SmoothTransformation


def get_fast_transformation():
    if QT_BACKEND == "PySide6":
        return Qt.TransformationMode.FastTransformation
    return Qt.FastTransformation


def get_horizontal():
    if QT_BACKEND == "PySide6":
        return Qt.Orientation.Horizontal
    return Qt.Horizontal


def get_vertical():
    if QT_BACKEND == "PySide6":
        return Qt.Orientation.Vertical
    return Qt.Vertical


def get_key_left():
    return Qt.Key_Left


def get_key_right():
    return Qt.Key_Right

def setup_media_player(player: QMediaPlayer, file_path: str):
    url = QUrl.fromLocalFile(file_path)
    
    if QT_BACKEND == "PySide6":
        player.setSource(url)
        if player.audioOutput() is None:
            audio_out = QAudioOutput()
            player.setAudioOutput(audio_out)
            audio_out.setVolume(1.0)
    else:
        player.setMedia(QMediaContent(url))


def set_media_player_position(player: QMediaPlayer, frame_num: int, fps: float):
    position_ms = int((frame_num / fps) * 1000)
    player.setPosition(position_ms)
