"""Validated, Qt-independent configuration and policy."""

import base64
import binascii
import re
from dataclasses import asdict, dataclass, field
from importlib.resources import files
from json import loads
from urllib.parse import urlsplit
from uuid import uuid4

PRESETS = loads(files("allinone").joinpath("recipes/services.json").read_text(encoding="utf-8"))


@dataclass
class LocalProfile:
    name: str = "My profile"
    avatar_png: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip() or len(self.name) > 60:
            raise ValueError("Profile name must contain 1–60 characters.")
        self.name = self.name.strip()
        if not isinstance(self.avatar_png, str) or len(self.avatar_png) > 200_000:
            raise ValueError("Profile picture is too large.")
        if self.avatar_png:
            try:
                if not base64.b64decode(self.avatar_png, validate=True).startswith(
                    b"\x89PNG\r\n\x1a\n"
                ):
                    raise ValueError("Choose a valid profile picture.")
            except (ValueError, binascii.Error) as exc:
                raise ValueError("Choose a valid profile picture.") from exc


def validate_id(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[a-f0-9]{32}", value):
        raise ValueError("Invalid service identifier")
    return value


def validate_url(value: str) -> str:
    value = value.strip()
    try:
        parsed = urlsplit(value)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or any(c.isspace() or ord(c) < 32 for c in value)
            or "\\" in value
        ):
            raise ValueError
        _ = parsed.port
    except ValueError as exc:
        raise ValueError("Use a valid HTTPS URL without embedded credentials.") from exc
    return value


def host_matches(host: str, domain: str) -> bool:
    host, domain = host.lower().rstrip("."), domain.lower().rstrip(".")
    return host == domain or host.endswith("." + domain)


def slack_workspace_url(value: str) -> str:
    """Accept a workspace address, never a generic landing or sign-in callback URL."""
    value = value.strip()
    if "://" not in value:
        value = "https://" + value
    parsed = urlsplit(validate_url(value))
    host = (parsed.hostname or "").lower()
    if parsed.port not in (None, 443):
        raise ValueError("Use your Slack workspace's HTTPS address on the default port.")
    if host == "app.slack.com":
        match = re.fullmatch(r"/client/(T[A-Z0-9]+)(?:/.*)?", parsed.path)
        if match:
            return f"https://app.slack.com/client/{match[1]}"
    else:
        match = re.fullmatch(
            r"([a-z0-9](?:[a-z0-9-]*[a-z0-9])?)(?:\.enterprise)?\.slack\.com", host
        )
        if match and match[1] not in {
            "www",
            "api",
            "app",
            "my",
            "help",
            "status",
            "slack",
            "docs",
            "slack-files",
        }:
            return f"https://{host}/"
    raise ValueError(
        "Enter your workspace URL, such as https://your-team.slack.com, "
        "or a workspace link beginning https://app.slack.com/client/T…"
    )


def needs_slack_workspace(service: "Service") -> bool:
    if service.kind != "slack":
        return False
    try:
        slack_workspace_url(service.url)
        return False
    except ValueError:
        return True


@dataclass
class Service:
    name: str
    url: str
    kind: str = "custom"
    id: str = field(default_factory=lambda: uuid4().hex)
    notifications: bool = True
    always_on: bool = True
    sticky: bool = False
    bypass_dnd: bool = False
    reminder_minutes: int = 0
    user_agent: str = ""

    def __post_init__(self) -> None:
        validate_id(self.id)
        if not isinstance(self.name, str) or not self.name.strip() or len(self.name) > 60:
            raise ValueError("Name must contain 1–60 characters.")
        self.name = self.name.strip()
        self.url = validate_url(self.url)
        if self.kind not in PRESETS and self.kind != "custom":
            raise ValueError("Unknown service type")
        for key in ("notifications", "always_on", "sticky", "bypass_dnd"):
            if not isinstance(getattr(self, key), bool):
                raise ValueError(f"{key} must be a boolean")
        if type(self.reminder_minutes) is not int or not 0 <= self.reminder_minutes <= 1440:
            raise ValueError("Reminder must be between 0 and 1440 minutes")
        if not isinstance(self.user_agent, str) or any(ord(c) < 32 for c in self.user_agent):
            raise ValueError("User agent must be a single line")

    def to_dict(self) -> dict:
        return asdict(self)


def internal_url(service: Service, value: str, *, allow_auth: bool = True) -> bool:
    try:
        validate_url(value)
        target, initial = urlsplit(value), urlsplit(service.url)
        if target.port != initial.port:
            return False
        host = target.hostname or ""
        if host == initial.hostname:
            return True
        recipe = PRESETS.get(service.kind, {})
        domains = recipe.get("domains", [])
        if allow_auth:
            domains = domains + recipe.get("auth_domains", [])
        return any(host_matches(host, domain) for domain in domains)
    except ValueError:
        return False


def unread_from_title(title: str) -> int:
    # Deliberately avoid interpreting workspace names, dates or message text.
    match = re.match(r"^\s*[([]([0-9][0-9,]*)\+?[)\]]", title)
    return min(int(match[1].replace(",", "")), 99999) if match else 0


def should_notify(service: Service, dnd: bool) -> bool:
    return service.notifications and (not dnd or service.bypass_dnd)


def can_hibernate(service: Service, unread: int, active: bool, idle_seconds: float) -> bool:
    return (
        not active
        and not service.always_on
        and not service.notifications
        and not service.sticky
        and not service.reminder_minutes
        and unread == 0
        and idle_seconds >= 900
    )
