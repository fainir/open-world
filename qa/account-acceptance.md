# OpenWorld account/studio acceptance - October29

All checks use disposable loopback SQLite, generated accounts and a lightweight base-game fixture. This proves the real studio/account UI and backend wiring, not game playback or performance. No real provider request, email, owner account, production data or deployment occurred.

[Source/ASGI checks](account-checks.log):21 cases pass. New behavior covers scoped ZIP metadata plus owned game HTML, no credential/foreign export, authenticated/password/typed account closure, ordinary DB/file rollback, other-account preservation, durable-intent crash reconciliation, old-backup restoration with mandatory surviving deletion evidence, and per-account action limits. Existing private game/guest/sandbox/provider-failure/recovery cases remain accepted after the changed recovery source. Python compile and frontend syntax checks pass.

[Actual headless Chrome UI](ui-checks.log), [fixture](local.py), [scenario](check-ui.mjs). At375x812 and1440x900:

- Real wrong-password/sign-in and account-loading failure/retry, then scoped ZIP downloaded through the UI. ZIP contains the matching account, one owned session/version and actual generated HTML; no password hash. Forget saved key removes its device entry.
- Account confirmation starts on Keep account; forward/backward Tabs stay inside, Escape restores the trigger. Wrong password and network failure preserve controls. A paused real closure request disables confirmation, prevents Escape/duplicate submission and completes once; the deleted account returns to signed-out state and its local studio data is cleared.
- Public privacy/contact fit with44px controls. A contact failure retains the form; retry writes only a synthetic local message. Actual signup succeeds without email/provider traffic. Empty history/store/key dialogs retain focus and close safely.
- All measured studio/account controls are44px, labels are connected and page errors are zero. Final overlap checks catch and fix the Store sort/Close overlap and auth-tab/Close overlap; Escape restores each modal trigger at both widths. [Scenario](check-modal-layout.mjs).

Phone account and desktop Store screenshots were visually reviewed; after overlap fixes the phone Store and desktop auth screenshots were reviewed again. Evidence is named `account-*`, `account-failure-*`, `contact-*`, `privacy-*`, `store-*`, `auth-*`, `key-*`, `history-*` under qa/.

Changed source is a candidate only. The real-base-game mobile performance gate, owner admin exact-width states, existing mirror runtime helper update and coordinator production rollout remain explicit in READINESS.md. Existing actual Sonnet generation/gameplay, sandbox and encrypted-recovery proofs remain valid where unchanged.
