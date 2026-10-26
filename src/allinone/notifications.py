"""Notification lifetimes and per-toast click routing on the Qt thread."""

import logging
import sys
import time
from dataclasses import dataclass
from typing import Any

from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtWebEngineCore import QWebEngineNotification
from PySide6.QtWidgets import QDialog, QLabel, QPushButton, QVBoxLayout, QWidget

from allinone.models import Service, should_notify
from allinone.storage import History

log = logging.getLogger(__name__)


@dataclass
class Pending:
    service: Service
    notification: QWebEngineNotification | None
    due: float
    popup: QDialog | None = None
    toast: Any = None


class NotificationCenter(QObject):
    activated = Signal(int)
    focus_service = Signal(str)
    changed = Signal()

    def __init__(self, history: History, parent: QWidget) -> None:
        super().__init__(parent)
        self.history = history
        self.window = parent
        self.dnd = False
        self.pending: dict[int, Pending] = {}
        self.toaster: Any = None
        if sys.platform == "win32":
            try:
                from windows_toasts import WindowsToaster

                self.toaster = WindowsToaster("All in One Chatapp")
            except Exception:
                log.warning("Native notifications unavailable; using application alerts")
        self.activated.connect(self.activate)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.reminders)
        self.timer.start(30_000)

    def receive(self, service: Service, notification: QWebEngineNotification) -> None:
        if not service.notifications:
            notification.close()
            return
        item_id = self.history.record(service)
        self.history.prune()
        self.pending[item_id] = Pending(service, notification, time.monotonic())
        notification.closed.connect(lambda: self.web_closed(item_id))
        self.changed.emit()
        if should_notify(service, self.dnd):
            self.display(item_id)
        else:
            notification.close()
        # Keep Chromium notification objects bounded during long-running sessions.
        while len(self.pending) > 200:
            self.forget(next(iter(self.pending)))

    def display(self, item_id: int) -> None:
        item = self.pending.get(item_id)
        if item is None:
            return
        item.due = time.monotonic() + item.service.reminder_minutes * 60
        notification = item.notification
        title = notification.title()[:150] if notification else "Unread activity"
        body = notification.message()[:500] if notification else "Open this service to catch up."
        if notification:
            notification.show()
        native_ok = False
        if self.toaster:
            try:
                from windows_toasts import Toast

                toast = Toast()
                toast.text_fields = [item.service.name, title, body]
                # Windows callbacks may be on a worker; the signal queues work to Qt.
                toast.on_activated = lambda _event: self.activated.emit(item_id)
                self.toaster.show_toast(toast)
                item.toast = toast
                native_ok = True
            except Exception:
                log.warning("Native notification failed; using application alert")
        if item.service.sticky or not native_ok:
            self.popup(item_id, title, body)

    def popup(self, item_id: int, title: str, body: str) -> None:
        item = self.pending[item_id]
        if item.popup:
            item.popup.show()
            return
        dialog = QDialog(self.window, Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint)
        dialog.setWindowTitle(item.service.name)
        dialog.setMinimumWidth(350)
        layout = QVBoxLayout(dialog)
        for text in (title, body):
            label = QLabel(text)
            label.setTextFormat(Qt.TextFormat.PlainText)
            label.setWordWrap(True)
            layout.addWidget(label)
        button = QPushButton("Open " + item.service.name)
        button.clicked.connect(lambda: self.activate(item_id))
        layout.addWidget(button)
        dismiss = QPushButton("Dismiss")
        dismiss.clicked.connect(lambda: self.forget(item_id))
        layout.addWidget(dismiss)
        dialog.finished.connect(lambda _result: self.popup_closed(item_id))
        item.popup = dialog
        dialog.show()
        if not item.service.sticky:
            QTimer.singleShot(10_000, dialog.close)

    def popup_closed(self, item_id: int) -> None:
        item = self.pending.get(item_id)
        if item and item.popup:
            item.popup.deleteLater()
            item.popup = None

    def web_closed(self, item_id: int) -> None:
        item = self.pending.get(item_id)
        if item:
            item.notification = None
            self.forget(item_id)  # Provider cancellation must also stop reminders.

    def activate(self, item_id: int) -> None:
        item = self.pending.get(item_id)
        if not item:
            return
        if item.notification:
            item.notification.click()
        self.focus_service.emit(item.service.id)
        self.history.mark_opened(item_id)
        self.forget(item_id)
        self.changed.emit()

    def forget(self, item_id: int) -> None:
        item = self.pending.pop(item_id, None)
        if not item:
            return
        if item.popup:
            item.popup.close()
            item.popup.deleteLater()
        if item.notification:
            item.notification.close()
        if item.toast and self.toaster:
            try:
                self.toaster.remove_toast(item.toast)
            except Exception:
                log.debug("Toast was already removed")

    def clear_service(self, service_id: str) -> None:
        for item_id, item in list(self.pending.items()):
            if item.service.id == service_id:
                self.forget(item_id)

    def reminders(self) -> None:
        for item_id, item in list(self.pending.items()):
            if (
                item.service.reminder_minutes
                and time.monotonic() >= item.due
                and should_notify(item.service, self.dnd)
            ):
                self.display(item_id)

    def shutdown(self) -> None:
        self.timer.stop()
        for item_id in list(self.pending):
            self.forget(item_id)
