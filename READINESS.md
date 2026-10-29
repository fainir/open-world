# OpenWorld - Readiness

Every row serves [GOAL.md](GOAL.md) and portfolio PT08. Prior valid evidence root: `/Users/nirfeinstein/Documents/ChatGPT/almost finished projects + marketing/artifacts/production-readiness-2026-10-26` (A). Existing accepted game/provider/recovery tests are not repeated without a changed concern.

Production https://open-world.gg. FastAPI/SQLite/static studio; exact run/test/deploy/recovery commands in [PRODUCT.md](PRODUCT.md) and [OPERATIONS.md](OPERATIONS.md). One writer: openworld_finish on codex/production-readiness. No production deployment by this worker.

| ID | Flow or gate | Status | Evidence / next action |
|---|---|---|---|
| F1 | Start/play the base and Sonnet-generated game, move and use vehicle selector | verified | A/openworld-production-browser-playback.json |
| F2 | Private sessions, versions and chat belong only to their caller | verified | A/openworld-live-canary.json; A/openworld-security-tests.log |
| F3 | Generate a complete edit, retain prior version, reload and explicitly share | verified | A/openworld-sonnet-live-canary.json; A/openworld-production-browser-playback.json |
| F4 | Game sandbox cannot access studio credentials/storage or privileged actions | verified | A/openworld-production-recovery.json; A/openworld-live-canary.json |
| F5 | Recovery recreates matching game/database data and invalidates old sessions | verified | A/openworld-unattended-mirror-status.json; OPERATIONS.md; accepted13 source/ASGI cases |
| A1 | Download the signed-in caller's profile, chats and generated game files | verified | [24 source/ASGI checks and real download](qa/account-acceptance.md); matching profile/chat/version ZIP and actual owned HTML at375/1440; credentials and foreign data excluded |
| A2 | Close an account safely, remove active owned data/files and preserve other users | verified | [24 source/ASGI checks and real closure](qa/account-acceptance.md); password/typed confirmation, DB/file rollback, other-account preservation, crash intent and mandatory old-restore reconciliation; actual busy/error/retry/deletion at375/1440 |
| A3 | Read accurate privacy/storage/provider/retention/contact disclosures | verified | [Compiled public policy/contact](qa/account-acceptance.md), `/privacy` and `/account`; explicit storage/provider/retention/removed-ID/independent-copy limits. Public rollout remains G4 |
| U1 | Sign-in, store, history, key entry, account and contact at375/1440 | verified | [Actual UI](qa/account-acceptance.md):375/1440 sign-in/signup, account/data controls, contact/privacy, empty history/store and key dialog; lightweight game fixture, gameplay unchanged |
| U2 | Modal focus/keyboard,44px controls and loading/error/empty states | verified | [Actual UI](qa/account-acceptance.md):44px controls, connected labels, loading/error retries, forward/backward focus wrapping, Escape/trigger return and no overlapping modal controls; zero page errors |
| U3 | Owner admin suggestions/contacts and role-denied states at375/1440 | verified | [Actual admin acceptance](qa/account-acceptance.md), [log](qa/admin-checks.log): role denial, submitted-only opaque preview, in-page review/cancel, rollback/idempotence, contacts/read retries and safe logout; all44px and no overflow |
| G1 | Main mobile Lighthouse performance/accessibility >=90 | building (coordinator) | Actual-base69/98 with slow-host CPU warning and TBT2.62s; no pass claimed. Later diagnostic reaches game intro/canvas with zero errors; main landmark fixed. [Unresolved measurement](qa/perf/README.md); independent public measurement before engine changes |
| G2 | Current changed-source tests and dependency/security checks | verified | [24 source/ASGI checks](qa/account-checks.log), frontend syntax and Python compile pass; dependency versions unchanged from accepted zero-vulnerability audit A/openworld-dependencies-after.json |
| G3 | Truthful deploy/rollback/CI and cost guide | verified | [Current README](README.md) and [operations](OPERATIONS.md): existing service only, no reseeding/new account, scoped limits and deletion-aware restore; shared hosted-CI/provider-budget owner actions retained |
| G4 | Verified public changed release | building (coordinator) | Source candidate is pushed and compiled/UI accepted; production remains unchanged. Finish G1 and the existing mirror helper rollout before deploying this service/volume |
| G5 | Existing independent mirror uses the deletion-aware helper and current-snapshot drill | building (coordinator) | Update only copied recovery.py/sync.py in the existing private runtime, preserve key/config/CLI, run its existing foreground sync; [procedure](OPERATIONS.md). Source old-backup reconciliation is tested |
| G6 | Hosted source checks | owner | New bounded workflow is configured and local24 tests/compile pass. Existing portfolio Actions allowance must be restored within an owner-chosen cap before hosted CI; no new budget authorized |

## Remaining buildable work

- G1: independent mobile measurement of the actual real-base-game studio, not the lightweight fixture. The local69/98 run is not a performance pass; no game-engine rewrite was made from a CPU-warned, early-frame result.
- Before release, coordinator updates only the existing independent mirror runtime copies (`recovery.py`, `sync.py`), preserving key/config/CLI/runtime, then runs its existing private foreground sync once. Source and old-snapshot reconciliation are tested; installed-runtime transport is not changed here.
- G4: coordinator deploys the candidate to the existing OpenWorld service/volume and performs public smoke.

## Owner / waiting

Shared inherited credential, hosted-CI allowance and provider-budget actions stay in the portfolio ledger; no duplicate owner request here. No new provider review is required for unchanged configuration.

## Log (last10)

- 2026-10-29 - Submitted-only admin preview/approval, rollback/idempotence and actual375/1440 owner review/messages/logout pass24 source cases plus browser checks. Main landmark and modal layout fixed. Actual-game69/98 CPU-warned audit remains open; coordinator owns G1, mirror runtime and rollout.

- 2026-10-29 - Scoped ZIP export, atomic account closure, durable deletion/restore reconciliation, privacy and studio modal/touch fixes pass24 source/ASGI cases and actual375/1440 UI. No real provider or production work; actual-game performance, admin and coordinator rollout remain.

- 2026-10-29 - Distilled accepted gameplay, private access, actual Sonnet journey and recovery proofs; claimed missing account-data/policy/UX/release rows only. No provider request, public change or production data touched.
