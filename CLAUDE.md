# Open World Game - Development Guide

This is the single source of truth for how to make changes to the Open World 3D browser game. Both Claude Code and the AI game editor agent should follow these practices.

## Project Overview

A 3D open-world browser game (Three.js) wrapped in a web app with an AI chat editor. The game is a single HTML file (`index.html`, ~10K lines). The studio overlay (`app/static/overlay.html`) is injected at serve time to add the chat panel, version history, and sharing features.

**Live:** https://open-world-studio-production.up.railway.app

## Architecture

```
index.html              # The game — ALL game code lives here
zones/                  # Zone modules (lazy-loaded JS, interior mini-games)
app/
  backend/
    main.py             # FastAPI server, overlay injection, routes
    agent.py            # Claude API agent + SYSTEM_PROMPT for game editor
    auth.py             # JWT auth
    models.py           # SQLAlchemy models
    database.py         # SQLite setup
  static/
    overlay.html        # Studio UI (chat, versions, share) — injected into game HTML
    css/styles.css      # Studio page styles (not the game)
    js/                 # Studio JS (auth.js, chat.js, app.js)
```

### How the overlay works
`main.py` reads `index.html`, appends `overlay.html` before `</body>`, and serves the combined HTML. The overlay wraps all existing body content in `#ow-game-container` and adds its own `#ow-overlay-root` alongside it. The overlay uses `position:fixed` elements with `z-index:9997-9999`.

### How the AI editor works
Users send chat messages -> `main.py` forwards to `agent.py` -> Claude receives the full game code + SYSTEM_PROMPT + user request -> returns SEARCH/REPLACE patches -> patches applied to game HTML -> new version saved and served.

**Important:** The SYSTEM_PROMPT in `agent.py` must stay in sync with the actual game code. When you change game architecture (controls, systems, CSS patterns), update the relevant section in the SYSTEM_PROMPT too.

## Key Game Systems

### Player State (global variables)
```
P = THREE.Vector3         # Player position
V = THREE.Vector3         # Velocity
yaw, pitch                # Camera angles
isFlying, mode            # Movement state ('walk'/'vehicle')
currentVeh                # Mounted vehicle or null
currentWeapon             # Active weapon name
aimMode, aimTimer         # Shooting camera toggle (2s timeout)
score, comboCount         # Scoring
boostFuel                 # Boost meter (0-100)
locked                    # Game is running (not on menu)
shooting                  # Mouse/touch held down
```

### Core Functions
| Function | Purpose |
|---|---|
| `getH(x,z)` | Terrain height at world position (handles all biomes) |
| `getSurfaceH(x,z)` | Surface height including buildings |
| `fwd()` | Forward direction vector (XZ plane) |
| `rgt()` | Right direction vector (XZ plane) |
| `flyFwd()` | Forward vector including pitch (3D aiming) |
| `colBldg(x,z,p)` | Collision check at point with padding — uses spatial hash grid |
| `colBldgY(x,z,y,p)` | Collision check with height |
| `_addBldg(b)` | Register building in array + spatial grid. ALWAYS use this, never push to bldgs[] directly |
| `mountVehicle(v)` / `dismountVehicle()` | Vehicle enter/exit |
| `nearestVehicle()` | Find closest vehicle to player |
| `showTip(text)` | Display HUD message |
| `startGame()` / `stopGame()` | Game state transitions |
| `tryTrick(i)` / `tryFight(i)` | Trigger trick/fight moves |
| `openVehMenu()` / `openWpnMenu()` | Open selection menus |

### Constants
```
CS = 1500       # City size
CH = 750        # City half-size (city extends from -CH to +CH)
BK = 42         # Building block size
ST = 12         # Street width
GRAV = 26       # Gravity
WSPD = 22       # Walk speed
JFORCE = 14     # Jump force
_CELL = 40      # Spatial hash grid cell size
```

### Entity Systems
- **NPCs:** `npcs[]`, `MAX_NPCS=60`, spawn near player (20-100 units), cull at 250, distance^2 checks
- **Sharks:** `sharks[]`, `MAX_SHARKS=8`, water-only, patrol circles, shootable
- **Aliens:** `aliens[]`, `MAX_ALIENS=15`, flying discs, spawn 40-160 units from player, sporadic bursts

### Camera System
Two modes controlled by `aimMode`:
- **Normal mode:** Camera behind player at `camD` distance, smooth lerp follow. Good for flying/driving.
- **Aim mode:** Camera shifts to right shoulder (+1.2 units), follows pitch, looks in `flyFwd()` direction. Crosshair visible. Activates on fire, deactivates after 2 seconds idle.

### Weapon System
Weapons defined in `WEAPONS` object. Fire with click/touch. Hitscan checks against NPCs, sharks, aliens with per-entity hit radii. Projectile weapons (rocket, grenade, nuke) use blast radius damage.

### Zone System
Zones are lazy-loaded ES modules in `zones/`. The `ZoneManager` handles proximity detection, E-key entry, fade transitions, and module lifecycle. Each zone module exports a class with `enter(group, zone)`, `exit()`, and `update(dt)` methods. Zones render at y=-500 (underground) to isolate from the overworld.

### Vehicle System
Defined in `VEHICLE_DEFS`. Types: bike, car, jetski, canoe, hoverboard, submarine, yacht, helicopter, etc. Each has platform type (ground/water/air/snow), max speed, acceleration, and trick definitions. Spawned at fixed positions throughout the world.

## Controls — Desktop & Mobile

The game runs identically on both platforms. The `keys` object is shared — mobile touch buttons set the same key states as keyboard input.

### Desktop
| Key | Action |
|---|---|
| WASD / Arrows | Move |
| Mouse | Look (pointer lock) |
| Click | Shoot |
| Space | Jump / Fly |
| Shift | Boost |
| E | Enter zones AND mount/dismount vehicles (unified) |
| F | Vehicle mount/dismount (backward compat) |
| V | Vehicle menu |
| B | Weapon menu |
| 1-4 | Tricks |
| 5-8 | Fight moves |

### Mobile
| Element | Position | Action |
|---|---|---|
| Joystick (`#mobile-joystick`) | Bottom-left | Move |
| Touch-drag (`#mobile-cam-area`) | Full screen | Look |
| SHOOT (`#btn-shoot`) | Bottom-right | Fire weapon |
| JUMP (`#btn-jump`) | Right | Jump / Fly |
| BOOST (`#btn-boost`) | Right | Sprint / Boost |
| ENTER (`#btn-enter`) | Right | Enter zones + vehicles (unified) |
| FLIP (`#btn-trick`) | Bottom-center | Cycle tricks |
| FIGHT (`#btn-fight`) | Bottom-center | Cycle fight moves |
| VEHICLE (`#btn-veh-m`) | Bottom-center | Open vehicle menu |
| WEAPON (`#btn-wpn-m`) | Bottom-center | Open weapon menu |

### Mobile CSS Classes
- `.mobile` — on `<body>` when mobile detected
- `.mobile.playing` — in-game (controls visible)
- `.mobile #weapon-hud` — hidden (display:none!important)
- `.mobile #bottom-bar` — hidden (desktop controls bar)

### Portrait Rotation
Mobile portrait is handled by JS body rotation (not CSS media query). The `_applyRotation()` function:
1. Detects portrait via `h > w` on real viewport dims
2. Rotates body 90deg, sets explicit px dimensions
3. Overrides `window.innerWidth/Height` to return swapped values
4. Directly calls `R.setSize()` and updates `cam.aspect`

**Critical rule:** Never use `100vw`/`100vh` in CSS — use `100%` instead. Viewport units reference the real (un-rotated) viewport and break in portrait mode.

## Performance Rules

### Geometry
- Low-poly only (BoxGeometry, SphereGeometry with few segments)
- Merge repeated objects: `geoAt(geo, x,y,z)` + `mergeGeometries()` into single draw calls
- Wrap large areas (20+ meshes) in `THREE.Group` with proximity toggling

### Rendering
- Pixel ratio capped at 1.0
- Shadow map: PCFShadowMap, 1024x1024 (NOT PCFSoftShadowMap)
- Camera far plane: 6000, fog hides cutoff
- NO PointLights freely — use emissive materials for glow effects
- NO post-processing (bloom, SSAO) unless explicitly asked

### Updates
- Distance-gate expensive operations (animations, DOM updates)
- Use distance^2 checks (no sqrt)
- Throttle DOM updates (every 3rd frame for zone markers)
- Object pooling for particles, projectiles, bullet trails
- Always dispose geometry/material/texture when removing objects

### Collision
Always use `_addBldg()` to register buildings — it adds to both the array and spatial hash grid. Never `bldgs.push()` directly.

## Adding New Content

### New World Area
1. Place outside city grid (`|x| > CH` or `|z| > CH`)
2. Wrap in `THREE.Group` with proximity toggling (Manhattan distance ~400-1200)
3. Use merged geometry for repeated objects
4. Add proximity toggle in update loop near other biome toggles
5. Use `getH(x,z)` for ground height
6. Keep mesh count reasonable (~50-200 per group before merging)

### New Zone (Interior/Mini-game)
1. Create module in `zones/` following existing pattern
2. Register in `_registry.js` with position at the doorway (not building center)
3. Set radius to 5-8 for E-key proximity
4. Export class with `enter(group, zone)`, `exit()`, `update(dt)`

### New Vehicle
1. Add to `VEHICLE_DEFS` with platform type, speed, acceleration, tricks
2. Create mesh builder function
3. Spawn at a logical position in the world
4. Test on both desktop (keyboard) and mobile (touch)

### New Keyboard Action
1. Add key handler in the keydown listener
2. Add corresponding mobile button or map to existing button
3. Update desktop controls bar HTML (both overlay and in-game instances)
4. Update SYSTEM_PROMPT in `agent.py`

## Overlay (overlay.html) Rules

- `#ow-game-container` wraps all game content — uses `width:100%; height:100%` (not vw/vh)
- `#ow-overlay-root` contains all studio UI (panel, fab, modals)
- `#ow-fab` (edit button) at top-right, `#ow-fs-btn` (fullscreen) at top-left
- Panel auto-opens on desktop, NOT on mobile (mobile users see game first)
- `z-index` hierarchy: game=1-10, studio overlay=9997-9999
- Keyboard events in panel/modals call `e.stopPropagation()` to not affect the game

## Deployment

```bash
# Deploy to Railway
railway up --detach

# Local dev
app/venv/bin/python app/run.py
# Open http://localhost:8000
```

### Environment Variables
| Variable | Required | Description |
|---|---|---|
| `JWT_SECRET` | Yes | For JWT tokens |
| `DATA_DIR` | No | SQLite DB directory (default: `app/data/`) |
| `VERSIONS_DIR` | No | Saved versions directory (default: `app/versions/`) |
| `PORT` | No | Server port (Railway sets automatically) |

## Common Pitfalls

- **Don't use `100vw`/`100vh`** — breaks mobile portrait rotation. Use `100%`.
- **Don't add `requestPointerLock()` without `if(!isMobile)`** — breaks mobile.
- **Don't push to `bldgs[]` directly** — use `_addBldg()` for spatial hash registration.
- **Don't forget to update `agent.py` SYSTEM_PROMPT** when changing game architecture.
- **Don't add PointLights freely** — each costs a fragment shader pass.
- **Don't use `position:fixed` with viewport units inside body** — use percentages (body is CSS-transformed on mobile).
- **Test both desktop and mobile** for any UI or control changes.
