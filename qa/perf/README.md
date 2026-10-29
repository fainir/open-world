# Actual-base mobile acceptance

The October29 final standard mobile Lighthouse13.6 run scores **90 performance /100 accessibility**, FCP/LCP1.1s,TBT180ms,CLS0, with **no run warnings**. It used the unchanged real source base game in a fresh isolated server. The [report](studio.html) and visually reviewed [final frame](studio.jpg) show the actual city and OPEN WORLD intro. This is not a lightweight or fallback scene.

The public base now loads directly in its existing opaque iframe response instead of buffering and reparsing the whole game as parent `srcdoc`. Private versions still use authenticated fetch and isolated `srcdoc`; no stored game HTML, game engine, generated version or provider configuration changed. The explicit mobile Start action can request fullscreen without a policy error. A missing base has an isolated, readable retry page.

[Actual-touch browser check](../game-startup.log), [scenario](../check-game-startup.mjs): the real engine initializes, Tap to play enters gameplay, the HUD/shoot control appears, and the vehicle selector opens. Studio storage remains inaccessible from the game. Page errors and console errors are zero. [Ready city](actual-game-ready.jpg), [actual vehicle selector](actual-game-vehicle.jpg). No provider call or customer data was used.

The same default mobile audit settings and headless software-rendering flags were retained from the earlier69/98 CPU-warned result. Trace attribution identified startup style/layout work before the transport change; the final report has no CPU warning. The independent public PageSpeed API returned429 and provides no additional verdict. The accepted evidence is this complete local actual-game measurement plus its functional check. Coordinator rollout/public smoke is accepted. The preserved production base differs from this source default; a separate actual-public96/100 report and gameplay acceptance are linked in [live release](../public-release.md).

Reproduce with `qa/local.py` in its default real-game mode, then:

```sh
CHROME_PATH='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' lighthouse "$OWNED_LOOPBACK_URL" --only-categories=performance,accessibility --chrome-flags='--headless=new --enable-unsafe-swiftshader' --output=html --output-path=qa/perf/studio.html --quiet --no-enable-error-reporting
```

Use Lighthouse13.6 and Node24, serialize the measurement with other audits, and close the audit browser afterward. `--lightweight-game` proves only account/editor functionality and is never a game/performance pass.
