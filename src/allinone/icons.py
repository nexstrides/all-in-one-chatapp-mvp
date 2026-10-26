"""Bundled vector symbols: no network fetches, tracking, or platform emoji fonts."""

import base64

from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPixmap
from PySide6.QtSvg import QSvgRenderer

SYMBOLS = {
    "add": '<path d="M12 5v14M5 12h14"/>',
    "bell": '<path d="M5 17h14l-2-3V9a5 5 0 0 0-10 0v5l-2 3zM10 20h4"/>',
    "moon": '<path d="M20 14A8 8 0 0 1 10 4a8 8 0 1 0 10 10z"/>',
    "settings": (
        '<path d="M4 7h16M4 17h16"/>'
        '<circle cx="9" cy="7" r="3" fill="#fff"/>'
        '<circle cx="15" cy="17" r="3" fill="#fff"/>'
    ),
    "profile": '<circle cx="12" cy="8" r="4"/><path d="M4 21v-2a8 8 0 0 1 16 0v2"/>',
    "custom": (
        '<circle cx="12" cy="12" r="9"/>'
        '<ellipse cx="12" cy="12" rx="4" ry="9"/>'
        '<path d="M3 12h18"/>'
    ),
    "whatsapp": (
        '<path d="M5 18l-2 4 5-2a9 9 0 1 0-3-2z"/>'
        '<path d="M8 7c-2 5 4 10 8 8l-2-3-2 1-2-3 1-1-3-2z"/>'
    ),
    "telegram": '<path d="M2 10l20-7-5 19-6-7-4 3 1-6 10-6-7 9"/>',
    "slack": (
        '<path stroke="#36c5f0" d="M4 9h7M9 3v3"/>'
        '<path stroke="#2eb67d" d="M15 3v8M19 9h2"/>'
        '<path stroke="#ecb22e" d="M13 15h8M15 19v2"/>'
        '<path stroke="#e01e5a" d="M9 13v8M3 15h2"/>'
    ),
    "discord": (
        '<path d="M6 6l4-1 1 2h2l1-2 4 1 3 12-5 2-2-3h-4l-2 3-5-2z"/>'
        '<circle cx="8" cy="12" r="1"/>'
        '<circle cx="16" cy="12" r="1"/>'
    ),
    "gmail": (
        '<path d="M3 19V5l9 7 9-7v14"/>'
        '<path stroke="#4285f4" d="M3 9v10"/>'
        '<path stroke="#34a853" d="M21 9v10"/>'
    ),
    "outlook": (
        '<path d="M10 6h11v14H9M11 10l5 4 5-4"/>'
        '<path fill="#167ad0" d="M2 4l10-2v20L2 20z"/>'
        '<ellipse stroke="#fff" cx="7" cy="12" rx="2.2" ry="3.3"/>'
    ),
}
COLORS = {
    "whatsapp": "#20a56b",
    "telegram": "#249bd7",
    "slack": "#663d73",
    "discord": "#5865f2",
    "gmail": "#d94c42",
    "outlook": "#167ad0",
}


def symbol_icon(name: str, color: str = "#685a7c") -> QIcon:
    symbol = SYMBOLS.get(name, SYMBOLS["custom"])
    color = COLORS.get(name, color)
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
        f'fill="none" stroke="{color}" stroke-width="1.8" stroke-linecap="round" '
        f'stroke-linejoin="round">{symbol}</svg>'
    )
    renderer = QSvgRenderer(QByteArray(svg.encode()))
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter, QRectF(6, 6, 52, 52))
    painter.end()
    return QIcon(pixmap)


def badge_icon(icon: QIcon, count: int) -> QIcon:
    pixmap = icon.pixmap(64, 64)
    if count:
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#dc354f"))
        rect = QRectF(29, 0, 35, 25)
        painter.drawRoundedRect(rect, 12, 12)
        painter.setPen(QColor("white"))
        font = painter.font()
        font.setPixelSize(14)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, str(count) if count < 100 else "99+")
        painter.end()
    return QIcon(pixmap)


def avatar_icon(name: str, encoded: str = "") -> QIcon:
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#e7def6"))
    painter.drawEllipse(2, 2, 60, 60)
    image = QPixmap()
    if encoded and image.loadFromData(base64.b64decode(encoded), "PNG"):
        clip = QPainterPath()
        clip.addEllipse(2, 2, 60, 60)
        painter.setClipPath(clip)
        painter.drawPixmap(2, 2, 60, 60, image)
    else:
        painter.setPen(QColor("#6345a1"))
        font = painter.font()
        font.setPixelSize(24)
        font.setBold(True)
        painter.setFont(font)
        initials = "".join(part[0] for part in name.split()[:2]).upper() or "ME"
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, initials)
    painter.end()
    return QIcon(pixmap)
