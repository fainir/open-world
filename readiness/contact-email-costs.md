# OpenWorld contact, email and current costs - October 31

Existing `/api/contact` stored name/email/message in the private SQLite admin inbox without sending email, while the page incorrectly claimed delivery and a quick reply. Privacy already provided the existing operator Gmail; there was no Terms page. No Resend/SMTP/mail command was configured. The approved relay provides owner-only notification without a new key/account. Root owns all real messages.

Current costs: base/public play, accounts and browsing are free. Editing is bring your own Anthropic key and provider billing; OpenWorld sells no paid plan. Account-email verification/recovery remains outside this release; no new promise is made.

New submissions preserve the durable private inbox and queue a notification. Additive columns default historical rows to legacy, never mail them. A UUID is bound to the stored payload and reused across bounded retries/restarts; unknown/old attempts park for review. Only the fixed existing operator is notified through the relay; no visitor acknowledgment. Operator status distinguishes queued/retry/provider-accepted/review/historical storage, and accepted means provider acceptance only. The existing read/unread/reply channel remains.

Privacy discloses OpenWorld's separate inbox, relay hashes/metadata retention, Resend/Gmail copies and account-deletion limits. No legal entity/address, compliance guarantee, earnings or support SLA is invented. Accepted analytics/private boundaries, engine/models, export/closure and independent recovery are preserved.

44 source/ASGI/security/recovery cases pass in `qa/contact-costs/source.log`, including legacy schema migration, payload-bound duplicates, atomic concurrent claim, interrupted recovery, retry delay, receipt review and private admin denial. Actual functional UI at 375/1440 passes contact validation/503/429/network retention/same-key retry/new-message reset/crypto fallback, truthful queued status, Terms/costs and synthetic admin states/retry in `qa/contact-costs/local-ui.log`; screenshots are alongside. Lightweight game is only a functional studio fixture, not new gameplay/performance proof. Python compile and JS syntax pass. Existing-service deployment is next. All worker provider responses are mocked; source proof is separate from Root's genuine inbox/header check.


## Public release

Final application source `569d1d2` is live on the existing service, deployment `f00a3b34-adc3-4580-bc23-19b5185b7521` SUCCESS. [Exact public files and health](../qa/contact-costs/release.log) match; `/data` volume `fb7f3ec8-79cc-4ac9-8c13-c59ecef8168f` remains READY in [platform.log](../qa/contact-costs/platform.log). Health confirms database, referenced game files and deletion-aware recovery; optional analytics identifiers and current BYOK model are unchanged.

[Public 375/1440 UI](../qa/contact-costs/public-ui.log) verifies real changed pages, contact field retention/retry and current costs. Every write/mail response is intercepted, admin identity is synthetic, and the unchanged game iframe is a functional double. This is changed-screen proof, not a repeated real-account, game-generation, game-performance or provider-receipt claim. Contact link/button/error contrast is measured at least 4.5:1 and final screenshots were visually inspected. Python compile and JS syntax pass. No fresh vendor events were sent because tracking was unchanged.

Root has the live `/contact` URL for its one separately approved real notification check. A `stored/queued` API result is not proof of Gmail arrival; C3 remains waiting until root records actual provider/inbox/header evidence. No worker sent a message or created an account/key/service.

The current `railway.toml` remains unchanged. The CLI surfaced a dated Config-as-Code warning; coordinator owns verifying official guidance and a separate maintenance row. No infrastructure migration was inferred during this contact rollout. The reviewed remote SEO/share/maker/README changes were preserved; divergent local main and unrelated untracked `video/`/analytics cache remain untouched.
