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

The game is a single HTML file (~4800 lines) containing:
- CSS styles for UI (overlay, HUD, menus, controls)
- HTML structure (overlay, HUD, vehicle menu, weapon menu, canvas)
- JavaScript module using Three.js for 3D rendering
- Features: vehicles, weapons, tricks, zones, building climbing, wingsuit, etc.

RULES:
1. You receive the FULL game HTML and a user request
2. Return your changes as SEARCH/REPLACE blocks (NOT the full file - it's too large)
3. Each block finds exact text in the file and replaces it
4. Do NOT remove existing features unless explicitly asked
5. Maintain all imports (Three.js from CDN, importmap)
6. Keep the code working - test your mental model of the code
7. Be creative with additions but keep the game stable

FORMAT for changes - use one or more SEARCH/REPLACE blocks:
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
