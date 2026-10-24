"""Entry point; no remote telemetry, credentials or cloud services."""

import argparse
import logging
import sys
from logging.handlers import RotatingFileHandler

from PySide6.QtCore import QLockFile
from PySide6.QtWidgets import QApplication, QMessageBox

from allinone import __version__
from allinone.main_window import MainWindow
from allinone.storage import History, Store, data_directory


def main() -> int:
    parser = argparse.ArgumentParser(description="All in One Chatapp")
    parser.add_argument("--hidden", action="store_true", help="Start in the system tray")
    parser.add_argument("--version", action="version", version=__version__)
    args = parser.parse_args()
    app = QApplication(sys.argv[:1])
    app.setApplicationName("AllInOneChatapp")
    app.setApplicationVersion(__version__)
    app.setQuitOnLastWindowClosed(False)
    root = data_directory()
    root.mkdir(parents=True, exist_ok=True)
    lock = QLockFile(str(root / "app.lock"))
    lock.setStaleLockTime(0)
    if not lock.tryLock(100):
        QMessageBox.information(
            None, "All in One Chatapp", "The app is already running. Open it from the system tray."
        )
        return 0
    (root / "logs").mkdir(exist_ok=True)
    handler = RotatingFileHandler(
        root / "logs" / "app.log", maxBytes=512_000, backupCount=3, encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logging.getLogger("allinone").addHandler(handler)
    logging.getLogger("allinone").setLevel(logging.INFO)
    try:
        store = Store(root)
        store.cleanup()
        history = History(root / "history.sqlite3")
    except (OSError, ValueError) as exc:
        QMessageBox.critical(None, "Cannot open workspace", str(exc))
        lock.unlock()
        return 1
    window = MainWindow(store, history)
    if not args.hidden or not window.tray.isVisible():
        window.show()
    logging.getLogger("allinone").info("Workspace started")
    result = app.exec()
    history.close()
    lock.unlock()
    handler.close()
    return result
