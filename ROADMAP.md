# Roadmap

Planned work after v0.1.1. Items come from the README's "Scope and known limits" and the
v0.1.1 feedback review. Estimates are rough; open an issue to discuss any item.

## Next: v0.1.2 (in review, PR #3)
- Fix the v0.1.1 slowdown, add mail sign-in help, light/dark/system themes and new icons.

## v0.2: reliability and release
| Work | Type | Estimate |
| --- | --- | --- |
| Run the Windows smoke checklist on real WhatsApp, Telegram, Slack, Discord, Gmail and Outlook accounts; fix what fails | bugs, tests | 4 h |
| Code signing and a signed release workflow; third-party license/notice file for PySide6 and dependencies | build, docs | 3 h |
| Reset an account in place (clear cache and sign-in without removing and re-adding it) | feature | 2 h |
| Performance measurements: startup time, memory per account, hibernation savings; add a benchmark script | perf, tests | 3 h |
| Raise GUI/WebEngine test coverage (sidebar, settings, profile modal, badge clearing) | tests | 3 h |

## v0.3: unread counts and notifications
| Work | Type | Estimate |
| --- | --- | --- |
| Per-provider DOM recipes for unread counts where title badges are missing or wrong | feature | 4 h |
| Custom notification sounds per account | feature | 2 h |
| Better DND: schedules, and respect Windows Focus Assist state in the UI | feature | 2 h |
| Downloads and attachments with a per-account permission prompt (denied today) | feature | 3 h |

## Later
- Signed automatic updates from a release feed.
- Optional camera/microphone permission for calls, per account.
- Import/export of account configuration (without session data).

Not planned: cloud accounts, admin, billing or analytics.
