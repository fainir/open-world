# Actual-base mobile measurement

The October29 standard mobile Lighthouse13.6 run used the real unchanged source base game in a fresh isolated server, with headless Chrome and `--enable-unsafe-swiftshader`. It scored **69 performance /98 accessibility**, LCP1.6s,TBT2.62s,CLS0, and warned that the host CPU was slower than the calibration expects. This is **not a performance pass**. [Report](studio.html), [frame](studio.jpg).

The reported frame was captured before the game intro finished painting, so it does not establish completed game readiness. A separate actual-game diagnostic reached the OPEN WORLD intro and a game canvas with zero page errors or failed requests, using the same real source game; [diagnostic](game-diagnostic.log), [frame](game-diagnostic.jpg), [probe](../probe-game.mjs). It is not a Lighthouse pass. No provider calls or saved customer data were used.

The missing main landmark was subsequently fixed in the studio shell; two focused private-shell/isolation tests pass. The actual game's heavy initialization/rendering remains the measured unresolved startup work. Do not use the lightweight functional fixture or a blank/fallback game to close G1. An independent public mobile measurement can distinguish current host contention from product CPU work before rewriting the accepted game engine.
