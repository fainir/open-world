import hashlib
import os
import re
import uuid
import random
import asyncio
import threading
from typing import Optional
from datetime import datetime, timezone

from fastapi import FastAPI, Depends, HTTPException, Query, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, RedirectResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.backend.database import get_db, init_db, DATA_DIR
from app.backend.models import (
    User,
    ChatSession,
    ChatMessage,
    GameVersion,
    ContactMessage,
    Star,
)
from app.backend.auth import (
    SignupRequest,
    LoginRequest,
    TokenResponse,
    signup,
    login,
    get_current_user_optional,
    get_current_user_required,
)
from app.backend.access import guest_hash, require_session, require_version, claim_session
from app.backend.game_security import game_response, studio_shell
from app.backend.request_limits import boundaries
from app.backend.recovery import snapshot, health as recovery_health, PUBLICATION_LOCK
from app.backend.agent import (
    run_agent,
    GAME_MODEL,
    get_base_game_path,
    create_initial_version,
    VERSIONS_DIR,
)

app = FastAPI(title="Open World Game Studio", version="1.0.0")
app.middleware("http")(boundaries)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in os.environ.get("STUDIO_ORIGINS", "https://open-world.gg").split(",") if origin.strip()],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Redirect www → bare domain ──
@app.middleware("http")
async def redirect_www(request: Request, call_next):
    host = request.headers.get("host", "")
    if host.startswith("www."):
        bare = host[4:]
        url = request.url.replace(scheme="https").replace(netloc=bare)
        return RedirectResponse(url=str(url), status_code=301)
    return await call_next(request)


# ── Startup ──


def _seed_store():
    """Seed the store with demo published versions with unique visual themes."""
    from app.backend.database import SessionLocal
    from app.backend.auth import hash_password

    db = SessionLocal()
    try:
        # Get or create demo user
        demo_user = db.query(User).filter(User.username == "OpenWorld").first()
        if not demo_user:
            demo_user = User(
                email="demo@openworld.game",
                username="OpenWorld",
                password_hash=hash_password(str(uuid.uuid4())),
            )
            db.add(demo_user)
            db.commit()
            db.refresh(demo_user)

        # Check if we need to (re)seed
        demo_published = (
            db.query(GameVersion)
            .filter(
                GameVersion.user_id == demo_user.id, GameVersion.is_published == True
            )
            .all()
        )

        if demo_published:
            # Check if already themed (v2) by looking for THEME marker
            fpath = os.path.join(VERSIONS_DIR, demo_published[0].file_path)
            if os.path.exists(fpath):
                with open(fpath, "r", encoding="utf-8") as f:
                    header = f.read(200)
                if "<!-- THEME:" in header:
                    return  # Already have themed versions

            # Delete old seed versions
            for v in demo_published:
                fp = os.path.join(VERSIONS_DIR, v.file_path)
                if os.path.exists(fp):
                    os.remove(fp)
                db.query(Star).filter(Star.version_id == v.id).delete()
                db.delete(v)
            db.commit()

        base_path = get_base_game_path()
        if not os.path.exists(base_path):
            return

        demo_session = ChatSession(user_id=demo_user.id)
        db.add(demo_session)
        db.commit()
        db.refresh(demo_session)

        with open(base_path, "r", encoding="utf-8") as f:
            base_html = f.read()

        seeds = [
            {
                "title": "Neon Night City",
                "desc": "Cyberpunk nightscape with neon purple skies and glowing waters",
                "replacements": [
                    ("<title>Open World</title>", "<title>Neon Night City</title>"),
                    ("<h1>OPEN WORLD</h1>", "<h1>NEON NIGHT CITY</h1>"),
                    ("FogExp2(0xb0d4ee,0.00020)", "FogExp2(0x0a0028,0.00028)"),
                    ("toneMappingExposure=1.2", "toneMappingExposure=0.6"),
                    (
                        "DirectionalLight(0xffeedd,3.0)",
                        "DirectionalLight(0x6644cc,1.5)",
                    ),
                    ("AmbientLight(0x88aacc,1.5)", "AmbientLight(0x221155,0.8)"),
                    (
                        "HemisphereLight(0x99ccff,0x88aa66,1.0)",
                        "HemisphereLight(0x3322aa,0x110033,0.5)",
                    ),
                    (
                        "vec3 top=vec3(0.28,0.52,0.92),mid=vec3(0.50,0.72,0.96),hor=vec3(0.78,0.88,0.96)",
                        "vec3 top=vec3(0.02,0.01,0.12),mid=vec3(0.06,0.02,0.20),hor=vec3(0.12,0.04,0.28)",
                    ),
                    ("vec3(0.45,0.55,0.7)", "vec3(0.05,0.02,0.15)"),
                    (
                        "col+=vec3(1,0.95,0.8)*pow(max(sd,0.0),900.0)*3.0;col+=vec3(1,0.85,0.5)*pow(max(sd,0.0),80.0)*0.5;col+=vec3(1,0.7,0.3)*pow(max(sd,0.0),8.0)*0.12",
                        "col+=vec3(0.6,0.2,1.0)*pow(max(sd,0.0),400.0)*2.0;col+=vec3(0.4,0.1,0.8)*pow(max(sd,0.0),40.0)*0.4;col+=vec3(0.3,0.1,0.5)*pow(max(sd,0.0),8.0)*0.15",
                    ),
                    ("vec3(0.95,0.92,0.86)", "vec3(0.15,0.08,0.30)"),
                    (
                        "mix(vec3(.08,.28,.48),vec3(.05,.18,.38),.4),vec3(.35,.58,.82),fr*.65);col+=vec3(1,.9,.7)",
                        "mix(vec3(.06,.02,.28),vec3(.08,.01,.32),.4),vec3(.22,.08,.55),fr*.65);col+=vec3(.5,.2,1.)",
                    ),
                ],
            },
            {
                "title": "Sunset Paradise",
                "desc": "Golden hour sunset with warm orange skies and shimmering waters",
                "replacements": [
                    ("<title>Open World</title>", "<title>Sunset Paradise</title>"),
                    ("<h1>OPEN WORLD</h1>", "<h1>SUNSET PARADISE</h1>"),
                    ("FogExp2(0xb0d4ee,0.00020)", "FogExp2(0xf5a050,0.00018)"),
                    ("toneMappingExposure=1.2", "toneMappingExposure=1.4"),
                    ("Vector3(0.45,0.55,-0.3)", "Vector3(0.85,0.12,-0.2)"),
                    (
                        "DirectionalLight(0xffeedd,3.0)",
                        "DirectionalLight(0xff8833,2.5)",
                    ),
                    ("AmbientLight(0x88aacc,1.5)", "AmbientLight(0xcc8844,1.2)"),
                    (
                        "HemisphereLight(0x99ccff,0x88aa66,1.0)",
                        "HemisphereLight(0xff9966,0x884422,0.8)",
                    ),
                    (
                        "vec3 top=vec3(0.28,0.52,0.92),mid=vec3(0.50,0.72,0.96),hor=vec3(0.78,0.88,0.96)",
                        "vec3 top=vec3(0.15,0.10,0.45),mid=vec3(0.60,0.25,0.35),hor=vec3(0.95,0.55,0.25)",
                    ),
                    ("vec3(0.45,0.55,0.7)", "vec3(0.50,0.20,0.15)"),
                    (
                        "col+=vec3(1,0.95,0.8)*pow(max(sd,0.0),900.0)*3.0;col+=vec3(1,0.85,0.5)*pow(max(sd,0.0),80.0)*0.5;col+=vec3(1,0.7,0.3)*pow(max(sd,0.0),8.0)*0.12",
                        "col+=vec3(1,0.7,0.2)*pow(max(sd,0.0),500.0)*4.0;col+=vec3(1,0.5,0.15)*pow(max(sd,0.0),30.0)*0.8;col+=vec3(1,0.4,0.1)*pow(max(sd,0.0),5.0)*0.25",
                    ),
                    ("vec3(0.95,0.92,0.86)", "vec3(1.0,0.65,0.30)"),
                    (
                        "mix(vec3(.08,.28,.48),vec3(.05,.18,.38),.4),vec3(.35,.58,.82),fr*.65);col+=vec3(1,.9,.7)",
                        "mix(vec3(.20,.12,.05),vec3(.15,.08,.03),.4),vec3(.60,.35,.15),fr*.65);col+=vec3(1,.6,.2)",
                    ),
                ],
            },
            {
                "title": "Arctic Tundra",
                "desc": "Frozen icy landscape with pale blue skies and crystal-clear waters",
                "replacements": [
                    ("<title>Open World</title>", "<title>Arctic Tundra</title>"),
                    ("<h1>OPEN WORLD</h1>", "<h1>ARCTIC TUNDRA</h1>"),
                    ("FogExp2(0xb0d4ee,0.00020)", "FogExp2(0xd8e8f0,0.00035)"),
                    ("toneMappingExposure=1.2", "toneMappingExposure=1.5"),
                    (
                        "DirectionalLight(0xffeedd,3.0)",
                        "DirectionalLight(0xddeeff,2.0)",
                    ),
                    ("AmbientLight(0x88aacc,1.5)", "AmbientLight(0xaaccee,2.0)"),
                    (
                        "HemisphereLight(0x99ccff,0x88aa66,1.0)",
                        "HemisphereLight(0xccddff,0xaabbdd,1.2)",
                    ),
                    (
                        "vec3 top=vec3(0.28,0.52,0.92),mid=vec3(0.50,0.72,0.96),hor=vec3(0.78,0.88,0.96)",
                        "vec3 top=vec3(0.55,0.70,0.92),mid=vec3(0.72,0.82,0.95),hor=vec3(0.88,0.92,0.96)",
                    ),
                    ("vec3(0.45,0.55,0.7)", "vec3(0.75,0.82,0.90)"),
                    (
                        "col+=vec3(1,0.95,0.8)*pow(max(sd,0.0),900.0)*3.0;col+=vec3(1,0.85,0.5)*pow(max(sd,0.0),80.0)*0.5;col+=vec3(1,0.7,0.3)*pow(max(sd,0.0),8.0)*0.12",
                        "col+=vec3(1,0.98,0.95)*pow(max(sd,0.0),900.0)*2.5;col+=vec3(0.9,0.92,1.0)*pow(max(sd,0.0),80.0)*0.4;col+=vec3(0.8,0.85,1.0)*pow(max(sd,0.0),8.0)*0.1",
                    ),
                    ("vec3(0.95,0.92,0.86)", "vec3(0.92,0.95,1.0)"),
                    (
                        "mix(vec3(.08,.28,.48),vec3(.05,.18,.38),.4),vec3(.35,.58,.82),fr*.65);col+=vec3(1,.9,.7)",
                        "mix(vec3(.15,.35,.55),vec3(.10,.28,.48),.4),vec3(.50,.70,.90),fr*.65);col+=vec3(.9,.95,1.)",
                    ),
                ],
            },
            {
                "title": "Volcanic World",
                "desc": "Fiery volcanic landscape with dark red skies and molten lava waters",
                "replacements": [
                    ("<title>Open World</title>", "<title>Volcanic World</title>"),
                    ("<h1>OPEN WORLD</h1>", "<h1>VOLCANIC WORLD</h1>"),
                    ("FogExp2(0xb0d4ee,0.00020)", "FogExp2(0x200800,0.00025)"),
                    ("toneMappingExposure=1.2", "toneMappingExposure=0.8"),
                    (
                        "DirectionalLight(0xffeedd,3.0)",
                        "DirectionalLight(0xff4400,2.0)",
                    ),
                    ("AmbientLight(0x88aacc,1.5)", "AmbientLight(0x441100,0.6)"),
                    (
                        "HemisphereLight(0x99ccff,0x88aa66,1.0)",
                        "HemisphereLight(0x882200,0x220000,0.5)",
                    ),
                    (
                        "vec3 top=vec3(0.28,0.52,0.92),mid=vec3(0.50,0.72,0.96),hor=vec3(0.78,0.88,0.96)",
                        "vec3 top=vec3(0.08,0.02,0.02),mid=vec3(0.20,0.05,0.02),hor=vec3(0.45,0.12,0.05)",
                    ),
                    ("vec3(0.45,0.55,0.7)", "vec3(0.15,0.03,0.01)"),
                    (
                        "col+=vec3(1,0.95,0.8)*pow(max(sd,0.0),900.0)*3.0;col+=vec3(1,0.85,0.5)*pow(max(sd,0.0),80.0)*0.5;col+=vec3(1,0.7,0.3)*pow(max(sd,0.0),8.0)*0.12",
                        "col+=vec3(1,0.3,0.05)*pow(max(sd,0.0),300.0)*3.5;col+=vec3(1,0.2,0.0)*pow(max(sd,0.0),30.0)*0.6;col+=vec3(0.8,0.15,0.0)*pow(max(sd,0.0),5.0)*0.2",
                    ),
                    ("vec3(0.95,0.92,0.86)", "vec3(0.50,0.15,0.05)"),
                    (
                        "mix(vec3(.08,.28,.48),vec3(.05,.18,.38),.4),vec3(.35,.58,.82),fr*.65);col+=vec3(1,.9,.7)",
                        "mix(vec3(.25,.04,.01),vec3(.18,.02,.00),.4),vec3(.50,.12,.02),fr*.65);col+=vec3(1,.3,.05)",
                    ),
                ],
            },
            {
                "title": "Enchanted Forest",
                "desc": "Mystical green world with emerald skies and enchanted glowing waters",
                "replacements": [
                    ("<title>Open World</title>", "<title>Enchanted Forest</title>"),
                    ("<h1>OPEN WORLD</h1>", "<h1>ENCHANTED FOREST</h1>"),
                    ("FogExp2(0xb0d4ee,0.00020)", "FogExp2(0x1a3a1a,0.00025)"),
                    ("toneMappingExposure=1.2", "toneMappingExposure=1.0"),
                    (
                        "DirectionalLight(0xffeedd,3.0)",
                        "DirectionalLight(0x88ff88,2.0)",
                    ),
                    ("AmbientLight(0x88aacc,1.5)", "AmbientLight(0x225522,1.0)"),
                    (
                        "HemisphereLight(0x99ccff,0x88aa66,1.0)",
                        "HemisphereLight(0x44aa55,0x113311,0.8)",
                    ),
                    (
                        "vec3 top=vec3(0.28,0.52,0.92),mid=vec3(0.50,0.72,0.96),hor=vec3(0.78,0.88,0.96)",
                        "vec3 top=vec3(0.05,0.18,0.12),mid=vec3(0.10,0.30,0.20),hor=vec3(0.25,0.50,0.35)",
                    ),
                    ("vec3(0.45,0.55,0.7)", "vec3(0.08,0.20,0.12)"),
                    (
                        "col+=vec3(1,0.95,0.8)*pow(max(sd,0.0),900.0)*3.0;col+=vec3(1,0.85,0.5)*pow(max(sd,0.0),80.0)*0.5;col+=vec3(1,0.7,0.3)*pow(max(sd,0.0),8.0)*0.12",
                        "col+=vec3(0.4,1.0,0.5)*pow(max(sd,0.0),600.0)*2.5;col+=vec3(0.3,0.8,0.4)*pow(max(sd,0.0),60.0)*0.4;col+=vec3(0.2,0.6,0.3)*pow(max(sd,0.0),8.0)*0.12",
                    ),
                    ("vec3(0.95,0.92,0.86)", "vec3(0.30,0.55,0.35)"),
                    (
                        "mix(vec3(.08,.28,.48),vec3(.05,.18,.38),.4),vec3(.35,.58,.82),fr*.65);col+=vec3(1,.9,.7)",
                        "mix(vec3(.02,.18,.10),vec3(.01,.15,.08),.4),vec3(.12,.45,.25),fr*.65);col+=vec3(.3,1.,.5)",
                    ),
                ],
            },
        ]

        for i, seed in enumerate(seeds):
            vid = str(uuid.uuid4())
            slug = str(uuid.uuid4())[:8]
            fname = f"{vid}.html"
            fpath = os.path.join(VERSIONS_DIR, fname)

            html = f"<!-- THEME: {seed['title']} -->\n" + base_html
            for old, new in seed["replacements"]:
                html = html.replace(old, new, 1)

            with open(fpath, "w", encoding="utf-8") as f:
                f.write(html)

            version = GameVersion(
                id=vid,
                session_id=demo_session.id,
                user_id=demo_user.id,
                version_number=i + 1,
                description=seed["desc"],
                file_path=fname,
                is_shared=True,
                share_slug=slug,
                is_published=True,
                published_at=datetime.now(timezone.utc),
                publish_title=seed["title"],
            )
            db.add(version)
        db.commit()
    finally:
        db.close()


@app.on_event("startup")
def on_startup():
    if os.environ.get('RAILWAY_ENVIRONMENT_ID') and len(os.environ.get('JWT_SECRET', '')) < 32:
        raise RuntimeError('A stable production JWT_SECRET of at least 32 characters is required')
    if os.environ.get('RAILWAY_ENVIRONMENT_ID') and not all(os.environ.get(name) for name in ['DATA_DIR','VERSIONS_DIR']):
        raise RuntimeError('Persistent production DATA_DIR and VERSIONS_DIR are required')
    database = os.path.join(DATA_DIR, 'openworld.db')
    if os.path.exists(database):
        snapshot(DATA_DIR, VERSIONS_DIR, get_base_game_path())
    init_db()
    if os.environ.get("SEED_DEMO_STORE") == "1":
        _seed_store()
    snapshot(DATA_DIR, VERSIONS_DIR, get_base_game_path())
    threading.Thread(target=_recovery_loop, daemon=True, name='openworld-recovery').start()


def _recovery_loop():
    import time
    while True:
        time.sleep(12 * 3600)
        try:
            snapshot(DATA_DIR, VERSIONS_DIR, get_base_game_path())
        except Exception:
            # Health fails once the last verified copy ages out; no private exception content.
            print('[Recovery] Snapshot failed; see health endpoint')


@app.get("/healthz")
def healthz(db: Session = Depends(get_db)):
    try:
        from sqlalchemy import text
        db.execute(text('SELECT 1'))
        paths = db.query(GameVersion.file_path).all()
        files_ok = os.path.isfile(get_base_game_path()) and all(
            os.path.basename(name) == name and os.path.isfile(os.path.join(VERSIONS_DIR, name)) for (name,) in paths)
        recovery = recovery_health(DATA_DIR)
        ok = files_ok and recovery['ok']
        return JSONResponse({'status': 'ok' if ok else 'degraded', 'database': 'ok',
                             'gameFiles': files_ok, 'recovery': recovery, 'providerMode': 'user-supplied-key', 'model': GAME_MODEL},
                            status_code=200 if ok else 503, headers={'Cache-Control':'no-store'})
    except Exception:
        return JSONResponse({'status':'degraded','database':'unavailable'}, status_code=503,
                            headers={'Cache-Control':'no-store'})


# ── Pydantic schemas ──


class ImageData(BaseModel):
    data: str = Field(max_length=6_000_000)
    media_type: str = "image/png"

    @field_validator('media_type')
    @classmethod
    def image_type(cls, value):
        if value not in ['image/png', 'image/jpeg', 'image/gif', 'image/webp']:
            raise ValueError('Unsupported image type')
        return value

    @field_validator('data')
    @classmethod
    def image_size(cls, value):
        import base64
        try:
            decoded = base64.b64decode(value, validate=True)
        except ValueError:
            raise ValueError('Invalid image')
        if not decoded or len(decoded) > 4 * 1024 * 1024:
            raise ValueError('Image must be at most 4MB')
        return value


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    session_id: Optional[str] = Field(default=None, max_length=36)
    current_version_id: Optional[str] = Field(default=None, max_length=36)
    api_key: str = Field(min_length=10, max_length=256)
    image: Optional[ImageData] = None


class VersionIdRequest(BaseModel):
    version_id: str = Field(min_length=1, max_length=36)


class ContactRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: str = Field(min_length=3, max_length=254)
    message: str = Field(min_length=1, max_length=8000)


class PublishRequest(BaseModel):
    version_id: str = Field(min_length=1, max_length=36)
    title: Optional[str] = Field(default=None, max_length=100)


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


_generation_slots = asyncio.Semaphore(2)
_active_generations = set()


@app.post("/api/chat")
async def api_chat(req: ChatRequest, request: Request, db: Session = Depends(get_db),
                   user: Optional[User] = Depends(get_current_user_optional)):
    identity = (user.id if user else guest_hash(request)) or request.client.host
    if _generation_slots.locked() or identity in _active_generations:
        raise HTTPException(429, "A generation is already running; please try again shortly")
    async with _generation_slots:
        _active_generations.add(identity)
        try:
            return await _api_chat_impl(req, request, db, user)
        finally:
            _active_generations.discard(identity)


async def _api_chat_impl(
    req: ChatRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional),
):
    if not req.api_key or len(req.api_key) < 10:
        raise HTTPException(
            status_code=400, detail="Please provide a valid Anthropic API key"
        )
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    session = None
    selected = None
    if req.session_id:
        session = require_session(db, req.session_id, request, user)
    if req.current_version_id:
        selected = require_version(db, req.current_version_id, request, user, allow_shared=True)
        if session and selected.session_id != session.id:
            raise HTTPException(400, "Start a new chat to branch another game")
    if session:
        claim_session(db, session, user, request)
        if not session.user_id and not session.guest_access_hash:
            proof = guest_hash(request)
            if not proof:
                raise HTTPException(400, "Reload the studio to secure this guest session")
            session.guest_access_hash = proof
            session.api_key_hash = None
        db.commit()
    else:
        proof = guest_hash(request)
        if not user and not proof:
            raise HTTPException(400, "Reload the studio to start a secure guest session")
        session = ChatSession(user_id=user.id if user else None,
                              guest_access_hash=proof if not user else None)
        db.add(session)
        db.commit()
        db.refresh(session)
        branch_path = os.path.join(VERSIONS_DIR, selected.file_path) if selected else None
        initial = create_initial_version(session.id, db, source_path=branch_path)
        initial.user_id = session.user_id
        db.commit()

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
        run_agent,
        req.api_key,
        req.message,
        session,
        db,
        current_path,
        parent_version_id,
        image_data,
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
    request: Request,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional),
):
    require_session(db, session_id, request, user)
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
            "is_published": v.is_published,
            "created_at": v.created_at.isoformat() if v.created_at else None,
        }
        for v in versions
    ]


@app.get("/api/versions/info/{version_id}")
def api_version_info(version_id: str, request: Request, db: Session = Depends(get_db),
                     user: Optional[User] = Depends(get_current_user_optional)):
    v = require_version(db, version_id, request, user, allow_shared=True)
    return {
        "id": v.id,
        "description": v.description,
        "publish_title": v.publish_title,
        "version_number": v.version_number,
    }


@app.post("/api/versions/share")
def api_share_version(
    req: VersionIdRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional),
):
    version = require_version(db, req.version_id, request, user)
    if not version.share_slug:
        version.share_slug = uuid.uuid4().hex
    version.is_shared = True
    db.commit()
    return {"status": "shared", "share_slug": version.share_slug}


@app.post("/api/versions/suggest")
def api_suggest_version(
    req: VersionIdRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    version = require_version(db, req.version_id, request, user)
    claim_session(db, version.session, user, request)
    if version.is_suggested:
        return {
            "status": "already_suggested",
            "suggestion_status": version.suggestion_status,
        }

    # Find the user prompt that led to this version
    user_prompt = version.description
    if version.session_id:
        last_user_msg = (
            db.query(ChatMessage)
            .filter(
                ChatMessage.session_id == version.session_id, ChatMessage.role == "user"
            )
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


# ── Store / Publish routes ──


@app.post("/api/versions/publish")
def api_publish_version(
    req: PublishRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    version = require_version(db, req.version_id, request, user)
    claim_session(db, version.session, user, request)
    if version.is_published:
        return {"status": "already_published", "share_slug": version.share_slug}
    if not version.share_slug:
        version.share_slug = uuid.uuid4().hex
    version.is_shared = True
    version.is_published = True
    version.published_at = datetime.now(timezone.utc)
    version.user_id = user.id
    if req.title:
        version.publish_title = req.title.strip()[:100]
    db.commit()
    return {"status": "published", "share_slug": version.share_slug}


@app.get("/api/store/versions")
def api_store_versions(
    sort: str = Query("recent"),
    page: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional),
):
    from sqlalchemy import func

    star_count = (
        db.query(Star.version_id, func.count(Star.id).label("star_count"))
        .group_by(Star.version_id)
        .subquery()
    )

    query = (
        db.query(GameVersion, star_count.c.star_count)
        .outerjoin(star_count, GameVersion.id == star_count.c.version_id)
        .filter(GameVersion.is_published == True)
    )

    if sort == "stars":
        query = query.order_by(
            func.coalesce(star_count.c.star_count, 0).desc(),
            GameVersion.published_at.desc(),
        )
    else:
        query = query.order_by(GameVersion.published_at.desc())

    total = query.count()
    results = query.offset(page * limit).limit(limit).all()

    user_stars = set()
    if user:
        user_stars = {
            s.version_id
            for s in db.query(Star.version_id).filter(Star.user_id == user.id).all()
        }

    return {
        "total": total,
        "page": page,
        "versions": [
            {
                "id": v.id,
                "title": v.publish_title or v.description,
                "description": v.description,
                "share_slug": v.share_slug,
                "username": v.user.username if v.user else "Anonymous",
                "star_count": sc or 0,
                "starred_by_me": v.id in user_stars,
                "published_at": v.published_at.isoformat() if v.published_at else None,
            }
            for v, sc in results
        ],
    }


@app.post("/api/store/star/{version_id}")
def api_toggle_star(
    version_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    version = (
        db.query(GameVersion)
        .filter(GameVersion.id == version_id, GameVersion.is_published == True)
        .first()
    )
    if not version:
        raise HTTPException(status_code=404, detail="Published version not found")

    existing = (
        db.query(Star)
        .filter(Star.user_id == user.id, Star.version_id == version_id)
        .first()
    )

    if existing:
        db.delete(existing)
        db.commit()
        new_count = db.query(Star).filter(Star.version_id == version_id).count()
        return {"status": "unstarred", "star_count": new_count}
    else:
        star = Star(user_id=user.id, version_id=version_id)
        db.add(star)
        db.commit()
        new_count = db.query(Star).filter(Star.version_id == version_id).count()
        return {"status": "starred", "star_count": new_count}


@app.get("/api/store/random")
def api_store_random(db: Session = Depends(get_db)):
    published = db.query(GameVersion).filter(GameVersion.is_published == True).all()
    if not published:
        raise HTTPException(status_code=404, detail="No published versions yet")
    chosen = random.choice(published)
    return RedirectResponse(url=f"/shared/{chosen.share_slug}", status_code=302)


@app.get("/api/store/random-slug")
def api_store_random_slug(db: Session = Depends(get_db)):
    published = db.query(GameVersion).filter(GameVersion.is_published == True).all()
    if not published:
        return {"share_slug": None, "title": None}
    chosen = random.choice(published)
    return {
        "share_slug": chosen.share_slug,
        "title": chosen.publish_title or chosen.description,
    }


# ── Admin routes ──

ADMIN_USERNAMES = [
    s.strip() for s in os.environ.get("ADMIN_USERNAMES", "").split(",") if s.strip()
]
ADMIN_EMAILS = [
    s.strip() for s in os.environ.get("ADMIN_EMAILS", "").split(",") if s.strip()
]


def get_admin_user(user: User = Depends(get_current_user_required)) -> User:
    is_admin = (
        user.is_admin or user.username in ADMIN_USERNAMES or user.email in ADMIN_EMAILS
    )
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
    versions = db.query(GameVersion).order_by(GameVersion.created_at.desc()).all()
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

    with PUBLICATION_LOCK:
        # Copy version file to replace the base game
        from app.backend.agent import _atomic_game_write

        version_path = os.path.join(VERSIONS_DIR, version.file_path)
        if not os.path.exists(version_path):
            raise HTTPException(status_code=404, detail="Version file not found")

        base_path = get_base_game_path()
        with open(version_path, "r", encoding="utf-8") as source:
            _atomic_game_write(base_path, source.read())

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
    msg = ContactMessage(
        name=req.name.strip(), email=req.email.strip(), message=req.message.strip()
    )
    db.add(msg)
    db.commit()
    return {"status": "ok"}


@app.get("/api/admin/contacts")
def api_admin_contacts(
    db: Session = Depends(get_db), admin: User = Depends(get_admin_user)
):
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
def api_admin_mark_read(
    contact_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
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
    return game_response(path)


@app.get("/game/version/{version_id}")
def serve_game_version(version_id: str, request: Request, db: Session = Depends(get_db),
                       user: Optional[User] = Depends(get_current_user_optional)):
    version = require_version(db, version_id, request, user, allow_shared=True)
    path = os.path.join(VERSIONS_DIR, version.file_path)
    if not os.path.isfile(path):
        raise HTTPException(404, "Version not found")
    return game_response(path)


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
    return game_response(path)


# ── Chat history ──


@app.get("/api/chat/history/{session_id}")
def api_chat_history(session_id: str, request: Request, db: Session = Depends(get_db),
                     user: Optional[User] = Depends(get_current_user_optional)):
    require_session(db, session_id, request, user)
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
            content = _re.sub(
                r"<game_code>.*?</game_code>",
                "[Game code updated]",
                content,
                flags=_re.DOTALL,
            )
            content = _re.sub(
                r"<<<SEARCH.*?>>>SEARCH",
                "[Code changes applied]",
                content,
                flags=_re.DOTALL,
            )
            # Extract just description and suggestions
            desc_match = _re.search(
                r"<description>(.*?)</description>", msg.content, _re.DOTALL
            )
            sugg_match = _re.search(
                r"<suggestions>(.*?)</suggestions>", msg.content, _re.DOTALL
            )
            if desc_match:
                content = desc_match.group(1).strip()
                if sugg_match:
                    content += f"\n\nSuggestions: {sugg_match.group(1).strip()}"

        result.append(
            {
                "id": msg.id,
                "role": msg.role,
                "content": content,
                "created_at": msg.created_at.isoformat() if msg.created_at else None,
            }
        )
    return result


# ── Static files & SPA ──

STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# ── Overlay injection ──


def _load_overlay_html() -> str:
    """Load the overlay HTML/CSS/JS (fresh on every request so deploys take effect)."""
    overlay_path = os.path.join(STATIC_DIR, "overlay.html")
    with open(overlay_path, "r", encoding="utf-8") as f:
        return f.read()


def _revalidated_html(request: Request, html: str) -> Response:
    """Serve a page browsers may keep but must re-check on every visit.

    "no-cache" (unlike "no-store") lets the browser ask whether the page
    changed; an unchanged game then costs a 304 instead of the whole page,
    and a new version is still picked up on the next visit.
    """
    etag = '"' + hashlib.sha256(html.encode("utf-8")).hexdigest()[:32] + '"'
    headers = {"Cache-Control": "no-cache", "ETag": etag}
    if etag in request.headers.get("if-none-match", ""):
        return Response(status_code=304, headers=headers)
    return HTMLResponse(html, headers=headers)


@app.get("/")
def serve_home(request: Request):
    return _revalidated_html(request, studio_shell(_load_overlay_html()))


@app.get("/v/{version_id}")
def serve_version_with_overlay(version_id: str, request: Request):
    # The shell contains no private game or metadata; the owner-authenticated fetch loads it.
    return _revalidated_html(request, studio_shell(_load_overlay_html()))


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
    return game_response(path)


@app.get("/{path:path}")
def serve_catchall(path: str):
    """Serve static files or redirect to home."""
    static_path = os.path.realpath(os.path.join(STATIC_DIR, path))
    if path and os.path.commonpath([os.path.realpath(STATIC_DIR), static_path]) == os.path.realpath(STATIC_DIR) and os.path.isfile(static_path):
        return FileResponse(static_path)
    from fastapi.responses import RedirectResponse

    return RedirectResponse(url="/", status_code=302)
