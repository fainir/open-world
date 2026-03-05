# Hacker News - Show HN Post

## Title
Show HN: Open World – A 3D browser game where AI rewrites the code as you play

## URL
https://open-world.gg

## First Comment (post immediately after submitting)

Hey HN! I built Open World — a 3D open-world game that runs entirely in the browser as a single HTML file (~5000 lines of Three.js).

The twist: there's an AI editor built in. Click the pencil icon, describe what you want in plain English — "add a day/night cycle", "make the buildings taller with neon lights", "add flying cars" — and Claude reads the entire game code, makes surgical SEARCH/REPLACE edits, and you're playing the new version in seconds.

Every version gets a unique URL you can share. So you build your dream game and send it to friends.

**Tech stack:**
- Three.js for 3D rendering (single HTML file, no build step)
- Claude (claude-opus-4-6) for code understanding and editing
- FastAPI backend that minifies the game code (~40% token reduction) before sending to Claude
- SQLite for version tracking
- The AI makes edits via SEARCH/REPLACE patches, not regenerating the whole file

**How the AI editing works:**
The entire game HTML gets minified and sent as context. Claude understands the game architecture (zone system, vehicle system, physics, etc.) and returns targeted patches. Each edit creates a new version file, so nothing is ever lost.

**Challenges I ran into:**
- Fitting ~725KB of game code into Claude's context window (solved with aggressive minification)
- Making SEARCH/REPLACE reliable (the system prompt is ~200 lines describing the codebase architecture)
- Mobile support — the game has full touch controls with virtual joystick

Would love feedback on the concept and any ideas for what to build next. Happy to answer technical questions about the architecture.
