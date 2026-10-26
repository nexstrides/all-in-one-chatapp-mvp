# Windows release checklist

Run on Windows 10 and Windows 11, using a non-admin account. These are manual release
gates, not claims that live-service integration has already passed.

- [ ] Install from the draft release; confirm Start Menu shortcut and executable work.
- [ ] Add all six presets and a custom HTTPS site; add ten accounts.
- [ ] At 100%, 125%, 150% and 200% scaling, check icon tooltips, visible keyboard focus,
      sidebar scrolling with ten accounts, and Add service directly below the list.
- [ ] Confirm service content fills the remaining window after resize/maximize.
- [ ] Right-click the sidebar and a service page; check app/account settings and native
      web copy/link actions. Check Ctrl+N, Ctrl+R, Ctrl+, and Ctrl+Q.
- [ ] Open the avatar modal; change name/photo, cancel edits, save and restart.
- [ ] Toggle DND from both the moon and Settings; verify the controls stay synchronized.
- [ ] Receive three notifications in another account; verify red service/bell badges,
      persistence after restart, per-account clearing and no clearing on hidden startup.
- [ ] Upgrade from v0.1.0 with a generic Slack account: set its workspace URL and verify
      the same profile directory is retained. Reject generic and lookalike Slack URLs.
- [ ] Add Slack with a workspace URL and sign in through the browser option in the panel.
      Verify app.slack.com/client redirects and record actual SSO/provider failures.
- [ ] Sign into two distinct Slack accounts and two Telegram accounts; restart and reboot.
- [ ] Confirm cookies, IndexedDB and service-worker state do not cross accounts.
- [ ] Receive notifications from background accounts with the window hidden to tray.
- [ ] Click two different Windows toasts in reverse order; each opens its original account.
- [ ] Test DND, bypass, sticky alerts, dismissal, reminders and provider notification closure.
- [ ] Confirm app alerts cannot bypass Windows Focus Assist, lock screen or sleep.
- [ ] Confirm title-derived unread totals match provider titles. Record provider gaps.
- [ ] External links open the browser; allowlisted authentication popups stay isolated.
- [ ] Document Gmail embedded sign-in outcome. Do not disable provider security controls.
- [ ] Confirm denied camera, microphone, location, downloads and clipboard permissions.
- [ ] Clear cache and verify login is preserved.
- [ ] Remove an account; confirm its profile directory and history disappear.
- [ ] With notifications and always-on off, idle an account for 15 minutes; switch back.
- [ ] Measure startup time and memory before/after hibernation; record observed values.
- [ ] Enable autostart; reboot; verify hidden startup and correct command quoting.
- [ ] Start a second process; verify it does not acquire another writable profile.
- [ ] Quit with pending notifications and open login popups; verify clean shutdown.
- [ ] Uninstall; startup entry is removed. Account profiles remain for reinstall unless
      removed through the app first (documented preservation policy).
- [ ] Validate dependency notices and code-signing before public distribution.

Unverified targets: <5 s cold start/restore, <2.5 GB with six live accounts, 70% memory
drop during hibernation. Do not report them as achieved measurements.

