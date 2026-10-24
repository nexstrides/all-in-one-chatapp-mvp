import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def test_notification_routing_dnd_and_cancellation(tmp_path):
    from PySide6.QtCore import QObject, Signal
    from PySide6.QtWidgets import QApplication, QWidget

    from allinone.models import Service
    from allinone.notifications import NotificationCenter
    from allinone.storage import History

    app = QApplication.instance() or QApplication([])
    parent = QWidget()
    history = History(tmp_path / "history.sqlite3")

    class FakeNotification(QObject):
        closed = Signal()

        def __init__(self):
            super().__init__()
            self.clicked = False

        def close(self):
            self.closed.emit()

        def click(self):
            self.clicked = True

    class Center(NotificationCenter):
        def display(self, item_id):
            self.displayed.append(item_id)

    center = Center(history, parent)
    center.displayed = []
    focused = []
    center.focus_service.connect(focused.append)
    a, b = (Service(name, "https://example.test") for name in ("A", "B"))
    first, second = FakeNotification(), FakeNotification()
    center.receive(a, first)
    center.receive(b, second)
    ids = list(center.pending)
    center.activate(ids[1])
    center.activate(ids[0])
    assert focused == [b.id, a.id]
    assert first.clicked and second.clicked
    assert not center.pending
    assert all(row["opened"] for row in history.search())
    center.dnd = True
    center.receive(a, FakeNotification())
    assert len(center.displayed) == 2
    assert not center.pending
    center.dnd = False
    third = FakeNotification()
    center.receive(a, third)
    assert center.pending
    third.close()
    assert not center.pending
    assert len(history.search()) == 4
    center.shutdown()
    history.close()
    parent.deleteLater()
    app.processEvents()
