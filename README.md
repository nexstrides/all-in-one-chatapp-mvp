# All in One Chatapp

A local Windows desktop workspace for your messenger and email accounts.
Built with Python 3.12 and PySide6/Qt WebEngine. No app server or subscription is required.

**v0.1.1 feedback review build.** Core behavior is implemented; live-provider compatibility and
Windows release acceptance remain manual gates. See [the smoke checklist](docs/windows-smoke-test.md).

## Run on Windows

Install Python 3.12 (64-bit), then run these commands from the repository in PowerShell:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[dev]"
.venv\Scripts\python.exe -m allinone
```

Use the **+** button immediately below the service icons to add WhatsApp, Telegram, Slack, Discord, Gmail, Outlook or a
custom HTTPS app. Add the same provider twice for separate accounts. Closing the
window keeps accounts running in the tray. Use the tray menu or Ctrl+Q to quit.
Start with Windows is available in Settings and the tray menu.

## Feedback update: v0.1.1

- Compact sidebar with bundled service icons, tooltips and keyboard-accessible names.
- Service content fills the window beside the sidebar; no Workspace menu or top toolbar.
- Right-click a service icon or the service page for account settings, reload, browser,
  cache and removal actions. The service page retains its browser context actions.
- App settings: right-click → App settings, **Ctrl+,**, or avatar → App settings.
- Avatar opens a local profile modal with a display name, photo, settings and history.
  This is a device-local profile, independent of provider accounts; nothing is uploaded.
- Bell and moon icon controls replace notification and Do Not Disturb text buttons.
- The bell's red badge counts unopened notification records. Opening a service clears
  its missed records. Counts survive restarts and are not cleared by hidden startup.
  Service badges show the larger of title-unread and missed counts, avoiding addition
  of two counts that may refer to the same activity. They are not exact message totals.

### Slack workspaces

When adding Slack, enter `https://your-team.slack.com` (or a workspace link such as
`https://app.slack.com/client/T123ABC`). Generic Slack landing pages are rejected.
Sign in inside the service panel and choose **Use Slack in your browser** if offered.
Existing Slack accounts with a generic URL show **Set workspace URL**; updating the
URL preserves that account's profile directory and saved sign-in data. Organization
SSO may still reject embedded browsers; compatibility must be tested with real accounts.

Offline previews with sample accounts/counts: [sidebar](docs/ui/slack-setup.png),
[settings](docs/ui/settings.png), [profile](docs/ui/profile.png).


## Included

| Area | v0.1.1 behavior |
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
  are denied in v0.1.1. This release focuses on messaging and email, not calls or attachments.
- Custom sounds, reset-in-place, signed automatic updates and performance measurements
  are deferred. Remove and re-add an account to reset it.
- Cloud accounts, admin, billing and analytics are Phase 2 and are not included.

## Local data and privacy

Windows data lives in `%APPDATA%\AllInOneChatapp`:

- `services.json`: account configuration and pending deletion IDs.
- `profiles/<id>/storage` and `profiles/<id>/cache`: Chromium-managed account data.
- `history.sqlite3`: service ID/name, timestamp and opened status; no notification body.
- `logs/`: rotating application diagnostics without message content.

Remove an account through right-clicking a service icon → Remove account to delete its profile and
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
PR CI uploads an unsigned installer, portable ZIP and SHA-256 checksums as a review artifact. A version tag matching the application
version runs the release workflow, builds the Inno Setup installer and creates a **draft**
release with SHA-256 checksums. The v0.1.0 pre-release remains available; the v0.1.1 changes are reviewed through a PR before publishing.

Before public distribution, complete Windows smoke testing, code signing and third-party
license/notice review. Project source licensing is intentionally undecided; PySide6 and
its dependencies keep their own terms.

See [architecture decisions](docs/adr/0001-local-desktop.md),
[security](SECURITY.md) and [release notes](docs/release-notes.md).

