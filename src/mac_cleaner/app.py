from __future__ import annotations

import sys
import warnings

from PySide6.QtCore import QtMsgType, qInstallMessageHandler
from PySide6.QtGui import QPalette, QColor
from PySide6.QtWidgets import QApplication, QStyleFactory

from mac_cleaner.ui.main_window import MainWindow

# Qt/macOS often dumps painter/timer noise to the terminal; keep the UI quiet.
_QT_NOISE = (
    "QPainter",
    "QBasicTimer",
    "QWidgetEffect",
    "libshiboken",
    "Overflow",
)


def _qt_message_handler(mode, _context, message: str) -> None:
    if any(token in message for token in _QT_NOISE):
        return
    if mode in (QtMsgType.QtCriticalMsg, QtMsgType.QtFatalMsg):
        sys.stderr.write(message + "\n")


def _apply_light_palette(app: QApplication) -> None:
    """Force readable selection colors (macOS native style often inverts text)."""
    palette = QPalette(app.palette())
    text = QColor("#0f172a")
    base = QColor("#ffffff")
    highlight = QColor("#bae6fd")
    palette.setColor(QPalette.ColorRole.WindowText, text)
    palette.setColor(QPalette.ColorRole.Text, text)
    palette.setColor(QPalette.ColorRole.ButtonText, text)
    palette.setColor(QPalette.ColorRole.Base, base)
    palette.setColor(QPalette.ColorRole.Window, QColor("#f1f5f9"))
    palette.setColor(QPalette.ColorRole.Highlight, highlight)
    palette.setColor(QPalette.ColorRole.HighlightedText, text)
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor("#94a3b8"))
    app.setPalette(palette)


def run() -> int:
    warnings.filterwarnings("ignore", message=".*libshiboken.*")
    qInstallMessageHandler(_qt_message_handler)

    app = QApplication(sys.argv)
    # Fusion makes stylesheet + palette selection colors reliable on macOS.
    if "Fusion" in QStyleFactory.keys():
        app.setStyle("Fusion")
    _apply_light_palette(app)
    app.setApplicationName("AppUnload")
    app.setOrganizationName("AppUnload")
    window = MainWindow()
    window.show()
    return app.exec()
