"""Compact accessible sidebar controls."""

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon, QResizeEvent
from PySide6.QtWidgets import QLabel, QPushButton, QWidget


class IconButton(QPushButton):
    def __init__(self, label: str, icon: QIcon, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("iconButton")
        self.setFixedSize(52, 52)
        self.setIconSize(QSize(30, 30))
        self.setIcon(icon)
        self.setToolTip(label)
        self.setAccessibleName(label)
        self.badge = QLabel(self)
        self.badge.setObjectName("notificationBadge")
        self.badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.badge.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.badge.hide()

    def set_count(self, count: int) -> None:
        self.badge.setText(str(count) if count < 100 else "99+")
        self.badge.setFixedSize(24 if count < 100 else 30, 20)
        self.badge.move(self.width() - self.badge.width(), 0)
        self.badge.setVisible(count > 0)

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self.badge.move(self.width() - self.badge.width(), 0)
