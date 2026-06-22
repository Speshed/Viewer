# -*- coding: utf-8 -*-
import sys
import os
import importlib
import importlib.util
import urllib.request
import urllib.error
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QGraphicsDropShadowEffect, QPushButton, QFileDialog, QMessageBox, QLineEdit, QStyle,
)
from PySide6.QtCore import Qt, Signal, Property, QPropertyAnimation, QEasingCurve, QTimer, QSize, QObject, QThread, Slot, QEvent
from PySide6.QtGui import QColor, QCursor, QPainter, QPixmap, QIcon, QImage

from shared.theme_toggle import (
    ThemeToggle, is_dark_theme, theme, resolve_icon_path,
    load_saved_theme, enable_theme_sync, set_back_to_menu_callback,
    apply_dark_titlebar,
)
from shared.dialogs import show_dialog, wire_message_box_buttons

if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ICON_DIR = os.path.join(BASE_DIR, "icon")
LOGO_LIGHT_REL = os.path.join("icon", "Manager-scaled.png")
LOGO_DARK_REL = os.path.join("icon", "Manager-scaled_white.png")
VIEWER_LOGO_LIGHT_REL = os.path.join("icon", "Larix Viewer_black.png")
VIEWER_LOGO_DARK_REL = os.path.join("icon", "Larix Viewer_white.png")
TITLEBAR_ICON_REL = os.path.join("icon", "logo.ico")
DEFAULT_API_BASE_URL = "http://localhost:5000"
_ACTIVE_API_CHECK_THREADS = set()


def _popup_error(parent, text: str, title: str = "Ошибка"):
    try:
        app = QApplication.instance()
        p = resolve_icon_path("error", ICON_DIR, app=app)
        pm = QPixmap(p) if p else QPixmap()
        msg = QMessageBox(parent)
        msg.setWindowTitle(title)
        msg.setText(text)
        if not pm.isNull():
            msg.setIconPixmap(pm.scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            msg.setIcon(QMessageBox.Critical)
        msg.setStandardButtons(QMessageBox.Ok)
        wire_message_box_buttons(msg)
        show_dialog(msg, modal=True)
    except Exception:
        try:
            QMessageBox.critical(parent, title, text)
        except Exception:
            pass


def _popup_info(parent, text: str, title: str = "Информация"):
    try:
        app = QApplication.instance()
        p = resolve_icon_path("alert", ICON_DIR, app=app)
        pm = QPixmap(p) if p else QPixmap()
        msg = QMessageBox(parent)
        msg.setWindowTitle(title)
        msg.setText(text)
        if not pm.isNull():
            msg.setIconPixmap(pm.scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            msg.setIcon(QMessageBox.Information)
        msg.setStandardButtons(QMessageBox.Ok)
        wire_message_box_buttons(msg)
        show_dialog(msg, modal=True)
    except Exception:
        try:
            QMessageBox.information(parent, title, text)
        except Exception:
            pass


def _load_symbol_from_dir(module_dir: str, module_name: str, symbol_name: str):
    mod_dir = os.path.join(BASE_DIR, module_dir)
    module_path = os.path.join(mod_dir, f"{module_name}.py")
    unique_name = f"_larix_{module_dir}_{module_name}"
    if mod_dir not in sys.path:
        sys.path.insert(0, mod_dir)
    if unique_name in sys.modules:
        del sys.modules[unique_name]
    spec = importlib.util.spec_from_file_location(unique_name, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot find module {module_name} in {mod_dir}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[unique_name] = module
    spec.loader.exec_module(module)
    return getattr(module, symbol_name)


def _extract_window_widget(window):
    if window is None:
        return None
    widget = None
    try:
        if hasattr(window, "takeCentralWidget"):
            widget = window.takeCentralWidget()
    except Exception:
        widget = None
    if widget is None:
        try:
            widget = window.centralWidget()
            if widget is not None:
                widget.setParent(None)
        except Exception:
            widget = None
    return widget


def _track_api_check_thread(thread: QThread) -> None:
    if thread is None:
        return
    _ACTIVE_API_CHECK_THREADS.add(thread)

    def _drop_ref() -> None:
        try:
            _ACTIVE_API_CHECK_THREADS.discard(thread)
        except Exception:
            pass

    try:
        thread.finished.connect(_drop_ref)
    except Exception:
        pass


def _shutdown_api_check_threads() -> None:
    for t in list(_ACTIVE_API_CHECK_THREADS):
        try:
            if t is not None and t.isRunning():
                t.quit()
                t.wait(3000)
        except Exception:
            pass
        try:
            _ACTIVE_API_CHECK_THREADS.discard(t)
        except Exception:
            pass


def _normalize_api_base_url(url: str) -> str:
    s = (url or "").strip()
    if not s:
        return DEFAULT_API_BASE_URL
    if "://" not in s:
        s = "http://" + s
    return s.rstrip("/")


def _check_api_connection(base_url: str, timeout_sec: float = 2.0) -> bool:
    test_urls = [
        f"{base_url}/api/project/projects",
        f"{base_url}/health",
        f"{base_url}/api/health",
    ]
    for u in test_urls:
        try:
            req = urllib.request.Request(u, method="GET")
            with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
                code = int(getattr(resp, "status", 0) or 0)
                if 200 <= code < 400:
                    return True
        except Exception:
            pass
    return False


class ApiCheckWorker(QObject):
    finished = Signal(int, str, bool)

    def __init__(self, seq: int, base_url: str):
        super().__init__()
        self._seq = int(seq)
        self._base_url = str(base_url or "")

    @Slot()
    def run(self):
        ok = _check_api_connection(self._base_url)
        self.finished.emit(self._seq, self._base_url, ok)


def get_logo_path(is_dark=False):
    rel = LOGO_DARK_REL if is_dark else LOGO_LIGHT_REL
    direct = os.path.join(BASE_DIR, rel)
    if os.path.exists(direct):
        return direct
    app = QApplication.instance()
    fallback_name = "logo_white" if is_dark else "logo"
    return resolve_icon_path(fallback_name, ICON_DIR, app=app, tint_in_dark=False) or ""


def get_viewer_logo_path(is_dark=False):
    rel = VIEWER_LOGO_DARK_REL if is_dark else VIEWER_LOGO_LIGHT_REL
    direct = os.path.join(BASE_DIR, rel)
    if os.path.exists(direct):
        return direct
    return ""


def _trim_transparent_pixmap(pm: QPixmap) -> QPixmap:
    if pm.isNull():
        return pm
    img = pm.toImage().convertToFormat(QImage.Format_ARGB32)
    w, h = img.width(), img.height()
    min_x, min_y = w, h
    max_x, max_y = -1, -1
    for y in range(h):
        for x in range(w):
            if img.pixelColor(x, y).alpha() > 0:
                if x < min_x:
                    min_x = x
                if y < min_y:
                    min_y = y
                if x > max_x:
                    max_x = x
                if y > max_y:
                    max_y = y
    if max_x < min_x or max_y < min_y:
        return pm
    return QPixmap.fromImage(img.copy(min_x, min_y, max_x - min_x + 1, max_y - min_y + 1))


def get_window_icon_path():
    direct = os.path.join(BASE_DIR, TITLEBAR_ICON_REL)
    if os.path.exists(direct):
        return direct
    app = QApplication.instance()
    return resolve_icon_path("app_icon", ICON_DIR, app=app, tint_in_dark=False) or ""


class AnimatableShadowEffect(QGraphicsDropShadowEffect):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._blur_radius = 0
        self._offset_y = 0
        self.setColor(QColor(0, 0, 0, 60))
        self.setBlurRadius(0)
        self.setOffset(0, 0)

    def getBlurRadiusAnim(self):
        return self._blur_radius

    def setBlurRadiusAnim(self, value):
        self._blur_radius = value
        self.setBlurRadius(value)

    def getOffsetY(self):
        return self._offset_y

    def setOffsetY(self, value):
        self._offset_y = value
        self.setOffset(0, int(value))

    animBlurRadius = Property(float, getBlurRadiusAnim, setBlurRadiusAnim)
    animOffsetY = Property(float, getOffsetY, setOffsetY)


class ModeCard(QFrame):
    clicked = Signal(str)

    def __init__(self, mode_id, title, description, is_dark=False, parent=None, icon_name=None):
        super().__init__(parent)
        self.mode_id = mode_id
        self._title_text = title
        self._desc_text = description
        self._is_dark = is_dark
        self._icon_name = icon_name
        self._icon_cache = {}
        self._hovered = False
        self._selected = False

        self.setMinimumHeight(140)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setFixedHeight(156)

        self._shadow = AnimatableShadowEffect(self)
        self.setGraphicsEffect(self._shadow)

        self._blur_anim = QPropertyAnimation(self._shadow, b"animBlurRadius", self)
        self._blur_anim.setDuration(180)
        self._blur_anim.setEasingCurve(QEasingCurve.OutCubic)

        self._offset_anim = QPropertyAnimation(self._shadow, b"animOffsetY", self)
        self._offset_anim.setDuration(180)
        self._offset_anim.setEasingCurve(QEasingCurve.OutCubic)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        self._icon_label = QLabel()
        self._icon_label.setAlignment(Qt.AlignCenter)
        self._icon_label.setFixedHeight(54)
        layout.addWidget(self._icon_label, 0, Qt.AlignCenter)

        self._title_label = QLabel(title)
        self._title_label.setAlignment(Qt.AlignCenter)
        self._title_label.setStyleSheet("font-size: 10pt; font-weight: 600;")
        layout.addWidget(self._title_label)

        QTimer.singleShot(0, self._update_style)

    def set_selected(self, selected):
        self._selected = selected
        self._update_style()

    def is_selected(self):
        return self._selected

    def _update_style(self):
        if self._is_dark:
            if self._selected:
                bg, border, title_color = "#3a2b1a", "#E07E12", "#ffd6a6"
            elif self._hovered:
                bg, border, title_color = "#2f2620", "#FFA74B", "#ffc989"
            else:
                bg, border, title_color = "#1e1e1e", "#404040", "#e0e0e0"
        else:
            if self._selected:
                bg, border, title_color = "#FFC37A", "#E07E12", "#000000"
            elif self._hovered:
                bg, border, title_color = "#FFE3C2", "#FFA74B", "#000000"
            else:
                bg, border, title_color = "#ffffff", "#e0e0e0", "#222222"

        self.setStyleSheet(f"ModeCard {{ background-color: {bg}; border: 2px solid {border}; border-radius: 12px; }}")
        self._title_label.setStyleSheet(f"font-size: 11pt; font-weight: 600; color: {title_color}; background: transparent;")
        self._icon_label.setStyleSheet("background-color: transparent; border: none;")
        self._update_icon()

    def _update_icon(self):
        if not self._icon_name:
            self._icon_label.setPixmap(QPixmap())
            self._icon_label.setVisible(False)
            return
        icon_source = self._icon_name
        if not os.path.isabs(icon_source):
            icon_source = os.path.join(ICON_DIR, icon_source)
        app = QApplication.instance()
        icon_path = resolve_icon_path(icon_source, ICON_DIR, app=app, tint_in_dark=False)
        if icon_path and os.path.exists(icon_path):
            cache_key = (icon_path, bool(self._is_dark))
            pix = self._icon_cache.get(cache_key)
            if pix is None:
                pix = self._prepare_icon_pixmap(icon_path)
                self._icon_cache[cache_key] = pix
            if not pix.isNull():
                self._icon_label.setPixmap(pix.scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                self._icon_label.setVisible(True)
                return
        self._icon_label.setPixmap(QPixmap())
        self._icon_label.setVisible(False)

    def _prepare_icon_pixmap(self, icon_path: str) -> QPixmap:
        pm = QPixmap(icon_path)
        if pm.isNull():
            return QPixmap()
        original_pm = pm
        img = pm.toImage().convertToFormat(QImage.Format_ARGB32)
        width, height = img.width(), img.height()
        dark = bool(self._is_dark)
        icon_base = os.path.basename(icon_path).strip().lower()
        preserve_shape_icons = {"parameters.png", "status.png", "sync.png"}
        preserve_shape = icon_base in preserve_shape_icons
        if not preserve_shape:
            self._erase_border_connected_background(img)
        for y in range(height):
            for x in range(width):
                c = img.pixelColor(x, y)
                if c.alpha() == 0:
                    continue
                r, g, b = c.red(), c.green(), c.blue()
                maxc = max(r, g, b)
                minc = min(r, g, b)
                is_light_bg = (maxc >= 242 and (maxc - minc) <= 18)
                if (not preserve_shape) and is_light_bg:
                    c.setAlpha(0)
                    img.setPixelColor(x, y, c)
                    continue
                if dark:
                    img.setPixelColor(x, y, QColor(255, 255, 255, c.alpha()))
        if not preserve_shape:
            img = self._trim_transparent_bounds(img)
        out = QPixmap.fromImage(img)
        if out.isNull():
            return original_pm
        out_img = out.toImage().convertToFormat(QImage.Format_ARGB32)
        opaque = 0
        for y in range(out_img.height()):
            for x in range(out_img.width()):
                if out_img.pixelColor(x, y).alpha() > 0:
                    opaque += 1
        if opaque == 0:
            return original_pm
        return out

    def _erase_border_connected_background(self, img: QImage) -> None:
        width, height = img.width(), img.height()
        if width <= 0 or height <= 0:
            return
        from collections import deque
        visited = set()

        def color_distance(c1: QColor, c2: QColor) -> int:
            return abs(c1.red() - c2.red()) + abs(c1.green() - c2.green()) + abs(c1.blue() - c2.blue())

        seeds = []
        for x in range(width):
            seeds.append((x, 0))
            seeds.append((x, height - 1))
        for y in range(height):
            seeds.append((0, y))
            seeds.append((width - 1, y))

        threshold = 28
        for sx, sy in seeds:
            if (sx, sy) in visited:
                continue
            seed_color = img.pixelColor(sx, sy)
            if seed_color.alpha() == 0:
                visited.add((sx, sy))
                continue
            sr, sg, sb = seed_color.red(), seed_color.green(), seed_color.blue()
            smax, smin = max(sr, sg, sb), min(sr, sg, sb)
            is_seed_white = (smax >= 242 and (smax - smin) <= 16)
            is_seed_black = (smax <= 28 and (smax - smin) <= 16)
            if not (is_seed_white or is_seed_black):
                visited.add((sx, sy))
                continue
            q = deque()
            q.append((sx, sy))
            while q:
                x, y = q.popleft()
                if (x, y) in visited:
                    continue
                visited.add((x, y))
                cur = img.pixelColor(x, y)
                if cur.alpha() == 0:
                    continue
                if color_distance(cur, seed_color) > threshold:
                    continue
                cur.setAlpha(0)
                img.setPixelColor(x, y, cur)
                if x > 0:
                    q.append((x - 1, y))
                if x + 1 < width:
                    q.append((x + 1, y))
                if y > 0:
                    q.append((x, y - 1))
                if y + 1 < height:
                    q.append((x, y + 1))

    def _trim_transparent_bounds(self, img: QImage) -> QImage:
        w, h = img.width(), img.height()
        if w <= 0 or h <= 0:
            return img
        min_x, min_y = w, h
        max_x, max_y = -1, -1
        for y in range(h):
            for x in range(w):
                if img.pixelColor(x, y).alpha() > 0:
                    if x < min_x: min_x = x
                    if y < min_y: min_y = y
                    if x > max_x: max_x = x
                    if y > max_y: max_y = y
        if max_x < min_x or max_y < min_y:
            return img
        return img.copy(min_x, min_y, max_x - min_x + 1, max_y - min_y + 1)

    def _animate_to(self, hover_in):
        if hover_in:
            self._blur_anim.setStartValue(self._shadow.getBlurRadiusAnim())
            self._blur_anim.setEndValue(25)
            self._offset_anim.setStartValue(self._shadow.getOffsetY())
            self._offset_anim.setEndValue(8)
        else:
            self._blur_anim.setStartValue(self._shadow.getBlurRadiusAnim())
            self._blur_anim.setEndValue(0)
            self._offset_anim.setStartValue(self._shadow.getOffsetY())
            self._offset_anim.setEndValue(0)
        self._blur_anim.start()
        self._offset_anim.start()

    def enterEvent(self, event):
        self._hovered = True
        self._update_style()
        self._animate_to(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self._update_style()
        self._animate_to(False)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.mode_id)
        super().mousePressEvent(event)


class AppMenuWidget(QWidget):
    mode_selected = Signal(str)
    api_base_changed = Signal(str)

    def __init__(self, *, is_dark=False, api_base_url=DEFAULT_API_BASE_URL,
                 cards_data=None, logo_func=None, logo_height=64,
                 app_version="1.0.0", app_version_date="",
                 app_version_changes=None,
                 show_template_download=False, parent=None):
        super().__init__(parent)
        self._is_dark = is_dark
        self._api_base_url = _normalize_api_base_url(api_base_url)
        self._api_is_connected = False
        self._api_check_seq = 0
        self._api_check_silent = True
        self._api_check_thread = None
        self._api_check_worker = None
        self._api_check_busy = False
        self._api_check_timeout = QTimer(self)
        self._api_check_timeout.setSingleShot(True)
        self._api_check_timeout.timeout.connect(self._on_api_check_timeout)
        self._cards_data = cards_data or []
        self._logo_func = logo_func or get_logo_path
        self._logo_height = logo_height
        self._app_version = app_version
        self._app_version_date = app_version_date
        self._app_version_changes = app_version_changes or []
        self._show_template_download = show_template_download
        self._cards = []
        self._setup_ui()
        QTimer.singleShot(0, self._connect_current_api_silent)

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(16)

        toggle_row = QHBoxLayout()
        toggle_row.addStretch(1)
        self.theme_toggle = ThemeToggle()
        self.theme_toggle.setChecked(bool(self._is_dark), animate=False)
        self.theme_toggle.toggled.connect(self._on_theme_toggled)
        toggle_row.addWidget(self.theme_toggle, 0, Qt.AlignRight)
        main_layout.addLayout(toggle_row)

        self._logo_label = QLabel()
        self._logo_label.setAlignment(Qt.AlignCenter)
        self._update_logo()
        main_layout.addWidget(self._logo_label)

        title_label = QLabel("Выберите режим работы")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 14pt; font-weight: 600;")
        main_layout.addWidget(title_label)

        cards_row = QHBoxLayout()
        cards_row.setSpacing(22)
        cards_row.addStretch(1)
        for item in self._cards_data:
            mode_id, title, desc = item[:3]
            icon_name = item[3] if len(item) > 3 else None
            card = ModeCard(mode_id, title, desc, self._is_dark, self, icon_name=icon_name)
            card.setFixedSize(168, 156)
            card.clicked.connect(self._on_card_clicked)
            self._cards.append(card)
            cards_row.addWidget(card)
        cards_row.addStretch(1)
        main_layout.addLayout(cards_row)
        main_layout.addStretch(1)

        if self._show_template_download:
            self._download_template_link = QLabel("<a href='download'>Скачать шаблон Excel</a>")
            self._download_template_link.setTextFormat(Qt.RichText)
            self._download_template_link.setTextInteractionFlags(Qt.TextBrowserInteraction)
            self._download_template_link.setOpenExternalLinks(False)
            self._download_template_link.setCursor(QCursor(Qt.PointingHandCursor))
            self._download_template_link.linkActivated.connect(lambda _link: self._download_template())
            main_layout.addWidget(self._download_template_link, 0, Qt.AlignCenter)
            self._update_template_link_style()

        api_row = QHBoxLayout()
        api_row.addStretch(1)
        api_row.addWidget(QLabel("Сервер API:"))
        self.api_base_edit = QLineEdit(self._api_base_url)
        self.api_base_edit.setFixedWidth(260)
        self.api_base_edit.setClearButtonEnabled(False)
        self.api_base_edit.setPlaceholderText(DEFAULT_API_BASE_URL)
        self.api_base_edit.textChanged.connect(self._on_api_base_text_changed)
        self.api_base_edit.editingFinished.connect(self._on_api_base_edited)
        self._api_status_icon = QLabel(self.api_base_edit)
        self._api_status_icon.setFixedSize(16, 16)
        self._api_status_icon.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.api_base_edit.installEventFilter(self)
        api_row.addWidget(self.api_base_edit)

        self.btn_api_connect = QPushButton("Подключить")
        self.btn_api_connect.clicked.connect(self._on_api_connect_clicked)
        self.btn_api_connect.setProperty("secondary", True)
        api_row.addWidget(self.btn_api_connect)
        self._set_connect_button_icon()
        self._set_api_status_icon(False)
        api_row.addStretch(1)
        main_layout.addLayout(api_row)

        version_row = QHBoxLayout()
        version_row.setContentsMargins(0, 0, 0, 0)
        version_row.addStretch(1)
        self._version_link = QLabel(f"<a href='version'>Версия {self._app_version}</a>")
        self._version_link.setTextFormat(Qt.RichText)
        self._version_link.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self._version_link.setOpenExternalLinks(False)
        self._version_link.setCursor(QCursor(Qt.PointingHandCursor))
        self._version_link.linkActivated.connect(lambda _link: self._download_version_info())
        version_row.addWidget(self._version_link, 0, Qt.AlignRight | Qt.AlignBottom)
        main_layout.addLayout(version_row)
        self._update_version_link_style()

    def _on_api_base_edited(self):
        value = _normalize_api_base_url(self.api_base_edit.text())
        self._api_base_url = value
        self.api_base_edit.setText(value)

    def _set_api_status_icon(self, connected: bool):
        self._api_is_connected = bool(connected)
        app = QApplication.instance()
        key = "ok" if connected else "none"
        path = resolve_icon_path(key, ICON_DIR, app=app)
        tip = (
            "Подключено к API"
            if connected
            else "Нет подключения к API. Измените адрес и нажмите 'Подключить'."
        )
        if path and os.path.exists(path):
            icon = QIcon(path)
        else:
            std = QStyle.SP_DialogApplyButton if connected else QStyle.SP_DialogCancelButton
            icon = self.style().standardIcon(std)
        pm = icon.pixmap(16, 16)
        self._api_status_icon.setPixmap(pm)
        self._api_status_icon.setToolTip(tip)
        self._api_status_icon.setStatusTip(tip)
        self._position_api_status_icon()

    def _position_api_status_icon(self):
        e = self.api_base_edit
        x = max(0, e.width() - 16 - 8)
        y = max(0, (e.height() - 16) // 2)
        self._api_status_icon.move(x, y)
        self._api_status_icon.raise_()

    def eventFilter(self, obj, event):
        try:
            if obj is getattr(self, "api_base_edit", None) and event is not None:
                t = event.type()
                if t in (QEvent.Resize, QEvent.Move, QEvent.Show):
                    self._position_api_status_icon()
        except Exception:
            pass
        return super().eventFilter(obj, event)

    def _set_connect_button_icon(self):
        app = QApplication.instance()
        icon_path = resolve_icon_path("login", ICON_DIR, app=app)
        if icon_path and os.path.exists(icon_path):
            self.btn_api_connect.setIcon(QIcon(icon_path))
            self.btn_api_connect.setIconSize(QSize(16, 16))

    def _on_api_base_text_changed(self, _text: str):
        self._set_api_status_icon(False)

    def _set_connect_ui_busy(self, busy: bool):
        try:
            self._api_check_busy = bool(busy)
            self.btn_api_connect.setEnabled(not busy)
            self.btn_api_connect.setText("Проверка..." if busy else "Подключить")
            if not busy:
                self._set_connect_button_icon()
        except Exception:
            pass

    def _start_api_check(self, silent: bool):
        value = _normalize_api_base_url(self.api_base_edit.text())
        self._api_base_url = value
        self.api_base_edit.setText(value)
        self._api_check_seq += 1
        seq = self._api_check_seq
        self._api_check_silent = bool(silent)
        self._set_connect_ui_busy(True)
        self._api_check_timeout.start(9000)
        thread = QThread()
        worker = ApiCheckWorker(seq, value)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._on_api_check_finished)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._on_api_check_thread_finished)
        self._api_check_worker = worker
        self._api_check_thread = thread
        _track_api_check_thread(thread)
        thread.start()

    def _on_api_check_finished(self, seq: int, value: str, ok: bool):
        if seq != self._api_check_seq:
            return
        self._api_check_timeout.stop()
        self._set_connect_ui_busy(False)
        self._set_api_status_icon(ok)
        self._api_check_worker = None
        self._api_check_thread = None
        if ok:
            self.api_base_changed.emit(value)
        elif not self._api_check_silent:
            QMessageBox.warning(self, "Сервер API", f"Не удалось подключиться к {value}")

    def _on_api_check_timeout(self):
        if not self._api_check_busy:
            return
        self._set_connect_ui_busy(False)
        self._set_api_status_icon(False)
        t = self._api_check_thread
        if t is not None:
            try:
                if t.isRunning():
                    t.quit()
                    t.wait(1000)
            except Exception:
                pass
        self._api_check_worker = None
        self._api_check_thread = None

    def _on_api_check_thread_finished(self):
        if self._api_check_busy:
            self._api_check_timeout.stop()
            self._set_connect_ui_busy(False)

    def _connect_current_api_silent(self):
        self._start_api_check(silent=True)

    def _on_api_connect_clicked(self):
        self._start_api_check(silent=False)

    def _on_theme_toggled(self, checked: bool) -> None:
        self._is_dark = bool(checked)
        self._apply_theme()

    def _apply_theme(self):
        try:
            app = QApplication.instance()
            if app is not None:
                theme(app, bool(self._is_dark), icon_dir=ICON_DIR)
        except Exception:
            pass
        for card in self._cards:
            try:
                card._is_dark = bool(self._is_dark)
                card._update_style()
            except Exception:
                pass
        self._update_logo()
        if self._show_template_download:
            self._update_template_link_style()
        self._update_version_link_style()
        try:
            self._set_connect_button_icon()
            self._set_api_status_icon(self._api_is_connected)
        except Exception:
            pass

    def _update_template_link_style(self):
        color = "#e0e0e0" if self._is_dark else "#303030"
        self._download_template_link.setStyleSheet("QLabel { font-size: 11pt; background: transparent; }")
        self._download_template_link.setText(
            f"<a href='download' style='color: {color}; text-decoration: underline;'>Скачать шаблон Excel</a>"
        )

    def _update_version_link_style(self):
        color = "#a8a8a8" if self._is_dark else "#606060"
        self._version_link.setStyleSheet("QLabel { font-size: 8pt; background: transparent; }")
        self._version_link.setText(
            f"<a href='version' style='color: {color}; text-decoration: none;'>Версия {self._app_version}</a>"
        )

    def _update_logo(self):
        logo_path = self._logo_func(self._is_dark)
        if os.path.exists(logo_path):
            pix = QPixmap(logo_path)
            pix = _trim_transparent_pixmap(pix)
            self._logo_label.setStyleSheet("")
            self._logo_label.setText("")
            self._logo_label.setPixmap(pix.scaledToHeight(self._logo_height, Qt.SmoothTransformation))
        else:
            self._logo_label.setPixmap(QPixmap())
            self._logo_label.setText("Larix")
            self._logo_label.setStyleSheet("font-size: 18pt; font-weight: bold;")

    def _on_card_clicked(self, mode_id):
        for card in self._cards:
            card.set_selected(card.mode_id == mode_id)
        QTimer.singleShot(150, lambda: self.mode_selected.emit(mode_id))

    def _download_template(self):
        try:
            from shared.excel_template import export_common_excel
        except Exception as e:
            _popup_error(self, f"Не удалось загрузить модуль шаблонов:\n{e}")
            return
        fn, _ = QFileDialog.getSaveFileName(
            self, "Скачать шаблон Excel", "Шаблон Excel.xlsx", "Excel (*.xlsx)",
        )
        if not fn:
            return
        if not fn.lower().endswith(".xlsx"):
            fn += ".xlsx"
        try:
            export_common_excel("", fn)
            _popup_info(self, f"Шаблон Excel сохранён:\n{fn}", "Готово")
        except Exception as e:
            _popup_error(self, str(e))

    def _build_version_info_text(self) -> str:
        lines = [f"Версия {self._app_version} от {self._app_version_date}"]
        lines.extend(f"- {item}" for item in self._app_version_changes)
        return "\n".join(lines) + "\n"

    def _download_version_info(self):
        default_name = f"Версия {self._app_version}.txt"
        fn, _ = QFileDialog.getSaveFileName(
            self, "Сохранить описание обновления", default_name, "Текстовые файлы (*.txt)",
        )
        if not fn:
            return
        if not fn.lower().endswith(".txt"):
            fn += ".txt"
        try:
            with open(fn, "w", encoding="utf-8") as f:
                f.write(self._build_version_info_text())
            _popup_info(self, f"Описание обновления сохранено:\n{fn}", "Готово")
        except Exception as e:
            _popup_error(self, f"Не удалось сохранить описание обновления:\n{e}")


class AppMainWindow(QMainWindow):
    def __init__(self, *, app_title="Larix",
                 cards_data=None, logo_func=None, logo_height=64,
                 module_loaders=None, bim_sync=False,
                 show_template_download=False,
                 app_version="1.0.0", app_version_date="",
                 app_version_changes=None,
                 skip_menu=False):
        super().__init__()
        self._app_title = app_title
        self._cards_data = cards_data or []
        self._logo_func = logo_func or get_logo_path
        self._logo_height = logo_height
        self._module_loaders = module_loaders or {}
        self._bim_sync = bim_sync
        self._show_template_download = show_template_download
        self._app_version = app_version
        self._app_version_date = app_version_date
        self._app_version_changes = app_version_changes or []
        self._skip_menu = bool(skip_menu)
        self._is_dark = load_saved_theme(False)
        self._api_base_url = _normalize_api_base_url(
            os.environ.get("LARIX_API_BASE_URL", DEFAULT_API_BASE_URL)
        )
        os.environ["LARIX_API_BASE_URL"] = self._api_base_url
        self._current_module_window = None
        self._current_module_widget = None

        try:
            app = QApplication.instance()
            theme(app, self._is_dark, icon_dir=ICON_DIR)
            icon_path = get_window_icon_path()
            if icon_path:
                app.setWindowIcon(QIcon(icon_path))
                self.setWindowIcon(QIcon(icon_path))
            apply_dark_titlebar(self, self._is_dark)
        except Exception:
            pass

        if not self._skip_menu:
            set_back_to_menu_callback(self._show_main_menu)

        if self._skip_menu and self._cards_data:
            first_mode = self._cards_data[0][0]
            QTimer.singleShot(0, lambda: self._on_mode_selected(first_mode))
        else:
            self._show_main_menu()

    def _center_on_screen(self):
        try:
            screen = self.windowHandle().screen() if self.windowHandle() else QApplication.primaryScreen()
            if screen is None:
                return
            geo = screen.availableGeometry()
            frm = self.frameGeometry()
            frm.moveCenter(geo.center())
            self.move(frm.topLeft())
        except Exception:
            pass

    def _show_main_menu(self):
        if self._current_module_widget is not None:
            self._current_module_widget = None
        self._current_module_window = None
        self.setWindowTitle(self._app_title)

        menu = AppMenuWidget(
            is_dark=self._is_dark,
            api_base_url=self._api_base_url,
            cards_data=self._cards_data,
            logo_func=self._logo_func,
            logo_height=self._logo_height,
            app_version=self._app_version,
            app_version_date=self._app_version_date,
            app_version_changes=self._app_version_changes,
            show_template_download=self._show_template_download,
            parent=self,
        )
        menu.mode_selected.connect(self._on_mode_selected)
        menu.api_base_changed.connect(self._on_api_base_changed)
        if hasattr(menu, 'theme_toggle'):
            menu.theme_toggle.toggled.connect(self._on_theme_toggled)
        self.setCentralWidget(menu)
        self._menu_widget = menu
        self.setMinimumSize(860, 640)
        self.resize(920, 700)
        self._center_on_screen()

    def _on_theme_toggled(self, dark: bool):
        self._is_dark = dark
        app = QApplication.instance()
        if app:
            theme(app, dark, icon_dir=ICON_DIR)
        try:
            apply_dark_titlebar(self, dark)
        except Exception:
            pass

    def _on_api_base_changed(self, value: str):
        self._api_base_url = _normalize_api_base_url(value)
        os.environ["LARIX_API_BASE_URL"] = self._api_base_url

    def _on_mode_selected(self, mode_id: str):
        if mode_id == "bim_sync" and self._bim_sync:
            self._open_bim_sync_dialog()
            return
        self._load_module(mode_id)

    def _load_module(self, mode_id: str):
        loader = self._module_loaders.get(mode_id)
        if not loader:
            _popup_error(self, f"Неизвестный модуль: {mode_id}")
            return
        try:
            mod_dir, mod_file, symbol, is_window = loader
            Klass = _load_symbol_from_dir(mod_dir, mod_file, symbol)
            if is_window:
                win = Klass()
                widget = _extract_window_widget(win)
                if widget is None:
                    _popup_error(self, f"Не удалось загрузить модуль {mode_id}")
                    return
                self._current_module_window = win
            else:
                widget = Klass()
                self._current_module_window = None
        except Exception as e:
            _popup_error(self, f"Не удалось загрузить модуль {mode_id}:\n{e}")
            return

        self._current_module_widget = widget
        self.setCentralWidget(widget)

        module_titles = {}
        for mid, (md, mf, ms, _) in self._module_loaders.items():
            module_titles[mid] = f"Larix — {mid.replace('_', ' ').title()}"
        module_titles["bim_sync"] = "Larix — Элементы"
        title = module_titles.get(mode_id, self._app_title)
        try:
            win = self._current_module_window
            if win is not None:
                wt = (win.windowTitle() or "").strip()
                if wt:
                    title = wt
        except Exception:
            pass
        self.setWindowTitle(title)

        target_w, target_h = 1120, 760
        min_w, min_h = 900, 620
        try:
            win = self._current_module_window
            if win is not None:
                ws = win.size()
                if ws.width() > 0 and ws.height() > 0:
                    target_w = ws.width()
                    target_h = ws.height()
                ms = win.minimumSize()
                if ms.width() > 0 and ms.height() > 0:
                    min_w = ms.width()
                    min_h = ms.height()
        except Exception:
            pass
        self.setMinimumSize(max(760, min_w), max(560, min_h))
        self.resize(max(900, target_w), max(620, target_h))
        self._center_on_screen()

    def _open_bim_sync_dialog(self):
        try:
            ModeSelectWidget = _load_symbol_from_dir("Sync", "ui", "ModeSelectWidget")
            widget = ModeSelectWidget(is_dark=self._is_dark, parent=self)
            widget.mode_selected.connect(self._on_bim_sync_mode_selected)
            widget.back_requested.connect(self._show_main_menu)

            self._current_module_widget = widget
            self._current_module_window = None
            self.setCentralWidget(widget)
            self.setWindowTitle("Larix — Элементы")
            self.setMinimumSize(600, 400)
            self.resize(700, 500)
            self._center_on_screen()
        except Exception as e:
            _popup_error(self, f"Не удалось открыть Элементы:\n{e}")

    def _on_bim_sync_mode_selected(self, mode_id):
        try:
            mode_id = str(mode_id or "").strip().lower()
            if not mode_id:
                return

            self._is_dark = bool(getattr(self._current_module_widget, "is_dark", self._is_dark))

            if mode_id == "powerbi":
                WindowClass = _load_symbol_from_dir("Sync", "ui", "PowerBiExportWindow")
                win = WindowClass("csv")
            elif mode_id == "parquet":
                WindowClass = _load_symbol_from_dir("Sync", "ui", "PowerBiExportWindow")
                win = WindowClass("parquet")
            elif mode_id == "sqlite":
                WindowClass = _load_symbol_from_dir("Sync", "ui", "PowerBiExportWindow")
                win = WindowClass("sqlite")
            else:
                WindowClass = _load_symbol_from_dir("Sync", "ui", "BimSyncWindow")
                win = WindowClass()

            if self._is_dark and hasattr(win, "_toggle_theme"):
                win._toggle_theme(True)
                if hasattr(win, "theme_toggle"):
                    win.theme_toggle.setChecked(True)

            if hasattr(win, "back_requested"):
                win.back_requested.connect(self._on_bim_sync_back)

            widget = win.takeCentralWidget() if hasattr(win, "takeCentralWidget") else None
            if widget is None:
                widget = win.centralWidget()
            if widget is None:
                _popup_error(self, "Не удалось загрузить интерфейс Элементы.")
                return

            self._current_module_widget = widget
            self._current_module_window = win
            self.setCentralWidget(widget)
            self.setWindowTitle((win.windowTitle() or "Larix — Элементы").strip())
            try:
                self.setMinimumSize(win.minimumSize())
                self.resize(win.size())
            except Exception:
                pass
            self._center_on_screen()
        except Exception as e:
            _popup_error(self, f"Не удалось загрузить режим Элементы:\n{e}")

    def _on_bim_sync_back(self):
        self._open_bim_sync_dialog()
