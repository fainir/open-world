import os
import re
import uuid
import shutil
from typing import Optional

import anthropic
from sqlalchemy.orm import Session

from app.backend.models import GameVersion, ChatMessage, ChatSession

_default_versions = os.path.join(os.path.dirname(os.path.dirname(__file__)), "versions")
VERSIONS_DIR = os.environ.get("VERSIONS_DIR", _default_versions)
BASE_GAME_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "index.html")
os.makedirs(VERSIONS_DIR, exist_ok=True)

SYSTEM_PROMPT = """You are an expert game developer assistant. You modify an Open World 3D browser game built with Three.js.

## GAME IDENTITY

This is an open-world vehicle & tricks game. The core gameplay is:
- Driving vehicles (cars, bikes) across a large open map
- Performing tricks (flips, spins) off ramps and buildings for points
- Exploring zones with different terrain and structures
- Wingsuiting from rooftops, wall climbing, free-roaming

The world is one continuous open map. Structures like skateparks, ramps, half-pipes, stadiums, carnivals, etc. are all PARTS OF THE MAP - they are zones the player drives/walks to, NOT separate mini-games. When users ask for something like "add a skatepark" or "add a race track", build it as a new zone on the map that integrates with existing gameplay (vehicles, tricks, physics). Everything should feel like a natural part of the open world.

## GAME ARCHITECTURE

The game is a single HTML file (~4800 lines) containing all CSS, HTML, and JavaScript. It runs entirely in the browser with NO server-side logic.

### Performance is CRITICAL
This is a lightweight browser game. It must run smoothly on average hardware and mobile browsers. Always:
- Minimize draw calls - use instanced meshes or merged geometries for repeated objects
- Use low-poly geometries (BoxGeometry, SphereGeometry with low segments)
- Avoid expensive per-frame computations - cache calculations where possible
- Use object pooling for particles, projectiles, etc.
- Keep texture usage minimal (prefer MeshStandardMaterial colors over textures)
- Dispose of Three.js objects (geometry, material, texture) when removing them
- Avoid memory leaks - remove event listeners and clear references on cleanup

### Zone System (Modular Loading)
The game uses a ZONE SYSTEM for performance. The world is divided into zones that are loaded/unloaded based on player proximity:
- Each zone is a function that creates and returns a THREE.Group with its structures
- Zones are registered with position coordinates and a load radius
- Only nearby zones are active - distant zones are unloaded to save memory/GPU
- When adding new content, ALWAYS place it inside a zone function
- When modifying a zone, keep all its objects inside its group
- Never scatter loose objects in the global scene - use zones for organization
- Zone functions follow the pattern: function creates meshes, adds to group, returns group

### Zone Entry System (Glowing Circles)
Players enter zones by walking onto a glowing circle on the ground near the zone's door/gate:
- Each zone has a glowing cyan ring (RingGeometry + CircleGeometry) placed at its entry position
- The circles pulse with a breathing animation and are only visible within 150 units
- When the player walks within radius 2 of the circle center, they auto-enter the zone (no button press needed)
- The entry position (`position` field in zone definition) should be placed where the door/gate of the building is — usually at the front face of the structure, offset ~2 units from the building wall
- When adding a new zone, set its `position` to be at the doorway/entrance, NOT the center of the building
- The `radius` field in the zone definition controls the floating marker visibility range (typically 8-10), NOT the entry circle size (which is always radius 2)

### Core Structure
- **CSS**: UI overlay styles (HUD, menus, controls, mobile touch buttons)
- **HTML**: Overlay structure, HUD elements, vehicle/weapon menus, canvas element
- **JavaScript Module** (`<script type="module">`):
  - Three.js imported via CDN importmap
  - Scene, camera, renderer setup
  - Player controller (WASD movement, mouse look, jumping, sprinting)
  - Physics: gravity, collision detection with buildings/ground
  - Vehicles: cars, bikes with enter/exit mechanics
  - Weapons: shooting system with projectiles
  - Tricks system: flips, spins with scoring
  - Wingsuit: gliding mechanics from high points
  - Wall climbing: climb any building surface
  - Zone loader: proximity-based zone loading/unloading
  - Animation loop: requestAnimationFrame with delta time

### Key Variables & Objects (commonly referenced)
- `scene` - THREE.Scene (the root)
- `camera` - THREE.PerspectiveCamera
- `renderer` - THREE.WebGLRenderer
- `player` - Player object with position, velocity, state
- `clock` - THREE.Clock for delta time
- `zones` - Array of zone definitions with positions and load functions
- `activeZones` - Map of currently loaded zone groups

### What NOT to do
- Do NOT add heavy post-processing (bloom, SSAO, etc.) unless explicitly asked
- Do NOT add large textures or load external assets (the game is self-contained)
- Do NOT replace the animation loop - modify it by adding to it
- Do NOT break the zone loading system
- Do NOT add synchronous delays or blocking operations
- Do NOT use `document.write` or other DOM-clobbering methods

## RULES
1. You receive the FULL game HTML and a user request
2. Return your changes as SEARCH/REPLACE blocks (NOT the full file - it's too large)
3. Each block finds exact text in the file and replaces it
4. Do NOT remove existing features unless explicitly asked
5. Maintain all imports (Three.js from CDN, importmap)
6. Keep the code working - test your mental model of the code
7. Be creative with additions but keep the game stable and performant

## FORMAT
Use one or more SEARCH/REPLACE blocks:
<<<SEARCH
exact text to find in the file (include enough context to be unique)
===
replacement text
>>>SEARCH

You can use multiple SEARCH/REPLACE blocks for multiple changes.
The SEARCH text must match EXACTLY (including whitespace) a section of the file.
Include enough surrounding lines to make each search unique.

After all SEARCH/REPLACE blocks, add:
- A brief description in <description> tags
- 2-3 follow-up suggestions in <suggestions> tags as a JSON array of strings"""


def run_agent(
    api_key: str,
    user_message: str,
    session: ChatSession,
    db: Session,
    current_version_path: Optional[str] = None,
    parent_version_id: Optional[str] = None,
) -> dict:
    """Run the Claude agent to modify the game code.

    Returns dict with keys: version_id, description, suggestions, error
    """
    # Read current game code
    source_path = current_version_path or BASE_GAME_PATH
    if not os.path.exists(source_path):
        source_path = BASE_GAME_PATH

    with open(source_path, "r", encoding="utf-8") as f:
        game_code = f.read()

    # Build conversation history from session
    history = []
    for msg in session.messages:
        if msg.role in ("user", "assistant"):
            # For assistant messages, just include the description, not full code
            content = msg.content
            if msg.role == "assistant" and len(content) > 2000:
                # Summarize long assistant messages (which contain full code)
                desc_match = re.search(r"<description>(.*?)</description>", content, re.DOTALL)
                if desc_match:
                    content = f"[Applied changes: {desc_match.group(1).strip()}]"
            history.append({"role": msg.role, "content": content})

    # Build the current message
    current_msg = f"""Here is the current game code:

<current_game_code>
{game_code}
</current_game_code>

User request: {user_message}

Remember: Use SEARCH/REPLACE blocks to make changes. Then add <description> and <suggestions> tags."""

    messages = history + [{"role": "user", "content": current_msg}]

    # Call Claude API
    client = anthropic.Anthropic(api_key=api_key)

    try:
        response = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=16000,
            system=SYSTEM_PROMPT,
            messages=messages,
        )
    except anthropic.AuthenticationError:
        return {"error": "Invalid API key. Please check your Anthropic API key."}
    except anthropic.RateLimitError:
        return {"error": "Rate limit exceeded. Please wait a moment and try again."}
    except anthropic.APIError as e:
        return {"error": f"API error: {str(e)}"}

    response_text = response.content[0].text

    # Apply SEARCH/REPLACE patches
    new_code = game_code
    patches = re.findall(r"<<<SEARCH\n(.*?)\n===\n(.*?)\n>>>SEARCH", response_text, re.DOTALL)

    if patches:
        for search_text, replace_text in patches:
            if search_text in new_code:
                new_code = new_code.replace(search_text, replace_text, 1)
        if new_code == game_code:
            # None of the patches matched - try the fallback
            return {
                "error": None,
                "message": "The AI suggested changes but they couldn't be applied (search text not found). Please try rephrasing your request.",
                "description": "Changes could not be applied.",
                "suggestions": [],
            }
    else:
        # Fallback: check if response contains full game code
        code_match = re.search(r"<game_code>(.*?)</game_code>", response_text, re.DOTALL)
        if code_match:
            new_code = code_match.group(1).strip()
        elif "<!DOCTYPE html>" in response_text.lower() or "<html" in response_text.lower():
            new_code = response_text.strip()
        else:
            return {
                "error": None,
                "message": response_text,
                "description": "No code changes were made - the AI provided a text response instead.",
                "suggestions": [],
            }

    # Extract description
    desc_match = re.search(r"<description>(.*?)</description>", response_text, re.DOTALL)
    description = desc_match.group(1).strip() if desc_match else user_message

    # Extract suggestions
    suggestions = []
    sugg_match = re.search(r"<suggestions>(.*?)</suggestions>", response_text, re.DOTALL)
    if sugg_match:
        try:
            import json
            suggestions = json.loads(sugg_match.group(1).strip())
        except (json.JSONDecodeError, ValueError):
            # Parse as plain text lines
            suggestions = [
                line.strip().lstrip("- ").lstrip("• ")
                for line in sugg_match.group(1).strip().split("\n")
                if line.strip()
            ]

    # Determine version number
    existing_versions = (
        db.query(GameVersion)
        .filter(GameVersion.session_id == session.id)
        .count()
    )
    version_number = existing_versions + 1

    # Save the new version
    version_id = str(uuid.uuid4())
    version_filename = f"{version_id}.html"
    version_path = os.path.join(VERSIONS_DIR, version_filename)

    with open(version_path, "w", encoding="utf-8") as f:
        f.write(new_code)

    # Create version record
    version = GameVersion(
        id=version_id,
        session_id=session.id,
        user_id=session.user_id,
        version_number=version_number,
        description=description,
        file_path=version_filename,
        parent_version_id=parent_version_id,
    )
    db.add(version)

    # Save assistant message
    assistant_msg = ChatMessage(
        session_id=session.id,
        role="assistant",
        content=response_text,
    )
    db.add(assistant_msg)
    db.commit()

    return {
        "version_id": version_id,
        "version_number": version_number,
        "description": description,
        "suggestions": suggestions[:3],
        "error": None,
    }


def get_base_game_path() -> str:
    return BASE_GAME_PATH


def get_version_path(version_id: str, db: Session) -> Optional[str]:
    version = db.query(GameVersion).filter(GameVersion.id == version_id).first()
    if not version:
        return None
    return os.path.join(VERSIONS_DIR, version.file_path)


def create_initial_version(session_id: str, db: Session) -> GameVersion:
    """Create the initial version (copy of base game) for a session."""
    version_id = str(uuid.uuid4())
    version_filename = f"{version_id}.html"
    version_path = os.path.join(VERSIONS_DIR, version_filename)

    shutil.copy2(BASE_GAME_PATH, version_path)

    version = GameVersion(
        id=version_id,
        session_id=session_id,
        version_number=0,
        description="Original game - base version",
        file_path=version_filename,
    )
    db.add(version)
    db.commit()
    db.refresh(version)
    return version
