"""Exercise the desktop shell offline, without provider sign-in or network requests."""

import base64
from dataclasses import replace
from types import SimpleNamespace

import pytest
from PySide6.QtCore import QCoreApplication, QEvent, Qt, Signal
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication, QFileDialog, QMenu, QMenuBar, QWidget

from allinone.dialogs import ServiceDialog
from allinone.main_window import MainWindow
from allinone.models import PRESETS, LocalProfile, Service
from allinone.settings import ProfileDialog
from allinone.storage import History, Store


class OfflineView(QWidget):
    unread_changed = Signal(int)
    status_changed = Signal(str)
    app_menu_requested = Signal(QMenu)

    def __init__(self, service, root, presenter, parent):
        super().__init__(parent)
        self.service = service
        self.root = root
        self.service_page = SimpleNamespace(service=service)
        self.account_profile = SimpleNamespace(setNotificationPresenter=lambda callback: None)

    def dispose(self, finished=None):
        self.deleteLater()
        if finished:
            finished()

    def reload(self):
        pass


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def shell(app, tmp_path, monkeypatch):
    monkeypatch.setattr("allinone.main_window.ServiceView", OfflineView)
    store = Store(tmp_path)
    history = History(tmp_path / "history.sqlite3")
    window = MainWindow(store, history)
    window.show()
    app.processEvents()
    yield window
    window.center.shutdown()
    window.tray.hide()
    window.idle_timer.stop()
    for sid in list(window.views):
        window.retire(sid)
    window.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    app.processEvents()
    history.close()


def add(window, kind="telegram", url=None):
    recipe = PRESETS[kind]
    service = Service(recipe["name"], url or recipe["url"], kind=kind)
    window.store.add(service)
    window.refresh_accounts()
    window.accounts.setCurrentRow(window.accounts.count() - 1)
    return service


def test_icon_rail_and_full_content_area(shell, app):
    add(shell)
    app.processEvents()
    assert not shell.findChildren(QMenuBar)
    assert shell.accounts.item(0).text() == ""
    assert not shell.accounts.item(0).icon().isNull()
    assert "Telegram" in shell.accounts.item(0).data(Qt.ItemDataRole.AccessibleTextRole)
    assert shell.sidebar.width() == 80
    assert shell.stack.x() == 80
    assert shell.stack.y() == 0
    assert shell.stack.width() == shell.centralWidget().width() - 80
    assert shell.stack.height() == shell.centralWidget().height()
    assert shell.add_button.y() >= shell.accounts.y() + shell.accounts.height()
    assert shell.add_button.y() - shell.accounts.geometry().bottom() < 16
    assert shell.history_button.text() == shell.dnd_button.text() == ""
    shell.show_settings()
    shell.accounts.itemClicked.emit(shell.accounts.item(0))
    assert shell.stack.currentWidget() is shell.views[shell.store.services[0].id]


def test_context_actions_and_settings_dnd(shell):
    add(shell)
    menu = QMenu()
    shell.populate_context_menu(menu)
    assert {"Account settings…", "App settings…", "Reload service"} <= {
        a.text() for a in menu.actions()
    }
    shell.show_settings()
    shell.settings_page.dnd.setChecked(True)
    assert shell.store.dnd and shell.dnd_button.isChecked() and shell.center.dnd
    shell.dnd_button.click()
    assert not shell.store.dnd and not shell.settings_page.dnd.isChecked()
    assert not Store(shell.store.root).dnd


def test_badges_persist_clear_per_account_and_keep_title_unread(shell):
    a = add(shell)
    b = add(shell, "gmail")
    shell.history.record(a)
    shell.history.record(a)
    shell.history.record(b)
    shell.center.changed.emit()
    assert shell.history_button.badge.text() == "3"
    assert not shell.history_button.badge.isHidden()
    shell.badges[a.id] = 5
    shell.focus_service(a.id)
    assert shell.history.unopened_counts() == {b.id: 1}
    assert shell.history_button.badge.text() == "1"
    assert "5 unread" in shell.accounts.currentItem().toolTip()
    shell.history.clear()
    shell.refresh_accounts()
    assert shell.history_button.badge.isHidden()


def test_hidden_start_does_not_clear_missed_notifications(shell):
    a = add(shell)
    shell.history.record(a)
    shell.hide()
    shell.selection_changed()
    assert shell.history.unopened_counts() == {a.id: 1}


def test_legacy_slack_setup_and_edit_preserves_profile(shell, monkeypatch):
    service = add(shell, "slack")
    assert service.id not in shell.views
    assert shell.stack.currentWidget() is shell.repair
    updated = replace(service, url="https://acme.slack.com/")
    monkeypatch.setattr(
        ServiceDialog,
        "exec",
        lambda dialog: (
            setattr(dialog, "result_service", updated) or ServiceDialog.DialogCode.Accepted
        ),
    )
    shell.edit_service()
    assert shell.views[service.id].service.url == updated.url
    profile_root = shell.views[service.id].root
    updated = replace(updated, url="https://second.slack.com/")
    shell.edit_service()
    assert shell.views[service.id].service.url == updated.url
    assert shell.views[service.id].root == profile_root
    restored = Store(shell.store.root)
    assert restored.services[0].id == service.id
    assert restored.services[0].url == updated.url


def test_slack_add_dialog_requires_workspace_and_normalizes_url(shell):
    dialog = ServiceDialog(shell)
    dialog.kind.setCurrentIndex(dialog.kind.findData("slack"))
    assert dialog.url.text() == ""
    assert dialog.url_label.text() == "Workspace URL"
    dialog.url.setText("acme.slack.com")
    dialog.save()
    assert dialog.result_service.url == "https://acme.slack.com/"
    edit = ServiceDialog(shell, dialog.result_service)
    assert edit.url.isEnabled()
    assert edit.service.id == dialog.result_service.id


def test_profile_photo_is_copied_and_profile_survives_restart(shell, tmp_path, monkeypatch):
    image_path = tmp_path / "test.png"
    image = QImage(64, 32, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.blue)
    image.save(str(image_path))
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *args: (str(image_path), "PNG"))
    dialog = ProfileDialog(shell.store.profile, shell)
    dialog.name.setText("My work")
    dialog.choose_photo()
    dialog.save()
    shell.store.profile = dialog.result_profile
    shell.store.save()
    image_path.unlink()
    profile = Store(shell.store.root).profile
    assert profile.name == "My work"
    assert base64.b64decode(profile.avatar_png).startswith(b"\x89PNG")
    dialog.clear_photo()
    dialog.save()
    assert dialog.result_profile.avatar_png == ""


def test_profile_validation():
    for kwargs in [{"name": ""}, {"avatar_png": "not base64"}, {"avatar_png": "YQ=="}]:
        with pytest.raises(ValueError):
            LocalProfile(**kwargs)
