# Security

Do not attach cookies, tokens, message content or full profile directories to issues.
The app never injects a Python/JavaScript bridge into provider pages and does not scrape
messages. Chromium owns provider session storage under the local user's AppData.

Only notifications from a configured service origin are auto-granted. Other device
permissions and downloads are denied in v0.1. The Chromium sandbox and certificate
validation are never disabled by production code.

Notification history is metadata-only; account labels can still be sensitive. It is
stored locally using the current OS user's filesystem permissions, not application-level
encryption. Protect the device with your normal Windows account and disk security.

Automatic update installation is deferred until a signed release/feed is configured.
Do not run arbitrary installers suggested by provider pages.
