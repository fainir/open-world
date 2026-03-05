---
title: "How I Built a 3D Game That AI Can Edit in Real Time"
published: false
description: "The architecture behind Open World — a Three.js game where players describe changes in plain English and Claude rewrites the code while they play"
tags: threejs, ai, webdev, gamedev
cover_image: [NEED SCREENSHOT]
---

# How I Built a 3D Game That AI Can Edit in Real Time

What if players could modify the game they're playing just by describing what they want?

That's the idea behind [Open World](https://open-world.gg) — a 3D open-world browser game where an AI reads the entire codebase, understands the game architecture, and makes targeted code edits based on natural language descriptions.

Type "add a day/night cycle with a moving sun" and 10 seconds later, you're playing under a sunset.

## The Game

The base game is a full 3D open world built with Three.js:

- **World:** City center, beach, mountains, desert, harbor, forest, festival area
- **Gameplay:** Drive vehicles, perform tricks for points, fight NPCs, glide with a wingsuit
- **Interiors:** Enter buildings — bars, shops, restaurants, sports venues
- **Platform:** Runs in any browser, full mobile support with virtual joystick

The entire game is a single HTML file — ~5000 lines of code, ~725KB. No build step, no bundler. Just Three.js imported via CDN.

## The AI Editor

Here's where it gets interesting. There's an overlay panel where users type natural language requests. The flow:

1. **User types a request** — "make the buildings taller and add neon lights"
2. **Backend minifies the game code** — strips comments, collapses whitespace, summarizes CSS (~40% token reduction)
3. **Sends to Claude** — the full minified game code + conversation history + a ~200-line system prompt
4. **Claude returns SEARCH/REPLACE patches** — not the full file, just targeted edits
5. **Backend applies patches** — creates a new version HTML file
6. **User plays the new version** — navigated to a unique URL

### Why SEARCH/REPLACE?

The game is too large to regenerate entirely on every edit. Instead, the AI makes surgical changes:

```
<<<SEARCH
const skyColor = 0x87CEEB;
const groundColor = 0x228B22;
===
const skyColor = getSkyColorForTime(gameTime);
const groundColor = getGroundColorForTime(gameTime);

let gameTime = 0;
function getSkyColorForTime(t) {
    // ... day/night cycle logic
}
>>>SEARCH
```

This is faster, cheaper, and more reliable than regenerating 5000 lines.

### The System Prompt

The key to making this work is a detailed system prompt (~200 lines) that teaches Claude the game architecture:

- How the zone system works (entry triggers, interior scenes)
- How vehicles work (spawn points, physics, controls)
- How the score/combo system works
- How collision detection is structured
- How mobile controls are implemented
- Performance rules (object pooling, draw distance, texture sizes)

Without this, Claude would make edits that break the game. With it, edits are surprisingly reliable.

### Conversation History

The system keeps the last 6 messages of conversation context, but compresses previous AI responses to just `[Applied changes: {description}]`. This saves tokens while maintaining continuity — the AI knows what it already changed.

## Version System

Every edit creates a new version:

- **Unique ID** — UUID-based filename
- **Version chain** — each version knows its parent
- **Branching** — users can go back to any version and branch from it
- **Sharing** — every version has a unique URL anyone can play

This means nothing is ever lost. You can experiment freely and always go back.

## Mobile Support

The game has full mobile support:

- Virtual joystick for movement
- Touch-drag for camera control
- On-screen action buttons
- Responsive UI that adapts to screen size

This was one of the harder parts — the AI editor needs to preserve mobile compatibility when making edits, so the system prompt explicitly includes mobile support rules.

## What's Next

The vision is a community platform where:

- Players create their own game versions
- Share them with unique URLs
- Browse and star community creations
- Build on top of each other's versions

If you want to try it: [open-world.gg](https://open-world.gg)

I'd love to hear what you build with it.

---

*Built with Three.js, Claude, FastAPI, and SQLite.*
