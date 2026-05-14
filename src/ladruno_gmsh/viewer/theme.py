"""Palettes, stylesheets and theme persistence."""
from __future__ import annotations


_DARK = {
    "bg":        "#1f2227",
    "panel":     "#262a31",
    "panel_alt": "#2f343c",
    "fg":        "#e6e8eb",
    "fg_dim":    "#a0a6b0",
    "accent":    "#4a9eff",
    "warn":      "#f3b23f",
    "error":     "#e26a6a",
    "ok":        "#5db075",
    "border":    "#383d46",
}


def palette() -> dict[str, str]:
    return dict(_DARK)


def stylesheet() -> str:
    p = palette()
    return f"""
QMainWindow, QWidget {{
    background: {p['bg']};
    color: {p['fg']};
    font-size: 11px;
}}
QDockWidget::title {{
    background: {p['panel_alt']};
    padding: 4px 8px;
    border-bottom: 1px solid {p['border']};
}}
QDockWidget {{
    border: 1px solid {p['border']};
}}
QToolBar {{
    background: {p['panel']};
    border-bottom: 1px solid {p['border']};
    spacing: 4px;
    padding: 2px;
}}
QPushButton {{
    background: {p['panel_alt']};
    border: 1px solid {p['border']};
    padding: 4px 10px;
    border-radius: 3px;
    color: {p['fg']};
}}
QPushButton:hover {{
    background: {p['accent']};
    color: white;
}}
QPushButton:disabled {{
    color: {p['fg_dim']};
    background: {p['panel']};
}}
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
    background: {p['panel']};
    border: 1px solid {p['border']};
    padding: 3px 6px;
    border-radius: 3px;
    color: {p['fg']};
}}
QListWidget, QTreeWidget, QTableWidget, QPlainTextEdit {{
    background: {p['panel']};
    border: 1px solid {p['border']};
    color: {p['fg']};
}}
QHeaderView::section {{
    background: {p['panel_alt']};
    color: {p['fg_dim']};
    padding: 3px 6px;
    border: 1px solid {p['border']};
}}
QTabWidget::pane {{
    border: 1px solid {p['border']};
}}
QTabBar::tab {{
    background: {p['panel']};
    padding: 4px 10px;
    border: 1px solid {p['border']};
    border-bottom: none;
}}
QTabBar::tab:selected {{
    background: {p['panel_alt']};
    color: {p['accent']};
}}
QStatusBar {{
    background: {p['panel']};
    color: {p['fg_dim']};
    border-top: 1px solid {p['border']};
}}
QLabel[role="title"] {{
    color: {p['accent']};
    font-weight: bold;
    padding: 4px 2px;
}}
QLabel[role="hint"] {{
    color: {p['fg_dim']};
}}
"""
