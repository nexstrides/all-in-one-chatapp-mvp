"""Desktop shell, account lifecycle, tray and hibernation."""

import time
from collections.abc import Callable
from importlib.resources import files
from typing import Any

from PySide6.QtCore import QSize, Qt, QTimer, QUrl
from PySide6.QtGui import QAction, QCloseEvent, QColor, QDesktopServices, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from allinone import autostart
from allinone.dialogs import HistoryDialog, ServiceDialog
from allinone.models import Service, can_hibernate
from allinone.notifications import NotificationCenter
from allinone.service_view import ServiceView
from allinone.storage import History, Store


def app_icon(count: int = 0) -> QIcon:
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor("#7653e6"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(2, 2, 60, 60, 18, 18)
    painter.setPen(QColor("white"))
    font = painter.font()
    font.setPixelSize(28 if count else 34)
    font.setBold(True)
    painter.setFont(font)
    painter.drawText(
        pixmap.rect(), Qt.AlignmentFlag.AlignCenter, str(min(count, 99)) if count else "a"
    )
    painter.end()
    return QIcon(pixmap)


class MainWindow(QMainWindow):
    def __init__(self, store: Store, history: History) -> None:
        super().__init__()
        self.store = store
        self.history = history
        self.views: dict[str, ServiceView] = {}
        self.badges: dict[str, int] = {}
        self.last_used: dict[str, float] = {}
        self.statuses: dict[str, str] = {}
        self.retiring: set[str] = set()
        self.quitting = False
        self.setWindowTitle("All in One Chatapp")
        self.setWindowIcon(app_icon())
        self.resize(1280, 830)
        self.setMinimumSize(850, 560)
        self.setStyleSheet(files("allinone").joinpath("theme.qss").read_text())
        self.center = NotificationCenter(history, self)
        self.center.dnd = store.dnd
        self.center.focus_service.connect(self.focus_service)
        self.build_ui()
        self.build_tray()
        self.refresh_accounts()
        for service in store.services:
            self.ensure_view(service)
        if store.services:
            self.accounts.setCurrentRow(0)
        self.idle_timer = QTimer(self)
        self.idle_timer.timeout.connect(self.hibernate_idle)
        self.idle_timer.start(60_000)

    def build_ui(self) -> None:
        shell = QWidget()
        self.setCentralWidget(shell)
        layout = QHBoxLayout(shell)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(255)
        nav = QVBoxLayout(sidebar)
        nav.setContentsMargins(18, 28, 18, 22)
        brand = QLabel("all in one.")
        brand.setObjectName("brand")
        nav.addWidget(brand)
        subtitle = QLabel("YOUR CONVERSATIONS, TOGETHER")
        subtitle.setObjectName("eyebrow")
        nav.addWidget(subtitle)
        nav.addSpacing(30)
        nav.addWidget(QLabel("WORKSPACE"))
        self.accounts = QListWidget()
        self.accounts.setSpacing(5)
        self.accounts.setAccessibleName("Service accounts")
        self.accounts.currentItemChanged.connect(self.selection_changed)
        nav.addWidget(self.accounts, 1)
        add = QPushButton("+  Add a service")
        add.setObjectName("primary")
        add.setShortcut("Ctrl+N")
        add.clicked.connect(self.add_service)
        nav.addWidget(add)
        history = QPushButton("Notification history")
        history.clicked.connect(self.show_history)
        nav.addWidget(history)
        self.dnd_button = QPushButton("Do Not Disturb")
        self.dnd_button.setCheckable(True)
        self.dnd_button.setChecked(self.store.dnd)
        self.dnd_button.toggled.connect(self.set_dnd)
        nav.addWidget(self.dnd_button)
        foot = QLabel("LOCAL WORKSPACE\nAccounts stay on this device")
        foot.setObjectName("footnote")
        nav.addSpacing(18)
        nav.addWidget(foot)
        layout.addWidget(sidebar)
        content = QWidget()
        panel = QVBoxLayout(content)
        panel.setContentsMargins(22, 18, 22, 16)
        bar = QHBoxLayout()
        self.heading = QLabel("Your workspace")
        self.heading.setObjectName("heading")
        self.heading.setTextFormat(Qt.TextFormat.PlainText)
        bar.addWidget(self.heading, 1)
        for label, callback in [
            ("Reload", self.reload),
            ("Open in browser", self.open_browser),
            ("Service settings", self.edit_service),
        ]:
            button = QPushButton(label)
            button.clicked.connect(callback)
            bar.addWidget(button)
        panel.addLayout(bar)
        self.stack = QStackedWidget()
        welcome = QWidget()
        welcome_layout = QVBoxLayout(welcome)
        welcome_layout.addStretch()
        for text, name in [
            ("A little less switching.\nA lot more focus.", "hero"),
            ("Your chats and inboxes, in one calm workspace.", "welcomeText"),
            (
                "Add WhatsApp, Telegram, Slack, Discord, Gmail or Outlook.\n"
                "Every account has its own private browser profile.",
                "welcomeText",
            ),
        ]:
            welcome_label = QLabel(text)
            welcome_label.setObjectName(name)
            welcome_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            welcome_layout.addWidget(welcome_label)
        start = QPushButton("Add your first service")
        start.setObjectName("primary")
        start.clicked.connect(self.add_service)
        welcome_layout.addWidget(start, 0, Qt.AlignmentFlag.AlignCenter)
        welcome_layout.addStretch()
        self.stack.addWidget(welcome)
        panel.addWidget(self.stack, 1)
        self.status = QLabel("Ready · no accounts connected")
        self.status.setObjectName("footnote")
        self.status.setWordWrap(True)
        panel.addWidget(self.status)
        layout.addWidget(content, 1)
        menu = self.menuBar().addMenu("Workspace")
        self.menu_action(menu, "Add service", self.add_service, "Ctrl+N")
        self.menu_action(menu, "Clear current cache (keeps login)", self.clear_cache)
        self.menu_action(menu, "Remove current account", self.remove_service)
        self.menu_action(menu, "Open log folder", self.open_logs)
        self.menu_action(menu, "Quit", self.quit_app, "Ctrl+Q")

    def menu_action(
        self, menu: QMenu, text: str, callback: Callable, shortcut: str = ""
    ) -> QAction:
        action = QAction(text, self)
        if shortcut:
            action.setShortcut(shortcut)
        action.triggered.connect(callback)
        menu.addAction(action)
        return action

    def build_tray(self) -> None:
        self.tray = QSystemTrayIcon(app_icon(), self)
        self.tray.setToolTip("All in One Chatapp")
        menu = QMenu(self)
        self.menu_action(menu, "Open workspace", self.show_window)
        self.menu_action(menu, "Notification history", self.show_history)
        self.startup = QAction("Start with Windows", self)
        self.startup.setCheckable(True)
        self.startup.setEnabled(__import__("sys").platform == "win32")
        try:
            self.startup.setChecked(autostart.enabled())
        except OSError:
            self.status.setText("Windows startup settings could not be read.")
        self.startup.toggled.connect(self.toggle_startup)
        menu.addAction(self.startup)
        self.menu_action(menu, "Quit", self.quit_app)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(
            lambda reason: (
                self.show_window()
                if reason
                in (
                    QSystemTrayIcon.ActivationReason.Trigger,
                    QSystemTrayIcon.ActivationReason.DoubleClick,
                )
                else None
            )
        )
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray.show()

    def current_service(self) -> Service | None:
        item = self.accounts.currentItem()
        service_id = item.data(Qt.ItemDataRole.UserRole) if item else None
        return next((s for s in self.store.services if s.id == service_id), None)

    def refresh_accounts(self) -> None:
        current = self.current_service()
        self.accounts.blockSignals(True)
        self.accounts.clear()
        for service in self.store.services:
            count = self.badges.get(service.id, 0)
            label = service.name + (f"  ({count})" if count else "")
            if service.id in self.statuses and service.id not in self.views:
                label += "  · sleeping"
            item = QListWidgetItem(label)
            item.setSizeHint(QSize(200, 48))
            item.setData(Qt.ItemDataRole.UserRole, service.id)
            self.accounts.addItem(item)
            if current and current.id == service.id:
                self.accounts.setCurrentItem(item)
        self.accounts.blockSignals(False)
        total = sum(self.badges.get(s.id, 0) for s in self.store.services)
        self.tray.setIcon(app_icon(total))
        self.tray.setToolTip(f"All in One Chatapp · {total} unread")

    def ensure_view(self, service: Service) -> ServiceView | None:
        if service.id in self.retiring:
            self.status.setText("Releasing this profile. Try again in a moment.")
            return None
        if service.id not in self.views:
            view = ServiceView(
                service, self.store.profile_path(service.id), self.center.receive, self.stack
            )
            view.unread_changed.connect(lambda count, sid=service.id: self.unread(sid, count))
            view.status_changed.connect(lambda text, sid=service.id: self.service_status(sid, text))
            self.views[service.id] = view
            self.last_used[service.id] = time.monotonic()
            self.stack.addWidget(view)
        return self.views[service.id]

    def selection_changed(self, _current: Any = None, _previous: Any = None) -> None:
        service = self.current_service()
        if service:
            view = self.ensure_view(service)
            if view:
                self.stack.setCurrentWidget(view)
                self.last_used[service.id] = time.monotonic()
                self.heading.setText(service.name)
                self.status.setText(self.statuses.get(service.id, "Loading…"))
        else:
            self.stack.setCurrentIndex(0)
            self.heading.setText("Your workspace")

    def service_status(self, service_id: str, text: str) -> None:
        self.statuses[service_id] = text
        current = self.current_service()
        if current and current.id == service_id:
            self.status.setText(text)

    def unread(self, service_id: str, count: int) -> None:
        if service_id not in self.views:
            return
        previous = self.badges.get(service_id, 0)
        self.badges[service_id] = count
        if previous and not count:
            self.center.clear_service(service_id)
        self.refresh_accounts()

    def add_service(self) -> None:
        dialog = ServiceDialog(self)
        if dialog.exec() == dialog.DialogCode.Accepted and dialog.result_service:
            try:
                self.store.add(dialog.result_service)
            except OSError as exc:
                self.error(exc)
                return
            self.refresh_accounts()
            self.accounts.setCurrentRow(len(self.store.services) - 1)

    def edit_service(self) -> None:
        service = self.current_service()
        if not service:
            return
        dialog = ServiceDialog(self, service)
        if dialog.exec() != dialog.DialogCode.Accepted or not dialog.result_service:
            return
        updated = dialog.result_service
        index = self.store.services.index(service)
        self.store.services[index] = updated
        try:
            self.store.save()
        except OSError as exc:
            self.store.services[index] = service
            self.error(exc)
            return
        self.center.clear_service(service.id)
        view = self.views.get(service.id)
        if view:
            view.service = updated
            view.service_page.service = updated
            view.account_profile.setNotificationPresenter(lambda n: self.center.receive(updated, n))
            if updated.user_agent != service.user_agent or updated.url != service.url:
                self.retire(service.id, lambda: self.focus_service(service.id))
        self.refresh_accounts()
        self.heading.setText(updated.name)

    def remove_service(self) -> None:
        service = self.current_service()
        if not service:
            return
        if (
            QMessageBox.question(
                self,
                "Remove account?",
                f"Remove {service.name} and delete its local sign-in data? This cannot be undone.",
            )
            != QMessageBox.StandardButton.Yes
        ):
            return
        try:
            self.store.remove(service.id)
            self.history.clear(service.id)
        except OSError as exc:
            self.error(exc)
            return
        self.center.clear_service(service.id)
        self.retire(service.id, lambda: self.store.cleanup(service.id))
        self.badges.pop(service.id, None)
        self.refresh_accounts()
        self.accounts.setCurrentRow(0 if self.store.services else -1)
        self.selection_changed()

    def retire(self, service_id: str, after: Callable[[], None] | None = None) -> None:
        view = self.views.pop(service_id, None)
        if view is None:
            if after:
                after()
            return
        self.retiring.add(service_id)
        self.stack.removeWidget(view)

        def finished() -> None:
            self.retiring.discard(service_id)
            if after:
                after()

        view.dispose(finished)

    def focus_service(self, service_id: str) -> None:
        self.show_window()
        for index in range(self.accounts.count()):
            item = self.accounts.item(index)
            if item.data(Qt.ItemDataRole.UserRole) == service_id:
                self.accounts.setCurrentRow(index)
                self.selection_changed()
                return
        self.status.setText("This account has been removed.")

    def reload(self) -> None:
        service = self.current_service()
        if service:
            view = self.ensure_view(service)
            if view:
                view.reload()

    def open_browser(self) -> None:
        service = self.current_service()
        if service:
            # Do not copy OAuth callback URLs or tokens into the system browser.
            QDesktopServices.openUrl(QUrl(service.url))

    def clear_cache(self) -> None:
        service = self.current_service()
        if service and service.id in self.views:
            self.views[service.id].clear_cache()
            self.status.setText("Clearing HTTP cache. Sign-in data is preserved.")

    def set_dnd(self, checked: bool) -> None:
        previous = self.store.dnd
        self.store.dnd = checked
        try:
            self.store.save()
        except OSError as exc:
            self.store.dnd = previous
            self.dnd_button.blockSignals(True)
            self.dnd_button.setChecked(previous)
            self.dnd_button.blockSignals(False)
            self.error(exc)
        self.center.dnd = self.store.dnd

    def toggle_startup(self, checked: bool) -> None:
        try:
            autostart.set_enabled(checked)
        except OSError as exc:
            self.startup.blockSignals(True)
            self.startup.setChecked(not checked)
            self.startup.blockSignals(False)
            self.error(exc)

    def hibernate_idle(self) -> None:
        current = self.current_service()
        for service in self.store.services:
            active = bool(current and current.id == service.id)
            if active:
                self.last_used[service.id] = time.monotonic()
            idle = time.monotonic() - self.last_used.get(service.id, time.monotonic())
            if service.id in self.views and can_hibernate(
                service, self.badges.get(service.id, 0), active, idle
            ):
                self.retire(service.id)
                self.statuses[service.id] = "Sleeping"
        self.refresh_accounts()

    def show_history(self) -> None:
        dialog = HistoryDialog(self.history, self)
        dialog.selected_service.connect(self.focus_service)
        self.center.changed.connect(dialog.refresh)
        dialog.exec()
        self.center.changed.disconnect(dialog.refresh)
        dialog.deleteLater()

    def open_logs(self) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.store.root / "logs")))

    def show_window(self) -> None:
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def error(self, exc: Exception) -> None:
        QMessageBox.warning(self, "Could not save changes", str(exc))

    def closeEvent(self, event: QCloseEvent) -> None:
        if not self.quitting and self.tray.isVisible():
            event.ignore()
            self.hide()
        else:
            event.ignore()
            self.quit_app()

    def quit_app(self) -> None:
        if self.quitting:
            return
        self.quitting = True
        self.idle_timer.stop()
        self.center.shutdown()
        self.tray.hide()
        self.hide()
        for service_id in list(self.views):
            self.retire(service_id)
        self.quit_timer = QTimer(self)
        self.quit_timer.timeout.connect(self.finish_quit)
        self.quit_timer.start(50)

    def finish_quit(self) -> None:
        if not self.retiring:
            self.quit_timer.stop()
            QApplication.quit()
