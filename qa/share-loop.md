# Share loop on shared game pages - November 3

Goal: a shared game spreads by itself. Every `/shared/<slug>` page now has a slim bar above the game with three things:
- "Made with OpenWorld - make your own", a link to the home page
- **Remix this**
- **Share**

The share prompt that follows a successful AI edit (X4, PR #15) now uses the same one-tap share.

## What changed

- **The shared page.** `/shared/<slug>` is now a small first-party page. The game still loads from `/game/shared/<slug>` in the same opaque sandbox frame the studio uses. That means:
  - the bar never covers the game's HUD
  - game code cannot touch the bar
  - the share sheet and clipboard work
  
  The page keeps the share card tags from PR #5, uses `script-src 'self'`, can only frame our own URLs, and has no studio script or storage keys. Private, unshared and missing games still return 404.
- **Remix this.** `/remix/<slug>` sends a visitor to `/v/<id>?remix=1`. Remix was already possible: the server branches a shared version into a new private chat when the editor sends that version with no session, the same way the store's Play works. The studio now starts a fresh chat for `remix=1`, removes the flag from the address and says "Remix: describe a change and it becomes your own copy." New visitors also see the one-click ideas card over the remixed game. Railway logs can count remixes by the `/remix/` path.
- **One-tap share.** `app/static/js/share-link.js` tries the device's share sheet first, then copies the link. If both fail, the shared page shows the link selected in a small box, and the studio opens its existing link dialog. The studio's "Share your version" and the chat Share button both use it. The dialog's Copy button now falls back too, and a Share button appears there when the device has a share sheet.

## Evidence

- [Source checks](share-loop/tests.log):
  - 81 unittest, including 6 new in `tests/test_share_loop.py` and 2 for the CrazyGames zip
  - 13 node tests (5 for the share helper and 8 for analytics)
  - pip check, compile and syntax checks
  
  The updated `SharedGameCards` cases still prove escaped share cards and no private data.
- [Local real-game visitor check](share-loop/local.log). `qa/check-share-loop.mjs` ran against a disposable fixture whose shared version is the real base game, at 375 (touch) and 1440. It checked:
  - the bar, with 44px targets and no horizontal scroll
  - the game below the bar in its opaque frame
  - the game starting with its HUD
  - the share sheet receiving the right URL and title
  - the real clipboard copy
  - the manual link box
  - Made with going to `/`
  - Remix landing on `/v/<id>` with the old chat cleared and the game loaded
  
  There were zero non-GET requests and zero page or console errors. Screenshots are in `share-loop/local/`.
- [Post-edit share prompt](share-loop/prompt.log). `qa/check-share-prompt.mjs` ran against `qa/local.py --lightweight-game --included-beta`, a synthetic provider with no model call. At 375 the share sheet received `/shared/<slug>` and no dialog opened. At 1440, with no share sheet, the link was copied and the dialog said so. The existing `qa/check-first-edit.mjs` still passes.
- Headless Chrome exposes `navigator.share` but never opens it or settles it. The checks replace it with a recorder, and `qa/check-first-edit.mjs` removes it to keep testing the dialog.
- [Live equals main before release](share-loop/live-before.log): 11 public responses from origin/main 82b2e88 match live byte for byte.
