"""Locally drawn vector icons: no network fetches, tracking, brand logos or emoji fonts.

Every icon is painted at twice its logical size with a device pixel ratio so it stays
crisp on high-DPI screens, and results are cached so refreshing the sidebar is cheap.
"""

import base64
from functools import lru_cache

from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QIcon,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPixmap,
)
from PySide6.QtSvg import QSvgRenderer

RATIO = 2
SIZE = 64

# Generic 24x24 outline glyphs, drawn for this app (not copies of any provider's logo).
GLYPHS = {
    "chat": (
        '<path d="M6 4h12a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2h-6l-4.5 4v-4H6a2 2 0 0 1-2-2V6a2 2 0 0 '
        '1 2-2z"/><path d="M8.5 10h7M8.5 13h4"/>'
    ),
    "plane": '<path d="M21 3L3 9.5l7.5 3L14.5 21z"/><path d="M21 3L10.5 12.5"/>',
    "hash": '<path d="M5 9h14M5 15h14M10 4L8 20M16 4l-2 16"/>',
    "gamepad": (
        '<path d="M7 8h10a4 4 0 0 1 4 4v2a3 3 0 0 1-5.2 2L14.5 15h-5l-1.3 1A3 3 0 0 1 3 14v-2a4 '
        '4 0 0 1 4-4z"/><path d="M8 10.5v3M6.5 12h3"/>'
        '<circle cx="15.5" cy="11.2" r="0.7"/><circle cx="17.5" cy="13" r="0.7"/>'
    ),
    "mail": (
        '<path d="M4 6h16a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1z"/>'
        '<path d="M3.5 7.5L12 13l8.5-5.5"/>'
    ),
    "inbox": (
        '<path d="M4 13l2-7h12l2 7v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1z"/>'
        '<path d="M4 13h4l1 2h6l1-2h4"/>'
    ),
    "globe": (
        '<circle cx="12" cy="12" r="9"/><ellipse cx="12" cy="12" rx="4" ry="9"/>'
        '<path d="M3 12h18"/>'
    ),
    "add": '<path d="M12 5v14M5 12h14"/>',
    "bell": '<path d="M6 16V11a6 6 0 0 1 12 0v5l1.5 2h-15z"/><path d="M10 21h4"/>',
    "moon": '<path d="M20 14A8 8 0 0 1 10 4a8 8 0 1 0 10 10z"/>',
    "settings": (
        '<path d="M4 8h9M17 8h3M4 16h3M11 16h9"/>'
        '<circle cx="15" cy="8" r="2"/><circle cx="9" cy="16" r="2"/>'
    ),
    "profile": '<circle cx="12" cy="8" r="4"/><path d="M4 21v-2a8 8 0 0 1 16 0v2"/>',
}

# kind: (glyph, gradient top, gradient bottom)
TILES = {
    "whatsapp": ("chat", "#3acb82", "#1c9f5f"),
    "telegram": ("plane", "#3cb9f2", "#2090d6"),
    "slack": ("hash", "#8f5aa8", "#5b2d72"),
    "discord": ("gamepad", "#7e88f7", "#5360ef"),
    "gmail": ("mail", "#f5685c", "#d63a2c"),
    "outlook": ("inbox", "#3294e6", "#0f68b8"),
    "custom": ("globe", "#8d96ab", "#5c657b"),
}

LINE_COLORS = {"light": "#4a5165", "dark": "#c9cee0"}
_scheme = "light"


def set_scheme(scheme: str) -> None:
    """Line icons (bell, moon, ...) follow the active theme; service tiles do not."""
    global _scheme
    _scheme = scheme if scheme in LINE_COLORS else "light"


def _canvas() -> tuple[QPixmap, QPainter]:
    pixmap = QPixmap(SIZE * RATIO, SIZE * RATIO)
    pixmap.setDevicePixelRatio(RATIO)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    return pixmap, painter


def _glyph(painter: QPainter, name: str, color: str, target: QRectF, width: float = 1.9) -> None:
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        f'stroke="{color}" stroke-width="{width}" stroke-linecap="round" '
        f'stroke-linejoin="round">{GLYPHS[name]}</svg>'
    )
    QSvgRenderer(QByteArray(svg.encode())).render(painter, target)


def _count_badge(painter: QPainter, count: int) -> None:
    text = str(count) if count < 100 else "99+"
    width = 26 if count < 10 else 34
    rect = QRectF(SIZE - width, 0, width, 24)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#e5484d"))
    painter.drawRoundedRect(rect, 12, 12)
    font = QFont()
    font.setPixelSize(14)
    font.setBold(True)
    painter.setFont(font)
    painter.setPen(QColor("#ffffff"))
    painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)


def _tile(top: str, bottom: str, glyph: str, count: int = 0) -> QIcon:
    pixmap, painter = _canvas()
    gradient = QLinearGradient(0, 4, 0, 60)
    gradient.setColorAt(0, QColor(top))
    gradient.setColorAt(1, QColor(bottom))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(gradient)
    painter.drawRoundedRect(QRectF(4, 4, 56, 56), 17, 17)
    _glyph(painter, glyph, "#ffffff", QRectF(15, 15, 34, 34), 1.8)
    if count:
        _count_badge(painter, count)
    painter.end()
    return QIcon(pixmap)


@lru_cache(maxsize=128)
def service_icon(kind: str, count: int = 0) -> QIcon:
    glyph, top, bottom = TILES.get(kind, TILES["custom"])
    return _tile(top, bottom, glyph, min(count, 100))


@lru_cache(maxsize=16)
def app_icon(count: int = 0) -> QIcon:
    return _tile("#8383f5", "#4c4cd1", "chat", min(count, 100))


@lru_cache(maxsize=64)
def _line_icon(name: str, color: str) -> QIcon:
    pixmap, painter = _canvas()
    _glyph(painter, name, color, QRectF(10, 10, 44, 44), 1.7)
    painter.end()
    return QIcon(pixmap)


def symbol_icon(name: str, color: str | None = None) -> QIcon:
    if name in TILES:
        return service_icon(name)
    if name not in GLYPHS:
        return service_icon("custom")
    return _line_icon(name, color or LINE_COLORS[_scheme])


def avatar_icon(name: str, encoded: str = "") -> QIcon:
    pixmap, painter = _canvas()
    painter.setPen(Qt.PenStyle.NoPen)
    gradient = QLinearGradient(0, 0, SIZE, SIZE)
    gradient.setColorAt(0, QColor("#c9c9fb"))
    gradient.setColorAt(1, QColor("#9d9df0"))
    painter.setBrush(gradient)
    painter.drawEllipse(QRectF(2, 2, 60, 60))
    image = QPixmap()
    if encoded and image.loadFromData(base64.b64decode(encoded), "PNG"):
        clip = QPainterPath()
        clip.addEllipse(QRectF(2, 2, 60, 60))
        painter.setClipPath(clip)
        painter.drawPixmap(QRectF(2, 2, 60, 60), image, QRectF(image.rect()))
    else:
        painter.setPen(QColor("#2f2f84"))
        font = QFont()
        font.setPixelSize(24)
        font.setBold(True)
        painter.setFont(font)
        initials = "".join(part[0] for part in name.split()[:2]).upper() or "ME"
        painter.drawText(QRectF(0, 0, SIZE, SIZE), Qt.AlignmentFlag.AlignCenter, initials)
    painter.end()
    return QIcon(pixmap)
