"""Compact accessible sidebar controls."""

from PySide6.QtCore import QEnterEvent, QEvent, QRectF, QSize, Qt, QVariantAnimation
from PySide6.QtGui import QColor, QIcon, QPainter, QPaintEvent, QResizeEvent
from PySide6.QtWidgets import QLabel, QPushButton, QWidget

from allinone import theme


class IconButton(QPushButton):
    """Icon-only button with a short fade on hover; the badge never intercepts clicks."""

    def __init__(self, label: str, icon: QIcon, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("iconButton")
        self.setFixedSize(52, 52)
        self.setIconSize(QSize(34, 34))
        self.setIcon(icon)
        self.setToolTip(label)
        self.setAccessibleName(label)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.hover = 0.0
        self.fade = QVariantAnimation(self)
        self.fade.setDuration(140)
        self.fade.valueChanged.connect(self.set_hover)
        self.badge = QLabel(self)
        self.badge.setObjectName("notificationBadge")
        self.badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.badge.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.badge.hide()

    def set_hover(self, value: float) -> None:
        self.hover = float(value)
        self.update()

    def animate_to(self, target: float) -> None:
        self.fade.stop()
        self.fade.setStartValue(self.hover)
        self.fade.setEndValue(target)
        self.fade.start()

    def enterEvent(self, event: QEnterEvent) -> None:
        super().enterEvent(event)
        self.animate_to(1.0)

    def leaveEvent(self, event: QEvent) -> None:
        super().leaveEvent(event)
        self.animate_to(0.0)

    def paintEvent(self, event: QPaintEvent) -> None:
        if self.hover > 0.01 and not self.isChecked():
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            color = QColor(theme.palette()["hover"])
            color.setAlphaF(self.hover)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            painter.drawRoundedRect(QRectF(self.rect()).adjusted(1, 1, -1, -1), 16, 16)
            painter.end()
        super().paintEvent(event)

    def set_count(self, count: int) -> None:
        text = str(count) if count < 100 else "99+"
        if self.badge.text() != text:
            self.badge.setText(text)
            self.badge.setFixedSize(24 if count < 100 else 30, 20)
            self.badge.move(self.width() - self.badge.width(), 0)
        self.badge.setVisible(count > 0)

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self.badge.move(self.width() - self.badge.width(), 0)
