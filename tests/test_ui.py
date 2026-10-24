"""Offline Qt smoke test; real-provider tests belong to the Windows checklist."""

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def test_empty_window_and_add_dialog(tmp_path):
    from PySide6.QtWidgets import QApplication

    from allinone.dialogs import ServiceDialog
    from allinone.main_window import MainWindow
    from allinone.storage import History, Store

    app = QApplication.instance() or QApplication([])
    store = Store(tmp_path)
    history = History(tmp_path / "history.sqlite3")
    window = MainWindow(store, history)
    window.show()
    app.processEvents()
    assert window.accounts.count() == 0
    assert window.stack.count() == 1
    dialog = ServiceDialog(window)
    dialog.name.setText("My Telegram")
    dialog.kind.setCurrentIndex(dialog.kind.findData("telegram"))
    dialog.save()
    assert dialog.result_service.kind == "telegram"
    window.set_dnd(True)
    assert Store(tmp_path).dnd
    window.center.shutdown()
    window.tray.hide()
    window.idle_timer.stop()
    window.deleteLater()
    app.processEvents()
    history.close()


@pytest.mark.skipif(os.environ.get("RUN_WEBENGINE_TESTS") != "1", reason="Opt-in WebEngine smoke")
def test_profile_paths_and_disposal(tmp_path):
    from PySide6.QtCore import QCoreApplication, QEvent
    from PySide6.QtWidgets import QApplication

    from allinone.models import Service
    from allinone.service_view import ServiceView

    app = QApplication.instance() or QApplication([])
    a = Service("A", "https://example.invalid")
    b = Service("B", "https://example.invalid")
    views = [ServiceView(s, tmp_path / s.id, lambda *_: None) for s in (a, b)]
    for view in views:
        view.stop()
    assert views[0].account_profile.storageName() != views[1].account_profile.storageName()
    assert views[0].account_profile.persistentStoragePath() != (
        views[1].account_profile.persistentStoragePath()
    )
    done = []
    for view in views:
        view.dispose(lambda: done.append(True))
    for _ in range(10):
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        app.processEvents()
    assert len(done) == 2
