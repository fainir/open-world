# OpenWorld live release - October29

Existing Railway deployment `faa70a28-d5e5-4ccf-80af-6d73571149b1` is SUCCESS, from accepted application source `d290e05`. Only the existing service/volume was updated; stored public base, user versions, provider configuration and stable secrets are retained. Previous compatible deployment is `e437d7f5-a452-48b8-9b7e-b63bf3d010e7`; rollback must retain current data and deletion-aware recovery helpers/evidence, never replace the volume with an older backup.

[Public HTTP proof](public-http.log) verifies200/no-store healthy database/game references/fresh deletion-backed recovery, exact tested studio/account/privacy/contact/admin HTML, anonymous account/admin401 and intentional home redirects for source/env/QA paths without source exposure. [Repeatable read-only check](check-public-http.py).

The preserved production base differs from repo index.html; local source-game90/100 was not treated as public-base evidence. A separate standard audit of https://open-world.gg/ scores96 performance/100 accessibility, no warnings, FCP/LCP1.4s,TBT10ms,CLS0. [Public report](perf/public-mobile.report.html), [actual city/intro frame](perf/public-mobile.jpg). The public base was preserved rather than overwritten with the default fixture.

[Actual public browser proof](public-browser.log), [scenario](check-public.mjs):375/1440 real base/direct opaque iframe, blocked parent storage, account/privacy/contact fit and anonymous sign-in Tab/Escape pass with zero page/console errors and no writes. Mobile Start opens actual gameplay and the vehicle selector. [Phone gameplay](public-gameplay-375.jpg), [desktop studio](public-studio-1440.jpg). The game's existing mobile landscape orientation behavior is retained. No real sign-in, account creation/deletion, contact send, owner-data access or model/provider call occurred.

The initial public smoke assumed a local-variant body class, a nonzero-size HUD container and a main tag on the legacy contact page. Inspection corrected these test assumptions to the actual overlay/computed HUD/visible vehicle controls and page heading. App behavior did not change for those fixture corrections. Final complete HTTP/browser checks pass.

## Independent current-format recovery

The already-updated private mirror uses restore contract2, with its existing key/config/pinnedCLI/runtime/hourly job preserved. After this deployment created its deletion-aware archive, one owned foreground sync completed at2026-10-29T17:25:29.530689Z. The snapshot was created at2026-10-29T17:23:23.024121Z. Encrypted copy verified, restore drill passed, drill actually ran this check and restoreContract2 were independently read back. Public health also confirms deletionsBackedUp=true. No archive/customer contents or credentials were logged.

All29 source checks/compile/syntax and actual local375/1440 account/admin/export/closure/retry/private bookmark/logout races remain accepted. [Account/source proof](account-acceptance.md). Changed private-data paths use disposable records; no destructive production test is needed. No buildable row remains; shared hosted-CI owner action remains.
