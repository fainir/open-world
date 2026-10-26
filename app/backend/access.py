"""Private studio access. A public UUID is never an ownership credential."""
import hashlib
import hmac
import re

from fastapi import HTTPException, Request

from app.backend.auth import hash_api_key
from app.backend.models import ChatSession, GameVersion


def guest_hash(request: Request):
    proof = request.headers.get("x-openworld-guest", "")
    if not re.fullmatch(r"[A-Za-z0-9_-]{43}", proof):
        return None
    return hashlib.sha256(proof.encode()).hexdigest()


def require_session(db, session_id, request, user):
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    allowed = False
    if session and session.user_id:
        allowed = bool(user and session.user_id == user.id)
    elif session:
        proof = guest_hash(request)
        if session.guest_access_hash:
            allowed = bool(proof and hmac.compare_digest(session.guest_access_hash, proof))
        else:
            # Existing guest sessions can be recovered only with their original provider key.
            legacy = request.headers.get("x-openworld-legacy-key", "")
            allowed = bool(32 <= len(legacy) <= 256 and session.api_key_hash and
                           hmac.compare_digest(session.api_key_hash, hash_api_key(legacy)))
    if not allowed:
        raise HTTPException(404, "Session not found")
    return session


def require_version(db, version_id, request, user, allow_shared=False):
    version = db.query(GameVersion).filter(GameVersion.id == version_id).first()
    if not version:
        raise HTTPException(404, "Version not found")
    if not (allow_shared and version.is_shared):
        require_session(db, version.session_id, request, user)
    return version


def claim_session(db, session, user, request):
    """An authenticated caller with guest proof can adopt only that proven session."""
    if session.user_id or not user:
        return
    require_session(db, session.id, request, user)
    session.user_id = user.id
    session.guest_access_hash = None
    session.api_key_hash = None
    db.query(GameVersion).filter(GameVersion.session_id == session.id).update({"user_id": user.id})
