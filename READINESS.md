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
| A1 | Download the signed-in caller's profile, chats and generated game files | building (openworld_finish) | Add scoped export without credentials or another user, then real download acceptance |
| A2 | Close an account safely, remove active owned data/files and preserve other users | todo | Password/typed confirmation, atomic failure recovery and exact privacy limits |
| A3 | Read accurate privacy/storage/provider/retention/contact disclosures | todo | Public policy is missing; current contact page alone is not the policy |
| U1 | Sign-in, store, history, key entry, account and contact at375/1440 | todo | Only missing UI coverage; preserve accepted game playback |
| U2 | Modal focus/keyboard,44px controls and loading/error/empty states | todo | Verify actual remaining states and fix concrete failures |
| G1 | Main mobile Lighthouse performance/accessibility >=90 | todo | Actual studio/game surface, no blank/fallback measurement |
| G2 | Current changed-source tests and dependency/security checks | todo | Reuse unchanged dependency audit where valid; no real model call |
| G3 | Truthful deploy/rollback/CI and cost guide | todo | Update stale README model/new-account instructions; preserve existing services |
| G4 | Verified public changed release | todo | Coordinator deploys only after candidate acceptance |

## Owner / waiting

Shared inherited credential, hosted-CI allowance and provider-budget actions stay in the portfolio ledger; no duplicate owner request here. No new provider review is required for unchanged configuration.

## Log (last10)

- 2026-10-29 - Distilled accepted gameplay, private access, actual Sonnet journey and recovery proofs; claimed missing account-data/policy/UX/release rows only. No provider request, public change or production data touched.
