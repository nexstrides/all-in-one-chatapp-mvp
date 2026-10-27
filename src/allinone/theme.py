"""Light and dark design tokens, Qt palette and stylesheet rendering."""

import re
from importlib.resources import files

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QColor, QGuiApplication, QPalette
from PySide6.QtWidgets import QApplication

from allinone import icons
from allinone.models import THEME_MODES

THEME_CHOICES = (("Match Windows", "system"), ("Light", "light"), ("Dark", "dark"))

# Every token must exist in both palettes; tests enforce this against theme.qss.
PALETTES: dict[str, dict[str, str]] = {
    "light": {
        "bg": "#f6f7fb",
        "surface": "#ffffff",
        "rail": "#eceef6",
        "border": "#e1e4ee",
        "text": "#1f2433",
        "text2": "#454c60",
        "muted": "#667089",
        "accent": "#5b5bd6",
        "accent_soft": "#e4e4fa",
        "accent_text": "#3a3aa8",
        "btn_bg": "#5b5bd6",
        "btn_hover": "#4a4ac4",
        "on_accent": "#ffffff",
        "hover": "#e8eaf4",
        "focus": "#5b5bd6",
        "danger": "#d93a4f",
        "notice_bg": "#fff7e0",
        "notice_text": "#614b13",
        "notice_border": "#ecd58a",
        "tip_bg": "#1f2433",
        "tip_text": "#ffffff",
        "scroll": "#c3c8d8",
        "input_bg": "#ffffff",
        "input_border": "#d3d7e5",
        "disabled_text": "#99a0b3",
        "disabled_bg": "#eff0f5",
    },
    "dark": {
        "bg": "#14161f",
        "surface": "#1c1f2b",
        "rail": "#0f1118",
        "border": "#2a2e3e",
        "text": "#e8eaf2",
        "text2": "#c3c8d8",
        "muted": "#98a0b6",
        "accent": "#8f8ff7",
        "accent_soft": "#2b2c54",
        "accent_text": "#cdcdff",
        "btn_bg": "#5f5fe0",
        "btn_hover": "#7070f0",
        "on_accent": "#ffffff",
        "hover": "#252938",
        "focus": "#8f8ff7",
        "danger": "#e5484d",
        "notice_bg": "#3a3016",
        "notice_text": "#f3dc9a",
        "notice_border": "#5c4c1c",
        "tip_bg": "#e8eaf2",
        "tip_text": "#14161f",
        "scroll": "#3a3f52",
        "input_bg": "#181b26",
        "input_border": "#343950",
        "disabled_text": "#666d82",
        "disabled_bg": "#1a1d28",
    },
}

_current = "light"


def palette() -> dict[str, str]:
    return PALETTES[_current]


def render_stylesheet(scheme: str) -> str:
    template = files("allinone").joinpath("theme.qss").read_text(encoding="utf-8")
    colors = PALETTES[scheme]
    return re.sub(r"@([a-z0-9_]+)", lambda match: colors[match.group(1)], template)


def qt_palette(scheme: str) -> QPalette:
    """Cover widgets the stylesheet does not style, such as native message boxes."""
    colors = PALETTES[scheme]
    result = QPalette()
    for role, key in [
        (QPalette.ColorRole.Window, "bg"),
        (QPalette.ColorRole.WindowText, "text"),
        (QPalette.ColorRole.Base, "input_bg"),
        (QPalette.ColorRole.AlternateBase, "surface"),
        (QPalette.ColorRole.Text, "text"),
        (QPalette.ColorRole.Button, "surface"),
        (QPalette.ColorRole.ButtonText, "text"),
        (QPalette.ColorRole.ToolTipBase, "tip_bg"),
        (QPalette.ColorRole.ToolTipText, "tip_text"),
        (QPalette.ColorRole.Highlight, "accent"),
        (QPalette.ColorRole.HighlightedText, "on_accent"),
        (QPalette.ColorRole.PlaceholderText, "muted"),
        (QPalette.ColorRole.Link, "accent"),
    ]:
        result.setColor(role, QColor(colors[key]))
    for role in (
        QPalette.ColorRole.WindowText,
        QPalette.ColorRole.Text,
        QPalette.ColorRole.ButtonText,
    ):
        result.setColor(QPalette.ColorGroup.Disabled, role, QColor(colors["disabled_text"]))
    return result


class ThemeManager(QObject):
    """Resolves Light / Dark / Match Windows and keeps Qt, web pages and icons in step."""

    changed = Signal(str)

    def __init__(self, mode: str = "system", parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.mode = "system"
        self._scheme = ""
        self._styled = False
        QGuiApplication.styleHints().colorSchemeChanged.connect(lambda *_args: self.refresh())
        self.set_mode(mode)

    @property
    def scheme(self) -> str:
        return self._scheme

    def set_mode(self, mode: str) -> None:
        if mode not in THEME_MODES:
            raise ValueError("Unknown theme")
        self.mode = mode
        hints = QGuiApplication.styleHints()
        forced = {"light": Qt.ColorScheme.Light, "dark": Qt.ColorScheme.Dark}.get(mode)
        # Setting the application scheme also tells web pages (prefers-color-scheme).
        if forced is not None and hasattr(hints, "setColorScheme"):
            hints.setColorScheme(forced)
        elif forced is None and hasattr(hints, "unsetColorScheme"):
            hints.unsetColorScheme()
        self.refresh()

    def resolve(self) -> str:
        if self.mode in ("light", "dark"):
            return self.mode
        dark = QGuiApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark
        return "dark" if dark else "light"

    def refresh(self) -> None:
        global _current
        scheme = self.resolve()
        if scheme == self._scheme:
            return
        self._scheme = scheme
        _current = scheme
        icons.set_scheme(scheme)
        app = QApplication.instance()
        if isinstance(app, QApplication):
            if not self._styled:
                app.setStyle("Fusion")  # Honors the palette on every Windows version.
                self._styled = True
            app.setPalette(qt_palette(scheme))
        self.changed.emit(scheme)
