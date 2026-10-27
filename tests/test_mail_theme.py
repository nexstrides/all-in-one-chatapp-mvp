"""Mail sign-in helpers, theme tokens and the title-change regression."""

import re
from importlib.resources import files

import pytest
from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QApplication

from allinone import theme
from allinone.icons import service_icon
from allinone.models import (
    PRESETS,
    Service,
    browser_user_agent,
    signin_rejected,
    start_url,
    validate_email,
)
from allinone.storage import Store


def mail(kind, hint):
    recipe = PRESETS[kind]
    return Service(recipe["name"], recipe["url"], kind=kind, login_hint=hint)


def test_user_agent_drops_only_the_webengine_token():
    default = "Mozilla/5.0 (Windows NT 10.0) Chrome/130.0 QtWebEngine/6.12.0 Safari/537.36"
    cleaned = browser_user_agent(default)
    assert "QtWebEngine" not in cleaned
    assert cleaned.startswith("Mozilla/5.0") and cleaned.endswith("Safari/537.36")
    assert browser_user_agent("Custom/1.0") == "Custom/1.0"


def test_google_rejection_page_is_detected_by_path_only():
    assert signin_rejected("https://accounts.google.com/v3/signin/rejected?x=1")
    assert not signin_rejected("https://accounts.google.com/v3/signin/identifier")
    assert not signin_rejected("https://evil.test/signin/rejected")


def test_email_hint_is_validated_and_only_for_mail():
    assert validate_email("me@example.com") == "me@example.com"
    for bad in ["nope", "a@b", "a b@example.com", "x@y.z"]:
        with pytest.raises(ValueError):
            validate_email(bad)
    with pytest.raises(ValueError):
        Service("Slack", "https://acme.slack.com/", kind="slack", login_hint="me@example.com")
    assert mail("gmail", "").login_hint == ""


def test_start_url_prefills_without_changing_the_origin():
    gmail = start_url(mail("gmail", "me+tag@example.com"))
    assert gmail.startswith("https://mail.google.com/mail/?authuser=me%2Btag%40example.com")
    outlook = start_url(mail("outlook", "me@example.com"))
    assert "login_hint=me%40example.com" in outlook
    assert start_url(mail("gmail", "")) == PRESETS["gmail"]["url"]


def test_theme_defaults_persist_and_reject_unknown(tmp_path):
    store = Store(tmp_path)
    assert store.theme == "system"
    store.theme = "dark"
    store.save()
    assert Store(tmp_path).theme == "dark"


def test_every_stylesheet_token_exists_in_both_palettes():
    source = files("allinone").joinpath("theme.qss").read_text(encoding="utf-8")
    tokens = set(re.findall(r"@([a-z0-9_]+)", source))
    assert tokens
    for scheme, colors in theme.PALETTES.items():
        assert tokens <= set(colors), (scheme, tokens - set(colors))
        assert "@" not in theme.render_stylesheet(scheme)
    assert set(theme.PALETTES["light"]) == set(theme.PALETTES["dark"])


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def test_forced_modes_resolve_and_notify(app):
    manager = theme.ThemeManager("light")
    seen = []
    manager.changed.connect(seen.append)
    manager.set_mode("dark")
    manager.set_mode("dark")
    assert manager.scheme == "dark" and seen == ["dark"]
    with pytest.raises(ValueError):
        manager.set_mode("neon")
    manager.set_mode("system")
    manager.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


def test_icons_are_cached_and_badged(app):
    assert service_icon("slack") is service_icon("slack")
    assert service_icon("slack", 3) is not service_icon("slack")
    assert not service_icon("unknown-kind").isNull()
