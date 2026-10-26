import pytest

from allinone.models import Service, internal_url, needs_slack_workspace, slack_workspace_url


@pytest.mark.parametrize(
    "value,expected",
    [
        ("acme.slack.com", "https://acme.slack.com/"),
        ("https://ACME.slack.com/messages?token=discard#fragment", "https://acme.slack.com/"),
        ("https://acme.enterprise.slack.com/", "https://acme.enterprise.slack.com/"),
        (
            "https://app.slack.com/client/T123ABC/C123?x=discard",
            "https://app.slack.com/client/T123ABC",
        ),
    ],
)
def test_workspace_address(value, expected):
    assert slack_workspace_url(value) == expected
    service = Service("Team", expected, kind="slack")
    assert not needs_slack_workspace(service)
    assert internal_url(service, "https://app.slack.com/client/T123ABC")
    assert internal_url(service, "https://accounts.google.com/signin")
    assert not internal_url(service, "https://slack.com.attacker.test/")


@pytest.mark.parametrize(
    "value",
    [
        "",
        "http://acme.slack.com",
        "https://slack.com",
        "https://app.slack.com/",
        "https://www.slack.com",
        "https://acme.slack.com.attacker.test",
        "https://evilslack.com",
        "https://user:pass@acme.slack.com",
        "https://acme.slack.com:8443",
        "https://app.slack.com/client/",
    ],
)
def test_workspace_rejects_generic_or_unsafe_address(value):
    with pytest.raises(ValueError):
        slack_workspace_url(value)


def test_legacy_slack_remains_loadable_for_repair():
    service = Service("Old Slack", "https://app.slack.com/", kind="slack")
    assert needs_slack_workspace(service)
    assert not needs_slack_workspace(Service("Custom", "https://example.com"))
