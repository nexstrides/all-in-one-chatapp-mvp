"""One Chromium profile per account; no bridge or injected message reader."""

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QUrl, Signal
from PySide6.QtGui import QContextMenuEvent, QDesktopServices
from PySide6.QtWebEngineCore import (
    QWebEngineNewWindowRequest,
    QWebEngineNotification,
    QWebEnginePage,
    QWebEnginePermission,
    QWebEngineProfile,
    QWebEngineSettings,
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QDialog, QMenu, QVBoxLayout, QWidget

from allinone.models import (
    Service,
    browser_user_agent,
    internal_url,
    signin_rejected,
    start_url,
    unread_from_title,
)


class ServicePage(QWebEnginePage):
    blocked = Signal(str)

    def __init__(self, profile: QWebEngineProfile, service: Service, parent: QWidget) -> None:
        super().__init__(profile, parent)
        self.owner_widget = parent
        self.service = service
        self.popups: list[QDialog] = []
        self.permissionRequested.connect(self.permission_request)
        self.newWindowRequested.connect(self.new_window)
        self.settings().setAttribute(
            QWebEngineSettings.WebAttribute.JavascriptCanAccessClipboard, False
        )
        self.settings().setAttribute(
            QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, False
        )

    def acceptNavigationRequest(
        self, url: QUrl | str, navigation_type: QWebEnginePage.NavigationType, main_frame: bool
    ) -> bool:
        url = QUrl(url)
        if not main_frame:
            return url.scheme() in {"https", "about", "blob", "data"}
        if internal_url(self.service, url.toString()):
            return True
        if (
            url.scheme() == "https"
            and navigation_type == QWebEnginePage.NavigationType.NavigationTypeLinkClicked
        ):
            QDesktopServices.openUrl(url)
        else:
            self.blocked.emit("Navigation outside this service was blocked. Use Open in browser.")
        return False

    def permission_request(self, permission: QWebEnginePermission) -> None:
        if (
            permission.permissionType() == QWebEnginePermission.PermissionType.Notifications
            and self.service.notifications
            and internal_url(self.service, permission.origin().toString(), allow_auth=False)
        ):
            permission.grant()
        else:
            permission.deny()

    def new_window(self, request: QWebEngineNewWindowRequest) -> None:
        url = request.requestedUrl()
        if not request.isUserInitiated():
            self.blocked.emit("Automatic popup blocked.")
            return
        if internal_url(self.service, url.toString()):
            dialog = QDialog(self.owner_widget)
            dialog.setWindowTitle("Sign in — " + self.service.name)
            dialog.resize(620, 760)
            layout = QVBoxLayout(dialog)
            view = QWebEngineView(dialog)
            page = ServicePage(self.profile(), self.service, view)
            page.windowCloseRequested.connect(dialog.close)
            page.blocked.connect(self.blocked)
            view.setPage(page)
            layout.addWidget(view)
            self.popups.append(dialog)
            dialog.finished.connect(lambda _result: self.close_popup(dialog))
            request.openIn(page)
            dialog.show()
        elif url.scheme() == "https":
            QDesktopServices.openUrl(url)

    def close_popup(self, dialog: QDialog) -> None:
        if dialog in self.popups:
            self.popups.remove(dialog)
            dialog.deleteLater()

    def close_popups(self) -> None:
        for dialog in self.popups[:]:
            dialog.close()


class ServiceView(QWebEngineView):
    unread_changed = Signal(int)
    status_changed = Signal(str)
    app_menu_requested = Signal(QMenu)

    def __init__(
        self,
        service: Service,
        root: Path,
        presenter: Callable[[Service, QWebEngineNotification], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.service = service
        self.disposing = False
        self.account_profile = QWebEngineProfile("svc-" + service.id, self)
        self.account_profile.setPersistentStoragePath(str(root / "storage"))
        self.account_profile.setCachePath(str(root / "cache"))
        self.account_profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.DiskHttpCache)
        self.account_profile.setPersistentCookiesPolicy(
            QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies
        )
        self.account_profile.setPersistentPermissionsPolicy(
            QWebEngineProfile.PersistentPermissionsPolicy.AskEveryTime
        )
        # Push uses Qt's FCM transport; notifications still depend on provider/OS support.
        self.account_profile.setPushServiceEnabled(True)
        # Google rejects embedded-browser identities, so drop the QtWebEngine token. An
        # explicit per-account override always wins.
        self.account_profile.setHttpUserAgent(
            service.user_agent or browser_user_agent(self.account_profile.httpUserAgent())
        )
        self.account_profile.setNotificationPresenter(lambda n: presenter(service, n))
        self.account_profile.downloadRequested.connect(lambda download: download.cancel())
        self.service_page = ServicePage(self.account_profile, service, self)
        self.service_page.blocked.connect(self.status_changed)
        self.setPage(self.service_page)
        self.last_unread = -1
        self.titleChanged.connect(self.title_changed)
        self.loadStarted.connect(lambda: self.status_changed.emit("Loading…"))
        self.loadFinished.connect(
            lambda ok: self.status_changed.emit(
                "Connected" if ok else "Page did not load. Reload or open in your browser."
            )
        )
        self.urlChanged.connect(self.url_changed)
        self.service_page.renderProcessTerminated.connect(
            lambda _status, _code: self.status_changed.emit(
                "Service stopped. Select Reload to recover."
            )
        )
        self.load(QUrl(start_url(service)))

    def url_changed(self, url: QUrl) -> None:
        if signin_rejected(url.toString()):
            self.status_changed.emit(
                "Google declined this sign-in. Use Open in browser to check the account, "
                "or add a user agent override in account settings."
            )

    def title_changed(self, title: str) -> None:
        # Pages rewrite their title constantly; only a changed count may touch the UI.
        count = unread_from_title(title)
        if count != self.last_unread:
            self.last_unread = count
            self.unread_changed.emit(count)

    def clear_cache(self) -> None:
        self.account_profile.clearHttpCache()

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        menu = self.createStandardContextMenu()
        menu.addSeparator()
        self.app_menu_requested.emit(menu)
        menu.exec(event.globalPos())
        menu.deleteLater()

    def dispose(self, finished: Callable[[], None] | None = None) -> None:
        if self.disposing:
            return
        self.disposing = True
        self.stop()
        self.hide()
        self.service_page.close_popups()
        # Qt requires every page to die before its profile.
        self.service_page.destroyed.connect(self.account_profile.deleteLater)
        self.account_profile.destroyed.connect(self.deleteLater)
        if finished:
            self.account_profile.destroyed.connect(finished)
        self.service_page.deleteLater()
