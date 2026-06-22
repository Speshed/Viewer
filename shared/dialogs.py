from __future__ import annotations

import os
import tempfile
from typing import Callable
import sys

_DIALOG_DEBUG = True

def _dialog_log(msg: str):
    if _DIALOG_DEBUG:
        print(f"[DIALOG] {msg}", file=sys.stderr, flush=True)

try:
    from PySide6 import QtCore, QtWidgets, QtGui
except Exception:
    from PyQt5 import QtCore, QtWidgets, QtGui  # type: ignore


_OPEN_DIALOG_REFS: set[QtWidgets.QDialog] = set()

_DEFAULT_ICON_DIR = os.path.join(
    getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "icon"
)
_CACHE_SUBDIR = "larix_dialog_icons"

_APP_ICON_PATH = None
_APP_ICON_CACHE = None


def set_app_icon_path(path: str) -> None:
    global _APP_ICON_PATH, _APP_ICON_CACHE
    _APP_ICON_PATH = path
    _APP_ICON_CACHE = None


def get_app_icon_path() -> str:
    global _APP_ICON_PATH
    if _APP_ICON_PATH and os.path.exists(_APP_ICON_PATH):
        return _APP_ICON_PATH
    candidates = [
        os.path.join(_DEFAULT_ICON_DIR, "logo.ico"),
        os.path.join(_DEFAULT_ICON_DIR, "logo.png"),
        os.path.join(_DEFAULT_ICON_DIR, "Manager-scaled.png"),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return ""


def get_app_icon() -> QtGui.QIcon:
    global _APP_ICON_CACHE
    if _APP_ICON_CACHE is not None:
        return _APP_ICON_CACHE
    path = get_app_icon_path()
    if path:
        _APP_ICON_CACHE = QtGui.QIcon(path)
        return _APP_ICON_CACHE
    return QtGui.QIcon()


def apply_dialog_icon(dialog: QtWidgets.QWidget) -> None:
    icon = get_app_icon()
    if not icon.isNull():
        dialog.setWindowIcon(icon)


def _is_dark_theme() -> bool:
    try:
        app = QtWidgets.QApplication.instance()
        if app is None:
            return False
        palette = app.palette()
        bg = palette.color(QtGui.QPalette.ColorRole.Window)
        return bg.lightness() < 128
    except Exception:
        return False


def _tint_pixmap_white(pm: QtGui.QPixmap) -> QtGui.QPixmap:
    if pm.isNull():
        return pm
    tinted = QtGui.QPixmap(pm.size())
    tinted.fill(QtCore.Qt.GlobalColor.transparent)
    p = QtGui.QPainter(tinted)
    p.setCompositionMode(QtGui.QPainter.CompositionMode.CompositionMode_Source)
    p.drawPixmap(0, 0, pm)
    p.setCompositionMode(QtGui.QPainter.CompositionMode.CompositionMode_SourceIn)
    p.fillRect(tinted.rect(), QtGui.QColor(QtCore.Qt.GlobalColor.white))
    p.end()
    return tinted


def _get_white_icon_path(src_path: str) -> str:
    if not src_path or not os.path.exists(src_path):
        return src_path
    cache_dir = os.path.join(tempfile.gettempdir(), _CACHE_SUBDIR)
    os.makedirs(cache_dir, exist_ok=True)
    name, ext = os.path.splitext(os.path.basename(src_path))
    dst = os.path.join(cache_dir, f"{name}_white{ext}")
    if os.path.exists(dst):
        return dst
    pm = QtGui.QPixmap(src_path)
    if pm.isNull():
        return src_path
    white_pm = _tint_pixmap_white(pm)
    white_pm.save(dst, "PNG")
    return dst


def _resolve_dialog_icon(name: str) -> str:
    candidates = {
        "error": ["error.png"],
        "warning": ["warning.png"],
        "alert": ["alert.png"],
    }
    names = candidates.get(name, [])
    for n in names:
        p = os.path.join(_DEFAULT_ICON_DIR, n)
        if os.path.exists(p):
            if _is_dark_theme() and name != "warning":
                return _get_white_icon_path(p)
            return p
    return ""


def _show_message_box(
    parent,
    text: str,
    title: str,
    icon_name: str,
) -> int:
    _dialog_log(f"_show_message_box called: parent={parent}, title={title}")
    
    # Use custom QDialog like in Adapters/ui.py - it works there
    dlg = QtWidgets.QDialog(parent)
    dlg.setWindowTitle(title)
    dlg.setWindowFlags(dlg.windowFlags() & ~QtCore.Qt.WindowType.WindowContextHelpButtonHint)
    dlg.setMinimumWidth(320)
    
    apply_dialog_icon(dlg)
    
    vlayout = QtWidgets.QVBoxLayout(dlg)
    vlayout.setSpacing(16)
    vlayout.setContentsMargins(20, 20, 20, 20)
    
    hlayout = QtWidgets.QHBoxLayout()
    
    # Icon
    icon_label = QtWidgets.QLabel()
    icon_path = _resolve_dialog_icon(icon_name)
    if icon_path:
        pm = QtGui.QPixmap(icon_path)
        if not pm.isNull():
            icon_label.setPixmap(pm.scaled(48, 48, QtCore.Qt.AspectRatioMode.KeepAspectRatio, QtCore.Qt.TransformationMode.SmoothTransformation))
    
    if icon_label.pixmap() is None or icon_label.pixmap().isNull():
        style = QtWidgets.QApplication.style()
        icon_label.setPixmap(style.standardIcon(QtWidgets.QStyle.StandardPixmap.SP_MessageBoxInformation).pixmap(48, 48))
    
    hlayout.addWidget(icon_label, 0, QtCore.Qt.AlignmentFlag.AlignTop)
    
    # Message
    msg_label = QtWidgets.QLabel(text)
    msg_label.setWordWrap(True)
    msg_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
    msg_label.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
    hlayout.addWidget(msg_label, 1)
    vlayout.addLayout(hlayout)
    
    # Button box - exactly like in Adapters/ui.py
    btn_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Ok)
    wire_dialog_button_box(btn_box, dlg.accept)
    vlayout.addWidget(btn_box, 0, QtCore.Qt.AlignmentFlag.AlignRight)
    
    _dialog_log(f"  Dialog created, about to exec()")
    
    result = dlg.exec()
    
    _dialog_log(f"  exec() returned: {result}")
    
    return result


def show_success(parent, text: str, title: str = "Успешно") -> int:
    return _show_message_box(parent, text, title, "alert")


def show_error(parent, text: str, title: str = "Ошибка") -> int:
    return _show_message_box(parent, text, title, "error")


def show_warning(parent, text: str, title: str = "Внимание") -> int:
    return _show_message_box(parent, text, title, "warning")


def _standard_button_candidates(owner, name: str) -> list[object]:
    values: list[object] = []
    enum_cls = getattr(owner, "StandardButton", None)
    if enum_cls is not None:
        value = getattr(enum_cls, name, None)
        if value is not None:
            values.append(value)
    legacy = getattr(owner, name, None)
    if legacy is not None and legacy not in values:
        values.append(legacy)
    return values


def _find_standard_button(container, owner, name: str):
    for value in _standard_button_candidates(owner, name):
        try:
            button = container.button(value)
        except Exception:
            button = None
        if button is not None:
            return button
    return None


def wire_message_box_buttons(msg_box: QtWidgets.QMessageBox) -> None:
    if bool(msg_box.property("_dialog_buttons_wired")):
        return
    msg_box.setProperty("_dialog_buttons_wired", True)

    ok_values = tuple(_standard_button_candidates(QtWidgets.QMessageBox, "Ok"))
    yes_values = tuple(_standard_button_candidates(QtWidgets.QMessageBox, "Yes"))
    cancel_values = tuple(_standard_button_candidates(QtWidgets.QMessageBox, "Cancel"))
    close_values = tuple(_standard_button_candidates(QtWidgets.QMessageBox, "Close"))
    no_values = tuple(_standard_button_candidates(QtWidgets.QMessageBox, "No"))

    def _handle_button(button) -> None:
        try:
            standard = msg_box.standardButton(button)
        except Exception:
            standard = None
        if standard in ok_values or standard in yes_values:
            msg_box.accept()
        elif standard in cancel_values or standard in close_values or standard in no_values:
            msg_box.reject()

    try:
        msg_box.buttonClicked.connect(_handle_button)
    except Exception:
        pass

    ok_button = _find_standard_button(msg_box, QtWidgets.QMessageBox, "Ok")
    if ok_button is not None:
        ok_button.clicked.connect(msg_box.accept)
        try:
            ok_button.setDefault(True)
            ok_button.setAutoDefault(True)
        except Exception:
            pass

    cancel_button = _find_standard_button(msg_box, QtWidgets.QMessageBox, "Cancel")
    if cancel_button is not None:
        cancel_button.clicked.connect(msg_box.reject)

    close_button = _find_standard_button(msg_box, QtWidgets.QMessageBox, "Close")
    if close_button is not None:
        close_button.clicked.connect(msg_box.reject)


def wire_dialog_button_box(
    button_box: QtWidgets.QDialogButtonBox,
    on_accept: Callable[[], None] | None = None,
    on_reject: Callable[[], None] | None = None,
) -> None:
    _dialog_log(f"wire_dialog_button_box called: on_accept={on_accept}, on_reject={on_reject}")
    
    ok_button = _find_standard_button(button_box, QtWidgets.QDialogButtonBox, "Ok")
    _dialog_log(f"  OK button found: {ok_button}")
    
    if ok_button is not None:
        if on_accept is not None:
            ok_button.clicked.connect(on_accept)
            _dialog_log(f"  Connected OK.clicked to {on_accept}")
        try:
            ok_button.setDefault(True)
            ok_button.setAutoDefault(True)
            _dialog_log(f"  Set OK button as default")
        except Exception:
            pass

    cancel_button = _find_standard_button(button_box, QtWidgets.QDialogButtonBox, "Cancel")
    if cancel_button is not None and on_reject is not None:
        cancel_button.clicked.connect(on_reject)
        _dialog_log(f"  Connected Cancel.clicked to {on_reject}")

    close_button = _find_standard_button(button_box, QtWidgets.QDialogButtonBox, "Close")
    if close_button is not None and on_reject is not None:
        close_button.clicked.connect(on_reject)
        _dialog_log(f"  Connected Close.clicked to {on_reject}")


def show_dialog(dialog: QtWidgets.QDialog, *, modal: bool = True):
    apply_dialog_icon(dialog)
    try:
        dialog.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
    except Exception:
        pass

    def _cleanup(*_args) -> None:
        _OPEN_DIALOG_REFS.discard(dialog)

    try:
        dialog.finished.connect(_cleanup)
    except Exception:
        pass

    if modal:
        if hasattr(dialog, "exec"):
            return dialog.exec()
        return dialog.exec_()

    _OPEN_DIALOG_REFS.add(dialog)
    if hasattr(dialog, "open"):
        dialog.open()
    else:
        dialog.show()
    return 0


def message_box(
    parent,
    text: str,
    title: str = "Сообщение",
    icon: QtWidgets.QMessageBox.Icon = QtWidgets.QMessageBox.Icon.Information,
    buttons: QtWidgets.QMessageBox.StandardButton = QtWidgets.QMessageBox.StandardButton.Ok,
) -> QtWidgets.QMessageBox.StandardButton:
    mb = QtWidgets.QMessageBox(parent)
    mb.setWindowTitle(title)
    mb.setText(text)
    mb.setIcon(icon)
    mb.setStandardButtons(buttons)
    mb.setWindowFlags(mb.windowFlags() & ~QtCore.Qt.WindowType.WindowContextHelpButtonHint)
    apply_dialog_icon(mb)
    wire_message_box_buttons(mb)
    _fit_message_box(mb)
    return mb.exec()


def information_box(parent, text: str, title: str = "Информация") -> QtWidgets.QMessageBox.StandardButton:
    return message_box(parent, text, title, QtWidgets.QMessageBox.Icon.Information)


def warning_box(parent, text: str, title: str = "Внимание") -> QtWidgets.QMessageBox.StandardButton:
    return message_box(parent, text, title, QtWidgets.QMessageBox.Icon.Warning)


def critical_box(parent, text: str, title: str = "Ошибка") -> QtWidgets.QMessageBox.StandardButton:
    return message_box(parent, text, title, QtWidgets.QMessageBox.Icon.Critical)


def question_box(
    parent,
    text: str,
    title: str = "Вопрос",
    buttons: QtWidgets.QMessageBox.StandardButton = QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
) -> QtWidgets.QMessageBox.StandardButton:
    return message_box(parent, text, title, QtWidgets.QMessageBox.Icon.Question, buttons)


_original_QMessageBox_exec = None
_original_QMessageBox_show = None
_original_QDialog_exec = None
_original_QDialog_show = None
_original_QDialog_open = None


def _fit_message_box(message_box: QtWidgets.QMessageBox) -> None:
    try:
        message_box.setMinimumSize(520, 180)
        for object_name in ("qt_msgbox_label", "qt_msgbox_informativelabel"):
            label = message_box.findChild(QtWidgets.QLabel, object_name)
            if label is not None:
                label.setWordWrap(True)
                label.setMinimumWidth(420)
                label.setSizePolicy(
                    QtWidgets.QSizePolicy.Policy.Expanding,
                    QtWidgets.QSizePolicy.Policy.MinimumExpanding,
                )
                label.adjustSize()
        layout = message_box.layout()
        if layout is not None:
            layout.activate()
        message_box.adjustSize()
    except Exception:
        pass


def _patched_message_box_exec(self):
    apply_dialog_icon(self)
    _fit_message_box(self)
    return _original_QMessageBox_exec(self)


def _patched_message_box_show(self):
    apply_dialog_icon(self)
    _fit_message_box(self)
    return _original_QMessageBox_show(self)


def _patched_dialog_exec(self):
    apply_dialog_icon(self)
    return _original_QDialog_exec(self)


def _patched_dialog_show(self):
    apply_dialog_icon(self)
    return _original_QDialog_show(self)


def _patched_dialog_open(self):
    apply_dialog_icon(self)
    return _original_QDialog_open(self)


def install_dialog_icon_patch():
    global _original_QMessageBox_exec, _original_QMessageBox_show
    global _original_QDialog_exec, _original_QDialog_show, _original_QDialog_open
    
    if _original_QMessageBox_exec is not None:
        return
    
    _original_QMessageBox_exec = QtWidgets.QMessageBox.exec
    _original_QMessageBox_show = QtWidgets.QMessageBox.show
    QtWidgets.QMessageBox.exec = _patched_message_box_exec
    QtWidgets.QMessageBox.show = _patched_message_box_show
    
    _original_QDialog_exec = QtWidgets.QDialog.exec
    _original_QDialog_show = QtWidgets.QDialog.show
    _original_QDialog_open = QtWidgets.QDialog.open
    QtWidgets.QDialog.exec = _patched_dialog_exec
    QtWidgets.QDialog.show = _patched_dialog_show
    QtWidgets.QDialog.open = _patched_dialog_open


install_dialog_icon_patch()
