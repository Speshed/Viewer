import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from shared.app_common import (
    AppMainWindow,
    ICON_DIR,
    _shutdown_api_check_threads,
    enable_theme_sync,
    get_viewer_logo_path,
    get_window_icon_path,
)

APP_VERSION = "1.0.0"
APP_VERSION_DATE = "03.03.2026"
APP_VERSION_CHANGES = [
    "Общий стартовый экран Larix Viewer с выбором Статусы и Элементы.",
]

VIEWER_CARDS = [
    ("viewer", "Статусы", "", "status.png"),
    ("bim_sync", "Элементы", "", "sync.png"),
]

VIEWER_MODULE_LOADERS = {
    "viewer": ("Viewer", "ui", "MainWindow", True),
}


def main():
    app = QApplication(sys.argv)
    try:
        app.aboutToQuit.connect(_shutdown_api_check_threads)
    except Exception:
        pass
    try:
        enable_theme_sync(app, ICON_DIR)
    except Exception:
        pass

    window = AppMainWindow(
        app_title="Larix Viewer",
        cards_data=VIEWER_CARDS,
        logo_func=get_viewer_logo_path,
        logo_height=64,
        module_loaders=VIEWER_MODULE_LOADERS,
        bim_sync=True,
        show_template_download=False,
        app_version=APP_VERSION,
        app_version_date=APP_VERSION_DATE,
        app_version_changes=APP_VERSION_CHANGES,
        skip_menu=False,
    )

    icon_path = get_window_icon_path()
    if icon_path:
        window.setWindowIcon(QIcon(icon_path))

    window.show()

    if hasattr(app, "exec"):
        sys.exit(app.exec())
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
