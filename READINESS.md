# OpenWorld - Readiness

Every row serves [GOAL.md](GOAL.md) and portfolio PT08. Prior valid evidence root: `/Users/nirfeinstein/Documents/ChatGPT/almost finished projects + marketing/artifacts/production-readiness-2026-10-26` (A). Existing accepted game/provider/recovery tests are not repeated without a changed concern.

Production https://open-world.gg. FastAPI/SQLite/static studio; exact run/test/deploy/recovery commands in [PRODUCT.md](PRODUCT.md) and [OPERATIONS.md](OPERATIONS.md). Current accepted analytics release branch is codex/website-analytics; source and existing-service deployment are accepted below.

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
| G1 | Main mobile Lighthouse performance/accessibility >=90 | verified | Actual public retained base96/100, warnings[],FCP/LCP1.4s,TBT10ms,CLS0; real city/intro visually reviewed. Local actual source game90/100 retained. [Public report](qa/perf/public-mobile.report.html), [release](qa/public-release.md) |
| G2 | Current changed-source tests and dependency/security checks | verified | [29 source/ASGI checks](qa/account-checks.log), frontend syntax and Python compile pass; dependency versions unchanged from accepted zero-vulnerability audit A/openworld-dependencies-after.json |
| G3 | Truthful deploy/rollback/CI and cost guide | verified | [Current README](README.md) and [operations](OPERATIONS.md): existing service only, no reseeding/new account, scoped limits and deletion-aware restore; shared hosted-CI/provider-budget owner actions retained |
| G4 | Verified public changed release | verified | Existing rollout SUCCESS; exact public HTML/health/access guards, actual375/1440 game/start/vehicle/account/privacy/contact/sign-in and new-format independent snapshot/restore pass. No writes/provider/owner data. [Live release/rollback](qa/public-release.md) |
| G5 | Existing independent mirror uses the deletion-aware helper and current-snapshot drill | verified | Coordinator atomic two-helper update and owned foreground sync succeeded at2026-10-29T17:06:57Z; encryptedCopyVerified/restoreDrillPassed/restoreDrillRanThisCheck true, contract2; key/config/CLI/runtime preserved. [Selected evidence](qa/account-acceptance.md) |
| G6 | Hosted source checks | owner | New bounded workflow is configured and local29 tests/compile pass. Existing portfolio Actions allowance must be restored within an owner-chosen cap before hosted CI; no new budget authorized |

| T1 | Optional public studio analytics, explicit device choice and safe payload/route boundaries | verified | [Source and actual375/1440 acceptance](qa/analytics.md):30 ASGI and8 analytics cases, all three transports intercepted, withdrawal/races and memory lock pass. No real provider receipt is claimed |
| T2 | Existing analytics project configuration and public rollout/receipt | verified | [Actual public release](qa/analytics.md), [live375/1440](qa/analytics-live.log), [exact public config/source/health](qa/analytics-public-http.log). Genuine Google204, Mixpanel200/body1 and cross-origin Betterloop200/bodyok; actual Store action to all3, no pre-consent requests, sanitized context, withdrawal, private account/contact exclusion and GPC pass. Same existing service/data volume; dashboard visibility is not inferred from HTTP proof |

## Contact, email and current costs - October 31

| ID | Flow or gate | Status | Evidence / next action |
|---|---|---|---|
| C1 | New contacts remain durable and notify the operator; failures are visible and bounded | verified | [44 source/ASGI/security/recovery cases](qa/contact-costs/source.log), [real public375/1440 changed screens](qa/contact-costs/public-ui.log) and [exact source/health](qa/contact-costs/release.log) pass. Existing-service f00a3b34 SUCCESS; legacy-safe migration, duplicate/atomic claim/retry/review boundaries tested with mocked transport. Genuine notification proof remains C3. [Handoff](readiness/contact-email-costs.md) |
| C2 | Read accurate Contact, Privacy, Terms and Free / Bring your own key / Paid labels | verified | Free play/account; own Anthropic key billed by provider; no paid OpenWorld plan. No verification/recovery email promise. |
| C3 | Actual new contact notification reaches Gmail with correct reply address | verified | Root's approved real phone submission returned stored/queued at23:39:58Z and Gmail INBOX received it at23:39:59Z on October30 UTC; exact visitor Reply-To preserved. [Handoff](readiness/contact-email-costs.md) and coordinator artifacts/contact-email-costs.md. No worker sends, label manipulation or separate OpenWorld reply is claimed. |

## Limited included Claude beta - October 31

| ID | Flow or gate | Status | Evidence / next action |
|---|---|---|---|
| B1 | Prepare a bounded Claude edit without signup or key, with optional BYOK | verified | [Offline candidate acceptance](qa/claude-beta/acceptance.md): actual375/1440 functional UI, current15 focused cases, guest quotas, stop-waiting/reload/replay, private result and unchanged BYOK. Provider/game doubles are explicit; no genuine model quality or public release claimed. [Track](readiness/claude-beta.md) |
| B2 | Shared money gate, signed caller and honest availability/cost/privacy UI | verified | Coordinator enabled the existing b3dcfa2 service through the accepted signed gateway after global GO; no direct owner-key fallback. Haiku5.5 input768KiB/output8000, actor2/IP4 per rolling24h, $25 rolling30d app cap. New full-wire bound is part of B3 correction. [Track](readiness/claude-beta.md) |
| B3 | Real limited creation quality and exact changed public release | verified | Exact-source fix is live on the existing service; health/source and persistent base match. One genuine Haiku edit completed, two strict unique patches saved a private version, and all original game scripts remain unchanged. Its actual saved HTML passes Start/canvas/sandbox at 375/1440 locally; real public navigation succeeded, but a CDP body race prevented reopening that private URL. The badge partly overlaps the existing studio Edit button, so pixel-perfect layout is not claimed. [Acceptance and scope](qa/claude-beta-anchor-fix.md) |

| B4 | Continue the small free daily allowance after the original November 3 cutoff | verified | [November 1 renewal and public acceptance](qa/allowance-renewal.md). Betterloop PR #14 and OpenWorld PR #13 merged/deployed; independent DB readback confirms December 1 cutoff with unchanged caps/key/profiles. Fresh public guests get 2 included attempts at 375/1440, comparison copy is conditional with no stale end date, and one real guest edit saved a private version for $0.201129. Funding review due before December 1. |

## Growth experiments - November 1

| ID | Flow or gate | Status | Evidence / next action |
|---|---|---|---|
| X4 | A new visitor reaches a first AI edit in one click and is asked to share it | waiting | [Local acceptance](qa/first-edit.md): 73 unittest and 8 node cases, synthetic 375/1440 ideas, progress, ready/share, failure and none-left states. Next: merge, deploy on the existing service, live 375/1440 check with one real included edit. Weekly read counts `POST /api/chat` plus `POST /api/chat/idea`. |

## Remaining buildable work

No buildable row remains in this scoped release. The limited included beta is deployed and its genuine model/parser/private-save result is accepted with the explicit browser-capture and generated-layout limits above. Earlier gameplay, private data, analytics, contacts and recovery proofs remain valid. Shared owner/provider actions stay in the portfolio ledger.

## Owner / waiting

Shared inherited credential, hosted-CI allowance and provider-budget actions stay in the portfolio ledger; no duplicate owner request here. No new provider review is required for unchanged configuration.

## Log (last10)

- 2026-10-31 - Released the exact-source included patch correction. 19 focused / all 63 source cases pass; one genuine Haiku creation saved two unique patches without changing original scripts or the public base. Exact saved private artifact Start/canvas/sandbox passes 375/1440 locally; public navigation succeeded but its CDP response capture raced navigation. No model replay, access change or publication.

- 2026-10-31 - Released durable new-contact notifications, honest failure/retry/admin status, Terms and visible costs.44 source/ASGI cases and actual375/1440 changed UI/contrast pass; public source/health and existing/data volume verified. All worker writes/mail mocked; root independently verified genuine Gmail receipt/Reply-To. Existing analytics, game/model, recovery and unrelated main/video files preserved.

-2026-10-30 - Existing-service analytics deployment SUCCESS; exact public source/config/health and actual375/1440 consent/Store actions to Google/Mixpanel/Betterloop pass, including cross-origin ingest200, withdrawal/private-route/GPC exclusion and zero page errors. Same/data volume; no generation/signup/send/payment. Dashboard visibility is a separate coordinator observation.

-2026-10-30 - Public studio/privacy analytics source passes30 ASGI+8 focused cases and actual375/1440 intercepted-provider controls, payloads, withdrawal and failed-write memory lock. Configuration/real receipt/public rollout remain T2; no real provider/game/data/recovery change.

-2026-10-29 - Existing public rollout accepted. Retained public base96/100, actual375/1440 game/UI/access/source checks and current deletion-aware encrypted-copy/restore drill pass. No real account/provider/message operation; only hosted-CI owner row remains.

- 2026-10-29 - Actual-base mobile90/100 has no warnings and paints the real city/intro. Direct opaque public startup, actual touch Start/vehicle, private bookmark/logout race and mobile missing-base retry pass;29 source cases/compile/syntax pass. Existing mirror contract2 rollout/drill verified. Coordinator owns public rollout/new-format snapshot sync.

- 2026-10-29 - Submitted-only admin preview/approval, rollback/idempotence and actual375/1440 owner review/messages/logout pass24 source cases plus browser checks. Main landmark and modal layout fixed. Actual-game69/98 CPU-warned audit remains open; coordinator owns G1, mirror runtime and rollout.

- 2026-10-29 - Scoped ZIP export, atomic account closure, durable deletion/restore reconciliation, privacy and studio modal/touch fixes pass24 source/ASGI cases and actual375/1440 UI. No real provider or production work; actual-game performance, admin and coordinator rollout remain.

- 2026-10-29 - Distilled accepted gameplay, private access, actual Sonnet journey and recovery proofs; claimed missing account-data/policy/UX/release rows only. No provider request, public change or production data touched.
