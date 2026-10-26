"""Desktop shell, account lifecycle, tray and hibernation."""

import time
from collections.abc import Callable
from importlib.resources import files
from typing import Any

from PySide6.QtCore import QPoint, QSize, Qt, QTimer, QUrl
from PySide6.QtGui import (
    QAction,
    QCloseEvent,
    QColor,
    QDesktopServices,
    QIcon,
    QPainter,
    QPixmap,
    QResizeEvent,
)
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
    QSizePolicy,
    QStackedWidget,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from allinone import autostart
from allinone.dialogs import HistoryDialog, ServiceDialog
from allinone.icons import avatar_icon, badge_icon, symbol_icon
from allinone.models import Service, can_hibernate, needs_slack_workspace
from allinone.notifications import NotificationCenter
from allinone.service_view import ServiceView
from allinone.settings import ProfileDialog, SettingsPage
from allinone.storage import History, Store
from allinone.widgets import IconButton


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
        self.center.changed.connect(self.refresh_accounts)
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
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(
            lambda pos: self.show_context_menu(self.mapToGlobal(pos))
        )
        layout = QHBoxLayout(shell)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(80)
        self.sidebar.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.sidebar.customContextMenuRequested.connect(
            lambda pos: self.show_context_menu(self.sidebar.mapToGlobal(pos))
        )
        nav = QVBoxLayout(self.sidebar)
        nav.setContentsMargins(10, 12, 10, 12)
        nav.setSpacing(6)
        brand = QLabel()
        brand.setPixmap(app_icon().pixmap(36, 36))
        brand.setToolTip("All in One Chatapp")
        nav.addWidget(brand, 0, Qt.AlignmentFlag.AlignHCenter)
        nav.addSpacing(12)
        self.accounts = QListWidget()
        self.accounts.setObjectName("serviceRail")
        self.accounts.setIconSize(QSize(40, 40))
        self.accounts.setSpacing(2)
        self.accounts.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.accounts.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        self.accounts.setAccessibleName("Service accounts; right-click for account actions")
        self.accounts.currentItemChanged.connect(self.selection_changed)
        self.accounts.itemClicked.connect(self.selection_changed)
        self.accounts.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.accounts.customContextMenuRequested.connect(self.account_context_menu)
        nav.addWidget(self.accounts)
        self.add_button = IconButton("Add a service (Ctrl+N)", symbol_icon("add"))
        self.add_button.setObjectName("addService")
        self.add_button.clicked.connect(self.add_service)
        nav.addWidget(self.add_button, 0, Qt.AlignmentFlag.AlignHCenter)
        nav.addStretch(1)
        self.history_button = IconButton("Notifications", symbol_icon("bell"))
        self.history_button.clicked.connect(self.show_history)
        nav.addWidget(self.history_button, 0, Qt.AlignmentFlag.AlignHCenter)
        self.dnd_button = IconButton("Do Not Disturb", symbol_icon("moon"))
        self.dnd_button.setCheckable(True)
        self.dnd_button.setChecked(self.store.dnd)
        self.dnd_button.toggled.connect(self.set_dnd)
        nav.addWidget(self.dnd_button, 0, Qt.AlignmentFlag.AlignHCenter)
        self.profile_button = IconButton(
            "Your profile and settings",
            avatar_icon(self.store.profile.name, self.store.profile.avatar_png),
        )
        self.profile_button.clicked.connect(self.show_profile)
        nav.addWidget(self.profile_button, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self.sidebar)
        self.stack = QStackedWidget()
        self.stack.setContentsMargins(0, 0, 0, 0)
        self.welcome = QWidget()
        welcome_layout = QVBoxLayout(self.welcome)
        welcome_layout.setContentsMargins(40, 40, 40, 40)
        welcome_layout.setSpacing(16)
        welcome_layout.addStretch()
        for text, name in [
            ("All your conversations.\nOne place to focus.", "hero"),
            ("Add your favourite chat and email services to get started.", "welcomeText"),
            ("Separate accounts. Saved sign-ins. A little less switching.", "muted"),
        ]:
            label = QLabel(text)
            label.setObjectName(name)
            label.setWordWrap(True)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            welcome_layout.addWidget(label)
        start = QPushButton("Add your first service")
        start.setObjectName("primary")
        start.clicked.connect(self.add_service)
        welcome_layout.addWidget(start, 0, Qt.AlignmentFlag.AlignCenter)
        hint = QLabel("Tip: right-click a service icon for settings and quick actions.")
        hint.setObjectName("muted")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome_layout.addWidget(hint)
        welcome_layout.addStretch()
        self.stack.addWidget(self.welcome)
        self.repair: QWidget | None = None
        self.settings_page: SettingsPage | None = None
        layout.addWidget(self.stack, 1)
        # Status is shown only for errors; service content has no permanent toolbar.
        self.status = QLabel(shell)
        self.status.setObjectName("statusNotice")
        self.status.setWordWrap(True)
        self.status.setTextFormat(Qt.TextFormat.PlainText)
        self.status.hide()
        for text, callback, shortcut in [
            ("Add service", self.add_service, "Ctrl+N"),
            ("App settings", self.show_settings, "Ctrl+,"),
            ("Reload", self.reload, "Ctrl+R"),
            ("Quit", self.quit_app, "Ctrl+Q"),
        ]:
            action = QAction(text, self)
            action.setShortcut(shortcut)
            action.triggered.connect(callback)
            self.addAction(action)
        self.sync_dnd()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        if hasattr(self, "accounts"):
            self.size_account_list()
        if hasattr(self, "status"):
            self.position_status()

    def size_account_list(self) -> None:
        height = min(self.accounts.count() * 60 + 4, max(64, self.height() - 310))
        self.accounts.setFixedHeight(height if self.accounts.count() else 0)

    def position_status(self) -> None:
        shell = self.centralWidget()
        if shell is None:
            return
        self.status.setGeometry(96, shell.height() - 76, max(280, shell.width() - 112), 60)
        self.status.raise_()

    def notify_status(self, text: str) -> None:
        self.status.setText(text)
        self.status.setVisible(bool(text) and text not in {"Connected", "Loading…"})
        self.position_status()

    def populate_context_menu(self, menu: QMenu) -> None:
        if self.current_service():
            self.menu_action(menu, "Reload service", self.reload)
            self.menu_action(menu, "Open in browser", self.open_browser)
            self.menu_action(menu, "Account settings…", self.edit_service)
            self.menu_action(menu, "Clear cache (keep sign-in)", self.clear_cache)
            self.menu_action(menu, "Remove account…", self.remove_service)
            menu.addSeparator()
        self.menu_action(menu, "Add service…", self.add_service)
        self.menu_action(menu, "App settings…", self.show_settings)
        self.menu_action(menu, "Your profile…", self.show_profile)
        self.menu_action(menu, "Notification history", self.show_history)
        menu.addSeparator()
        self.menu_action(menu, "Quit", self.quit_app)

    def show_context_menu(self, point: QPoint) -> None:
        menu = QMenu(self)
        self.populate_context_menu(menu)
        menu.exec(point)
        menu.deleteLater()

    def account_context_menu(self, point: QPoint) -> None:
        item = self.accounts.itemAt(point)
        if item:
            self.accounts.setCurrentItem(item)
        self.show_context_menu(self.accounts.viewport().mapToGlobal(point))

    def show_settings(self) -> None:
        if self.settings_page is None:
            self.settings_page = SettingsPage(self.store, self.set_dnd, self.toggle_startup, self)
            self.settings_page.closed.connect(self.selection_changed)
            self.settings_page.edit_requested.connect(self.edit_selected_service)
            self.settings_page.remove_requested.connect(self.remove_selected_service)
            self.settings_page.profile_requested.connect(self.show_profile)
            self.settings_page.history_requested.connect(self.show_history)
            self.stack.addWidget(self.settings_page)
        self.refresh_settings()
        self.stack.setCurrentWidget(self.settings_page)
        self.status.hide()

    def refresh_settings(self) -> None:
        if self.settings_page:
            self.settings_page.refresh(self.startup.isChecked(), self.startup.isEnabled())

    def edit_selected_service(self, service_id: str) -> None:
        self.focus_service(service_id)
        self.edit_service()
        self.show_settings()

    def remove_selected_service(self, service_id: str) -> None:
        self.focus_service(service_id)
        self.remove_service()
        self.show_settings()

    def show_profile(self) -> None:
        dialog = ProfileDialog(self.store.profile, self)
        if dialog.exec() == dialog.DialogCode.Accepted and dialog.result_profile:
            previous = self.store.profile
            self.store.profile = dialog.result_profile
            try:
                self.store.save()
            except OSError as exc:
                self.store.profile = previous
                self.error(exc)
                return
            self.profile_button.setIcon(
                avatar_icon(self.store.profile.name, self.store.profile.avatar_png)
            )
            self.profile_button.setToolTip(self.store.profile.name + " · Profile and settings")
            if dialog.destination == "settings":
                self.show_settings()
            elif dialog.destination == "history":
                self.show_history()
        dialog.deleteLater()

    def sync_dnd(self) -> None:
        checked = self.store.dnd
        self.dnd_button.blockSignals(True)
        self.dnd_button.setChecked(checked)
        self.dnd_button.blockSignals(False)
        label = "Do Not Disturb: " + (
            "on — click to resume alerts" if checked else "off — click to pause alerts"
        )
        self.dnd_button.setToolTip(label)
        self.dnd_button.setAccessibleName(label)

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
        self.menu_action(menu, "Open app", self.show_window)
        self.menu_action(menu, "Notification history", self.show_history)
        self.startup = QAction("Start with Windows", self)
        self.startup.setCheckable(True)
        self.startup.setEnabled(__import__("sys").platform == "win32")
        try:
            self.startup.setChecked(autostart.enabled())
        except OSError:
            self.notify_status("Windows startup settings could not be read.")
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
        missed = self.history.unopened_counts()
        self.accounts.blockSignals(True)
        self.accounts.clear()
        for service in self.store.services:
            count = max(self.badges.get(service.id, 0), missed.get(service.id, 0))
            tooltip = service.name
            if count:
                tooltip += f" · {count} unread / missed activity"
            if needs_slack_workspace(service):
                tooltip += " · Workspace URL required"
            elif service.id in self.statuses and service.id not in self.views:
                tooltip += " · Sleeping"
            item = QListWidgetItem(badge_icon(symbol_icon(service.kind), count), "")
            item.setSizeHint(QSize(54, 56))
            item.setToolTip(tooltip)
            item.setData(Qt.ItemDataRole.AccessibleTextRole, tooltip)
            item.setData(Qt.ItemDataRole.UserRole, service.id)
            self.accounts.addItem(item)
            if current and current.id == service.id:
                self.accounts.setCurrentItem(item)
        self.accounts.blockSignals(False)
        self.size_account_list()
        total = sum(missed.get(service.id, 0) for service in self.store.services)
        self.history_button.set_count(total)
        label = f"Notifications · {total} missed"
        self.history_button.setToolTip(label)
        self.history_button.setAccessibleName(label)
        unread = sum(
            max(self.badges.get(s.id, 0), missed.get(s.id, 0)) for s in self.store.services
        )
        self.tray.setIcon(badge_icon(app_icon(), unread))
        self.tray.setToolTip(f"All in One Chatapp · {unread} unread / missed activity")
        self.refresh_settings()

    def ensure_view(self, service: Service) -> ServiceView | None:
        if needs_slack_workspace(service):
            return None
        if service.id in self.retiring:
            self.notify_status("Releasing this profile. Try again in a moment.")
            return None
        if service.id not in self.views:
            view = ServiceView(
                service, self.store.profile_path(service.id), self.center.receive, self.stack
            )
            view.app_menu_requested.connect(self.populate_context_menu)
            view.unread_changed.connect(lambda count, sid=service.id: self.unread(sid, count))
            view.status_changed.connect(lambda text, sid=service.id: self.service_status(sid, text))
            self.views[service.id] = view
            self.last_used[service.id] = time.monotonic()
            self.stack.addWidget(view)
        return self.views[service.id]

    def selection_changed(self, _current: Any = None, _previous: Any = None) -> None:
        service = self.current_service()
        self.status.hide()
        if service:
            if needs_slack_workspace(service):
                self.show_slack_setup()
                return
            view = self.ensure_view(service)
            if view:
                self.stack.setCurrentWidget(view)
                self.last_used[service.id] = time.monotonic()
                if self.isVisible() and not self.isMinimized():
                    self.history.mark_service_opened(service.id)
                    self.center.clear_service(service.id)
                self.refresh_accounts()
                self.notify_status(self.statuses.get(service.id, "Loading…"))
        else:
            self.stack.setCurrentWidget(self.welcome)

    def show_slack_setup(self) -> None:
        if self.repair is None:
            self.repair = QWidget()
            layout = QVBoxLayout(self.repair)
            layout.setContentsMargins(48, 40, 48, 40)
            layout.addStretch()
            label = QLabel("Connect your Slack workspace")
            label.setObjectName("heading")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(label)
            hint = QLabel(
                "Enter your team's workspace URL to open Slack here.\n"
                "Your existing account and saved sign-in data will be kept."
            )
            hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
            hint.setWordWrap(True)
            layout.addWidget(hint)
            button = QPushButton("Set workspace URL")
            button.setObjectName("primary")
            button.clicked.connect(self.edit_service)
            layout.addWidget(button, 0, Qt.AlignmentFlag.AlignCenter)
            layout.addStretch()
            self.stack.addWidget(self.repair)
        self.stack.setCurrentWidget(self.repair)

    def service_status(self, service_id: str, text: str) -> None:
        self.statuses[service_id] = text
        current = self.current_service()
        if (
            current
            and current.id == service_id
            and self.stack.currentWidget() is self.views.get(service_id)
        ):
            self.notify_status(text)

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
        if updated.url != service.url and not view:
            self.selection_changed()
        self.refresh_settings()

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
        self.notify_status("This account has been removed.")

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
            self.notify_status("Clearing HTTP cache. Sign-in data is preserved.")

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
        self.sync_dnd()
        self.refresh_settings()

    def toggle_startup(self, checked: bool) -> None:
        try:
            autostart.set_enabled(checked)
        except OSError as exc:
            self.startup.blockSignals(True)
            self.startup.setChecked(not checked)
            self.startup.blockSignals(False)
            self.error(exc)
        else:
            self.startup.blockSignals(True)
            self.startup.setChecked(checked)
            self.startup.blockSignals(False)
        self.refresh_settings()

    def hibernate_idle(self) -> None:
        current = self.current_service()
        for service in self.store.services:
            active = bool(
                current
                and current.id == service.id
                and self.stack.currentWidget() is self.views.get(service.id)
            )
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
        dialog.history_changed.connect(self.refresh_accounts)
        self.center.changed.connect(dialog.refresh)
        dialog.exec()
        self.center.changed.disconnect(dialog.refresh)
        dialog.deleteLater()

    def open_logs(self) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.store.root / "logs")))

    def show_window(self) -> None:
        if self.isMinimized():
            self.showNormal()
        else:
            self.show()
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
