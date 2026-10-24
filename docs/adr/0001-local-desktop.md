# ADR 0001 — Local desktop MVP

Accepted for v0.1.

Use Python 3.12 and PySide6, the alternative permitted in the supplied specification.
The first release is a desktop application, not a hosted web app. PySide6 avoids making
the product's own source licensing decision a prerequisite for development. No project
license is granted by this repository yet; Qt and bundled dependencies retain their
own licensing and distribution obligations.

Each account uses a named QWebEngineProfile with distinct storage and cache paths.
The app embeds provider pages without a JavaScript bridge or message extraction.
Provider and known authentication domains are allowed inside each instance; external
HTTPS link clicks open the default browser. Automatic popups are rejected.

Remote notifications are shown transiently. Persistent history contains service IDs,
user-chosen account labels, timestamps and opened status only. This resolves the spec's
tension between searchable history and never storing message content in favor of
content-free history. Chromium profiles and Windows' own notification history may retain
provider content as part of their normal operation.

The OS may suppress notifications. No app can guarantee delivery when the machine sleeps,
the network fails, a provider stops sending events, or Focus Assist suppresses alerts.
Always-on is enabled by default. Hibernation requires notifications to be disabled.

Retain the bundled Chromium user agent by default. A per-account override is available;
the application does not impersonate a newer browser to bypass sign-in restrictions.
