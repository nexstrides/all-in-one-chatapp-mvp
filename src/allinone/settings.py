"""Local profile dialog and application settings page."""

import base64
from collections.abc import Callable

from PySide6.QtCore import QBuffer, QIODevice, QSize, Qt, Signal, SignalInstance
from PySide6.QtGui import QImageReader
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from allinone.icons import avatar_icon, service_icon
from allinone.models import LocalProfile
from allinone.storage import Store
from allinone.theme import THEME_CHOICES


class ProfileDialog(QDialog):
    def __init__(self, profile: LocalProfile, parent: QWidget) -> None:
        super().__init__(parent)
        self.result_profile: LocalProfile | None = None
        self.destination = ""
        self.encoded_avatar = profile.avatar_png
        self.setWindowTitle("Your profile")
        self.setMinimumWidth(420)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)
        self.avatar = QLabel()
        self.avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.avatar)
        self.name = QLineEdit(profile.name)
        self.name.setMaxLength(60)
        self.name.textChanged.connect(self.refresh_avatar)
        form = QFormLayout()
        form.addRow("Display name", self.name)
        layout.addLayout(form)
        photos = QHBoxLayout()
        for title, callback in [
            ("Choose photo…", self.choose_photo),
            ("Use initials", self.clear_photo),
        ]:
            button = QPushButton(title)
            button.clicked.connect(callback)
            photos.addWidget(button)
        layout.addLayout(photos)
        note = QLabel(
            "Your profile stays on this device. Each connected service keeps its own account."
        )
        note.setWordWrap(True)
        note.setObjectName("muted")
        layout.addWidget(note)
        for title, destination in [
            ("App settings", "settings"),
            ("Notification history", "history"),
        ]:
            button = QPushButton(title)
            button.clicked.connect(lambda _checked=False, dest=destination: self.save(dest))
            layout.addWidget(button)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.refresh_avatar()

    def refresh_avatar(self) -> None:
        self.avatar.setPixmap(avatar_icon(self.name.text(), self.encoded_avatar).pixmap(80, 80))

    def clear_photo(self) -> None:
        self.encoded_avatar = ""
        self.refresh_avatar()

    def choose_photo(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose profile photo", "", "Images (*.png *.jpg *.jpeg *.webp)"
        )
        if not path:
            return
        reader = QImageReader(path)
        reader.setAutoTransform(True)
        size = reader.size()
        if not size.isValid() or size.width() * size.height() > 40_000_000:
            QMessageBox.warning(
                self, "Choose another photo", "Choose an image smaller than 40 megapixels."
            )
            return
        reader.setScaledSize(size.scaled(256, 256, Qt.AspectRatioMode.KeepAspectRatio))
        image = reader.read()
        if image.isNull():
            QMessageBox.warning(self, "Choose another photo", "This image could not be opened.")
            return
        side = min(image.width(), image.height())
        image = image.copy((image.width() - side) // 2, (image.height() - side) // 2, side, side)
        image = image.scaled(
            128,
            128,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        buffer = QBuffer()
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        image.save(buffer, "PNG")  # type: ignore[call-overload]  # PySide runtime expects str.
        self.encoded_avatar = base64.b64encode(buffer.data().data()).decode("ascii")
        self.refresh_avatar()

    def save(self, destination: str = "") -> None:
        try:
            self.result_profile = LocalProfile(self.name.text(), self.encoded_avatar)
        except ValueError as exc:
            QMessageBox.warning(self, "Check your profile", str(exc))
            return
        self.destination = destination
        self.accept()


class SettingsPage(QWidget):
    closed = Signal()
    edit_requested = Signal(str)
    remove_requested = Signal(str)
    profile_requested = Signal()
    history_requested = Signal()

    def __init__(
        self,
        store: Store,
        set_dnd: Callable[[bool], None],
        set_startup: Callable[[bool], None],
        set_theme: Callable[[str], None],
        parent: QWidget,
    ) -> None:
        super().__init__(parent)
        self.store = store
        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 28, 36, 28)
        layout.setSpacing(16)
        header = QHBoxLayout()
        title = QLabel("Settings")
        title.setObjectName("heading")
        header.addWidget(title, 1)
        back = QPushButton("Back to conversations")
        back.clicked.connect(self.closed)
        header.addWidget(back)
        layout.addLayout(header)
        subtitle = QLabel("Make this app work your way.")
        subtitle.setObjectName("muted")
        layout.addWidget(subtitle)
        profile = QPushButton("Edit your profile")
        profile.clicked.connect(self.profile_requested)
        layout.addWidget(profile, 0, Qt.AlignmentFlag.AlignLeft)
        self.dnd = QCheckBox("Do Not Disturb — pause alerts except allowed accounts")
        self.dnd.toggled.connect(set_dnd)
        layout.addWidget(self.dnd)
        self.startup = QCheckBox("Start with Windows")
        self.startup.toggled.connect(set_startup)
        layout.addWidget(self.startup)
        appearance = QHBoxLayout()
        appearance.addWidget(QLabel("Appearance"))
        self.theme = QComboBox()
        self.theme.setAccessibleName("Appearance")
        for title, mode in THEME_CHOICES:
            self.theme.addItem(title, mode)
        self.theme.currentIndexChanged.connect(lambda _index: set_theme(self.theme.currentData()))
        appearance.addWidget(self.theme)
        appearance.addStretch()
        layout.addLayout(appearance)
        layout.addWidget(QLabel("Connected accounts"))
        self.accounts = QListWidget()
        self.accounts.setAccessibleName("Accounts in settings")
        self.accounts.setMinimumHeight(120)
        self.accounts.itemActivated.connect(
            lambda item: self.edit_requested.emit(item.data(Qt.ItemDataRole.UserRole))
        )
        layout.addWidget(self.accounts, 1)
        actions = QHBoxLayout()
        self.edit = QPushButton("Account settings")
        self.remove = QPushButton("Remove account…")
        self.edit.clicked.connect(lambda: self.selected(self.edit_requested))
        self.remove.clicked.connect(lambda: self.selected(self.remove_requested))
        actions.addWidget(self.edit)
        actions.addWidget(self.remove)
        actions.addStretch()
        layout.addLayout(actions)
        self.accounts.currentRowChanged.connect(self.update_selection)
        history = QPushButton("Notification history")
        history.clicked.connect(self.history_requested)
        layout.addWidget(history, 0, Qt.AlignmentFlag.AlignLeft)
        note = QLabel(
            "Account settings control notifications, reminders and background activity.\n"
            "Right-click a service icon for reload, cache and account actions."
        )
        note.setWordWrap(True)
        note.setObjectName("muted")
        layout.addWidget(note)

    def selected(self, signal: SignalInstance) -> None:
        item = self.accounts.currentItem()
        if item:
            signal.emit(item.data(Qt.ItemDataRole.UserRole))

    def update_selection(self) -> None:
        selected = self.accounts.currentItem() is not None
        self.edit.setEnabled(selected)
        self.remove.setEnabled(selected)

    def refresh(self, startup: bool, startup_enabled: bool) -> None:
        current = self.accounts.currentItem()
        service_id = current.data(Qt.ItemDataRole.UserRole) if current else None
        self.accounts.clear()
        for service in self.store.services:
            item = QListWidgetItem(service_icon(service.kind), service.name)
            item.setSizeHint(QSize(250, 48))
            item.setData(Qt.ItemDataRole.UserRole, service.id)
            self.accounts.addItem(item)
            if service.id == service_id:
                self.accounts.setCurrentItem(item)
        if self.accounts.currentRow() < 0 and self.accounts.count():
            self.accounts.setCurrentRow(0)
        self.update_selection()
        for checkbox, value in [(self.dnd, self.store.dnd), (self.startup, startup)]:
            checkbox.blockSignals(True)
            checkbox.setChecked(value)
            checkbox.blockSignals(False)
        self.startup.setEnabled(startup_enabled)
        self.theme.blockSignals(True)
        self.theme.setCurrentIndex(max(0, self.theme.findData(self.store.theme)))
        self.theme.blockSignals(False)
