
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QFile, QIODevice, QTextStream
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication, QWidget


def allDirectChildrenAreHidden(widget: QWidget) -> bool:
    children = [child for child in widget.children() if isinstance(child, QWidget)]
    return all(child.isHidden() for child in children) if children else True


def load_stylesheet_from_resource(resource_path: str) -> str:
    file = QFile(resource_path)
    if not file.open(QIODevice.ReadOnly | QIODevice.Text):
        return ''

    stream = QTextStream(file)
    return stream.readAll()


def _dark_palette() -> QPalette:
    palette = QPalette()

    window = QColor(53, 53, 53)
    base = QColor(35, 35, 35)
    alt_base = QColor(53, 53, 53)
    text = QColor(220, 220, 220)
    disabled_text = QColor(127, 127, 127)
    button = QColor(53, 53, 53)
    highlight = QColor(42, 130, 218)
    highlighted_text = QColor(0, 0, 0)

    palette.setColor(QPalette.Window, window)
    palette.setColor(QPalette.WindowText, text)
    palette.setColor(QPalette.Base, base)
    palette.setColor(QPalette.AlternateBase, alt_base)
    palette.setColor(QPalette.ToolTipBase, text)
    palette.setColor(QPalette.ToolTipText, text)
    palette.setColor(QPalette.Text, text)
    palette.setColor(QPalette.Button, button)
    palette.setColor(QPalette.ButtonText, text)
    palette.setColor(QPalette.BrightText, QColor(255, 0, 0))
    palette.setColor(QPalette.Highlight, highlight)
    palette.setColor(QPalette.HighlightedText, highlighted_text)
    palette.setColor(QPalette.Link, highlight)

    palette.setColor(QPalette.Disabled, QPalette.Text, disabled_text)
    palette.setColor(QPalette.Disabled, QPalette.ButtonText, disabled_text)
    palette.setColor(QPalette.Disabled, QPalette.WindowText, disabled_text)

    return palette


def apply_dark_mode_stylesheet(app: QWidget, enabled: bool, resource_path: str = ':/ElegantDark.qss'):
    """Apply/revert dark mode globally.

    Uses a dark QPalette (fixes default-widget white backgrounds) plus optional QSS from Qt resources.
    """

    qapp: Optional[QApplication] = QApplication.instance()
    if enabled:
        if qapp is not None:
            # Fusion style tends to respect palette more consistently across widgets.
            qapp.setStyle('Fusion')
            qapp.setPalette(_dark_palette())

        qss = load_stylesheet_from_resource(resource_path)
        if qss:
            app.setStyleSheet(qss)
    else:
        if qapp is not None:
            qapp.setPalette(qapp.style().standardPalette())

        app.setStyleSheet('')
