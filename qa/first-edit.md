# First AI edit in one click - November 1, 2026 (growth experiment X4)

Baseline from Railway request logs over 7 days: 420 human visitors, 180 engaged, 31 game loads, 2 AI edits (POST /api/chat), 2 shares.

## What blocked first edits

Seen as a fresh visitor on the live site in headless system Chrome at 375 (touch) and 1440:

- Phone: the game shows only a pencil icon. Nothing says the game can be changed with words, and the free allowance is invisible until the editor opens. The editor then covers the whole game (game width 0).
- Desktop: the editor opens by itself, but its three example prompts sit below the fold of a 130px message area under the creation-mode select and key button, so a visitor never sees them. The examples were also large features (day/night cycle, minimap) that a text patch edit is unlikely to land.
- The allowance reads "2 included attempts left in the rolling 24-hour allowance", which is accurate but not plain.

## What changed

- A card over the game for new visitors (no editing session yet, included mode, edits available): "Change this game with words", three one-click ideas (Make it snow, Turn the sky purple, Add a dragon), Write your own, and the plain count "2 free AI edits left" with "Each try counts, even if it fails, and comes back 24 hours after you use it."
- An idea fills and submits the normal edit box, so the existing included allowance, request reference, limits and checks apply unchanged. Caps and funding are unchanged.
- While it runs the card shows a progress bar, stage text and an elapsed clock; on failure it shows the server's reason and keeps the ideas; with none left it says so and when they come back.
- After success the private version opens with "Your version is ready" and a Share your version button (existing share link and modal) plus Try another idea.
- The card folds into a small count button when hidden or when the game takes focus on desktop. The editor's own example list now uses the same ideas.
- One-click ideas post to `/api/chat/idea`, the same handler as `/api/chat` with the same generation rate bucket, so request logs can tell them apart. Railway HTTP logs drop query strings, so a path was needed.

## Evidence

- [Source checks](first-edit/tests.log): 73 unittest cases (67 before, 6 new in tests/test_first_edit.py) and 8 analytics node cases pass; pip check, compile and overlay script syntax pass.
- [Browser check](first-edit/browser.log) with `qa/check-first-edit.mjs` against `qa/local.py --lightweight-game --included-beta` (synthetic provider, no model call): 375 and 1440 screenshots of [ideas](first-edit/ideas-375.png), [progress](first-edit/working-375.png), [ready](first-edit/ready-1440.png), [shared](first-edit/shared-375.png), [failed](first-edit/failed-375.png), [none left](first-edit/none-left-375.png) and [folded](first-edit/collapsed-375.png). The lightweight fixture proves the studio UI only, not gameplay.

## Weekly read

Count AI edit attempts as `POST /api/chat` (typed in the editor) plus `POST /api/chat/idea` (one-click idea); status 200 is a completed edit, and a saved version is followed by `GET /v/<id>`. Shares are `POST /api/versions/share`; shared plays are `GET /shared/<slug>`.
