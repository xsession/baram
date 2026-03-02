
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


# ---------------------------------------------------------------------------
# Shared VTK viewport background defaults
# ---------------------------------------------------------------------------

#: Light-mode gradient (top-left blue-grey → bottom-right light grey)
LIGHT_BG1 = (56 / 255, 61 / 255, 84 / 255)
LIGHT_BG2 = (209 / 255, 209 / 255, 209 / 255)

#: Dark-mode gradient (near-black → dark grey)
DARK_BG1 = (26 / 255, 26 / 255, 26 / 255)
DARK_BG2 = (64 / 255, 64 / 255, 64 / 255)


def _almost_equal_rgbf(
    a: tuple[float, float, float],
    b: tuple[float, float, float],
    tol: float = 1e-3,
) -> bool:
    return abs(a[0] - b[0]) <= tol and abs(a[1] - b[1]) <= tol and abs(a[2] - b[2]) <= tol


def apply_vtk_theme_defaults(view, dark_mode: bool) -> None:
    """Switch VTK viewport gradient between light/dark defaults.

    Only changes the background when it still matches the *opposite*
    theme's default – i.e. user-customised colours are preserved.

    Parameters
    ----------
    view:
        Any object exposing ``background1()``, ``background2()``,
        ``setBackground1(r, g, b)`` and ``setBackground2(r, g, b)``.
    dark_mode:
        ``True`` to apply dark defaults, ``False`` for light.
    """
    cur1 = tuple(view.background1())
    cur2 = tuple(view.background2())

    if dark_mode:
        if _almost_equal_rgbf(cur1, LIGHT_BG1) and _almost_equal_rgbf(cur2, LIGHT_BG2):
            view.setBackground1(*DARK_BG1)
            view.setBackground2(*DARK_BG2)
    else:
        if _almost_equal_rgbf(cur1, DARK_BG1) and _almost_equal_rgbf(cur2, DARK_BG2):
            view.setBackground1(*LIGHT_BG1)
            view.setBackground2(*LIGHT_BG2)


# ---------------------------------------------------------------------------
# Global dark-mode stylesheet
# ---------------------------------------------------------------------------


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
