# Public studio analytics acceptance - October30

The generated public studio overlay and public privacy page now support Google Analytics, Mixpanel and Betterloop with device opt-in, withdrawal and fixed content-free event names. Version/account/admin/contact/game surfaces do not collect. Existing game, private data and recovery behavior are preserved.

- Thirty disposable SQLite/ASGI cases pass, including public-only validated configuration and no trackers on account/admin/contact. Eight focused analytics cases cover initial consent, missing values, DNT/GPC/storage denial, exact routes, sensitive payload omission, late SDK and failed-withdrawal memory lock. [ASGI](analytics-asgi.log), [analytics cases](analytics-source.log).
- Actual public shell375/1440 passes consent off/allow, three intercepted transports, fixed sanitized events, exactly one pageview, withdrawal/identifier cleanup/reload, modal focus/Tab/fit, DNT/GPC, late SDK and failed-write/focus/pageshow recovery. [Browser log](analytics-browser.log), [phone](analytics-choices-375.jpg), [desktop](analytics-choices-1440.jpg). The existing lightweight fixture establishes studio/analytics UI only; no game or performance verdict is inferred.
- The storage-denial analytics UI check uses the actual `/privacy` page to isolate analytics: the existing studio bootstrap itself requires localStorage and throws when the browser wholly denies it. Normal studio375/1440 passes; this run does not claim the studio works without storage.

All vendor responses were intercepted, so production receipt remains unverified. The coordinator must configure matching public `GA_ID`, `MIXPANEL_TOKEN`, `BETTERLOOP_KEY`, disable GA enhanced measurement, deploy the new Betterloop exact-path/discard SDK first, then roll out this existing service and verify public consent/receipt. Preserve the SQLite/game volume and independent mirror.

New integrations request `sdk.js?v=20261030` so an older cached SDK cannot bypass the new exact-path and discard controls. Eight focused transport/privacy cases pass with an explicit cache-version assertion; previous full consent UI acceptance remains linked.

## Existing-service rollout preparation - October30

The coordinator matched the existing Google/Mixpanel projects, explicitly disabled Google enhanced measurement and set/read back public `GA_ID`, `MIXPANEL_TOKEN` and `BETTERLOOP_KEY` with skip-deploys. The release worker independently confirmed the accepted `faa70a28` deployment is still SUCCESS on the existing `open-world-studio` service, with the same `/data` volume. No deployment has started at this preparation step.

Wait for the coordinator's verified Betterloop SDK/server release before `railway up --project 0715cb1d-44c0-48c3-94e7-bedc0de00ede --service f913ee3a-6dee-4891-8dd1-80dd849e6681 --environment production --detach`. Preserve current data, existing secret configuration, snapshots and deletion-aware recovery. The accepted analytics branch descends from remote main; divergent local main is not reset or rebased. Unrelated untracked `video/` and `qa/analytics-sdk-cache.log` remain untouched.

The prepared actual public smoke is `node qa/check-analytics-live.mjs /Users/nirfeinstein/Documents/shelf/node_modules/playwright/index.mjs`. Its syntax is checked; no production receipt is claimed until it runs after deployment. It drives actual consent/Store UI at375/1440 with genuine provider responses, checks private query/hash omission, withdrawal, saved-allow account/contact exclusion and GPC. No model generation, signup, contact send, email or paid action is included. Provider HTTP acceptance and dashboard visibility are separate verdicts.
