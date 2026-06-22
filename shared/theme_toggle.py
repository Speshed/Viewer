from __future__ import annotations

import os
import sys
import tempfile
import ctypes
from dataclasses import dataclass

from PySide6 import QtCore, QtGui, QtWidgets


_THEME_FILE = os.path.join(tempfile.gettempdir(), "addon_manager_theme.txt")
_BACK_TO_MENU_CALLBACK = None
_CACHE_SUBDIR = "addon_manager_icon_cache"


@dataclass
class Palette:
    BG_LIGHT: str = "#FFFFFF"
    BG_DARK: str = "#1E1E1E"
    FG_LIGHT: str = "#222222"
    FG_DARK: str = "#FFFFFF"
    ACCENT: str = "#F7921E"
    ACCENT_HOVER: str = "#FFA74B"
    ACCENT_PRESSED: str = "#E07E12"
    BORDER_LIGHT: str = "#dcdcdc"
    BORDER_DARK: str = "#3A3A3A"
    SOFT_HOVER: str = "#FFE3C2"
    SELECTED: str = "#FFC37A"
    SCROLL_TRACK_LIGHT: str = "#FAFAFA"
    SCROLL_TRACK_DARK: str = "#252525"


PALETTE = Palette()


_ICON_FILES: dict[str, list[str]] = {
    "logo": ["logo.png", "Manager-scaled.png"],
    "logo_white": ["logo_white.png", "Manager-scaled_white.png"],
    "app_icon": ["logo.ico", "app_icon.png", "Manager-scaled.png"],
    "back": ["back.png", "arrow-left.png"],
    "arrow_left": ["arrow-left.png"],
    "arrow_right": ["arrow-right.png"],
    "arrow_up": ["arrow-up.png"],
    "arrow_down": ["arrow-down.png"],
    "sort_up": ["arrow-up.png"],
    "sort_down": ["arrow-down.png"],
    "sun": ["sun.png"],
    "moon": ["moon.png"],
    "check": ["check.png"],
    "select": ["select.png"],
    "poloska": ["poloska.png"],
    "refresh": ["refresh.png", "free-icon-refresh-5234214.png"],
    "gear": ["free-icon-setting-3288004.png", "setting.png"],
    "login": ["free-icon-login-2623062.png", "login.png"],
    "insert": ["insert.png"],
    "sync": ["sync.png"],
    "warning": ["warning.png"],
    "error": ["error.png"],
    "ok": ["ok.png", "check mark.png", "approve_circle.png"],
    "alert": ["alert.png", "warning.png"],
    "info": ["ok.png", "alert.png"],
}


def _fallback_icon_dirs(primary: str) -> list[str]:
    dirs: list[str] = []
    p = os.path.abspath(primary) if primary else ""
    if p:
        dirs.append(p)

    root = getattr(sys, "_MEIPASS", os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    common = os.path.join(root, "icon")
    if common not in dirs:
        dirs.append(common)

    return dirs


def register_icon_files(extra: dict[str, list[str]]) -> None:
    for k, v in (extra or {}).items():
        if isinstance(v, list):
            _ICON_FILES[k] = list(v)


def _cache_dir(icon_dir: str) -> str:
    base = os.path.abspath(icon_dir or "")
    root = os.path.join(tempfile.gettempdir(), _CACHE_SUBDIR)
    os.makedirs(root, exist_ok=True)
    sub = os.path.join(root, os.path.basename(base) or "icon")
    os.makedirs(sub, exist_ok=True)
    return sub


def _qss_url(path: str) -> str:
    return (path or "").replace("\\", "/")


def _tint_pixmap(pm: QtGui.QPixmap, color: QtGui.QColor) -> QtGui.QPixmap:
    if pm.isNull():
        return pm
    tinted = QtGui.QPixmap(pm.size())
    tinted.fill(QtCore.Qt.transparent)
    p = QtGui.QPainter(tinted)
    p.setCompositionMode(QtGui.QPainter.CompositionMode_Source)
    p.drawPixmap(0, 0, pm)
    p.setCompositionMode(QtGui.QPainter.CompositionMode_SourceIn)
    p.fillRect(tinted.rect(), color)
    p.end()
    return tinted


def _ensure_color_copy(src_path: str, icon_dir: str, color: QtGui.QColor, suffix: str) -> str:
    try:
        if not src_path or not os.path.exists(src_path):
            return src_path
        cache = _cache_dir(icon_dir)
        name, ext = os.path.splitext(os.path.basename(src_path))
        dst = os.path.join(cache, f"{name}_{suffix}{ext}")
        if os.path.exists(dst):
            return dst
        pm = QtGui.QPixmap(src_path)
        if pm.isNull():
            return src_path
        out = _tint_pixmap(pm, color)
        out.save(dst)
        return dst
    except Exception:
        return src_path


def _ensure_white_copy(src_path: str, icon_dir: str) -> str:
    return _ensure_color_copy(src_path, icon_dir, QtGui.QColor("#FFFFFF"), "white")


def _ensure_black_copy(src_path: str, icon_dir: str) -> str:
    return _ensure_color_copy(src_path, icon_dir, QtGui.QColor("#000000"), "black")


def _ensure_scaled_copy(src_path: str, icon_dir: str, size_px: int, suffix: str) -> str:
    try:
        if not src_path or not os.path.exists(src_path):
            return src_path
        size_px = max(4, int(size_px))
        cache = _cache_dir(icon_dir)
        name, ext = os.path.splitext(os.path.basename(src_path))
        dst = os.path.join(cache, f"{name}_{suffix}_{size_px}px{ext}")
        if os.path.exists(dst):
            return dst
        pm = QtGui.QPixmap(src_path)
        if pm.isNull():
            return src_path
        out = pm.scaled(size_px, size_px, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
        out.save(dst)
        return dst
    except Exception:
        return src_path


def is_dark_theme(app: QtWidgets.QApplication | None = None) -> bool:
    app = app or QtWidgets.QApplication.instance()
    if app is None:
        return False
    prop = str(app.property("nik_theme") or "").strip().lower()
    if prop in ("dark", "night"):
        return True
    if prop in ("light", "day"):
        return False
    try:
        c = app.palette().color(QtGui.QPalette.Window)
        return c.lightness() < 128
    except Exception:
        return False


def _first_existing(names: list[str], icon_dir: str) -> str:
    for d in _fallback_icon_dirs(icon_dir):
        for n in names:
            p = os.path.join(d, n)
            if os.path.exists(p):
                return p
    return ""


def resolve_icon_path(
    name: str,
    icon_dir: str,
    app: QtWidgets.QApplication | None = None,
    tint_in_dark: bool = True,
) -> str:
    if not name:
        return ""
    if os.path.exists(name):
        p = os.path.abspath(name)
    else:
        candidates = _ICON_FILES.get(name, [])
        if name == "logo" and is_dark_theme(app):
            candidates = _ICON_FILES.get("logo_white", []) + candidates
        p = _first_existing(candidates, icon_dir)
        if not p:
            for d in _fallback_icon_dirs(icon_dir):
                direct = os.path.join(d, f"{name}.png")
                if os.path.exists(direct):
                    p = direct
                    break
    if not p:
        return ""
    if tint_in_dark and is_dark_theme(app):
        no_tint = {"logo", "logo_white", "app_icon", "warning", "gear", "setting", "ok", "none"}
        if name not in no_tint:
            return _ensure_white_copy(p, icon_dir)
    return p


def nik_icon(
    name: str,
    app: QtWidgets.QApplication | None = None,
    icon_dir: str = "",
    tint_in_dark: bool = True,
) -> QtGui.QIcon:
    p = resolve_icon_path(name, icon_dir, app=app, tint_in_dark=tint_in_dark)
    return QtGui.QIcon(p) if p else QtGui.QIcon()


def apply_themed_icon(widget_or_action, name: str, icon_dir: str) -> None:
    app = QtWidgets.QApplication.instance()
    icon = nik_icon(name, app=app, icon_dir=icon_dir)
    try:
        widget_or_action.setIcon(icon)
    except Exception:
        pass


def load_saved_theme(default: bool = False) -> bool:
    try:
        if os.path.exists(_THEME_FILE):
            v = (open(_THEME_FILE, "r", encoding="utf-8").read().strip().lower())
            return v in ("1", "true", "dark")
    except Exception:
        pass
    return bool(default)


def _save_theme(dark: bool) -> None:
    try:
        with open(_THEME_FILE, "w", encoding="utf-8") as f:
            f.write("dark" if dark else "light")
    except Exception:
        pass


def _build_qss(dark: bool, icon_dir: str = "") -> str:
    bg = PALETTE.BG_DARK if dark else PALETTE.BG_LIGHT
    fg = PALETTE.FG_DARK if dark else PALETTE.FG_LIGHT
    border = PALETTE.BORDER_DARK if dark else PALETTE.BORDER_LIGHT
    panel = bg if dark else "#FFFFFF"
    soft = "rgba(247,146,30,0.15)" if dark else "rgba(247,146,30,0.08)"
    pressed = "rgba(247,146,30,0.25)" if dark else "rgba(247,146,30,0.15)"
    dialog_soft = "rgba(247,146,30,0.15)" if dark else "rgba(247,146,30,0.10)"
    dialog_pressed = "rgba(247,146,30,0.25)" if dark else "rgba(247,146,30,0.20)"
    input_bg = bg if dark else "#FFFFFF"
    tip_bg = "#2a2a2a" if dark else "#FFFFFF"
    tip_fg = "#e0e0e0" if dark else "#222222"
    menu_bg = bg if dark else "#FFFFFF"
    group_border = "rgba(255,255,255,0.16)" if dark else "rgba(0,0,0,0.12)"
    hover_fg = "#000000"
    button_hover_fg = "#FFFFFF" if dark else "#000000"

    app = QtWidgets.QApplication.instance()
    down_arrow = resolve_icon_path("arrow_down", icon_dir, app=app, tint_in_dark=False)
    up_arrow = resolve_icon_path("arrow_up", icon_dir, app=app, tint_in_dark=False)
    left_arrow = resolve_icon_path("arrow_left", icon_dir, app=app, tint_in_dark=False)
    right_arrow = resolve_icon_path("arrow_right", icon_dir, app=app, tint_in_dark=False)
    check_off = resolve_icon_path("check", icon_dir, app=app, tint_in_dark=False)
    check_on = resolve_icon_path("select", icon_dir, app=app, tint_in_dark=False)
    check_mid = resolve_icon_path("poloska", icon_dir, app=app, tint_in_dark=False)

    if dark:
        if down_arrow:
            down_arrow = _ensure_white_copy(down_arrow, icon_dir)
        if up_arrow:
            up_arrow = _ensure_white_copy(up_arrow, icon_dir)
        if left_arrow:
            left_arrow = _ensure_white_copy(left_arrow, icon_dir)
        if right_arrow:
            right_arrow = _ensure_white_copy(right_arrow, icon_dir)
        if check_off:
            check_off = _ensure_white_copy(check_off, icon_dir)
        if check_on:
            check_on = _ensure_white_copy(check_on, icon_dir)
        if check_mid:
            check_mid = _ensure_white_copy(check_mid, icon_dir)

    down_arrow_url = _qss_url(down_arrow) if down_arrow else ""
    up_arrow_url = _qss_url(up_arrow) if up_arrow else ""
    left_arrow_url = _qss_url(left_arrow) if left_arrow else ""
    right_arrow_url = _qss_url(right_arrow) if right_arrow else ""
    check_off_url = _qss_url(check_off) if check_off else ""
    check_on_url = _qss_url(check_on) if check_on else ""
    check_mid_url = _qss_url(check_mid) if check_mid else ""
    tree_branch_qss = ""
    tree_right = _ensure_scaled_copy(right_arrow, icon_dir, 8, "tree") if right_arrow else ""
    tree_down = _ensure_scaled_copy(down_arrow, icon_dir, 8, "tree") if down_arrow else ""
    tree_right_url = _qss_url(tree_right) if tree_right else ""
    tree_down_url = _qss_url(tree_down) if tree_down else ""
    if tree_right_url and tree_down_url:
        tree_branch_qss = f"""
    QTreeView::branch, QTreeWidget::branch {{
        width: 8px;
        height: 8px;
    }}
    QTreeView::branch:closed:has-children, QTreeWidget::branch:closed:has-children {{
        image: url("{tree_right_url}");
    }}
    QTreeView::branch:open:has-children, QTreeWidget::branch:open:has-children {{
        image: url("{tree_down_url}");
    }}
    """
    return f"""
    * {{
        font-family: 'Segoe UI';
        font-size: 10.5pt;
        color: {fg};
        selection-background-color: {PALETTE.SELECTED};
        selection-color: #000000;
        outline: none;
    }}
    *:focus {{ outline: none; }}
    QWidget, QMainWindow, QDialog {{ background: {bg}; }}

    QLineEdit, QPlainTextEdit, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit,
    QTableView, QTreeView, QTableWidget, QTreeWidget, QListView, QListWidget {{
        background: {input_bg};
        border: 1px solid {border};
        border-radius: 10px;
        padding: 5px 8px;
        min-height: 22px;
        selection-background-color: {PALETTE.SELECTED};
        selection-color: #000000;
    }}
    QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{ border-color: {PALETTE.ACCENT_HOVER}; }}

    QHeaderView::section {{
        background: {panel};
        border: none;
        padding: 6px 10px;
    }}
    QHeaderView::section:hover {{ background: {PALETTE.SOFT_HOVER}; color: {hover_fg}; border-radius: 8px; }}
    QHeaderView::section:pressed {{ background: {PALETTE.SELECTED}; color: {hover_fg}; border-radius: 8px; }}

    QToolButton#btn_primary, QPushButton#btn_primary,
    QToolButton[class="primary"], QPushButton[class="primary"] {{
        background: {PALETTE.ACCENT};
        color: #FFFFFF;
        border: 1px solid {PALETTE.ACCENT};
        border-radius: 14px;
        padding: 6px 12px;
        min-height: 24px;
        font-weight: 600;
    }}
    QToolButton#btn_primary:hover, QPushButton#btn_primary:hover,
    QToolButton[class="primary"]:hover, QPushButton[class="primary"]:hover {{
        background: {PALETTE.SOFT_HOVER};
        color: {button_hover_fg};
        border-color: {PALETTE.ACCENT_HOVER};
    }}
    QToolButton#btn_primary:pressed, QPushButton#btn_primary:pressed,
    QToolButton[class="primary"]:pressed, QPushButton[class="primary"]:pressed {{
        background: {PALETTE.SELECTED};
        color: {button_hover_fg};
        border-color: {PALETTE.ACCENT_PRESSED};
    }}

    QPushButton, QToolButton {{
        background: {panel};
        border: 1px solid {border};
        border-radius: 14px;
        padding: 6px 12px;
        min-height: 24px;
        font-weight: 600;
    }}
    QPushButton[secondary="true"], QToolButton[secondary="true"],
    QToolButton#btn_secondary, QPushButton#btn_secondary,
    QDialogButtonBox QPushButton {{
        background: {panel};
        color: {fg};
        border: 1px solid {border};
        border-radius: 14px;
        padding: 6px 12px;
        min-height: 24px;
        font-weight: 600;
    }}
    QPushButton:hover, QToolButton:hover {{ background: {soft}; color: {button_hover_fg}; border-color: {PALETTE.ACCENT_HOVER}; }}
    QPushButton:pressed, QToolButton:pressed {{ background: {pressed}; color: {button_hover_fg}; border-color: {PALETTE.ACCENT_PRESSED}; }}

    QTreeView::item:hover, QTableView::item:hover, QTreeWidget::item:hover, QTableWidget::item:hover,
    QListView::item:hover, QListWidget::item:hover {{ background: {PALETTE.SOFT_HOVER}; color: {hover_fg}; border-radius: 8px; }}
    QTreeView::item:selected, QTableView::item:selected, QTreeWidget::item:selected, QTableWidget::item:selected,
    QListView::item:selected, QListWidget::item:selected {{ background: {PALETTE.SELECTED}; color: #000000; border-radius: 8px; }}
    {tree_branch_qss}

    QMenu {{ background: {menu_bg}; border: 1px solid {border}; border-radius: 10px; padding: 4px 0; }}
    QMenu::item {{ padding: 6px 12px; border-radius: 8px; margin: 2px 6px; }}
    QMenu::item:selected {{ background: {PALETTE.SOFT_HOVER}; color: {hover_fg}; }}
    QMenu::separator {{ height: 1px; background: {border}; margin: 4px 8px; }}

    QAbstractItemView::item {{ min-height: 22px; border-radius: 8px; margin: 1px 4px; padding: 2px 6px; }}
    QAbstractItemView::item:focus {{ outline: none; border: none; }}

    QComboBox QAbstractItemView {{ outline: none; }}
    QComboBox QAbstractItemView::item {{ border: none; }}
    QComboBox QAbstractItemView::item:hover {{ border: none; }}
    QComboBox QAbstractItemView::item:selected {{ border: none; }}
    QComboBox QAbstractItemView::item:selected:active {{ border: none; outline: none; }}
    QComboBox QAbstractItemView::item:selected:!active {{ border: none; outline: none; }}
    QComboBox QAbstractItemView::item:focus {{ outline: none; border: none; }}

    QGroupBox {{
        background: {bg};
        border: 1px solid {group_border};
        border-radius: 12px;
        margin-top: 16px;
        padding-top: 8px;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        left: 12px;
        padding: 0 8px;
        background-color: {bg};
        color: {fg};
    }}

    QComboBox::drop-down, QDateEdit::drop-down {{ border: none; width: 20px; background: transparent; }}
    QComboBox::down-arrow, QDateEdit::down-arrow {{
        image: url("{down_arrow_url}");
        width: 12px;
        height: 12px;
        margin-right: 4px;
    }}

    QCheckBox::indicator, QListView::indicator, QListWidget::indicator {{ width: 18px; height: 18px; }}
    QCheckBox::indicator:unchecked, QListView::indicator:unchecked, QListWidget::indicator:unchecked {{ image: url("{check_off_url}"); }}
    QCheckBox::indicator:checked, QListView::indicator:checked, QListWidget::indicator:checked {{ image: url("{check_on_url}"); }}
    QCheckBox::indicator:indeterminate, QListView::indicator:indeterminate, QListWidget::indicator:indeterminate {{ image: url("{check_mid_url}"); }}

    QScrollBar:vertical {{ background: {bg}; width: 12px; margin: 16px 0 16px 0; border: none; }}
    QScrollBar::handle:vertical {{ background: rgba(247,146,30,0.12); min-height: 24px; border-radius: 6px; border: 1px solid {PALETTE.ACCENT_HOVER}; }}
    QScrollBar::handle:vertical:hover {{ background: rgba(247,146,30,0.15); border: 1px solid {PALETTE.ACCENT_HOVER}; }}
    QScrollBar::handle:vertical:pressed {{ background: rgba(247,146,30,0.25); border: 1px solid {PALETTE.ACCENT_PRESSED}; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ background: {bg}; height: 16px; subcontrol-origin: margin; border: none; border-radius: 0; image: none; }}
    QScrollBar::add-line:vertical {{ subcontrol-position: bottom; border: none; }}
    QScrollBar::sub-line:vertical {{ subcontrol-position: top; border: none; }}
    QScrollBar::add-line:vertical:hover, QScrollBar::sub-line:vertical:hover {{ background: rgba(247,146,30,0.15); }}
    QScrollBar::add-line:vertical:pressed, QScrollBar::sub-line:vertical:pressed {{ background: rgba(247,146,30,0.25); }}
    QScrollBar::up-arrow:vertical {{ image: url("{up_arrow_url}"); width: 12px; height: 12px; }}
    QScrollBar::down-arrow:vertical {{ image: url("{down_arrow_url}"); width: 12px; height: 12px; }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: {bg}; }}

    QScrollBar:horizontal {{ background: {bg}; height: 12px; margin: 0 16px 0 16px; border: none; }}
    QScrollBar::handle:horizontal {{ background: rgba(247,146,30,0.12); min-width: 24px; border-radius: 6px; border: 1px solid {PALETTE.ACCENT_HOVER}; }}
    QScrollBar::handle:horizontal:hover {{ background: rgba(247,146,30,0.15); border: 1px solid {PALETTE.ACCENT_HOVER}; }}
    QScrollBar::handle:horizontal:pressed {{ background: rgba(247,146,30,0.25); border: 1px solid {PALETTE.ACCENT_PRESSED}; }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ background: {bg}; width: 16px; subcontrol-origin: margin; border: none; border-radius: 0; image: none; }}
    QScrollBar::add-line:horizontal {{ subcontrol-position: right; border: none; }}
    QScrollBar::sub-line:horizontal {{ subcontrol-position: left; border: none; }}
    QScrollBar::add-line:horizontal:hover, QScrollBar::sub-line:horizontal:hover {{ background: rgba(247,146,30,0.15); }}
    QScrollBar::add-line:horizontal:pressed, QScrollBar::sub-line:horizontal:pressed {{ background: rgba(247,146,30,0.25); }}
    QScrollBar::left-arrow:horizontal {{ image: url("{left_arrow_url}"); width: 12px; height: 12px; }}
    QScrollBar::right-arrow:horizontal {{ image: url("{right_arrow_url}"); width: 12px; height: 12px; }}
    QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: {bg}; }}

    QToolTip {{
        background: {tip_bg};
        color: {tip_fg};
        border: 1px solid {PALETTE.ACCENT_HOVER};
        border-radius: 8px;
        padding: 6px 10px;
    }}

    /* Диалоги QMessageBox - унифицированный стиль кнопок */
    QMessageBox {{
        background: {bg};
    }}
    QMessageBox QLabel {{
        color: {fg};
        background: transparent;
    }}
    QMessageBox QPushButton {{
        background: {panel};
        color: {fg};
        border: 1px solid {border};
        border-radius: 14px;
        padding: 6px 12px;
        min-height: 24px;
        font-weight: 600;
    }}
    QMessageBox QPushButton:hover {{
        background: {dialog_soft};
        color: {button_hover_fg};
        border-color: {PALETTE.ACCENT_HOVER};
    }}
    QMessageBox QPushButton:pressed {{
        background: {dialog_pressed};
        color: {button_hover_fg};
        border-color: {PALETTE.ACCENT_PRESSED};
    }}
    QMessageBox QPushButton:disabled {{
        background: {bg};
        color: #9b9b9b;
        border-color: {border};
    }}

    """


def theme(
    app: QtWidgets.QApplication,
    dark: bool | str,
    icon_dir: str = "",
    persist: bool = True,
) -> None:
    is_dark = bool(dark)
    if isinstance(dark, str):
        is_dark = dark.strip().lower() == "dark"
    app.setProperty("nik_theme", "dark" if is_dark else "light")

    pal = app.palette()
    if is_dark:
        pal.setColor(QtGui.QPalette.Window, QtGui.QColor(PALETTE.BG_DARK))
        pal.setColor(QtGui.QPalette.WindowText, QtGui.QColor(PALETTE.FG_DARK))
        pal.setColor(QtGui.QPalette.Base, QtGui.QColor(PALETTE.BG_DARK))
        pal.setColor(QtGui.QPalette.Text, QtGui.QColor(PALETTE.FG_DARK))
        pal.setColor(QtGui.QPalette.Button, QtGui.QColor("#2a2a2a"))
        pal.setColor(QtGui.QPalette.ButtonText, QtGui.QColor(PALETTE.FG_DARK))
        pal.setColor(QtGui.QPalette.Highlight, QtGui.QColor(PALETTE.SELECTED))
        pal.setColor(QtGui.QPalette.HighlightedText, QtGui.QColor("#000000"))
    else:
        pal.setColor(QtGui.QPalette.Window, QtGui.QColor(PALETTE.BG_LIGHT))
        pal.setColor(QtGui.QPalette.WindowText, QtGui.QColor(PALETTE.FG_LIGHT))
        pal.setColor(QtGui.QPalette.Base, QtGui.QColor(PALETTE.BG_LIGHT))
        pal.setColor(QtGui.QPalette.Text, QtGui.QColor(PALETTE.FG_LIGHT))
        pal.setColor(QtGui.QPalette.Button, QtGui.QColor("#ffffff"))
        pal.setColor(QtGui.QPalette.ButtonText, QtGui.QColor(PALETTE.FG_LIGHT))
        pal.setColor(QtGui.QPalette.Highlight, QtGui.QColor(PALETTE.SELECTED))
        pal.setColor(QtGui.QPalette.HighlightedText, QtGui.QColor("#000000"))
    app.setPalette(pal)
    app.setStyleSheet(_build_qss(is_dark, icon_dir=icon_dir))

    if persist:
        _save_theme(is_dark)


def enable_theme_sync(app: QtWidgets.QApplication, icon_dir: str = "") -> None:
    theme(app, load_saved_theme(False), icon_dir=icon_dir, persist=False)


class ThemeToggle(QtWidgets.QWidget):
    """Larix Nexus-style animated theme toggle. checked=True means dark theme."""

    toggled = QtCore.Signal(bool)

    def __init__(self, parent=None, icon_dir: str = ""):
        super().__init__(parent)
        self._checked = False
        self._handle_progress = 0.0
        self._hovered = False
        self._pressed = False
        self._icon_cache: dict[tuple[str, int, float], QtGui.QPixmap] = {}
        self._icon_dir = icon_dir

        self._sun_source = self._load_icon("sun")
        self._moon_source = self._load_icon("moon")

        self._anim = QtCore.QPropertyAnimation(self, b"handleProgress", self)
        self._anim.setDuration(190)
        self._anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)

        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setFocusPolicy(QtCore.Qt.NoFocus)
        self.setAttribute(QtCore.Qt.WA_Hover, True)
        self.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        self.setFixedSize(66, 28)

    def _load_icon(self, name: str) -> QtGui.QPixmap:
        path = resolve_icon_path(name, self._icon_dir)
        pm = QtGui.QPixmap(path)
        return pm if not pm.isNull() else QtGui.QPixmap()

    def _scaled_icon(self, key: str, source: QtGui.QPixmap, size: int) -> QtGui.QPixmap:
        if source.isNull() or size <= 0:
            return QtGui.QPixmap()
        dpr = max(1.0, self.devicePixelRatioF())
        cache_key = (key, size, dpr)
        cached = self._icon_cache.get(cache_key)
        if cached is not None:
            return cached

        px = max(1, int(round(size * dpr)))
        scaled = source.scaled(px, px, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
        scaled.setDevicePixelRatio(dpr)
        self._icon_cache[cache_key] = scaled
        return scaled

    def sizeHint(self) -> QtCore.QSize:
        return QtCore.QSize(66, 28)

    def minimumSizeHint(self) -> QtCore.QSize:
        return QtCore.QSize(66, 28)

    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, checked: bool, animate: bool = True):
        checked = bool(checked)
        if self._checked == checked:
            return
        self._checked = checked
        target = 1.0 if checked else 0.0

        if animate and self.isVisible():
            self._anim.stop()
            self._anim.setStartValue(self._handle_progress)
            self._anim.setEndValue(target)
            self._anim.start()
        else:
            self._handle_progress = target
            self.update()

        self.toggled.emit(self._checked)

    checked = QtCore.Property(bool, isChecked, setChecked, notify=toggled)

    def _get_handle_progress(self) -> float:
        return self._handle_progress

    def _set_handle_progress(self, value: float) -> None:
        self._handle_progress = max(0.0, min(1.0, float(value)))
        self.update()

    handleProgress = QtCore.Property(float, _get_handle_progress, _set_handle_progress)

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == QtCore.Qt.LeftButton:
            self._pressed = True
            self.update()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == QtCore.Qt.LeftButton:
            was_pressed = self._pressed
            self._pressed = False
            if was_pressed and self.rect().contains(event.position().toPoint()):
                self.setChecked(not self._checked)
            self.update()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        if event.key() in (QtCore.Qt.Key_Space, QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
            self.setChecked(not self._checked)
            event.accept()
            return
        super().keyPressEvent(event)

    def enterEvent(self, event: QtCore.QEvent) -> None:
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event: QtCore.QEvent) -> None:
        self._hovered = False
        self._pressed = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        del event
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing, True)
        p.setRenderHint(QtGui.QPainter.SmoothPixmapTransform, True)

        track = QtCore.QRectF(self.rect().adjusted(1, 1, -1, -1))
        dark = bool(self._checked)
        radius = track.height() * 0.5

        if dark:
            bg_start = QtGui.QColor("#2b2b2d")
            bg_end = QtGui.QColor("#1d1d1f")
            border_col = QtGui.QColor(255, 255, 255, 28)
        else:
            bg_start = QtGui.QColor("#f2f2f2")
            bg_end = QtGui.QColor("#e7e7e7")
            border_col = QtGui.QColor(0, 0, 0, 24)

        grad = QtGui.QLinearGradient(track.topLeft(), track.bottomLeft())
        grad.setColorAt(0.0, bg_start)
        grad.setColorAt(1.0, bg_end)
        p.setPen(QtCore.Qt.NoPen)
        p.setBrush(grad)
        p.drawRoundedRect(track, radius, radius)

        p.setPen(QtGui.QPen(border_col, 1.0))
        p.setBrush(QtCore.Qt.NoBrush)
        p.drawRoundedRect(track, radius, radius)

        icon_size = int(track.height() * 0.48)
        center_y = track.center().y()
        pad_x = max(6.0, track.height() * 0.24)
        left_x = track.left() + pad_x
        right_x = track.right() - icon_size - pad_x

        sun_pm = QtGui.QPixmap()
        moon_pm = QtGui.QPixmap()

        if not self._sun_source.isNull():
            _sun = self._sun_source.scaled(icon_size, icon_size, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
            sun_pm = self._tint_pixmap(_sun, QtGui.QColor(0, 0, 0) if not dark else QtGui.QColor(255, 255, 255))

        if not self._moon_source.isNull():
            _moon = self._moon_source.scaled(icon_size, icon_size, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
            moon_pm = self._tint_pixmap(_moon, QtGui.QColor(0, 0, 0) if not dark else QtGui.QColor(255, 255, 255))

        hl_size = icon_size + 9
        hl_center_x = right_x + icon_size * 0.5 - (right_x - left_x) * self._handle_progress
        p.save()
        p.setPen(QtCore.Qt.NoPen)
        p.setBrush(QtGui.QColor("#F7921E"))
        p.drawEllipse(QtCore.QRectF(hl_center_x - hl_size * 0.5, center_y - hl_size * 0.5, hl_size, hl_size))
        p.restore()

        if not sun_pm.isNull():
            p.setOpacity(1.0 - 0.62 * self._handle_progress)
            p.drawPixmap(int(right_x), int(center_y - sun_pm.height() / 2), sun_pm)
        if not moon_pm.isNull():
            p.setOpacity(0.38 + 0.62 * self._handle_progress)
            p.drawPixmap(int(left_x), int(center_y - moon_pm.height() / 2), moon_pm)

        p.setOpacity(1.0)

    @staticmethod
    def _tint_pixmap(pm: QtGui.QPixmap, color: QtGui.QColor) -> QtGui.QPixmap:
        if pm.isNull():
            return pm
        tinted = QtGui.QPixmap(pm.size())
        tinted.fill(QtCore.Qt.transparent)
        painter = QtGui.QPainter(tinted)
        painter.drawPixmap(0, 0, pm)
        painter.setCompositionMode(QtGui.QPainter.CompositionMode_SourceIn)
        painter.fillRect(tinted.rect(), color)
        painter.end()
        return tinted


def set_back_to_menu_callback(callback) -> None:
    global _BACK_TO_MENU_CALLBACK
    _BACK_TO_MENU_CALLBACK = callback


def go_to_main_menu(window=None) -> None:
    if callable(_BACK_TO_MENU_CALLBACK):
        try:
            _BACK_TO_MENU_CALLBACK()
            return
        except Exception:
            pass
    try:
        if window is not None:
            window.close()
    except Exception:
        pass


def create_back_button(parent=None, size: int = 28, icon_dir: str = "") -> QtWidgets.QToolButton:
    b = QtWidgets.QToolButton(parent)
    b.setObjectName("btnBack")
    b.setFixedSize(size, size)
    b.setAutoRaise(False)
    app = QtWidgets.QApplication.instance()
    dark = is_dark_theme(app)
    p = resolve_icon_path("arrow_left", icon_dir, app=app, tint_in_dark=False)
    if not p:
        p = resolve_icon_path("back", icon_dir, app=app, tint_in_dark=False)
    if p:
        if dark:
            p = _ensure_white_copy(p, icon_dir)
        else:
            p = _ensure_black_copy(p, icon_dir)
    # btnBack is compact; remove generic button paddings so icon stays visible.
    b.setStyleSheet(
        "QToolButton#btnBack { padding: 0px; margin: 0px; border-radius: 14px; }"
        "QToolButton#btnBack:hover { padding: 0px; }"
        "QToolButton#btnBack:pressed { padding: 0px; }"
    )

    icon_px = max(16, size - 6)
    if p and os.path.exists(p):
        pm = QtGui.QPixmap(p)
        if not pm.isNull():
            img = pm.toImage()
            crop = QtGui.QRegion(QtGui.QBitmap.fromImage(img.createAlphaMask())).boundingRect()
            if crop.isValid() and crop.width() > 0 and crop.height() > 0:
                pm = pm.copy(crop)
            pm = pm.scaled(icon_px, icon_px, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
            b.setIcon(QtGui.QIcon(pm))
        else:
            b.setIcon(QtGui.QIcon(p))
    else:
        b.setIcon(QtGui.QIcon())
    b.setIconSize(QtCore.QSize(icon_px, icon_px))
    b.setToolTip("Назад")
    return b


def apply_dark_titlebar(window, dark: bool | None = None) -> None:
    if sys.platform != "win32":
        return
    try:
        if dark is None:
            dark = is_dark_theme(QtWidgets.QApplication.instance())
        dark = bool(dark)
        hwnd = int(window.winId())
        val = ctypes.c_int(1 if dark else 0)

        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(val), ctypes.sizeof(val))
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 19, ctypes.byref(val), ctypes.sizeof(val))

        def _to_colorref(hex_color: str) -> ctypes.c_uint:
            s = (hex_color or "").lstrip("#")
            if len(s) != 6:
                s = "1E1E1E" if dark else "F5F5F5"
            r = int(s[0:2], 16)
            g = int(s[2:4], 16)
            b = int(s[4:6], 16)
            return ctypes.c_uint((r) | (g << 8) | (b << 16))

        caption = _to_colorref("#1E1E1E" if dark else "#F5F5F5")
        text = _to_colorref("#FFFFFF" if dark else "#222222")
        border = _to_colorref("#1E1E1E" if dark else "#DCDCDC")
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 35, ctypes.byref(caption), ctypes.sizeof(caption))
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 36, ctypes.byref(text), ctypes.sizeof(text))
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 34, ctypes.byref(border), ctypes.sizeof(border))
    except Exception:
        pass


class _HoverTracker(QtCore.QObject):
    def __init__(self, view: QtWidgets.QAbstractItemView):
        super().__init__(view.viewport())
        self.view = view
        self._last_hover_row = -1

    def eventFilter(self, obj, ev):
        t = ev.type()
        if t == QtCore.QEvent.MouseMove:
            pos = ev.position().toPoint() if hasattr(ev, "position") else ev.pos()
            idx = self.view.indexAt(pos)
            new_row = idx.row() if idx.isValid() else -1
            if new_row != self._last_hover_row:
                self._last_hover_row = new_row
                self.view.setProperty("_hover_row", new_row)
                self.view.viewport().update()
        elif t in (QtCore.QEvent.Leave, QtCore.QEvent.HoverLeave):
            if self._last_hover_row != -1:
                self._last_hover_row = -1
                self.view.setProperty("_hover_row", -1)
                self.view.viewport().update()
        return False


class RowHoverDelegate(QtWidgets.QStyledItemDelegate):
    def paint(self, painter, option, index):
        opt = QtWidgets.QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        opt.state &= ~QtWidgets.QStyle.State_HasFocus
        
        view = option.widget
        hover_row = -1
        if isinstance(view, QtWidgets.QAbstractItemView):
            try:
                val = view.property("_hover_row")
                hover_row = int(val) if val is not None else -1
            except Exception:
                hover_row = -1
        
        is_selected = bool(opt.state & QtWidgets.QStyle.State_Selected)
        is_hovered = bool(hover_row >= 0 and index.row() == hover_row)
        
        opt.state &= ~QtWidgets.QStyle.State_Selected
        opt.state &= ~QtWidgets.QStyle.State_MouseOver
        
        if index.column() == 0 and isinstance(view, QtWidgets.QAbstractItemView):
            if is_hovered and not is_selected:
                painter.save()
                painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
                vp = view.viewport()
                margin_h = 4
                margin_v = 1
                row_rect = QtCore.QRectF(
                    float(margin_h),
                    float(option.rect.top()) + float(margin_v),
                    float(vp.width()) - float(margin_h * 2),
                    float(option.rect.height()) - float(margin_v * 2)
                )
                painter.setPen(QtCore.Qt.NoPen)
                painter.setBrush(QtGui.QColor(PALETTE.SOFT_HOVER))
                painter.drawRoundedRect(row_rect, 8.0, 8.0)
                painter.restore()
            
            if is_selected:
                painter.save()
                painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
                vp = view.viewport()
                margin_h = 4
                margin_v = 1
                row_rect = QtCore.QRectF(
                    float(margin_h),
                    float(option.rect.top()) + float(margin_v),
                    float(vp.width()) - float(margin_h * 2),
                    float(option.rect.height()) - float(margin_v * 2)
                )
                painter.setPen(QtCore.Qt.NoPen)
                painter.setBrush(QtGui.QColor(PALETTE.SELECTED))
                painter.drawRoundedRect(row_rect, 8.0, 8.0)
                painter.restore()
        
        if is_selected or is_hovered:
            pal = QtGui.QPalette(opt.palette)
            dark_text = QtGui.QColor("#000000")
            for role in (QtGui.QPalette.Text, QtGui.QPalette.WindowText, QtGui.QPalette.HighlightedText):
                pal.setColor(QtGui.QPalette.Active, role, dark_text)
                pal.setColor(QtGui.QPalette.Inactive, role, dark_text)
            opt.palette = pal
        
        style = opt.widget.style() if opt.widget is not None else QtWidgets.QApplication.style()
        style.drawControl(QtWidgets.QStyle.CE_ItemViewItem, opt, painter, opt.widget)


def install_viewport_row_highlighter(view: QtWidgets.QAbstractItemView) -> None:
    try:
        setup_hover_tracking(view)
    except Exception:
        pass


def setup_hover_tracking(view: QtWidgets.QAbstractItemView) -> None:
    try:
        view.setMouseTracking(True)
        vp = view.viewport()
        old = getattr(view, "_hover_tracker", None)
        if old is not None:
            vp.removeEventFilter(old)
        tracker = _HoverTracker(view)
        vp.installEventFilter(tracker)
        setattr(view, "_hover_tracker", tracker)
    except Exception:
        pass
