"""Keyboard-accessible account editing and metadata-only history."""

from datetime import datetime

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from allinone.models import PRESETS, Service, slack_workspace_url
from allinone.storage import History


class ServiceDialog(QDialog):
    def __init__(self, parent: QWidget, service: Service | None = None) -> None:
        super().__init__(parent)
        self.service = service
        self.result_service: Service | None = None
        self.setWindowTitle("Service settings" if service else "Add a service")
        self.setMinimumWidth(480)
        form = QFormLayout(self)
        self.kind = QComboBox()
        for key, preset in PRESETS.items():
            self.kind.addItem(preset["name"], key)
        self.kind.addItem("Custom HTTPS service", "custom")
        self.name = QLineEdit()
        self.url = QLineEdit()
        self.url_label = QLabel("HTTPS URL")
        self.workspace_hint = QLabel(
            "Enter your team's Slack URL. Sign in inside the app, then choose "
            "Use Slack in your browser if Slack offers to launch its desktop app."
        )
        self.workspace_hint.setWordWrap(True)
        self.notifications = QCheckBox("Receive notifications")
        self.always_on = QCheckBox("Keep service running in the background")
        self.sticky = QCheckBox("Show a persistent in-app alert")
        self.bypass = QCheckBox("Allow through app Do Not Disturb")
        self.reminder = QSpinBox()
        self.reminder.setRange(0, 1440)
        self.reminder.setSuffix(" minutes")
        self.reminder.setSpecialValueText("Off")
        self.agent = QLineEdit()
        self.agent.setPlaceholderText("Default Qt browser identity")
        for label, widget in [
            ("Service", self.kind),
            ("Account name", self.name),
            ("", self.url),
            ("Notifications", self.notifications),
            ("Background", self.always_on),
            ("Important", self.sticky),
            ("Do Not Disturb", self.bypass),
            ("Remind until opened", self.reminder),
            ("User agent override", self.agent),
        ]:
            if widget is self.url:
                form.addRow(self.url_label, widget)
            else:
                form.addRow(label, widget)
        form.addRow(self.workspace_hint)
        note = QLabel(
            "To allow hibernation after 15 idle minutes, turn off notifications, "
            "background running, persistent alerts and reminders. Sleeping services "
            "cannot deliver notifications. Windows Focus Assist still applies."
        )
        note.setWordWrap(True)
        form.addRow(note)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)
        self.kind.currentIndexChanged.connect(self.preset_changed)
        if service:
            self.kind.setCurrentIndex(self.kind.findData(service.kind))
            self.kind.setEnabled(False)
            self.url.setEnabled(service.kind == "slack")
            self.name.setText(service.name)
            self.url.setText(service.url)
            self.notifications.setChecked(service.notifications)
            self.always_on.setChecked(service.always_on)
            self.sticky.setChecked(service.sticky)
            self.bypass.setChecked(service.bypass_dnd)
            self.reminder.setValue(service.reminder_minutes)
            self.agent.setText(service.user_agent)
        else:
            self.notifications.setChecked(True)
            self.always_on.setChecked(True)
            self.preset_changed()
        self.workspace_hint.setVisible(self.kind.currentData() == "slack")

    def preset_changed(self) -> None:
        preset = PRESETS.get(self.kind.currentData(), {})
        is_slack = self.kind.currentData() == "slack"
        self.url_label.setText("Workspace URL" if is_slack else "HTTPS URL")
        self.workspace_hint.setVisible(is_slack)
        self.url.setPlaceholderText("https://your-team.slack.com" if is_slack else "https://")
        self.name.setText(preset.get("name", ""))
        self.url.setText("" if is_slack else preset.get("url", "https://"))

    def save(self) -> None:
        data = {
            "name": self.name.text(),
            "url": self.url.text(),
            "kind": self.kind.currentData(),
            "notifications": self.notifications.isChecked(),
            "always_on": self.always_on.isChecked(),
            "sticky": self.sticky.isChecked(),
            "bypass_dnd": self.bypass.isChecked(),
            "reminder_minutes": self.reminder.value(),
            "user_agent": self.agent.text(),
        }
        if self.service:
            data["id"] = self.service.id
        try:
            if data["kind"] == "slack":
                data["url"] = slack_workspace_url(str(data["url"]))
            self.result_service = Service(**data)
        except ValueError as exc:
            QMessageBox.warning(self, "Check service details", str(exc))
            return
        self.accept()


class HistoryDialog(QDialog):
    selected_service = Signal(str)

    def __init__(self, history: History, parent: QWidget) -> None:
        super().__init__(parent)
        self.history = history
        self.setWindowTitle("Notification history")
        self.resize(640, 480)
        layout = QVBoxLayout(self)
        label = QLabel("Last 90 days · service and time only · message content is never saved")
        label.setWordWrap(True)
        layout.addWidget(label)
        self.query = QLineEdit()
        self.query.setPlaceholderText("Search account names…")
        self.query.textChanged.connect(self.refresh)
        layout.addWidget(self.query)
        self.rows = QListWidget()
        self.rows.itemActivated.connect(self.open_item)
        layout.addWidget(self.rows)
        clear = QPushButton("Clear history")
        clear.clicked.connect(self.clear)
        layout.addWidget(clear)
        self.refresh()

    def refresh(self) -> None:
        self.rows.clear()
        for row in self.history.search(self.query.text()):
            date = datetime.fromtimestamp(row["created"]).strftime("%b %d, %H:%M")
            state = "Opened" if row["opened"] else "New activity"
            item = QListWidgetItem(f"{row['service_name']}  ·  {date}  ·  {state}")
            item.setData(Qt.ItemDataRole.UserRole, (row["id"], row["service_id"]))
            self.rows.addItem(item)

    def open_item(self, item: QListWidgetItem) -> None:
        item_id, service_id = item.data(Qt.ItemDataRole.UserRole)
        self.history.mark_opened(item_id)
        self.selected_service.emit(service_id)
        self.refresh()

    def clear(self) -> None:
        if (
            QMessageBox.question(
                self, "Clear history?", "Delete all locally stored notification metadata?"
            )
            == QMessageBox.StandardButton.Yes
        ):
            self.history.clear()
            self.refresh()
