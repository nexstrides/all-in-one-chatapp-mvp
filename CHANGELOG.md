# Changelog

## 0.1.2 — speed, sign-in and look

- Fix the slowdown introduced in 0.1.1: unchanged page titles no longer trigger work, sidebar
  icons are cached and updated in place, bursts of title changes are coalesced, and the settings
  page and tray icon are only redrawn when they changed.
- Gmail and Outlook: report a browser identity without the embedded-engine token that Google
  rejects, accept an optional email address that pre-fills the provider's own sign-in, widen the
  allowed sign-in domains and explain Google's refusal page. Passwords are never read or stored.
- New original icon set: rounded tiles with count badges, crisp on high-DPI screens.
- Working light and dark themes with Match Windows, set in Settings or the Appearance menu.
- Smoother sidebar buttons with a short hover fade.

## 0.1.1 — feedback review

- Require a Slack workspace URL and offer repair for existing generic Slack accounts.
- Preserve existing profiles when updating a Slack workspace address.
- Replace the text sidebar and toolbar with a compact icon rail and full content panel.
- Add right-click account actions, an app settings page and keyboard shortcuts.
- Add a local profile modal with optional avatar photo and settings shortcuts.
- Put Add service directly below the service list; use bell and moon icon controls.
- Show red missed-notification badges, persist them across restarts and clear per account.
- Include an installer, portable ZIP and checksums in PR review builds.

## 0.1.0

- Add local Windows desktop MVP with isolated profiles and service presets.
- Add notification routing, app alerts, tray controls and local metadata history.
- Add unit tests, Windows CI, portable packaging and per-user installer configuration.

