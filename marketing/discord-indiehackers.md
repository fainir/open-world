# Discord Messages - Ready to Post

## AI Discord Servers (Anthropic, AI Tools, etc.)

**Message:**
Just launched something I've been working on — **Open World** (open-world.gg)

It's a 3D open-world game that runs in your browser (desktop + mobile). The twist: there's a built-in AI editor. You describe changes in plain English and Claude rewrites the game code in real time.

Type "add a day/night cycle" → AI reads 5000 lines of Three.js → makes targeted code edits → you're playing the new version in seconds.

Every version gets a shareable URL. Build your version, share the link.

Would love for people to try it and see what wild stuff they create.

---

## Game Dev Discord Servers

**Message:**
Sharing a project I just shipped — **Open World** (open-world.gg)

It's a Three.js open-world game (single HTML file, ~5000 lines) with a built-in AI code editor. Players describe what they want in plain English and the AI modifies the actual game code.

The AI makes SEARCH/REPLACE patches — not regenerating the whole thing. There's a ~200 line system prompt that teaches it the game architecture (zone system, vehicle physics, collision detection, etc.).

Curious what game devs think of the concept — AI-assisted player game creation. Every version is shareable with a unique URL.

---

## Three.js / WebGL Discord Servers

**Message:**
Built a Three.js open world game that AI can edit in real time — **open-world.gg**

The entire game is a single HTML file (~725KB, ~5000 lines). Three.js 0.160 via CDN importmap. No build step.

The interesting part: there's an AI overlay where you describe changes in natural language. The backend minifies the game code (~40% token reduction), sends it to Claude, and gets back SEARCH/REPLACE patches. Each edit creates a new version with a unique URL.

Full mobile support with virtual joystick + touch camera. The AI is taught to preserve mobile compatibility when making edits.

Would love to hear from Three.js folks — what would you ask it to add?

---

# IndieHackers Post

**Title:** Open World — A 3D browser game where AI lets anyone create their own version

**Body:**
Hey IH!

Just launched **Open World** — a 3D open-world game that runs in your browser on desktop and mobile.

**The concept:** Players use a built-in AI editor to modify the game. Describe what you want in plain English → AI rewrites the game code → play your new version instantly → share via unique URL.

**Why I built it:** I wanted to make game creation accessible to everyone. You don't need to code — just describe your vision and AI builds it.

**Tech:** Three.js, Claude, FastAPI, SQLite. The entire game is a single HTML file.

**Business model exploration:**
- Currently BYOK (bring your own API key)
- Considering: freemium credits, subscription, or keeping it free and monetizing the community/marketplace

**Growth strategy:** Launching across HN, Reddit, Twitter, Product Hunt simultaneously. The shareability is built in — every version has a unique URL.

Would love feedback on:
1. The concept itself — does "AI game creation" resonate?
2. Monetization ideas
3. Growth tactics for this kind of product

Try it: https://open-world.gg
