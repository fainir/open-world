# Shared demo startup verification

[OpenWorld PR #24](https://github.com/fainir/open-world/pull/24) passed all 88 source tests at its final head. The merged tree matched the tested tree. Railway marked the [existing production deployment](https://railway.com/project/0715cb1d-44c0-48c3-94e7-bedc0de00ede/service/f913ee3a-6dee-4891-8dd1-80dd849e6681?id=c9c3d130-905c-4fae-a306-766c8cc49d3f) successful for merged source `7d39cf0b3275993cb8c57aed75fedf9a0bd705f0`. Public health returned status and database okay, game files present and recovery current.

Independent HTTP checks on 13 November 2026 found both public game-frame endpoints returned the same guarded HTML for all five first-party demos. Their opaque sandbox allowed scripts and pointer lock. A direct or query-bearing GET to [the portfolio route](https://open-world.gg/play/from-portfolio) returned a fixed 302 to [Enchanted Forest](https://open-world.gg/shared/0cf0e229), with no cookie and no caching.

| Live Chrome check | Touch at 375px | Keyboard at 1440px |
|---|---|---|
| Shared page and Remix on a normal connection | One tap opened the game with touch controls | Enter opened the game with desktop controls |
| Delayed dependency in both entry points | Loading stayed visible and Start appeared when ready | Loading stayed visible and Start appeared when ready |
| Failed dependency in both entry points | Retry requested the module again, then Start opened the game | Retry and Start worked with visible keyboard focus |

Checks ran from 19:26:18 to 19:29:26 UTC. The game frame could not read the parent page’s storage. Browser checks made zero writes and zero model requests. Uncaught page errors were absent and the module errors occurred only under intentional failure injection. Under an artificial module stall, the original keyboard hints can show briefly on a phone. The normal phone controls appear after the module loads.

[Campaign measurement and browser screenshots](https://github.com/fainir/oss-growth/blob/main/qa/marketing-2026-11-13/openworld-portfolio-demo.md).
