# All in One Chatapp

A local Windows desktop workspace for your messenger and email accounts.
Built with Python 3.12 and PySide6/Qt WebEngine. No app server or subscription is required.

**v0.1 review build.** Core behavior is implemented; live-provider compatibility and
Windows release acceptance remain manual gates. See [the smoke checklist](docs/windows-smoke-test.md).

## Run on Windows

Install Python 3.12 (64-bit), then run these commands from the repository in PowerShell:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[dev]"
.venv\Scripts\python.exe -m allinone
```

Use **Add a service** to add WhatsApp, Telegram, Slack, Discord, Gmail, Outlook or a
custom HTTPS app. Add the same provider twice for separate accounts. Closing the
window keeps accounts running in the tray. Use the tray menu or Ctrl+Q to quit.
Start with Windows is available in the tray menu.

## Included

| Area | v0.1 behavior |
| --- | --- |
| Accounts | Six presets, custom HTTPS URLs, isolated persistent profiles |
| Navigation | Sidebar, reload, external links, allowlisted login popups |
| Notifications | Windows toasts with per-notification click routing; in-app fallback |
| Controls | App DND, per-account bypass, persistent in-app alerts, timed reminders |
| Unread | Counts parsed from leading title badges; tray total |
| Lifecycle | Close to tray, single-process lock, per-user Windows autostart |
| Data | Atomic settings, deletion retries, 90-day metadata-only notification history |
| Memory | Opt-in hibernation after 15 idle minutes when notifications are disabled |
| Build | Windows test/build workflow, portable folder, Inno Setup installer recipe |

## Scope and known limits

- Providers can reject embedded sign-in; Gmail and organization SSO need early testing.
  Opening a service in the default browser uses that browser's separate login session.
- Only title-based unread badges are implemented. Counts may be unavailable for some
  provider layouts; DOM recipes are deferred.
- OS Focus Assist, sleep, network loss and provider behavior can suppress delivery.
  Closing the window preserves delivery eligibility; quitting the app does not.
- Native notification behavior requires Windows validation. In-app alerts are the fallback.
- Camera/microphone, screen sharing, downloads and programmatic clipboard permissions
  are denied in v0.1. This release focuses on messaging and email, not calls or attachments.
- Custom sounds, reset-in-place, signed automatic updates and performance measurements
  are deferred. Remove and re-add an account to reset it.
- Cloud accounts, admin, billing and analytics are Phase 2 and are not included.

## Local data and privacy

Windows data lives in `%APPDATA%\AllInOneChatapp`:

- `services.json`: account configuration and pending deletion IDs.
- `profiles/<id>/storage` and `profiles/<id>/cache`: Chromium-managed account data.
- `history.sqlite3`: service ID/name, timestamp and opened status; no notification body.
- `logs/`: rotating application diagnostics without message content.

Remove an account through Workspace → Remove current account to delete its profile and
history. Locked files are retried on the next startup. Uninstall preserves account
profiles for reinstall; remove accounts first if you want those profiles deleted.

No analytics, message scraping, Python bridge or application-owned credential collection.
Provider web apps and Windows itself can retain content through normal browser/OS behavior.

## Development

```powershell
.venv\Scripts\python.exe -m ruff check src tests
.venv\Scripts\python.exe -m ruff format --check src tests
.venv\Scripts\python.exe -m mypy src
$env:QT_QPA_PLATFORM = "offscreen"
$env:RUN_WEBENGINE_TESTS = "1"
.venv\Scripts\python.exe -m pytest --cov
```

Unit coverage targets the Qt-independent model, storage and autostart code, with a 70%
minimum. GUI and WebEngine smoke tests are additional checks, not part of that coverage
denominator. Provider acceptance requires real accounts on Windows.

## Build and release

```powershell
.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --windowed --onedir --name AllInOneChatapp --collect-data allinone --collect-all windows_toasts packaging/entrypoint.py
```

The executable is `dist/AllInOneChatapp/AllInOneChatapp.exe`. Keep the whole folder.
The CI workflow uploads it as a Windows artifact. A version tag matching the application
version runs the release workflow, builds the Inno Setup installer and creates a **draft**
release with SHA-256 checksums. No release has been published by this PR.

Before public distribution, complete Windows smoke testing, code signing and third-party
license/notice review. Project source licensing is intentionally undecided; PySide6 and
its dependencies keep their own terms.

See [architecture decisions](docs/adr/0001-local-desktop.md),
[security](SECURITY.md) and [release notes](docs/release-notes.md).
