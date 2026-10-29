# OpenWorld account/studio acceptance - October29

Account/admin checks use disposable loopback SQLite, generated accounts and an explicitly lightweight base-game fixture. Actual-game startup/performance checks below use the real source game instead. No real provider request, email, owner account, production data or deployment occurred.

[Source/ASGI checks](account-checks.log):29 cases pass. New behavior covers scoped ZIP metadata plus owned game HTML, no credential/foreign export, authenticated/password/typed account closure, ordinary DB/file rollback, other-account preservation, durable-intent crash reconciliation, old-backup restoration with mandatory surviving deletion evidence, and per-account action limits. Existing private game/guest/sandbox/provider-failure/recovery cases remain accepted after the changed recovery source; the final suite also includes the mirror-contract guard and public transport/error response. Python compile and frontend syntax checks pass.

[Actual headless Chrome UI](ui-checks.log), [fixture](local.py), [scenario](check-ui.mjs). At375x812 and1440x900:

- Real wrong-password/sign-in and account-loading failure/retry, then scoped ZIP downloaded through the UI. ZIP contains the matching account, one owned session/version and actual generated HTML; no password hash. Forget saved key removes its device entry.
- Account confirmation starts on Keep account; forward/backward Tabs stay inside, Escape restores the trigger. Wrong password and network failure preserve controls. A paused real closure request disables confirmation, prevents Escape/duplicate submission and completes once; the deleted account returns to signed-out state and its local studio data is cleared.
- Public privacy/contact fit with44px controls. A contact failure retains the form; retry writes only a synthetic local message. Actual signup succeeds without email/provider traffic. Empty history/store/key dialogs retain focus and close safely.
- All measured studio/account controls are44px, labels are connected and page errors are zero. Final overlap checks catch and fix the Store sort/Close overlap and auth-tab/Close overlap; Escape restores each modal trigger at both widths. [Scenario](check-modal-layout.mjs).

Phone account and desktop Store screenshots were visually reviewed; after overlap fixes, the phone Store and desktop auth were reviewed again. The desktop auth cap remains420px rather than expanding with the viewport; phone editor titles clear the floating controls. Two focused shell/isolation cases pass after the semantic main landmark addition in [shell checks](shell-checks.log). Evidence is named `account-*`, `account-failure-*`, `contact-*`, `privacy-*`, `store-*`, `auth-*`, `key-*`, `history-*` under qa/.

Changed source is a candidate only; coordinator production rollout remains explicit in READINESS.md. Existing actual Sonnet generation/gameplay, sandbox and encrypted-recovery proofs remain valid where unchanged.


## Admin review and contacts

[Real admin UI](admin-checks.log), [scenario](check-admin.mjs). At375/1440 a non-admin account is denied without receiving game HTML; an actual signed-in admin can preview only a submitted contribution. The preview's opaque sandbox blocks parent credential access. The in-page approval dialog supports safe cancel and focus return; approval/decline failures keep actionable recovery feedback, retry succeeds, and contacts loading/read failure/retry behaves truthfully. Logout removes token and saved key. All measured admin actions are44px and the pages fit. [Phone admin](admin-375.jpg), [phone messages](admin-messages-375.jpg) were visually reviewed.

The24 source cases include admin role/submission boundaries, rollback to the prior base game on a failed approval commit and idempotent completed reviews. Approval preserves the existing explicit contribution flow; unsubmitted private games cannot be previewed/approved. The closure policy explicitly distinguishes a saved version from a contribution already copied into the shared base game.


## Existing independent mirror helper rollout

The coordinator updated only the existing private runtime copies of `recovery.py` and `sync.py`, atomically under its existing `mirror.lock`, and ran the owned foreground sync. The encryption key, configuration, pinned Railway CLI, Python runtime and hourly schedule were preserved. Selected status at2026-10-29T17:06:57.524675Z confirms encrypted copy verified, restore drill passed, drill actually ran for this check, and restore contract2. The copied server snapshot was created at2026-10-29T07:57:02.749823+00:00. No account contents or credentials were logged. This verifies the new helper contract against the current legacy server archive.

After the application rollout creates its first deletion-aware snapshot, G4 still requires one current-snapshot sync to verify the newly included deletion-evidence file end to end. This is a changed-format release check, not another account deletion or provider/model test.

## Public game startup and private-version regression

[Actual-game mobile acceptance](perf/README.md) scores90 performance/100 accessibility without warnings. The actual city/intro is in the final audit frame; a separate actual-touch check enters gameplay and opens the real vehicle selector with zero page/console errors. The source game and saved versions are unchanged. The public base streams directly in the existing opaque sandbox, while private versions retain caller-authenticated fetch without credential-bearing URLs.

[Private transport UI](private-startup.log), [scenario](check-private-startup.mjs): at375/1440 a real signed-in caller opens/reloads their bookmarked owned version through bearer headers, and game access to parent storage fails. A deliberately delayed owned response returns after logout; it cannot replace the now-public base or restore the removed local token. The real missing-base404 response fits375px, retains the opaque policy and a44px retry control; retry recovers when the synthetic fixture file is restored. [Phone private version](private-game-375.jpg), [desktop private version](private-game-1440.jpg), [phone retry](game-load-retry-375.jpg). These private/error tests use the functional fixture and make no gameplay/performance claim.
