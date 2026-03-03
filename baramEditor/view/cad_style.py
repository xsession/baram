#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Fusion 360 / Plasticity-style stylesheet for BaramEditor.

Provides a dark, professional CAD-application look with:
- Slim toolbar ribbon at top
- Flat panel backgrounds
- Accent colour highlights
- Clean typography
"""

# Colour palette (Fusion 360 / Plasticity inspired)
ACCENT = '#0696D7'          # Fusion 360 blue
ACCENT_HOVER = '#0AA8ED'
ACCENT_PRESSED = '#0580B4'
BG_DARK = '#2D2D2D'         # Main window bg
BG_PANEL = '#333333'        # Panel bg
BG_INPUT = '#3C3C3C'        # Input fields
BG_HOVER = '#404040'
BG_SELECTED = '#0696D7'
BORDER = '#484848'
BORDER_LIGHT = '#555555'
TEXT = '#E0E0E0'
TEXT_DIM = '#888888'
TEXT_BRIGHT = '#FFFFFF'
DANGER = '#E04040'
SUCCESS = '#40C040'
WARNING = '#E0A020'

CAD_STYLESHEET = f"""
/* ─── Main Window ──────────────────────────────────────────── */
QMainWindow {{
    background-color: {BG_DARK};
}}

/* ─── Toolbar Ribbon ─────────────────────────────────────── */
QToolBar {{
    background-color: {BG_PANEL};
    border: none;
    border-bottom: 1px solid {BORDER};
    padding: 2px 4px;
    spacing: 2px;
}}
QToolBar::separator {{
    width: 1px;
    background: {BORDER};
    margin: 4px 6px;
}}
QToolBar QToolButton {{
    background: transparent;
    border: 1px solid transparent;
    border-radius: 4px;
    padding: 4px 8px;
    color: {TEXT};
    font-size: 11px;
    min-width: 40px;
}}
QToolBar QToolButton:hover {{
    background: {BG_HOVER};
    border-color: {BORDER_LIGHT};
}}
QToolBar QToolButton:pressed {{
    background: {ACCENT_PRESSED};
    border-color: {ACCENT};
}}
QToolBar QToolButton:checked {{
    background: {ACCENT};
    color: {TEXT_BRIGHT};
}}
QToolBar QToolButton:disabled {{
    color: {TEXT_DIM};
}}
QToolBar QLabel {{
    color: {TEXT_DIM};
    font-size: 9px;
    padding: 0 4px;
}}

/* ─── Dock Widgets (Panels) ──────────────────────────────── */
QDockWidget {{
    titlebar-close-icon: none;
    titlebar-normal-icon: none;
    color: {TEXT};
    font-weight: bold;
    font-size: 11px;
}}
QDockWidget::title {{
    background: {BG_PANEL};
    border-bottom: 1px solid {BORDER};
    padding: 6px 8px;
    text-align: left;
}}
QDockWidget > QWidget {{
    background: {BG_PANEL};
}}

/* ─── Panels (general) ───────────────────────────────────── */
QFrame#cadPanel, QWidget#cadPanel {{
    background: {BG_PANEL};
    border: none;
}}

/* ─── Tree Widget (Component Browser) ────────────────────── */
QTreeWidget {{
    background: {BG_PANEL};
    border: none;
    color: {TEXT};
    font-size: 12px;
    outline: none;
}}
QTreeWidget::item {{
    padding: 4px 2px;
    border: none;
    border-bottom: 1px solid {BORDER};
}}
QTreeWidget::item:hover {{
    background: {BG_HOVER};
}}
QTreeWidget::item:selected {{
    background: {BG_SELECTED};
    color: {TEXT_BRIGHT};
}}
QTreeWidget::branch {{
    background: {BG_PANEL};
}}
QHeaderView::section {{
    background: {BG_PANEL};
    color: {TEXT_DIM};
    border: none;
    border-bottom: 1px solid {BORDER};
    padding: 4px 8px;
    font-size: 10px;
    font-weight: bold;
    text-transform: uppercase;
}}

/* ─── List Widget (Timeline) ─────────────────────────────── */
QListWidget {{
    background: {BG_PANEL};
    border: none;
    color: {TEXT};
    font-size: 11px;
    outline: none;
}}
QListWidget::item {{
    padding: 3px 6px;
    border: none;
}}
QListWidget::item:hover {{
    background: {BG_HOVER};
}}
QListWidget::item:selected {{
    background: {BG_SELECTED};
    color: {TEXT_BRIGHT};
}}

/* ─── Buttons ────────────────────────────────────────────── */
QPushButton {{
    background: {BG_INPUT};
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 5px 14px;
    color: {TEXT};
    font-size: 11px;
    min-height: 22px;
}}
QPushButton:hover {{
    background: {BG_HOVER};
    border-color: {BORDER_LIGHT};
}}
QPushButton:pressed {{
    background: {ACCENT_PRESSED};
}}
QPushButton:disabled {{
    color: {TEXT_DIM};
    background: {BG_DARK};
}}
QPushButton#accentBtn {{
    background: {ACCENT};
    color: {TEXT_BRIGHT};
    border: none;
    font-weight: bold;
}}
QPushButton#accentBtn:hover {{
    background: {ACCENT_HOVER};
}}
QPushButton#dangerBtn {{
    background: {DANGER};
    color: {TEXT_BRIGHT};
    border: none;
}}

/* ─── Line Edit / Input ──────────────────────────────────── */
QLineEdit {{
    background: {BG_INPUT};
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 4px 8px;
    color: {TEXT};
    font-size: 11px;
    selection-background-color: {ACCENT};
}}
QLineEdit:focus {{
    border-color: {ACCENT};
}}

/* ─── Spin boxes ─────────────────────────────────────────── */
QDoubleSpinBox, QSpinBox {{
    background: {BG_INPUT};
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 3px 6px;
    color: {TEXT};
    font-size: 11px;
}}
QDoubleSpinBox:focus, QSpinBox:focus {{
    border-color: {ACCENT};
}}

/* ─── Combo Box ──────────────────────────────────────────── */
QComboBox {{
    background: {BG_INPUT};
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 4px 8px;
    color: {TEXT};
    font-size: 11px;
}}
QComboBox:hover {{
    border-color: {BORDER_LIGHT};
}}
QComboBox::drop-down {{
    border: none;
    width: 20px;
}}
QComboBox QAbstractItemView {{
    background: {BG_PANEL};
    border: 1px solid {BORDER};
    color: {TEXT};
    selection-background-color: {ACCENT};
}}

/* ─── Scroll Bars (thin, modern) ─────────────────────────── */
QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {BORDER_LIGHT};
    border-radius: 4px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: {TEXT_DIM};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 8px;
    margin: 0;
}}
QScrollBar::handle:horizontal {{
    background: {BORDER_LIGHT};
    border-radius: 4px;
    min-width: 30px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {TEXT_DIM};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}

/* ─── Labels ─────────────────────────────────────────────── */
QLabel {{
    color: {TEXT};
    font-size: 11px;
}}
QLabel#panelTitle {{
    color: {TEXT_BRIGHT};
    font-size: 12px;
    font-weight: bold;
    padding: 4px 0;
}}
QLabel#sectionLabel {{
    color: {TEXT_DIM};
    font-size: 10px;
    font-weight: bold;
    text-transform: uppercase;
    padding: 8px 0 2px 0;
}}
QLabel#dimLabel {{
    color: {TEXT_DIM};
    font-size: 10px;
}}

/* ─── Group Box ──────────────────────────────────────────── */
QGroupBox {{
    background: {BG_PANEL};
    border: 1px solid {BORDER};
    border-radius: 6px;
    margin-top: 12px;
    padding-top: 14px;
    color: {TEXT};
    font-size: 11px;
    font-weight: bold;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
    color: {TEXT_DIM};
}}

/* ─── Menu Bar ───────────────────────────────────────────── */
QMenuBar {{
    background: {BG_PANEL};
    color: {TEXT};
    border-bottom: 1px solid {BORDER};
    font-size: 11px;
}}
QMenuBar::item {{
    padding: 4px 10px;
    background: transparent;
}}
QMenuBar::item:selected {{
    background: {BG_HOVER};
}}
QMenu {{
    background: {BG_PANEL};
    border: 1px solid {BORDER};
    color: {TEXT};
    font-size: 11px;
}}
QMenu::item {{
    padding: 5px 28px 5px 20px;
}}
QMenu::item:selected {{
    background: {ACCENT};
    color: {TEXT_BRIGHT};
}}
QMenu::separator {{
    height: 1px;
    background: {BORDER};
    margin: 4px 8px;
}}

/* ─── Status Bar ─────────────────────────────────────────── */
QStatusBar {{
    background: {BG_PANEL};
    color: {TEXT_DIM};
    border-top: 1px solid {BORDER};
    font-size: 10px;
    min-height: 22px;
}}
QStatusBar QLabel {{
    color: {TEXT_DIM};
    font-size: 10px;
    padding: 0 6px;
}}

/* ─── Dialogs ────────────────────────────────────────────── */
QDialog {{
    background: {BG_DARK};
}}
QDialogButtonBox QPushButton {{
    min-width: 80px;
}}

/* ─── Check Box ──────────────────────────────────────────── */
QCheckBox {{
    color: {TEXT};
    font-size: 11px;
    spacing: 6px;
}}

/* ─── Tab Widget ─────────────────────────────────────────── */
QTabWidget::pane {{
    border: 1px solid {BORDER};
    background: {BG_PANEL};
}}
QTabBar::tab {{
    background: {BG_DARK};
    color: {TEXT_DIM};
    border: none;
    padding: 6px 14px;
    font-size: 11px;
}}
QTabBar::tab:selected {{
    background: {BG_PANEL};
    color: {TEXT_BRIGHT};
    border-bottom: 2px solid {ACCENT};
}}
QTabBar::tab:hover {{
    color: {TEXT};
}}

/* ─── Progress Bar ───────────────────────────────────────── */
QProgressBar {{
    background: {BG_INPUT};
    border: 1px solid {BORDER};
    border-radius: 4px;
    text-align: center;
    color: {TEXT};
    font-size: 10px;
    min-height: 14px;
}}
QProgressBar::chunk {{
    background: {ACCENT};
    border-radius: 3px;
}}

/* ─── Tool Tip ───────────────────────────────────────────── */
QToolTip {{
    background: {BG_DARK};
    color: {TEXT};
    border: 1px solid {BORDER};
    padding: 4px 8px;
    font-size: 11px;
}}

/* ─── Splitter ───────────────────────────────────────────── */
QSplitter::handle {{
    background: {BORDER};
}}
QSplitter::handle:horizontal {{
    width: 2px;
}}
QSplitter::handle:vertical {{
    height: 2px;
}}
"""
