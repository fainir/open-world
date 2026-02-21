import os
import re
import uuid
import asyncio
import functools
from typing import Optional

import rjsmin

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.backend.database import get_db, init_db
from app.backend.models import User, ChatSession, ChatMessage, GameVersion, ContactMessage
from app.backend.auth import (
    SignupRequest, LoginRequest, TokenResponse,
    signup, login, get_current_user_optional, get_current_user_required,
    hash_api_key,
)
from app.backend.agent import (
    run_agent, get_base_game_path, get_version_path,
    create_initial_version, VERSIONS_DIR,
)

app = FastAPI(title="Open World Game Studio", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Startup ──

@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


# ── Pydantic schemas ──

class ImageData(BaseModel):
    data: str  # base64
    media_type: str = "image/png"

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    current_version_id: Optional[str] = None
    api_key: str
    image: Optional[ImageData] = None


class VersionIdRequest(BaseModel):
    version_id: str


class ContactRequest(BaseModel):
    name: str
    email: str
    message: str


# ── Auth routes ──

@app.post("/api/auth/signup", response_model=TokenResponse)
def api_signup(req: SignupRequest, db: Session = Depends(get_db)):
    return signup(req, db)


@app.post("/api/auth/login", response_model=TokenResponse)
def api_login(req: LoginRequest, db: Session = Depends(get_db)):
    return login(req, db)


@app.get("/api/auth/me")
def api_me(user: User = Depends(get_current_user_required)):
    return {"id": user.id, "email": user.email, "username": user.username}


# ── Chat / Agent routes ──

@app.post("/api/chat")
async def api_chat(
    req: ChatRequest,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional),
):
    if not req.api_key or len(req.api_key) < 10:
        raise HTTPException(status_code=400, detail="Please provide a valid Anthropic API key")
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    # Get or create session
    session = None
    if req.session_id:
        session = db.query(ChatSession).filter(ChatSession.id == req.session_id).first()

    if not session:
        session = ChatSession(
            user_id=user.id if user else None,
            api_key_hash=hash_api_key(req.api_key),
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        # Create initial version
        create_initial_version(session.id, db)

    # Save user message
    user_msg = ChatMessage(
        session_id=session.id,
        role="user",
        content=req.message,
    )
    db.add(user_msg)
    db.commit()

    # Find the version to modify: use the selected version, or fall back to latest
    current_path = None
    parent_version_id = None
    if req.current_version_id:
        selected = db.query(GameVersion).filter(GameVersion.id == req.current_version_id).first()
        if selected:
            current_path = os.path.join(VERSIONS_DIR, selected.file_path)
            parent_version_id = selected.id
    if not current_path:
        latest_version = (
            db.query(GameVersion)
            .filter(GameVersion.session_id == session.id)
            .order_by(GameVersion.version_number.desc())
            .first()
        )
        if latest_version:
            current_path = os.path.join(VERSIONS_DIR, latest_version.file_path)
            parent_version_id = latest_version.id

    # Prepare image data if provided
    image_data = None
    if req.image:
        image_data = {"data": req.image.data, "media_type": req.image.media_type}

    # Run agent in thread to not block the event loop
    result = await asyncio.to_thread(
        run_agent, req.api_key, req.message, session, db, current_path, parent_version_id, image_data
    )

    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])

    return {
        "session_id": session.id,
        "version_id": result.get("version_id"),
        "version_number": result.get("version_number"),
        "description": result.get("description"),
        "suggestions": result.get("suggestions", []),
        "message": result.get("message"),
    }


# ── Version routes ──

@app.get("/api/versions/{session_id}")
def api_get_versions(
    session_id: str,
    db: Session = Depends(get_db),
):
    versions = (
        db.query(GameVersion)
        .filter(GameVersion.session_id == session_id)
        .order_by(GameVersion.version_number.desc())
        .all()
    )
    return [
        {
            "id": v.id,
            "version_number": v.version_number,
            "description": v.description,
            "is_shared": v.is_shared,
            "share_slug": v.share_slug,
            "is_suggested": v.is_suggested,
            "suggestion_status": v.suggestion_status,
            "created_at": v.created_at.isoformat() if v.created_at else None,
        }
        for v in versions
    ]


@app.post("/api/versions/share")
def api_share_version(
    req: VersionIdRequest,
    db: Session = Depends(get_db),
):
    version = db.query(GameVersion).filter(GameVersion.id == req.version_id).first()
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    if not version.share_slug:
        version.share_slug = str(uuid.uuid4())[:8]
    version.is_shared = True
    db.commit()
    return {"status": "shared", "share_slug": version.share_slug}


@app.post("/api/versions/suggest")
def api_suggest_version(
    req: VersionIdRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    version = db.query(GameVersion).filter(GameVersion.id == req.version_id).first()
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    if version.is_suggested:
        return {"status": "already_suggested", "suggestion_status": version.suggestion_status}

    # Find the user prompt that led to this version
    user_prompt = version.description
    if version.session_id:
        last_user_msg = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == version.session_id, ChatMessage.role == "user")
            .order_by(ChatMessage.created_at.desc())
            .first()
        )
        if last_user_msg:
            user_prompt = last_user_msg.content

    from datetime import datetime, timezone
    version.is_suggested = True
    version.suggestion_status = "pending"
    version.suggested_at = datetime.now(timezone.utc)
    version.user_id = user.id
    version.user_prompt = user_prompt
    db.commit()
    return {"status": "suggested"}


# ── Admin routes ──

ADMIN_USERNAMES = [s.strip() for s in os.environ.get("ADMIN_USERNAMES", "").split(",") if s.strip()]
ADMIN_EMAILS = [s.strip() for s in os.environ.get("ADMIN_EMAILS", "").split(",") if s.strip()]


def get_admin_user(user: User = Depends(get_current_user_required)) -> User:
    is_admin = user.is_admin or user.username in ADMIN_USERNAMES or user.email in ADMIN_EMAILS
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


@app.get("/api/admin/suggestions")
def api_admin_suggestions(
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    suggestions = (
        db.query(GameVersion)
        .filter(GameVersion.is_suggested == True)
        .order_by(GameVersion.suggested_at.desc())
        .all()
    )
    return [
        {
            "id": v.id,
            "version_number": v.version_number,
            "description": v.description,
            "user_prompt": v.user_prompt,
            "suggestion_status": v.suggestion_status,
            "suggested_at": v.suggested_at.isoformat() if v.suggested_at else None,
            "reviewed_at": v.reviewed_at.isoformat() if v.reviewed_at else None,
            "username": v.user.username if v.user else "Anonymous",
            "share_slug": v.share_slug,
            "created_at": v.created_at.isoformat() if v.created_at else None,
        }
        for v in suggestions
    ]


@app.get("/api/admin/all-versions")
def api_admin_all_versions(
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    versions = (
        db.query(GameVersion)
        .order_by(GameVersion.created_at.desc())
        .all()
    )
    return [
        {
            "id": v.id,
            "version_number": v.version_number,
            "description": v.description,
            "user_prompt": v.user_prompt,
            "is_suggested": v.is_suggested,
            "suggestion_status": v.suggestion_status,
            "suggested_at": v.suggested_at.isoformat() if v.suggested_at else None,
            "reviewed_at": v.reviewed_at.isoformat() if v.reviewed_at else None,
            "username": v.user.username if v.user else "Anonymous",
            "session_id": v.session_id,
            "share_slug": v.share_slug,
            "is_shared": v.is_shared,
            "created_at": v.created_at.isoformat() if v.created_at else None,
        }
        for v in versions
    ]


@app.post("/api/admin/approve/{version_id}")
def api_admin_approve(
    version_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    version = db.query(GameVersion).filter(GameVersion.id == version_id).first()
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")

    # Copy version file to replace the base game
    import shutil
    version_path = os.path.join(VERSIONS_DIR, version.file_path)
    if not os.path.exists(version_path):
        raise HTTPException(status_code=404, detail="Version file not found")

    base_path = get_base_game_path()
    shutil.copy2(version_path, base_path)

    from datetime import datetime, timezone
    version.suggestion_status = "approved"
    version.reviewed_at = datetime.now(timezone.utc)
    version.reviewed_by = admin.id
    db.commit()
    return {"status": "approved", "version_id": version.id}


@app.post("/api/admin/decline/{version_id}")
def api_admin_decline(
    version_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    version = db.query(GameVersion).filter(GameVersion.id == version_id).first()
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")

    from datetime import datetime, timezone
    version.suggestion_status = "declined"
    version.reviewed_at = datetime.now(timezone.utc)
    version.reviewed_by = admin.id
    db.commit()
    return {"status": "declined", "version_id": version.id}


# ── Contact routes ──

@app.post("/api/contact")
def api_contact(req: ContactRequest, db: Session = Depends(get_db)):
    if not req.name.strip() or not req.email.strip() or not req.message.strip():
        raise HTTPException(status_code=400, detail="All fields are required")
    msg = ContactMessage(name=req.name.strip(), email=req.email.strip(), message=req.message.strip())
    db.add(msg)
    db.commit()
    return {"status": "ok"}


@app.get("/api/admin/contacts")
def api_admin_contacts(db: Session = Depends(get_db), admin: User = Depends(get_admin_user)):
    messages = db.query(ContactMessage).order_by(ContactMessage.created_at.desc()).all()
    return [
        {
            "id": m.id,
            "name": m.name,
            "email": m.email,
            "message": m.message,
            "is_read": m.is_read,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in messages
    ]


@app.post("/api/admin/contacts/{contact_id}/read")
def api_admin_mark_read(contact_id: str, db: Session = Depends(get_db), admin: User = Depends(get_admin_user)):
    msg = db.query(ContactMessage).filter(ContactMessage.id == contact_id).first()
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    msg.is_read = True
    db.commit()
    return {"status": "ok"}


# ── Game file serving ──

@app.get("/game/base")
def serve_base_game():
    path = get_base_game_path()
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Base game not found")
    return FileResponse(path, media_type="text/html")


@app.get("/game/version/{version_id}")
def serve_game_version(version_id: str, db: Session = Depends(get_db)):
    path = get_version_path(version_id, db)
    if not path or not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Version not found")
    return FileResponse(path, media_type="text/html")


@app.get("/game/shared/{share_slug}")
def serve_shared_game(share_slug: str, db: Session = Depends(get_db)):
    version = (
        db.query(GameVersion)
        .filter(GameVersion.share_slug == share_slug, GameVersion.is_shared == True)
        .first()
    )
    if not version:
        raise HTTPException(status_code=404, detail="Shared game not found")
    path = os.path.join(VERSIONS_DIR, version.file_path)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Game file not found")
    return FileResponse(path, media_type="text/html")


# ── Chat history ──

@app.get("/api/chat/history/{session_id}")
def api_chat_history(session_id: str, db: Session = Depends(get_db)):
    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at)
        .all()
    )
    import re as _re
    result = []
    for msg in messages:
        content = msg.content
        if msg.role == "assistant":
            # Strip out code blocks and SEARCH/REPLACE blocks for display
            content = _re.sub(r"<game_code>.*?</game_code>", "[Game code updated]", content, flags=_re.DOTALL)
            content = _re.sub(r"<<<SEARCH.*?>>>SEARCH", "[Code changes applied]", content, flags=_re.DOTALL)
            # Extract just description and suggestions
            desc_match = _re.search(r"<description>(.*?)</description>", msg.content, _re.DOTALL)
            sugg_match = _re.search(r"<suggestions>(.*?)</suggestions>", msg.content, _re.DOTALL)
            if desc_match:
                content = desc_match.group(1).strip()
                if sugg_match:
                    content += f"\n\nSuggestions: {sugg_match.group(1).strip()}"

        result.append({
            "id": msg.id,
            "role": msg.role,
            "content": content,
            "created_at": msg.created_at.isoformat() if msg.created_at else None,
        })
    return result


# ── Static files & SPA ──

STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# ── Overlay injection ──

@functools.lru_cache(maxsize=1)
def _load_overlay_html() -> str:
    """Load the overlay HTML/CSS/JS once and cache it."""
    overlay_path = os.path.join(STATIC_DIR, "overlay.html")
    with open(overlay_path, "r", encoding="utf-8") as f:
        return f.read()


def _inject_overlay(game_html: str) -> str:
    """Inject the studio overlay into game HTML before </body>."""
    overlay = _load_overlay_html()
    if "</body>" in game_html:
        return game_html.replace("</body>", f"\n{overlay}\n</body>", 1)
    return game_html + f"\n{overlay}"


_INLINE_SCRIPT_RE = re.compile(r"<script((?:(?!src=)[^>])*)>(.*?)</script>", re.DOTALL)


def _obfuscate_html(html: str) -> str:
    """Minify inline JS in HTML so source code is not easily readable."""

    def _minify_script(match: re.Match) -> str:
        attrs = match.group(1)
        content = match.group(2)
        if not content.strip():
            return match.group(0)
        try:
            minified = rjsmin.jsmin(content)
            return f"<script{attrs}>{minified}</script>"
        except Exception:
            return match.group(0)

    return _INLINE_SCRIPT_RE.sub(_minify_script, html)


@app.get("/")
def serve_home():
    """Serve the base game with studio overlay (no iframe)."""
    path = get_base_game_path()
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Base game not found")
    with open(path, "r", encoding="utf-8") as f:
        game_html = f.read()
    return HTMLResponse(_inject_overlay(_obfuscate_html(game_html)))


@app.get("/v/{version_id}")
def serve_version_with_overlay(version_id: str, db: Session = Depends(get_db)):
    """Serve a specific version with studio overlay."""
    path = get_version_path(version_id, db)
    if not path or not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Version not found")
    with open(path, "r", encoding="utf-8") as f:
        game_html = f.read()
    return HTMLResponse(_inject_overlay(_obfuscate_html(game_html)))


@app.get("/admin")
def admin_page():
    """Serve the admin panel."""
    admin_path = os.path.join(STATIC_DIR, "admin.html")
    return FileResponse(admin_path, media_type="text/html")


@app.get("/contact")
def contact_page():
    """Serve the contact page."""
    contact_path = os.path.join(STATIC_DIR, "contact.html")
    return FileResponse(contact_path, media_type="text/html")


@app.get("/shared/{share_slug}")
def shared_page(share_slug: str, db: Session = Depends(get_db)):
    """Serve the shared game as a standalone page (no overlay)."""
    version = (
        db.query(GameVersion)
        .filter(GameVersion.share_slug == share_slug, GameVersion.is_shared == True)
        .first()
    )
    if not version:
        raise HTTPException(status_code=404, detail="Shared game not found")
    path = os.path.join(VERSIONS_DIR, version.file_path)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Game file not found")
    with open(path, "r", encoding="utf-8") as f:
        game_html = f.read()
    return HTMLResponse(_obfuscate_html(game_html))


@app.get("/{path:path}")
def serve_catchall(path: str):
    """Serve static files or redirect to home."""
    static_path = os.path.join(STATIC_DIR, path)
    if path and os.path.isfile(static_path):
        return FileResponse(static_path)
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/", status_code=302)
