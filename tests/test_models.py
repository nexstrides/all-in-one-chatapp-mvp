from dataclasses import replace

import pytest

from allinone.models import (
    PRESETS,
    Service,
    can_hibernate,
    host_matches,
    internal_url,
    should_notify,
    unread_from_title,
    validate_id,
    validate_url,
)


@pytest.mark.parametrize(
    "value",
    [
        "http://slack.com",
        "javascript:alert(1)",
        "file:///etc/passwd",
        "https://user:secret@slack.com",
        "https://",
        "https://a.test:bad",
        "https://a.test/with space",
        "https://a.test\\@b.test",
    ],
)
def test_reject_unsafe_url(value):
    with pytest.raises(ValueError):
        validate_url(value)


def test_presets_validate_and_accounts_are_unique():
    for key, recipe in PRESETS.items():
        a = Service(recipe["name"], recipe["url"], kind=key)
        b = Service(recipe["name"], recipe["url"], kind=key)
        assert a.id != b.id
        assert internal_url(a, recipe["url"])


@pytest.mark.parametrize("value", ["../secret", "/tmp/test", "ABC", "", "a" * 33])
def test_profile_id_blocks_path_traversal(value):
    with pytest.raises(ValueError):
        validate_id(value)


@pytest.mark.parametrize(
    "field,value",
    [
        ("name", ""),
        ("name", "x" * 61),
        ("kind", "unknown"),
        ("notifications", "yes"),
        ("reminder_minutes", -1),
        ("reminder_minutes", True),
        ("reminder_minutes", 1441),
        ("user_agent", "Bad\nHeader"),
    ],
)
def test_invalid_settings(field, value):
    settings = {"name": "Work", "url": "https://app.slack.com"}
    settings[field] = value
    with pytest.raises(ValueError):
        Service(**settings)


def test_domain_boundaries_and_auth():
    service = Service("Work", "https://app.slack.com", kind="slack")
    assert internal_url(service, "https://team.slack.com/messages")
    assert internal_url(service, "https://accounts.google.com/signin")
    assert not internal_url(service, "https://accounts.google.com", allow_auth=False)
    assert not internal_url(service, "https://slack.com.attacker.test")
    assert not internal_url(service, "https://evilslack.com")
    assert not internal_url(service, "https://app.slack.com:8443")
    assert not internal_url(service, "http://app.slack.com")
    assert host_matches("Team.Slack.Com.", "slack.com")
    custom = Service("Custom", "https://chat.example.test/")
    assert not internal_url(custom, "https://other.example.test")


@pytest.mark.parametrize(
    "title,count",
    [
        ("(3) WhatsApp", 3),
        ("[12] Inbox", 12),
        ("(1,234) Slack", 1234),
        ("(99+) Discord", 99),
        ("Inbox (4)", 0),
        ("2026 planning", 0),
        ("(9999999) Mail", 99999),
        ("normal title", 0),
        ("", 0),
    ],
)
def test_unread_title(title, count):
    assert unread_from_title(title) == count


def test_notification_and_hibernation_rules():
    service = Service("Work", "https://app.slack.com")
    assert should_notify(service, False)
    assert not should_notify(service, True)
    assert should_notify(replace(service, bypass_dnd=True), True)
    assert not should_notify(replace(service, notifications=False, bypass_dnd=True), True)
    sleeping = replace(service, always_on=False, notifications=False)
    assert can_hibernate(sleeping, 0, False, 901)
    assert not can_hibernate(sleeping, 1, False, 901)
    assert not can_hibernate(sleeping, 0, True, 901)
    assert not can_hibernate(sleeping, 0, False, 899)
    assert not can_hibernate(replace(sleeping, sticky=True), 0, False, 901)
    assert not can_hibernate(replace(sleeping, reminder_minutes=5), 0, False, 901)
    assert not can_hibernate(service, 0, False, 901)
