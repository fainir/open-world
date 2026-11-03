# OpenWorld on CrazyGames

Prepared on 2026-11-03. Nothing is published. Creating the developer account, accepting the terms and submitting are owner steps (below).

## Verdict: go for Basic Launch

The playable base game can go to CrazyGames' Basic Launch QA. The AI editor cannot: it needs our backend and keys. So the upload is the base game alone, built by `build.py`.

What makes it a go:
- **Small.** About 2 MB in 3 files, and 444 KB zipped. The limits are 250 MB total, 1500 files, and 50 MB initial download (20 MB for the mobile homepage). [1]
- **Fast to play.** One click or tap starts it, and it needs only one JS library, which ships inside the zip. The limit is 20 s to gameplay, and Full Launch allows at most 1 click. [1][2]
- **All platforms.** It plays with mouse and keyboard, has touch controls, and runs in Chrome and Edge. [1]
- **Rule-clean once built.** The portal build removes everything their rules forbid:
  - the in-game portal to other people's games on open-world.gg (cross-promotion and external calls)
  - the install-the-app banner
  - the game requesting fullscreen on start (CrazyGames owns fullscreen)
  
  [2]

What could still fail, and the smallest fix:

| Risk | Why | Smallest fix |
|---|---|---|
| PEGI 12 call on violence | The player can shoot low-poly pedestrians for points. The build already turns red blood into light hit puffs. PEGI 12 allows non-realistic violence toward human-like characters, but their QA decides. [2][4] | If rejected: in `build.py`, make weapons skip pedestrians (one more `replace_once`). |
| Basic Launch metrics | Their benchmarks: 10+ min average playtime, 10-15% day-1 retention, 80%+ who play 1+ minute. [3] A free sandbox with mini-games may land below that; we have no data yet. | The test itself is the measurement. If metrics are low, add goals (missions or challenges) before a second Basic Launch. |
| Real phones in their app | Checked at 375 px with touch emulation only. Safe areas in their fullscreen app were not tested on a device. [1] | Check in their Preview tool on a phone before submitting (owner step 4). |
| Low-end Chromebooks | They disable games that are not smooth on 4 GB RAM. [1] Our own mobile Lighthouse score is 96, but no Chromebook was tested. | None needed before Basic Launch. |
| Full Launch | Needs the full SDK: SDK ads, plus cloud save if the game has progress. [5][6] The game has no audio, so mute does not apply, and it saves only the character style. | Later, only if Basic Launch metrics invite it. |

## Revenue (what their terms say)

- **Basic Launch pays nothing.** Ads are off and "no revenue will be shared". [6]
- **Full Launch pays a share of ad revenue, but no fixed percentage is published.**
  - The amount is set monthly from traffic and ad performance (terms 5.4). [7]
  - It requires four things (terms 5.3): no other portal's branding, the CrazyGames SDK, no other ads, and an original game.
  - Exclusivity adds 50% for two months on CrazyGames only (terms 5.5).
  - Payouts carry over until 100 EUR (terms 5.6). [7][8]
- **In-game purchases are possible but optional.** They go through Xsolla and need a Full Implementation. [8]

## What is in the zip

```
python3 release/crazygames/build.py --sdk   # openworld-crazygames-sdk.zip  (upload this one)
python3 release/crazygames/build.py         # openworld-crazygames.zip      (no SDK, zero network requests)
```

Each zip contains three files:
- `index.html`: the base game.
- `vendor/three/three.module.js` and `vendor/three/addons/utils/BufferGeometryUtils.js`: the same Three.js r160 files the live game loads. They are pinned by SHA-256.

The zip has no AI editor, no external link and no call to open-world.gg. The build stops if any of these is still in the game: `open-world.gg`, `/api/`, `fetch(`, the CDN hosts, `window.open`, `location.href=`. The build makes these changes to the base game, and stops with a clear message if the game changed and a step no longer matches:

1. Three.js loads from the zip by relative path. Their docs say never to use absolute paths. [1]
2. The cache-busting reload, which only made sense on our own site, is removed.
3. The Game Store portal (ring, marker, F action, `/api/store/random-slug`) is removed.
4. The install-the-app banner and the web app manifest are removed.
5. The game no longer requests fullscreen on mobile start. The fullscreen button was already hidden. [2]
6. Hit particles are light gray instead of red.
7. The body gets `user-select: none` and no long-press callout. [1]
8. The page title is "Open World City Sandbox".

With `--sdk` (the portal flag), the build adds the SDK v3 script from `sdk.crazygames.com` and a small bridge. The bridge calls `init`, then `loadingStart`. It calls `loadingStop` when the start screen is ready. It calls `gameplayStart` when play starts or resumes, and `gameplayStop` on the pause screen. Every call is guarded, so the game still runs if the SDK is missing or reports a non-CrazyGames site. [5]

Checked on 2026-11-03 by unzipping each zip into an empty folder, serving it on 127.0.0.1 and playing it at 375 px (touch) and 1440 px with `qa/check-crazygames-zip.mjs` (log: `qa/crazygames/zip.log`, screenshots: `qa/crazygames/`):
- **Plain zip:** zero requests outside its folder. Start, HUD, vehicle menu and movement work. There is no portal marker, no fullscreen grab, no manifest, and zero page or console errors.
- **SDK zip with a recording stand-in for the SDK:** the calls arrive in order: `init`, `loadingStart`, `loadingStop`, `gameplayStart`, `gameplayStop` (pause), `gameplayStart` (resume).
- **SDK zip with the real SDK:** the environment is `local`. The only outside host is `sdk.crazygames.com`, and there are zero errors.

## Listing copy

**Title:** Open World City Sandbox

**Short description:**
Fly a wingsuit over a 3D city, then drive, ride and explore it your way.

**Long description:**
Jump off a snowy mountain in a wingsuit and glide down into a big 3D city. Land anywhere and explore on foot, or take one of many vehicles: cars, motorbikes, bikes, ATVs, scooters, go-karts, a pogo stick and even a horse. Find the beach, the river and the mountains. Step into shops, cafes and arenas for quick mini-games: bowling, tennis, boxing, basketball, archery, go-kart and swimming races, bumper cars, a roller coaster and more. Pull off flips and tricks in the air, try different tools and gadgets, and change your character's style. No goals you have to follow: it is your city to play in.

**Controls:**

| Action | Desktop | Mobile |
|---|---|---|
| Start | Click or press any key | Tap the screen |
| Move | WASD or arrow keys | Left joystick |
| Look | Mouse | Drag on the right side |
| Jump / Boost | Space / Shift | JUMP / BOOST buttons |
| Enter, use, get on a vehicle | E (or F near a vehicle) | ENTER button |
| Vehicles menu | V | VEHICLE button |
| Tools and weapons | B, click to use | WEAPON button, SHOOT |
| Tricks / Fight | 1-4 / 5-8 | FLIP / FIGHT buttons |
| Character style | C | STYLE button |
| Pause | Esc | Pause button |

**Tags (pick the closest from their list in the form):** Open World, Sandbox, 3D, Flying, Driving, Exploration, Simulation, City

**Orientation:** landscape. **Mobile:** yes. **Progress save:** off; only the character style is saved, on the device. **In-game purchases:** none. **Multiplayer:** no.

## Images and video they require

All are mandatory. [4]
- **Covers:**
  - landscape 16:9 at 1920x1080
  - portrait 2:3 at 800x1200
  - square 1:1 at 800x800
  
  They must have no border, no text except the title, no icons or store logos, and nothing blurry.
- **Preview videos:** landscape 1080p 16:9 and portrait 1080p 2:3.
  - 15-20 s each, 50 MB at most
  - no sound, no "Play Now" text, no cursor, no black bars
  - they should open on the static cover

Drafts made from the real portal build are in `media/`:
- `cover-landscape-1920x1080.png`
- `cover-portrait-800x1200.png`
- `cover-square-800x800.png`
- `preview-landscape-1920x1080.mp4` (18 s, silent, H.264)
- `preview-portrait-1080x1620.mp4` (18 s, silent, H.264)

They were recorded in headless Chrome with software rendering, so a recording from a real GPU will look smoother. Recreate them with:
```
node release/crazygames/capture-media.mjs http://127.0.0.1:PORT <playwright/index.mjs> <out-dir>
```
Serve the unzipped plain build at that port first.

## Owner steps (exact)

1. Open https://developer.crazygames.com/ and create a developer account. This is a new third-party account and their terms, so it is the owner's click.
2. In the portal, complete payout onboarding: address, country and tax details. The docs say this is required before you can submit, and you can set payments to Hold. [8]
3. Click **Submit a game** (https://developer.crazygames.com/games) and choose HTML5. Upload `release/crazygames/openworld-crazygames-sdk.zip` from this repo: https://github.com/fainir/open-world/raw/main/release/crazygames/openworld-crazygames-sdk.zip
4. Open the game in their Preview tool (crazygames.com/preview) on a computer and a phone. Check four things: one click or tap starts it, V opens vehicles, Esc pauses, and nothing links out. [5]
5. Fill in the listing from this file: title, short and long description, controls, tags, landscape orientation, mobile yes, progress save off, no purchases. Upload the three covers and two videos from `media/`, or better ones at the same sizes.
6. Submit for Basic Launch, then share the game's portal status or link so its 7-21 day metrics can be tracked. [3]

The submission form is behind their login, so its exact field names were not confirmed. The fields above are the ones their docs mention. [1][8]

## Sources (read 2026-11-03)

1. https://docs.crazygames.com/requirements/technical/ and https://docs.crazygames.com/requirements/intro/
2. https://docs.crazygames.com/requirements/gameplay/ and https://docs.crazygames.com/requirements/quality/
3. https://docs.crazygames.com/ and https://docs.crazygames.com/resources/basic-launch-metrics/
4. https://docs.crazygames.com/requirements/game-covers/
5. https://docs.crazygames.com/sdk/intro/ and https://docs.crazygames.com/sdk/game/
6. https://docs.crazygames.com/requirements/ads/ and https://docs.crazygames.com/requirements/account-integration/
7. https://files.crazygames.com/documents/developer_terms_20250818.pdf (Developer Portal Terms, updated 18.08.2025, articles 5.3-5.6)
8. https://docs.crazygames.com/faq/ and https://docs.crazygames.com/payouts/
