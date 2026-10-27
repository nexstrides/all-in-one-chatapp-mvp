# v0.1.2 — Speed, mail sign-in and a new look

Fixes the freezing and slow loading reported in v0.1.1 (the cause was found by reading the
code, not by profiling on Windows, so please confirm on your machine). Adds working light,
dark and Match Windows themes, a new icon set and an optional email field for Gmail and
Outlook that pre-fills the provider's sign-in page. Google sign-in inside an embedded browser
is not guaranteed; if Google declines, the app says so and you can use Open in browser.

Unsigned pre-release: Windows will show an unknown-publisher warning. Please run the manual
Windows checklist (docs/windows-smoke-test.md) before this is published.

---

# v0.1.1 — User feedback review build

A compact icon sidebar and full content panel replace the Workspace menu and top
bar. Add service sits under the service icons. Right-click opens account actions
and App settings; the avatar opens your local profile with photo and name controls.
Bell/moon controls show notifications and Do Not Disturb, with red missed-activity badges.

Slack now requires a workspace URL. Existing generic Slack accounts offer a repair
step without deleting their profile. In Slack, choose the browser sign-in path.

This is an unsigned MVP review build. Real Slack workspace authentication, organization
SSO, Windows notifications and DPI/keyboard behavior need the manual Windows checklist.
Tests of the shell use offline service substitutes; they do not prove live provider login.
No production compatibility or notification-delivery guarantee is implied.

Not included: calls, downloads, cloud profiles, automatic updates, code signing,
custom notification sounds, payments, analytics or an admin portal.
