# ui/widgets/no_wheel_filter.py
from ui.qt_compat import QObject, QEvent


class NoWheelEventFilter(QObject):
    def eventFilter(self, obj, event):
        if event.type() == QEvent.Wheel:
            return True
        return super().eventFilter(obj, event)
