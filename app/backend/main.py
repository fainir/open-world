import os
import uuid
import asyncio
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.backend.database import get_db, init_db
from app.backend.models import User, ChatSession, ChatMessage, GameVersion
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

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    api_key: str


class SaveVersionRequest(BaseModel):
    version_id: str


class ShareVersionRequest(BaseModel):
    version_id: str


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

    # Find current latest version path
    latest_version = (
        db.query(GameVersion)
        .filter(GameVersion.session_id == session.id)
        .order_by(GameVersion.version_number.desc())
        .first()
    )
    current_path = None
    if latest_version:
        current_path = os.path.join(VERSIONS_DIR, latest_version.file_path)

    # Run agent in thread to not block the event loop
    result = await asyncio.to_thread(
        run_agent, req.api_key, req.message, session, db, current_path
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
            "is_saved": v.is_saved,
            "is_shared": v.is_shared,
            "share_slug": v.share_slug,
            "created_at": v.created_at.isoformat() if v.created_at else None,
        }
        for v in versions
    ]


@app.post("/api/versions/save")
def api_save_version(
    req: SaveVersionRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    version = db.query(GameVersion).filter(GameVersion.id == req.version_id).first()
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")

    version.is_saved = True
    version.user_id = user.id
    db.commit()
    return {"status": "saved", "version_id": version.id}


@app.post("/api/versions/share")
def api_share_version(
    req: ShareVersionRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    version = db.query(GameVersion).filter(GameVersion.id == req.version_id).first()
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")

    if not version.share_slug:
        version.share_slug = str(uuid.uuid4())[:8]
    version.is_shared = True
    version.user_id = user.id
    db.commit()
    return {"status": "shared", "share_slug": version.share_slug}


@app.get("/api/user/versions")
def api_user_versions(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    versions = (
        db.query(GameVersion)
        .filter(GameVersion.user_id == user.id, GameVersion.is_saved == True)
        .order_by(GameVersion.created_at.desc())
        .all()
    )
    return [
        {
            "id": v.id,
            "version_number": v.version_number,
            "description": v.description,
            "is_shared": v.is_shared,
            "share_slug": v.share_slug,
            "created_at": v.created_at.isoformat() if v.created_at else None,
        }
        for v in versions
    ]


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


@app.get("/shared/{share_slug}")
def shared_page(share_slug: str, db: Session = Depends(get_db)):
    """Serve the shared game as a standalone page."""
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


@app.get("/{path:path}")
def serve_spa(path: str):
    """Serve the SPA for all non-API routes."""
    # Check if it's a static file
    static_path = os.path.join(STATIC_DIR, path)
    if path and os.path.isfile(static_path):
        return FileResponse(static_path)
    # Serve index.html for SPA routing
    index_path = os.path.join(STATIC_DIR, "index.html")
    return FileResponse(index_path, media_type="text/html")
