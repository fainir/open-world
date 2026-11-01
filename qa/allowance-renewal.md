# Continued included editing - November 1, 2026

Nir approved continuing the existing small free daily allowance. [Betterloop PR #14](https://github.com/fainir/betterloop/pull/14) adds a reviewed renewal command; [OpenWorld PR #13](https://github.com/fainir/open-world/pull/13) corrects the comparison's implication that regular editing always requires BYOK. Both are merged and deployed on existing services. No cap, key, paid resource, purchase or auto-reload setting changed.

The old November 3 date was the central activation/funding cutoff, tied conservatively to the old promotional credit expiry. It was not the external baseline expiry. Signed-in Console revealed a separate already-granted $200 tranche expiring December 3; all-workspace/key/model cost was $96.88 over the last 30 days as of November 1 at 09:40 UTC. [Funding and independent DB evidence](https://github.com/fainir/betterloop/blob/main/ops/claude-beta-renewal.md) confirms the live cutoff is now December 1 at 00:00 UTC, with the existing five-minute admission margin. Recheck actual funding before then, without assuming another credit grant.

Limits remain $25 per rolling 30 days for OpenWorld, two actor/four network attempts per rolling 24 hours, text-only pinned Haiku, $100 active new-serving/$150 hard ceiling/$200 outer ceiling and reserve-before-call. The $100 external baseline was conservatively reimported on November 1 at 10:43:23Z, without lowering it or resetting any request history.

## Public acceptance

Existing OpenWorld deployment `817ca527-d0e2-477a-b566-0f2c1969d351` is SUCCESS, from merged main e990352. [Release readback](allowance-renewal-release.log) verifies health/database/game files/recovery, included Haiku metadata and exact live comparison HTML equal to main. Runtime source did not change for the funding extension; the public copy change is the sole user-visible release.

Fresh anonymous browser contexts followed the comparison's Play link into the actual public studio at both widths. [Live log](allowance-renewal-live.log) and screenshots show:

- [375px guest](allowance-guest-375.png), [1440px guest](allowance-guest-1440.png): "2 included attempts" per rolling 24 hours, Included Claude beta selected, Sign In still offered, no own-key or signup requirement, no horizontal overflow or page errors.
- [375px comparison](allowance-rosebud-375.png), [1440px comparison](allowance-rosebud-1440.png): conditional two-attempt allowance, BYOK for larger edits or unavailable capacity, no November 3/end-date promise.

Personal Chrome independently showed the same guest allowance. Its sizing control did not reliably target the guest tab, so the saved responsive verdict uses automated QA of our own site in fresh headless Chrome contexts. No personal browser profile or credentials were used by that QA.

## One real synthetic guest edit

Exactly one deliberate public included request asked for a small bottom-center "Guest trial verified" badge. The app navigated while DevTools was reading the response body, hitting the repository's documented capture race. [Capture limitation](allowance-real-edit-capture.log). The test was not repeated and no private capability was exported or reconstructed.

Instead, scoped read-only production verification of that exact synthetic request confirms the gateway completed Haiku with 400,783 input / 295 output tokens and $0.201129 settled cost. [Gateway metadata](https://github.com/fainir/betterloop/blob/main/qa/allowance-real-edit-gateway.log). The matching [OpenWorld persisted row/artifact readback](allowance-real-edit-persisted.log) confirms completed status, private guest version 2, badge saved, unshared/unpublished, 366 added bytes, four original script blocks byte-identical and parent equal to the public base. Public base bytes were independently checked again. This is saved-result/accounting proof, not a claim that the private production URL was reopened after capture closed.

[67 source/ASGI cases](allowance-renewal-tests.log) pass, and PR #13's [hosted CI](https://github.com/fainir/open-world/actions/runs/41298794449) passed dependency consistency, compilation and tests. Repeat the read-only public check with `node qa/check-allowance-renewal.mjs` after installing Playwright under `.runtime/allowance-qa`; the retained script cannot dispatch a model call. [Exact synthetic readback script](allowance-private-readback.py) reads only that known test row and its artifacts.

No owner action was required. Next funding review is due before December 1; shared budget exhaustion can still pause included editing earlier.
