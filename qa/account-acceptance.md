# OpenWorld account/studio acceptance - October29

All checks use disposable loopback SQLite, generated accounts and a lightweight base-game fixture. This proves the real studio/account UI and backend wiring, not game playback or performance. No real provider request, email, owner account, production data or deployment occurred.

[Source/ASGI checks](account-checks.log):24 cases pass. New behavior covers scoped ZIP metadata plus owned game HTML, no credential/foreign export, authenticated/password/typed account closure, ordinary DB/file rollback, other-account preservation, durable-intent crash reconciliation, old-backup restoration with mandatory surviving deletion evidence, and per-account action limits. Existing private game/guest/sandbox/provider-failure/recovery cases remain accepted after the changed recovery source. Python compile and frontend syntax checks pass.

[Actual headless Chrome UI](ui-checks.log), [fixture](local.py), [scenario](check-ui.mjs). At375x812 and1440x900:

- Real wrong-password/sign-in and account-loading failure/retry, then scoped ZIP downloaded through the UI. ZIP contains the matching account, one owned session/version and actual generated HTML; no password hash. Forget saved key removes its device entry.
- Account confirmation starts on Keep account; forward/backward Tabs stay inside, Escape restores the trigger. Wrong password and network failure preserve controls. A paused real closure request disables confirmation, prevents Escape/duplicate submission and completes once; the deleted account returns to signed-out state and its local studio data is cleared.
- Public privacy/contact fit with44px controls. A contact failure retains the form; retry writes only a synthetic local message. Actual signup succeeds without email/provider traffic. Empty history/store/key dialogs retain focus and close safely.
- All measured studio/account controls are44px, labels are connected and page errors are zero. Final overlap checks catch and fix the Store sort/Close overlap and auth-tab/Close overlap; Escape restores each modal trigger at both widths. [Scenario](check-modal-layout.mjs).

Phone account and desktop Store screenshots were visually reviewed; after overlap fixes, the phone Store and desktop auth were reviewed again. The desktop auth cap remains420px rather than expanding with the viewport; phone editor titles clear the floating controls. Two focused shell/isolation cases pass after the semantic main landmark addition in [shell checks](shell-checks.log). Evidence is named `account-*`, `account-failure-*`, `contact-*`, `privacy-*`, `store-*`, `auth-*`, `key-*`, `history-*` under qa/.

Changed source is a candidate only. The real-base-game mobile performance gate, owner admin exact-width states, existing mirror runtime helper update and coordinator production rollout remain explicit in READINESS.md. Existing actual Sonnet generation/gameplay, sandbox and encrypted-recovery proofs remain valid where unchanged.


## Admin review and contacts

[Real admin UI](admin-checks.log), [scenario](check-admin.mjs). At375/1440 a non-admin account is denied without receiving game HTML; an actual signed-in admin can preview only a submitted contribution. The preview's opaque sandbox blocks parent credential access. The in-page approval dialog supports safe cancel and focus return; approval/decline failures keep actionable recovery feedback, retry succeeds, and contacts loading/read failure/retry behaves truthfully. Logout removes token and saved key. All measured admin actions are44px and the pages fit. [Phone admin](admin-375.jpg), [phone messages](admin-messages-375.jpg) were visually reviewed.

The24 source cases include admin role/submission boundaries, rollback to the prior base game on a failed approval commit and idempotent completed reviews. Approval preserves the existing explicit contribution flow; unsubmitted private games cannot be previewed/approved. The closure policy explicitly distinguishes a saved version from a contribution already copied into the shared base game.
