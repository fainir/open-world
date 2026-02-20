import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Integer, Boolean
from sqlalchemy.orm import relationship
from app.backend.database import Base


def _uuid():
    return str(uuid.uuid4())


def _now():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=_uuid)
    email = Column(String, unique=True, nullable=False, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=_now)

    versions = relationship("GameVersion", back_populates="user", order_by="desc(GameVersion.created_at)")
    sessions = relationship("ChatSession", back_populates="user", order_by="desc(ChatSession.created_at)")


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    api_key_hash = Column(String, nullable=True)
    created_at = Column(DateTime, default=_now)

    user = relationship("User", back_populates="sessions")
    messages = relationship("ChatMessage", back_populates="session", order_by="ChatMessage.created_at")
    versions = relationship("GameVersion", back_populates="session", order_by="desc(GameVersion.created_at)")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(String, primary_key=True, default=_uuid)
    session_id = Column(String, ForeignKey("chat_sessions.id"), nullable=False)
    role = Column(String, nullable=False)  # "user" or "assistant"
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=_now)

    session = relationship("ChatSession", back_populates="messages")


class GameVersion(Base):
    __tablename__ = "game_versions"

    id = Column(String, primary_key=True, default=_uuid)
    session_id = Column(String, ForeignKey("chat_sessions.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    version_number = Column(Integer, nullable=False)
    description = Column(Text, nullable=False)
    file_path = Column(String, nullable=False)
    is_shared = Column(Boolean, default=False)
    share_slug = Column(String, unique=True, nullable=True, index=True)
    parent_version_id = Column(String, ForeignKey("game_versions.id"), nullable=True)
    # Suggestion system
    is_suggested = Column(Boolean, default=False)
    suggestion_status = Column(String, nullable=True)  # pending, approved, declined
    suggested_at = Column(DateTime, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    reviewed_by = Column(String, ForeignKey("users.id"), nullable=True)
    user_prompt = Column(Text, nullable=True)  # The original user request
    created_at = Column(DateTime, default=_now)

    session = relationship("ChatSession", back_populates="versions")
    user = relationship("User", back_populates="versions")
