# ui/dialogs/contribute_dialog.py
from ui.qt_compat import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, Qt


def show_contribute_dialog(parent, translator):
    _tr = translator.tr

    dlg = QDialog(parent)
    dlg.setWindowTitle(_tr("contribute_title"))
    dlg.setWindowFlags(
        dlg.windowFlags()
        & ~Qt.WindowContextHelpButtonHint
        & ~Qt.WindowMaximizeButtonHint
    )
    dlg.setFixedWidth(460)

    layout = QVBoxLayout(dlg)
    layout.setSpacing(12)
    layout.setContentsMargins(16, 16, 16, 16)

    lbl = QLabel(_tr("contribute_text"))
    lbl.setTextFormat(Qt.RichText)
    lbl.setTextInteractionFlags(Qt.TextBrowserInteraction)
    lbl.setOpenExternalLinks(True)
    lbl.setWordWrap(True)
    layout.addWidget(lbl)

    btn_row = QHBoxLayout()
    btn_row.addStretch()
    btn_close = QPushButton(_tr("close", default="Close"))
    btn_close.setDefault(True)
    btn_close.setFixedWidth(80)
    btn_close.clicked.connect(dlg.accept)
    btn_row.addWidget(btn_close)
    layout.addLayout(btn_row)

    dlg.exec_()
