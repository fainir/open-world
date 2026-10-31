# Included game-edit anchor correction

October 31, 2026. The coordinator's first genuine public included edit was a small Synthetic QA badge. The model completed, but the strict parser returned HTTP 400 and saved no game change. No automatic retry was made.

The existing prompt used `_minify_game_code` while exact patches were applied to the untouched original. That compact view collapses spaces and comments and replaces a CSS section with a placeholder. An anchor copied faithfully from that view can therefore have zero matches in the original. The generic non-unique error covers both zero and multiple matches. The source regression demonstrates this mismatch without another model call.

Included requests now show the original source verbatim, with literal-unique-anchor guidance. The parser still requires exactly one original match for every patch and creates no version until all edits pass. Existing BYOK compaction, model/output/image behavior and the retained public game are unchanged. The signed transport now checks the entire UTF8 JSON body, including escaping, system, history and envelope, against 768 KiB before any request.

[19 focused tests](claude-beta-anchor-tests.log), [all 63 source/ASGI tests](claude-beta-anchor-full.log), Python compile and the [offline full-source wire check](claude-beta-wire-check.log) pass. The largest tracked original plus actual new prompt/history/envelope is 766,901 bytes, below 786,432. The existing production volume base was read without modification: 725,574 UTF8 bytes, intentionally different from tracked index.html, with one each of the three HTML boundaries. Its exact first-request input before the extra guidance was 752,118 bytes, also below the bound. No data/volume base is replaced by this code change.

## Actual release and creation

The coordinator authorized existing-service rollout of eeb8c60. Deployment 98a1c2b1-de49-49d7-a2ca-d49d9406547f is SUCCESS. Public health returned 200; installed agent/transport source matches and the persistent 725,574-byte public base remains byte-identical. [Preservation/source checks](claude-beta-base-preserved.log).

One additional deliberate synthetic private-guest edit completed after the fix, request 2b7c6d03-0a8d-4460-9a87-8e52beeca9af. The coordinator independently reconciled the gateway row as COMPLETED: Haiku 5.5, 400,739 input / 513 output tokens, $0.201652 settled, 10.921 seconds. This was a new controlled quality test after a known parser rejection, not an unknown-outcome retry. No more model request was needed.

The strict parser applied two patches, each with exactly one original match. The resulting private version remains unshared/unpublished, adds 399 UTF8 bytes, preserves all original source text in order and leaves all four script blocks byte-identical. The initial private source equals the unchanged public base. [Exact synthetic-row read-only proof](claude-beta-real-parser.log).

## Browser evidence and its limits

The actual public app navigated to its generated private version. DevTools response-body retrieval raced navigation and failed before its body could be captured; the QA browser was closed without exporting its ephemeral guest proof. [Original capture log](claude-beta-real-anchor.log) and [retained public loading screenshot](claude-beta/real-anchor-incomplete.jpg). No access proof was changed/recovered, and no different user's rows were read.

The coordinator approved read-only recovery of only this synthetic request/version's saved HTML. That genuine 725,973-byte output remains private outside git. It was then rendered locally in the unchanged studio/opaque game sandbox, not via a reopened production private URL. [375/1440 acceptance](claude-beta-artifact-ui.log) and [read-only renderer log](claude-beta-artifact-server.log) verify real canvas/Start, mobile vehicle menu, desktop HUD, blocked parent storage, zero writes/model/account/mail, no overflow or page errors. No provider or game double was used in this artifact check.

- 375: [ready](claude-beta/actual-artifact-ready-375.jpg), [playing/mobile vehicle menu](claude-beta/actual-artifact-play-375.jpg).
- 1440: [ready](claude-beta/actual-artifact-ready-1440.jpg), [playing/desktop HUD](claude-beta/actual-artifact-play-1440.jpg).

Visual review confirms the small upper-right badge is present before/after Start. It partly overlaps the unchanged studio Edit control, so this proves source-edit/parser/game preservation rather than pixel-perfect generated layout. All original game scripts remain unchanged. No production private-URL reopen, new publication, real account, email, payment, credentials or resources are claimed.

The reusable live QA helper now captures a native fetch clone before allowing navigation and still requires an explicit paid-test gate plus caller-supplied UUID. It was syntax-checked but not rerun: no second paid request was made to improve the capture.
