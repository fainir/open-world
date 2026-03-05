# Reddit Posts - Ready to Copy/Paste

---

## r/artificial

**Title:** I built an open-world 3D game that AI edits in real time — describe what you want and it rewrites the game code while you play

**Body:**
I just finished building Open World — a 3D open-world game that runs in your browser (desktop and mobile).

The twist: there's an AI editor built in. You click the edit button, type something like "add a day/night cycle with a moving sun" or "make all buildings neon-lit cyberpunk style" — and Claude reads the entire game codebase, makes targeted code edits, and you're playing the new version in seconds.

Every version gets a unique URL. You build your version, share the link, and anyone can play it.

The game itself has driving, tricks, combat, wingsuit gliding, different biomes (city, beach, mountains, desert), interiors, NPCs — all in a single HTML file running Three.js.

The AI doesn't regenerate the whole game — it reads ~5000 lines of code, understands the architecture, and makes surgical SEARCH/REPLACE patches. Each edit creates a new version so nothing is lost.

Works on desktop and mobile (full touch controls with virtual joystick).

Try it: https://open-world.gg

Would love to hear what you'd build with it.

---

## r/gaming

**Title:** I made a game where you just describe what you want and AI builds it in real time — open world, runs in your browser, works on phone too

**Body:**
Been working on this for a while. It's a 3D open-world game — you can drive cars, do tricks off ramps, fight NPCs, glide with a wingsuit, explore different areas (city, beach, mountains, desert).

But the real feature: there's an AI edit button. You describe any change you want — "add flying cars", "make it snow everywhere", "add a racing track" — and the AI actually rewrites the game code and you're playing your new version in seconds.

Every version you make gets its own link. So you can build your dream game and share it with friends.

No downloads. Runs in your browser on desktop and mobile.

https://open-world.gg

What would you ask the AI to add?

---

## r/indiegaming

**Title:** After months of work, I finished my open-world browser game where players use AI to create their own versions — describe changes in plain English and AI modifies the code in real time

**Body:**
Hey r/indiegaming! Just launched Open World — a 3D open-world browser game with a unique twist.

**The game:** Drive vehicles, perform tricks, fight, glide with a wingsuit, explore a world with a city center, beach, mountains, desert, harbor, forest, festival area, and tons of interiors. Full mobile support with touch controls.

**The twist:** Built-in AI editor. Click the edit button, describe what you want in plain English, and the AI rewrites the actual game code. Add new mechanics, change the world, create new areas — whatever you can describe.

**The community angle:** Every version gets a shareable URL. Players build their own versions and share them. The goal is a community of player-created game versions.

Built with Three.js, runs entirely in the browser as a single HTML file. No downloads, no installs.

https://open-world.gg

Feedback welcome — especially on the concept of AI-assisted player game creation.

---

## r/webdev

**Title:** I built a 5000-line Three.js game in a single HTML file with an AI editor that lets users rewrite the code in real time via natural language

**Body:**
Wanted to share a project I just finished: Open World — a 3D open-world game that runs as a single HTML file (~725KB) with Three.js.

The interesting technical challenge: I built an AI editor overlay where users describe changes in plain English, and Claude reads the entire game codebase, understands the architecture, and makes surgical SEARCH/REPLACE patches to modify the game.

**Tech stack:**
- Three.js 0.160 (imported via CDN, no build step)
- FastAPI backend
- Claude claude-opus-4-6 for code editing
- SQLite for version tracking
- The entire game code gets minified (~40% token reduction) before being sent as context

**Challenges:**
- Fitting 725KB of game code into an LLM context window (aggressive minification of JS + CSS stripping)
- Making SEARCH/REPLACE edits reliable (~200 line system prompt describing game architecture)
- Full mobile support with virtual joystick + touch camera
- Version branching — users can pick any previous version and branch from it

Every edit creates a new version with a unique URL. Works on desktop and mobile browsers.

https://open-world.gg

Happy to go deeper on any part of the architecture.

---

## r/SideProject

**Title:** I built Open World — a 3D browser game where AI lets anyone create their own version by describing changes in plain English

**Body:**
Just shipped this after months of work.

**What it is:** A 3D open-world game (Three.js) that runs in your browser. Drive cars, do tricks, fight, explore. Desktop + mobile.

**What makes it different:** Built-in AI editor. Users describe changes in natural language → AI rewrites the game code → new playable version in seconds. Every version gets a shareable URL.

**The vision:** A platform where anyone can create and share their own game version without coding. Describe your dream game, AI builds it, share the link.

**Stack:** Three.js, FastAPI, Claude, SQLite, single HTML file

https://open-world.gg

Would love feedback on the concept and growth ideas.

---

## r/ChatGPT (or r/ClaudeAI)

**Title:** I built a 3D game where Claude rewrites the code in real time based on what you describe — "add flying cars" and it just does it

**Body:**
Built an open-world 3D browser game with an AI editor powered by Claude.

How it works:
1. Open the game (runs in browser, desktop + mobile)
2. Click the edit button
3. Type what you want: "add a day/night cycle", "make buildings taller with neon lights", "add a minimap"
4. Claude reads the entire game codebase (~5000 lines), understands the architecture, and makes targeted code edits
5. You're playing the new version in seconds

The AI doesn't regenerate everything — it makes surgical SEARCH/REPLACE patches. Each edit creates a new version with a shareable URL.

The system prompt is ~200 lines describing the game architecture so Claude understands the zone system, vehicle system, physics, collision detection, etc.

Some fun things to try:
- "Add a day/night cycle with a moving sun"
- "Make it rain with particle effects"
- "Add a minimap in the corner"
- "Create a racing mode with checkpoints"

https://open-world.gg

What would you ask it to build?
